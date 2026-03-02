"""
Lifecycle mixin for Site.

Provides build, serve, clean, and state reset operations. These are the
"active" operations that coordinate with orchestrators and manage
per-build ephemeral state.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.menu import MenuBuilder, MenuItem
    from bengal.core.page import Page
    from bengal.core.registry import ContentRegistry
    from bengal.core.section import Section
    from bengal.core.url_ownership import URLRegistry
    from bengal.orchestration.build.inputs import BuildInput
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats.models import BuildStats


class SiteLifecycleMixin:
    """
    Mixin providing lifecycle operations for Site.

    Expects from host class:
        root_path: Path
        output_dir: Path
        pages: list[Page]
        sections: list[Section]
        assets: list[Asset]
        taxonomies: dict[str, dict[str, Any]]
        xref_index: dict[str, Any]
        menu: dict[str, list[MenuItem]]
        menu_builders: dict[str, MenuBuilder]
        menu_localized: dict[str, dict[str, list[MenuItem]]]
        menu_builders_localized: dict[str, dict[str, MenuBuilder]]
        url_registry: URLRegistry
        _registry: ContentRegistry | None
        _current_build_state: BuildState | None
        _cascade_snapshot: Any
        _page_lookup_maps: Any
        invalidate_page_caches() -> None
        invalidate_regular_pages_cache() -> None
        registry: ContentRegistry (property)
    """

    root_path: Path
    output_dir: Path
    pages: list[Page]
    sections: list[Section]
    assets: list[Asset]
    taxonomies: dict[str, dict[str, Any]]
    xref_index: dict[str, Any]
    menu: dict[str, list[MenuItem]]
    menu_builders: dict[str, MenuBuilder]
    menu_localized: dict[str, dict[str, list[MenuItem]]]
    menu_builders_localized: dict[str, dict[str, MenuBuilder]]
    url_registry: URLRegistry
    _current_build_state: BuildState | None
    _cascade_snapshot: Any
    _page_lookup_maps: Any

    # Host-provided (from SiteDiscoveryMixin, Site, etc.)
    registry: ContentRegistry
    _theme_obj: Any
    _bengal_theme_chain_cache: Any
    _bengal_template_dirs_cache: Any
    _bengal_template_metadata_cache: Any
    _discovery_breakdown_ms: Any
    features_detected: set[str]
    _asset_manifest_fallbacks_global: set[str]

    def invalidate_page_caches(self) -> None: ...
    def invalidate_regular_pages_cache(self) -> None: ...

    def prepare_for_rebuild(self) -> None:
        """
        Reset content and derived-content state for a warm rebuild.

        Called by BuildTrigger before each warm build to ensure clean state
        while preserving config, theme, paths, and other immutable state that
        is expensive to recompute.

        What IS reset here (content and derived structures):
            - pages, sections, assets (rediscovered every build)
            - taxonomies, menus, xref_index (rebuilt from content)
            - page caches (regular_pages, generated_pages, etc.)
            - content registry and URL registry
            - _cascade_snapshot fallback (primary is on BuildState)
            - _page_lookup_maps (legacy fallback field)

        What is handled by BuildState (structurally fresh each build):
            - cascade_snapshot (primary — site.cascade delegates to BuildState)
            - features_detected, discovery_timing_ms
            - template caches (theme_chain, template_dirs, template_metadata)
            - asset_manifest_previous, asset_manifest_fallbacks
            - current_language, current_version (render context)

        What is NOT reset (immutable/persistent across builds):
            - root_path, config, theme, output_dir (configuration)
            - _theme_obj, _paths, _config_hash (derived config)
            - version_config (versioning setup)
            - data (data/ directory — reloaded during discovery if changed)
            - dev_mode (runtime flag)
            - build_time (overwritten at build start)

        Example:
            # Dev server warm rebuild:
            site.prepare_for_rebuild()
            site.build(options)

        See Also:
            bengal/server/build_trigger.py: Where this is called
            bengal/orchestration/build_state.py: Per-build ephemeral state
            bengal/core/site/cascade.py: Cascade bridge to BuildState
        """
        self.pages = []
        self.sections = []
        self.assets = []

        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        self.xref_index = {}

        self._cascade_snapshot = None

        self.invalidate_page_caches()
        self.invalidate_regular_pages_cache()
        self.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        self._page_lookup_maps = None

    def build(
        self,
        options: BuildOptions | BuildInput,
    ) -> BuildStats:
        """
        Build the entire site.

        Delegates to BuildOrchestrator for actual build process.

        Args:
            options: BuildOptions or BuildInput with all build configuration.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(strict=True)
            >>> stats = site.build(options)
        """
        from bengal.orchestration import BuildOrchestrator

        orchestrator = BuildOrchestrator(self)
        return orchestrator.build(options)

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        version_scope: str | None = None,
    ) -> None:
        """
        Start a development server.

        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
            auto_port: Whether to automatically find an available port if the specified one is
                       in use
            open_browser: Whether to automatically open the browser
            version_scope: Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
        """
        from bengal.server.dev_server import DevServer

        server = DevServer(
            self,
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            version_scope=version_scope,
        )
        server.start()

    def clean(self) -> None:
        """
        Clean the output directory by removing all generated files.

        Useful for starting fresh or troubleshooting build issues.

        Example:
            >>> site = Site.from_config(Path('/path/to/site'))
            >>> site.clean()  # Remove all files in public/
            >>> site.build()  # Rebuild from scratch
        """
        if self.output_dir.exists():
            emit_diagnostic(self, "debug", "cleaning_output_dir", path=str(self.output_dir))
            self._rmtree_robust(self.output_dir)
            emit_diagnostic(self, "debug", "output_dir_cleaned", path=str(self.output_dir))
        else:
            emit_diagnostic(self, "debug", "output_dir_does_not_exist", path=str(self.output_dir))

    @staticmethod
    def _rmtree_robust(path: Path, max_retries: int = 3) -> None:
        """
        Remove directory tree with retry logic for transient filesystem errors.

        Args:
            path: Directory to remove
            max_retries: Number of retry attempts (default 3)

        Raises:
            OSError: If deletion fails after all retries
        """
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(path, max_retries=max_retries, caller="site")

    def reset_ephemeral_state(self) -> None:
        """
        Clear ephemeral/derived state that should not persist between builds.

        This method is intended for long-lived Site instances (e.g., dev server)
        to avoid stale object references across rebuilds.

        Persistence contract:
        - Persist: root_path, config, theme, output_dir, build_time, dev_mode
        - Clear: pages, sections, assets (content)
        - Clear derived: taxonomies, menu, xref_index
        - Clear caches: page caches
        - Clear registries: content registry, URL registry
        - Handled by BuildState: cascade, template caches, features, discovery timing
        """
        emit_diagnostic(self, "debug", "site_reset_ephemeral_state", site_root=str(self.root_path))

        self.pages = []
        self.sections = []
        self.assets = []

        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}

        self.xref_index = {}

        self.invalidate_page_caches()
        self.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        self.__dict__.pop("indexes", None)

        self._theme_obj = None
        self._page_lookup_maps = None
        self._bengal_theme_chain_cache = None
        self._bengal_template_dirs_cache = None
        self._bengal_template_metadata_cache = None
        self._discovery_breakdown_ms = None
        self._asset_manifest_fallbacks_global.clear()
        self.features_detected.clear()

        if hasattr(self, "_kida_asset_manifest_cache"):
            delattr(self, "_kida_asset_manifest_cache")

        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        from bengal.rendering.assets import reset_asset_manifest

        reset_asset_manifest()

    @property
    def build_state(self) -> BuildState | None:
        """
        Current build state (None outside build context).

        Returns:
            BuildState during build execution, None otherwise

        Example:
            if site.build_state:
                lock = site.build_state.get_lock("asset_write")
        """
        return self._current_build_state

    def set_build_state(self, state: BuildState | None) -> None:
        """
        Set current build state (called by BuildOrchestrator).

        Args:
            state: BuildState to set, or None to clear

        Note:
            This is called internally by BuildOrchestrator at build start/end.
            Do not call directly unless implementing custom build coordination.
        """
        self._current_build_state = state
