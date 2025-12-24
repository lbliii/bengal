"""
Site Content - Mutable content container for Bengal SSG.

Provides SiteContent dataclass for storing mutable content (pages, sections,
assets) populated during discovery. Supports freeze/unfreeze lifecycle for
thread-safe reads during parallel rendering.

Public API:
    SiteContent: Mutable container for site content

Key Concepts:
    Discovery Population: Content is populated during the discovery phase.
        Pages, sections, and assets are added as they're discovered.

    Freeze Lifecycle: Content can be frozen before rendering to enable
        thread-safe concurrent reads.

    Cached Derived Lists: Common page filters (regular, generated, listable)
        are cached for O(1) repeated access.

Lifecycle:
    1. Created empty at Site initialization
    2. Populated during discovery phase (pages, sections, assets)
    3. Extended during taxonomy/menu phases
    4. Frozen before rendering (optional, for safety)
    5. Cleared on rebuild via clear()

Thread Safety:
    - Mutations during discovery are single-threaded
    - After freeze(), reads are safe for parallel rendering
    - Dev server calls clear() before re-discovery

Related Packages:
    bengal.core.site.core: Site dataclass using SiteContent
    bengal.orchestration.content: Content discovery that populates SiteContent

See Also:
    plan/drafted/rfc-site-responsibility-separation.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.menu import MenuBuilder, MenuItem
    from bengal.core.page import Page
    from bengal.core.section import Section


@dataclass
class SiteContent:
    """
    Mutable content container populated during discovery.

    Lifecycle:
        1. Created empty at Site initialization
        2. Populated during discovery phase (pages, sections, assets)
        3. Extended during taxonomy/menu phases
        4. Frozen before rendering (optional, for safety)
        5. Cleared on rebuild via clear()

    Separation from Site:
        - Contains ONLY content data (pages, sections, assets)
        - No caches (those go in BuildState or derived properties)
        - No registries (those go in ContentRegistry)
        - No config (that goes in SiteData)

    Thread Safety:
        - Mutations during discovery are single-threaded
        - After freeze(), reads are safe for parallel rendering
        - Dev server calls clear() before re-discovery

    Attributes:
        pages: All pages in the site
        sections: All sections in the site
        assets: All assets in the site
        taxonomies: Collected taxonomies (tags, categories, etc.)
        menu: Navigation menus by name
        menu_builders: Menu builders by name
        menu_localized: Localized menus by language/name
        menu_builders_localized: Localized menu builders
        data: Data from data/ directory
    """

    # Core content
    pages: list[Page] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)

    # Derived content (populated after discovery)
    taxonomies: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Menu structures
    menu: dict[str, list[MenuItem]] = field(default_factory=dict)
    menu_builders: dict[str, MenuBuilder] = field(default_factory=dict)
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)

    # Data directory content
    data: dict[str, Any] = field(default_factory=dict)

    # Frozen flag
    _frozen: bool = field(default=False, repr=False)

    # Cached derived lists (invalidated on changes)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False)
    _generated_pages_cache: list[Page] | None = field(default=None, repr=False)
    _listable_pages_cache: list[Page] | None = field(default=None, repr=False)

    def freeze(self) -> None:
        """
        Freeze content before rendering phase.

        Called at end of content phase, before parallel rendering begins.
        After freezing, content should not be modified.
        """
        self._frozen = True

    def unfreeze(self) -> None:
        """
        Unfreeze content for dev server rebuilds.

        Called at start of reset_ephemeral_state() to allow re-population.
        """
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        """Whether content is frozen."""
        return self._frozen

    def clear(self) -> None:
        """
        Clear all content for rebuild.

        Called by Site.reset_ephemeral_state() before re-discovery.
        """
        self.pages = []
        self.sections = []
        self.assets = []
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        # Note: data is typically reloaded, not cleared
        self._frozen = False
        self.invalidate_caches()

    def invalidate_caches(self) -> None:
        """
        Invalidate derived page caches.

        Called after modifying pages list to ensure cached
        derived lists are recomputed on next access.
        """
        self._regular_pages_cache = None
        self._generated_pages_cache = None
        self._listable_pages_cache = None

    @property
    def regular_pages(self) -> list[Page]:
        """
        Get non-generated pages (cached).

        Returns:
            List of pages without _generated flag

        Example:
            for page in content.regular_pages:
                print(page.title)
        """
        if self._regular_pages_cache is None:
            self._regular_pages_cache = [p for p in self.pages if not p.metadata.get("_generated")]
        return self._regular_pages_cache

    @property
    def generated_pages(self) -> list[Page]:
        """
        Get generated pages (cached).

        Returns:
            List of pages with _generated flag (taxonomy, archive, etc.)
        """
        if self._generated_pages_cache is None:
            self._generated_pages_cache = [p for p in self.pages if p.metadata.get("_generated")]
        return self._generated_pages_cache

    @property
    def listable_pages(self) -> list[Page]:
        """
        Get pages visible in listings (cached).

        Respects visibility settings:
        - Excludes pages with hidden: true
        - Excludes pages with visibility.listings: false
        - Excludes draft pages

        Returns:
            List of pages that should appear in public listings
        """
        if self._listable_pages_cache is None:
            self._listable_pages_cache = [p for p in self.pages if p.in_listings]
        return self._listable_pages_cache

    @property
    def page_count(self) -> int:
        """Total number of pages."""
        return len(self.pages)

    @property
    def section_count(self) -> int:
        """Total number of sections."""
        return len(self.sections)

    @property
    def asset_count(self) -> int:
        """Total number of assets."""
        return len(self.assets)

    def __repr__(self) -> str:
        frozen_str = " (frozen)" if self._frozen else ""
        return (
            f"SiteContent(pages={len(self.pages)}, "
            f"sections={len(self.sections)}, "
            f"assets={len(self.assets)}{frozen_str})"
        )
