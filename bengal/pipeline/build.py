"""
Bengal build pipeline factory functions.

This module provides factory functions for creating build pipelines:
- create_build_pipeline(): Full site build
- create_incremental_pipeline(): Incremental rebuild for changed files

These pipelines integrate Bengal's discovery, page creation, and rendering
with the reactive dataflow infrastructure.

Example:
    >>> from bengal.pipeline.build import create_build_pipeline
    >>> pipeline = create_build_pipeline(site)
    >>> result = pipeline.run()
    >>> print(f"Built {result.items_processed} pages")

Related:
    - bengal/pipeline/bengal_streams.py - Bengal-specific stream adapters
    - bengal/pipeline/builder.py - Pipeline builder API
    - bengal/orchestration/build/ - Legacy build orchestration (being replaced)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.pipeline.bengal_streams import (
    ParsedContent,
    RenderedPage,
    write_output,
)
from bengal.pipeline.builder import Pipeline
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_build_pipeline(
    site: Site,
    *,
    parallel: bool = True,
    workers: int = 4,
) -> Pipeline:
    """
    Create the main Bengal build pipeline.

    The pipeline flows:

        discover → parse → page → [collect] → navigation
                              ↓           ↓
                           render ← ← ← ←┘
                              ↓
                           write

    Args:
        site: Bengal Site instance to build
        parallel: Enable parallel processing
        workers: Number of worker threads for parallel stages

    Returns:
        Configured Pipeline ready to run

    Example:
        >>> pipeline = create_build_pipeline(site)
        >>> result = pipeline.run()
        >>> if result.success:
        ...     print(f"Built {result.items_processed} pages")
    """
    from bengal.core.page import Page

    content_dir = site.root_path / "content"

    # Build navigation from all pages (collected first)
    all_pages: list[Page] = []
    navigation: Any = None

    def discover_and_parse():
        """Discover content files and parse frontmatter."""
        import hashlib

        import frontmatter

        from bengal.utils.file_io import read_text_file

        for file_path in _discover_content_files(content_dir):
            try:
                file_content = read_text_file(file_path)
                content_hash = hashlib.sha256(file_content.encode()).hexdigest()[:16]

                try:
                    post = frontmatter.loads(file_content)
                    content = post.content
                    metadata = dict(post.metadata)
                except Exception:
                    content = file_content
                    metadata = {
                        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
                    }

                yield ParsedContent(
                    source_path=file_path,
                    content=content,
                    metadata=metadata,
                    content_hash=content_hash,
                )
            except Exception as e:
                logger.warning("parse_error", file=str(file_path), error=str(e))
                continue

    def create_page(parsed: ParsedContent) -> Page:
        """Create Page from ParsedContent."""
        page = Page(
            source_path=parsed.source_path,
            raw_content=parsed.content,
            params=parsed.metadata,
            site=site,
        )
        all_pages.append(page)
        return page

    def build_navigation_once(pages: list[Page]) -> Any:
        """Build navigation from collected pages."""
        nonlocal navigation
        if navigation is None:
            from bengal.core.menu import MenuBuilder

            menu_builder = MenuBuilder(site)
            navigation = menu_builder.build_menus(pages)
        return navigation

    def render_page(page: Page) -> RenderedPage:
        """Render page with navigation."""
        from bengal.rendering.template_engine import TemplateEngine

        # Ensure navigation is built
        if navigation is None:
            build_navigation_once(all_pages)

        engine = getattr(site, "_template_engine", None)
        if engine is None:
            engine = TemplateEngine(site)
            site._template_engine = engine

        html = engine.render_page(page, navigation=navigation)

        output_path = page.url.lstrip("/")
        if not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        return RenderedPage(
            page=page,
            html=html,
            output_path=Path(output_path),
        )

    def write_page(rendered: RenderedPage) -> None:
        """Write rendered page to disk."""
        write_output(site, rendered)

    # Build the pipeline
    pipeline = (
        Pipeline("bengal-build")
        .source("discover", discover_and_parse)
        .map("create_page", create_page)
    )

    if parallel:
        pipeline = pipeline.parallel(workers=workers)

    pipeline = (
        pipeline.collect("all_pages").map("build_nav", build_navigation_once)
        # After building nav, we need to render each page
    )

    # For now, use a simpler approach - render in for_each
    # This captures the navigation in closure
    return (
        Pipeline("bengal-build")
        .source("discover", discover_and_parse)
        .map("create_page", create_page)
        .map("render", render_page)
        .for_each("write", write_page)
    )


def create_incremental_pipeline(
    site: Site,
    changed_files: list[Path],
    *,
    parallel: bool = True,
    workers: int = 4,
) -> Pipeline:
    """
    Create an incremental build pipeline for changed files.

    This pipeline:
    1. Only processes files in changed_files
    2. Reuses cached pages for unchanged files (from site.pages)
    3. Rebuilds navigation only if structure changed
    4. Re-renders only affected pages

    Args:
        site: Bengal Site instance
        changed_files: List of paths that have changed
        parallel: Enable parallel processing
        workers: Number of worker threads

    Returns:
        Configured Pipeline for incremental build

    Example:
        >>> changed = [Path("content/docs/guide.md")]
        >>> pipeline = create_incremental_pipeline(site, changed)
        >>> result = pipeline.run()
    """
    from bengal.core.page import Page

    # Track if navigation needs rebuild
    nav_rebuild_needed = False
    navigation: Any = None

    def get_changed_content():
        """Yield content for changed files only."""
        import hashlib

        import frontmatter

        from bengal.utils.file_io import read_text_file

        for file_path in changed_files:
            if not file_path.exists():
                logger.debug("file_deleted", path=str(file_path))
                continue

            if file_path.suffix not in (".md", ".markdown"):
                continue

            try:
                file_content = read_text_file(file_path)
                content_hash = hashlib.sha256(file_content.encode()).hexdigest()[:16]

                try:
                    post = frontmatter.loads(file_content)
                    content = post.content
                    metadata = dict(post.metadata)
                except Exception:
                    content = file_content
                    metadata = {
                        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
                    }

                yield ParsedContent(
                    source_path=file_path,
                    content=content,
                    metadata=metadata,
                    content_hash=content_hash,
                )
            except Exception as e:
                logger.warning("parse_error", file=str(file_path), error=str(e))
                continue

    def create_page(parsed: ParsedContent) -> Page:
        """Create Page from ParsedContent."""
        nonlocal nav_rebuild_needed

        page = Page(
            source_path=parsed.source_path,
            raw_content=parsed.content,
            params=parsed.metadata,
            site=site,
        )

        # Check if nav rebuild needed (weight or title changed)
        existing = next((p for p in site.pages if p.source_path == parsed.source_path), None)
        if existing:
            if existing.weight != page.weight or existing.title != page.title:
                nav_rebuild_needed = True
        else:
            # New page - nav rebuild needed
            nav_rebuild_needed = True

        return page

    def render_page(page: Page) -> RenderedPage:
        """Render page with navigation."""
        nonlocal navigation

        from bengal.rendering.template_engine import TemplateEngine

        # Build or reuse navigation
        if navigation is None:
            if nav_rebuild_needed:
                from bengal.core.menu import MenuBuilder

                menu_builder = MenuBuilder(site)
                navigation = menu_builder.build_menus(site.pages)
            else:
                # Reuse existing navigation
                navigation = getattr(site, "_navigation", {})

        engine = getattr(site, "_template_engine", None)
        if engine is None:
            engine = TemplateEngine(site)
            site._template_engine = engine

        html = engine.render_page(page, navigation=navigation)

        output_path = page.url.lstrip("/")
        if not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        return RenderedPage(
            page=page,
            html=html,
            output_path=Path(output_path),
        )

    def write_page(rendered: RenderedPage) -> None:
        """Write rendered page to disk."""
        write_output(site, rendered)

    pipeline = (
        Pipeline("bengal-incremental")
        .source("changed", get_changed_content)
        .map("create_page", create_page)
        .map("render", render_page)
        .for_each("write", write_page)
    )

    return pipeline


def create_simple_pipeline(
    site: Site,
    pages: list[Page] | None = None,
) -> Pipeline:
    """
    Create a simple render-only pipeline for pre-discovered pages.

    Useful when pages are already discovered and you just need to render.

    Args:
        site: Bengal Site instance
        pages: Pre-discovered pages (uses site.pages if not provided)

    Returns:
        Pipeline that renders and writes pages
    """

    pages_to_render = pages if pages is not None else list(site.pages)
    navigation: Any = None

    def get_pages():
        """Yield pages to render."""
        yield from pages_to_render

    def render_page(page: Page) -> RenderedPage:
        """Render page with navigation."""
        nonlocal navigation

        from bengal.rendering.template_engine import TemplateEngine

        if navigation is None:
            from bengal.core.menu import MenuBuilder

            menu_builder = MenuBuilder(site)
            navigation = menu_builder.build_menus(pages_to_render)

        engine = getattr(site, "_template_engine", None)
        if engine is None:
            engine = TemplateEngine(site)
            site._template_engine = engine

        html = engine.render_page(page, navigation=navigation)

        output_path = page.url.lstrip("/")
        if not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        return RenderedPage(
            page=page,
            html=html,
            output_path=Path(output_path),
        )

    def write_page(rendered: RenderedPage) -> None:
        """Write rendered page to disk."""
        write_output(site, rendered)

    return (
        Pipeline("bengal-render")
        .source("pages", get_pages)
        .map("render", render_page)
        .for_each("write", write_page)
    )


def _discover_content_files(content_dir: Path) -> list[Path]:
    """
    Discover all content files in directory.

    Args:
        content_dir: Root content directory

    Returns:
        List of markdown file paths
    """
    files: list[Path] = []
    seen_inodes: set[int] = set()

    def walk(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            # Skip hidden (except _index.md)
            if entry.name.startswith("."):
                continue
            if entry.name.startswith("_") and entry.name != "_index.md":
                continue

            # Symlink loop detection
            if entry.is_symlink():
                try:
                    inode = entry.stat().st_ino
                    if inode in seen_inodes:
                        continue
                    seen_inodes.add(inode)
                except OSError:
                    continue

            if entry.is_dir():
                walk(entry)
            elif entry.is_file() and entry.suffix in (".md", ".markdown"):
                files.append(entry)

    walk(content_dir)
    return files
