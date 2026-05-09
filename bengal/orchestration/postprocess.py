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

from threading import Lock
from typing import TYPE_CHECKING

from bengal.orchestration.utils.errors import is_shutdown_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.core.output import OutputCollector
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.types import ProgressManagerProtocol
    from bengal.protocols import ProgressReporter
    from bengal.utils.observability.cli_progress import LiveProgressManager

from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.redirects import RedirectGenerator
from bengal.postprocess.robots_txt import RobotsTxtGenerator
from bengal.postprocess.rss import AtomGenerator, RSSGenerator
from bengal.postprocess.sitemap import SitemapGenerator
from bengal.postprocess.social_cards import (
    SOCIAL_CARD_FINGERPRINT_PREFIX,
    SocialCardGenerator,
    parse_social_cards_config,
)
from bengal.postprocess.special_pages import SpecialPagesGenerator
from bengal.postprocess.xref_index import XRefIndexGenerator, should_export_xref_index
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site

# Thread-safe output lock for parallel processing
_print_lock = Lock()


def _emit_postprocess_line(message: str) -> None:
    """Route post-processing fallback messages through shared CLI output."""
    from bengal.output import get_cli_output

    get_cli_output().raw(message, stream="stderr", level=None)


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
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        build_context: BuildContext | None = None,
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
            from bengal.output import get_cli_output

            cli = get_cli_output()
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

        # OPTIMIZATION: For incremental builds, skip expensive post-processing
        # except for sitemap which must always be regenerated for correctness.
        #
        # RFC: rfc-incremental-build-dependency-gaps (Phase 3)
        # Sitemap is always regenerated because:
        # - It's fast (~10ms for 1K pages)
        # - New pages must appear in sitemap for SEO
        # - Correctness matters more than the minimal time savings
        #
        # Skip these on incremental:
        # - Social cards: Only needed for production (OG images don't change during dev)
        # - RSS: Regenerated on content rebuild (not layout changes)
        # - Redirects: Regenerated on full builds (aliases rarely change)

        # Sitemap: Always regenerate for correctness (fast: ~10ms for 1K pages)
        if self.site.config.get("generate_sitemap", True):
            tasks.append(("sitemap", self._generate_sitemap))

        # robots.txt with Content-Signal directives (fast, always regenerated)
        cs_config = self.site.config.get("content_signals", {})
        if cs_config.get("enabled", True):
            tasks.append(("robots.txt", self._generate_robots_txt))

        social_cards_task = None

        if not incremental:
            # Full build: run all expensive tasks

            # Generate social cards (OG images) - EXPENSIVE (~30ms per card)
            # Only on full builds, not dev server reloads
            social_cards_config = parse_social_cards_config(self.site.config)
            if social_cards_config.enabled:
                # Run after parallel postprocess tasks so social-card fingerprints
                # never mutate the build-cache fingerprint map concurrently with
                # output-format generation on free-threaded Python.
                def run_social_cards() -> None:
                    self._generate_social_cards(build_context)

                social_cards_task = run_social_cards

            if self.site.config.get("generate_rss", True):
                tasks.append(("rss", self._generate_rss))
            if self.site.config.get("generate_atom", False):
                tasks.append(("atom", self._generate_atom))

            redirects_config = self.site.config.get("redirects", {})
            if redirects_config.get("generate_html", True):
                tasks.append(("redirects", self._generate_redirects))

            # Generate xref.json for cross-project linking (RFC: External References)
            if should_export_xref_index(self.site):
                tasks.append(("xref index", self._generate_xref_index))
        else:
            # Incremental: skip expensive tasks for dev server responsiveness
            # Note: Output formats and sitemap ARE still generated (above)
            logger.info(
                "postprocessing_incremental",
                reason="skipping_social_cards_rss_for_speed",
                sitemap="always_generated",
            )

        if tasks:
            # Run in parallel if enabled and multiple tasks
            # Threshold of 2 tasks (always parallel if multiple tasks since they're independent)
            if parallel and len(tasks) > 1:
                self._run_parallel(tasks, progress_manager, reporter)
            else:
                self._run_sequential(tasks, progress_manager, reporter)

        if social_cards_task is not None:
            self._run_sequential([("social cards", social_cards_task)], progress_manager, reporter)

    def _run_sequential(
        self,
        tasks: list[tuple[str, Callable[[], None]]],
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        reporter: ProgressReporter | None = None,
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
                from bengal.errors import (
                    BengalError,
                    ErrorCode,
                    ErrorContext,
                    enrich_error,
                    record_error,
                )

                # Enrich error with context for better debugging
                context = ErrorContext(
                    operation=f"post-processing task: {task_name}",
                    suggestion=f"Check {task_name} configuration and file permissions",
                    original_error=e,
                )
                enriched = enrich_error(e, context, BengalError)

                # Log with error code
                logger.error(
                    "postprocess_task_failed",
                    task=task_name,
                    error=str(enriched),
                    error_type=type(e).__name__,
                    error_code=ErrorCode.B008.value,
                    suggestion=f"Check {task_name} configuration and file permissions",
                )

                # Record in error session for pattern detection
                record_error(enriched, file_path=f"postprocess:{task_name}")

                # Also print for user visibility
                if not progress_manager:
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
                                    action="falling_back_to_cli_output",
                                )
                                _emit_postprocess_line(f"  ✗ {task_name}: {e}")
                        else:
                            _emit_postprocess_line(f"  ✗ {task_name}: {e}")

    def _run_parallel(
        self,
        tasks: list[tuple[str, Callable[[], None]]],
        progress_manager: LiveProgressManager | ProgressManagerProtocol | None = None,
        reporter: ProgressReporter | None = None,
    ) -> None:
        """
        Run post-processing tasks in parallel.

        Args:
            tasks: List of (task_name, task_function) tuples
            progress_manager: Live progress manager (optional)
        """
        errors = []
        completed_count = 0

        def _run_task(name_fn_tuple: tuple[str, Callable[[], None]]) -> str:
            name, fn = name_fn_tuple
            try:
                fn()
            except Exception as e:
                e.__task_name__ = name  # type: ignore[attr-defined]
                raise
            return name

        from bengal.utils.concurrency.work_scope import WorkScope

        with WorkScope("PostProcess", max_workers=len(tasks)) as scope:
            results = scope.map(_run_task, tasks)

        for r in results:
            if r.ok:
                task_name = r.value
                if progress_manager:
                    completed_count += 1
                    progress_manager.update_phase(
                        "postprocess", current=completed_count, current_item=task_name
                    )
            else:
                e = r.error
                if is_shutdown_error(e):
                    logger.debug("postprocess_shutdown")
                    continue

                # Extract task name from the error if possible
                task_name = getattr(e, "__task_name__", "unknown")
                error_msg = str(e)
                errors.append((task_name, error_msg))

                # Import error handling utilities
                from bengal.errors import (
                    BengalError,
                    ErrorCode,
                    ErrorContext,
                    enrich_error,
                    record_error,
                )

                # Enrich error with context
                context = ErrorContext(
                    operation=f"post-processing task: {task_name}",
                    suggestion=f"Check {task_name} configuration and file permissions",
                    original_error=e,
                )
                enriched = enrich_error(e, context, BengalError)

                # Log with error code
                logger.error(
                    "postprocess_task_failed",
                    task=task_name,
                    error=str(enriched),
                    error_type=type(e).__name__,
                    error_code=ErrorCode.B008.value,
                    suggestion=f"Check {task_name} configuration and file permissions",
                )

                # Record in error session
                record_error(enriched, file_path=f"postprocess:{task_name}")

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
                            action="falling_back_to_cli_output",
                        )
                        _emit_postprocess_line(header)
                        for task_name, error in errors:
                            _emit_postprocess_line(f"    • {task_name}: {error}")
                else:
                    _emit_postprocess_line(header)
                    for task_name, error in errors:
                        _emit_postprocess_line(f"    • {task_name}: {error}")

    def _generate_special_pages(self, build_context: BuildContext | None = None) -> None:
        """
        Generate special pages like 404 (extracted for parallel execution).

        Wraps template rendering with asset_manifest_context when available so
        asset_url() in base.html resolves fingerprinted paths (Plan: asset-manifest-context-refactor).

        Args:
            build_context: Optional BuildContext with cached knowledge graph and asset_manifest_ctx

        Raises:
            Exception: If special page generation fails
        """
        from bengal.rendering.assets import asset_manifest_context

        collector = getattr(self, "_collector", None)
        generator = SpecialPagesGenerator(self.site, collector=collector)
        asset_ctx = getattr(build_context, "asset_manifest_ctx", None) if build_context else None
        if asset_ctx is not None:
            with asset_manifest_context(asset_ctx):
                generator.generate(build_context=build_context)
        else:
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

    def _generate_robots_txt(self) -> None:
        """Generate robots.txt with Content-Signal directives and manifest."""
        collector = getattr(self, "_collector", None)
        generator = RobotsTxtGenerator(self.site, collector=collector)
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

    def _generate_atom(self) -> None:
        """Generate Atom feed."""
        collector = getattr(self, "_collector", None)
        generator = AtomGenerator(self.site, collector=collector)
        generator.generate()

    def _generate_redirects(self) -> None:
        """
        Generate redirect pages for page aliases.

        Creates lightweight HTML redirect pages at each alias URL that
        redirect to the canonical page location.

        Raises:
            Exception: If redirect generation fails
        """
        collector = getattr(self, "_collector", None)
        generator = RedirectGenerator(self.site, collector=collector)
        generator.generate()

    def _generate_social_cards(self, build_context: BuildContext | None = None) -> None:
        """
        Generate social card (Open Graph) images for pages.

        Creates 1200x630px PNG images with page title, description, and
        site branding for social media preview cards.

        Raises:
            Exception: If social card generation fails
        """
        from bengal.output import get_cli_output

        social_config = parse_social_cards_config(self.site.config)

        if not social_config.enabled:
            return

        collector = getattr(self, "_collector", None)
        fingerprint_cache = None
        if build_context is not None and build_context.cache is not None:
            fingerprint_cache = {
                key: value
                for key, value in build_context.cache.output_format_fingerprints.items()
                if key.startswith(SOCIAL_CARD_FINGERPRINT_PREFIX)
            }
        generator = SocialCardGenerator(
            self.site,
            social_config,
            collector=collector,
            fingerprint_cache=fingerprint_cache,
        )
        output_dir = self.site.output_dir / social_config.output_dir

        generated, cached = generator.generate_all(self.site.pages, output_dir)
        if (
            build_context is not None
            and build_context.cache is not None
            and fingerprint_cache is not None
        ):
            build_context.cache.output_format_fingerprints.update(fingerprint_cache)

        # Log results using CLI output pattern
        cli = get_cli_output()
        if generated > 0 or cached > 0:
            cli.detail(
                f"Generated: {generated}, Cached: {cached}",
                indent=1,
                icon=cli.icons.tree_end,
            )

    def _build_graph_data(
        self, build_context: BuildContext | None = None
    ) -> dict[str, object] | None:
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
            from bengal.analysis.graph.visualizer import GraphVisualizer
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
                from bengal.analysis.graph.knowledge_graph import KnowledgeGraph

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
        graph_data: dict[str, object] | None = None,
        build_context: BuildContext | None = None,
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

    def _generate_xref_index(self) -> None:
        """
        Generate xref.json for cross-project documentation linking.

        Creates a JSON index that other Bengal sites can import to enable
        [[ext:project:target]] references to this site's content.

        Only runs on full builds (not incremental) and when export_index is enabled.

        See: plan/rfc-external-references.md

        Raises:
            Exception: If xref index generation fails
        """
        collector = getattr(self, "_collector", None)
        generator = XRefIndexGenerator(self.site, collector=collector)
        generator.generate()
