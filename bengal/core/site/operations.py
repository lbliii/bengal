"""
Site operations mixin.

Provides core site operations: build, serve, clean, and ephemeral state reset.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.url_ownership import URLRegistry
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats import BuildStats


class SiteOperationsMixin:
    """
    Mixin providing core site operations for Site.

    Provides build(), serve(), clean(), and reset_ephemeral_state() methods.
    """

    # These attributes are defined on the Site dataclass
    root_path: Path
    output_dir: Path
    pages: list[Any]
    sections: list[Any]
    assets: list[Any]
    taxonomies: dict[str, dict[str, Any]]
    menu: dict[str, list[Any]]
    menu_builders: dict[str, Any]
    menu_localized: dict[str, dict[str, list[Any]]]
    menu_builders_localized: dict[str, dict[str, Any]]
    xref_index: dict[str, Any]
    url_registry: URLRegistry
    _theme_obj: Any
    _current_build_state: BuildState | None
    _page_lookup_maps: dict[str, dict[str, Any]] | None
    _bengal_theme_chain_cache: dict[str, Any] | None
    _bengal_template_dirs_cache: dict[str, Any] | None
    _bengal_template_metadata_cache: dict[str, Any] | None
    _discovery_breakdown_ms: dict[str, float] | None
    _asset_manifest_fallbacks_global: set[str]
    features_detected: set[str]

    # These methods/properties are provided by other mixins or the main Site class:
    # - invalidate_page_caches(): from SiteCachesMixin
    # - registry: property from main Site class

    def build(
        self,
        options: BuildOptions,
    ) -> BuildStats:
        """
        Build the entire site.

        Delegates to BuildOrchestrator for actual build process.

        Args:
            options: BuildOptions dataclass with all build configuration.

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
            # Use debug level to avoid noise in clean command output
            emit_diagnostic(self, "debug", "cleaning_output_dir", path=str(self.output_dir))
            self._rmtree_robust(self.output_dir)
            emit_diagnostic(self, "debug", "output_dir_cleaned", path=str(self.output_dir))
        else:
            emit_diagnostic(self, "debug", "output_dir_does_not_exist", path=str(self.output_dir))

    @staticmethod
    def _rmtree_robust(path: Path, max_retries: int = 3) -> None:
        """
        Remove directory tree with retry logic for transient filesystem errors.

        Delegates to bengal.utils.file_io.rmtree_robust for the actual
        implementation.

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
        - Persist: root_path, config, theme, output_dir, build_time
        - Clear: pages, sections, assets
        - Clear derived: taxonomies, menu, menu_builders, xref_index (if present)
        - Clear caches: cached page lists
        """
        emit_diagnostic(self, "debug", "site_reset_ephemeral_state", site_root=str(self.root_path))

        # Content to be rediscovered
        self.pages = []
        self.sections = []
        self.assets = []

        # Derived structures (contain object references)
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}

        # Indices (rebuilt from pages)
        self.xref_index = {}

        # Cached properties
        self.invalidate_page_caches()

        # Clear content registry (includes section registries and URL ownership)
        self.registry.clear()

        # Reset URL registry and reconnect with content registry
        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        # Reset query registry (clear cached_property)
        self.__dict__.pop("indexes", None)

        # Reset lookup maps
        self._page_lookup_maps = None

        # Reset theme if needed (will be reloaded on first access)
        self._theme_obj = None

        # Runtime caches (Phase B fields)
        self._bengal_theme_chain_cache = None
        self._bengal_template_dirs_cache = None
        self._bengal_template_metadata_cache = None
        self._discovery_breakdown_ms = None
        self._asset_manifest_fallbacks_global.clear()

        # Clear Kida adapter's asset manifest cache (used for fingerprint resolution)
        if hasattr(self, "_kida_asset_manifest_cache"):
            delattr(self, "_kida_asset_manifest_cache")

        # CSS optimization state
        self.features_detected.clear()

        # Clear thread-local rendering caches (Phase B formalization)
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        # Clear thread-local asset manifest context (RFC: rfc-global-build-state-dependencies)
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
