"""
Build lifecycle mixin for Site.

Provides prepare_for_rebuild() — the SINGLE SOURCE OF TRUTH for all mutable
per-build state that must be reset between warm rebuilds in the dev server.

Architecture:
    The dev server keeps a single Site object alive across rebuilds (warm builds)
    to preserve expensive-to-compute immutable state (config, theme, paths).
    Between builds, all per-build mutable state must be reset cleanly.

    Before this mixin existed, the reset logic lived inline in BuildTrigger,
    manually enumerating each field. This caused bugs when new fields were added
    but not included in the reset (e.g., _cascade_snapshot, which caused layout
    cascade to be silently lost on hot reload).

    Now, Site owns its own reset contract. BuildTrigger calls a single method.

Usage:
    # In BuildTrigger (dev server):
    self.site.prepare_for_rebuild()

    # In tests:
    site.prepare_for_rebuild()
    site.build(options)

Related:
    bengal/server/build_trigger.py: Calls prepare_for_rebuild() before warm builds
    bengal/core/site/cascade.py: Cascade snapshot reset handled here
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

    Centralizes per-build state reset to prevent stale data bugs during
    warm rebuilds in the dev server. Every piece of mutable per-build state
    is reset here — nowhere else.
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
    features_detected: set[str]
    _cascade_snapshot: Any
    _affected_tags: set[str]
    _page_lookup_maps: dict[str, Any] | None
    _discovery_breakdown_ms: dict[str, float] | None

    def prepare_for_rebuild(self) -> None:
        """
        Reset all mutable per-build state for a warm rebuild.

        Called by BuildTrigger before each warm build to ensure clean state
        while preserving config, theme, paths, and other immutable state that
        is expensive to recompute.

        This method is the SINGLE SOURCE OF TRUTH for per-build state reset.
        If you add new mutable per-build state to Site, add its reset here.

        What IS reset (per-build, changes every build):
            - pages, sections, assets (content)
            - taxonomies, menus, xref_index (derived content)
            - _cascade_snapshot (cascade metadata)
            - page caches (regular_pages, generated_pages, etc.)
            - content registry and URL registry
            - features_detected, affected_tags, page_lookup_maps
            - discovery breakdown timing

        What is NOT reset (immutable across builds):
            - root_path, config, theme, output_dir (configuration)
            - _theme_obj, _paths, _config_hash (derived config)
            - version_config (versioning setup)
            - data (data/ directory — reloaded during discovery if changed)
            - dev_mode (runtime flag)
            - _asset_manifest_previous (needed for incremental asset comparison)
            - template caches (theme chain, template dirs, metadata)

        Example:
            # Dev server warm rebuild:
            site.prepare_for_rebuild()
            site.build(options)

        See Also:
            bengal/server/build_trigger.py: Where this is called
            bengal/core/site/caches.py: Page cache invalidation
            bengal/core/site/cascade.py: Cascade snapshot management
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
        # Cascade snapshot — CRITICAL
        #
        # Must be reset to None so that:
        # 1. No stale cascade data survives from the previous build
        # 2. The cascade property returns CascadeSnapshot.empty() until
        #    _apply_cascades() rebuilds it during discovery
        # 3. CascadeView cache keys (keyed by id(snapshot)) are invalidated
        #    when the new snapshot is built (different object = different id)
        #
        # Previously this was NOT reset, causing layout cascade to silently
        # fall back to empty values during hot reload.
        # =================================================================
        self._cascade_snapshot = None

        # =================================================================
        # Page caches (must be invalidated when pages change)
        # =================================================================
        # Delegate to existing cache invalidation methods
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
        # Discovery state
        # =================================================================
        self.features_detected = set()
        self._affected_tags = set()
        self._page_lookup_maps = None
        self._discovery_breakdown_ms = None
