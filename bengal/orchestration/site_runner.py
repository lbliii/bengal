"""
Site lifecycle runner.

Owns the build/serve/clean/rebuild operations that previously lived as
methods on `bengal.core.site.Site`. Extracting these moves the four
upward imports (BuildOrchestrator, DevServer, rendering.pipeline.thread_local,
rendering.assets) out of `bengal.core` — they belong in orchestration, not
in a passive data container.

Site retains thin delegating shims for back-compat with ~100 test call sites
and external code; new callers should construct `SiteRunner(site)` directly.

See `plan/immutable-floating-sun.md` Sprint B1 for context.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.site import Site
    from bengal.orchestration.build.inputs import BuildInput
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.stats.models import BuildStats


class SiteRunner:
    """
    Coordinates Site lifecycle: build, serve, clean, rebuild.

    Holds a reference to the Site it operates on. Stateless beyond that —
    each method is independent and can be invoked multiple times.

    """

    __slots__ = ("site",)

    def __init__(self, site: Site) -> None:
        self.site = site

    # =========================================================================
    # Build / Serve / Clean
    # =========================================================================

    def build(self, options: BuildOptions | BuildInput) -> BuildStats:
        """
        Build the entire site. Delegates to BuildOrchestrator.

        Args:
            options: BuildOptions or BuildInput with all build configuration.

        Returns:
            BuildStats object with build statistics

        """
        from bengal.orchestration.build import BuildOrchestrator

        orchestrator = BuildOrchestrator(self.site)
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
            auto_port: Whether to automatically find an available port
            open_browser: Whether to automatically open the browser
            version_scope: Focus rebuilds on a single version

        """
        from bengal.server.dev_server import DevServer

        server = DevServer(
            self.site,
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            version_scope=version_scope,
        )
        server.start()

    def clean(self) -> None:
        """Clean the output directory by removing all generated files."""
        site = self.site
        if site.output_dir.exists():
            emit_diagnostic(site, "debug", "cleaning_output_dir", path=str(site.output_dir))
            self._rmtree_robust(site.output_dir)
            emit_diagnostic(site, "debug", "output_dir_cleaned", path=str(site.output_dir))
        else:
            emit_diagnostic(site, "debug", "output_dir_does_not_exist", path=str(site.output_dir))

    @staticmethod
    def _rmtree_robust(path: Path, max_retries: int = 3) -> None:
        """Remove directory tree with retry logic for transient filesystem errors."""
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(path, max_retries=max_retries, caller="site")

    # =========================================================================
    # Rebuild lifecycle
    # =========================================================================

    def prepare_for_rebuild(self) -> None:
        """
        Reset content and derived-content state for a warm rebuild.

        Called by BuildTrigger before each warm build to ensure clean state
        while preserving config, theme, paths, and other immutable state.

        """
        site = self.site

        site.pages = []
        site.sections = []
        site.assets = []

        site.taxonomies = {}
        site.menu = {}
        site.menu_builders = {}
        site.menu_localized = {}
        site.menu_builders_localized = {}
        site.xref_index = {}

        site._cascade_snapshot = None

        site.invalidate_page_caches()
        site.invalidate_regular_pages_cache()
        site.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        site.url_registry = URLRegistry()
        site.registry.url_ownership = site.url_registry

        site._page_lookup_maps = None

    def reset_ephemeral_state(self) -> None:
        """
        Clear ephemeral/derived state that should not persist between builds.

        For long-lived Site instances (e.g., dev server) to avoid stale
        object references across rebuilds.

        """
        site = self.site
        emit_diagnostic(site, "debug", "site_reset_ephemeral_state", site_root=str(site.root_path))

        site.pages = []
        site.sections = []
        site.assets = []

        site.taxonomies = {}
        site.menu = {}
        site.menu_builders = {}
        site.menu_localized = {}
        site.menu_builders_localized = {}

        site.xref_index = {}

        site.invalidate_page_caches()
        site.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        site.url_registry = URLRegistry()
        site.registry.url_ownership = site.url_registry

        site.__dict__.pop("indexes", None)

        site._theme_obj = None
        site._page_lookup_maps = None
        site._bengal_theme_chain_cache = None
        site._bengal_template_dirs_cache = None
        site._bengal_template_metadata_cache = None
        site._discovery_breakdown_ms = None
        site._asset_manifest_fallbacks_global.clear()
        site.features_detected.clear()

        if hasattr(site, "_kida_asset_manifest_cache"):
            delattr(site, "_kida_asset_manifest_cache")

        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        from bengal.rendering.assets import reset_asset_manifest

        reset_asset_manifest()
