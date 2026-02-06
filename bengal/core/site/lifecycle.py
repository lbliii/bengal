"""
Build lifecycle mixin for Site.

Provides prepare_for_rebuild() — the SINGLE SOURCE OF TRUTH for content and
derived-content state that must be reset between warm rebuilds in the dev server.

Architecture:
    The dev server keeps a single Site object alive across rebuilds (warm builds)
    to preserve expensive-to-compute immutable state (config, theme, paths).
    Between builds, content and derived structures must be reset cleanly.

    Per-build ephemeral state (cascade snapshot, template caches, features_detected,
    discovery timing) now lives on BuildState, which is created fresh for each build.
    This eliminates the class of bugs where we "forgot to reset field X" — the
    structural freshness of BuildState handles it automatically.

    prepare_for_rebuild() only resets CONTENT (pages, sections, assets), DERIVED
    STRUCTURES (taxonomies, menus, xref), PAGE CACHES, and REGISTRIES. Everything
    else is either immutable across builds or structurally fresh via BuildState.

Usage:
    # In BuildTrigger (dev server):
    self.site.prepare_for_rebuild()

    # In tests:
    site.prepare_for_rebuild()
    site.build(options)

Related:
    bengal/server/build_trigger.py: Calls prepare_for_rebuild() before warm builds
    bengal/orchestration/build_state.py: Per-build state (cascade, caches, features)
    bengal/core/site/cascade.py: Cascade bridge property delegates to BuildState
    bengal/core/site/caches.py: Page cache invalidation delegated to existing methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


class SiteLifecycleMixin:
    """
    Mixin providing build lifecycle management for Site.

    Centralizes content/derived-content reset for warm rebuilds.
    Per-build ephemeral state lives on BuildState (structurally fresh).
    """

    # These attributes are defined on the Site dataclass or other mixins
    pages: list[Page]
    sections: list[Section]
    assets: list[Any]
    taxonomies: dict[str, dict[str, Any]]
    xref_index: dict[str, Any]
    menu: dict[str, Any]
    menu_builders: dict[str, Any]
    menu_localized: dict[str, dict[str, Any]]
    menu_builders_localized: dict[str, dict[str, Any]]
    # Legacy fields kept for backward compat; primary path is BuildState
    _cascade_snapshot: Any
    _affected_tags: set[str]
    _page_lookup_maps: dict[str, Any] | None

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
            - _affected_tags, _page_lookup_maps (legacy fallback fields)

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
        # =================================================================
        # Content (rediscovered every build)
        # =================================================================
        self.pages = []
        self.sections = []
        self.assets = []

        # =================================================================
        # Derived content (rebuilt from content every build)
        # =================================================================
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        self.xref_index = {}

        # =================================================================
        # Cascade snapshot — local fallback
        #
        # The primary cascade path now goes through BuildState (structurally
        # fresh each build). This reset is a safety net for the local
        # fallback path used by tests and CLI health checks.
        # =================================================================
        self._cascade_snapshot = None

        # =================================================================
        # Page caches (must be invalidated when pages change)
        # =================================================================
        if hasattr(self, "invalidate_page_caches"):
            self.invalidate_page_caches()
        if hasattr(self, "invalidate_regular_pages_cache"):
            self.invalidate_regular_pages_cache()

        # =================================================================
        # Content registry (unfreezes and clears for re-discovery)
        # =================================================================
        if hasattr(self, "registry"):
            self.registry.clear()

        # URL registry (fresh registry for new build)
        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        if hasattr(self, "registry"):
            self.registry.url_ownership = self.url_registry

        # =================================================================
        # Legacy per-build fields (primary path is now BuildState)
        #
        # These are kept as safety nets for code paths that haven't
        # been migrated to use BuildState yet.
        # =================================================================
        self._affected_tags = set()
        self._page_lookup_maps = None
