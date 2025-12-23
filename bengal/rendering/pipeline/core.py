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
from contextlib import suppress
from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.rendering.engines import create_engine
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
    normalize_markdown_links,
    transform_internal_links,
)
from bengal.rendering.renderer import Renderer
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

        self.dependency_tracker = dependency_tracker

        # Enable cross-references if xref_index is available
        if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
            # Pass version_config for cross-version linking support [[v2:path]]
            version_config = getattr(site, "version_config", None)

            # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
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

        self.renderer = Renderer(self.template_engine, build_stats=build_stats)
        self.build_context = build_context
        self.changed_sources = {Path(p) for p in (changed_sources or set())}

        # Extract output collector from build context for hot reload tracking
        self._output_collector = (
            getattr(build_context, "output_collector", None) if build_context else None
        )

        # Cache per-pipeline helpers (one pipeline per worker thread).
        # These are safe to reuse and avoid per-page import/initialization overhead.
        self._api_doc_enhancer: Any | None = None
        self._page_json_generator: Any | None = None
        self._page_json_generator_opts: tuple[bool, bool] | None = None

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

        write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)
        # Inline asset extraction for cache hits
        self._accumulate_asset_deps(page)

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

        # Pre-compute plain_text cache
        _ = page.plain_text

        # Restore cached links if present; otherwise fall back to extraction.
        cached_links = cached.get("links")
        if isinstance(cached_links, list):
            try:
                page.links = [str(x) for x in cached_links]
            except Exception:
                page.links = []
        else:
            try:
                page.extract_links()
            except Exception as e:
                logger.debug(
                    "link_extraction_failed",
                    page=str(page.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )
        html_content = self.renderer.render_content(parsed_content)
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)
        # Inline asset extraction for parsed cache hits
        self._accumulate_asset_deps(page)

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

        # Normalize .md links to clean URLs (./page.md -> ./page/)
        page.parsed_ast = normalize_markdown_links(page.parsed_ast)

        # Transform internal links (add baseurl prefix)
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
            # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
            # Inject source_path into metadata for cross-version dependency tracking
            # (non-context parse methods don't have access to page object)
            metadata_with_source = dict(page.metadata)
            metadata_with_source["_source_path"] = page.source_path

            if need_toc:
                parsed_content, toc = self.parser.parse_with_toc(page.content, metadata_with_source)
                parsed_content = escape_template_syntax_in_html(parsed_content)
            else:
                parsed_content = self.parser.parse(page.content, metadata_with_source)
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
                and persist_tokens
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
        enhancer = self._api_doc_enhancer
        page_type = page.metadata.get("type")
        if enhancer and enhancer.should_enhance(page_type):
            page.parsed_ast = enhancer.enhance(page.parsed_ast or "", page_type)

    def _cache_parsed_content(self, page: Page, template: str, parser_version: str) -> None:
        """Store parsed content in cache for next build."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "cache")):
            return

        cache = self.dependency_tracker.cache
        if not cache or page.metadata.get("_generated"):
            return

        toc_items = extract_toc_structure(page.toc or "")
        md_cfg = self.site.config.get("markdown", {}) or {}
        ast_cache_cfg = md_cfg.get("ast_cache", {}) or {}
        persist_tokens = bool(ast_cache_cfg.get("persist_tokens", False))
        cached_ast = getattr(page, "_ast_cache", None) if persist_tokens else None
        cached_links = getattr(page, "links", None)

        cache.store_parsed_content(
            page.source_path,
            page.parsed_ast,
            page.toc,
            toc_items,
            cached_links if isinstance(cached_links, list) else None,
            page.metadata,
            template,
            parser_version,
            ast=cached_ast,
        )

    def _render_and_write(self, page: Page, template: str) -> None:
        """Render template and write output."""
        html_content = self.renderer.render_content(page.parsed_ast or "")
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        # Store rendered output in cache
        self._cache_rendered_output(page, template)

        write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)

        # Accumulate unified page data during rendering (JSON + search index)
        # See: plan/drafted/rfc-unified-page-data-accumulation.md
        self._accumulate_unified_page_data(page)
        # Inline asset extraction (eliminates separate Track assets phase)
        self._accumulate_asset_deps(page)

    def _cache_rendered_output(self, page: Page, template: str) -> None:
        """Store rendered output in cache for next build."""
        if not (self.dependency_tracker and hasattr(self.dependency_tracker, "cache")):
            return

        cache = self.dependency_tracker.cache
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
                options = output_formats_config.get("options", {})
                include_html = options.get("include_html_content", False)
                include_text = options.get("include_plain_text", True)

                # Reuse per-pipeline generator instance for speed.
                opts = (include_html, include_text)
                if self._page_json_generator is None or self._page_json_generator_opts != opts:
                    self._page_json_generator = PageJSONGenerator(self.site, graph_data=None)
                    self._page_json_generator_opts = opts

                page_data = self._page_json_generator.page_to_json(
                    page, include_html=include_html, include_text=include_text
                )
                self.build_context.accumulate_page_json(json_path, page_data)
        except Exception as e:
            logger.debug(
                "json_accumulation_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

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

    def _accumulate_unified_page_data(self, page: Page) -> None:
        """
        Accumulate unified page data during rendering.

        Computes all per-page derivatives once (excerpt, word_count, etc.)
        for consumption by multiple post-processing generators:
        - PageJSONGenerator (per-page JSON files)
        - SiteIndexGenerator (index.json for search)

        Replaces: _accumulate_json_data()

        See: plan/drafted/rfc-unified-page-data-accumulation.md
        """
        if not self.build_context or not self.site:
            return

        from bengal.postprocess.output_formats.utils import (
            generate_excerpt,
            get_page_json_path,
            get_page_relative_url,
            get_page_url,
        )
        from bengal.utils.build_context import AccumulatedPageData

        try:
            # Compute URLs
            url = get_page_url(page, self.site)  # Full URL with baseurl
            uri = get_page_relative_url(page, self.site)  # Relative path

            # Content derivatives (computed once)
            plain_text = page.plain_text
            word_count = len(plain_text.split())
            excerpt_length = 200  # Standard excerpt length
            excerpt = generate_excerpt(plain_text, excerpt_length)
            content_preview = generate_excerpt(plain_text, excerpt_length * 3)

            # Directory structure for SiteIndexGenerator
            dir_path = "/"
            if uri and isinstance(uri, str):
                path_parts = uri.strip("/").split("/")
                if len(path_parts) > 1:
                    dir_path = "/" + "/".join(path_parts[:-1]) + "/"

            # Extract enhanced metadata for SiteIndexGenerator
            enhanced = self._extract_enhanced_metadata(page)

            # Date handling
            page_date = getattr(page, "date", None)
            date_str = page_date.strftime("%Y-%m-%d") if page_date else None
            date_iso = page_date.isoformat() if page_date else None

            # Build unified data
            data = AccumulatedPageData(
                source_path=page.source_path,
                url=url,
                uri=uri,
                title=page.title or "",
                description=page.metadata.get("description", "") or "",
                date=date_str,
                date_iso=date_iso,
                plain_text=plain_text,
                excerpt=excerpt,
                content_preview=content_preview,
                word_count=word_count,
                reading_time=max(1, round(word_count / 200)),
                section=page._section.name if getattr(page, "_section", None) else "",
                tags=list(page.tags) if page.tags else [],
                dir=dir_path,
                enhanced_metadata=enhanced,
                raw_metadata=dict(page.metadata),
            )

            # Extended JSON data (only if per-page JSON enabled)
            output_formats_config = self.site.config.get("output_formats", {})
            if output_formats_config.get("enabled", True):
                per_page = output_formats_config.get("per_page", ["json", "llm_txt"])
                if "json" in per_page:
                    json_path = get_page_json_path(page)
                    if json_path:
                        data.json_output_path = json_path
                        data.full_json_data = self._build_full_json_data(page)

            self.build_context.accumulate_page_data(data)

        except Exception as e:
            logger.debug(
                "unified_page_data_accumulation_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

    def _extract_enhanced_metadata(self, page: Page) -> dict[str, Any]:
        """
        Extract enhanced metadata fields for SiteIndexGenerator.

        Mirrors the fields extracted by SiteIndexGenerator._add_enhanced_metadata()
        to ensure index.json output is identical.

        See: plan/drafted/rfc-unified-page-data-accumulation.md
        """
        from bengal.utils.autodoc import is_autodoc_page

        metadata = page.metadata
        enhanced: dict[str, Any] = {}

        # Content type and layout
        if value := metadata.get("type"):
            enhanced["type"] = value
        if value := metadata.get("layout"):
            enhanced["layout"] = value

        # Authorship
        if value := metadata.get("author"):
            enhanced["author"] = value
        if value := metadata.get("authors"):
            enhanced["authors"] = value

        # Categories
        if value := metadata.get("category"):
            enhanced["category"] = value
        if value := metadata.get("categories"):
            enhanced["categories"] = value

        # Weight for sorting
        if value := metadata.get("weight"):
            enhanced["weight"] = value

        # Status flags
        if metadata.get("draft"):
            enhanced["draft"] = True
        if metadata.get("featured"):
            enhanced["featured"] = True

        # Search-specific
        if value := metadata.get("search_keywords"):
            enhanced["search_keywords"] = value
        if metadata.get("search_exclude"):
            enhanced["search_exclude"] = True

        # Visibility system integration
        visibility = metadata.get("visibility")
        if metadata.get("hidden", False) or (
            isinstance(visibility, dict) and not visibility.get("search", True)
        ):
            enhanced["search_exclude"] = True

        # API/CLI specific
        if value := metadata.get("cli_name"):
            enhanced["cli_name"] = value
        if value := metadata.get("api_module"):
            enhanced["api_module"] = value

        # Difficulty/level
        if value := metadata.get("difficulty"):
            enhanced["difficulty"] = value
        if value := metadata.get("level"):
            enhanced["level"] = value

        # Related content
        if value := metadata.get("related"):
            enhanced["related"] = value

        # Last modified
        if value := metadata.get("lastmod"):
            if hasattr(value, "isoformat"):
                enhanced["lastmod"] = value.isoformat()
            else:
                enhanced["lastmod"] = str(value)

        # Source file path
        if value := metadata.get("source_file"):
            enhanced["source_file"] = value

        # Version field
        if hasattr(page, "version") and page.version:
            enhanced["version"] = page.version

        # Autodoc flag
        if is_autodoc_page(page):
            enhanced["isAutodoc"] = True

        return enhanced

    def _build_full_json_data(self, page: Page) -> dict[str, Any]:
        """Build full JSON data for per-page JSON files."""
        from bengal.postprocess.output_formats.json_generator import PageJSONGenerator

        output_formats_config = self.site.config.get("output_formats", {})
        options = output_formats_config.get("options", {})
        include_html = options.get("include_html_content", False)
        include_text = options.get("include_plain_text", True)

        # Reuse per-pipeline generator instance for speed.
        opts = (include_html, include_text)
        if self._page_json_generator is None or self._page_json_generator_opts != opts:
            self._page_json_generator = PageJSONGenerator(self.site, graph_data=None)
            self._page_json_generator_opts = opts

        return self._page_json_generator.page_to_json(
            page, include_html=include_html, include_text=include_text
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
        # Note: Section-index pages have autodoc_element=None but still need autodoc rendering
        if page.metadata.get("is_autodoc") and (
            page.metadata.get("autodoc_element") is not None
            or page.metadata.get("is_section_index")
        ):
            self._render_autodoc_page(page)
            write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)
            # Inline asset extraction for autodoc pages
            self._accumulate_asset_deps(page)
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

        write_output(page, self.site, self.dependency_tracker, collector=self._output_collector)
        # Inline asset extraction for virtual pages
        self._accumulate_asset_deps(page)

        logger.debug(
            "virtual_page_rendered",
            source_path=str(page.source_path),
            output_path=str(page.output_path),
            is_complete_page=is_complete_page,
        )

    def _render_autodoc_page(self, page: Page) -> None:
        """
        Render an autodoc page using the site's template engine.

        NOTE: This is the ONLY rendering path for autodoc pages. The deferred
        rendering architecture ensures full template context (menus, active states,
        versioning) is available. See bengal/autodoc/README.md for details.

        This is called during the rendering phase (after menus are built),
        ensuring full template context is available for proper header/nav rendering.

        Args:
            page: Virtual page with autodoc_element in metadata
        """
        element = self._normalize_autodoc_element(page.metadata.get("autodoc_element"))
        template_name = page.metadata.get("_autodoc_template", "autodoc/python/module")

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
                fallback_desc = getattr(element, "description", "") if element else ""
                page._prerendered_html = f"<h1>{page.title}</h1><p>{fallback_desc}</p>"
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
                # Versioning context - autodoc pages are not versioned
                current_version=None,
                is_latest_version=True,
                # Page context expected by base.html templates
                params=page.metadata,  # Alias for metadata (required by base.html)
                metadata=page.metadata,
                content="",  # Autodoc content is rendered by element templates
                meta_desc=getattr(page, "meta_description", "") or "",
                reading_time=getattr(page, "reading_time", 0) or 0,
                excerpt=getattr(page, "excerpt", "") or "",
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
        Also adds href property to elements and their children for URL access.
        """
        import contextlib

        if element is None:
            return None

        # Determine doc_type from page metadata or template name
        doc_type = None
        autodoc_config = {}
        if hasattr(self, "site") and self.site and hasattr(self.site, "config"):
            config = self.site.config
            if isinstance(config, dict):
                autodoc_config = config.get("autodoc", {})
                if "python" in autodoc_config:
                    doc_type = "python"
                elif "cli" in autodoc_config:
                    doc_type = "cli"
                elif "openapi" in autodoc_config:
                    doc_type = "openapi"

        def _compute_element_url(elem: Any, elem_type: str | None = None) -> str:
            """Compute URL for an element based on its qualified_name and type."""
            if not hasattr(elem, "qualified_name"):
                return "#"

            qualified_name = elem.qualified_name
            element_type = elem_type or getattr(elem, "element_type", None)

            # Get prefixes from config with safe defaults
            if doc_type == "python":
                prefix = autodoc_config.get("python", {}).get("output_prefix", "api")
                url_path = f"{prefix}/{qualified_name.replace('.', '/')}"
                return f"/{url_path}/"
            elif doc_type == "cli":
                prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
                from bengal.autodoc.utils import resolve_cli_url_path

                cli_path = resolve_cli_url_path(qualified_name)
                url_path = f"{prefix}/{cli_path}" if cli_path else prefix
                return f"/{url_path}/"
            elif doc_type == "openapi":
                prefix = autodoc_config.get("openapi", {}).get("output_prefix", "api")
                if element_type == "openapi_endpoint":
                    from bengal.autodoc.utils import get_openapi_method, get_openapi_path

                    method = get_openapi_method(elem).lower()
                    path = get_openapi_path(elem).strip("/").replace("/", "-")
                    return f"/{prefix}/endpoints/{method}-{path}/"
                elif element_type == "openapi_schema":
                    return f"/{prefix}/schemas/{elem.name}/"
                else:
                    return f"/{prefix}/overview/"

            # Fallback: infer from element_type
            if element_type in ["command", "command-group"]:
                prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
                from bengal.autodoc.utils import resolve_cli_url_path

                cli_path = resolve_cli_url_path(qualified_name)
                url_path = f"{prefix}/{cli_path}" if cli_path else prefix
                return f"/{url_path}/"
            elif element_type in ["class", "function", "method", "module"]:
                prefix = autodoc_config.get("python", {}).get("output_prefix", "api")
                url_path = f"{prefix}/{qualified_name.replace('.', '/')}"
                return f"/{url_path}/"

            # Ultimate fallback
            return "#"

        def _wrap_metadata(meta: Any) -> Any:
            if isinstance(meta, dict):
                return _MetadataView(meta)
            # Fallback to empty metadata view for non-dict types (avoid str access errors)
            return _MetadataView({})

        def _coerce(obj: Any) -> None:
            # Ensure children attribute exists and is a list (templates rely on it)
            # Use try/except to handle objects that don't support attribute assignment
            try:
                children = getattr(obj, "children", None)
                if children is None or not isinstance(children, list):
                    obj.children = []
            except (AttributeError, TypeError):
                # Object doesn't support attribute assignment - set in __dict__ if possible
                with contextlib.suppress(AttributeError, TypeError):
                    obj.__dict__["children"] = []

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
            # Add href property for URL access in templates
            if not hasattr(obj, "href"):
                try:
                    href = _compute_element_url(obj, getattr(obj, "element_type", None))
                    obj.href = href
                except Exception:
                    # If URL computation fails, set to None (template will use fallback)
                    with suppress(AttributeError, TypeError):
                        obj.href = None

            # Recursively coerce children if they exist and are iterable
            children = getattr(obj, "children", None)
            if children and isinstance(children, (list, tuple)):
                for child in children:
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
