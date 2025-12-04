"""
Postprocessing streams for generating sitemap, RSS, search index, etc.

This module provides stream-based postprocessing that replaces
PostprocessOrchestrator with a declarative, reactive approach.

Flow:
    rendered_pages → generate_sitemap → sitemap.xml
    rendered_pages → generate_rss → feed.xml
    rendered_pages → generate_output_formats → index.json, llm-full.txt
    rendered_pages → generate_special_pages → 404.html, robots.txt
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.pipeline.bengal_streams import RenderedPage
from bengal.pipeline.core import Stream
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_postprocess_streams(
    rendered_pages_stream: Stream[RenderedPage],
    site: Site,
    *,
    parallel: bool = True,
    incremental: bool = False,
) -> Stream[RenderedPage]:
    """
    Create streams that generate postprocessing outputs (sitemap, RSS, etc.).

    This stream:
    1. Collects all rendered pages
    2. Generates postprocessing outputs (sitemap, RSS, output formats, special pages)
    3. Returns rendered pages unchanged (postprocessing is side-effect)

    Args:
        rendered_pages_stream: Stream of RenderedPage objects
        site: Site instance
        parallel: Whether to run postprocessing tasks in parallel
        incremental: Whether this is an incremental build

    Returns:
        Stream emitting same rendered pages (postprocessing done as side-effect)

    Example:
        >>> rendered_stream = Stream.from_iterable(rendered_pages)
        >>> postprocess_stream = create_postprocess_streams(rendered_stream, site)
        >>> # After iterating, postprocessing outputs are generated
        >>> list(postprocess_stream.iterate())
    """
    # Collect all rendered pages first (barrier operation)
    collected_pages = rendered_pages_stream.collect(name="collect_rendered_pages")

    # Generate postprocessing outputs and return pages unchanged
    def run_postprocessing(rendered_pages: list[RenderedPage]) -> list[RenderedPage]:
        """
        Run postprocessing tasks.

        This function:
        1. Generates special pages (404, etc.)
        2. Generates output formats (JSON, TXT, LLM-friendly)
        3. Generates sitemap (if enabled, full builds only)
        4. Generates RSS (if enabled, full builds only)
        5. Generates redirects (if enabled, full builds only)

        Args:
            rendered_pages: List of all rendered pages

        Returns:
            Same list of rendered pages (postprocessing is side-effect)
        """
        # Run postprocessing tasks
        _run_postprocessing_tasks(site, parallel=parallel, incremental=incremental)

        return rendered_pages

    # Run postprocessing and flatten back to individual pages
    processed_stream = collected_pages.map(run_postprocessing, name="run_postprocessing")

    # Flatten back to individual pages
    flattened_stream = processed_stream.flat_map(
        lambda pages: iter(pages), name="flatten_postprocess_pages"
    )

    return flattened_stream


def _run_postprocessing_tasks(
    site: Site, *, parallel: bool = True, incremental: bool = False
) -> None:
    """
    Run all postprocessing tasks.

    Args:
        site: Site instance
        parallel: Whether to run tasks in parallel
        incremental: Whether this is an incremental build
    """
    # Collect enabled tasks
    tasks = []

    # Always generate special pages (404, etc.) - important for deployment
    tasks.append(("special pages", lambda: _generate_special_pages(site)))

    # CRITICAL: Always generate output formats (index.json, llm-full.txt)
    # These are essential for search functionality and must reflect current site state
    output_formats_config = site.config.get("output_formats", {})
    if output_formats_config.get("enabled", True):
        # Build graph first if we want to include graph data in page JSON
        graph_data = None
        if output_formats_config.get("options", {}).get("include_graph_connections", True):
            graph_data = _build_graph_data(site)
        tasks.append(("output formats", lambda: _generate_output_formats(site, graph_data)))

    # OPTIMIZATION: For incremental builds with small changes, skip some postprocessing
    if not incremental:
        # Full build: run all tasks
        if site.config.get("generate_sitemap", True):
            tasks.append(("sitemap", lambda: _generate_sitemap(site)))

        if site.config.get("generate_rss", True):
            tasks.append(("rss", lambda: _generate_rss(site)))

        redirects_config = site.config.get("redirects", {})
        if redirects_config.get("generate_html", True):
            tasks.append(("redirects", lambda: _generate_redirects(site)))
    else:
        # Incremental: only regenerate sitemap/RSS/validation if explicitly requested
        logger.info(
            "postprocessing_incremental",
            reason="skipping_sitemap_rss_validation_for_speed",
        )

    if not tasks:
        return

    # Run in parallel if enabled and multiple tasks
    if parallel and len(tasks) > 1:
        _run_parallel(tasks)
    else:
        _run_sequential(tasks)


def _run_sequential(tasks: list[tuple[str, callable]]) -> None:
    """
    Run postprocessing tasks sequentially.

    Args:
        tasks: List of (task_name, task_function) tuples
    """
    for task_name, task_fn in tasks:
        try:
            task_fn()
        except Exception as e:
            logger.error("postprocess_task_failed", task=task_name, error=str(e))


def _run_parallel(tasks: list[tuple[str, callable]]) -> None:
    """
    Run postprocessing tasks in parallel.

    Args:
        tasks: List of (task_name, task_function) tuples
    """
    import concurrent.futures

    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(task_fn): name for name, task_fn in tasks}

        for future in concurrent.futures.as_completed(futures):
            task_name = futures[future]
            try:
                future.result()
            except Exception as e:
                error_msg = str(e)
                errors.append((task_name, error_msg))
                logger.error("postprocess_task_failed", task=task_name, error=error_msg)

    # Report errors
    if errors:
        logger.warning(
            "postprocessing_errors",
            error_count=len(errors),
            tasks=[name for name, _ in errors],
        )


def _generate_special_pages(site: Site) -> None:
    """
    Generate special pages like 404.

    Args:
        site: Site instance
    """
    from bengal.postprocess.special_pages import SpecialPagesGenerator

    generator = SpecialPagesGenerator(site)
    generator.generate()


def _generate_sitemap(site: Site) -> None:
    """
    Generate sitemap.xml.

    Args:
        site: Site instance
    """
    from bengal.postprocess.sitemap import SitemapGenerator

    generator = SitemapGenerator(site)
    generator.generate()


def _generate_rss(site: Site) -> None:
    """
    Generate RSS feed.

    Args:
        site: Site instance
    """
    from bengal.postprocess.rss import RSSGenerator

    generator = RSSGenerator(site)
    generator.generate()


def _generate_redirects(site: Site) -> None:
    """
    Generate redirect pages for page aliases.

    Args:
        site: Site instance
    """
    from bengal.postprocess.redirects import RedirectGenerator

    generator = RedirectGenerator(site)
    generator.generate()


def _build_graph_data(site: Site) -> dict | None:
    """
    Build knowledge graph and return graph data for inclusion in page JSON.

    Args:
        site: Site instance

    Returns:
        Graph data dictionary or None if graph building fails or is disabled
    """
    try:
        from bengal.analysis.graph_visualizer import GraphVisualizer
        from bengal.analysis.knowledge_graph import KnowledgeGraph
        from bengal.config.defaults import is_feature_enabled

        # Check if graph is enabled (handles both bool and dict)
        if not is_feature_enabled(site.config, "graph"):
            return None

        # Build knowledge graph
        logger.debug("building_knowledge_graph_for_output_formats")
        graph = KnowledgeGraph(site)
        graph.build()

        # Generate graph data
        visualizer = GraphVisualizer(site, graph)
        return visualizer.generate_graph_data()
    except Exception as e:
        logger.warning(
            "graph_build_failed_for_output_formats",
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def _generate_output_formats(site: Site, graph_data: dict | None = None) -> None:
    """
    Generate custom output formats like JSON, plain text.

    Args:
        site: Site instance
        graph_data: Optional pre-computed graph data to include in page JSON
    """
    from bengal.postprocess.output_formats import OutputFormatsGenerator

    config = site.config.get("output_formats", {})
    generator = OutputFormatsGenerator(site, config, graph_data=graph_data)
    generator.generate()
