"""
Core rendering pipeline for Bengal SSG.

Orchestrates the parsing, AST building, templating, and output rendering phases
for individual pages. Manages thread-local parser instances for performance
and provides dependency tracking for incremental builds.

Parse and render bodies live in parse_stage.py and render_stage.py. This module
keeps RenderingPipeline as the public facade so callers and tests keep using
the same method names.

Related Modules:
- bengal.parsing: Markdown parser implementations (Patitas default)
- bengal.rendering.template_engine: Template engine for rendering (Kida default)
- bengal.rendering.renderer: Individual page rendering logic
- bengal.build.tracking: Dependency graph construction

See Also:
- bengal/rendering/pipeline/parse_stage.py: Markdown parse / TOC / plugin links
- bengal/rendering/pipeline/render_stage.py: Template render / assets / context
- bengal/rendering/pipeline/cache_checker.py: Cache operations
- bengal/rendering/pipeline/json_accumulator.py: JSON data accumulation
- bengal/rendering/pipeline/autodoc_renderer.py: Autodoc rendering

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.rendering.api_doc_enhancer import set_enhancer_for_render

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.records import ParsedPage
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.parsing.protocols import RichMarkdownParser
    from bengal.protocols import PageLike, SiteLike
    from bengal.rendering.pipeline.write_behind import WriteBehindCollector
from bengal.rendering.engines import create_engine
from bengal.rendering.page_operations import extract_links, get_prerendered_html
from bengal.rendering.pipeline.autodoc_renderer import AutodocRenderer
from bengal.rendering.pipeline.cache_checker import CacheChecker
from bengal.rendering.pipeline.json_accumulator import JsonAccumulator
from bengal.rendering.pipeline.output import (
    determine_output_path,
    determine_template,
    write_output,
)
from bengal.rendering.pipeline.parse_stage import (
    build_parsed_page,
    get_plugin_collected_links,
    parse_content,
    parse_with_context_aware_parser,
    parse_with_legacy,
    preprocess_content,
    set_links_collector_for_parse,
    should_generate_toc,
)
from bengal.rendering.pipeline.profiler import RenderProfiler
from bengal.rendering.pipeline.profiler import is_enabled as _profiling_enabled
from bengal.rendering.pipeline.render_stage import (
    accumulate_asset_deps,
    build_variable_context,
    enhance_api_docs,
    render_and_write,
)
from bengal.rendering.pipeline.thread_local import get_thread_parser
from bengal.rendering.pipeline.toc import TOC_EXTRACTION_VERSION
from bengal.rendering.pipeline.unified_transform import (
    HybridHTMLTransformer,
)
from bengal.rendering.renderer import Renderer
from bengal.utils.observability.logger import get_logger, truncate_error

logger = get_logger(__name__)


class RenderingPipeline:
    """
    Coordinates the entire rendering process for content pages.

    Orchestrates the complete rendering pipeline from markdown parsing through
    template rendering to final HTML output. Manages thread-local parser instances
    for performance and integrates with dependency tracking for incremental builds.

    Creation:
        Direct instantiation: RenderingPipeline(site, ...)
            - Created by RenderOrchestrator for page rendering
            - One instance per worker thread (thread-local)
            - Requires Site instance with config

    Attributes:
        site: Site instance with config and xref_index
        parser: Thread-local markdown parser (cached per thread)
        build_cache: Optional BuildCache for direct cache access
        quiet: Whether to suppress per-page output
        build_stats: Optional BuildStats for error collection

    Pipeline Stages:
        1. Parse source content (Markdown, etc.)
        2. Build Abstract Syntax Tree (AST)
        3. Apply templates (Kida by default)
        4. Render output (HTML)
        5. Write to output directory

    Relationships:
        - Uses: TemplateEngine for template rendering
        - Uses: Renderer for individual page rendering
        - Uses: EffectTracer for dependency tracking (via BuildEffectTracer)
        - Used by: RenderOrchestrator for page rendering

    Thread Safety:
        Thread-safe. Uses thread-local parser instances. Each thread should
        have its own RenderingPipeline instance.

    Examples:
        pipeline = RenderingPipeline(site)
        pipeline.render_page(page)

    """

    def __init__(
        self,
        site: Site,
        quiet: bool = False,
        build_stats: BuildStats | None = None,
        build_context: BuildContext | None = None,
        output_collector: Any | None = None,
        changed_sources: set[Path] | None = None,
        block_cache: Any | None = None,
        highlight_cache: Any | None = None,
        write_behind: WriteBehindCollector | None = None,
        build_cache: BuildCache | None = None,
        api_doc_enhancer: Any | None = None,
    ) -> None:
        """
        Initialize the rendering pipeline.

        Parser Selection:
            Reads from config in this order:
            1. config['markdown_engine'] (legacy)
            2. config['markdown']['parser'] (preferred)
            3. Default: 'patitas' (Bengal's native parser)

        Parser Caching:
            Uses thread-local caching via get_thread_parser().
            Creates ONE parser per worker thread, cached for reuse.

        Args:
            site: Site instance with config and xref_index
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings
            build_context: Optional BuildContext for dependency injection
            output_collector: Explicit collector for hot reload. When build_context is
                also provided, this overrides build_context.output_collector.
            write_behind: Optional WriteBehindCollector for async I/O (RFC: rfc-path-to-200-pgs)
            build_cache: Optional BuildCache for direct cache access.
        """
        self.site = site

        # Auto-enable directive cache for versioned sites (3-5x speedup on repeated directives)
        from bengal.cache.directive_cache import configure_for_site

        configure_for_site(site)

        # Get markdown engine from config (default: patitas)
        markdown_engine = site.config.get("markdown_engine")
        if not markdown_engine:
            markdown_config = site.config.get("markdown", {})
            markdown_engine = markdown_config.get("parser", "patitas")

        # Allow injection of parser via BuildContext for tests/experiments
        injected_parser = getattr(build_context, "markdown_parser", None) if build_context else None

        # Use thread-local parser to avoid re-initialization overhead
        self.parser = injected_parser or get_thread_parser(markdown_engine)

        # Direct cache access
        self.build_cache = build_cache

        # Enable cross-references if xref_index is available
        if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
            # Pass version_config for cross-version linking support [[v2:path]]
            version_config = getattr(site, "version_config", None)

            # Cross-version link tracking now handled by EffectTracer via
            # record_extra_dependency() - no explicit tracker callback needed.
            cross_version_tracker = None

            # Create external reference resolver for [[ext:project:target]] syntax
            # See: plan/rfc-external-references.md
            external_ref_resolver = None
            external_refs_config = site.config.get("external_refs", {})
            if external_refs_config and external_refs_config.get("enabled", True):
                from bengal.rendering.external_refs import ExternalRefResolver

                external_ref_resolver = ExternalRefResolver(site.config)
                # Accumulate resolvers from all worker threads so health checks
                # see unresolved refs from every thread, not just the last one.
                # List is pre-initialized by the orchestrator before thread dispatch;
                # fallback here handles direct RenderingPipeline use (tests, CLI).
                if not hasattr(site, "_external_ref_resolvers"):
                    site._external_ref_resolvers = []
                import _thread
                import threading

                lock = getattr(site, "_external_ref_resolvers_lock", None)
                if not isinstance(lock, _thread.LockType):
                    site._external_ref_resolvers_lock = lock = threading.Lock()
                with lock:
                    site._external_ref_resolvers.append(external_ref_resolver)
                    site.external_ref_resolver = external_ref_resolver

            rich_parser = cast("RichMarkdownParser", self.parser)
            rich_parser.enable_cross_references(
                site.xref_index, version_config, cross_version_tracker, external_ref_resolver
            )
        self.quiet = quiet
        self.build_stats = build_stats

        # Allow injection of TemplateEngine via BuildContext
        injected_engine = getattr(build_context, "template_engine", None) if build_context else None
        if injected_engine:
            self.template_engine = injected_engine
        else:
            profile_templates = (
                getattr(build_context, "profile_templates", False) if build_context else False
            )
            self.template_engine = create_engine(site, profile=profile_templates)

        self.renderer = Renderer(
            self.template_engine,
            build_stats=build_stats,
            block_cache=block_cache,
            build_context=build_context,
        )
        self.build_context = build_context
        self.changed_sources = {Path(p) for p in (changed_sources or set())}
        self._highlight_cache = highlight_cache
        self._compare_existing_output = bool(
            getattr(build_context, "incremental", True) if build_context else True
        )

        # Extract output collector: explicit param > build_context (hot reload tracking)
        self._output_collector = output_collector or (
            getattr(build_context, "output_collector", None) if build_context else None
        )

        # Warning emitted once at orchestrator level (RenderOrchestrator._render_parallel)
        # when output_collector is missing; no per-pipeline warning to avoid N duplicates

        # Write-behind collector for async I/O (RFC: rfc-path-to-200-pgs Phase III)
        # Use explicit parameter, or get from BuildContext if available
        # NOTE: Must be computed before helper modules that need it (cache_checker, etc.)
        self._write_behind = write_behind or (
            getattr(build_context, "write_behind", None) if build_context else None
        )

        # Initialize helper modules (composition)
        self._cache_checker = CacheChecker(
            site=site,
            renderer=self.renderer,
            build_stats=build_stats,
            output_collector=self._output_collector,
            write_behind=self._write_behind,
            build_cache=self.build_cache,
            parser=self.parser,
            compare_existing_output=self._compare_existing_output,
        )
        self._json_accumulator = JsonAccumulator(site, build_context)
        self._autodoc_renderer = AutodocRenderer(
            site=site,
            template_engine=self.template_engine,
            renderer=self.renderer,
            output_collector=self._output_collector,
            build_stats=build_stats,
            write_behind=self._write_behind,
            build_cache=self.build_cache,
            compare_existing_output=self._compare_existing_output,
        )

        # PERF: Unified HTML transformer - single instance reused across all pages, ~27% faster than separate transforms
        self._html_transformer = HybridHTMLTransformer(baseurl=getattr(site, "baseurl", "") or "")

        # PERF: Cache build config flags to avoid repeated dict lookups per page
        # These flags are immutable during a build, so caching is safe.
        build_cfg = site.config.get("build", {}) or {}
        self._fast_writes = build_cfg.get("fast_writes", False)
        # PERF: Lazily-initialized reverse manifest map (fingerprinted_path -> logical_path).
        # Built at most once per pipeline instance (one per worker thread) rather than
        # once per cache-hit page, eliminating repeated O(manifest) dict construction.
        self._manifest_reverse: dict[str, str] | None = None
        self._manifest_reverse_built: bool = False
        self._fast_mode = build_cfg.get("fast_mode", False)
        self._content_hash_in_html = build_cfg.get("content_hash_in_html", True)

        # Cache per-pipeline helpers (one pipeline per worker thread).
        # Prefer: constructor param > build_context.api_doc_enhancer > get_enhancer()
        try:
            from bengal.rendering.api_doc_enhancer import get_enhancer

            injected = api_doc_enhancer or (
                build_context.api_doc_enhancer if build_context else None
            )
            self._api_doc_enhancer: Any | None = injected or get_enhancer()
        except Exception as e:
            logger.debug("api_doc_enhancer_init_failed", error=str(e))
            self._api_doc_enhancer = None

    def process_page(self, page: PageLike) -> None:
        """
        Process a single page through the entire rendering pipeline.

        Executes all rendering stages: parsing, AST building, template rendering,
        and output writing. Uses cached parsed content when available.

        Virtual pages (e.g., autodoc API pages) bypass markdown parsing and use
        pre-rendered HTML directly.

        Data File Tracking:
            Sets the dependency tracker in ContextVar so that template access
            to site.data.X is automatically tracked. This enables incremental
            builds to rebuild pages when data files change.

            RFC: rfc-incremental-build-dependency-gaps (Phase 1)

        Args:
            page: Page object to process. Must have source_path set.
        """
        # Clear per-render get_page() cache at start of each page render.
        from bengal.rendering.template_functions.get_page import clear_get_page_cache

        clear_get_page_cache()

        # Set enhancer in context so get_page() can use it during template rendering
        set_enhancer_for_render(self._api_doc_enhancer)
        try:
            self._process_page_impl(page)
        finally:
            set_enhancer_for_render(None)

    def _process_page_impl(self, page: PageLike) -> None:
        """Implementation of page processing (called within tracker context)."""
        _prof = RenderProfiler.get() if _profiling_enabled() else None

        # Handle virtual pages (autodoc, etc.)
        # - Pages with pre-rendered HTML (truthy or empty string)
        # - Autodoc pages that defer rendering until navigation is available
        prerendered = get_prerendered_html(page)
        is_autodoc = page.metadata.get("is_autodoc")
        if getattr(page, "virtual", False) and (prerendered is not None or is_autodoc):
            if is_autodoc:
                # Optimized autodoc path: try rendered cache first
                template = page.metadata.get("_autodoc_template", "autodoc/python/module")
                if not self._cache_checker.should_bypass_cache(
                    page, self.changed_sources
                ) and self._cache_checker.try_rendered_cache(page, template):
                    # Cache hit - skip extraction and rendering
                    self._json_accumulator.accumulate_unified_page_data(page)
                    self._accumulate_asset_deps(page)
                    if _prof:
                        _prof.record("cache_hit_rendered", 0)
                        _prof.record_page()
                    return

            self._autodoc_renderer.process_virtual_page(page)
            # Accumulate unified page data for virtual pages (JSON + search index)
            self._json_accumulator.accumulate_unified_page_data(page)
            # Inline asset extraction for virtual pages
            self._accumulate_asset_deps(page)

            # Cache the rendered output for next time
            if is_autodoc:
                template = page.metadata.get("_autodoc_template", "autodoc/python/module")
                self._cache_checker.cache_rendered_output(page, template)
            if _prof:
                _prof.record_page()
            return

        if not page.output_path:
            page.output_path = determine_output_path(page, self.site)

        plan = self.build_context.build_plan if self.build_context is not None else None
        template = determine_template(page, build_plan=plan)
        parser_version = self._get_parser_version()

        # Determine cache bypass using centralized helper
        if _prof:
            with _prof.step("cache_check"):
                skip_cache = self._cache_checker.should_bypass_cache(page, self.changed_sources)
        else:
            skip_cache = self._cache_checker.should_bypass_cache(page, self.changed_sources)

        # Track cache bypass statistics
        if self.build_stats:
            if skip_cache:
                self.build_stats.cache_bypass_hits += 1
            else:
                self.build_stats.cache_bypass_misses += 1

        if not skip_cache and self._cache_checker.try_rendered_cache(page, template):
            # Inline asset extraction for cache hits
            self._accumulate_asset_deps(page)
            if _prof:
                _prof.record("cache_hit_rendered", 0)
                _prof.record_page()
            return

        if not skip_cache and self._cache_checker.try_parsed_cache(page, template, parser_version):
            # Inline asset extraction for parsed cache hits
            self._accumulate_asset_deps(page)
            if _prof:
                _prof.record("cache_hit_parsed", 0)
                _prof.record_page()
            return

        if _prof:
            _prof.record("full_render", 0)

        # Full pipeline execution
        # Skip parsing if already done (e.g., by parsing phase before snapshot)
        # This avoids redundant parsing when using WaveScheduler with pre-parsed content
        if not page.html_content:
            if self.build_stats:
                self.build_stats.parsed_cache_misses += 1
            self._set_links_collector_for_parse()
            if _prof:
                with _prof.step("parse_markdown"):
                    self._parse_content(page)
            else:
                self._parse_content(page)

        if _prof:
            with _prof.step("api_enhance"):
                self._enhance_api_docs(page)
        else:
            self._enhance_api_docs(page)

        # Extract links: use plugin-collected wikilinks when available, merge with markdown/HTML
        try:
            plugin_links = self._get_plugin_collected_links()
            if _prof:
                with _prof.step("link_extract"):
                    extract_links(page, plugin_links=plugin_links)
            else:
                extract_links(page, plugin_links=plugin_links)
        except Exception as e:
            # Log at warning level so users are aware of extraction issues
            # In strict mode, this could indicate malformed content that needs attention
            logger.warning(
                "link_extraction_failed",
                page=str(page.source_path),
                error=truncate_error(e),
                error_type=type(e).__name__,
                suggestion="Check page content for malformed HTML or encoding issues",
            )
            # Track in build stats if available (helps surface in build summary)
            if self.build_stats:
                self.build_stats.add_warning(
                    str(page.source_path),
                    f"Link extraction failed: {truncate_error(e)}",
                    "link_extraction",
                )

        # Build immutable ParsedPage record (Epic: Immutable Page Pipeline, Sprint 1)
        parsed_page = self._build_parsed_page(page)

        if _prof:
            with _prof.step("cache_parsed"):
                self._cache_checker.cache_parsed_content(
                    page, template, parser_version, parsed_page=parsed_page
                )
        else:
            self._cache_checker.cache_parsed_content(
                page, template, parser_version, parsed_page=parsed_page
            )

        self._render_and_write(page, template, _prof=_prof, parsed_page=parsed_page)
        if _prof:
            _prof.record_page()

    def _set_links_collector_for_parse(self) -> None:
        """Set links collector on xref plugin before parse (Patitas only)."""
        set_links_collector_for_parse(self)

    def _get_plugin_collected_links(self) -> list[str]:
        """Get and clear links collected by xref plugin during parse (Patitas only)."""
        return get_plugin_collected_links(self)

    def _parse_content(self, page: PageLike) -> None:
        """Parse page content through markdown parser."""
        parse_content(self, page)

    def _should_generate_toc(self, page: PageLike) -> bool:
        """Determine if TOC should be generated for this page."""
        return should_generate_toc(page)

    def _parse_with_context_aware_parser(
        self, page: PageLike, need_toc: bool
    ) -> tuple[ParsedPage, list[str]]:
        """Parse content using a context-aware parser (Mistune, Patitas)."""
        return parse_with_context_aware_parser(self, page, need_toc)

    def _parse_with_legacy(self, page: PageLike, need_toc: bool) -> ParsedPage:
        """Parse content using legacy python-markdown parser."""
        return parse_with_legacy(self, page, need_toc)

    def _enhance_api_docs(self, page: PageLike) -> None:
        """Enhance API documentation with badges."""
        enhance_api_docs(self, page)

    def _build_parsed_page(self, page: PageLike) -> ParsedPage:
        """Construct a ParsedPage from current page state after parsing."""
        return build_parsed_page(page)

    def _render_and_write(
        self,
        page: PageLike,
        template: str,
        _prof: RenderProfiler | None = None,
        parsed_page: ParsedPage | None = None,
    ) -> None:
        """Render template and write output."""
        render_and_write(self, page, template, _prof=_prof, parsed_page=parsed_page)

    def _accumulate_asset_deps(
        self,
        page: PageLike,
        tracked_assets: set[str] | None = None,
        rendered_html: str | None = None,
    ) -> None:
        """Accumulate asset dependencies during rendering."""
        accumulate_asset_deps(self, page, tracked_assets, rendered_html)

    def _build_variable_context(self, page: PageLike) -> dict[str, Any]:
        """Build variable context for {{ variable }} substitution in markdown."""
        return build_variable_context(self, page)

    def _get_parser_version(self) -> str:
        """Get parser version string for cache validation."""
        parser_name = type(self.parser).__name__

        match parser_name:
            case "PythonMarkdownParser":
                try:
                    import markdown

                    base_version = f"markdown-{markdown.__version__}"
                except ImportError, AttributeError:
                    base_version = "markdown-unknown"
            case "PatitasParser":
                import patitas

                base_version = f"patitas-{patitas.__version__}"
            case _:
                base_version = f"{parser_name}-unknown"

        return f"{base_version}-toc{TOC_EXTRACTION_VERSION}"

    def _write_output(self, page: PageLike) -> None:
        """Write rendered page to output directory (backward compatibility wrapper)."""
        write_output(
            page,
            cast("SiteLike", self.site),
            collector=self._output_collector,
            build_cache=self.build_cache,
            compare_existing_output=self._compare_existing_output,
        )

    def _preprocess_content(self, page: PageLike) -> str:
        """Pre-process page content through configured template engine (legacy parser only)."""
        return preprocess_content(self, page)
