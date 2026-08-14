"""
Parse-stage helpers for the rendering pipeline.

Extracted from core.py so RenderingPipeline stays a coordinator. Behavior is
identical: frozen ParsedPage records, deferred highlighting, and plugin link
collection still run on the pipeline instance (tests monkeypatch methods there).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from bengal.cache.parsed_output import apply_parsed_page_to_page, with_parsed_html
from bengal.content.page_source import get_raw_source
from bengal.core.records import ParsedPage, parsed_page_from_page_state
from bengal.errors import ErrorCode
from bengal.rendering.page_operations import set_content_dependencies, set_directive_links
from bengal.rendering.pipeline.profiler import RenderProfiler
from bengal.rendering.pipeline.profiler import is_enabled as _profiling_enabled
from bengal.rendering.pipeline.transforms import escape_template_syntax_in_html
from bengal.rendering.shortcodes import expand_shortcodes
from bengal.utils.observability.logger import get_logger, truncate_error

if TYPE_CHECKING:
    from bengal.parsing.protocols import RichMarkdownParser
    from bengal.protocols import PageLike
    from bengal.rendering.pipeline.core import RenderingPipeline

logger = get_logger(__name__)


def set_links_collector_for_parse(pipeline: RenderingPipeline) -> None:
    """Set links collector on xref plugin before parse (Patitas only)."""
    if hasattr(pipeline.parser, "_xref_plugin") and pipeline.parser._xref_plugin:
        pipeline.parser._xref_plugin.set_links_collector([])


def get_plugin_collected_links(pipeline: RenderingPipeline) -> list[str]:
    """Get and clear links collected by xref plugin during parse (Patitas only)."""
    if hasattr(pipeline.parser, "_xref_plugin") and pipeline.parser._xref_plugin:
        return pipeline.parser._xref_plugin.get_collected_links()
    return []


def parse_content(pipeline: RenderingPipeline, page: PageLike) -> None:
    """Parse page content through markdown parser.

    Uses deferred (parallel) syntax highlighting on Python 3.14t for
    pages with multiple code blocks. This provides 1.5-2x speedup.
    """
    from bengal.rendering.highlighting import (
        disable_deferred_highlighting,
        enable_deferred_highlighting,
        flush_deferred_highlighting,
    )

    need_toc = should_generate_toc(page)

    # Enable deferred highlighting for parallel batch processing (3.14t)
    enable_deferred_highlighting(cache=pipeline._highlight_cache)
    try:
        from bengal.parsing.backends.patitas.render_session import page_render_session

        with page_render_session(page_context=page, site=pipeline.site) as session:
            if hasattr(pipeline.parser, "parse_with_toc_and_context"):
                parsed_page, directive_links = parse_with_context_aware_parser(
                    pipeline, page, need_toc
                )
            else:
                parsed_page = parse_with_legacy(pipeline, page, need_toc)
                directive_links = []
        set_content_dependencies(page, session.content_dependencies)
        if directive_links:
            set_directive_links(page, directive_links)

        # Flush deferred highlighting: batch process all code blocks in parallel
        # This replaces <!--code:XXX--> placeholders with highlighted HTML
        # Must run BEFORE transformer so highlighter output is also escaped/transformed
        _prof_inner = RenderProfiler.get() if _profiling_enabled() else None
        if parsed_page.html_content:
            if _prof_inner:
                with _prof_inner.step("flush_highlight"):
                    parsed_page = with_parsed_html(
                        parsed_page,
                        flush_deferred_highlighting(parsed_page.html_content),
                    )
            else:
                parsed_page = with_parsed_html(
                    parsed_page,
                    flush_deferred_highlighting(parsed_page.html_content),
                )

        # PERF: Unified HTML transformation (~27% faster than separate passes)
        # Handles: Jinja block escaping, .md link normalization, baseurl prefixing
        if _prof_inner:
            with _prof_inner.step("html_transform"):
                parsed_page = with_parsed_html(
                    parsed_page,
                    pipeline._html_transformer.transform(parsed_page.html_content or ""),
                )
        else:
            parsed_page = with_parsed_html(
                parsed_page,
                pipeline._html_transformer.transform(parsed_page.html_content or ""),
            )

        # Restore any remaining escape placeholders in code block output
        # This is needed because deferred highlighting captures code BEFORE
        # restore_placeholders() runs, so {{/* */}} escapes appear as
        # BENGALESCAPED*ENDESC in the final highlighted HTML
        # fmt: off
        if hasattr(pipeline.parser, "_var_plugin"):
            rich_parser = cast("RichMarkdownParser", pipeline.parser)
            if rich_parser._var_plugin and rich_parser._var_plugin.escaped_placeholders:
                parsed_page = with_parsed_html(
                    parsed_page,
                    rich_parser._var_plugin.restore_placeholders(
                        parsed_page.html_content
                    ),
                )
        # fmt: on
        apply_parsed_page_to_page(
            page,
            parsed_page,
            seed_counts=False,
            seed_links=False,
            seed_plain_text=False,
            seed_ast=True,
        )
    finally:
        disable_deferred_highlighting()

    # Pre-compute plain_text cache
    _prof_pt = RenderProfiler.get() if _profiling_enabled() else None
    if _prof_pt:
        with _prof_pt.step("plain_text"):
            _ = page.plain_text
    else:
        _ = page.plain_text


def should_generate_toc(page: PageLike) -> bool:
    """Determine if TOC should be generated for this page."""
    if page.metadata.get("toc") is False:
        return False

    content_text = get_raw_source(page)
    likely_has_atx = re.search(r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE)
    if likely_has_atx:
        return True

    likely_has_setext = re.search(r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE)
    return bool(likely_has_setext)


def parse_with_context_aware_parser(
    pipeline: RenderingPipeline, page: PageLike, need_toc: bool
) -> tuple[ParsedPage, list[str]]:
    """Parse content using a context-aware parser (Mistune, Patitas)."""

    def parse_markdown(s: str) -> str:
        return pipeline.parser.parse(s, {})

    raw_source = get_raw_source(page)
    source = expand_shortcodes(
        raw_source,
        pipeline.template_engine,
        page,
        pipeline.site,
        parse_markdown=parse_markdown,
    )

    # Protect pipes inside [[...]] cross-references from table cell splitting.
    # Must run before the markdown parser sees the source.
    if "[[" in source and hasattr(pipeline.parser, "_xref_plugin") and pipeline.parser._xref_plugin:
        source = pipeline.parser._xref_plugin.protect_table_pipes(source)

    # Collect directive-generated links during rendering (cards, buttons, etc.)
    directive_links: list[str] = []
    ast_cache: Any = None
    parsed_excerpt = ""
    parsed_meta_description = ""

    if page.metadata.get("preprocess") is False:
        # Inject source_path and excerpt_length for cross-version dependency tracking
        # (non-context parse methods don't have access to page object)
        from bengal.config.utils import resolve_excerpt_length

        meta = page.metadata
        metadata_with_source = dict(meta or {})
        metadata_with_source["_source_path"] = str(page.source_path)
        content_cfg = pipeline.site.config.get("content", {}) or {}
        metadata_with_source["_excerpt_length"] = resolve_excerpt_length(page, content_cfg)

        if need_toc:
            result = pipeline.parser.parse_with_toc(source, metadata_with_source)
            parsed_content, toc = result[0], result[1]
            result_ext = cast("tuple[str, ...]", result)
            if len(result_ext) > 2:
                parsed_excerpt = result_ext[2]
            if len(result_ext) > 3:
                parsed_meta_description = result_ext[3]
            parsed_content = escape_template_syntax_in_html(parsed_content)
        else:
            parsed_content = pipeline.parser.parse(source, metadata_with_source)
            parsed_content = escape_template_syntax_in_html(parsed_content)
            toc = ""
    else:
        from bengal.config.utils import resolve_excerpt_length

        # Honor instance monkeypatches (tests assign pipeline._build_variable_context).
        context = pipeline._build_variable_context(page)
        context["_links_collector"] = directive_links
        md_cfg = pipeline.site.config.get("markdown", {}) or {}
        ast_cache_cfg = md_cfg.get("ast_cache", {}) or {}
        persist_tokens = bool(ast_cache_cfg.get("persist_tokens", False))

        # Build mutable metadata for parser (CascadeView is immutable)
        meta = page.metadata
        metadata_for_parser = dict(meta or {})
        metadata_for_parser["_source_path"] = str(page.source_path)
        content_cfg = pipeline.site.config.get("content", {}) or {}
        metadata_for_parser["_excerpt_length"] = resolve_excerpt_length(page, content_cfg)

        # Type narrowing: check if parser supports context methods (PatitasParser)
        if hasattr(pipeline.parser, "parse_with_toc_and_context") and hasattr(
            pipeline.parser, "parse_with_context"
        ):
            rich_parser = cast("RichMarkdownParser", pipeline.parser)
            if need_toc:
                result = rich_parser.parse_with_toc_and_context(
                    source, metadata_for_parser, context
                )
                parsed_content, toc = result[0], result[1]
                result_ext = cast("tuple[str, ...]", result)
                if len(result_ext) > 2:
                    parsed_excerpt = result_ext[2]
                if len(result_ext) > 3:
                    parsed_meta_description = result_ext[3]
            else:
                parsed_content = rich_parser.parse_with_context(
                    source, metadata_for_parser, context
                )
                toc = ""
        else:
            # Fallback for parsers without context support (e.g., PythonMarkdownParser)
            if need_toc:
                result = pipeline.parser.parse_with_toc(source, metadata_for_parser)
                parsed_content, toc = result[0], result[1]
                result_ext = cast("tuple[str, ...]", result)
                if len(result_ext) > 2:
                    parsed_excerpt = result_ext[2]
                if len(result_ext) > 3:
                    parsed_meta_description = result_ext[3]
                parsed_content = escape_template_syntax_in_html(parsed_content)
            else:
                parsed_content = pipeline.parser.parse(source, metadata_for_parser)
                parsed_content = escape_template_syntax_in_html(parsed_content)
                toc = ""

        # Extract AST for caching
        if (
            hasattr(pipeline.parser, "supports_ast")
            and pipeline.parser.supports_ast
            and persist_tokens
        ):
            try:
                if hasattr(pipeline.parser, "parse_to_document"):
                    import patitas

                    from bengal.utils.serialization import to_jsonable

                    parser_with_document = cast("Any", pipeline.parser)
                    doc = None
                    consume_last_document = getattr(pipeline.parser, "consume_last_document", None)
                    if callable(consume_last_document):
                        doc = consume_last_document()
                    if doc is None:
                        doc = parser_with_document.parse_to_document(source, metadata_for_parser)
                    ast_cache = to_jsonable(patitas.to_dict(doc))
                elif hasattr(pipeline.parser, "parse_to_ast"):
                    ast_tokens = pipeline.parser.parse_to_ast(source, metadata_for_parser)
                    ast_cache = ast_tokens
            except Exception as e:
                logger.debug(
                    "ast_extraction_failed",
                    page=str(page.source_path),
                    error=str(e),
                )

    return (
        ParsedPage(
            html_content=parsed_content,
            toc=toc,
            toc_items=(),
            excerpt=parsed_excerpt,
            meta_description=parsed_meta_description,
            plain_text="",
            word_count=getattr(page, "word_count", 0) or 0,
            reading_time=getattr(page, "reading_time", 0) or 0,
            links=(),
            ast_cache=ast_cache,
        ),
        directive_links,
    )


def parse_with_legacy(pipeline: RenderingPipeline, page: PageLike, need_toc: bool) -> ParsedPage:
    """Parse content using legacy python-markdown parser."""
    content = preprocess_content(pipeline, page)
    if need_toc and hasattr(pipeline.parser, "parse_with_toc"):
        result = pipeline.parser.parse_with_toc(content, page.metadata)
        parsed_content, toc = result[0], result[1]
    else:
        parsed_content = pipeline.parser.parse(content, page.metadata)
        toc = ""

    if page.metadata.get("preprocess") is False:
        parsed_content = escape_template_syntax_in_html(parsed_content)

    return ParsedPage(
        html_content=parsed_content,
        toc=toc,
        toc_items=(),
        excerpt="",
        meta_description="",
        plain_text="",
        word_count=getattr(page, "word_count", 0) or 0,
        reading_time=getattr(page, "reading_time", 0) or 0,
        links=(),
    )


def build_parsed_page(page: PageLike) -> ParsedPage:
    """Construct a ParsedPage from current page state after parsing.

    Called after parse_content, enhance_api_docs, and extract_links
    have finished mutating the page.  The resulting frozen record
    captures all parse-phase output for downstream rendering.
    """
    from bengal.rendering.pipeline.toc import extract_toc_structure

    toc_items = tuple(extract_toc_structure(page.toc or ""))
    return parsed_page_from_page_state(page, toc_items=toc_items)


def preprocess_content(pipeline: RenderingPipeline, page: PageLike) -> str:
    """Pre-process page content through configured template engine (legacy parser only)."""

    def parse_markdown(s: str) -> str:
        return pipeline.parser.parse(s, {})

    raw_source = get_raw_source(page)
    source = expand_shortcodes(
        raw_source,
        pipeline.template_engine,
        page,
        pipeline.site,
        parse_markdown=parse_markdown,
    )

    # Protect pipes inside [[...]] cross-references from table cell splitting
    if "[[" in source and hasattr(pipeline.parser, "_xref_plugin") and pipeline.parser._xref_plugin:
        source = pipeline.parser._xref_plugin.protect_table_pipes(source)

    if page.metadata.get("preprocess") is False:
        return source

    try:
        # Use the configured template engine for preprocessing
        # This respects site.config.template_engine (Kida, Jinja2, etc.)
        # If preprocessing fails (e.g. undefined variables in doc examples),
        # the exception handler below falls back to raw source
        return pipeline.template_engine.render_string(
            source,
            {"page": page, "site": pipeline.site, "config": pipeline.site.config},
            strict=False,
        )
    except Exception as e:
        if pipeline.build_stats:
            # Map error to correct category for stats display
            # Use engine name for categorization (defaults to kida)
            engine_name = getattr(pipeline.template_engine, "NAME", "template")
            error_type = engine_name if "syntax" in str(e).lower() else "preprocessing"
            pipeline.build_stats.add_warning(str(page.source_path), str(e), error_type)
        else:
            logger.warning(
                "preprocessing_error",
                source_path=str(page.source_path),
                error=truncate_error(e),
                error_code=ErrorCode.R003.value,
                suggestion="Check page content for template syntax errors",
            )
        return source
