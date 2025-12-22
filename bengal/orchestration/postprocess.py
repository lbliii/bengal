"""
Post-processing orchestration for Bengal SSG.

Handles post-build tasks like sitemap generation, RSS feeds, link validation,
and special page generation. Runs after all pages are rendered and coordinates
parallel post-processing tasks.

Key Concepts:
    - Sitemap generation: XML sitemap for search engines
    - RSS feeds: RSS/Atom feed generation for blog content
    - Link validation: Broken link detection and reporting
    - Special pages: 404, robots.txt, and other generated pages
    - Output formats: JSON, TXT, LLM-friendly output generation

Related Modules:
    - bengal.postprocess.sitemap: Sitemap generation
    - bengal.postprocess.rss: RSS feed generation
    - bengal.postprocess.output_formats: Output format generators
    - bengal.health.validators: Link validation

See Also:
    - bengal/orchestration/postprocess.py:PostprocessOrchestrator for orchestration logic
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector
    from bengal.utils.build_context import BuildContext

from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.redirects import RedirectGenerator
from bengal.postprocess.rss import RSSGenerator
from bengal.postprocess.sitemap import SitemapGenerator
from bengal.postprocess.special_pages import SpecialPagesGenerator
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site

# Thread-safe output lock for parallel processing
_print_lock = Lock()


class PostprocessOrchestrator:
    """
    Orchestrates post-processing tasks after page rendering.

    Handles sitemap generation, RSS feeds, link validation, special pages,
    and output format generation. Supports parallel execution for performance
    and incremental build optimization.

    Creation:
        Direct instantiation: PostprocessOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with rendered pages and configuration

    Relationships:
        - Uses: SitemapGenerator for sitemap generation
        - Uses: RSSGenerator for RSS feed generation
        - Uses: OutputFormatsGenerator for JSON/TXT/LLM output
        - Uses: SpecialPagesGenerator for 404 and other special pages
        - Used by: BuildOrchestrator for post-processing phase

    Thread Safety:
        Thread-safe for parallel task execution. Uses thread-safe locks
        for output operations.

    Examples:
        orchestrator = PostprocessOrchestrator(site)
        orchestrator.run(parallel=True, incremental=False)
    """

    def __init__(self, site: Site):
        """
        Initialize postprocess orchestrator.

        Args:
            site: Site instance with rendered pages and configuration
        """
        self.site = site

    def run(
        self,
        parallel: bool = True,
        progress_manager: Any | None = None,
        build_context: BuildContext | Any | None = None,
        incremental: bool = False,
        collector: OutputCollector | None = None,
    ) -> None:
        """
        Perform post-processing tasks (sitemap, RSS, output formats, link validation, etc.).

        Args:
            parallel: Whether to run tasks in parallel
            progress_manager: Live progress manager (optional)
            incremental: Whether this is an incremental build (can skip some tasks)
            collector: Optional output collector for hot reload tracking
        """
        # Store collector for use in task methods
        self._collector = collector
        # Resolve from context if absent
        if (
            not progress_manager
            and build_context
            and getattr(build_context, "progress_manager", None)
        ):
            progress_manager = build_context.progress_manager
        reporter = None
        if build_context and getattr(build_context, "reporter", None):
            reporter = build_context.reporter

        if not progress_manager:
            from bengal.output import CLIOutput

            cli = CLIOutput()
            cli.section("Post-processing")

        # Collect enabled tasks
        tasks = []

        # Always generate special pages (404, etc.) - important for deployment
        tasks.append(("special pages", lambda: self._generate_special_pages(build_context)))

        # CRITICAL: Always generate output formats (index.json, llm-full.txt)
        # These are essential for search functionality and must reflect current site state
        output_formats_config = self.site.config.get("output_formats", {})
        if output_formats_config.get("enabled", True):
            # Build graph first if we want to include graph data in page JSON
            graph_data = None
            if output_formats_config.get("options", {}).get("include_graph_connections", True):
                graph_data = self._build_graph_data(build_context)
            tasks.append(
                ("output formats", lambda: self._generate_output_formats(graph_data, build_context))
            )

        # OPTIMIZATION: For incremental builds with small changes, skip some postprocessing
        # This is safe because:
        # - Sitemaps update on full builds (periodic refresh)
        # - RSS regenerated on content rebuild (not layout changes)
        # - Redirects regenerated on full builds (aliases rarely change)
        # - Link validation now runs via the health check system (LinkValidatorWrapper)
        if not incremental:
            # Full build: run all tasks
            if self.site.config.get("generate_sitemap", True):
                tasks.append(("sitemap", self._generate_sitemap))

            if self.site.config.get("generate_rss", True):
                tasks.append(("rss", self._generate_rss))

            redirects_config = self.site.config.get("redirects", {})
            if redirects_config.get("generate_html", True):
                tasks.append(("redirects", self._generate_redirects))
        else:
            # Incremental: only regenerate sitemap/RSS/validation if explicitly requested
            # (Most users don't need updated sitemaps/RSS for every content change)
            # Note: Output formats ARE still generated (see above) because search requires it
            logger.info(
                "postprocessing_incremental",
                reason="skipping_sitemap_rss_validation_for_speed",
            )

        if not tasks:
            return

        # Run in parallel if enabled and multiple tasks
        # Threshold of 2 tasks (always parallel if multiple tasks since they're independent)
        if parallel and len(tasks) > 1:
            self._run_parallel(tasks, progress_manager, reporter)
        else:
            self._run_sequential(tasks, progress_manager, reporter)

    def _run_sequential(
        self,
        tasks: list[tuple[str, Callable[[], None]]],
        progress_manager: Any | None = None,
        reporter: Any | None = None,
    ) -> None:
        """
        Run post-processing tasks sequentially.

        Args:
            tasks: List of (task_name, task_function) tuples
            progress_manager: Live progress manager (optional)
        """
        for i, (task_name, task_fn) in enumerate(tasks):
            try:
                if progress_manager:
                    progress_manager.update_phase(
                        "postprocess", current=i + 1, current_item=task_name
                    )
                task_fn()
            except Exception as e:
                if progress_manager:
                    logger.error("postprocess_task_failed", task=task_name, error=str(e))
                else:
                    with _print_lock:
                        if reporter:
                            try:
                                reporter.log(f"  ✗ {task_name}: {e}")
                            except Exception as reporter_error:
                                logger.debug(
                                    "postprocess_reporter_log_failed",
                                    task=task_name,
                                    reporter_error=str(reporter_error),
                                    error_type=type(reporter_error).__name__,
                                    action="falling_back_to_print",
                                )
                                print(f"  ✗ {task_name}: {e}")
                        else:
                            print(f"  ✗ {task_name}: {e}")

    def _run_parallel(
        self,
        tasks: list[tuple[str, Callable[[], None]]],
        progress_manager: Any | None = None,
        reporter: Any | None = None,
    ) -> None:
        """
        Run post-processing tasks in parallel.

        Args:
            tasks: List of (task_name, task_function) tuples
            progress_manager: Live progress manager (optional)
        """
        errors = []
        completed_count = 0
        lock = Lock()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(task_fn): name for name, task_fn in tasks}

            for future in concurrent.futures.as_completed(futures):
                # Get task name outside try block (dictionary lookup is fast)
                task_name = futures[future]
                try:
                    future.result()
                    if progress_manager:
                        # Minimize lock hold time - only update counter and progress
                        with lock:
                            completed_count += 1
                            progress_manager.update_phase(
                                "postprocess", current=completed_count, current_item=task_name
                            )
                except Exception as e:
                    # Error handling outside lock
                    error_msg = str(e)
                    errors.append((task_name, error_msg))
                    if progress_manager:
                        logger.error("postprocess_task_failed", task=task_name, error=error_msg)

        # Report errors
        if errors and not progress_manager:
            with _print_lock:
                header = f"  ⚠️  {len(errors)} post-processing task(s) failed:"
                if reporter:
                    try:
                        reporter.log(header)
                        for task_name, error in errors:
                            reporter.log(f"    • {task_name}: {error}")
                    except Exception as reporter_error:
                        logger.debug(
                            "postprocess_reporter_error_log_failed",
                            error_count=len(errors),
                            reporter_error=str(reporter_error),
                            error_type=type(reporter_error).__name__,
                            action="falling_back_to_print",
                        )
                        print(header)
                        for task_name, error in errors:
                            print(f"    • {task_name}: {error}")
                else:
                    print(header)
                    for task_name, error in errors:
                        print(f"    • {task_name}: {error}")

    def _generate_special_pages(self, build_context: BuildContext | Any | None = None) -> None:
        """
        Generate special pages like 404 (extracted for parallel execution).

        Args:
            build_context: Optional BuildContext with cached knowledge graph

        Raises:
            Exception: If special page generation fails
        """
        generator = SpecialPagesGenerator(self.site)
        generator.generate(build_context=build_context)

    def _generate_sitemap(self) -> None:
        """
        Generate sitemap.xml (extracted for parallel execution).

        Raises:
            Exception: If sitemap generation fails
        """
        collector = getattr(self, "_collector", None)
        generator = SitemapGenerator(self.site, collector=collector)
        generator.generate()

    def _generate_rss(self) -> None:
        """
        Generate RSS feed (extracted for parallel execution).

        Raises:
            Exception: If RSS generation fails
        """
        collector = getattr(self, "_collector", None)
        generator = RSSGenerator(self.site, collector=collector)
        generator.generate()

    def _generate_redirects(self) -> None:
        """
        Generate redirect pages for page aliases.

        Creates lightweight HTML redirect pages at each alias URL that
        redirect to the canonical page location.

        Raises:
            Exception: If redirect generation fails
        """
        generator = RedirectGenerator(self.site)
        generator.generate()

    def _build_graph_data(
        self, build_context: BuildContext | Any | None = None
    ) -> dict[str, Any] | None:
        """
        Build knowledge graph and return graph data for inclusion in page JSON.

        Uses build_context.knowledge_graph if available to avoid rebuilding
        the graph multiple times per build.

        Args:
            build_context: Optional BuildContext with cached knowledge graph

        Returns:
            Graph data dictionary or None if graph building fails or is disabled
        """
        try:
            from bengal.analysis.graph_visualizer import GraphVisualizer
            from bengal.config.defaults import is_feature_enabled

            # Check if graph is enabled (handles both bool and dict)
            if not is_feature_enabled(self.site.config, "graph"):
                return None

            # Try to get cached graph from build context first (lazy-computed artifact)
            graph = None
            if build_context is not None:
                graph = build_context.knowledge_graph

            # Fallback: build our own (for standalone usage)
            if graph is None:
                from bengal.analysis.knowledge_graph import KnowledgeGraph

                logger.debug("building_knowledge_graph_for_output_formats")
                graph = KnowledgeGraph(self.site)
                graph.build()
            else:
                logger.debug("using_cached_knowledge_graph_for_output_formats")

            # Generate graph data
            visualizer = GraphVisualizer(self.site, graph)
            return visualizer.generate_graph_data()
        except Exception as e:
            logger.warning(
                "graph_build_failed_for_output_formats",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _generate_output_formats(
        self,
        graph_data: dict[str, Any] | None = None,
        build_context: BuildContext | Any | None = None,
    ) -> None:
        """
        Generate custom output formats like JSON, plain text (extracted for parallel execution).

        Args:
            graph_data: Optional pre-computed graph data to include in page JSON
            build_context: Optional BuildContext with accumulated JSON data from rendering phase

        Raises:
            Exception: If output format generation fails
        """
        config = self.site.config.get("output_formats", {})
        generator = OutputFormatsGenerator(
            self.site, config, graph_data=graph_data, build_context=build_context
        )
        generator.generate()
