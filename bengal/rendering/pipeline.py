"""
Rendering pipeline for orchestrating page rendering workflow.

Orchestrates the parsing, AST building, templating, and output rendering phases
for individual pages. Manages thread-local parser instances for performance
and provides dependency tracking for incremental builds.

Key Concepts:
    - Thread-local parsers: Parser instances reused per thread for performance
    - AST-based processing: Content represented as AST for efficient transformation
    - Template rendering: Jinja2 template rendering with page context
    - Dependency tracking: Template and asset dependency tracking

Related Modules:
    - bengal.rendering.parsers.mistune: Markdown parser implementation
    - bengal.rendering.template_engine: Template engine for Jinja2 rendering
    - bengal.rendering.renderer: Individual page rendering logic
    - bengal.cache.dependency_tracker: Dependency graph construction

See Also:
    - bengal/rendering/pipeline.py:RenderingPipeline for pipeline logic
    - plan/active/rfc-content-ast-architecture.md: AST architecture RFC
"""

from __future__ import annotations

import html as html_module
import re
import threading
from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.rendering.parsers import BaseMarkdownParser, create_markdown_parser
from bengal.rendering.renderer import Renderer
from bengal.rendering.template_engine import TemplateEngine
from bengal.utils.logger import get_logger, truncate_error
from bengal.utils.url_strategy import URLStrategy

logger = get_logger(__name__)


# Thread-local storage for parser instances (reuse parsers per thread)
_thread_local = threading.local()

# Cache for created directories (reduces syscalls in parallel builds)
_created_dirs = set()
_created_dirs_lock = threading.Lock()


def _get_thread_parser(engine: str | None = None) -> BaseMarkdownParser:
    """
    Get or create a MarkdownParser instance for the current thread.

    Thread-Local Caching Strategy:
        - Creates ONE parser per worker thread (expensive operation ~10ms)
        - Caches it for the lifetime of that thread
        - Each thread reuses its parser for all pages it processes
        - Total parsers created = number of worker threads

    Performance Impact:
        With max_workers=N (from config):
        - N worker threads created
        - N parser instances created (one per thread)
        - Each parser handles ~(total_pages / N) pages

        Example with max_workers=10 and 200 pages:
        - 10 threads → 10 parsers created
        - Each parser processes ~20 pages
        - Creation cost: 10ms × 10 = 100ms one-time
        - Reuse savings: 9.9 seconds (avoiding 190 × 10ms)

    Thread Safety:
        Each thread gets its own parser instance, no locking needed.
        Read-only access to site config and xref_index is safe.

    Args:
        engine: Parser engine to use ('python-markdown', 'mistune', or None for default)

    Returns:
        Cached MarkdownParser instance for this thread

    Note:
        If you see N parser instances created where N = max_workers,
        this is OPTIMAL behavior, not a bug!
    """
    # Store parser per engine type
    cache_key = f"parser_{engine or 'default'}"
    if not hasattr(_thread_local, cache_key):
        setattr(_thread_local, cache_key, create_markdown_parser(engine))
    return getattr(_thread_local, cache_key)


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
        3. Apply templates (Jinja2)
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
        site: Any,
        dependency_tracker: Any = None,
        quiet: bool = False,
        build_stats: Any = None,
        build_context: Any | None = None,
    ) -> None:
        """
        Initialize the rendering pipeline.

        Parser Selection:
            Reads from config in this order:
            1. config['markdown_engine'] (legacy)
            2. config['markdown']['parser'] (preferred)
            3. Default: 'mistune' (recommended for speed)

            Common values:
            - 'mistune': Fast parser, recommended for most sites (default)
            - 'python-markdown': Full-featured, slightly slower

        Parser Caching:
            Uses thread-local caching via _get_thread_parser().
            Creates ONE parser per worker thread, cached for reuse.

            With max_workers=N:
            - First page in thread: creates parser (~10ms)
            - Subsequent pages: reuses cached parser (~0ms)
            - Total parsers = N (optimal)

        Cross-Reference Support:
            If site has xref_index (built during discovery):
            - Enables [[link]] syntax in markdown
            - Enables automatic .md link resolution (future)
            - O(1) lookup performance

        Args:
            site: Site instance with config and xref_index
            dependency_tracker: Optional tracker for incremental builds
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings

        Note:
            Each worker thread creates its own RenderingPipeline instance.
            The parser is cached at thread level, not pipeline level.
        """
        self.site = site
        # Get markdown engine from config (default: mistune)
        # Check both old location (markdown_engine) and new nested location (markdown.parser)
        markdown_engine = site.config.get("markdown_engine")
        if not markdown_engine:
            # Check nested markdown section
            markdown_config = site.config.get("markdown", {})
            markdown_engine = markdown_config.get("parser", "mistune")
        # Allow injection of parser via BuildContext for tests/experiments
        injected_parser = None
        if build_context and getattr(build_context, "markdown_parser", None):
            injected_parser = build_context.markdown_parser
        # Use thread-local parser to avoid re-initialization overhead
        self.parser = injected_parser or _get_thread_parser(markdown_engine)

        # Enable cross-references if xref_index is available
        if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
            self.parser.enable_cross_references(site.xref_index)

        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats
        # Allow injection of TemplateEngine via BuildContext (e.g., strict modes or mocks)
        if build_context and getattr(build_context, "template_engine", None):
            self.template_engine = build_context.template_engine
        else:
            # Check if template profiling is enabled via build_context
            profile_templates = (
                getattr(build_context, "profile_templates", False) if build_context else False
            )
            self.template_engine = TemplateEngine(site, profile_templates=profile_templates)
        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker
        self.renderer = Renderer(self.template_engine, build_stats=build_stats)
        # Optional build context for future DI (e.g., caches, reporters)
        self.build_context = build_context

    def _build_variable_context(self, page: Page) -> dict:
        """
        Build variable context for {{ variable }} substitution in markdown.

        Creates a rich context that allows writers to access data in multiple ways:

        Direct shortcuts:
            {{ product_name }}     - Direct from frontmatter (most ergonomic!)
            {{ params.version }}   - Via params namespace (page.metadata)
            {{ meta.beta }}        - Short alias for page.metadata

        Full path access:
            {{ page.title }}       - Page properties
            {{ page.metadata.x }}  - Explicit frontmatter access
            {{ site.config.x }}    - Site configuration
            {{ config.baseurl }}   - Config shortcut

        Section access:
            {{ section.title }}    - Parent section title
            {{ section.params.x }} - Section metadata (for cascaded values)

        Example markdown:
            Welcome to {{ product_name }}!
            Version: {{ version }}
            Beta: {{ beta }}

            Site: {{ site.config.title }}
            Section: {{ section.title }}

        Args:
            page: Page being rendered

        Returns:
            Context dict with all variable shortcuts
        """
        context: dict = {}

        # Core objects (always available)
        context["page"] = page
        context["site"] = self.site
        context["config"] = self.site.config

        # Shortcuts for ergonomic access
        # params → page.metadata (namespace for frontmatter)
        context["params"] = page.metadata if hasattr(page, "metadata") else {}
        # meta → shorter alias
        context["meta"] = context["params"]

        # Direct frontmatter access (most ergonomic)
        # {{ product_name }} instead of {{ page.metadata.product_name }}
        if hasattr(page, "metadata") and page.metadata:
            for key, value in page.metadata.items():
                # Don't override core objects or private keys
                if key not in context and not key.startswith("_"):
                    context[key] = value

        # Section access (for cascaded values)
        section = getattr(page, "_section", None)
        if section:
            section_context = {
                "title": getattr(section, "title", ""),
                "name": getattr(section, "name", ""),
                "path": str(getattr(section, "path", "")),
                "params": section.metadata if hasattr(section, "metadata") else {},
            }
            context["section"] = type("Section", (), section_context)()
        else:
            # Empty section context for pages without section
            context["section"] = type(
                "Section", (), {"title": "", "name": "", "path": "", "params": {}}
            )()

        return context

    def process_page(self, page: Page) -> None:
        """
        Process a single page through the entire rendering pipeline.

        Executes all rendering stages: parsing, AST building, template rendering,
        and output writing. Uses cached parsed content when available (skips
        markdown parsing if only template changed).

        Virtual pages (e.g., autodoc API pages) bypass markdown parsing and use
        pre-rendered HTML directly. They still go through template rendering.

        Args:
            page: Page object to process. Must have source_path set.

        Process:
            1. Determine output path early (for page.url property)
            2. Check for virtual page with pre-rendered HTML (fast path)
            3. Check parsed content cache (skip parsing if cache hit)
            4. Parse markdown with variable substitution (if not cached)
            5. Build AST and extract TOC (if not cached)
            6. Render template with page context
            7. Format HTML output (minify/pretty)
            8. Write to output directory

        Performance:
            - Virtual page: Skips markdown parsing entirely
            - Cache hit: Skips markdown parsing (~10-50ms saved per page)
            - Cache miss: Full pipeline execution
            - Thread-local parser reuse: No parser creation overhead

        Examples:
            pipeline.process_page(page)
            # Page is now fully rendered with rendered_html populated
        """
        # Handle virtual pages with pre-rendered HTML (autodoc, etc.)
        if getattr(page, "_virtual", False) and getattr(page, "_prerendered_html", None):
            self._process_virtual_page(page)
            return

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.start_page(page.source_path)

        if not page.output_path:
            page.output_path = self._determine_output_path(page)

        template = self._determine_template(page)
        parser_version = self._get_parser_version()

        # OPTIMIZATION #3: Try rendered output cache first (skips parsing AND template rendering)
        # Generated pages are excluded - they depend on site structure that may have changed
        if self.dependency_tracker and hasattr(self.dependency_tracker, "cache"):
            cache = self.dependency_tracker.cache
            if cache and not page.metadata.get("_generated"):
                # Try fully rendered output cache first (most aggressive caching)
                rendered_html = cache.get_rendered_output(page.source_path, template, page.metadata)
                if rendered_html:
                    page.rendered_html = rendered_html

                    if self.build_stats:
                        if not hasattr(self.build_stats, "rendered_cache_hits"):
                            self.build_stats.rendered_cache_hits = 0
                        self.build_stats.rendered_cache_hits += 1

                    self._write_output(page)

                    if self.dependency_tracker and not page.metadata.get("_generated"):
                        self.dependency_tracker.end_page()

                    return

                # Fall back to parsed content cache (skips parsing, still does template rendering)
                cached = cache.get_parsed_content(
                    page.source_path, page.metadata, template, parser_version
                )

                if cached:
                    page.parsed_ast = cached["html"]
                    page.toc = cached["toc"]
                    page._toc_items_cache = cached.get("toc_items", [])

                    if cached.get("ast"):
                        page._ast_cache = cached["ast"]

                    if self.build_stats:
                        if not hasattr(self.build_stats, "parsed_cache_hits"):
                            self.build_stats.parsed_cache_hits = 0
                        self.build_stats.parsed_cache_hits += 1

                    parsed_content = cached["html"]
                    parsed_content = self._transform_internal_links(parsed_content)

                    # OPTIMIZATION: Pre-compute plain_text cache for post-processing
                    # This runs strip_html() now (parallelized) instead of later (sequential)
                    _ = page.plain_text

                    page.extract_links()
                    html_content = self.renderer.render_content(parsed_content)
                    page.rendered_html = self.renderer.render_page(page, html_content)

                    try:
                        from bengal.postprocess.html_output import format_html_output

                        if page.metadata.get("no_format") is True:
                            mode = "raw"
                            options = {}
                        else:
                            html_cfg = self.site.config.get("html_output", {}) or {}
                            mode = html_cfg.get(
                                "mode",
                                "minify" if self.site.config.get("minify_html", True) else "pretty",
                            )
                            options = {
                                "remove_comments": html_cfg.get(
                                    "remove_comments", mode == "minify"
                                ),
                                "collapse_blank_lines": html_cfg.get("collapse_blank_lines", True),
                            }
                        page.rendered_html = format_html_output(
                            page.rendered_html, mode=mode, options=options
                        )
                    except Exception:
                        pass

                    self._write_output(page)

                    if self.dependency_tracker and not page.metadata.get("_generated"):
                        self.dependency_tracker.end_page()

                    return

        # Parse content with variable substitution
        # Architecture: Mistune handles {{ vars }}, templates handle {% logic %}, code blocks stay literal
        # Pages can disable preprocessing via `preprocess: false` in frontmatter
        need_toc = True
        if page.metadata.get("toc") is False:
            need_toc = False
        else:
            # Quick heuristic: only generate TOC if markdown likely contains h2-h4 headings
            # Matches atx-style (##, ###, ####) and setext-style ("---" underlines after a line)
            content_text = page.content or ""
            likely_has_atx = re.search(
                r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE
            )
            if not likely_has_atx:
                # Lightweight check for setext h2 (===) and h3 (---) style underlines
                likely_has_setext = re.search(
                    r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE
                )
                need_toc = bool(likely_has_setext)
            else:
                need_toc = True

        if hasattr(self.parser, "parse_with_toc_and_context"):
            # Mistune with VariableSubstitutionPlugin (recommended)
            # Check if preprocessing is disabled
            if page.metadata.get("preprocess") is False:
                if need_toc:
                    # Parse without variable substitution (for docs showing template syntax)
                    parsed_content, toc = self.parser.parse_with_toc(page.content, page.metadata)
                    # Escape raw template syntax so it doesn't leak into final HTML
                    parsed_content = self._escape_template_syntax_in_html(parsed_content)
                else:
                    parsed_content = self.parser.parse(page.content, page.metadata)
                    # Escape raw template syntax so it doesn't leak into final HTML
                    parsed_content = self._escape_template_syntax_in_html(parsed_content)
                    toc = ""
            else:
                # Single-pass parsing with variable substitution - fast and simple!
                context = self._build_variable_context(page)

                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc_and_context(
                        page.content, page.metadata, context
                    )
                else:
                    parsed_content = self.parser.parse_with_context(
                        page.content, page.metadata, context
                    )
                    toc = ""

                # Phase 3: Extract AST separately for caching (doesn't affect rendered HTML)
                # This enables page.plain_text and page.links to use AST walkers
                if (
                    hasattr(self.parser, "supports_ast")
                    and self.parser.supports_ast
                    and hasattr(self.parser, "parse_to_ast")
                ):
                    try:
                        ast_tokens = self.parser.parse_to_ast(page.content, page.metadata)
                        page._ast_cache = ast_tokens
                    except Exception:
                        # AST extraction is optional - don't break builds
                        pass
        else:
            # FALLBACK: python-markdown (legacy)
            # Uses Jinja2 preprocessing - deprecated, use Mistune instead
            content = self._preprocess_content(page)
            if need_toc and hasattr(self.parser, "parse_with_toc"):
                parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
            else:
                parsed_content = self.parser.parse(content, page.metadata)
                toc = ""

            # If preprocessing was explicitly disabled, ensure raw template markers are escaped
            if page.metadata.get("preprocess") is False:
                parsed_content = self._escape_template_syntax_in_html(parsed_content)

        # Additional hardening: ensure no Jinja2 block syntax leaks in HTML content
        # even when pages use variable substitution path (handled in MistuneParser as well).
        parsed_content = self._escape_jinja_blocks(parsed_content)

        # Transform internal links to include baseurl (for GitHub Pages, etc.)
        # This handles standard markdown links like [text](/path/) by prepending baseurl
        parsed_content = self._transform_internal_links(parsed_content)

        page.parsed_ast = parsed_content

        # Post-process: Enhance API documentation with badges
        # (inject HTML badges for @async, @property, etc. markers)
        # Prefer injected enhancer if present in BuildContext, else use singleton
        try:
            enhancer = None
            if self.build_context and getattr(self.build_context, "api_doc_enhancer", None):
                enhancer = self.build_context.api_doc_enhancer
            if enhancer is None:
                from bengal.rendering.api_doc_enhancer import get_enhancer

                enhancer = get_enhancer()
        except Exception:
            enhancer = None
        page_type = page.metadata.get("type")
        if enhancer and enhancer.should_enhance(page_type):
            before_enhancement = page.parsed_ast
            page.parsed_ast = enhancer.enhance(page.parsed_ast, page_type)

            # Debug output only in dev mode
            from bengal.utils.profile import should_show_debug

            if (
                should_show_debug()
                and "@property" in before_enhancement
                and "page.md" in str(page.source_path)
                and "core" in str(page.source_path)
            ):
                logger.debug(
                    "api_doc_enhancement",
                    source_path=str(page.source_path),
                    before_chars=len(before_enhancement),
                    after_chars=len(page.parsed_ast),
                    has_markers=("@property" in before_enhancement),
                    has_badges=("api-badge" in page.parsed_ast),
                )

        # ============================================================================
        # Build Phase: PARSING COMPLETE
        # ============================================================================
        # At this point:
        # - page.parsed_ast contains HTML (post-markdown, pre-template)
        # - page.toc contains TOC HTML
        # - page.toc_items property can now extract structured TOC data
        #
        # Note: toc_items is a lazy @property that:
        # - Returns [] if accessed before this point (doesn't cache empty)
        # - Extracts and caches structure when accessed after this point
        # ============================================================================
        page.toc = toc

        # OPTIMIZATION: Pre-compute plain_text cache for post-processing
        # This runs strip_html() now (parallelized) instead of later (sequential)
        # Saves ~400-600ms on post-processing for large sites
        _ = page.plain_text

        # OPTIMIZATION #2 + Phase 3: Store parsed content and AST in cache for next build
        if self.dependency_tracker and hasattr(self.dependency_tracker, "_cache"):
            cache = self.dependency_tracker._cache
            if cache and not page.metadata.get("_generated"):
                # Extract TOC items for caching
                toc_items = extract_toc_structure(toc)

                # Get AST from page cache (may be None if extraction failed)
                cached_ast = getattr(page, "_ast_cache", None)

                cache.store_parsed_content(
                    page.source_path,
                    parsed_content,
                    toc,
                    toc_items,
                    page.metadata,
                    template,
                    parser_version,
                    ast=cached_ast,  # Phase 3: Cache AST for parse-once patterns
                )

        # Stage 3: Extract links for validation
        page.extract_links()

        # Stage 4: Render content to HTML
        html_content = self.renderer.render_content(parsed_content)

        # Stage 5: Apply template (with dependency tracking already set in __init__)
        page.rendered_html = self.renderer.render_page(page, html_content)

        # Stage 6: HTML formatting (pristine output)
        try:
            from bengal.postprocess.html_output import format_html_output

            # Resolve mode from config with backward compatibility
            # Priority: page.metadata.no_format → html_output.mode → minify_html
            if page.metadata.get("no_format") is True:
                mode = "raw"
                options = {}
            else:
                html_cfg = self.site.config.get("html_output", {}) or {}
                mode = html_cfg.get(
                    "mode",
                    "minify" if self.site.config.get("minify_html", True) else "pretty",
                )
                options = {
                    "remove_comments": html_cfg.get("remove_comments", mode == "minify"),
                    "collapse_blank_lines": html_cfg.get("collapse_blank_lines", True),
                }
            page.rendered_html = format_html_output(page.rendered_html, mode=mode, options=options)
        except Exception:
            # Never fail the build on formatter errors; fall back to raw HTML
            pass

        # OPTIMIZATION #3: Store rendered output in cache for next build
        # Excludes generated pages (depend on site structure)
        if self.dependency_tracker and hasattr(self.dependency_tracker, "_cache"):
            cache = self.dependency_tracker._cache
            if cache and not page.metadata.get("_generated"):
                # Get template dependencies for this page
                page_key = str(page.source_path)
                deps = list(cache.dependencies.get(page_key, []))

                cache.store_rendered_output(
                    page.source_path,
                    page.rendered_html,
                    template,
                    page.metadata,
                    dependencies=deps,
                )

        # Stage 7: Write output
        self._write_output(page)

        # OPTIMIZATION: Accumulate JSON data during rendering (Phase 2 of post-processing optimization)
        # This eliminates double iteration of pages in post-processing, saving ~500-700ms
        # See: plan/active/rfc-postprocess-optimization.md
        if self.build_context and self.site:
            output_formats_config = self.site.config.get("output_formats", {})
            if output_formats_config.get("enabled", True):
                per_page = output_formats_config.get("per_page", ["json", "llm_txt"])
                if "json" in per_page:
                    # Build JSON data now (parallelized) instead of later (sequential)
                    try:
                        from bengal.postprocess.output_formats.json_generator import (
                            PageJSONGenerator,
                        )
                        from bengal.postprocess.output_formats.utils import get_page_json_path

                        json_path = get_page_json_path(page)
                        if json_path:
                            # Create a temporary generator instance to use its page_to_json method
                            # We'll pass graph_data later in post-processing if needed
                            json_gen = PageJSONGenerator(self.site, graph_data=None)
                            # Respect config option for including HTML content (default: False)
                            options = output_formats_config.get("options", {})
                            include_html = options.get("include_html_content", False)
                            include_text = options.get("include_plain_text", True)
                            page_data = json_gen.page_to_json(
                                page, include_html=include_html, include_text=include_text
                            )
                            self.build_context.accumulate_page_json(json_path, page_data)
                    except Exception as e:
                        # Never fail the build on JSON accumulation errors
                        # Fall back to computing in post-processing
                        logger.debug(
                            "json_accumulation_failed",
                            page=str(page.source_path),
                            error=str(e)[:100],
                        )

        # End page tracking
        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

    def _process_virtual_page(self, page: Page) -> None:
        """
        Process a virtual page with pre-rendered HTML content.

        Virtual pages (e.g., autodoc API documentation) bypass markdown parsing
        and use pre-rendered HTML directly. They still go through template rendering
        and HTML output formatting.

        This is the fast path for dynamically-generated content that doesn't
        need markdown processing.

        Args:
            page: Virtual page with _prerendered_html set
        """
        # Ensure output path is set and absolute
        if not page.output_path:
            page.output_path = self._determine_output_path(page)
        elif not page.output_path.is_absolute():
            # Virtual pages may have relative output paths - make absolute
            page.output_path = self.site.output_dir / page.output_path

        # Use pre-rendered HTML as the parsed content
        page.parsed_ast = page._prerendered_html
        page.toc = ""  # Virtual pages handle their own TOC if needed

        # Render with template (wraps content in full page HTML)
        template = self._determine_template(page)
        html_content = self.renderer.render_content(page.parsed_ast)
        page.rendered_html = self.renderer.render_page(page, html_content)

        # HTML formatting (minify/pretty)
        try:
            from bengal.postprocess.html_output import format_html_output

            if page.metadata.get("no_format") is True:
                mode = "raw"
                options = {}
            else:
                html_cfg = self.site.config.get("html_output", {}) or {}
                mode = html_cfg.get(
                    "mode",
                    "minify" if self.site.config.get("minify_html", True) else "pretty",
                )
                options = {
                    "remove_comments": html_cfg.get("remove_comments", mode == "minify"),
                    "collapse_blank_lines": html_cfg.get("collapse_blank_lines", True),
                }
            page.rendered_html = format_html_output(page.rendered_html, mode=mode, options=options)
        except Exception:
            pass  # Continue without formatting if it fails

        # Write output
        self._write_output(page)

        logger.debug(
            "virtual_page_rendered",
            source_path=str(page.source_path),
            output_path=str(page.output_path),
        )

    def _escape_template_syntax_in_html(self, html: str) -> str:
        """
        Escape Jinja2 variable delimiters in already-rendered HTML.

        Converts "{{" and "}}" to HTML entities so they appear literally
        in documentation pages but won't be detected by tests as unrendered.
        """
        try:
            return html.replace("{{", "&#123;&#123;").replace("}}", "&#125;&#125;")
        except Exception:
            return html

    def _escape_jinja_blocks(self, html: str) -> str:
        """
        Escape Jinja2 block delimiters in already-rendered HTML content.

        Converts "{%" and "%}" to HTML entities to avoid leaking raw
        control-flow markers into final HTML outside template processing.
        """
        try:
            return html.replace("{%", "&#123;%").replace("%}", "%&#125;")
        except Exception:
            return html

    def _transform_internal_links(self, html: str) -> str:
        """
        Transform internal links to include baseurl prefix.

        This handles standard markdown links like [text](/path/) by prepending
        the configured baseurl. Essential for GitHub Pages project sites and
        similar deployments where the site is not at the domain root.

        Args:
            html: Rendered HTML content

        Returns:
            HTML with transformed internal links
        """
        try:
            from bengal.rendering.link_transformer import (
                get_baseurl,
                should_transform_links,
                transform_internal_links,
            )

            if not should_transform_links(self.site.config):
                return html

            baseurl = get_baseurl(self.site.config)
            return transform_internal_links(html, baseurl)
        except Exception as e:
            # Never fail the build on link transformation errors
            logger.debug("link_transformation_error", error=str(e))
            return html

    def _write_output(self, page: Page) -> None:
        """
        Write rendered page to output directory.

        Args:
            page: Page with rendered content
        """
        # Ensure parent directory exists (with caching to reduce syscalls)
        parent_dir = page.output_path.parent

        # Only create directory if not already done (thread-safe check)
        if parent_dir not in _created_dirs:
            with _created_dirs_lock:
                # Double-check inside lock to avoid race condition
                if parent_dir not in _created_dirs:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    _created_dirs.add(parent_dir)

        # Write rendered HTML (atomic for safety, fast mode for performance)
        # Fast mode skips atomic writes for dev server (PERFORMANCE OPTIMIZATION)
        fast_writes = self.site.config.get("build", {}).get("fast_writes", False)

        if fast_writes:
            # Direct write (faster, but not crash-safe)
            page.output_path.write_text(page.rendered_html, encoding="utf-8")
        else:
            # Atomic write (crash-safe, slightly slower)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(page.output_path, page.rendered_html, encoding="utf-8")

        # Track source→output mapping for cleanup on deletion
        # (Skip generated pages - they have virtual paths)
        if (
            self.dependency_tracker
            and not page.metadata.get("_generated")
            and hasattr(self.dependency_tracker, "cache")
            and self.dependency_tracker.cache
        ):
            self.dependency_tracker.cache.track_output(
                page.source_path, page.output_path, self.site.output_dir
            )

        # Per-page output removed - progress bar provides sufficient feedback
        # Individual page logging available via --full-output if needed for debugging

    def _determine_output_path(self, page: Page) -> Path:
        """
        Determine the output path for a page.

        Args:
            page: Page to determine path for

        Returns:
            Output path
        """
        # Delegate path computation to centralized URLStrategy (i18n-aware)
        return URLStrategy.compute_regular_page_output_path(page, self.site)

    def _determine_template(self, page: Page) -> str:
        """
        Determine which template will be used for this page.

        Args:
            page: Page object

        Returns:
            Template name (e.g., 'single.html', 'page.html')
        """
        # Check page-specific template first
        if hasattr(page, "template") and page.template:
            return page.template

        # Check metadata
        if "template" in page.metadata:
            return page.metadata["template"]

        # Default based on page type
        page_type = page.metadata.get("type", "page")

        match page_type:
            case "page":
                return "page.html"
            case "section":
                return "list.html"
            case _ if page.metadata.get("is_section"):
                return "list.html"
            case _:
                return "single.html"

    def _get_parser_version(self) -> str:
        """
        Get parser version string for cache validation.

        Includes both parser library version and TOC extraction version to
        invalidate cache when TOC parsing logic changes.

        Returns:
            Parser version (e.g., "mistune-3.0-toc2", "markdown-3.4-toc2")
        """
        parser_name = type(self.parser).__name__

        # Try to get actual version
        match parser_name:
            case "MistuneParser":
                try:
                    import mistune

                    base_version = f"mistune-{mistune.__version__}"
                except (ImportError, AttributeError):
                    base_version = "mistune-unknown"
            case "PythonMarkdownParser":
                try:
                    import markdown

                    base_version = f"markdown-{markdown.__version__}"
                except (ImportError, AttributeError):
                    base_version = "markdown-unknown"
            case _:
                base_version = f"{parser_name}-unknown"

        # Add TOC extraction version to invalidate cache when extraction logic changes
        return f"{base_version}-toc{TOC_EXTRACTION_VERSION}"

    def _preprocess_content(self, page: Page) -> str:
        """
        Pre-process page content through Jinja2 to allow variable substitution.

        This allows technical writers to use {{ page.metadata.xxx }} directly
        in their markdown content, not just in templates.

        Pages can disable preprocessing by setting `preprocess: false` in frontmatter.
        This is useful for documentation pages that show Jinja2 syntax examples.

        Args:
            page: Page to pre-process

        Returns:
            Content with Jinja2 variables rendered

        Example:
            # In markdown:
            Today we're talking about {{ page.metadata.product_name }}
            version {{ page.metadata.version }}.
        """
        # Skip preprocessing if disabled in frontmatter
        if page.metadata.get("preprocess") is False:
            return page.content

        from jinja2 import Template, TemplateSyntaxError

        try:
            # Create a Jinja2 template from the content
            template = Template(page.content)

            # Render with page and site context
            rendered_content = template.render(page=page, site=self.site, config=self.site.config)

            return rendered_content

        except TemplateSyntaxError as e:
            # If there's a syntax error, warn but continue with original content
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), "jinja2")
            else:
                logger.warning(
                    "jinja2_syntax_error",
                    source_path=str(page.source_path),
                    error=truncate_error(e),
                    error_type=type(e).__name__,
                )
            if not self.quiet and not self.build_stats:
                print(f"  ⚠️  Jinja2 syntax error in {page.source_path}: {truncate_error(e)}")
            return page.content
        except Exception as e:
            # For any other error, warn but continue
            if self.build_stats:
                self.build_stats.add_warning(
                    str(page.source_path), truncate_error(e), "preprocessing"
                )
            else:
                logger.warning(
                    "preprocessing_error",
                    source_path=str(page.source_path),
                    error=truncate_error(e),
                    error_type=type(e).__name__,
                )
            if not self.quiet and not self.build_stats:
                print(f"  ⚠️  Error pre-processing {page.source_path}: {truncate_error(e)}")
            return page.content


# TOC extraction version - increment when extract_toc_structure() logic changes
TOC_EXTRACTION_VERSION = "2"  # v2: Added regex-based indentation parsing for mistune


def extract_toc_structure(toc_html: str) -> list:
    """
    Parse TOC HTML into structured data for custom rendering.

    Handles both nested <ul> structures (python-markdown style) and flat lists (mistune style).
    For flat lists from mistune, parses indentation to infer heading levels.

    This is a standalone function so it can be called from Page.toc_items
    property for lazy evaluation.

    Args:
        toc_html: HTML table of contents

    Returns:
        List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)
    """
    if not toc_html:
        return []

    import re

    try:
        # For mistune's flat TOC with indentation, use regex to preserve whitespace
        # Pattern: optional spaces + <li><a href="#id">title</a></li>
        pattern = r'^(\s*)<li><a href="#([^"]+)">([^<]+)</a></li>'

        items = []
        for line in toc_html.split("\n"):
            match = re.match(pattern, line)
            if match:
                indent_str, anchor_id, title = match.groups()
                # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
                title = html_module.unescape(title)
                # Count spaces to determine level (mistune uses 2 spaces per level)
                indent_level = len(indent_str)
                level = (
                    indent_level // 2
                ) + 1  # 0 spaces = level 1 (H2), 2 spaces = level 2 (H3), etc.

                items.append({"id": anchor_id, "title": title, "level": level})

        if items:
            return items

        # Fallback to HTML parser for nested structures (python-markdown style)
        from html.parser import HTMLParser

        class TOCParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items = []
                self.current_item = None
                self.depth = 0

            def handle_starttag(self, tag, attrs):
                if tag == "ul":
                    self.depth += 1
                elif tag == "a":
                    attrs_dict = dict(attrs)
                    self.current_item = {
                        "id": attrs_dict.get("href", "").lstrip("#"),
                        "title": "",
                        "level": self.depth,
                    }

            def handle_data(self, data):
                if self.current_item is not None:
                    # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
                    decoded_data = html_module.unescape(data.strip())
                    self.current_item["title"] += decoded_data

            def handle_endtag(self, tag):
                if tag == "ul":
                    self.depth -= 1
                elif tag == "a" and self.current_item:
                    if self.current_item["title"]:
                        self.items.append(self.current_item)
                    self.current_item = None

        parser = TOCParser()
        parser.feed(toc_html)
        return parser.items

    except Exception:
        # If parsing fails, return empty list
        return []
