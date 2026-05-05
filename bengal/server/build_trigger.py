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
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bengal.errors import ErrorCode, create_dev_error, get_dev_server_state
from bengal.orchestration.stats import (
    ReloadHint,
    display_build_stats,
    show_building_indicator,
    show_error,
)
from bengal.output import get_cli_output
from bengal.protocols import SiteLike
from bengal.server.build_executor import BuildExecutor, BuildResult
from bengal.server.build_hooks import run_post_build_hooks, run_pre_build_hooks
from bengal.server.build_state import build_state
from bengal.server.live_reload import LiveReloadNotifier
from bengal.server.reload_controller import (
    ReloadController,
    ReloadDecision,
)
from bengal.server.reload_controller import (
    controller as default_reload_controller,
)
from bengal.server.reload_types import BuildReloadInfo
from bengal.server.utils import get_timestamp
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix
from bengal.utils.stats_minimal import MinimalStats

if TYPE_CHECKING:
    from bengal.server.buffer_manager import BufferManager
    from bengal.server.reload_protocols import ReloadNotifier

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FrontmatterCacheEntry:
    """Cache entry for frontmatter nav-key detection (mtime, has_nav_keys)."""

    mtime: float
    has_nav_keys: bool


@dataclass(frozen=True, slots=True)
class ContentHashCacheEntry:
    """Cache entry for content-only change detection (mtime, fm_hash, content_hash)."""

    mtime: float
    frontmatter_hash: str
    content_hash: str


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

    # Cache size limits (instance-level caches in __init__)
    _frontmatter_cache_max = 500
    _content_hash_cache_max = 500

    def __init__(
        self,
        site: SiteLike,
        host: str = "localhost",
        port: int = 5173,
        executor: BuildExecutor | None = None,
        controller: ReloadController | None = None,
        notifier: ReloadNotifier | None = None,
        version_scope: str | None = None,
        buffer_manager: BufferManager | None = None,
    ) -> None:
        """
        Initialize build trigger.

        Args:
            site: Site instance
            host: Server host for URL display
            port: Server port for URL display
            executor: BuildExecutor instance (created if not provided)
            controller: ReloadController for reload decisions (uses default if None)
            notifier: ReloadNotifier for client notification (uses live reload if None)
            version_scope: Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
            buffer_manager: Optional BufferManager for double-buffered output.
                When set, full builds write to staging and swap on completion.
        """
        self.site = site
        self.host = host
        self.port = port
        self.version_scope = version_scope
        self._buffer_manager = buffer_manager
        self._executor = executor or BuildExecutor(max_workers=1)
        self._reload_controller = controller or default_reload_controller
        self._reload_notifier = notifier or LiveReloadNotifier()
        self._building = False
        self._build_lock = threading.Lock()
        # Queue for changes that arrive during a build (prevents lost changes)
        self._pending_changes: set[Path] = set()
        self._pending_event_types: set[str] = set()
        # Reset template dirs cache for this instance (theme may differ)
        self._template_dirs: list[Path] | None = None
        # Instance-level caches (3.14t: avoid ClassVar mutable state)
        self._frontmatter_cache: dict[Path, FrontmatterCacheEntry] = {}
        self._content_hash_cache: dict[Path, ContentHashCacheEntry] = {}
        # Track last successful build for error context
        self._last_successful_build: datetime | None = None
        # Track whether the previous build surfaced template errors so we
        # know when to push a `build_ok` message that dismisses the overlay.
        self._had_template_errors_last_build: bool = False

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
        # Signal build in progress to the request handler via build_state.
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
            cli = get_cli_output()
            cli.file_change_notice(file_name=file_name, timestamp=timestamp)
            show_building_indicator("Rebuilding")

            # RFC: Output Cache Architecture - Capture content hash baseline BEFORE build
            # This enables accurate change detection vs regeneration noise
            if self._reload_controller._use_content_hashes:
                self._reload_controller.capture_content_hash_baseline(self.site.output_dir)

            # Run pre-build hooks
            config = self.site.config or {}
            # run_pre_build_hooks expects a dict, use .raw for serialization
            raw = getattr(config, "raw", config)
            config_dict: dict[str, Any] = raw if isinstance(raw, dict) else {}
            if not run_pre_build_hooks(config_dict, self.site.root_path):
                show_error("Pre-build hook failed - skipping build", show_art=False)
                cli.request_log_header()
                logger.error("rebuild_skipped", reason="pre_build_hook_failed")
                return

            # Reactive path: content-only edit skips full build
            if not needs_full_rebuild and self._can_use_reactive_path(changed_paths, event_types):
                path = next(iter(changed_paths))
                from bengal.core.output import OutputType
                from bengal.server.reactive import ReactiveContentHandler
                from bengal.server.reload_types import SerializedOutputRecord

                handler = ReactiveContentHandler(self.site, self.site.output_dir)
                try:
                    result = handler.handle_content_change(path)
                    if result is not None:
                        output_path = result.output_path
                        # Use path relative to output_dir (matches full build)
                        rel_path = output_path
                        if output_path.is_absolute() and self.site.output_dir:
                            with suppress(ValueError):
                                rel_path = output_path.relative_to(self.site.output_dir)
                        changed_outputs = (
                            SerializedOutputRecord(
                                path=str(rel_path),
                                type_value=OutputType.HTML.value,
                                phase="render",
                            ),
                        )

                        # Fragment path: extract #main-content from in-memory
                        # rendered HTML (zero-disk — no read-back from disk)
                        dev_config = config_dict.get("dev", {}) or {}
                        content_selector = dev_config.get("content_selector", "#main-content")
                        from bengal.server.live_reload.fragment import extract_main_content
                        from bengal.server.live_reload.notification import send_fragment_payload
                        from bengal.utils.paths.url_strategy import URLStrategy

                        fragment = extract_main_content(result.rendered_html, content_selector)
                        if fragment:
                            permalink = URLStrategy.url_from_output_path(output_path, self.site)
                            send_fragment_payload(content_selector, fragment, permalink)
                        else:
                            self._handle_reload(
                                BuildReloadInfo(
                                    changed_files=tuple(changed_files),
                                    changed_outputs=changed_outputs,
                                    reload_hint=None,
                                )
                            )
                        self._clear_html_cache()
                        return
                except Exception as e:
                    logger.warning(
                        "reactive_path_failed",
                        error=str(e),
                        fallback="full_build",
                    )

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

            # Double-buffer: redirect output to staging directory so the ASGI
            # app continues serving from the active buffer during the build.
            original_output_dir = self.site.output_dir
            swapped = False
            if self._buffer_manager is not None:
                staging = self._buffer_manager.prepare_staging()
                self.site.output_dir = staging
                logger.debug(
                    "build_to_staging",
                    staging=str(staging),
                    active=str(self._buffer_manager.active_dir),
                )

            # Execute warm build directly on the existing site
            build_start = time.time()
            try:
                stats = self.site.build(options=build_opts)
                build_duration = time.time() - build_start

                # Double-buffer: swap staging to active now that the build
                # wrote a complete, consistent snapshot.
                if self._buffer_manager is not None:
                    self._buffer_manager.swap()
                    swapped = True
                    self.site.output_dir = self._buffer_manager.active_dir
                    logger.debug(
                        "buffer_swapped",
                        active=str(self._buffer_manager.active_dir),
                        generation=self._buffer_manager.generation,
                    )

                # Build succeeded - convert stats to result-like object for display
                class WarmBuildResult:
                    def __init__(self, stats: Any, build_time: float) -> None:
                        from bengal.server.reload_types import (
                            SerializedOutputRecord,
                        )

                        self.success = True
                        self.pages_built = stats.total_pages
                        self.build_time_ms = build_time * 1000
                        self.error_message = None
                        self.changed_outputs = (
                            tuple(
                                SerializedOutputRecord(
                                    path=str(r.path),
                                    type_value=r.output_type.value,
                                    phase=r.phase,
                                )
                                for r in stats.changed_outputs
                            )
                            if hasattr(stats, "changed_outputs")
                            else ()
                        )
                        self.reload_hint = stats.reload_hint
                        self._stats = stats

                result = WarmBuildResult(stats, build_duration)

                # Seed content hash cache so first edit can use reactive path
                self.seed_content_hash_cache(list(self.site.pages))

            except Exception as e:
                # Double-buffer: resync output_dir with the active buffer.
                # If swap already ran, active_dir points to the new buffer;
                # otherwise fall back to original_output_dir (pre-build).
                if self._buffer_manager is not None:
                    if swapped:
                        self.site.output_dir = self._buffer_manager.active_dir
                    else:
                        self.site.output_dir = original_output_dir

                # Build crashed - log error and reinitialize site for next build
                build_duration = time.time() - build_start
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

            # Browser-overlay control: if any pages failed to render, push a
            # `build_error` envelope so the SSE client renders the overlay in
            # place. If a previous build had errors and this one is clean,
            # push `build_ok` (which the client treats as both dismiss AND
            # cache-bust reload). Skip the regular reload path in those
            # cases — the overlay messages are the reload signal.
            template_errors = list(getattr(stats, "template_errors", None) or [])
            overlay_handled = self._handle_overlay_messages(template_errors, build_duration)

            if overlay_handled:
                self._clear_html_cache()
                return

            # Handle reload decision
            self._handle_reload(
                BuildReloadInfo(
                    changed_files=tuple(changed_files),
                    changed_outputs=result.changed_outputs,
                    reload_hint=result.reload_hint,
                )
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

    def _can_use_reactive_path(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        """Check if content-only reactive path can be used (skips full build).

        Content-only = frontmatter unchanged, body changed. Safe for leaf AND
        section pages. Cascade, nav, and structure keys are in frontmatter;
        if unchanged, no downstream impact.
        """
        if len(changed_paths) != 1 or event_types != {"modified"}:
            return False
        path = next(iter(changed_paths))
        if path.suffix.lower() not in {".md", ".markdown"}:
            return False
        return self._is_content_only_change(path)

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
            resolved = path.resolve()

            # Check cache (keyed by resolved path for watcher/discovery consistency)
            cached = self._frontmatter_cache.get(resolved)
            if cached is not None and cached.mtime == mtime:
                return cached.has_nav_keys

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

            # Update cache with LRU eviction (resolved path for watcher consistency)
            if len(self._frontmatter_cache) >= self._frontmatter_cache_max:
                first_key = next(iter(self._frontmatter_cache))
                del self._frontmatter_cache[first_key]
            self._frontmatter_cache[resolved] = FrontmatterCacheEntry(
                mtime=mtime, has_nav_keys=result
            )

            return result

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug("frontmatter_check_failed", file=str(path), error=str(e))
            return False

    def _compute_content_hashes(self, path: Path) -> ContentHashCacheEntry | None:
        """
        Read a markdown file and compute frontmatter/content hashes.

        Returns None if the file has no frontmatter or cannot be read.
        Used by _is_content_only_change and seed_content_hash_cache.
        """
        import hashlib

        if path.suffix.lower() not in {".md", ".markdown"}:
            return None

        try:
            mtime = path.stat().st_mtime
            with open(path, encoding="utf-8") as f:
                text = f.read()

            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
            if not match:
                return None

            fm_hash = hashlib.sha256(match.group(1).encode()).hexdigest()[:16]
            content_hash = hashlib.sha256(match.group(2).encode()).hexdigest()[:16]
            return ContentHashCacheEntry(
                mtime=mtime,
                frontmatter_hash=fm_hash,
                content_hash=content_hash,
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug("content_hash_check_failed", file=str(path), error=str(e))
            return None

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
        entry = self._compute_content_hashes(path)
        if entry is None:
            return False

        resolved = path.resolve()
        cached = self._content_hash_cache.get(resolved)
        if (
            cached is not None
            and cached.frontmatter_hash == entry.frontmatter_hash
            and cached.content_hash != entry.content_hash
        ):
            logger.debug(
                "content_only_change_detected",
                file=str(path),
                hint="frontmatter_unchanged",
            )
            self._content_hash_cache[resolved] = entry
            return True

        # Update cache with LRU eviction (resolved path for watcher consistency)
        if len(self._content_hash_cache) >= self._content_hash_cache_max:
            first_key = next(iter(self._content_hash_cache))
            del self._content_hash_cache[first_key]
        self._content_hash_cache[resolved] = entry
        return False

    def seed_content_hash_cache(self, pages: list[Any]) -> None:
        """
        Populate content hash cache for content pages after a successful build.

        Enables the first content-only edit after startup to use the reactive path
        instead of falling back to full build (RFC: content-only-hot-reload).

        Keys are resolved to absolute paths to match the watcher's path format
        (watchfiles yields absolute paths). Without this, the first edit after
        startup misses the cache and falls through to a full warm build.
        """
        root = self.site.root_path
        for page in pages:
            src = getattr(page, "source_path", None)
            if src is None:
                continue
            path = Path(src) if not isinstance(src, Path) else src
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue
            try:
                if path.is_absolute():
                    abs_path = path
                elif root is not None:
                    abs_path = (root / path).resolve()
                else:
                    abs_path = path.resolve()
            except OSError, ValueError:
                continue
            entry = self._compute_content_hashes(abs_path)
            if entry is None:
                continue
            if len(self._content_hash_cache) >= self._content_hash_cache_max:
                first_key = next(iter(self._content_hash_cache))
                del self._content_hash_cache[first_key]
            self._content_hash_cache[abs_path] = entry

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
        root_path = self.site.root_path

        if not root_path:
            self._template_dirs = []
            return self._template_dirs

        dirs = [
            root_path / "templates",
            root_path / "themes",
        ]

        theme = self.site.theme
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

                cache_path = self.site.config_service.paths.build_cache
                if cache_path.exists():
                    cache = BuildCache.load(cache_path)
                    cache.site_root = self.site.root_path
            except Exception:
                cache = None

        for path in html_paths:
            if not self._is_in_template_dir(path, template_dirs):
                continue

            affected, dependency_data_known = self._get_template_dependents(
                path,
                cache,
                template_dirs,
            )

            if not affected:
                if dependency_data_known:
                    # Template has no dependents - skip entirely
                    logger.debug(
                        "template_change_ignored",
                        template=str(path),
                        reason="no_dependents",
                    )
                    continue

                logger.debug(
                    "template_change_full_rebuild",
                    template=str(path),
                    affected_pages=0,
                    reason="dependency_data_missing",
                )
                return True

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

    def _template_name_for_path(self, path: Path, template_dirs: list[Path]) -> str:
        """Return the template name used by BuildCache dependency indexes."""
        for template_dir in template_dirs:
            try:
                return to_posix(path.resolve().relative_to(template_dir.resolve()))
            except OSError, ValueError:
                continue
        return path.name

    def _get_template_dependents(
        self,
        path: Path,
        cache: Any,
        template_dirs: list[Path],
    ) -> tuple[set[str], bool]:
        """Return pages affected by a template and whether dependency data was known."""
        if cache is None:
            return set(), False

        template_name = self._template_name_for_path(path, template_dirs)
        template_dependencies = getattr(cache, "template_dependencies", None)
        if isinstance(template_dependencies, dict) and template_dependencies:
            try:
                return set(cache.get_pages_for_template(template_name)), True
            except Exception as exc:
                logger.debug(
                    "template_dependency_lookup_failed",
                    template=template_name,
                    error=str(exc),
                )

        try:
            affected = set(cache.get_affected_pages(path))
        except Exception as exc:
            logger.debug(
                "template_reverse_dependency_lookup_failed",
                template=str(path),
                error=str(exc),
            )
            return set(), False

        return affected, bool(affected)

    def _is_in_template_dir(self, path: Path, template_dirs: list[Path]) -> bool:
        """Check if path is within any template directory."""
        try:
            resolved_path = path.resolve()
        except OSError, ValueError:
            resolved_path = path

        for template_dir in template_dirs:
            try:
                resolved_dir = template_dir.resolve()
                resolved_path.relative_to(resolved_dir)
                return True
            except ValueError, OSError:
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

            template_dependencies = getattr(cache, "template_dependencies", None)
            return isinstance(template_dependencies, dict) and bool(template_dependencies)
        except Exception as exc:
            logger.debug(
                "template_incremental_check_failed",
                template=str(template_path),
                error=str(exc),
            )
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

    def _handle_overlay_messages(self, template_errors: list[Any], build_duration: float) -> bool:
        """Push browser-overlay control messages over SSE.

        Returns ``True`` when the overlay messages take ownership of the
        client-notification slot for this build, signalling the caller to
        skip the regular reload path. Returns ``False`` when the build is
        clean and was preceded by another clean build (no overlay state).
        """
        from bengal.errors.overlay import build_error_payload, build_ok_payload
        from bengal.server.live_reload.notification import (
            send_build_error_payload,
            send_build_ok_payload,
        )

        if template_errors:
            try:
                payload = build_error_payload(template_errors)
                send_build_error_payload(payload)
            except Exception as exc:
                logger.warning(
                    "build_error_overlay_send_failed",
                    error_code=ErrorCode.S003.name,
                    error=str(exc),
                )
                # Fall through to normal reload — the per-page overlay
                # HTML written to disk still gives the developer a useful
                # page even without the live overlay.
                return False
            self._had_template_errors_last_build = True
            return True

        if self._had_template_errors_last_build:
            try:
                payload = build_ok_payload(build_ms=int(build_duration * 1000))
                send_build_ok_payload(payload)
            except Exception as exc:
                logger.warning(
                    "build_ok_overlay_send_failed",
                    error_code=ErrorCode.S003.name,
                    error=str(exc),
                )
                # Fall through to normal reload so the user still gets a
                # refresh; the overlay JS treats a plain `reload` as a
                # dismiss as well.
                self._had_template_errors_last_build = False
                return False
            self._had_template_errors_last_build = False
            return True

        return False

    def _handle_reload(self, info: BuildReloadInfo) -> None:
        """Handle reload decision and notification.

        Decision flow:
        1. reload_hint=NONE + typed outputs → suppress (build knows no reload needed)
        2. Typed outputs available → use ReloadController for CSS vs full
        3. No outputs but changed_files → full reload (fallback when output collector empty)
        4. Neither → suppress

        Args:
            info: BuildReloadInfo from build (changed_files, changed_outputs, reload_hint)
        """
        changed_files = list(info.changed_files)
        changed_outputs = info.changed_outputs
        reload_hint = info.reload_hint

        # Trust reload_hint=NONE only when we have typed outputs (build can confirm)
        if reload_hint is ReloadHint.NONE and changed_outputs:
            logger.info("reload_suppressed", reason="reload-hint-none")
            return

        decision: ReloadDecision | None = None
        decision_source = "none"

        # Primary: typed outputs from build
        if changed_outputs:
            from bengal.core.output import OutputType

            records = []
            for rec in changed_outputs:
                try:
                    if rec.phase in ("render", "asset", "postprocess"):
                        records.append(rec.to_output_record())
                except ValueError, TypeError:
                    logger.debug("invalid_output_type", path=rec.path, type_val=rec.type_value)

            if records:
                decision = self._reload_controller.decide_from_outputs(
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
                paths = [rec.path for rec in changed_outputs]
                decision = self._reload_controller.decide_from_changed_paths(paths)
                decision_source = "fallback-paths"
                logger.debug(
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
                    action="reload", reason="source-change-no-outputs", changed_paths=()
                )
                decision_source = "fallback-source-change"
                logger.debug(
                    "reload_fallback_no_outputs",
                    changed_files_count=len(changed_files),
                    changed_files=changed_files[:5],
                )
            else:
                # No sources changed and no outputs - suppress reload
                decision = ReloadDecision(action="none", reason="no-changes", changed_paths=())
                decision_source = "no-changes"
                logger.debug("reload_suppressed_no_changes")

        # Content-hash filter: aggregate-only (sitemap, feeds) → no reload.
        # Skip when: (1) fallback-source-change, or (2) user edited source files.
        # If changed_files is non-empty, user triggered a build—don't suppress reload.
        if (
            decision.action == "reload"
            and decision_source != "fallback-source-change"
            and not changed_files
            and self._reload_controller._use_content_hashes
            and hasattr(self._reload_controller, "_baseline_content_hashes")
            and self._reload_controller._baseline_content_hashes
        ):
            enhanced = self._reload_controller.decide_with_content_hashes(self.site.output_dir)
            if enhanced.meaningful_change_count == 0:
                # All changes are aggregate-only (sitemap, feeds, search index)
                decision = ReloadDecision(
                    action="none",
                    reason="aggregate-only",
                    changed_paths=(),
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
            # Safety: user changed files but decision is none (e.g. throttled).
            # Send reload unless we trust aggregate-only (sitemap/feeds only).
            if changed_files and decision.reason != "aggregate-only":
                logger.info(
                    "reload_bypass_source_changes",
                    reason="changed_files_nonempty_decision_none",
                    changed_count=len(changed_files),
                )
                self._reload_notifier.send("reload", "source-changes-bypass", ())
        else:
            logger.info(
                "reload_decision",
                action=decision.action,
                reason=decision.reason,
                source=decision_source,
            )
            self._reload_notifier.send(decision.action, decision.reason, decision.changed_paths)

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
