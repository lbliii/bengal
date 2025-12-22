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

import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from bengal.orchestration.stats import display_build_stats, show_building_indicator, show_error
from bengal.output import CLIOutput
from bengal.server.build_executor import BuildExecutor, BuildRequest, BuildResult
from bengal.server.build_hooks import run_post_build_hooks, run_pre_build_hooks
from bengal.server.reload_controller import ReloadDecision, controller
from bengal.utils.logger import get_logger
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
        - Navigation frontmatter detection
        - Template change detection
        - Autodoc source change detection
        - Live reload notification

    Example:
        >>> trigger = BuildTrigger(site, host="localhost", port=5173)
        >>> trigger.trigger_build(changed_paths, event_types)
    """

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
            version_scope: RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
                Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
        """
        self.site = site
        self.host = host
        self.port = port
        self.version_scope = version_scope
        self._executor = executor or BuildExecutor(max_workers=1)
        self._building = False
        self._build_lock = threading.Lock()

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

        Args:
            changed_paths: Set of changed file paths
            event_types: Set of event types (created, modified, deleted, moved)
        """
        with self._build_lock:
            if self._building:
                logger.debug("build_skipped", reason="build_already_in_progress")
                return
            self._building = True

        try:
            self._execute_build(changed_paths, event_types)
        finally:
            with self._build_lock:
                self._building = False

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
            timestamp = datetime.now().strftime("%H:%M:%S")
            cli = CLIOutput()
            cli.file_change_notice(file_name=file_name, timestamp=timestamp)
            show_building_indicator("Rebuilding")

            # Run pre-build hooks
            config = getattr(self.site, "config", {}) or {}
            if not run_pre_build_hooks(config, self.site.root_path):
                show_error("Pre-build hook failed - skipping build", show_art=False)
                cli.request_log_header()
                logger.error("rebuild_skipped", reason="pre_build_hook_failed")
                return

            # Create build request
            use_incremental = not needs_full_rebuild
            # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
            request = BuildRequest(
                site_root=str(self.site.root_path),
                changed_paths=tuple(changed_files),
                incremental=use_incremental,
                profile="WRITER",
                nav_changed_paths=tuple(str(p) for p in nav_changed_files),
                structural_changed=structural_changed,
                parallel=True,
                version_scope=self.version_scope,
            )

            # Execute build in subprocess
            result = self._executor.submit(request, timeout=300.0)
            build_duration = result.build_time_ms / 1000

            if not result.success:
                show_error(f"Build failed: {result.error_message}", show_art=False)
                cli.request_log_header()
                logger.error(
                    "rebuild_failed",
                    duration_seconds=round(build_duration, 2),
                    error=result.error_message,
                )
                return

            # Display build stats
            self._display_stats(result, use_incremental)

            # Run post-build hooks
            if not run_post_build_hooks(config, self.site.root_path):
                logger.warning("post_build_hook_failed", action="continuing")

            # Show server URL
            cli.server_url_inline(host=self.host, port=self.port)
            cli.request_log_header()

            logger.info(
                "rebuild_complete",
                duration_seconds=round(build_duration, 2),
                pages_built=result.pages_built,
                incremental=use_incremental,
            )

            # Handle reload decision
            self._handle_reload(changed_files, result.changed_outputs)

            # Clear HTML cache
            self._clear_html_cache()

        except Exception as e:
            logger.error(
                "rebuild_error",
                error=str(e),
                error_type=type(e).__name__,
            )
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
            path_str = str(path).replace("\\", "/")
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
            path_str = str(path).replace("\\", "/")
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
            path_str = str(path).replace("\\", "/")

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

            path_str = str(path).replace("\\", "/")

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
        """
        if needs_full_rebuild:
            return set()

        from bengal.orchestration.constants import NAV_AFFECTING_KEYS

        nav_changed: set[Path] = set()

        for path in changed_paths:
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue

            try:
                text = path.read_text(encoding="utf-8")
                match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
                if not match:
                    continue

                fm = yaml.safe_load(match.group(1)) or {}
                if not isinstance(fm, dict):
                    continue

                if any(str(key).lower() in NAV_AFFECTING_KEYS for key in fm):
                    nav_changed.add(path)
                    logger.debug("nav_frontmatter_detected", file=str(path))
            except Exception as e:
                logger.debug("frontmatter_parse_failed", file=str(path), error=str(e))

        return nav_changed

    def _is_template_change(self, changed_paths: set[Path]) -> bool:
        """Check if any changed file is a template."""
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        root_path = getattr(self.site, "root_path", None)
        if not root_path:
            return False

        template_dirs = [
            root_path / "templates",
            root_path / "themes",
        ]

        theme = getattr(self.site, "theme", None)
        if theme:
            bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
            if bundled_theme_dir.exists():
                template_dirs.append(bundled_theme_dir)

        for path in changed_paths:
            if path.suffix.lower() != ".html":
                continue

            for template_dir in template_dirs:
                if not template_dir.exists():
                    continue
                try:
                    path.relative_to(template_dir)
                    return True
                except ValueError:
                    continue

        return False

    def _should_regenerate_autodoc(self, changed_paths: set[Path]) -> bool:
        """Check if autodoc regeneration is needed."""
        if not hasattr(self.site, "config") or not self.site.config:
            return False

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
    ) -> None:
        """Handle reload decision and notification.

        Args:
            changed_files: List of source file paths that changed
            changed_outputs: Serialized OutputRecords as (path, type, phase) tuples
        """
        decision = None

        # Source-gated reload decision
        if changed_files:
            try:
                lower = [p.lower() for p in changed_files]
                src_only = [p for p in lower if "/public/" not in p and "\\public\\" not in p]

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
                    # Use typed outputs to get CSS paths
                    css_paths = (
                        [path for path, type_val, _phase in changed_outputs if type_val == "css"]
                        if changed_outputs
                        else []
                    )
                    decision = ReloadDecision(
                        action="reload-css", reason="css-only", changed_paths=css_paths
                    )
                else:
                    decision = ReloadDecision(
                        action="reload", reason="source-change", changed_paths=[]
                    )
            except Exception as e:
                logger.debug("reload_decision_failed", error=str(e))

        # Use typed builder outputs if available - preferred path (no snapshot diffing)
        if decision is None and changed_outputs:
            # Reconstruct OutputRecord objects for decide_from_outputs
            from pathlib import Path

            from bengal.core.output import OutputRecord, OutputType

            records = []
            for path_str, type_val, phase in changed_outputs:
                try:
                    output_type = OutputType(type_val)
                    # phase needs to be a valid literal
                    if phase in ("render", "asset", "postprocess"):
                        records.append(OutputRecord(Path(path_str), output_type, phase))  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    # Invalid type value, skip
                    pass

            if records:
                decision = controller.decide_from_outputs(records)
            else:
                # Fall back to path-based decision
                paths = [path for path, _type, _phase in changed_outputs]
                decision = controller.decide_from_changed_paths(paths)

        # Default: suppress reload
        if decision is None:
            decision = ReloadDecision(action="none", reason="no-source-change", changed_paths=[])

        # Send reload notification
        if decision.action == "none":
            logger.info("reload_suppressed", reason=decision.reason)
        else:
            from bengal.server.live_reload import send_reload_payload

            logger.info(
                "reload_decision",
                action=decision.action,
                reason=decision.reason,
            )
            send_reload_payload(decision.action, decision.reason, decision.changed_paths)

    def _set_build_in_progress(self, building: bool) -> None:
        """Signal build state to request handler."""
        try:
            from bengal.server.request_handler import BengalRequestHandler

            BengalRequestHandler.set_build_in_progress(building)
        except Exception as e:
            logger.debug("build_state_signal_failed", error=str(e))

    def _clear_html_cache(self) -> None:
        """Clear HTML and Site caches after rebuild."""
        try:
            from bengal.server.request_handler import BengalRequestHandler

            # Clear HTML injection cache
            with BengalRequestHandler._html_cache_lock:
                cache_size = len(BengalRequestHandler._html_cache)
                BengalRequestHandler._html_cache.clear()

            # Clear static Site cache (component preview)
            BengalRequestHandler.clear_cached_site()

            if cache_size > 0:
                logger.debug("html_cache_cleared", entries=cache_size)
        except Exception as e:
            logger.debug("html_cache_clear_failed", error=str(e))

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)
