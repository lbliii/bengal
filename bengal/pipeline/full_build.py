"""
Full build pipeline that replaces orchestrators with streams.

This module implements a complete reactive dataflow pipeline for Bengal builds,
replacing the hybrid orchestrator+pipeline approach with a pure stream-based
architecture.

Pipeline Flow:
==============

1. Content Discovery
   files → parse → pages

2. Sections
   pages → finalize_sections → sections_with_indexes

3. Taxonomies
   pages → collect_tags → taxonomy_pages

4. Menus
   pages + sections → build_navigation → menu_structure

5. Assets
   assets → process → fingerprinted_assets

6. Rendering
   pages + nav + taxonomies → render → rendered_pages

7. Postprocessing
   rendered_pages → sitemap + rss + search_index

Key Benefits:
=============
- Automatic dependency tracking through stream connections
- Fine-grained reactivity (only affected nodes recompute)
- Stream-based caching (no manual DependencyTracker)
- Better incremental builds
- Streaming output (show pages as they complete)

Related:
    - bengal/pipeline/build.py - Legacy hybrid pipeline
    - bengal/orchestration/ - Orchestrators being replaced
    - plan/implemented/rfc-reactive-dataflow-pipeline.md - Full RFC
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.pipeline.bengal_streams import (
    ContentDiscoveryStream,
    ParsedContent,
    RenderedPage,
    write_output,
)
from bengal.pipeline.builder import Pipeline
from bengal.pipeline.cache import StreamCache
from bengal.pipeline.menu import create_menu_stream
from bengal.pipeline.postprocess import create_postprocess_streams
from bengal.pipeline.sections import create_sections_stream
from bengal.pipeline.taxonomy import create_taxonomy_stream
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def _discover_sections_only(content_dir: Path, site: Site, pages: list[Page]) -> None:
    """
    Discover sections from directory structure and assign pages to them.

    This is an optimization: we already have pages from ContentDiscoveryStream,
    so we only need to discover sections and assign pages to them, rather than
    re-discovering everything.

    Args:
        content_dir: Content directory to scan
        site: Site instance to populate with sections
        pages: Already-discovered pages to assign to sections
    """
    from bengal.core.section import Section

    # Build a map of pages by their parent directory
    pages_by_dir: dict[Path, list[Page]] = {}
    for page in pages:
        parent_dir = page.source_path.parent
        if parent_dir not in pages_by_dir:
            pages_by_dir[parent_dir] = []
        pages_by_dir[parent_dir].append(page)

    # Track visited directories to detect symlink loops
    visited_inodes: set[tuple[int, int]] = set()

    def walk_directory(directory: Path, parent_section: Section | None = None) -> Section | None:
        """Recursively walk directory to create sections."""
        if not directory.exists():
            return None

        # Check for symlink loops
        try:
            stat = directory.stat()
            inode_key = (stat.st_dev, stat.st_ino)
            if inode_key in visited_inodes:
                logger.warning(
                    "symlink_loop_detected",
                    path=str(directory),
                    action="skipping_to_prevent_infinite_recursion",
                )
                return None
            visited_inodes.add(inode_key)
        except (OSError, PermissionError) as e:
            logger.warning(
                "directory_stat_failed",
                path=str(directory),
                error=str(e),
                action="skipping",
            )
            return None

        # Create section for this directory
        section = Section(name=directory.name, path=directory)
        section._site = site

        # Assign pages in this directory to the section
        if directory in pages_by_dir:
            for page in pages_by_dir[directory]:
                page._section = section
                section.add_page(page)

        # Walk subdirectories
        try:
            for item in sorted(directory.iterdir()):
                # Skip hidden files and directories
                if item.name.startswith((".", "_")) and item.name not in (
                    "_index.md",
                    "_index.markdown",
                ):
                    continue

                if item.is_dir():
                    subsection = walk_directory(item, section)
                    if subsection and (subsection.pages or subsection.subsections):
                        section.add_subsection(subsection)
        except PermissionError as e:
            logger.warning(
                "directory_permission_denied",
                path=str(directory),
                error=str(e),
                action="skipping",
            )

        # Only return section if it has content
        if section.pages or section.subsections:
            return section
        return None

    # Walk top-level directories
    try:
        for item in sorted(content_dir.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith((".", "_")) and item.name not in (
                "_index.md",
                "_index.markdown",
            ):
                continue

            if item.is_dir():
                section = walk_directory(item)
                if section:
                    site.sections.append(section)
    except PermissionError as e:
        logger.warning(
            "content_dir_permission_denied",
            path=str(content_dir),
            error=str(e),
            action="skipping",
        )


def create_full_build_pipeline(
    site: Site,
    *,
    parallel: bool = True,
    workers: int | None = None,
    use_cache: bool = True,
) -> Pipeline:
    """
    Create a complete build pipeline using pure streams (no orchestrators).

    This replaces the hybrid approach with a full reactive dataflow pipeline
    where all operations flow through streams.

    Args:
        site: Bengal Site instance to build
        parallel: Enable parallel processing
        workers: Number of worker threads (default: from config or 4)
        use_cache: Enable stream-based disk caching

    Returns:
        Complete Pipeline ready to run

    Example:
        >>> pipeline = create_full_build_pipeline(site)
        >>> result = pipeline.run()
        >>> print(f"Built {result.items_processed} pages")
    """
    from bengal.core.page import Page

    content_dir = site.root_path / "content"
    max_workers = workers or site.config.get("max_workers", 4)

    # Initialize stream cache if enabled
    cache: StreamCache | None = None
    if use_cache:
        cache_dir = site.root_path / ".bengal" / "pipeline_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = StreamCache(cache_dir)

    # ========================================================================
    # Phase 1: Content Discovery & Parsing
    # ========================================================================
    # Discover and parse all content files
    content_stream = ContentDiscoveryStream(content_dir)

    # Apply disk caching if enabled
    if cache:
        from bengal.pipeline.cache import DiskCachedStream

        content_stream = DiskCachedStream(content_stream, cache)

    # Transform ParsedContent → Page
    def create_page(parsed: ParsedContent) -> Page:
        """Create Page from ParsedContent."""
        return Page(
            source_path=parsed.source_path,
            content=parsed.content,
            metadata=parsed.metadata,
            _site=site,
        )

    page_stream = content_stream.map(create_page, name="create_page")

    # Cache pages if enabled
    if cache:
        from bengal.pipeline.cache import DiskCachedStream

        page_stream = DiskCachedStream(page_stream, cache)

    # ========================================================================
    # Phase 2-5: Sections, Taxonomies, Menus, Assets
    # ========================================================================
    # These need all pages collected first, so we use a barrier
    def process_all_phases(pages: list[Page]) -> list[Page]:
        """
        Process sections, taxonomies, menus, and assets.

        This is a temporary bridge that uses orchestrators for sections/menus/assets
        until we build pure stream implementations. Taxonomies now use streams.

        Note: Orchestrators modify site.pages directly, so we need to
        populate site.pages first, then let orchestrators add generated pages.
        """
        # Set pages first (needed for enrichment)
        site.pages = pages

        # CRITICAL: We need to discover sections and enrich pages before processing
        # The ContentDiscoveryStream only discovers pages, not sections
        # We discover sections separately and then enrich existing pages
        from bengal.orchestration.content import ContentOrchestrator

        content = ContentOrchestrator(site)
        content_dir = site.root_path / "content"

        if content_dir.exists():
            # Discover sections from directory structure (without re-discovering pages)
            # This is much faster than full discovery
            site.sections = []
            _discover_sections_only(content_dir, site, pages)

            # Register sections for path-based lookups
            site.register_sections()

            # Set up page references (next, prev, parent, etc.)
            content._setup_page_references()

            # Apply cascading frontmatter from sections to pages
            content._apply_cascades()

            # Set output paths for all pages
            content._set_output_paths()

            # Build cross-reference index
            content._build_xref_index()

        # Also discover assets (needed for asset processing)
        content.discover_assets()

        # Phase 2: Sections (now using streams!)
        # Create a stream from pages, finalize sections, collect results
        from bengal.pipeline.core import StreamItem
        from bengal.pipeline.streams import SourceStream

        def pages_for_sections_producer():
            """Produce StreamItems from pages list for section finalization."""
            for i, page in enumerate(pages):
                yield StreamItem.create(
                    source="pages_for_sections",
                    id=str(i),
                    value=page,
                )

        pages_for_sections_stream = SourceStream(
            pages_for_sections_producer, name="pages_for_sections"
        )
        sections_stream = create_sections_stream(pages_for_sections_stream, site)
        # Collect pages (includes original + generated archive pages)
        all_pages_with_sections = [item.value for item in sections_stream.iterate()]
        # Update site.pages with section pages
        pages = all_pages_with_sections
        site.pages = pages

        # Phase 3: Taxonomies (now using streams!)
        # Create a stream from pages, process taxonomies, collect results
        from bengal.pipeline.streams import SourceStream

        def pages_producer():
            """Produce StreamItems from pages list."""
            for i, page in enumerate(pages):
                yield StreamItem.create(
                    source="pages_list",
                    id=str(i),
                    value=page,
                )

        pages_stream = SourceStream(pages_producer, name="pages_list")
        taxonomy_stream = create_taxonomy_stream(pages_stream, site, parallel=parallel)
        # Collect taxonomy pages (includes original + generated)
        all_pages_with_taxonomies = [item.value for item in taxonomy_stream.iterate()]
        # Update site.pages with taxonomy pages
        site.pages = all_pages_with_taxonomies

        # Phase 4: Menus (now using streams!)
        # Create a stream from pages, build menus, collect results
        def pages_for_menu_producer():
            """Produce StreamItems from pages list for menu building."""
            for i, page in enumerate(site.pages):
                yield StreamItem.create(
                    source="pages_for_menu",
                    id=str(i),
                    value=page,
                )

        pages_for_menu_stream = SourceStream(pages_for_menu_producer, name="pages_for_menu")
        menu_stream = create_menu_stream(pages_for_menu_stream, site)
        # Iterate to build menus (menus are side-effect on site)
        list(menu_stream.iterate())

        # Phase 5: Assets (now using streams!)
        from bengal.pipeline.assets import create_assets_stream

        assets_stream = create_assets_stream(site.assets, site, parallel=parallel)
        # Process assets (assets are processed as side-effect)
        list(assets_stream.iterate())

        # Return all pages (including generated taxonomy pages)
        return list(site.pages)

    # ========================================================================
    # Phase 6: Rendering
    # ========================================================================
    # Filter by visibility
    is_production = not site.config.get("dev_server", False)

    def should_render(page: Page) -> bool:
        """Check if page should be rendered."""
        return page.should_render_in_environment(is_production=is_production)

    # Render pages using RenderingPipeline (with proper dependency tracker)
    import threading

    from bengal.cache.build_cache import BuildCache
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.rendering.pipeline import RenderingPipeline

    # Initialize build cache for dependency tracking
    cache_dir = site.root_path / ".bengal" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "cache.json"
    build_cache = BuildCache.load(cache_path) if cache_path.exists() else BuildCache()

    # Store cache on site for access by dependency tracker
    site._build_cache = build_cache

    _thread_local = threading.local()

    def get_render_pipeline() -> RenderingPipeline:
        """Get thread-local rendering pipeline with dependency tracker."""
        if not hasattr(_thread_local, "pipeline"):
            # Create dependency tracker with build cache for proper caching
            tracker = DependencyTracker(build_cache, site)
            _thread_local.pipeline = RenderingPipeline(site, dependency_tracker=tracker, quiet=True)
        return _thread_local.pipeline

    def render_page(page: Page) -> RenderedPage:
        """Parse markdown and render page using RenderingPipeline."""
        pipeline = get_render_pipeline()
        # process_page parses markdown (with cache), sets parsed_ast, and renders HTML
        pipeline.process_page(page)

        output_path = page.url.lstrip("/")
        if not output_path:
            output_path = "index.html"
        elif not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        return RenderedPage(
            page=page,
            html=page.rendered_html,
            output_path=Path(output_path),
        )

    # Write rendered pages
    def write_page(rendered: RenderedPage) -> None:
        """Write rendered page to disk."""
        write_output(site, rendered)

    # ========================================================================
    # Phase 7: Postprocessing (now using streams!)
    # ========================================================================
    # Postprocessing runs after all pages are written
    # We collect all rendered pages, run postprocessing, then continue
    def run_postprocess(rendered_pages: list[RenderedPage]) -> list[RenderedPage]:
        """Run postprocessing (sitemap, RSS, etc.) using streams."""
        from bengal.pipeline.core import StreamItem
        from bengal.pipeline.streams import SourceStream

        # Create stream from rendered pages
        def rendered_producer():
            """Produce StreamItems from rendered pages list."""
            for i, page in enumerate(rendered_pages):
                yield StreamItem.create(
                    source="rendered_pages",
                    id=str(i),
                    value=page,
                )

        rendered_stream = SourceStream(rendered_producer, name="rendered_pages")
        postprocess_stream = create_postprocess_streams(
            rendered_stream, site, parallel=parallel, incremental=False
        )
        # Iterate to run postprocessing (postprocessing is side-effect)
        list(postprocess_stream.iterate())
        return rendered_pages

    # Build pipeline using Pipeline builder API
    # The builder expects functions, not streams, so we wrap stream iteration
    def get_content_items():
        """Get items from content stream."""
        yield from (item.value for item in content_stream.iterate())

    pipeline = (
        Pipeline("bengal-full-build")
        .source("content", get_content_items)
        .map("create_page", create_page)
        .collect("all_pages")
        .map("process_phases", process_all_phases)
        .flat_map("flatten_pages", lambda pages: iter(pages))
        .filter("visibility_filter", should_render)
        .map("render", render_page)
    )

    if parallel:
        pipeline = pipeline.parallel(workers=max_workers)

    pipeline = pipeline.for_each("write", write_page)

    return pipeline
