"""
Build trigger orchestrating the dev server rebuild pipeline.

Coordinates the complete rebuild workflow when file changes are detected,
from pre-build hooks through build execution to client reload notification.

BuildTrigger is a thin facade over focused modules:

- classify: change classification (nav, content-only, versions)
- debounce: queue/coalesce edits that arrive mid-rebuild
- incremental_gate: incremental vs full rebuild
- rebuild_plan: double-buffer + direct asset copies
- execute: reactive and warm rebuild strategies
- reload: overlay messages and reload decisions

Public import path is unchanged: ``from bengal.server.build_trigger import BuildTrigger``.
"""

import threading
from typing import TYPE_CHECKING, Any, Literal

from bengal.server.build_executor import BuildExecutor, BuildResult
from bengal.server.build_trigger.classify import ContentHashCacheEntry, FrontmatterCacheEntry
from bengal.server.build_trigger.rebuild_plan import _DoubleBuffer
from bengal.server.live_reload import LiveReloadNotifier
from bengal.server.reload_controller import ReloadController
from bengal.server.reload_controller import controller as default_reload_controller

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from pathlib import Path

    from bengal.protocols import SiteLike
    from bengal.server.buffer_manager import BufferManager
    from bengal.server.reload_protocols import ReloadNotifier
    from bengal.server.reload_types import BuildReloadInfo

__all__ = [
    "BuildTrigger",
    "ContentHashCacheEntry",
    "FrontmatterCacheEntry",
    "_DoubleBuffer",
]


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
        completion_policy: Any | None = None,
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
            completion_policy: Build completion policy for watched rebuilds.
        """
        from bengal.orchestration.build.options import BuildCompletionPolicy

        self.site = site
        self.host = host
        self.port = port
        self.version_scope = version_scope
        self.completion_policy = BuildCompletionPolicy.from_value(
            completion_policy or BuildCompletionPolicy.SERVE_READY
        )
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
        # Paths changed by the previous successful incremental buffered build.
        # The next staging buffer can be repaired by syncing only these paths.
        self._last_buffer_delta_paths: tuple[Path, ...] | None = None

    def trigger_build(self, changed_paths: set[Path], event_types: set[str]) -> None:
        """Trigger a build for the given changed paths."""
        from bengal.server.build_trigger.debounce import trigger_build as impl

        impl(self, changed_paths, event_types)

    def _execute_build(self, changed_paths: set[Path], event_types: set[str]) -> None:
        from bengal.server.build_trigger.execute import _execute_build as impl

        impl(self, changed_paths, event_types)

    def _run_reactive_build(
        self,
        changed_paths: set[Path],
        event_types: set[str],
        changed_files: list[str],
        config_dict: dict[str, Any],
    ) -> bool:
        from bengal.server.build_trigger.execute import _run_reactive_build as impl

        return impl(self, changed_paths, event_types, changed_files, config_dict)

    def _run_warm_build(
        self,
        *,
        changed_paths: set[Path],
        changed_files: list[str],
        nav_changed_files: set[Path] | None,
        structural_changed: bool,
        use_incremental: bool,
        cli: Any,
    ) -> tuple[BuildResult, Any, float] | None:
        from bengal.server.build_trigger.execute import _run_warm_build as impl

        return impl(
            self,
            changed_paths=changed_paths,
            changed_files=changed_files,
            nav_changed_files=nav_changed_files,
            structural_changed=structural_changed,
            use_incremental=use_incremental,
            cli=cli,
        )

    def _make_build_result(self, stats: Any, build_duration: float) -> BuildResult:
        from bengal.server.build_trigger.reload import _make_build_result as impl

        return impl(self, stats, build_duration)

    def _needs_full_rebuild(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        from bengal.server.build_trigger.incremental_gate import _needs_full_rebuild as impl

        return impl(self, changed_paths, event_types)

    def _can_use_reactive_path(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        from bengal.server.build_trigger.classify import _can_use_reactive_path as impl

        return impl(self, changed_paths, event_types)

    def _try_fast_asset_reload(
        self,
        changed_paths: set[Path],
        event_types: set[str],
        config: dict[str, Any],
    ) -> bool:
        from bengal.server.build_trigger.rebuild_plan import _try_fast_asset_reload as impl

        return impl(self, changed_paths, event_types, config)

    def _direct_asset_output_mappings(
        self,
        changed_paths: set[Path],
        event_types: set[str],
        config: dict[str, Any],
    ) -> tuple[tuple[Path, Path, Literal["asset"]], ...] | None:
        from bengal.server.build_trigger.rebuild_plan import _direct_asset_output_mappings as impl

        return impl(self, changed_paths, event_types, config)

    def _has_configured_build_hooks(self, config: dict[str, Any]) -> bool:
        from bengal.server.build_trigger.rebuild_plan import _has_configured_build_hooks as impl

        return impl(self, config)

    def _static_source_root(self, config: dict[str, Any]) -> Path:
        from bengal.server.build_trigger.rebuild_plan import _static_source_root as impl

        return impl(self, config)

    def _can_copy_site_asset_directly(self, source: Path) -> bool:
        from bengal.server.build_trigger.rebuild_plan import _can_copy_site_asset_directly as impl

        return impl(self, source)

    def _site_asset_for_source(self, source: Path) -> Any | None:
        from bengal.server.build_trigger.rebuild_plan import _site_asset_for_source as impl

        return impl(self, source)

    def _served_output_roots(self) -> tuple[Path, ...]:
        from bengal.server.build_trigger.rebuild_plan import _served_output_roots as impl

        return impl(self)

    def _buffer_delta_paths(self, changed_outputs: tuple[Any, ...]) -> tuple[Path, ...] | None:
        from bengal.server.build_trigger.rebuild_plan import _buffer_delta_paths as impl

        return impl(self, changed_outputs)

    def _active_output_exists(self, rel_output: Path) -> bool:
        from bengal.server.build_trigger.rebuild_plan import _active_output_exists as impl

        return impl(self, rel_output)

    def _relative_to(self, path: Path, root: Path) -> Path | None:
        from bengal.server.build_trigger.rebuild_plan import _relative_to as impl

        return impl(self, path, root)

    def _has_rendered_dependents(self, path: Path) -> bool:
        from bengal.server.build_trigger.classify import _has_rendered_dependents as impl

        return impl(self, path)

    def _is_shared_content_change(self, changed_paths: set[Path]) -> bool:
        from bengal.server.build_trigger.classify import _is_shared_content_change as impl

        return impl(self, changed_paths)

    def _get_affected_versions(self, changed_paths: set[Path]) -> set[str]:
        from bengal.server.build_trigger.classify import _get_affected_versions as impl

        return impl(self, changed_paths)

    def _is_version_config_change(self, changed_paths: set[Path]) -> bool:
        from bengal.server.build_trigger.classify import _is_version_config_change as impl

        return impl(self, changed_paths)

    def _detect_nav_changes(
        self,
        changed_paths: set[Path],
        needs_full_rebuild: bool,
    ) -> set[Path]:
        from bengal.server.build_trigger.classify import _detect_nav_changes as impl

        return impl(self, changed_paths, needs_full_rebuild)

    def _has_nav_affecting_frontmatter(self, path: Path) -> bool:
        from bengal.server.build_trigger.classify import _has_nav_affecting_frontmatter as impl

        return impl(self, path)

    def _compute_content_hashes(self, path: Path) -> ContentHashCacheEntry | None:
        from bengal.server.build_trigger.classify import _compute_content_hashes as impl

        return impl(self, path)

    def _is_content_only_change(self, path: Path) -> bool:
        from bengal.server.build_trigger.classify import _is_content_only_change as impl

        return impl(self, path)

    def seed_content_hash_cache(self, pages: list[Any]) -> None:
        """Populate content hash cache for content pages after a successful build."""
        from bengal.server.build_trigger.classify import seed_content_hash_cache as impl

        impl(self, pages)

    def _get_template_dirs(self) -> list[Path]:
        from bengal.server.build_trigger.incremental_gate import _get_template_dirs as impl

        return impl(self)

    def _is_template_change(self, changed_paths: set[Path]) -> bool:
        from bengal.server.build_trigger.incremental_gate import _is_template_change as impl

        return impl(self, changed_paths)

    def _template_name_for_path(self, path: Path, template_dirs: list[Path]) -> str:
        from bengal.server.build_trigger.incremental_gate import _template_name_for_path as impl

        return impl(self, path, template_dirs)

    def _get_template_dependents(
        self,
        path: Path,
        cache: Any,
        template_dirs: list[Path],
    ) -> tuple[set[str], bool]:
        from bengal.server.build_trigger.incremental_gate import _get_template_dependents as impl

        return impl(self, path, cache, template_dirs)

    def _is_in_template_dir(self, path: Path, template_dirs: list[Path]) -> bool:
        from bengal.server.build_trigger.incremental_gate import _is_in_template_dir as impl

        return impl(self, path, template_dirs)

    def _can_use_incremental_template_update(self, template_path: Path, cache: Any) -> bool:
        from bengal.server.build_trigger.incremental_gate import (
            _can_use_incremental_template_update as impl,
        )

        return impl(self, template_path, cache)

    def _should_regenerate_autodoc(self, changed_paths: set[Path]) -> bool:
        from bengal.server.build_trigger.incremental_gate import _should_regenerate_autodoc as impl

        return impl(self, changed_paths)

    def _display_stats(self, result: BuildResult, incremental: bool) -> None:
        from bengal.server.build_trigger.reload import _display_stats as impl

        impl(self, result, incremental)

    def _handle_overlay_messages(self, template_errors: list[Any], build_duration: float) -> bool:
        from bengal.server.build_trigger.reload import _handle_overlay_messages as impl

        return impl(self, template_errors, build_duration)

    def _handle_reload(self, info: BuildReloadInfo) -> None:
        from bengal.server.build_trigger.reload import _handle_reload as impl

        impl(self, info)

    def _should_capture_content_hash_baseline(self, changed_files: Sequence[str]) -> bool:
        from bengal.server.build_trigger.reload import (
            _should_capture_content_hash_baseline as impl,
        )

        return impl(self, changed_files)

    def _set_build_in_progress(self, building: bool) -> None:
        from bengal.server.build_trigger.reload import _set_build_in_progress as impl

        impl(self, building)

    def _clear_html_cache(self) -> None:
        from bengal.server.build_trigger.reload import _clear_html_cache as impl

        impl(self)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)
