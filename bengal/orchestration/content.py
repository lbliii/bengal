"""
Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup,
and cascading frontmatter.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.core.site import Site


class ContentOrchestrator:
    """
    Handles content and asset discovery.

    Responsibilities:
        - Discover content (pages and sections)
        - Discover assets (site and theme)
        - Set up page/section references for navigation
        - Apply cascading frontmatter from sections to pages
    """

    def __init__(self, site: Site):
        """
        Initialize content orchestrator.

        Args:
            site: Site instance to populate with content
        """
        self.site = site
        self.logger = get_logger(__name__)

    def discover(self, incremental: bool = False, cache: Any | None = None) -> None:
        """
        Discover all content and assets.

        Main entry point called during build.

        Args:
            incremental: Whether this is an incremental build (enables lazy loading)
            cache: PageDiscoveryCache instance (required if incremental=True)
        """
        self.discover_content(incremental=incremental, cache=cache)
        self.discover_assets()

    def discover_content(
        self, content_dir: Path | None = None, incremental: bool = False, cache: Any | None = None
    ) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Supports optional lazy loading with PageProxy for incremental builds.

        Args:
            content_dir: Content directory path (defaults to root_path/content)
            incremental: Whether this is an incremental build (enables lazy loading)
            cache: PageDiscoveryCache instance (required if incremental=True)
        """
        if content_dir is None:
            content_dir = self.site.root_path / "content"

        if not content_dir.exists():
            self.logger.warning("content_dir_not_found", path=str(content_dir))
            return

        self.logger.debug(
            "discovering_content",
            path=str(content_dir),
            incremental=incremental,
            use_cache=incremental and cache is not None,
        )

        from bengal.collections import load_collections
        from bengal.discovery.content_discovery import ContentDiscovery

        # Load collection schemas from project root (if collections.py exists)
        collections = load_collections(self.site.root_path)

        # Check if strict validation is enabled
        build_config = (
            self.site.config.get("build", {}) if isinstance(self.site.config, dict) else {}
        )
        strict_validation = build_config.get("strict_collections", False)

        discovery = ContentDiscovery(
            content_dir,
            site=self.site,
            collections=collections,
            strict_validation=strict_validation,
        )

        # Use lazy loading if incremental build with cache
        use_cache = incremental and cache is not None
        self.site.sections, self.site.pages = discovery.discover(use_cache=use_cache, cache=cache)

        # Note: Autodoc synthetic pages disabled - using traditional Markdown generation

        # Track how many pages are proxies (for logging)
        from bengal.core.page.proxy import PageProxy

        proxy_count = sum(1 for p in self.site.pages if isinstance(p, PageProxy))
        full_page_count = len(self.site.pages) - proxy_count

        self.logger.debug(
            "raw_content_discovered",
            pages=len(self.site.pages),
            sections=len(self.site.sections),
            proxies=proxy_count,
            full_pages=full_page_count,
        )

        # Build section registry for path-based lookups (MUST come before _setup_page_references)
        # This enables O(1) section lookups via page._section property
        self.site.register_sections()
        self.logger.debug("section_registry_built")

        # Set up page references for navigation
        self._setup_page_references()
        self.logger.debug("page_references_setup")

        # Apply cascading frontmatter from sections to pages
        self._apply_cascades()
        self.logger.debug("cascades_applied")

        # Set output paths for all pages immediately after discovery
        # This ensures page.url works correctly before rendering
        self._set_output_paths()
        self.logger.debug("output_paths_set")

        # Build cross-reference index for O(1) lookups
        self._build_xref_index()
        self.logger.debug(
            "xref_index_built", index_size=len(self.site.xref_index.get("by_path", {}))
        )

    def _discover_autodoc_content(self) -> list[Any]:
        """
        Generate autodoc synthetic pages if enabled.

        Returns:
            Empty list - HTML renderer disabled, using traditional Markdown generation
        """
        # HTML renderer disabled - return empty list
        return []

        # Check for missing weight metadata (info logging to educate users)
        self._check_weight_metadata()

        # Build cross-reference index for O(1) lookups
        self._build_xref_index()
        self.logger.debug(
            "xref_index_built", index_size=len(self.site.xref_index.get("by_path", {}))
        )

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.discovery.asset_discovery import AssetDiscovery

        self.site.assets = []
        theme_asset_count = 0
        site_asset_count = 0

        # Discover theme assets first (lower priority)
        if self.site.theme:
            theme_assets_dir = self._get_theme_assets_dir()
            if theme_assets_dir and theme_assets_dir.exists():
                self.logger.debug(
                    "discovering_theme_assets", theme=self.site.theme, path=str(theme_assets_dir)
                )
                theme_discovery = AssetDiscovery(theme_assets_dir)
                theme_assets = theme_discovery.discover()
                self.site.assets.extend(theme_assets)
                theme_asset_count = len(theme_assets)

        # Discover site assets (higher priority, can override theme assets)
        if assets_dir is None:
            assets_dir = self.site.root_path / "assets"

        if assets_dir.exists():
            self.logger.debug("discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            site_assets = site_discovery.discover()
            self.site.assets.extend(site_assets)
            site_asset_count = len(site_assets)
        elif not self.site.assets:
            # Only warn if we have no theme assets either
            self.logger.warning("assets_dir_not_found", path=str(assets_dir))

        self.logger.debug(
            "assets_discovered",
            theme_assets=theme_asset_count,
            site_assets=site_asset_count,
            total=len(self.site.assets),
        )

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        This method sets _site and _section references on all pages to enable
        navigation properties (next, prev, ancestors, etc.).

        Top-level pages (those not in any section) will have _section = None.
        """
        # Set site reference on all pages (including top-level pages)
        for page in self.site.pages:
            page._site = self.site
            # Initialize _section to None for pages not yet assigned
            if not hasattr(page, "_section"):
                page._section = None

        # Set section references
        for section in self.site.sections:
            # Set site reference on section
            section._site = self.site

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

        Args:
            section: Section to set up references for
        """
        for subsection in section.subsections:
            subsection._site = self.site

            # Set section reference on the subsection's index page (if it has one)
            if subsection.index_page:
                subsection.index_page._section = subsection

            # Set section reference on pages in subsection
            for page in subsection.pages:
                page._section = subsection

            # Recurse into deeper subsections
            self._setup_section_references(subsection)

    def _apply_cascades(self) -> None:
        """
        Apply cascading metadata from sections to their child pages and subsections.

        This implements Hugo-style cascade functionality where section _index.md files
        can define metadata that automatically applies to all descendant pages.

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

        Delegates to CascadeEngine for the actual implementation and collects statistics.
        """
        from bengal.core.cascade_engine import CascadeEngine

        engine = CascadeEngine(self.site.pages, self.site.sections)
        stats = engine.apply()

        # Log cascade statistics
        if stats.get("cascade_keys_applied"):
            keys_info = ", ".join(
                f"{k}({v})" for k, v in sorted(stats["cascade_keys_applied"].items())
            )
            self.logger.info(
                "cascades_applied",
                pages_processed=stats["pages_processed"],
                pages_affected=stats["pages_with_cascade"],
                root_cascade_pages=stats["root_cascade_pages"],
                cascade_keys=keys_info,
            )
        else:
            self.logger.debug(
                "cascades_applied",
                pages_processed=stats["pages_processed"],
                pages_affected=0,
                reason="no_cascades_defined",
            )

    def _set_output_paths(self) -> None:
        """
        Set output paths for all discovered pages.

        This must be called after discovery and cascade application but before
        any code tries to access page.url (which depends on output_path).

        Setting output_path early ensures:
        - page.url returns correct paths based on file structure
        - Templates can access page.url without getting fallback slug-based URLs
        - xref_index links work correctly
        - Navigation links have proper URLs
        """
        from bengal.utils.url_strategy import URLStrategy
        # SyntheticPage import removed - using traditional pages only

        paths_set = 0
        already_set = 0
        synthetic_paths_set = 0

        for page in self.site.pages:
            # Note: SyntheticPage handling removed - using traditional pages only

            # Skip if already set (e.g., generated pages, or set by section orchestrator)
            if page.output_path:
                already_set += 1
                continue

            # Compute output path using centralized strategy for regular pages
            page.output_path = URLStrategy.compute_regular_page_output_path(page, self.site)
            paths_set += 1

        self.logger.debug(
            "output_paths_configured",
            paths_set=paths_set,
            synthetic_paths_set=synthetic_paths_set,
            already_set=already_set,
            total_pages=len(self.site.pages),
        )

    def _check_weight_metadata(self) -> None:
        """
        Check for documentation pages without weight metadata.

        Weight is important for sequential content like docs and tutorials
        to ensure correct navigation order. This logs info (not a warning)
        to educate users about weight metadata.
        """
        doc_types = {"doc", "tutorial", "api-reference", "cli-reference", "changelog"}

        missing_weight_pages = []
        for page in self.site.pages:
            content_type = page.metadata.get("type")
            # Skip index pages (they don't need weight for navigation)
            if (
                content_type in doc_types
                and "weight" not in page.metadata
                and page.source_path.stem not in ("_index", "index")
            ):
                missing_weight_pages.append(page)

        if missing_weight_pages:
            # Log info (not warning - it's not an error, just helpful guidance)
            page_samples = [
                str(p.source_path.relative_to(self.site.root_path))
                for p in missing_weight_pages[:5]
            ]

            self.logger.info(
                "pages_without_weight",
                count=len(missing_weight_pages),
                content_types=list(doc_types),
                samples=page_samples[:5],  # Limit to 5 samples for brevity
            )

    def _build_xref_index(self) -> None:
        """
        Build cross-reference index for O(1) page lookups.

        Creates multiple indices to support different reference styles:
        - by_path: Reference by file path (e.g., 'docs/installation')
        - by_slug: Reference by slug (e.g., 'installation')
        - by_id: Reference by custom ID from frontmatter (e.g., 'install-guide')
        - by_heading: Reference by heading text for anchor links

        Performance: O(n) build time, O(1) lookup time
        Thread-safe: Read-only after building, safe for parallel rendering
        """
        self.site.xref_index = {
            "by_path": {},  # 'docs/getting-started' -> Page
            "by_slug": {},  # 'getting-started' -> [Pages]
            "by_id": {},  # Custom IDs from frontmatter -> Page
            "by_heading": {},  # Heading text -> [(Page, anchor)]
        }

        content_dir = self.site.root_path / "content"

        for page in self.site.pages:
            # Index by relative path (without extension)
            try:
                rel_path = page.source_path.relative_to(content_dir)
                # Remove extension and normalize path separators
                path_key = str(rel_path.with_suffix("")).replace("\\", "/")
                # Also handle _index.md -> directory path
                if path_key.endswith("/_index"):
                    path_key = path_key[:-7]  # Remove '/_index'
                self.site.xref_index["by_path"][path_key] = page
            except ValueError:
                # Page is not relative to content_dir (e.g., generated page)
                pass

            # Index by slug (multiple pages can have same slug)
            if hasattr(page, "slug") and page.slug:
                self.site.xref_index["by_slug"].setdefault(page.slug, []).append(page)

            # Index custom IDs from frontmatter
            if "id" in page.metadata:
                ref_id = page.metadata["id"]
                self.site.xref_index["by_id"][ref_id] = page

            # Index headings from TOC (for anchor links)
            # NOTE: This accesses toc_items BEFORE parsing (during discovery phase).
            # This is safe because toc_items property returns [] when toc is not set,
            # and importantly does NOT cache the empty result. After parsing, when
            # toc is set, the property will extract and cache the real structure.
            if hasattr(page, "toc_items") and page.toc_items:
                for toc_item in page.toc_items:
                    heading_text = toc_item.get("title", "").lower()
                    anchor_id = toc_item.get("id", "")
                    if heading_text and anchor_id:
                        self.site.xref_index["by_heading"].setdefault(heading_text, []).append(
                            (page, anchor_id)
                        )

    def _get_theme_assets_dir(self) -> Path | None:
        """
        Get the assets directory for the current theme.

        Returns:
            Path to theme assets or None if not found
        """
        if not self.site.theme:
            return None

        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / self.site.theme / "assets"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.site.theme / "assets"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None
