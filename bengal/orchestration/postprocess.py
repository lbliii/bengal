"""
Post-processing orchestration for Bengal SSG.

Handles post-build tasks like sitemap generation, RSS feeds, and link validation.
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats import OutputFormatsGenerator
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
    Handles post-processing tasks.

    Responsibilities:
        - Sitemap generation
        - RSS feed generation
        - Link validation
        - Parallel/sequential execution of tasks
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
        progress_manager=None,
        build_context=None,
        incremental: bool = False,
    ) -> None:
        """
        Perform post-processing tasks (sitemap, RSS, output formats, link validation, etc.).

        Args:
            parallel: Whether to run tasks in parallel
            progress_manager: Live progress manager (optional)
            incremental: Whether this is an incremental build (can skip some tasks)
        """
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
            if reporter:
                reporter.log("\n🔧 Post-processing:")
            else:
                print("\n🔧 Post-processing:")

        # Collect enabled tasks
        tasks = []

        # Always generate special pages (404, etc.) - important for deployment
        tasks.append(("special pages", self._generate_special_pages))

        # CRITICAL: Always generate output formats (index.json, llm-full.txt)
        # These are essential for search functionality and must reflect current site state
        output_formats_config = self.site.config.get("output_formats", {})
        if output_formats_config.get("enabled", True):
            # Build graph first if we want to include graph data in page JSON
            graph_data = None
            if output_formats_config.get("options", {}).get("include_graph_connections", True):
                graph_data = self._build_graph_data()
            tasks.append(("output formats", lambda: self._generate_output_formats(graph_data)))

        # OPTIMIZATION: For incremental builds with small changes, skip some postprocessing
        # This is safe because:
        # - Sitemaps update on full builds (periodic refresh)
        # - RSS regenerated on content rebuild (not layout changes)
        # - Link validation happens in CI/full builds
        if not incremental:
            # Full build: run all tasks
            if self.site.config.get("generate_sitemap", True):
                tasks.append(("sitemap", self._generate_sitemap))

            if self.site.config.get("generate_rss", True):
                tasks.append(("rss", self._generate_rss))

            if self.site.config.get("validate_links", True):
                tasks.append(("link validation", self._validate_links))
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
        self, tasks: list[tuple[str, Callable]], progress_manager=None, reporter=None
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
                            except Exception:
                                print(f"  ✗ {task_name}: {e}")
                        else:
                            print(f"  ✗ {task_name}: {e}")

    def _run_parallel(
        self, tasks: list[tuple[str, Callable]], progress_manager=None, reporter=None
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
                    except Exception:
                        print(header)
                        for task_name, error in errors:
                            print(f"    • {task_name}: {error}")
                else:
                    print(header)
                    for task_name, error in errors:
                        print(f"    • {task_name}: {error}")

    def _generate_special_pages(self) -> None:
        """
        Generate special pages like 404 (extracted for parallel execution).

        Raises:
            Exception: If special page generation fails
        """
        generator = SpecialPagesGenerator(self.site)
        generator.generate()

    def _generate_sitemap(self) -> None:
        """
        Generate sitemap.xml (extracted for parallel execution).

        Raises:
            Exception: If sitemap generation fails
        """
        generator = SitemapGenerator(self.site)
        generator.generate()

    def _generate_rss(self) -> None:
        """
        Generate RSS feed (extracted for parallel execution).

        Raises:
            Exception: If RSS generation fails
        """
        generator = RSSGenerator(self.site)
        generator.generate()

    def _build_graph_data(self) -> dict[str, Any] | None:
        """
        Build knowledge graph and return graph data for inclusion in page JSON.

        Returns:
            Graph data dictionary or None if graph building fails or is disabled
        """
        try:
            from bengal.analysis.graph_visualizer import GraphVisualizer
            from bengal.analysis.knowledge_graph import KnowledgeGraph

            # Check if graph is enabled
            graph_config = self.site.config.get("graph", True)
            if isinstance(graph_config, dict) and not graph_config.get("enabled", True):
                return None
            if graph_config is False:
                return None

            # Build knowledge graph
            logger.debug("building_knowledge_graph_for_output_formats")
            graph = KnowledgeGraph(self.site)
            graph.build()

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

    def _generate_output_formats(self, graph_data: dict[str, Any] | None = None) -> None:
        """
        Generate custom output formats like JSON, plain text (extracted for parallel execution).

        Args:
            graph_data: Optional pre-computed graph data to include in page JSON

        Raises:
            Exception: If output format generation fails
        """
        config = self.site.config.get("output_formats", {})
        generator = OutputFormatsGenerator(self.site, config, graph_data=graph_data)
        generator.generate()

    def _validate_links(self) -> None:
        """
        Validate internal links across all pages (extracted for parallel execution).

        Checks for broken internal links and logs warnings for any found.

        Raises:
            Exception: If link validation process fails
        """
        from bengal.rendering.link_validator import LinkValidator

        validator = LinkValidator()
        broken_links = validator.validate_site(self.site)
        if broken_links:
            logger.warning("broken_links_found", count=len(broken_links))
