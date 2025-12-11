"""
Core rendering pipeline for Bengal SSG.

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
    - plan/active/rfc-content-ast-architecture.md: AST architecture RFC
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.rendering.pipeline.output import (
    determine_output_path,
    determine_template,
    format_html,
    write_output,
)
from bengal.rendering.pipeline.thread_local import get_thread_parser
from bengal.rendering.pipeline.toc import TOC_EXTRACTION_VERSION, extract_toc_structure
from bengal.rendering.pipeline.transforms import (
    escape_jinja_blocks,
    escape_template_syntax_in_html,
    transform_internal_links,
)
from bengal.rendering.renderer import Renderer
from bengal.rendering.template_engine import TemplateEngine
from bengal.utils.logger import get_logger, truncate_error

logger = get_logger(__name__)


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
        changed_sources: set[Path] | None = None,
    ) -> None:
        """
        Initialize the rendering pipeline.

        Parser Selection:
            Reads from config in this order:
            1. config['markdown_engine'] (legacy)
            2. config['markdown']['parser'] (preferred)
            3. Default: 'mistune' (recommended for speed)

        Parser Caching:
            Uses thread-local caching via get_thread_parser().
            Creates ONE parser per worker thread, cached for reuse.

        Args:
            site: Site instance with config and xref_index
            dependency_tracker: Optional tracker for incremental builds
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings
            build_context: Optional BuildContext for dependency injection
        """
        self.site = site
        # Get markdown engine from config (default: mistune)
        markdown_engine = site.config.get("markdown_engine")
        if not markdown_engine:
            markdown_config = site.config.get("markdown", {})
            markdown_engine = markdown_config.get("parser", "mistune")

        # Allow injection of parser via BuildContext for tests/experiments
        injected_parser = None
        if build_context and getattr(build_context, "markdown_parser", None):
            injected_parser = build_context.markdown_parser

        # Use thread-local parser to avoid re-initialization overhead
        self.parser = injected_parser or get_thread_parser(markdown_engine)

        # Enable cross-references if xref_index is available
        if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
            self.parser.enable_cross_references(site.xref_index)

        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats

        # Allow injection of TemplateEngine via BuildContext
        if build_context and getattr(build_context, "template_engine", None):
            self.template_engine = build_context.template_engine
        else:
            profile_templates = (
                getattr(build_context, "profile_templates", False) if build_context else False
            )
            self.template_engine = TemplateEngine(site, profile_templates=profile_templates)

        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker

        self.renderer = Renderer(self.template_engine, build_stats=build_stats)
        self.build_context = build_context
        self.changed_sources = {Path(p) for p in (changed_sources or set())}

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
        # Handle virtual pages (autodoc, etc.)
        # - Pages with pre-rendered HTML (truthy or empty string)
        # - Autodoc pages that defer rendering until navigation is available
        prerendered = getattr(page, "_prerendered_html", None)
        is_autodoc = page.metadata.get("is_autodoc")
        if getattr(page, "_virtual", False) and (prerendered is not None or is_autodoc):
            self._process_virtual_page(page)
            return

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.start_page(page.source_path)

        if not page.output_path:
            page.output_path = determine_output_path(page, self.site)

        template = determine_template(page)
        parser_version = self._get_parser_version()

        # Determine cache bypass using centralized helper (RFC: rfc-incremental-hot-reload-invariants)
        # Single source of truth: should_bypass(source, changed_sources)
        skip_cache = False
        if self.dependency_tracker and hasattr(self.dependency_tracker, "cache"):
            cache = self.dependency_tracker.cache
            if cache:
                skip_cache = cache.should_bypass(page.source_path, self.changed_sources)

        # Track cache bypass statistics
        if self.build_stats:
            if skip_cache:
                self.build_stats.cache_bypass_hits += 1
            else:
                self.build_stats.cache_bypass_misses += 1

        if not skip_cache and self._try_rendered_cache(page, template):
            return

        if not skip_cache and self._try_parsed_cache(page, template, parser_version):
            return

        # Full pipeline execution
        self._parse_content(page)
        self._enhance_api_docs(page)
        self._cache_parsed_content(page, template, parser_version)
        self._render_and_write(page, template)

        # End page tracking
        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

    def _try_rendered_cache(self, page: Page, template: str) -> bool:
        """Try to use rendered output cache. Returns True if cache hit."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "cache")):
            return False

        cache = self.dependency_tracker.cache
        if not cache or page.metadata.get("_generated"):
            return False

        rendered_html = cache.get_rendered_output(page.source_path, template, page.metadata)
        if not rendered_html:
            return False

        page.rendered_html = rendered_html

        if self.build_stats:
            if not hasattr(self.build_stats, "rendered_cache_hits"):
                self.build_stats.rendered_cache_hits = 0
            self.build_stats.rendered_cache_hits += 1

        write_output(page, self.site, self.dependency_tracker)

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

        return True

    def _try_parsed_cache(self, page: Page, template: str, parser_version: str) -> bool:
        """Try to use parsed content cache. Returns True if cache hit."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "cache")):
            return False

        cache = self.dependency_tracker.cache
        if not cache or page.metadata.get("_generated"):
            return False

        cached = cache.get_parsed_content(page.source_path, page.metadata, template, parser_version)
        if not cached:
            return False

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
        parsed_content = transform_internal_links(parsed_content, self.site.config)

        # Pre-compute plain_text cache
        _ = page.plain_text

        page.extract_links()
        html_content = self.renderer.render_content(parsed_content)
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        write_output(page, self.site, self.dependency_tracker)

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

        return True

    def _parse_content(self, page: Page) -> None:
        """Parse page content through markdown parser."""
        need_toc = self._should_generate_toc(page)

        if hasattr(self.parser, "parse_with_toc_and_context"):
            self._parse_with_mistune(page, need_toc)
        else:
            self._parse_with_legacy(page, need_toc)

        # Additional hardening: escape Jinja2 blocks
        page.parsed_ast = escape_jinja_blocks(page.parsed_ast or "")

        # Transform internal links
        page.parsed_ast = transform_internal_links(page.parsed_ast, self.site.config)

        # Pre-compute plain_text cache
        _ = page.plain_text

    def _should_generate_toc(self, page: Page) -> bool:
        """Determine if TOC should be generated for this page."""
        if page.metadata.get("toc") is False:
            return False

        content_text = page.content or ""
        likely_has_atx = re.search(r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE)
        if likely_has_atx:
            return True

        likely_has_setext = re.search(r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE)
        return bool(likely_has_setext)

    def _parse_with_mistune(self, page: Page, need_toc: bool) -> None:
        """Parse content using Mistune parser."""
        if page.metadata.get("preprocess") is False:
            if need_toc:
                parsed_content, toc = self.parser.parse_with_toc(page.content, page.metadata)
                parsed_content = escape_template_syntax_in_html(parsed_content)
            else:
                parsed_content = self.parser.parse(page.content, page.metadata)
                parsed_content = escape_template_syntax_in_html(parsed_content)
                toc = ""
        else:
            context = self._build_variable_context(page)

            # Type narrowing: check if parser supports context methods (MistuneParser)
            if hasattr(self.parser, "parse_with_toc_and_context") and hasattr(
                self.parser, "parse_with_context"
            ):
                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc_and_context(
                        page.content, page.metadata, context
                    )
                else:
                    parsed_content = self.parser.parse_with_context(
                        page.content, page.metadata, context
                    )
                    toc = ""
            else:
                # Fallback for parsers without context support (e.g., PythonMarkdownParser)
                if need_toc:
                    parsed_content, toc = self.parser.parse_with_toc(page.content, page.metadata)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                else:
                    parsed_content = self.parser.parse(page.content, page.metadata)
                    parsed_content = escape_template_syntax_in_html(parsed_content)
                    toc = ""

            # Extract AST for caching
            if (
                hasattr(self.parser, "supports_ast")
                and self.parser.supports_ast
                and hasattr(self.parser, "parse_to_ast")
            ):
                try:
                    ast_tokens = self.parser.parse_to_ast(page.content, page.metadata)
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
        try:
            enhancer = None
            if self.build_context and getattr(self.build_context, "api_doc_enhancer", None):
                enhancer = self.build_context.api_doc_enhancer
            if enhancer is None:
                from bengal.rendering.api_doc_enhancer import get_enhancer

                enhancer = get_enhancer()
        except Exception as e:
            logger.debug("api_doc_enhancer_init_failed", error=str(e))
            enhancer = None

        page_type = page.metadata.get("type")
        if enhancer and enhancer.should_enhance(page_type):
            page.parsed_ast = enhancer.enhance(page.parsed_ast or "", page_type)

    def _cache_parsed_content(self, page: Page, template: str, parser_version: str) -> None:
        """Store parsed content in cache for next build."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "_cache")):
            return

        cache = self.dependency_tracker._cache
        if not cache or page.metadata.get("_generated"):
            return

        toc_items = extract_toc_structure(page.toc or "")
        cached_ast = getattr(page, "_ast_cache", None)

        cache.store_parsed_content(
            page.source_path,
            page.parsed_ast,
            page.toc,
            toc_items,
            page.metadata,
            template,
            parser_version,
            ast=cached_ast,
        )

    def _render_and_write(self, page: Page, template: str) -> None:
        """Render template and write output."""
        page.extract_links()
        html_content = self.renderer.render_content(page.parsed_ast or "")
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        # Store rendered output in cache
        self._cache_rendered_output(page, template)

        write_output(page, self.site, self.dependency_tracker)

        # Accumulate JSON data during rendering
        self._accumulate_json_data(page)

    def _cache_rendered_output(self, page: Page, template: str) -> None:
        """Store rendered output in cache for next build."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "_cache")):
            return

        cache = self.dependency_tracker._cache
        if not cache or page.metadata.get("_generated"):
            return

        page_key = str(page.source_path)
        deps = list(cache.dependencies.get(page_key, []))

        cache.store_rendered_output(
            page.source_path,
            page.rendered_html,
            template,
            page.metadata,
            dependencies=deps,
        )

    def _accumulate_json_data(self, page: Page) -> None:
        """Accumulate JSON data during rendering for post-processing optimization."""
        if not (self.build_context and self.site):
            return

        output_formats_config = self.site.config.get("output_formats", {})
        if not output_formats_config.get("enabled", True):
            return

        per_page = output_formats_config.get("per_page", ["json", "llm_txt"])
        if "json" not in per_page:
            return

        try:
            from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
            from bengal.postprocess.output_formats.utils import get_page_json_path

            json_path = get_page_json_path(page)
            if json_path:
                json_gen = PageJSONGenerator(self.site, graph_data=None)
                options = output_formats_config.get("options", {})
                include_html = options.get("include_html_content", False)
                include_text = options.get("include_plain_text", True)
                page_data = json_gen.page_to_json(
                    page, include_html=include_html, include_text=include_text
                )
                self.build_context.accumulate_page_json(json_path, page_data)
        except Exception as e:
            logger.debug(
                "json_accumulation_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

    def _process_virtual_page(self, page: Page) -> None:
        """
        Process a virtual page with pre-rendered HTML content.

        Virtual pages (like autodoc pages) may have pre-rendered HTML that is either:
        1. A complete HTML page (extends base.html) - use directly
        2. A content fragment - wrap with template
        3. Deferred autodoc page - render now with full context (menus available)

        Complete pages start with <!DOCTYPE or <html and should not be wrapped.
        """
        if not page.output_path:
            page.output_path = determine_output_path(page, self.site)
        elif not page.output_path.is_absolute():
            page.output_path = self.site.output_dir / page.output_path

        # Check if this is a deferred autodoc page (render with full context)
        if page.metadata.get("is_autodoc") and page.metadata.get("autodoc_element"):
            self._render_autodoc_page(page)
            write_output(page, self.site, self.dependency_tracker)
            logger.debug(
                "autodoc_page_rendered",
                source_path=str(page.source_path),
                output_path=str(page.output_path),
            )
            return

        page.parsed_ast = page._prerendered_html
        page.toc = ""

        # Check if pre-rendered HTML is already a complete page (extends base.html)
        # Complete pages should not be wrapped with another template
        prerendered = page._prerendered_html or ""
        prerendered_stripped = prerendered.strip()
        is_complete_page = (
            prerendered_stripped.startswith("<!DOCTYPE")
            or prerendered_stripped.startswith("<html")
            or prerendered_stripped.startswith("<!doctype")
        )

        if is_complete_page:
            # Use pre-rendered HTML directly (it's already a complete page)
            page.rendered_html = prerendered
            page.rendered_html = format_html(page.rendered_html, page, self.site)
        else:
            # Wrap content fragment with template
            html_content = self.renderer.render_content(page.parsed_ast or "")
            page.rendered_html = self.renderer.render_page(page, html_content)
            page.rendered_html = format_html(page.rendered_html, page, self.site)

        write_output(page, self.site, self.dependency_tracker)

        logger.debug(
            "virtual_page_rendered",
            source_path=str(page.source_path),
            output_path=str(page.output_path),
            is_complete_page=is_complete_page,
        )

    def _render_autodoc_page(self, page: Page) -> None:
        """
        Render an autodoc page using the site's template engine.

        This is called during the rendering phase (after menus are built),
        ensuring full template context is available for proper header/nav rendering.

        Args:
            page: Virtual page with autodoc_element in metadata
        """
        element = self._normalize_autodoc_element(page.metadata.get("autodoc_element"))
        template_name = page.metadata.get("_autodoc_template", "api-reference/module")

        # Mark active menu items for this page
        if hasattr(self.site, "mark_active_menu_items"):
            self.site.mark_active_menu_items(page)

        # Use the site's template engine (which has full context: menus, globals, etc.)
        # This ensures autodoc pages have the same nav/header as regular pages
        try:
            template = self.template_engine.env.get_template(f"{template_name}.html")
        except Exception:
            # Try without .html extension
            try:
                template = self.template_engine.env.get_template(template_name)
            except Exception as e:
                logger.warning(
                    "autodoc_template_not_found",
                    template=template_name,
                    error=str(e),
                )
                # Tag page metadata to indicate fallback was used
                page.metadata["_autodoc_fallback_template"] = True
                page.metadata["_autodoc_fallback_reason"] = str(e)
                # Fall back to rendering as regular virtual page
                page._prerendered_html = f"<h1>{page.title}</h1><p>{element.description}</p>"
                page.parsed_ast = page._prerendered_html
                page.toc = ""
                page.rendered_html = self.renderer.render_page(page, page._prerendered_html)
                page.rendered_html = format_html(page.rendered_html, page, self.site)
                return

        # Render with full site context (same as regular pages)
        # Prefer explicit _section reference set by orchestrators; fall back to page.section
        section = getattr(page, "_section", None) or getattr(page, "section", None)

        try:
            html_content = template.render(
                element=element,
                page=page,
                section=section,  # Pass section explicitly for section index pages
                site=self.site,
                config=self._normalize_config(self.site.config),
                toc_items=getattr(page, "toc_items", []) or [],
                toc=getattr(page, "toc", "") or "",
            )
        except Exception as e:  # Capture template errors with context
            logger.error(
                "autodoc_template_render_failed",
                template=template_name,
                page=str(page.source_path),
                element=getattr(element, "qualified_name", getattr(element, "name", None)),
                element_type=getattr(element, "element_type", None),
                metadata=_safe_metadata_summary(getattr(element, "metadata", None)),
                error=str(e),
            )
            # Fallback minimal HTML to keep build moving
            fallback_desc = getattr(element, "description", "") if element else ""
            page._prerendered_html = f"<h1>{page.title}</h1><p>{fallback_desc}</p>"
            page.parsed_ast = page._prerendered_html
            page.toc = ""
            page._toc_items_cache = []  # Set private cache, not read-only property
            page.rendered_html = self.renderer.render_page(page, page._prerendered_html)
            page.rendered_html = format_html(page.rendered_html, page, self.site)
            return

        page._prerendered_html = html_content
        page.parsed_ast = html_content
        page.toc = ""
        page._toc_items_cache = []  # Set private cache, not read-only property
        page.rendered_html = html_content
        page.rendered_html = format_html(page.rendered_html, page, self.site)

    def _build_variable_context(self, page: Page) -> dict[str, Any]:
        """Build variable context for {{ variable }} substitution in markdown."""
        context: dict[str, Any] = {}

        # Core objects
        context["page"] = page
        context["site"] = self.site
        context["config"] = self.site.config

        # Shortcuts
        context["params"] = page.metadata if hasattr(page, "metadata") else {}
        context["meta"] = context["params"]

        # Direct frontmatter access
        if hasattr(page, "metadata") and page.metadata:
            for key, value in page.metadata.items():
                if key not in context and not key.startswith("_"):
                    context[key] = value

        # Section access
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
            context["section"] = type(
                "Section", (), {"title": "", "name": "", "path": "", "params": {}}
            )()

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
        write_output(page, self.site, self.dependency_tracker)

    def _preprocess_content(self, page: Page) -> str:
        """Pre-process page content through Jinja2 (legacy parser only)."""
        if page.metadata.get("preprocess") is False:
            return page.content

        from jinja2 import Template, TemplateSyntaxError

        try:
            template = Template(page.content)
            return template.render(page=page, site=self.site, config=self.site.config)
        except TemplateSyntaxError as e:
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), "jinja2")
            else:
                logger.warning(
                    "jinja2_syntax_error",
                    source_path=str(page.source_path),
                    error=truncate_error(e),
                )
            return page.content
        except Exception as e:
            if self.build_stats:
                self.build_stats.add_warning(
                    str(page.source_path), truncate_error(e), "preprocessing"
                )
            else:
                logger.warning(
                    "preprocessing_error",
                    source_path=str(page.source_path),
                    error=truncate_error(e),
                )
            return page.content

    def _normalize_autodoc_element(self, element: Any) -> Any:
        """
        Ensure autodoc element metadata supports both dotted and mapping access.
        """
        if element is None:
            return None

        def _wrap_metadata(meta: Any) -> Any:
            if isinstance(meta, dict):
                return _MetadataView(meta)
            # Fallback to empty metadata view for non-dict types (avoid str access errors)
            return _MetadataView({})

        def _coerce(obj: Any) -> None:
            if hasattr(obj, "metadata"):
                meta_wrapped = _wrap_metadata(obj.metadata)
                obj.metadata = meta_wrapped
                meta = meta_wrapped if isinstance(meta_wrapped, dict) else None
                if meta is not None:
                    if not hasattr(obj, "description") and "description" in meta:
                        obj.description = meta.get("description", "")
                    if not hasattr(obj, "title") and "title" in meta:
                        obj.title = meta.get("title", "")
                    # Ensure is_dataclass key exists for templates
                    if "is_dataclass" not in meta:
                        meta["is_dataclass"] = False
                    # Common defaults to avoid Jinja UndefinedError
                    meta.setdefault("signature", "")
                    meta.setdefault("parameters", [])
                    meta.setdefault("properties", {})
                    meta.setdefault("required", [])
                    meta.setdefault("example", None)
                    # Normalize properties values to MetadataView so .type works
                    if isinstance(meta.get("properties"), dict):
                        normalized_props: dict[str, Any] = {}
                        for k, v in meta["properties"].items():
                            if isinstance(v, dict):
                                normalized_props[k] = _MetadataView(v)
                            elif isinstance(v, str):
                                # If property schema is a string, treat it as a type name
                                normalized_props[k] = _MetadataView({"type": v})
                            else:
                                normalized_props[k] = _MetadataView({})
                        meta["properties"] = normalized_props
            if hasattr(obj, "children"):
                for child in obj.children or []:
                    _coerce(child)

        _coerce(element)
        return element

    def _normalize_config(self, config: Any) -> Any:
        """
        Wrap config to allow dotted access with safe defaults for github metadata.

        Extracts github_repo and github_branch from the autodoc section of the config
        and normalizes github_repo to a full URL if provided in owner/repo format.
        """
        base = {}
        if isinstance(config, dict):
            base.update(config)
        else:
            return config

        # Extract github metadata from autodoc config section if not at top level
        autodoc_config = base.get("autodoc", {})

        # Get github_repo: prefer top-level, fall back to autodoc section
        github_repo = base.get("github_repo") or autodoc_config.get("github_repo", "")

        # Normalize owner/repo format to full GitHub URL
        if github_repo and not github_repo.startswith(("http://", "https://")):
            github_repo = f"https://github.com/{github_repo}"

        base["github_repo"] = github_repo

        # Get github_branch: prefer top-level, fall back to autodoc section
        github_branch = base.get("github_branch") or autodoc_config.get("github_branch", "main")
        base["github_branch"] = github_branch

        return _MetadataView(base)


class _MetadataView(dict[str, Any]):
    """
    Dict that also supports attribute-style access (dotted) used by templates.
    """

    def __getattr__(self, item: str) -> Any:
        return self.get(item)


def _safe_metadata_summary(meta: Any) -> str:
    """
    Summarize metadata for logging without raising on missing attributes.
    """
    try:
        if isinstance(meta, dict):
            keys = list(meta.keys())[:10]
            return f"dict keys={keys}"
        return str(meta)
    except Exception:
        return "<unavailable>"
