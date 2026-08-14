"""
Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup, cascading
frontmatter, and cross-reference indexing. This orchestrator is responsible
for populating the Site with all content before rendering.

Key Responsibilities:
Content Discovery
    Discovers pages and sections from the content/ directory, supports
    cache-based reconstruction for incremental builds
Asset Discovery
    Discovers site and theme assets from assets/ directories
Page References
    Sets up navigation references (next, prev, parent, children) between
    pages and their sections
Cascade Application
    Applies cascading frontmatter from section _index.md files to
    descendant pages
Cross-Reference Index
    Builds O(1) lookup indexes for cross-references by path, slug, ID,
    heading, and anchor

Build Phases:
The ContentOrchestrator is called during Phase 2 of the build pipeline.
It must complete before taxonomies, menus, or rendering can proceed.

Thread Safety:
Not thread-safe. Discovery runs on the main thread before parallel
rendering begins.

Package layout (behavior-preserving peel of the former content.py megafile):
    discover.py — discover, discover_content
    autodoc.py — remote sources + autodoc registration
    assets.py — discover_assets + provider/library bundles
    setup.py — page/section refs, cascades, output paths, validation
    xref.py — xref index + target directives
    features.py — _detect_features
    __init__.py — ContentOrchestrator facade

Related Modules:
bengal.content.discovery.content_discovery: Low-level content discovery
bengal.content.discovery.asset_discovery: Low-level asset discovery
bengal.core.cascade_snapshot: Immutable cascade data for thread-safe resolution

See Also:
bengal.orchestration.build: Build coordinator that calls this orchestrator

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

from . import assets as asset_ops
from . import autodoc, discover, features, setup, xref

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.autodoc.orchestration.result import AutodocRunResult
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.page_discovery_cache import PageDiscoveryCache
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import PageLike, SectionLike

logger = get_logger("bengal.orchestration.content")

__all__ = ["ContentOrchestrator"]


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

    def _strict_missing_content_dir(self) -> bool:
        """Return whether missing content should fail discovery."""
        return discover._strict_missing_content_dir(self)

    def discover(
        self,
        incremental: bool = False,
        cache: PageDiscoveryCache | None = None,
        build_context: BuildContext | None = None,
        build_cache: BuildCache | None = None,
    ) -> None:
        """Discover all content and assets. Main entry point called during build."""
        discover.discover(
            self,
            incremental=incremental,
            cache=cache,
            build_context=build_context,
            build_cache=build_cache,
        )

    def discover_content(
        self,
        content_dir: Path | None = None,
        incremental: bool = False,
        cache: PageDiscoveryCache | None = None,
        build_context: BuildContext | None = None,
        build_cache: BuildCache | None = None,
        warn_missing: bool = False,
    ) -> None:
        """Discover all content (pages, sections) in the content directory."""
        discover.discover_content(
            self,
            content_dir=content_dir,
            incremental=incremental,
            cache=cache,
            build_context=build_context,
            build_cache=build_cache,
            warn_missing=warn_missing,
        )

    def _fetch_remote_sources(
        self,
        collections: dict,
        content_dir: Path,
    ) -> None:
        """Fetch remote content sources and write to content directory."""
        autodoc._fetch_remote_sources(self, collections, content_dir)

    def _discover_autodoc_content(
        self, cache: PageDiscoveryCache | None = None, build_cache: Any | None = None
    ) -> tuple[list[PageLike], list[SectionLike]]:
        """Generate virtual autodoc pages if enabled."""
        return autodoc._discover_autodoc_content(self, cache=cache, build_cache=build_cache)

    def _register_autodoc_dependencies(
        self, run_result: AutodocRunResult, build_cache: Any
    ) -> None:
        """Register autodoc source -> page dependencies with the build cache."""
        autodoc._register_autodoc_dependencies(self, run_result, build_cache)

    def _log_autodoc_summary(self, result: AutodocRunResult) -> None:
        """Log a summary of autodoc run results."""
        autodoc._log_autodoc_summary(self, result)

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """Discover all assets in the assets directory and theme assets."""
        asset_ops.discover_assets(self, assets_dir)

    def _discover_provider_assets(self) -> None:
        """Discover assets from theme library providers, namespaced by prefix."""
        asset_ops._discover_provider_assets(self)

    def _write_library_asset_bundle(
        self,
        bundle_path: Path,
        assets: list[Any],
        asset_type: str,
    ) -> None:
        """Concatenate declared library assets into a generated bundle source."""
        asset_ops._write_library_asset_bundle(self, bundle_path, assets, asset_type)

    def _setup_page_references(self) -> None:
        """Set up page references for navigation (next, prev, parent, etc.)."""
        setup._setup_page_references(self)

    def _setup_section_references(self, section: SectionLike) -> None:
        """Recursively set up references for a section and its subsections."""
        setup._setup_section_references(self, section)

    def _apply_cascades(self) -> None:
        """Build cascade snapshot for view-based resolution."""
        setup._apply_cascades(self)

    def _set_output_paths(self) -> None:
        """Set output paths for all discovered pages."""
        setup._set_output_paths(self)

    def _validate_page_section_references(self) -> None:
        """Validate that pages in sections have correct _section references."""
        setup._validate_page_section_references(self)

    def _validate_subsection_references(
        self, section: SectionLike, pages_without_section: list[tuple[PageLike, SectionLike]]
    ) -> None:
        """Recursively validate page-section references in subsections."""
        setup._validate_subsection_references(self, section, pages_without_section)

    def _check_weight_metadata(self) -> None:
        """Check for documentation pages without weight metadata."""
        setup._check_weight_metadata(self)

    def _build_xref_index(self) -> None:
        """Build cross-reference index for O(1) page lookups."""
        xref._build_xref_index(self)

    def _index_by_path(self, page: PageLike, content_dir: Path) -> None:
        """Index a page by its content-relative path (without extension)."""
        xref._index_by_path(self, page, content_dir)

    def _index_by_slug(self, page: PageLike) -> None:
        """Index a page by slug (multiple pages can share a slug)."""
        xref._index_by_slug(self, page)

    def _index_by_id(self, page: PageLike) -> None:
        """Index a page by its custom frontmatter ``id``."""
        xref._index_by_id(self, page)

    def _index_headings(self, page: PageLike) -> None:
        """Index heading anchors from a page's TOC."""
        xref._index_headings(self, page)

    def _index_target_directives(self, page: PageLike) -> None:
        """Index ``:::{target} id`` directives from a page's raw source."""
        xref._index_target_directives(self, page)

    def _warn_anchor_collision(
        self,
        *,
        page: PageLike,
        anchor_id: str,
        existing_page: PageLike,
        existing_anchor: str,
        page_version: Any,
        details: str,
    ) -> None:
        """Emit the single ``anchor_collision`` warning shared by both index helpers."""
        logger.warning(
            "anchor_collision",
            anchor_id=anchor_id,
            target_page=str(getattr(page, "source_path", "unknown")),
            existing_page=str(getattr(existing_page, "source_path", "unknown")),
            existing_anchor=existing_anchor,
            version=page_version or "unversioned",
            details=details,
        )

    def _extract_target_directives(self, content: str) -> list[str]:
        """Extract target directive anchor IDs from markdown content."""
        return xref._extract_target_directives(self, content)

    def _detect_features(self, build_cache: BuildCache | None = None) -> None:
        """Detect CSS-requiring features in all pages."""
        features._detect_features(self, build_cache=build_cache)
