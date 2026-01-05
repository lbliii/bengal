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
    - bengal.rendering.parsers: Markdown parser implementations (Patitas default)
    - bengal.rendering.template_engine: Template engine for rendering (Kida default)
    - bengal.rendering.renderer: Individual page rendering logic
    - bengal.cache.dependency_tracker: Dependency graph construction

See Also:
    - bengal/rendering/pipeline/cache_checker.py: Cache operations
    - bengal/rendering/pipeline/json_accumulator.py: JSON data accumulation
    - bengal/rendering/pipeline/autodoc_renderer.py: Autodoc rendering
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.page import Page

if TYPE_CHECKING:
    from bengal.cache import DependencyTracker
    from bengal.core.site import Site
    from bengal.orchestration.stats import BuildStats
    from bengal.utils.build_context import BuildContext
from bengal.errors import ErrorCode
from bengal.rendering.engines import create_engine
from bengal.rendering.pipeline.autodoc_renderer import AutodocRenderer
from bengal.rendering.pipeline.cache_checker import CacheChecker
from bengal.rendering.pipeline.json_accumulator import JsonAccumulator
from bengal.rendering.pipeline.output import (
    determine_output_path,
    determine_template,
    format_html,
    write_output,
)
from bengal.rendering.pipeline.thread_local import get_thread_parser
from bengal.rendering.pipeline.toc import TOC_EXTRACTION_VERSION
from bengal.rendering.pipeline.transforms import (
    escape_template_syntax_in_html,
)
from bengal.rendering.pipeline.unified_transform import (
    HybridHTMLTransformer,
)
from bengal.rendering.pipeline.write_behind import WriteBehindCollector
from bengal.rendering.renderer import Renderer
from bengal.utils.logger import get_logger, truncate_error

logger = get_logger(__name__)


def _configure_directive_cache_for_versions(site: Site) -> None:
    """Auto-enable directive cache for versioned sites.

    Versioned sites benefit from directive caching because identical
    directive blocks appear across multiple versions. Cache provides
    3-5x speedup for repeated directive content.

    Single-version sites skip caching (no benefit, adds overhead).
    """
    from bengal.directives.cache import configure_cache

    version_config = getattr(site, "version_config", None)
    if not version_config:
        return

    # Check for explicit config override
    build_config = site.config.get("build", {}) or {}
    cache_override = build_config.get("directive_cache")

    if cache_override is not None:
        # Explicit config: respect user preference
        configure_cache(enabled=bool(cache_override))
        logger.debug(
            "directive_cache_configured",
            enabled=bool(cache_override),
            reason="explicit_config",
        )
        return

    # Auto-detect: enable if multiple versions
    if version_config.enabled and len(version_config.versions) > 1:
        configure_cache(enabled=True)
        logger.debug(
            "directive_cache_auto_enabled",
            versions=len(version_config.versions),
            reason="multiple_versions_detected",
        )
    else:
        # Single version or no versioning: disable (avoid overhead)
        configure_cache(enabled=False)


class RenderingPipeline:
    """
    Coordinates the entire rendering process for content pages.

    Orchestrates the complete rendering pipeline from markdown parsing through
    template rendering to final HTML output. Manages thread-local parser instances
    for performance and integrates with dependency tracking for incremental builds.

    Creation:
        Direct instantiation: RenderingPipeline(site, dependency_tracker=None, ...)
            - Created by RenderOrchestrator for page rendering
            - One instance per worker thread (thread-local)
            - Requires Site instance with config

    Attributes:
        site: Site instance with config and xref_index
        parser: Thread-local markdown parser (cached per thread)
        dependency_tracker: Optional DependencyTracker for incremental builds
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
        - Uses: DependencyTracker for dependency tracking
        - Used by: RenderOrchestrator for page rendering

    Thread Safety:
        Thread-safe. Uses thread-local parser instances. Each thread should
        have its own RenderingPipeline instance.

    Examples:
        pipeline = RenderingPipeline(site, dependency_tracker=tracker)
        pipeline.render_page(page)
    """

    def __init__(
        self,
        site: Site,
        dependency_tracker: DependencyTracker | None = None,
        quiet: bool = False,
        build_stats: BuildStats | None = None,
        build_context: BuildContext | None = None,
        changed_sources: set[Path] | None = None,
        block_cache: Any | None = None,
        write_behind: WriteBehindCollector | None = None,
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
            dependency_tracker: Optional tracker for incremental builds
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings
            build_context: Optional BuildContext for dependency injection
            write_behind: Optional WriteBehindCollector for async I/O (RFC: rfc-path-to-200-pgs)
        """
        self.site = site

        # Auto-enable directive cache for versioned sites (3-5x speedup on repeated directives)
        _configure_directive_cache_for_versions(site)

        # Get markdown engine from config (default: patitas)
        markdown_engine = site.config.get("markdown_engine")
        if not markdown_engine:
            markdown_config = site.config.get("markdown", {})
            markdown_engine = markdown_config.get("parser", "patitas")

        # Allow injection of parser via BuildContext for tests/experiments
        injected_parser = None
        if build_context and getattr(build_context, "markdown_parser", None):
            injected_parser = build_context.markdown_parser

        # Use thread-local parser to avoid re-initialization overhead
        self.parser = injected_parser or get_thread_parser(markdown_engine)

        self.dependency_tracker = dependency_tracker

        # Enable cross-references if xref_index is available
        if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
            # Pass version_config for cross-version linking support [[v2:path]]
            version_config = getattr(site, "version_config", None)

            # Pass cross-version tracker for dependency tracking during incremental builds
            cross_version_tracker = None
            if dependency_tracker and hasattr(dependency_tracker, "track_cross_version_link"):
                cross_version_tracker = dependency_tracker.track_cross_version_link

            self.parser.enable_cross_references(
                site.xref_index, version_config, cross_version_tracker
            )
        self.quiet = quiet
        self.build_stats = build_stats

        # Allow injection of TemplateEngine via BuildContext
        if build_context and getattr(build_context, "template_engine", None):
            self.template_engine = build_context.template_engine
        else:
            profile_templates = (
                getattr(build_context, "profile_templates", False) if build_context else False
            )
            self.template_engine = create_engine(site, profile=profile_templates)

        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker

        self.renderer = Renderer(
            self.template_engine, build_stats=build_stats, block_cache=block_cache
        )
        self.build_context = build_context
        self.changed_sources = {Path(p) for p in (changed_sources or set())}

        # Extract output collector from build context for hot reload tracking
        self._output_collector = (
            getattr(build_context, "output_collector", None) if build_context else None
        )

        # Initialize helper modules (composition)
        self._cache_checker = CacheChecker(
            dependency_tracker=dependency_tracker,
            site=site,
            renderer=self.renderer,
            build_stats=build_stats,
            output_collector=self._output_collector,
        )
        self._json_accumulator = JsonAccumulator(site, build_context)
        self._autodoc_renderer = AutodocRenderer(
            site=site,
            template_engine=self.template_engine,
            renderer=self.renderer,
            dependency_tracker=dependency_tracker,
            output_collector=self._output_collector,
            build_stats=build_stats,
        )

        # PERF: Unified HTML transformer - single instance reused across all pages, ~27% faster than separate transforms
        self._html_transformer = HybridHTMLTransformer(baseurl=site.baseurl or "")

        # Write-behind collector for async I/O (RFC: rfc-path-to-200-pgs Phase III)
        # Use explicit parameter, or get from BuildContext if available
        self._write_behind = write_behind or (
            getattr(build_context, "write_behind", None) if build_context else None
        )

        # Cache per-pipeline helpers (one pipeline per worker thread).
        # These are safe to reuse and avoid per-page import/initialization overhead.
        self._api_doc_enhancer: Any | None = None

        # Prefer injected enhancer (tests/experiments), fall back to singleton enhancer.
        try:
            if build_context and getattr(build_context, "api_doc_enhancer", None):
                self._api_doc_enhancer = build_context.api_doc_enhancer
            else:
                from bengal.rendering.api_doc_enhancer import get_enhancer

                self._api_doc_enhancer = get_enhancer()
        except Exception as e:
            logger.debug("api_doc_enhancer_init_failed", error=str(e))
            self._api_doc_enhancer = None

    def process_page(self, page: Page) -> None:
        """
        Process a single page through the entire rendering pipeline.

        Executes all rendering stages: parsing, AST building, template rendering,
        and output writing. Uses cached parsed content when available.

        Virtual pages (e.g., autodoc API pages) bypass markdown parsing and use
        pre-rendered HTML directly.

        Args:
            page: Page object to process. Must have source_path set.
        """
        # Clear per-render get_page() cache at start of each page render.
        # This ensures each page render starts with a fresh cache, avoiding
        # stale results from previous page renders in the same thread.
        from bengal.rendering.template_functions.get_page import clear_get_page_cache

        clear_get_page_cache()

        # Handle virtual pages (autodoc, etc.)
        # - Pages with pre-rendered HTML (truthy or empty string)
        # - Autodoc pages that defer rendering until navigation is available
        prerendered = getattr(page, "_prerendered_html", None)
        is_autodoc = page.metadata.get("is_autodoc")
        if getattr(page, "_virtual", False) and (prerendered is not None or is_autodoc):
            self._autodoc_renderer.process_virtual_page(page)
            # Accumulate unified page data for virtual pages (JSON + search index)
            self._json_accumulator.accumulate_unified_page_data(page)
            # Inline asset extraction for virtual pages
            self._accumulate_asset_deps(page)
            return

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.start_page(page.source_path)

        if not page.output_path:
            page.output_path = determine_output_path(page, self.site)

        template = determine_template(page)
        parser_version = self._get_parser_version()

        # Determine cache bypass using centralized helper
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
            return

        if not skip_cache and self._cache_checker.try_parsed_cache(page, template, parser_version):
            # Inline asset extraction for parsed cache hits
            self._accumulate_asset_deps(page)
            return

        # Full pipeline execution
        self._parse_content(page)
        self._enhance_api_docs(page)
        # Extract links once (regex-heavy); cache can reuse these on template-only rebuilds.
        try:
            page.extract_links()
        except Exception as e:
            logger.debug(
                "link_extraction_failed",
                page=str(page.source_path),
                error=str(e),
                error_type=type(e).__name__,
            )
        self._cache_checker.cache_parsed_content(page, template, parser_version)
        self._render_and_write(page, template)

        # End page tracking
        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

    def _parse_content(self, page: Page) -> None:
        """Parse page content through markdown parser.

        Uses deferred (parallel) syntax highlighting on Python 3.14t for
        pages with multiple code blocks. This provides 1.5-2x speedup.
        """
        from bengal.rendering.parsers.mistune.highlighting import (
            disable_deferred_highlighting,
            enable_deferred_highlighting,
            flush_deferred_highlighting,
        )

        need_toc = self._should_generate_toc(page)

        # Enable deferred highlighting for parallel batch processing (3.14t)
        enable_deferred_highlighting()
        try:
            if hasattr(self.parser, "parse_with_toc_and_context"):
                self._parse_with_context_aware_parser(page, need_toc)
            else:
                self._parse_with_legacy(page, need_toc)

            # Flush deferred highlighting: batch process all code blocks in parallel
            # This replaces <!--code:XXX--> placeholders with highlighted HTML
            # Must run BEFORE transformer so highlighter output is also escaped/transformed
            page.parsed_ast = flush_deferred_highlighting(page.parsed_ast)

            # PERF: Unified HTML transformation (~27% faster than separate passes)
            # Handles: Jinja block escaping, .md link normalization, baseurl prefixing
            page.parsed_ast = self._html_transformer.transform(page.parsed_ast or "")

            # Restore any remaining escape placeholders in code block output
            # This is needed because deferred highlighting captures code BEFORE
            # restore_placeholders() runs, so {{/* */}} escapes appear as
            # BENGALESCAPED*ENDESC in the final highlighted HTML
            if (
                hasattr(self.parser, "_var_plugin")
                and self.parser._var_plugin
                and self.parser._var_plugin.escaped_placeholders
            ):
                page.parsed_ast = self.parser._var_plugin.restore_placeholders(page.parsed_ast)
        finally:
            disable_deferred_highlighting()

        # Pre-compute plain_text cache
        _ = page.plain_text

    def _should_generate_toc(self, page: Page) -> bool:
        """Determine if TOC should be generated for this page."""
        if page.metadata.get("toc") is False:
            return False

        content_text = page._source or ""
        likely_has_atx = re.search(r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE)
        if likely_has_atx:
            return True

        likely_has_setext = re.search(r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE)
        return bool(likely_has_setext)

    def _parse_with_context_aware_parser(self, page: Page, need_toc: bool) -> None:
        """Parse content using a context-aware parser (Mistune, Patitas)."""
        if page.metadata.get("preprocess") is False:
            # Inject source_path into metadata for cross-version dependency tracking
            # (non-context parse methods don't have access to page object)
            metadata_with_source = dict(page.metadata)
            metadata_with_source["_source_path"] = page.source_path

            if need_toc:
                parsed_content, toc = self.parser.parse_with_toc(page._source, metadata_with_source)
                parsed_content = escape_template_syntax_in_html(parsed_content)
            else:
                parsed_content = self.parser.parse(page._source, metadata_with_source)
                parsed_content = escape_template_syntax_in_html(parsed_content)
                toc = ""
        else:
            context = self._build_variable_context(page)
            md_cfg = self.site.config.get("markdown", {}) or {}
            ast_cache_cfg = md_cfg.get("ast_cache", {}) or {}
            persist_tokens = bool(ast_cache_cfg.get("persist_tokens", False))

            # Type narrowing: check if parser supports context methods (MistuneParser)
            if hasattr(self.parser, "parse_with_toc_and_context") and hasattr(
                self.parser, "parse_with_context"
            ):
                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc_and_context(
                        page._source, page.metadata, context
                    )
                else:
                    parsed_content = self.parser.parse_with_context(
                        page._source, page.metadata, context
                    )
                    toc = ""
            else:
                # Fallback for parsers without context support (e.g., PythonMarkdownParser)
                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc(page._source, page.metadata)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                else:
                    parsed_content = self.parser.parse(page._source, page.metadata)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                    toc = ""

            # Extract AST for caching
            if (
                hasattr(self.parser, "supports_ast")
                and self.parser.supports_ast
                and hasattr(self.parser, "parse_to_ast")
                and persist_tokens
            ):
                try:
                    ast_tokens = self.parser.parse_to_ast(page._source, page.metadata)
                    page._ast_cache = ast_tokens
                except Exception as e:
                    logger.debug(
                        "ast_extraction_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )

        page.parsed_ast = parsed_content
        page.toc = toc

    def _parse_with_legacy(self, page: Page, need_toc: bool) -> None:
        """Parse content using legacy python-markdown parser."""
        content = self._preprocess_content(page)
        if need_toc and hasattr(self.parser, "parse_with_toc"):
            parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        else:
            parsed_content = self.parser.parse(content, page.metadata)
            toc = ""

        if page.metadata.get("preprocess") is False:
            parsed_content = escape_template_syntax_in_html(parsed_content)

        page.parsed_ast = parsed_content
        page.toc = toc

    def _enhance_api_docs(self, page: Page) -> None:
        """Enhance API documentation with badges."""
        enhancer = self._api_doc_enhancer
        page_type = page.metadata.get("type")
        if enhancer and enhancer.should_enhance(page_type):
            page.parsed_ast = enhancer.enhance(page.parsed_ast or "", page_type)

    def _render_and_write(self, page: Page, template: str) -> None:
        """Render template and write output."""
        html_content = self.renderer.render_content(page.parsed_ast or "")
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        # Store rendered output in cache
        self._cache_checker.cache_rendered_output(page, template)

        # Write output (sync or async via write-behind)
        write_output(
            page,
            self.site,
            self.dependency_tracker,
            collector=self._output_collector,
            write_behind=self._write_behind,
        )

        # Accumulate unified page data during rendering (JSON + search index)
        self._json_accumulator.accumulate_unified_page_data(page)
        # Inline asset extraction (eliminates separate Track assets phase)
        self._accumulate_asset_deps(page)

    def _accumulate_asset_deps(self, page: Page) -> None:
        """
        Accumulate asset dependencies during rendering.

        Similar to _accumulate_json_data - extracts asset refs from rendered
        HTML and stores in BuildContext for later persistence.
        """
        if not self.build_context or not page.rendered_html:
            return

        try:
            from bengal.rendering.asset_extractor import extract_assets_from_html

            assets = extract_assets_from_html(page.rendered_html)
            if assets:
                self.build_context.accumulate_page_assets(page.source_path, assets)
        except Exception as e:
            # Extraction failure should not break render
            # Fallback extraction will handle this page in phase_track_assets
            logger.debug(
                "asset_extraction_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

    def _build_variable_context(self, page: Page) -> dict[str, Any]:
        """Build variable context for {{ variable }} substitution in markdown."""
        from bengal.rendering.context import (
            ParamsContext,
            SectionContext,
            _get_global_contexts,
        )

        section = getattr(page, "_section", None)
        metadata = page.metadata if hasattr(page, "metadata") else {}

        # Get cached global contexts (site/config are stateless wrappers)
        global_contexts = _get_global_contexts(self.site)

        context: dict[str, Any] = {
            # Core objects with cached smart wrappers
            "page": page,
            "site": global_contexts["site"],
            "config": global_contexts["config"],
            # Shortcuts with safe access (per-page, not cached)
            "params": ParamsContext(metadata),
            "meta": ParamsContext(metadata),
            # Section with safe access (never None)
            "section": SectionContext(section),
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
            case "MistuneParser":
                try:
                    import mistune

                    base_version = f"mistune-{mistune.__version__}"
                except (ImportError, AttributeError):
                    base_version = "mistune-unknown"
            case "PythonMarkdownParser":
                try:
                    import markdown  # type: ignore[import-untyped]

                    base_version = f"markdown-{markdown.__version__}"
                except (ImportError, AttributeError):
                    base_version = "markdown-unknown"
            case _:
                base_version = f"{parser_name}-unknown"

        return f"{base_version}-toc{TOC_EXTRACTION_VERSION}"

    def _write_output(self, page: Page) -> None:
        """Write rendered page to output directory (backward compatibility wrapper)."""
        write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)

    def _preprocess_content(self, page: Page) -> str:
        """Pre-process page content through configured template engine (legacy parser only)."""
        if page.metadata.get("preprocess") is False:
            return page._source

        try:
            # Use the configured template engine for preprocessing
            # This respects site.config.template_engine (Kida, Jinja2, etc.)
            # If preprocessing fails (e.g. undefined variables in doc examples),
            # the exception handler below falls back to raw source
            return self.template_engine.render_string(
                page._source,
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
            return page._source
