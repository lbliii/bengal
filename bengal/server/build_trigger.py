"""
Build trigger orchestrating the dev server rebuild pipeline.

Coordinates the complete rebuild workflow when file changes are detected,
from pre-build hooks through build execution to client reload notification.

Features:
- Event type classification (created/modified/deleted → full/incremental)
- Pre/post build hook execution with timeout handling
- Process-isolated build submission via BuildExecutor
- Smart reload decisions (CSS-only vs full page reload)
- Navigation change detection for taxonomy rebuilds
- Build state tracking for UI feedback (rebuilding page)

Classes:
BuildTrigger: Main orchestrator coordinating the rebuild pipeline

Architecture:
BuildTrigger is the central coordinator in the rebuild pipeline:

WatcherRunner → BuildTrigger → BuildExecutor
                    ↓
               ReloadController → LiveReload → Browser

Rebuild Flow:
1. WatcherRunner detects file changes, calls on_file_change()
2. BuildTrigger classifies event types (structural vs content-only)
3. Pre-build hooks execute (e.g., npm build, tailwind)
4. BuildExecutor runs Site.build() in subprocess
5. Post-build hooks execute
6. ReloadController decides reload type (CSS-only vs full)
7. LiveReload notifies connected browsers

Rebuild Decisions:
- Created/deleted files → Full rebuild (structural change)
- Modified content files → Incremental rebuild
- Modified CSS/assets → CSS-only hot reload (if no template changes)
- Navigation frontmatter changes → Full rebuild (affects menus/breadcrumbs)

Related:
- bengal/server/watcher_runner.py: Calls BuildTrigger on changes
- bengal/server/build_executor.py: Executes builds in subprocess
- bengal/server/build_hooks.py: Pre/post build hook execution
- bengal/server/reload_controller.py: Reload type decisions
- bengal/server/live_reload.py: Client notification

"""

from __future__ import annotations

import contextlib
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import yaml

from bengal.errors import ErrorCode, create_dev_error, get_dev_server_state
from bengal.orchestration.stats import display_build_stats, show_building_indicator, show_error
from bengal.output import CLIOutput
from bengal.protocols import SiteLike
from bengal.server.build_executor import BuildExecutor, BuildResult
from bengal.server.build_hooks import run_post_build_hooks, run_pre_build_hooks
from bengal.server.build_state import build_state
from bengal.server.reload_controller import ReloadDecision, controller
from bengal.server.utils import get_timestamp
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix
from bengal.utils.stats_minimal import MinimalStats

logger = get_logger(__name__)


class BuildTrigger:
    """
    Triggers builds when file changes are detected.

    All builds are executed via BuildExecutor in a subprocess for:
    - Crash resilience (build crash doesn't kill server)
    - Clean isolation (no stale state between builds)
    - Future-ready (supports free-threaded Python)

    Features:
        - Pre/post build hooks
        - Incremental vs full rebuild detection
        - Navigation frontmatter detection (with caching)
        - Template change detection (with directory caching)
        - Autodoc source change detection
        - Live reload notification

    Caching:
        - Frontmatter cache: (path, mtime) -> has_nav_keys (avoids re-parsing)
        - Template dirs cache: Resolved template directories (avoids exists() calls)

    Example:
            >>> trigger = BuildTrigger(site, host="localhost", port=5173)
            >>> trigger.trigger_build(changed_paths, event_types)

    """

    # Class-level caches (shared across instances for efficiency)
    # Frontmatter cache: path -> (mtime, has_nav_keys)
    _frontmatter_cache: ClassVar[dict[Path, tuple[float, bool]]] = {}
    _frontmatter_cache_max = 500

    # Content hash cache: path -> (mtime, frontmatter_hash, content_hash)
    # Used for content-only change detection (RFC: content-only-hot-reload)
    _content_hash_cache: ClassVar[dict[Path, tuple[float, str, str]]] = {}
    _content_hash_cache_max = 500

    # Template directories cache (per-instance, set to None to invalidate)
    _template_dirs: list[Path] | None = None

    def __init__(
        self,
        site: Any,
        host: str = "localhost",
        port: int = 5173,
        executor: BuildExecutor | None = None,
        version_scope: str | None = None,
    ) -> None:
        """
        Initialize build trigger.

        Args:
            site: Site instance
            host: Server host for URL display
            port: Server port for URL display
            executor: BuildExecutor instance (created if not provided)
            version_scope: Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
        """
        self.site = site
        self.host = host
        self.port = port
        self.version_scope = version_scope
        self._executor = executor or BuildExecutor(max_workers=1)
        self._building = False
        self._build_lock = threading.Lock()
        # Queue for changes that arrive during a build (prevents lost changes)
        self._pending_changes: set[Path] = set()
        self._pending_event_types: set[str] = set()
        # Reset template dirs cache for this instance (theme may differ)
        self._template_dirs = None
        # Track last successful build for error context
        self._last_successful_build: datetime | None = None

    def trigger_build(
        self,
        changed_paths: set[Path],
        event_types: set[str],
    ) -> None:
        """
        Trigger a build for the given changed paths.

        This method:
        1. Determines build strategy (incremental vs full)
        2. Runs pre-build hooks
        3. Submits build to BuildExecutor
        4. Runs post-build hooks
        5. Notifies clients to reload

        If a build is already in progress, changes are queued and will trigger
        another build when the current one completes. This prevents lost changes
        during rapid editing (especially important for autodoc pages).

        Args:
            changed_paths: Set of changed file paths
            event_types: Set of event types (created, modified, deleted, moved)
        """
        with self._build_lock:
            if self._building:
                # Queue changes instead of discarding them
                self._pending_changes.update(changed_paths)
                self._pending_event_types.update(event_types)
                logger.debug(
                    "build_changes_queued",
                    queued_count=len(changed_paths),
                    total_pending=len(self._pending_changes),
                )
                return
            self._building = True

        try:
            self._execute_build(changed_paths, event_types)
        finally:
            # Check for queued changes before releasing lock
            queued_changes: set[Path] = set()
            queued_events: set[str] = set()
            with self._build_lock:
                self._building = False
                if self._pending_changes:
                    queued_changes = self._pending_changes.copy()
                    queued_events = self._pending_event_types.copy()
                    self._pending_changes.clear()
                    self._pending_event_types.clear()

            # Trigger another build if changes were queued during this build
            if queued_changes:
                # Stabilization delay: Give browsers time to fetch updated assets
                # before the next build potentially replaces them again.
                # This prevents CSS disappearing during rapid edit sequences.
                # 100ms is enough for most browser requests to complete while
                # keeping the feedback loop fast.
                time.sleep(0.1)

                logger.info(
                    "build_queued_changes_triggering",
                    queued_count=len(queued_changes),
                    queued_events=list(queued_events),
                )
                # Recursive call to handle the queued changes
                self.trigger_build(queued_changes, queued_events)

    def _execute_build(
        self,
        changed_paths: set[Path],
        event_types: set[str],
    ) -> None:
        """
        Execute the build (internal, called with lock held).
        """
        # Signal build in progress to request handler
        self._set_build_in_progress(True)

        try:
            changed_files = [str(p) for p in changed_paths]
            file_count = len(changed_files)

            # Determine file name for display
            if file_count == 1:
                file_name = Path(changed_files[0]).name
            else:
                first_file = Path(changed_files[0]).name
                file_name = f"{first_file} (+{file_count - 1} more)"

            # Determine build strategy
            needs_full_rebuild = self._needs_full_rebuild(changed_paths, event_types)
            nav_changed_files = self._detect_nav_changes(changed_paths, needs_full_rebuild)
            structural_changed = bool({"created", "deleted", "moved"} & event_types)

            logger.info(
                "rebuild_triggered",
                changed_file_count=file_count,
                changed_files=changed_files[:10],
                build_strategy="full" if needs_full_rebuild else "incremental",
                structural_changed=structural_changed,
            )

            # Display building indicator
            timestamp = get_timestamp()
            cli = CLIOutput()
            cli.file_change_notice(file_name=file_name, timestamp=timestamp)
            show_building_indicator("Rebuilding")

            # RFC: Output Cache Architecture - Capture content hash baseline BEFORE build
            # This enables accurate change detection vs regeneration noise
            if controller._use_content_hashes:
                controller.capture_content_hash_baseline(self.site.output_dir)

            # Run pre-build hooks
            config = getattr(self.site, "config", {}) or {}
            # run_pre_build_hooks expects a dict, use .raw for serialization
            config_dict = config.raw if hasattr(config, "raw") else config
            if not run_pre_build_hooks(config_dict, self.site.root_path):
                show_error("Pre-build hook failed - skipping build", show_art=False)
                cli.request_log_header()
                logger.error("rebuild_skipped", reason="pre_build_hook_failed")
                return

            # Create build options for warm build
            use_incremental = not needs_full_rebuild

            # Warm build: reuse the existing site object instead of creating a new one
            # This eliminates Site.from_config() overhead (~250ms per rebuild)
            from bengal.orchestration.build.options import BuildOptions
            from bengal.utils.observability.profile import BuildProfile

            # Reset all per-build mutable state in one call.
            # Site.prepare_for_rebuild() is the single source of truth for what
            # must be reset between warm builds — including cascade snapshot,
            # content registry, page caches, and URL registry.
            self.site.prepare_for_rebuild()

            build_opts = BuildOptions(
                force_sequential=False,  # Auto-detect based on page count
                incremental=use_incremental,
                profile=BuildProfile.WRITER,
                changed_sources={Path(p) for p in changed_files} if changed_files else None,
                nav_changed_sources=nav_changed_files,
                structural_changed=structural_changed,
            )

            # Apply version scope if set
            if self.version_scope:
                self.site.config["_version_scope"] = self.version_scope

            # Execute warm build directly on the existing site
            build_start = time.time()
            try:
                stats = self.site.build(options=build_opts)
                build_duration = (time.time() - build_start)

                # Build succeeded - convert stats to result-like object for display
                class WarmBuildResult:
                    def __init__(self, stats: Any, build_time: float) -> None:
                        self.success = True
                        self.pages_built = stats.total_pages
                        self.build_time_ms = build_time * 1000
                        self.error_message = None
                        self.changed_outputs = tuple(
                            (str(r.path), r.output_type.value, r.phase)
                            for r in stats.changed_outputs
                        ) if hasattr(stats, 'changed_outputs') else ()
                        self._stats = stats

                result = WarmBuildResult(stats, build_duration)

            except Exception as e:
                # Build crashed - log error and reinitialize site for next build
                build_duration = (time.time() - build_start)
                error_msg = str(e)

                show_error(f"Build failed: {error_msg}", show_art=False)
                cli.request_log_header()

                # Record failure for pattern detection
                error_sig = f"build_failed:{error_msg[:50] if error_msg else 'unknown'}"
                is_new = get_dev_server_state().record_failure(error_sig)
                if not is_new:
                    logger.warning(
                        "recurring_error_detected",
                        error_code=ErrorCode.S003.name,
                        signature=error_sig,
                    )

                logger.error(
                    "rebuild_failed",
                    error_code=ErrorCode.S003.name,
                    duration_seconds=round(build_duration, 2),
                    error=error_msg,
                    changed_files=[str(p) for p in changed_paths][:5],
                    is_recurring=not is_new,
                )

                # Reinitialize site from scratch to recover from corrupted state
                # This ensures the next build starts clean
                try:
                    from bengal.core.site import Site
                    logger.info("warm_build_recovery", action="reinitializing_site")
                    self.site = Site.from_config(self.site.root_path)
                    self.site.dev_mode = True
                except Exception as reinit_error:
                    logger.error(
                        "warm_build_recovery_failed",
                        error=str(reinit_error),
                    )
                return

            # Display build stats
            self._display_stats(result, use_incremental)

            # Run post-build hooks
            if not run_post_build_hooks(config_dict, self.site.root_path):
                logger.warning("post_build_hook_failed", action="continuing")

            # Show server URL
            cli.server_url_inline(host=self.host, port=self.port)
            cli.request_log_header()

            # Record success for session tracking
            self._last_successful_build = datetime.now()
            get_dev_server_state().record_success()

            logger.info(
                "rebuild_complete",
                duration_seconds=round(build_duration, 2),
                pages_built=result.pages_built,
                incremental=use_incremental,
            )

            # Handle reload decision
            self._handle_reload(
                changed_files,
                result.changed_outputs,
                reload_hint=getattr(result, "reload_hint", None),
            )

            # Clear HTML cache
            self._clear_html_cache()

        except Exception as e:
            # Create dev server error context for rich debugging
            # Use next(iter(...)) instead of pop() to avoid mutating the set
            context = create_dev_error(
                e,
                changed_files=[str(p) for p in changed_paths],
                trigger_file=str(next(iter(changed_paths))) if changed_paths else None,
                last_successful_build=self._last_successful_build,
            )

            # Record failure for pattern detection
            error_sig = f"{type(e).__name__}:{str(e)[:50]}"
            is_new = get_dev_server_state().record_failure(error_sig)
            if not is_new:
                logger.warning(
                    "recurring_error_detected",
                    error_code=ErrorCode.S003.name,
                    signature=error_sig,
                )

            logger.error(
                "rebuild_error",
                error_code=ErrorCode.S003.name,
                error=str(e),
                error_type=type(e).__name__,
                likely_cause=context.get_likely_cause(),
                quick_actions=context.quick_actions[:3],
                auto_fixable=context.auto_fixable,
                is_recurring=not is_new,
            )

            # Show auto-fix suggestion if available
            if context.auto_fix_command:
                show_error(f"Build failed: {e}\n\nTry: {context.auto_fix_command}", show_art=False)
        finally:
            self._set_build_in_progress(False)

    def _needs_full_rebuild(
        self,
        changed_paths: set[Path],
        event_types: set[str],
    ) -> bool:
        """
        Determine if a full rebuild is needed.

        Full rebuild triggers:
        - Structural changes (created/deleted/moved files)
        - Template changes (.html in templates/themes)
        - Autodoc source changes (.py, OpenAPI specs)
        - SVG icon changes (inlined in HTML)
        - Shared content changes (_shared/ directory) [versioned sites]
        - Version config changes (versioning.yaml)
        """
        # Structural changes always need full rebuild
        if {"created", "deleted", "moved"} & event_types:
            return True

        # Check for template changes
        if self._is_template_change(changed_paths):
            logger.debug("full_rebuild_triggered_by_template")
            return True

        # Check for autodoc changes
        if self._should_regenerate_autodoc(changed_paths):
            logger.debug("full_rebuild_triggered_by_autodoc")
            return True

        # Check for SVG icon changes (inlined in HTML)
        for path in changed_paths:
            path_str = to_posix(path)
            if (
                path.suffix.lower() == ".svg"
                and "/themes/" in path_str
                and "/assets/icons/" in path_str
            ):
                logger.debug("full_rebuild_triggered_by_svg", file=str(path))
                return True

        # RFC: rfc-versioned-docs-pipeline-integration
        # Check for shared content changes (forces full rebuild for versioned sites)
        if self._is_shared_content_change(changed_paths):
            logger.debug("full_rebuild_triggered_by_shared_content")
            return True

        # Check for version config changes (forces full rebuild)
        if self._is_version_config_change(changed_paths):
            logger.debug("full_rebuild_triggered_by_version_config")
            return True

        return False

    def _is_shared_content_change(self, changed_paths: set[Path]) -> bool:
        """
        Check if any changed path is in _shared/ directory.

        Shared content is included in all versions, so changes require
        a full rebuild to cascade to all versioned pages.

        Args:
            changed_paths: Set of changed file paths

        Returns:
            True if any changed file is in _shared/
        """
        if not getattr(self.site, "versioning_enabled", False):
            return False

        for path in changed_paths:
            path_str = to_posix(path)
            # Check for _shared/ anywhere in path
            if "/_shared/" in path_str or path_str.startswith("_shared/"):
                return True
            # Also check content/_shared/ pattern
            if "/content/_shared/" in path_str:
                return True

        return False

    def _get_affected_versions(self, changed_paths: set[Path]) -> set[str]:
        """
        Determine which versions are affected by changes.

        Maps changed file paths to version IDs:
        - _versions/<id>/* → version id
        - Regular content (docs/, etc.) → latest version
        - _shared/* → all versions (handled separately)

        Args:
            changed_paths: Set of changed file paths

        Returns:
            Set of affected version IDs
        """
        if not getattr(self.site, "versioning_enabled", False):
            return set()

        version_config = getattr(self.site, "version_config", None)
        if not version_config or not version_config.enabled:
            return set()

        affected: set[str] = set()

        for path in changed_paths:
            path_str = to_posix(path)

            # Check if in _versions/<id>/
            if "/_versions/" in path_str or path_str.startswith("_versions/"):
                # Extract version ID from path
                if "/_versions/" in path_str:
                    parts = path_str.split("/_versions/")[1].split("/")
                else:
                    parts = path_str.split("_versions/")[1].split("/")

                if parts:
                    version_id = parts[0]
                    affected.add(version_id)

            # Check if in versioned section (implies latest version)
            elif not path_str.startswith("_"):
                # Check if path is in a versioned section
                for section in version_config.sections:
                    if f"/{section}/" in path_str or path_str.startswith(f"{section}/"):
                        if version_config.latest_version:
                            affected.add(version_config.latest_version.id)
                        break

        return affected

    def _is_version_config_change(self, changed_paths: set[Path]) -> bool:
        """
        Check if versioning config changed (requires full rebuild).

        Detects changes to versioning.yaml or version-related config files.

        Args:
            changed_paths: Set of changed file paths

        Returns:
            True if version config changed
        """
        for path in changed_paths:
            # Check for versioning.yaml
            if path.name == "versioning.yaml":
                return True

            path_str = to_posix(path)

            # Check for version config in config directories
            if "/config/" in path_str and "version" in path.name.lower():
                return True

        return False

    def _detect_nav_changes(
        self,
        changed_paths: set[Path],
        needs_full_rebuild: bool,
    ) -> set[Path]:
        """
        Detect which changed files have navigation-affecting frontmatter.

        Uses caching with mtime invalidation for efficiency:
        - Cache hit: O(1) lookup
        - Cache miss: Read only first 4KB (frontmatter is at file start)
        """
        if needs_full_rebuild:
            return set()

        nav_changed: set[Path] = set()

        for path in changed_paths:
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue

            if self._has_nav_affecting_frontmatter(path):
                nav_changed.add(path)
                logger.debug("nav_frontmatter_detected", file=str(path))

        return nav_changed

    def _has_nav_affecting_frontmatter(self, path: Path) -> bool:
        """
        Check if file has navigation-affecting frontmatter (cached).

        Optimizations:
        1. LRU cache keyed by (path, mtime) - avoids re-parsing unchanged files
        2. Partial read (4KB) - frontmatter is always at file start

        Args:
            path: Path to markdown file

        Returns:
            True if file has navigation-affecting frontmatter keys
        """
        try:
            stat = path.stat()
            mtime = stat.st_mtime

            # Check cache (keyed by path, validated by mtime)
            cached = self._frontmatter_cache.get(path)
            if cached is not None and cached[0] == mtime:
                return cached[1]

            # Read only first 4KB (frontmatter is at start)
            # Most frontmatter is < 500 bytes, but YAML-heavy files may be larger
            with open(path, encoding="utf-8") as f:
                text = f.read(4096)

            # Extract frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
            if not match:
                result = False
            else:
                try:
                    fm = yaml.safe_load(match.group(1)) or {}
                    if not isinstance(fm, dict):
                        result = False
                    else:
                        from bengal.orchestration.constants import NAV_AFFECTING_KEYS

                        result = any(str(key).lower() in NAV_AFFECTING_KEYS for key in fm)
                except yaml.YAMLError:
                    result = False

            # Update cache with LRU eviction
            if len(self._frontmatter_cache) >= self._frontmatter_cache_max:
                first_key = next(iter(self._frontmatter_cache))
                del self._frontmatter_cache[first_key]
            self._frontmatter_cache[path] = (mtime, result)

            return result

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug("frontmatter_check_failed", file=str(path), error=str(e))
            return False

    def _is_content_only_change(self, path: Path) -> bool:
        """
        Check if a markdown file change is content-only (frontmatter unchanged).

        Content-only changes can potentially use faster rendering paths that
        skip template processing and inject new content into cached page shells.

        Args:
            path: Path to the markdown file

        Returns:
            True if only the markdown body changed (not frontmatter)

        RFC: content-only-hot-reload
        """
        import hashlib

        if path.suffix.lower() != ".md":
            return False

        try:
            mtime = path.stat().st_mtime

            # Read file and split frontmatter/content
            with open(path, encoding="utf-8") as f:
                text = f.read()

            # Extract frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
            if not match:
                return False  # No frontmatter = can't detect

            fm_text = match.group(1)
            content_text = match.group(2)

            # Hash both parts
            fm_hash = hashlib.sha256(fm_text.encode()).hexdigest()[:16]
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()[:16]

            # Check against cache
            cached = self._content_hash_cache.get(path)
            if cached is not None:
                _cached_mtime, cached_fm_hash, cached_content_hash = cached

                # Content-only if frontmatter same but content different
                if cached_fm_hash == fm_hash and cached_content_hash != content_hash:
                    logger.debug(
                        "content_only_change_detected",
                        file=str(path),
                        hint="frontmatter_unchanged",
                    )
                    # Update cache with new hashes
                    self._content_hash_cache[path] = (mtime, fm_hash, content_hash)
                    return True

            # Update cache with LRU eviction
            if len(self._content_hash_cache) >= self._content_hash_cache_max:
                first_key = next(iter(self._content_hash_cache))
                del self._content_hash_cache[first_key]
            self._content_hash_cache[path] = (mtime, fm_hash, content_hash)

            return False

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug("content_hash_check_failed", file=str(path), error=str(e))
            return False

    def _get_template_dirs(self) -> list[Path]:
        """
        Get template directories (cached).

        Caches the list of existing template directories to avoid
        repeated exists() calls on every file change check.

        Returns:
            List of existing template directories
        """
        if self._template_dirs is not None:
            return self._template_dirs

        import bengal

        assert bengal.__file__ is not None, "bengal module has no __file__"
        bengal_dir = Path(bengal.__file__).parent
        root_path = getattr(self.site, "root_path", None)

        if not root_path:
            self._template_dirs = []
            return self._template_dirs

        dirs = [
            root_path / "templates",
            root_path / "themes",
        ]

        theme = getattr(self.site, "theme", None)
        if theme:
            bundled = bengal_dir / "themes" / theme / "templates"
            dirs.append(bundled)

        # Filter to existing directories (cached)
        self._template_dirs = [d for d in dirs if d.exists()]
        return self._template_dirs

    def _is_template_change(self, changed_paths: set[Path]) -> bool:
        """
        Check if template changes require full rebuild.

        Instead of full rebuild for any template change, uses dependency tracking
        to determine if incremental rebuild is possible.

        Returns True only if:
        1. Changed templates have dependents AND
        2. Incremental template update isn't possible

        Optimizations:
        1. Filter to .html files first (skip non-templates early)
        2. Use cached template directories (avoids exists() calls)
        3. Check dependency graph to skip orphan templates
        """
        template_dirs = self._get_template_dirs()
        if not template_dirs:
            return False

        # Filter to .html files first (early exit optimization)
        html_paths = [p for p in changed_paths if p.suffix.lower() == ".html"]
        if not html_paths:
            return False

        # Get cache for dependency tracking
        cache = getattr(self.site, "_cache", None)
        if cache is None:
            # Try to get cache from site's cache manager or incremental orchestrator
            try:
                from bengal.cache import BuildCache

                cache_path = self.site.paths.build_cache
                if cache_path.exists():
                    cache = BuildCache.load(cache_path)
            except Exception:
                cache = None

        for path in html_paths:
            if not self._is_in_template_dir(path, template_dirs):
                continue

            # Check if template has any dependents
            affected: set[str] = set()
            if cache is not None:
                with contextlib.suppress(Exception):
                    affected = cache.get_affected_pages(path)

            if not affected:
                # Template has no dependents - skip entirely
                logger.debug(
                    "template_change_ignored",
                    template=str(path),
                    reason="no_dependents",
                )
                continue

            # Has dependents - check if we can do incremental update
            if self._can_use_incremental_template_update(path, cache):
                logger.debug(
                    "template_change_incremental",
                    template=str(path),
                    affected_pages=len(affected),
                )
                continue  # Will be handled by incremental build

            # Must do full rebuild
            logger.debug(
                "template_change_full_rebuild",
                template=str(path),
                affected_pages=len(affected),
                reason="incremental_not_possible",
            )
            return True

        return False

    def _is_in_template_dir(self, path: Path, template_dirs: list[Path]) -> bool:
        """Check if path is within any template directory."""
        try:
            resolved_path = path.resolve()
        except (OSError, ValueError):
            resolved_path = path

        for template_dir in template_dirs:
            try:
                resolved_dir = template_dir.resolve()
                resolved_path.relative_to(resolved_dir)
                return True
            except (ValueError, OSError):
                continue
        return False

    def _can_use_incremental_template_update(self, template_path: Path, cache: Any) -> bool:
        """
        Check if incremental template update is possible.

        Incremental update is possible when:
        1. Block-level detection is available (Kida engine)
        2. Only site-scoped blocks changed (nav, footer, etc.)
        3. All affected pages can be re-rendered individually

        Args:
            template_path: Path to the changed template
            cache: BuildCache instance or None

        Returns:
            True if incremental update is possible
        """
        try:
            from bengal.protocols import EngineCapability
            from bengal.rendering.engines import create_engine

            # Check if template engine supports block-level detection via capability
            engine = create_engine(self.site)
            if not engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION):
                return False

            # Check if we have block cache support
            from bengal.orchestration.incremental.template_detector import (
                TemplateChangeDetector,
            )

            detector = TemplateChangeDetector(self.site, cache, block_cache=None)
            return detector._can_use_block_detection()
        except Exception:
            return False

    def _should_regenerate_autodoc(self, changed_paths: set[Path]) -> bool:
        """Check if autodoc regeneration is needed."""
        if not isinstance(self.site, SiteLike) or not self.site.config:
            return False

        # ConfigSection now supports dict methods, use directly
        autodoc_config = self.site.config.get("autodoc", {})

        # Check Python source directories
        python_config = autodoc_config.get("python", {})
        if python_config.get("enabled", False):
            source_dirs = python_config.get("source_dirs", [])
            for path in changed_paths:
                for source_dir in source_dirs:
                    source_path = self.site.root_path / source_dir
                    try:
                        path.relative_to(source_path)
                        if path.suffix == ".py":
                            return True
                    except ValueError:
                        continue

        # Check OpenAPI spec
        openapi_config = autodoc_config.get("openapi", {})
        if openapi_config.get("enabled", False):
            spec_file = openapi_config.get("spec_file")
            if spec_file:
                spec_path = self.site.root_path / spec_file
                for path in changed_paths:
                    if path == spec_path or path.resolve() == spec_path.resolve():
                        return True

        return False

    def _display_stats(self, result: BuildResult, incremental: bool) -> None:
        """Display build statistics using MinimalStats adapter."""
        stats = MinimalStats.from_build_result(result, incremental=incremental)
        display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

    def _handle_reload(
        self,
        changed_files: list[str],
        changed_outputs: tuple[tuple[str, str, str], ...],
        reload_hint: str | None = None,
    ) -> None:
        """Handle reload decision and notification.

        Uses typed outputs from the build for accurate reload decisions.
        reload_hint from BuildStats is advisory (css-only, full, none).
        1. Primary: Typed outputs from build (CSS-only vs full reload)
        2. Fallback: Path-based decision (when typed outputs unavailable)

        The typed output approach is more accurate than source-file inspection
        because it knows exactly what was written, not just what changed.

        Args:
            changed_files: List of source file paths that changed (for logging)
            changed_outputs: Serialized OutputRecords as (path, type, phase) tuples
        """
        decision = None
        decision_source = "none"

        # Primary path: Use typed outputs from build
        if changed_outputs:
            from bengal.core.output import OutputRecord, OutputType

            records = []
            for path_str, type_val, phase in changed_outputs:
                try:
                    output_type = OutputType(type_val)
                    if phase in ("render", "asset", "postprocess"):
                        records.append(OutputRecord(Path(path_str), output_type, phase))  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    # Invalid type value, skip
                    logger.debug("invalid_output_type", path=path_str, type_val=type_val)

            if records:
                decision = controller.decide_from_outputs(
                    records, reload_hint=reload_hint
                )
                decision_source = "typed-outputs"
                logger.debug(
                    "reload_from_typed_outputs",
                    output_count=len(records),
                    css_count=sum(1 for r in records if r.output_type == OutputType.CSS),
                )
            else:
                # Fallback: Path-based decision (when type reconstruction fails)
                paths = [path for path, _type, _phase in changed_outputs]
                decision = controller.decide_from_changed_paths(paths)
                decision_source = "fallback-paths"
                logger.warning(
                    "reload_decision_fallback",
                    reason="typed_output_reconstruction_failed",
                    output_count=len(changed_outputs),
                )

        # Fallback: If sources changed but no typed outputs were recorded, trigger full reload
        # This handles cases where the output collector didn't receive records (e.g., subprocess
        # serialization issues, early exit paths, or collector not being passed through).
        if decision is None:
            if changed_files:
                # Sources changed, but no typed outputs - fall back to full reload
                decision = ReloadDecision(
                    action="reload", reason="source-change-no-outputs", changed_paths=[]
                )
                decision_source = "fallback-source-change"
                logger.warning(
                    "reload_fallback_no_outputs",
                    changed_files_count=len(changed_files),
                    changed_files=changed_files[:5],
                )
            else:
                # No sources changed and no outputs - suppress reload
                decision = ReloadDecision(action="none", reason="no-changes", changed_paths=[])
                decision_source = "no-changes"
                logger.debug("reload_suppressed_no_changes")

        # RFC: Output Cache Architecture - Use content-hash detection to filter aggregate-only changes
        # Only reload if there are meaningful content/asset changes (not just sitemap/feeds)
        if (
            decision.action == "reload"
            and controller._use_content_hashes
            and hasattr(controller, "_baseline_content_hashes")
            and controller._baseline_content_hashes
        ):
            enhanced = controller.decide_with_content_hashes(self.site.output_dir)
            if enhanced.meaningful_change_count == 0:
                # All changes are aggregate-only (sitemap, feeds, search index)
                decision = ReloadDecision(
                    action="none",
                    reason="aggregate-only",
                    changed_paths=[],
                )
                decision_source = "content-hash-filtered"
                logger.info(
                    "reload_filtered_aggregate_only",
                    total_changes=len(enhanced.aggregate_changes),
                )
            else:
                # Update with accurate change count
                decision_source = f"{decision_source}+content-hash"
                logger.debug(
                    "content_hash_breakdown",
                    content_changes=len(enhanced.content_changes),
                    aggregate_changes=len(enhanced.aggregate_changes),
                    asset_changes=len(enhanced.asset_changes),
                )

        # Log decision source for observability
        logger.debug(
            "reload_decision_source",
            source=decision_source,
            action=decision.action,
            reason=decision.reason,
        )

        # Send reload notification
        if decision.action == "none":
            logger.info("reload_suppressed", reason=decision.reason)
        else:
            from bengal.server.live_reload import send_reload_payload

            logger.info(
                "reload_decision",
                action=decision.action,
                reason=decision.reason,
                source=decision_source,
            )
            send_reload_payload(decision.action, decision.reason, decision.changed_paths)

    def _set_build_in_progress(self, building: bool) -> None:
        """Signal build state to shared registry (handler and ASGI app read from it)."""
        try:
            build_state.set_build_in_progress(building)
        except Exception as e:
            logger.debug("build_state_signal_failed", error=str(e))

    def _clear_html_cache(self) -> None:
        """Clear HTML injection cache after rebuild."""
        try:
            from bengal.server.live_reload import LiveReloadMixin

            with LiveReloadMixin._html_cache_lock:
                cache_size = len(LiveReloadMixin._html_cache)
                LiveReloadMixin._html_cache.clear()

            if cache_size > 0:
                logger.debug("html_cache_cleared", entries=cache_size)
        except Exception as e:
            logger.debug("html_cache_clear_failed", error=str(e))

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)
