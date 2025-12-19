"""
File system event handler for automatic site rebuilds.

Watches for file changes and triggers incremental rebuilds with debouncing.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from bengal.cache.paths import STATE_DIR_NAME
from bengal.server.build_hooks import run_post_build_hooks, run_pre_build_hooks
from bengal.server.ignore_filter import IgnoreFilter
from bengal.server.reload_controller import ReloadDecision, controller
from bengal.server.utils import is_process_isolation_enabled
from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error
from bengal.utils.cli_output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


# Module-level executor instance (lazy-initialized)
# This allows the executor to be shared across multiple BuildHandler instances
# and ensures proper cleanup on shutdown
_build_executor = None
_executor_lock = threading.Lock()


def get_build_executor():
    """
    Get or create the shared BuildExecutor instance.

    Returns:
        BuildExecutor instance (lazily created on first access)
    """
    global _build_executor
    with _executor_lock:
        if _build_executor is None:
            from bengal.server.build_executor import BuildExecutor

            _build_executor = BuildExecutor(max_workers=1)
            logger.debug("build_executor_created_lazy")
        return _build_executor


def shutdown_build_executor():
    """
    Shutdown the shared BuildExecutor instance.

    Called during server cleanup to ensure proper resource release.
    """
    global _build_executor
    with _executor_lock:
        if _build_executor is not None:
            logger.debug("build_executor_shutdown_requested")
            _build_executor.shutdown(wait=True)
            _build_executor = None
            logger.debug("build_executor_shutdown_complete")


class BuildHandler(FileSystemEventHandler):
    """
    File system event handler that triggers site rebuild with debouncing.

    Dev reload policy (source-gated):
    - Only source edits (markdown/content, config, templates, theme assets) trigger reloads.
    - CSS-only source edits send reload-css; any other source edits send full reload.
    - We do NOT scan output directories for diffs in dev; this avoids dev-only churn
      (timestamps, site-wide JSON/TXT) from causing spurious reloads.

    Features:
    - Debounced rebuilds (0.3s delay to batch changes)
    - Incremental builds for speed (5-10x faster)
    - Parallel rendering
    - Stale object reference prevention (clears ephemeral state)
    - Build error recovery (errors don't crash server)
    - Automatic cache invalidation for config/template changes
    - Handles all file events: create, modify, delete, move/rename

    Ignored files:
    - Output directory (public/)
    - Bengal state directory (.bengal/) - logs, cache, metrics
    - Temp files (.tmp, ~, .swp, .swo)
    - System files (.DS_Store, .git)
    - Python cache (__pycache__, .pyc)

    Example:
        handler = BuildHandler(site, host="localhost", port=5173)
        observer = Observer()
        observer.schedule(handler, "content/", recursive=True)
        observer.start()
    """

    # Debounce delay in seconds (slightly higher to coalesce noisy editor events)
    DEBOUNCE_DELAY = 0.3

    def __init__(
        self,
        site: Any,
        host: str = "localhost",
        port: int = 5173,
    ) -> None:
        """
        Initialize the build handler.

        Args:
            site: Site instance
            host: Server host
            port: Server port
        """
        self.site = site
        self.host = host
        self.port = port
        self.building = False
        self.pending_changes: set[str] = set()
        self.pending_event_types: set[str] = set()  # Track event types for build strategy
        self.debounce_timer: threading.Timer | None = None
        self.timer_lock = threading.Lock()

        # Create ignore filter from config (with output_dir always ignored)
        self._ignore_filter = self._create_ignore_filter()

        # Check if process isolation is enabled (BENGAL_DEV_SERVER_V2=1 or config)
        config = getattr(self.site, "config", {}) or {}
        self._use_process_isolation = is_process_isolation_enabled(config)
        if self._use_process_isolation:
            logger.info("build_handler_process_isolation_enabled")
        else:
            logger.debug("build_handler_process_isolation_disabled")

    def _create_ignore_filter(self) -> IgnoreFilter:
        """
        Create IgnoreFilter from site config.

        Includes:
        - User-configured patterns from dev_server config
        - Output directory (to prevent rebuild loops)
        - Default transient file patterns (vim swap, etc.)

        Returns:
            Configured IgnoreFilter instance
        """
        # Get user config, fall back to empty dict
        config = getattr(self.site, "config", {}) or {}

        # Add standard suffix patterns that _should_ignore_file used
        standard_globs = [
            "*.swp",
            "*.swo",
            "*.swx",  # Vim swap files
            "*.tmp",
            "*.pyc",
            "*.pyo",
            "*.orig",
            "*.rej",
            "*~",  # Editor backup files
            "*~~",  # Alternate backup suffixes
            ".DS_Store",
            ".bengal-cache.json",
        ]

        # Merge with user-configured patterns
        dev_server = config.get("dev_server", {})
        user_patterns = dev_server.get("exclude_patterns", [])

        all_patterns = standard_globs + list(user_patterns)

        # Get user regex patterns
        user_regex = dev_server.get("exclude_regex", [])

        return IgnoreFilter(
            glob_patterns=all_patterns,
            regex_patterns=user_regex,
            directories=[self.site.output_dir] if hasattr(self.site, "output_dir") else [],
            include_defaults=True,  # Include .git, node_modules, etc.
        )

    def _clear_ephemeral_state(self) -> None:
        """Clear ephemeral state safely via Site API."""
        try:
            self.site.reset_ephemeral_state()
        except AttributeError:
            # Backward compatibility: inline clear for older Site versions
            logger.debug("clearing_ephemeral_state_legacy", site_root=str(self.site.root_path))
            self.site.pages = []
            self.site.sections = []
            self.site.assets = []
            self.site.taxonomies = {}
            self.site.menu = {}
            self.site.menu_builders = {}
            if hasattr(self.site, "xref_index"):
                self.site.xref_index = {}
            self.site.invalidate_regular_pages_cache()

    def _should_regenerate_autodoc(self, changed_paths: set[str]) -> bool:
        """
        Check if any changed file is in autodoc source directories.

        Args:
            changed_paths: Set of changed file paths

        Returns:
            True if any changed file is a Python file in autodoc source directories,
            or an OpenAPI spec file
        """
        if not hasattr(self.site, "config") or not self.site.config:
            return False

        autodoc_config = self.site.config.get("autodoc", {})

        # Check Python source directories
        python_config = autodoc_config.get("python", {})
        if python_config.get("enabled", False):
            source_dirs = python_config.get("source_dirs", [])
            for changed_path in changed_paths:
                path = Path(changed_path)
                for source_dir in source_dirs:
                    source_path = self.site.root_path / source_dir
                    try:
                        path.relative_to(source_path)
                        if path.suffix == ".py":
                            logger.debug(
                                "autodoc_source_changed",
                                file=str(path),
                                source_dir=source_dir,
                                type="python",
                            )
                            return True
                    except ValueError:
                        continue

        # Check OpenAPI spec file
        openapi_config = autodoc_config.get("openapi", {})
        if openapi_config.get("enabled", False):
            spec_file = openapi_config.get("spec_file")
            if spec_file:
                spec_path = self.site.root_path / spec_file
                for changed_path in changed_paths:
                    path = Path(changed_path)
                    if path == spec_path or path.resolve() == spec_path.resolve():
                        logger.debug(
                            "autodoc_source_changed",
                            file=str(path),
                            type="openapi",
                        )
                        return True
                    # Also check for referenced schema files ($ref)
                    # if they're in the same directory as the spec
                    spec_dir = spec_path.parent
                    try:
                        path.relative_to(spec_dir)
                        if path.suffix in (".yaml", ".yml", ".json"):
                            logger.debug(
                                "autodoc_source_changed",
                                file=str(path),
                                type="openapi_ref",
                            )
                            return True
                    except ValueError:
                        continue

        return False

    def _is_template_change(self, changed_paths: set[str]) -> bool:
        """
        Check if any changed file is a template (.html) in templates/themes directories.

        Template files affect all rendered pages, but their dependencies aren't fully
        tracked (especially for autodoc virtual pages). When templates change, we need
        to trigger a full rebuild to ensure all pages render with the updated templates.

        Args:
            changed_paths: Set of changed file paths

        Returns:
            True if any changed file is a template file that affects page rendering
        """
        import bengal

        bengal_dir = Path(bengal.__file__).parent

        # Get root_path safely (handles mock sites in tests)
        root_path = getattr(self.site, "root_path", None)
        if not root_path:
            return False

        # Directories where template changes should trigger full rebuild
        template_dirs = [
            # Site-level custom templates
            root_path / "templates",
            # Project theme directory
            root_path / "themes",
        ]

        # Add bundled theme templates if using a bundled theme
        theme = getattr(self.site, "theme", None)
        if theme:
            bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
            if bundled_theme_dir.exists():
                template_dirs.append(bundled_theme_dir)

        for changed_path in changed_paths:
            path = Path(changed_path)

            # Only check .html files (templates)
            if path.suffix.lower() != ".html":
                continue

            # Check if the file is within any template directory
            for template_dir in template_dirs:
                if not template_dir.exists():
                    continue
                try:
                    path.relative_to(template_dir)
                    logger.debug(
                        "template_change_detected",
                        file=str(path),
                        template_dir=str(template_dir),
                    )
                    return True
                except ValueError:
                    continue

        return False

    def _should_ignore_file(self, file_path: str) -> bool:
        """
        Check if file should be ignored (temp files, swap files, etc).

        Uses IgnoreFilter for pattern matching with support for:
        - Glob patterns (user-configurable via exclude_patterns)
        - Regex patterns (user-configurable via exclude_regex)
        - Default ignored directories (.git, node_modules, etc.)
        - Output directory (always ignored to prevent loops)

        Args:
            file_path: Path to file

        Returns:
            True if file should be ignored
        """
        path = Path(file_path)

        # Use IgnoreFilter for pattern matching
        if self._ignore_filter(path):
            return True

        # Also check for STATE_DIR_NAME explicitly (bengal cache directory)
        # This is critical to prevent rebuild loops
        return STATE_DIR_NAME in path.parts

    def _trigger_build(self) -> None:
        """
        Execute the actual build (called after debounce delay).

        This method:
        1. Clears ephemeral state to prevent stale object references
        2. Runs an incremental + parallel build for speed
        3. Displays build statistics
        4. Notifies connected SSE clients to reload

        Note:
            Build errors are caught and logged but don't crash the server.
            The server continues running even if a build fails.

        Raises:
            Exception: Build failures are logged but don't propagate
        """
        with self.timer_lock:
            self.debounce_timer = None

            if self.building:
                logger.debug("build_skipped", reason="build_already_in_progress")
                return

            self.building = True

            # Signal to request handler that build is in progress
            # This causes directory listings to show "rebuilding" page instead
            try:
                from bengal.server.request_handler import BengalRequestHandler

                BengalRequestHandler.set_build_in_progress(True)
            except Exception as e:
                logger.debug("build_state_signal_failed", error=str(e))

            # Get first changed file for display
            file_name = "multiple files"
            changed_files = list(self.pending_changes)
            file_count = len(changed_files)

            if self.pending_changes:
                first_file = next(iter(self.pending_changes))
                file_name = Path(first_file).name
                if file_count > 1:
                    file_name = f"{file_name} (+{file_count - 1} more)"

            # Determine build strategy based on event types and file types
            # Force full rebuild for:
            # 1. Structural changes (created/deleted/moved files) - affects section relationships
            # 2. Content file changes (.md) - may affect navigation via hidden/visibility frontmatter
            # 3. Template changes - affects all rendered pages
            # 4. Autodoc source changes (.py, OpenAPI specs) - need to regenerate autodoc pages
            # Use incremental only for asset-only modifications (CSS, JS, images)
            needs_full_rebuild = bool({"created", "deleted", "moved"} & self.pending_event_types)

            # Check if template files changed (.html in templates/themes directories)
            # Template dependencies aren't fully tracked (especially for autodoc virtual pages),
            # so force full rebuild when any template changes to ensure all pages render correctly.
            template_changed = self._is_template_change(set(changed_files))
            if template_changed and not needs_full_rebuild:
                needs_full_rebuild = True
                logger.debug(
                    "full_rebuild_triggered_by_template",
                    reason="template_file_changed",
                )

            # Check if autodoc regeneration is needed (Python source or OpenAPI spec changed)
            autodoc_changed = self._should_regenerate_autodoc(set(changed_files))
            if autodoc_changed and not needs_full_rebuild:
                # Force full rebuild to regenerate all autodoc pages
                # Phase 1: coarse-grained; Phase 2 will enable selective rebuild
                needs_full_rebuild = True
                logger.debug(
                    "full_rebuild_triggered_by_autodoc",
                    reason="autodoc_source_changed",
                )

            # Use shared constant for nav-affecting keys (RFC: rfc-incremental-hot-reload-invariants)
            from bengal.utils.incremental_constants import NAV_AFFECTING_KEYS

            nav_frontmatter_keys = NAV_AFFECTING_KEYS

            def _frontmatter_nav_change(path_obj: Path) -> bool:
                """Parse first YAML frontmatter block and detect nav-affecting keys."""
                try:
                    text = path_obj.read_text(encoding="utf-8")
                except Exception as e:
                    logger.debug(
                        "frontmatter_read_failed",
                        file=str(path_obj),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return False

                match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
                if not match:
                    return False
                try:
                    fm = yaml.safe_load(match.group(1)) or {}
                except Exception as e:
                    logger.debug(
                        "frontmatter_parse_failed",
                        file=str(path_obj),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return False

                if not isinstance(fm, dict):
                    return False

                return any(str(key).lower() in nav_frontmatter_keys for key in fm)

            nav_changed_files: set[Path] = set()
            content_changed_files: set[Path] = set()

            if not needs_full_rebuild:
                svg_extensions = {".svg"}
                for changed_path in changed_files:
                    path_obj = Path(changed_path)
                    suffix = path_obj.suffix.lower()

                    if suffix in {".md", ".markdown"}:
                        content_changed_files.add(path_obj)
                        if _frontmatter_nav_change(path_obj):
                            nav_changed_files.add(path_obj)
                            logger.debug(
                                "nav_frontmatter_detected",
                                file=changed_path,
                            )

                    # SVG files in theme assets/icons/ are inlined in HTML, so pages need re-rendering
                    if suffix in svg_extensions:
                        path_str = str(path_obj).replace("\\", "/")
                        if "/themes/" in path_str and "/assets/icons/" in path_str:
                            needs_full_rebuild = True
                            logger.debug(
                                "full_rebuild_triggered_by_svg",
                                reason="svg_icon_changed_inlined_in_html",
                                file=changed_path,
                            )
                            break

                if not needs_full_rebuild:
                    logger.debug(
                        "incremental_allowed_for_content",
                        changed_content=len(content_changed_files),
                        nav_frontmatter=len(nav_changed_files),
                    )

            # Structural changes (create/delete/move) require full content discovery
            structural_changed = bool({"created", "deleted", "moved"} & self.pending_event_types)

            logger.info(
                "rebuild_triggered",
                changed_file_count=file_count,
                changed_files=changed_files[:10],  # Limit to first 10 for readability
                trigger_file=str(changed_files[0]) if changed_files else None,
                event_types=list(self.pending_event_types),
                build_strategy="full" if needs_full_rebuild else "incremental",
                structural_changed=structural_changed,
            )

            self.pending_changes.clear()
            self.pending_event_types.clear()  # Clear event types for next batch

            timestamp = datetime.now().strftime("%H:%M:%S")

            # Use CLIOutput for consistent formatting
            cli = CLIOutput()
            cli.file_change_notice(file_name=file_name, timestamp=timestamp)
            show_building_indicator("Rebuilding")

            build_start = time.time()

            # CRITICAL: Clear ephemeral state before rebuild
            # This prevents stale object references (bug: taxonomy counts wrong)
            self._clear_ephemeral_state()

            # Run pre-build hooks (e.g., npm run build:css)
            # Skip build if any pre-build hook fails
            config = getattr(self.site, "config", {}) or {}
            if not run_pre_build_hooks(config, self.site.root_path):
                show_error("Pre-build hook failed - skipping build", show_art=False)
                cli.request_log_header()
                logger.error("rebuild_skipped", reason="pre_build_hook_failed")
                self.building = False
                try:
                    from bengal.server.request_handler import BengalRequestHandler

                    BengalRequestHandler.set_build_in_progress(False)
                except Exception:
                    pass
                return

            try:
                # Use incremental + parallel for fast dev server rebuilds (5-10x faster)
                # Cache invalidation auto-detects config/template changes and falls back to full rebuild
                # Use WRITER profile for fast builds (can enable specific validators via config)
                # Config can override profile to enable directives validator without full THEME_DEV overhead
                from bengal.utils.profile import BuildProfile

                # Use incremental builds only for file modifications
                # Force full rebuild for structural changes (created/deleted/moved)
                # to ensure proper section relationships and cascade application
                use_incremental = not needs_full_rebuild

                # Execute build - either in-process or in subprocess depending on config
                if self._use_process_isolation:
                    # Process-isolated build for crash resilience
                    from bengal.server.build_executor import BuildRequest

                    executor = get_build_executor()
                    request = BuildRequest(
                        site_root=str(self.site.root_path),
                        changed_paths=tuple(str(p) for p in changed_files),
                        incremental=use_incremental,
                        profile="WRITER",
                        nav_changed_paths=tuple(str(p) for p in nav_changed_files),
                        structural_changed=structural_changed,
                        parallel=True,
                    )

                    # Use a reasonable timeout (5 minutes for large sites)
                    result = executor.submit(request, timeout=300.0)
                    build_duration = result.build_time_ms / 1000

                    if not result.success:
                        raise RuntimeError(result.error_message or "Build failed in subprocess")

                    # Create a stats-like object for display
                    class _BuildStats:
                        def __init__(self, pages: int, time_ms: float, outputs: tuple):
                            self.total_pages = pages
                            self.build_time_ms = time_ms
                            self.incremental = use_incremental
                            self.parallel = True
                            self.cache_bypass_hits = 0
                            self.cache_bypass_misses = 0
                            self.changed_outputs = list(outputs)
                            self.skipped = False

                    stats = _BuildStats(
                        result.pages_built, result.build_time_ms, result.changed_outputs
                    )

                    logger.info(
                        "rebuild_complete_subprocess",
                        duration_seconds=round(build_duration, 2),
                        pages_built=result.pages_built,
                    )
                else:
                    # In-process build (default, faster for small sites)
                    # Ensure dev flags remain active on rebuilds
                    try:
                        cfg = self.site.config
                        cfg["dev_server"] = True
                        cfg["fingerprint_assets"] = False
                        cfg.setdefault("minify_assets", False)
                    except Exception as e:
                        logger.debug(
                            "build_handler_dev_config_update_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            action="continuing_without_update",
                        )
                        pass

                    stats = self.site.build(
                        parallel=True,
                        incremental=use_incremental,
                        profile=BuildProfile.WRITER,
                        changed_sources={Path(p) for p in changed_files},
                        nav_changed_sources=nav_changed_files,
                        structural_changed=structural_changed,
                    )
                    build_duration = time.time() - build_start

                display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

                # Run post-build hooks (e.g., custom notifications, cache warming)
                # Log but don't fail if post-build hooks fail
                if not run_post_build_hooks(config, self.site.root_path):
                    logger.warning("post_build_hook_failed", action="continuing")

                # Show server URL after rebuild for easy access
                cli.server_url_inline(host=self.host, port=self.port)
                cli.request_log_header()

                logger.info(
                    "rebuild_complete",
                    duration_seconds=round(build_duration, 2),
                    pages_built=stats.total_pages,
                    incremental=stats.incremental,
                    parallel=stats.parallel,
                    cache_bypass_hits=getattr(stats, "cache_bypass_hits", 0),
                    cache_bypass_misses=getattr(stats, "cache_bypass_misses", 0),
                    process_isolated=self._use_process_isolation,
                )

                # Reload decision (prefer source-gated, then builder hints, then output diff)
                if getattr(stats, "skipped", False):
                    logger.info("reload_suppressed", reason="build_skipped")
                else:
                    # 1) Source-gated quick path: if we know which sources changed, decide directly
                    #    CSS-only → reload-css; otherwise full reload. This avoids output churn.
                    #    SVG files in theme icons need full reload (they're inlined in HTML)
                    if changed_files:
                        try:
                            lower = [str(p).lower() for p in changed_files]
                            # Ignore any changes that might have slipped from output dir just in case
                            src_only = [
                                p for p in lower if "/public/" not in p and "\\public\\" not in p
                            ]

                            # Check for SVG icon changes (need full reload because inlined in HTML)
                            has_svg_icons = any(
                                "/themes/" in p and "/assets/icons/" in p and p.endswith(".svg")
                                for p in src_only
                            )

                            css_only = (
                                bool(src_only)
                                and all(p.endswith(".css") for p in src_only)
                                and not has_svg_icons
                            )

                            if css_only:
                                decision = ReloadDecision(
                                    action="reload-css", reason="css-only", changed_paths=[]
                                )
                            else:
                                decision = ReloadDecision(
                                    action="reload", reason="source-change", changed_paths=[]
                                )
                        except Exception as e:
                            logger.debug(
                                "build_handler_reload_decision_failed",
                                error=str(e),
                                error_type=type(e).__name__,
                                action="using_none_decision",
                            )
                            decision = None
                    else:
                        decision = None

                    # 2) Prefer builder-provided changed outputs if available
                    if decision is None:
                        changed_outputs = getattr(stats, "changed_outputs", None)
                        if isinstance(changed_outputs, list | tuple) and changed_outputs:
                            decision = controller.decide_from_changed_paths(list(changed_outputs))

                    # 3) No source change, no builder hints → suppress reload (dev: source-gated only)
                    if decision is None:
                        decision = ReloadDecision(
                            action="none", reason="no-source-change", changed_paths=[]
                        )

                    if decision.action == "none":
                        logger.info("reload_suppressed", reason=decision.reason)
                    else:
                        # Public API: send structured payload to clients
                        from bengal.server.live_reload import send_reload_payload

                        logger.info(
                            "reload_decision",
                            action=decision.action,
                            reason=decision.reason,
                            changed_paths=len(decision.changed_paths or []),
                        )
                        send_reload_payload(
                            decision.action, decision.reason, decision.changed_paths
                        )

                    # Clear HTML cache after successful rebuild (files have changed)
                    from bengal.server.request_handler import BengalRequestHandler

                    with BengalRequestHandler._html_cache_lock:
                        cache_size = len(BengalRequestHandler._html_cache)
                        BengalRequestHandler._html_cache.clear()
                    if cache_size > 0:
                        logger.debug("html_cache_cleared", entries_removed=cache_size)
            except Exception as e:
                build_duration = time.time() - build_start

                show_error(f"Build failed: {e}", show_art=False)
                cli.blank()
                cli.request_log_header()

                logger.error(
                    "rebuild_failed",
                    duration_seconds=round(build_duration, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    changed_files=changed_files[:5],
                )
            finally:
                self.building = False

                # Clear build-in-progress state for request handler
                try:
                    from bengal.server.request_handler import BengalRequestHandler

                    BengalRequestHandler.set_build_in_progress(False)
                except Exception as e:
                    logger.debug("build_state_clear_failed", error=str(e))

    def _handle_file_event(self, event: FileSystemEvent, event_type: str) -> None:
        """
        Common handler for file system events with debouncing.

        Multiple rapid file changes are batched together and trigger a single
        rebuild after a short delay (DEBOUNCE_DELAY seconds).

        Files in the output directory and matching ignore patterns are skipped
        to prevent infinite rebuild loops.

        Args:
            event: File system event
            event_type: Type of event (created, modified, deleted, moved)

        Note:
            This method implements debouncing by canceling the previous timer
            and starting a new one on each file change.
        """
        if event.is_directory:
            return

        # Skip files in output directory
        try:
            Path(event.src_path).relative_to(self.site.output_dir)
            logger.debug("file_change_ignored", file=event.src_path, reason="in_output_directory")
            return
        except ValueError:
            pass

        # Skip temp files and other files that should be ignored
        if self._should_ignore_file(event.src_path):
            logger.debug("file_change_ignored", file=event.src_path, reason="ignored_pattern")
            return

        # Add to pending changes and track event type
        is_new = event.src_path not in self.pending_changes
        self.pending_changes.add(event.src_path)
        self.pending_event_types.add(event_type)  # Track event type for build strategy

        logger.debug(
            "file_change_detected",
            file=event.src_path,
            event_type=event_type,
            pending_count=len(self.pending_changes),
            is_new_in_batch=is_new,
        )

        # Cancel existing timer and start new one (debouncing)
        with self.timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                logger.debug("debounce_timer_reset", delay_ms=self.DEBOUNCE_DELAY * 1000)

            # Allow override via config: dev.watch.debounce_ms or env BENGAL_DEBOUNCE_MS
            delay = self.DEBOUNCE_DELAY
            import os as _os

            from bengal.server.utils import get_dev_config, safe_int

            debounce_ms_env = _os.environ.get("BENGAL_DEBOUNCE_MS")
            debounce_ms_cfg = (
                get_dev_config(self.site.config, "watch", "debounce_ms")
                if hasattr(self.site, "config")
                else None
            )
            debounce_ms = safe_int(
                debounce_ms_env if debounce_ms_env is not None else debounce_ms_cfg, 0
            )
            if debounce_ms > 0:
                delay = debounce_ms / 1000.0

            self.debounce_timer = threading.Timer(delay, self._trigger_build)
            self.debounce_timer.daemon = True
            self.debounce_timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Handle file deletion events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        """
        Handle file move/rename events.

        Args:
            event: File system event with src_path and dest_path
        """
        # For moved files, we need to track both source and destination
        # The _handle_file_event will handle src_path, and we manually add dest_path
        self._handle_file_event(event, "moved")

        # Also add the destination path if it's not in the output directory
        if hasattr(event, "dest_path"):
            try:
                Path(event.dest_path).relative_to(self.site.output_dir)
                return
            except ValueError:
                pass

            if not self._should_ignore_file(event.dest_path):
                self.pending_changes.add(event.dest_path)
                logger.debug(
                    "file_move_destination_tracked",
                    dest_path=event.dest_path,
                    pending_count=len(self.pending_changes),
                )
