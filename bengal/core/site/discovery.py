"""
Content discovery mixin for Site.

Provides methods for discovering content (pages, sections) and assets,
and setting up page/section references.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.discovery.content_discovery: Content discovery implementation
    - bengal.discovery.asset_discovery: Asset discovery implementation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section

logger = get_logger(__name__)


class ContentDiscoveryMixin:
    """
    Mixin providing content and asset discovery methods.

    Requires these attributes on the host class:
        - root_path: Path
        - config: dict[str, Any]
        - pages: list[Page]
        - sections: list[Section]
        - assets: list[Asset]
        - theme: str | None
        - register_sections: Callable (from SectionRegistryMixin)
        - _get_theme_assets_chain: Callable (from ThemeIntegrationMixin)
    """

    # Type hints for mixin attributes (provided by host class)
    root_path: Path
    config: dict[str, Any]
    pages: list[Page]
    sections: list[Section]
    assets: list[Asset]
    theme: str | None

    def discover_content(self, content_dir: Path | None = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Scans the content directory recursively, creating Page and Section
        objects for all markdown files and organizing them into a hierarchy.

        Args:
            content_dir: Content directory path (defaults to root_path/content)

        Example:
            >>> site = Site.from_config(Path('/path/to/site'))
            >>> site.discover_content()
            >>> print(f"Found {len(site.pages)} pages in {len(site.sections)} sections")
        """
        if content_dir is None:
            content_dir = self.root_path / "content"

        if not content_dir.exists():
            logger.warning("content_dir_not_found", path=str(content_dir))
            return

        from bengal.collections import load_collections
        from bengal.discovery.content_discovery import ContentDiscovery

        collections = load_collections(self.root_path)

        build_config = self.config.get("build", {}) if isinstance(self.config, dict) else {}
        strict_validation = build_config.get("strict_collections", False)

        discovery = ContentDiscovery(
            content_dir,
            site=self,
            collections=collections,
            strict_validation=strict_validation,
        )
        self.sections, self.pages = discovery.discover()

        # MUST come before _setup_page_references (registry needed for lookups)
        self.register_sections()
        self._setup_page_references()
        self._apply_cascades()

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Scans both theme assets (from theme inheritance chain) and site assets
        (from assets/ directory). Theme assets are discovered first (lower priority),
        then site assets (higher priority, can override theme assets). Assets are
        deduplicated by output path with site assets taking precedence.

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets).
                       If None, uses site root_path / "assets"

        Process:
            1. Discover theme assets from inheritance chain (child → parent → default)
            2. Discover site assets from assets_dir
            3. Deduplicate by output path (site assets override theme assets)

        Examples:
            site.discover_assets()  # Discovers from root_path/assets
            site.discover_assets(Path('/custom/assets'))  # Custom assets directory
        """
        from bengal.discovery.asset_discovery import AssetDiscovery

        self.assets = []

        # Theme assets first (lower priority), then site assets (higher priority)
        if self.theme:
            for theme_dir in self._get_theme_assets_chain():
                if theme_dir and theme_dir.exists():
                    theme_discovery = AssetDiscovery(theme_dir)
                    self.assets.extend(theme_discovery.discover())

        if assets_dir is None:
            assets_dir = self.root_path / "assets"

        if assets_dir.exists():
            logger.debug("discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            logger.warning("assets_dir_not_found", path=str(assets_dir))

        # Deduplicate by output path: later entries override earlier (site > child theme > parents)
        if self.assets:
            dedup: dict[str, Asset] = {}
            order: list[str] = []
            for asset in self.assets:
                key = str(asset.output_path) if asset.output_path else str(asset.source_path.name)
                if key in dedup:
                    dedup[key] = asset
                else:
                    dedup[key] = asset
                    order.append(key)
            self.assets = [dedup[k] for k in order]

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        Sets _site and _section references on all pages to enable navigation
        properties. Must be called after content discovery and section registry
        building, but before cascade application.

        Process:
            1. Set _site reference on all pages
            2. Set _site reference on all sections
            3. Set _section reference on pages based on their location

        Called By:
            discover_content() - Automatically called after content discovery

        See Also:
            _setup_section_references(): Sets up section parent-child relationships
        """
        for page in self.pages:
            page._site = self

        for section in self.sections:
            section._site = self
            for page in section.pages:
                page._section = section
            self._setup_section_references(section)

    def _setup_section_references(self, section: Section) -> None:
        """
        Recursively set up references for a section and its subsections.

        Sets _site reference on subsections and _section reference on pages
        within subsections. Recursively processes all nested subsections.

        Args:
            section: Section to set up references for (processes its subsections)

        Called By:
            _setup_page_references() - Called for each top-level section

        See Also:
            _setup_page_references(): Main entry point for reference setup
        """
        for subsection in section.subsections:
            subsection._site = self

            # Set section reference on pages in subsection
            for page in subsection.pages:
                page._section = subsection

            # Recurse into deeper subsections
            self._setup_section_references(subsection)

    def _apply_cascades(self) -> None:
        """
        Apply cascading metadata from sections to their child pages and subsections.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages. This allows setting common metadata (like type, version, or
        visibility) at the section level rather than repeating it on every page.

        Cascade metadata is defined in a section's _index.md frontmatter:

        Example:
            ---
            title: "Products"
            cascade:
              type: "product"
              version: "2.0"
              show_price: true
            ---

        All pages under this section will inherit these values unless they
        define their own values (page values take precedence over cascaded values).

        Delegates to CascadeEngine for the actual implementation.
        """
        from bengal.core.cascade_engine import CascadeEngine

        engine = CascadeEngine(self.pages, self.sections)
        engine.apply()

    # These methods are expected from other mixins - provide stubs for type checking
    def register_sections(self) -> None:
        """Build section registry. Provided by SectionRegistryMixin."""
        raise NotImplementedError("Must be provided by SectionRegistryMixin")

    def _get_theme_assets_chain(self) -> list[Path]:
        """Get theme assets chain. Provided by ThemeIntegrationMixin."""
        raise NotImplementedError("Must be provided by ThemeIntegrationMixin")

