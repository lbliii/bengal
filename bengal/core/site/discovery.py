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

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section


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

    # Method stubs for type checking (provided by other mixins)
    # NOTE: Do NOT add stub methods here that shadow real implementations in other mixins!
    # Python MRO resolves methods left-to-right, so stubs here would override implementations
    # in mixins listed later (like SectionRegistryMixin). Use NotImplementedError pattern only
    # for methods that MUST be overridden by the concrete class.

    def _get_theme_assets_chain(self) -> list[Path]:
        """Get theme assets paths in inheritance order (from ThemeIntegrationMixin)."""
        raise NotImplementedError("Implemented by ThemeIntegrationMixin")

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
            emit_diagnostic(self, "warning", "content_dir_not_found", path=str(content_dir))
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
        self._validate_page_section_references()
        self._apply_cascades()
        # Set output paths for all pages immediately after discovery
        self._set_output_paths()

    def _set_output_paths(self) -> None:
        """
        Set output paths for all discovered pages.

        This must be called after discovery and cascade application but before
        any code tries to access page.href (which depends on output_path).
        """
        from bengal.utils.url_strategy import URLStrategy

        for page in self.pages:
            # Skip if already set (e.g., generated pages)
            if page.output_path:
                continue

            # Compute output path using centralized strategy for regular pages
            page.output_path = URLStrategy.compute_regular_page_output_path(page, self)

            # Claim URL in registry for ownership enforcement
            # Priority 100 = user content (highest priority)
            if hasattr(self, "url_registry") and self.url_registry:
                try:
                    url = URLStrategy.url_from_output_path(page.output_path, self)
                    source = str(getattr(page, "source_path", page.title))
                    version = getattr(page, "version", None)
                    lang = getattr(page, "lang", None)
                    self.url_registry.claim(
                        url=url,
                        owner="content",
                        source=source,
                        priority=100,  # User content always wins
                        version=version,
                        lang=lang,
                    )
                except Exception:
                    # Don't fail discovery on registry errors (graceful degradation)
                    # Registry errors will be caught during validation phase
                    pass

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
            emit_diagnostic(self, "debug", "discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            emit_diagnostic(self, "warning", "assets_dir_not_found", path=str(assets_dir))

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
            1. Set _site reference on all pages (including top-level pages)
            2. Set _site reference on all sections
            3. Set _section reference on section index pages
            4. Set _section reference on pages based on their location
            5. Recursively process subsections

        Build Ordering Invariant:
            This method must be called after register_sections() to ensure
            the section registry is populated for virtual section URL lookups.

        Called By:
            discover_content() - Automatically called after content discovery

        See Also:
            _setup_section_references(): Sets up section parent-child relationships
            plan/active/rfc-page-section-reference-contract.md
        """
        # Set site reference on all pages (including top-level pages not in sections)
        for page in self.pages:
            page._site = self

        for section in self.sections:
            # Set site reference on section
            section._site = self

            # Set section reference on the section's index page (if it has one)
            if section.index_page:
                section.index_page._section = section

            # Set section reference on all pages in this section
            for page in section.pages:
                page._section = section

            # Recursively set for subsections
            self._setup_section_references(section)

    def _setup_section_references(self, section: Section) -> None:
        """
        Recursively set up references for a section and its subsections.

        Sets _site reference on subsections, _section reference on index pages,
        and _section reference on pages within subsections. Recursively
        processes all nested subsections.

        Args:
            section: Section to set up references for (processes its subsections)

        Called By:
            _setup_page_references() - Called for each top-level section

        See Also:
            _setup_page_references(): Main entry point for reference setup
            plan/active/rfc-page-section-reference-contract.md
        """
        for subsection in section.subsections:
            subsection._site = self

            # Set section reference on the subsection's index page (if it has one)
            if subsection.index_page:
                subsection.index_page._section = subsection

            # Set section reference on pages in subsection
            for page in subsection.pages:
                page._section = subsection

            # Recurse into deeper subsections
            self._setup_section_references(subsection)

    def _validate_page_section_references(self) -> None:
        """
        Validate that pages in sections have correct _section references.

        Logs warnings for pages that are in a section's pages list but have
        _section = None, which would cause navigation to fall back to flat mode.

        This validation catches bugs like the virtual section path=None issue
        described in plan/active/rfc-page-section-reference-contract.md.

        Called By:
            discover_content() - After _setup_page_references()
        """
        pages_without_section: list[tuple[Page, Section]] = []

        for section in self.sections:
            for page in section.pages:
                if page._section is None:
                    pages_without_section.append((page, section))

            # Check subsections recursively
            self._validate_subsection_references(section, pages_without_section)

        if pages_without_section:
            # Log warning with samples (limit to 5 to avoid log spam)
            sample_pages = [(str(p.source_path), s.name) for p, s in pages_without_section[:5]]
            emit_diagnostic(
                self,
                "warning",
                "pages_missing_section_reference",
                count=len(pages_without_section),
                samples=sample_pages,
                note="These pages are in sections but have _section=None, navigation may be flat",
            )

    def _validate_subsection_references(
        self, section: Section, pages_without_section: list[tuple[Page, Section]]
    ) -> None:
        """
        Recursively validate page-section references in subsections.

        Args:
            section: Section to check subsections of
            pages_without_section: List to append (page, expected_section) tuples to
        """
        for subsection in section.subsections:
            for page in subsection.pages:
                if page._section is None:
                    pages_without_section.append((page, subsection))

            # Recurse into deeper subsections
            self._validate_subsection_references(subsection, pages_without_section)

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
