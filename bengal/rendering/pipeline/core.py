"""
Core rendering pipeline for Bengal SSG.

Orchestrates the parsing, AST building, templating, and output rendering phases
for individual pages. Manages thread-local parser instances for performance
and provides dependency tracking for incremental builds.

Key Concepts:
- Thread-local parsers: Parser instances reused per thread for performance
- AST-based processing: Content represented as AST for efficient transformation
- Template rendering: Template rendering with page context (Kida default)
- Dependency tracking: Template and asset dependency tracking

Related Modules:
- bengal.parsing: Markdown parser implementations (Patitas default)
- bengal.rendering.template_engine: Template engine for rendering (Kida default)
- bengal.rendering.renderer: Individual page rendering logic
- bengal.build.tracking: Dependency graph construction

See Also:
- bengal/rendering/pipeline/cache_checker.py: Cache operations
- bengal/rendering/pipeline/json_accumulator.py: JSON data accumulation
- bengal/rendering/pipeline/autodoc_renderer.py: Autodoc rendering

"""

from __future__ import annotations

import re
import time as _time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.core.records import ParsedPage, RenderedPage
from bengal.rendering.api_doc_enhancer import set_enhancer_for_render

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.parsing.protocols import RichMarkdownParser
    from bengal.protocols import PageLike, SiteLike
    from bengal.rendering.pipeline.write_behind import WriteBehindCollector
from bengal.errors import ErrorCode
from bengal.rendering.engines import create_engine
from bengal.rendering.page_operations import extract_links
from bengal.rendering.pipeline.autodoc_renderer import AutodocRenderer
from bengal.rendering.pipeline.cache_checker import CacheChecker
from bengal.rendering.pipeline.json_accumulator import JsonAccumulator
from bengal.rendering.pipeline.output import (
    determine_output_path,
    determine_template,
    format_html,
    write_output,
)
from bengal.rendering.pipeline.profiler import RenderProfiler
from bengal.rendering.pipeline.profiler import is_enabled as _profiling_enabled
from bengal.rendering.pipeline.thread_local import get_thread_parser
from bengal.rendering.pipeline.toc import TOC_EXTRACTION_VERSION
from bengal.rendering.pipeline.transforms import (
    escape_template_syntax_in_html,
)
from bengal.rendering.pipeline.unified_transform import (
    HybridHTMLTransformer,
)
from bengal.rendering.renderer import Renderer
from bengal.rendering.shortcodes import expand_shortcodes
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
        prerendered = getattr(page, "prerendered_html", None)
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

        template = determine_template(page)
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
        if hasattr(self.parser, "_xref_plugin") and self.parser._xref_plugin:
            self.parser._xref_plugin.set_links_collector([])

    def _get_plugin_collected_links(self) -> list[str]:
        """Get and clear links collected by xref plugin during parse (Patitas only)."""
        if hasattr(self.parser, "_xref_plugin") and self.parser._xref_plugin:
            return self.parser._xref_plugin.get_collected_links()
        return []

    def _parse_content(self, page: PageLike) -> None:
        """Parse page content through markdown parser.

        Uses deferred (parallel) syntax highlighting on Python 3.14t for
        pages with multiple code blocks. This provides 1.5-2x speedup.
        """
        from bengal.rendering.highlighting import (
            disable_deferred_highlighting,
            enable_deferred_highlighting,
            flush_deferred_highlighting,
        )

        need_toc = self._should_generate_toc(page)

        # Enable deferred highlighting for parallel batch processing (3.14t)
        enable_deferred_highlighting(cache=self._highlight_cache)
        try:
            if hasattr(self.parser, "parse_with_toc_and_context"):
                self._parse_with_context_aware_parser(page, need_toc)
            else:
                self._parse_with_legacy(page, need_toc)

            # Flush deferred highlighting: batch process all code blocks in parallel
            # This replaces <!--code:XXX--> placeholders with highlighted HTML
            # Must run BEFORE transformer so highlighter output is also escaped/transformed
            _prof_inner = RenderProfiler.get() if _profiling_enabled() else None
            if page.html_content:
                if _prof_inner:
                    with _prof_inner.step("flush_highlight"):
                        page.html_content = flush_deferred_highlighting(page.html_content)
                else:
                    page.html_content = flush_deferred_highlighting(page.html_content)

            # PERF: Unified HTML transformation (~27% faster than separate passes)
            # Handles: Jinja block escaping, .md link normalization, baseurl prefixing
            if _prof_inner:
                with _prof_inner.step("html_transform"):
                    page.html_content = self._html_transformer.transform(page.html_content or "")
            else:
                page.html_content = self._html_transformer.transform(page.html_content or "")

            # Restore any remaining escape placeholders in code block output
            # This is needed because deferred highlighting captures code BEFORE
            # restore_placeholders() runs, so {{/* */}} escapes appear as
            # BENGALESCAPED*ENDESC in the final highlighted HTML
            # fmt: off
            if hasattr(self.parser, "_var_plugin"):
                rich_parser = cast("RichMarkdownParser", self.parser)
                if rich_parser._var_plugin and rich_parser._var_plugin.escaped_placeholders:
                    page.html_content = rich_parser._var_plugin.restore_placeholders(
                        page.html_content
                    )
            # fmt: on
        finally:
            disable_deferred_highlighting()

        # Pre-compute plain_text cache
        _prof_pt = RenderProfiler.get() if _profiling_enabled() else None
        if _prof_pt:
            with _prof_pt.step("plain_text"):
                _ = page.plain_text
        else:
            _ = page.plain_text

    def _should_generate_toc(self, page: PageLike) -> bool:
        """Determine if TOC should be generated for this page."""
        if page.metadata.get("toc") is False:
            return False

        content_text = page._source or ""
        likely_has_atx = re.search(r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE)
        if likely_has_atx:
            return True

        likely_has_setext = re.search(r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE)
        return bool(likely_has_setext)

    def _parse_with_context_aware_parser(self, page: PageLike, need_toc: bool) -> None:
        """Parse content using a context-aware parser (Mistune, Patitas)."""

        def parse_markdown(s: str) -> str:
            return self.parser.parse(s, {})

        source = expand_shortcodes(
            page._source,
            self.template_engine,
            page,
            self.site,
            parse_markdown=parse_markdown,
        )

        # Protect pipes inside [[...]] cross-references from table cell splitting.
        # Must run before the markdown parser sees the source.
        if "[[" in source and hasattr(self.parser, "_xref_plugin") and self.parser._xref_plugin:
            source = self.parser._xref_plugin.protect_table_pipes(source)

        # Collect directive-generated links during rendering (cards, buttons, etc.)
        directive_links: list[str] = []

        if page.metadata.get("preprocess") is False:
            # Inject source_path and excerpt_length for cross-version dependency tracking
            # (non-context parse methods don't have access to page object)
            from bengal.config.utils import resolve_excerpt_length

            meta = page.metadata
            metadata_with_source = dict(meta or {})
            metadata_with_source["_source_path"] = page.source_path
            content_cfg = self.site.config.get("content", {}) or {}
            metadata_with_source["_excerpt_length"] = resolve_excerpt_length(page, content_cfg)

            if need_toc:
                result = self.parser.parse_with_toc(source, metadata_with_source)
                parsed_content, toc = result[0], result[1]
                result_ext = cast("tuple[str, ...]", result)
                if len(result_ext) > 2:
                    page._excerpt = result_ext[2]
                if len(result_ext) > 3:
                    page._meta_description = result_ext[3]
                parsed_content = escape_template_syntax_in_html(parsed_content)
            else:
                parsed_content = self.parser.parse(source, metadata_with_source)
                parsed_content = escape_template_syntax_in_html(parsed_content)
                toc = ""
        else:
            from bengal.config.utils import resolve_excerpt_length

            context = self._build_variable_context(page)
            context["_links_collector"] = directive_links
            md_cfg = self.site.config.get("markdown", {}) or {}
            ast_cache_cfg = md_cfg.get("ast_cache", {}) or {}
            persist_tokens = bool(ast_cache_cfg.get("persist_tokens", False))

            # Build mutable metadata for parser (CascadeView is immutable)
            meta = page.metadata
            metadata_for_parser = dict(meta or {})
            metadata_for_parser["_source_path"] = page.source_path
            content_cfg = self.site.config.get("content", {}) or {}
            metadata_for_parser["_excerpt_length"] = resolve_excerpt_length(page, content_cfg)

            # Type narrowing: check if parser supports context methods (PatitasParser)
            if hasattr(self.parser, "parse_with_toc_and_context") and hasattr(
                self.parser, "parse_with_context"
            ):
                rich_parser = cast("RichMarkdownParser", self.parser)
                if need_toc:
                    result = rich_parser.parse_with_toc_and_context(
                        source, metadata_for_parser, context
                    )
                    parsed_content, toc = result[0], result[1]
                    result_ext = cast("tuple[str, ...]", result)
                    if len(result_ext) > 2:
                        page._excerpt = result_ext[2]
                    if len(result_ext) > 3:
                        page._meta_description = result_ext[3]
                else:
                    parsed_content = rich_parser.parse_with_context(
                        source, metadata_for_parser, context
                    )
                    toc = ""
            else:
                # Fallback for parsers without context support (e.g., PythonMarkdownParser)
                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc(source, metadata_for_parser)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                else:
                    parsed_content = self.parser.parse(source, metadata_for_parser)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                    toc = ""

            # Extract AST for caching
            if hasattr(self.parser, "supports_ast") and self.parser.supports_ast and persist_tokens:
                try:
                    if hasattr(self.parser, "parse_to_document"):
                        import patitas

                        doc = self.parser.parse_to_document(source, metadata_for_parser)
                        page._ast_cache = patitas.to_dict(doc)
                    elif hasattr(self.parser, "parse_to_ast"):
                        ast_tokens = self.parser.parse_to_ast(source, metadata_for_parser)
                        page._ast_cache = ast_tokens
                except Exception as e:
                    logger.debug(
                        "ast_extraction_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )

        page.html_content = parsed_content
        page.toc = toc

        # Store directive-collected links on page for extract_links to use
        if directive_links:
            page._directive_links = directive_links

    def _parse_with_legacy(self, page: PageLike, need_toc: bool) -> None:
        """Parse content using legacy python-markdown parser."""
        content = self._preprocess_content(page)
        if need_toc and hasattr(self.parser, "parse_with_toc"):
            parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        else:
            parsed_content = self.parser.parse(content, page.metadata)
            toc = ""

        if page.metadata.get("preprocess") is False:
            parsed_content = escape_template_syntax_in_html(parsed_content)

        page.html_content = parsed_content
        page.toc = toc

    def _enhance_api_docs(self, page: PageLike) -> None:
        """Enhance API documentation with badges."""
        enhancer = self._api_doc_enhancer
        page_type = page.metadata.get("type")
        if enhancer and enhancer.should_enhance(page_type):
            page.html_content = enhancer.enhance(page.html_content or "", page_type)

    def _build_parsed_page(self, page: PageLike) -> ParsedPage:
        """Construct a ParsedPage from current page state after parsing.

        Called after _parse_content, _enhance_api_docs, and extract_links
        have finished mutating the page.  The resulting frozen record
        captures all parse-phase output for downstream rendering.
        """
        from bengal.rendering.pipeline.toc import extract_toc_structure

        toc_items = tuple(extract_toc_structure(page.toc or ""))
        links = tuple(getattr(page, "links", None) or ())

        return ParsedPage(
            html_content=page.html_content or "",
            toc=page.toc or "",
            toc_items=toc_items,
            excerpt=getattr(page, "excerpt", "") or "",
            meta_description=getattr(page, "meta_description", "")
            or getattr(page, "description", "")
            or "",
            plain_text=page.plain_text,
            word_count=getattr(page, "word_count", 0) or 0,
            reading_time=getattr(page, "reading_time", 0) or 0,
            links=links,
            ast_cache=getattr(page, "_ast_cache", None),
        )

    def _render_and_write(
        self,
        page: PageLike,
        template: str,
        _prof: RenderProfiler | None = None,
        parsed_page: ParsedPage | None = None,
    ) -> None:
        """Render template and write output.

        RFC: rfc-build-performance-optimizations Phase 2
        Uses render-time asset tracking to avoid post-render HTML parsing.

        RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)
        Optionally records effects for unified dependency tracking.

        Epic: Immutable Page Pipeline, Sprint 2
        Constructs a RenderedPage record after rendering. Passes it to
        write_output so the write phase reads from the immutable record.
        Dual-writes page.rendered_html for backward compatibility.
        """
        # Allow empty html_content - pages like home pages, section indexes, and
        # taxonomy pages may have no markdown body but should still render
        # (they're driven by template logic and frontmatter, not content)
        if page.html_content is None:
            page.html_content = ""  # Ensure it's a string, not None

        # Read source HTML from ParsedPage when available (Sprint 1: Immutable Pipeline)
        source_html = parsed_page.html_content if parsed_page else (page.html_content or "")

        # RFC: rfc-build-performance-optimizations Phase 2
        # Track assets during rendering (render-time tracking)
        # RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)
        # Record render effects if effect tracing is enabled
        from bengal.effects import BuildEffectTracer
        from bengal.rendering.asset_tracking import AssetTracker

        effect_tracer = BuildEffectTracer.get_instance()
        effect_recorder = effect_tracer.record_page_render(page, template)

        render_start = _time.perf_counter()
        rendered_html = ""

        tracker = AssetTracker()
        with tracker:
            if effect_recorder:
                with effect_recorder:
                    if _prof:
                        with _prof.step("render_content"):
                            html_content = self.renderer.render_content(source_html)
                        with _prof.step("render_template"):
                            rendered_html = self.renderer.render_page(
                                page, html_content, parsed_page=parsed_page
                            )
                        with _prof.step("format_html"):
                            rendered_html = format_html(
                                rendered_html, page, cast("SiteLike", self.site)
                            )
                    else:
                        html_content = self.renderer.render_content(source_html)
                        rendered_html = self.renderer.render_page(
                            page, html_content, parsed_page=parsed_page
                        )
                        rendered_html = format_html(
                            rendered_html, page, cast("SiteLike", self.site)
                        )
            else:
                if _prof:
                    with _prof.step("render_content"):
                        html_content = self.renderer.render_content(source_html)
                    with _prof.step("render_template"):
                        rendered_html = self.renderer.render_page(
                            page, html_content, parsed_page=parsed_page
                        )
                    with _prof.step("format_html"):
                        rendered_html = format_html(
                            rendered_html, page, cast("SiteLike", self.site)
                        )
                else:
                    html_content = self.renderer.render_content(source_html)
                    rendered_html = self.renderer.render_page(
                        page, html_content, parsed_page=parsed_page
                    )
                    rendered_html = format_html(rendered_html, page, cast("SiteLike", self.site))

        render_time_ms = (_time.perf_counter() - render_start) * 1000

        # Dual-write: set page.rendered_html for backward compatibility
        # (downstream code like json_accumulator, cache_checker still reads from page)
        page.rendered_html = rendered_html

        # Get tracked assets from render-time tracking
        tracked_assets = tracker.get_assets()

        # Sprint 2: Build immutable RenderedPage record
        rendered_page = RenderedPage(
            source_path=page.source_path,
            output_path=page.output_path,  # must be set by determine_output_path before render
            rendered_html=rendered_html,
            render_time_ms=render_time_ms,
            dependencies=frozenset(tracked_assets) if tracked_assets else frozenset(),
        )

        # Store rendered output in cache
        if _prof:
            with _prof.step("cache_rendered"):
                self._cache_checker.cache_rendered_output(page, template)
        else:
            self._cache_checker.cache_rendered_output(page, template)

        # Write output (sync or async via write-behind)
        if _prof:
            with _prof.step("write_output"):
                write_output(
                    page,
                    cast("SiteLike", self.site),
                    collector=self._output_collector,
                    write_behind=self._write_behind,
                    build_cache=self.build_cache,
                    rendered_page=rendered_page,
                )
        else:
            write_output(
                page,
                cast("SiteLike", self.site),
                collector=self._output_collector,
                write_behind=self._write_behind,
                build_cache=self.build_cache,
                rendered_page=rendered_page,
            )

        # Accumulate unified page data during rendering (JSON + search index)
        if _prof:
            with _prof.step("json_accumulate"):
                self._json_accumulator.accumulate_unified_page_data(page)
        else:
            self._json_accumulator.accumulate_unified_page_data(page)

        # RFC: rfc-build-performance-optimizations Phase 2
        # Use render-time tracked assets, fall back to HTML parsing if needed
        if _prof:
            with _prof.step("asset_deps"):
                self._accumulate_asset_deps(page, tracked_assets=tracked_assets)
        else:
            self._accumulate_asset_deps(page, tracked_assets=tracked_assets)

    def _accumulate_asset_deps(
        self, page: PageLike, tracked_assets: set[str] | None = None
    ) -> None:
        """
        Accumulate asset dependencies during rendering.

        RFC: rfc-build-performance-optimizations Phase 2
        Uses render-time tracked assets (fast) with fallback to HTML parsing (slow).

        Args:
            page: Page with rendered HTML
            tracked_assets: Assets tracked during render-time (if available)
        """
        if not self.build_context or not page.rendered_html:
            return

        assets: set[str] = set()

        # RFC: rfc-build-performance-optimizations Phase 2
        # Use render-time tracked assets if available (fast path)
        if tracked_assets:
            assets = tracked_assets
        else:
            # Fallback: parse HTML (slow, but catches assets not using filters)
            try:
                from urllib.parse import urlparse

                from bengal.rendering.asset_extractor import extract_assets_from_html
                from bengal.rendering.assets import get_asset_manifest

                raw_assets = extract_assets_from_html(page.rendered_html)

                # Normalize fingerprinted URLs back to logical paths.
                # When Kida fragment cache hits, asset_url() is not called, so
                # tracked_assets is empty and we fall back to HTML parsing.
                # HTML parsing extracts full fingerprinted URLs like
                # "http://host/assets/css/style.abc123.css", not logical paths
                # like "css/style.css". Use the manifest reverse map to recover
                # the logical path so incremental builds invalidate correctly.
                # Build reverse map once per pipeline instance (lazy, cached).
                # Use getattr so tests can pass a SimpleNamespace as self.
                if not getattr(self, "_manifest_reverse_built", False):
                    manifest = get_asset_manifest()
                    if manifest and manifest.entries:
                        self._manifest_reverse = {v: k for k, v in manifest.entries.items()}
                    self._manifest_reverse_built = True

                if getattr(self, "_manifest_reverse", None) and raw_assets:
                    reverse = self._manifest_reverse
                    assert reverse is not None  # guarded by truthiness check above
                    normalized: set[str] = set()
                    for url in raw_assets:
                        path = urlparse(url).path.lstrip("/") if "://" in url else url.lstrip("/")
                        normalized.add(reverse.get(path, url))
                    assets = normalized
                else:
                    assets = raw_assets
            except Exception as e:
                # Extraction failure should not break render
                # Fallback extraction will handle this page in phase_track_assets
                logger.debug(
                    "asset_extraction_failed",
                    page=str(page.source_path),
                    error=str(e)[:100],
                )

        if assets:
            self.build_context.accumulate_page_assets(page.source_path, assets)

    def _build_variable_context(self, page: PageLike) -> dict[str, Any]:
        """Build variable context for {{ variable }} substitution in markdown."""
        from bengal.rendering.context import (
            ParamsContext,
            _get_global_contexts,
        )
        from bengal.snapshots.types import NO_SECTION, SectionSnapshot

        section = getattr(page, "_section", None)
        metadata = page.metadata if hasattr(page, "metadata") else {}

        # Get snapshot from build_context if available (RFC: rfc-bengal-snapshot-engine)
        snapshot = None
        if self.build_context:
            snapshot = getattr(self.build_context, "snapshot", None)

        # Resolve section to SectionSnapshot (no wrapper needed)
        # PERF: Use BuildContext cached lookup for O(1) instead of O(S) iteration
        section_for_context: SectionSnapshot = NO_SECTION
        if section:
            if self.build_context:
                # O(1) cached lookup via BuildContext
                section_for_context = self.build_context.get_section_snapshot(section)
            elif snapshot:
                # Fallback: O(S) iteration (when no build_context available)
                for sec_snap in snapshot.sections:
                    if sec_snap.path == getattr(section, "path", None) or sec_snap.name == getattr(
                        section, "name", ""
                    ):
                        section_for_context = sec_snap
                        break

        # Get cached global contexts (site/config are stateless wrappers)
        global_contexts = _get_global_contexts(cast("SiteLike", self.site))

        context: dict[str, Any] = {
            # Core objects with cached smart wrappers
            "page": page,
            "site": global_contexts["site"],
            "config": global_contexts["config"],
            # Shortcuts with safe access (per-page, not cached)
            "params": ParamsContext(metadata),
            "meta": ParamsContext(metadata),
            # Section: SectionSnapshot or NO_SECTION sentinel (has params and __bool__)
            "section": section_for_context,
        }

        # Direct frontmatter access for convenience
        if metadata:
            for key, value in metadata.items():
                if key not in context and not key.startswith("_"):
                    context[key] = value

        return context

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
        )

    def _preprocess_content(self, page: PageLike) -> str:
        """Pre-process page content through configured template engine (legacy parser only)."""

        def parse_markdown(s: str) -> str:
            return self.parser.parse(s, {})

        source = expand_shortcodes(
            page._source,
            self.template_engine,
            page,
            self.site,
            parse_markdown=parse_markdown,
        )

        # Protect pipes inside [[...]] cross-references from table cell splitting
        if "[[" in source and hasattr(self.parser, "_xref_plugin") and self.parser._xref_plugin:
            source = self.parser._xref_plugin.protect_table_pipes(source)

        if page.metadata.get("preprocess") is False:
            return source

        try:
            # Use the configured template engine for preprocessing
            # This respects site.config.template_engine (Kida, Jinja2, etc.)
            # If preprocessing fails (e.g. undefined variables in doc examples),
            # the exception handler below falls back to raw source
            return self.template_engine.render_string(
                source,
                {"page": page, "site": self.site, "config": self.site.config},
                strict=False,
            )
        except Exception as e:
            if self.build_stats:
                # Map error to correct category for stats display
                # Use engine name for categorization (defaults to kida)
                engine_name = getattr(self.template_engine, "NAME", "template")
                error_type = engine_name if "syntax" in str(e).lower() else "preprocessing"
                self.build_stats.add_warning(str(page.source_path), str(e), error_type)
            else:
                logger.warning(
                    "preprocessing_error",
                    source_path=str(page.source_path),
                    error=truncate_error(e),
                    error_code=ErrorCode.R003.value,
                    suggestion="Check page content for template syntax errors",
                )
            return source
