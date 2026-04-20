"""
HTML overlay renderer for build errors (Sprint A3.1).

Produces a self-contained HTML page that displays a
:class:`bengal.rendering.errors.TemplateRenderError` with the same data
the terminal renderer surfaces:

- ``[R0XX]`` ErrorCode badge + human-readable error-type label
- File / template name + line:column location
- Source code window with line numbers, error-line highlight, caret
- Primary suggestion (rendered as a "Tip")
- Suggested alternatives (Levenshtein top-N)
- Inclusion chain
- Source page that triggered the error
- Template search paths
- Documentation URL (when an ErrorCode is set)
- Collapsible Python traceback (when ``error._show_traceback`` is set)

The HTML is intentionally inline-styled and JS-free in A3.1. A3.2 will
inject a tiny SSE listener via the ``reload_script`` placeholder so the
overlay self-dismisses on the next ``build_ok``.

The renderer is pure: no I/O beyond the one-shot template load; no
mutation of the error object.
"""

from __future__ import annotations

import html
from importlib import resources
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.errors import TemplateRenderError


__all__ = ["render_error_page"]


_ERROR_TYPE_LABELS: dict[str, str] = {
    "syntax": "Template Syntax Error",
    "filter": "Unknown Filter",
    "undefined": "Undefined Variable",
    "runtime": "Template Runtime Error",
    "callable": "None Is Not Callable",
    "none_access": "None Is Not Iterable",
    "type_comparison": "Type Comparison Error",
    "include_missing": "Include Not Found",
    "circular_include": "Circular Include",
    "other": "Template Error",
}


def render_error_page(
    error: TemplateRenderError,
    *,
    page_title: str = "Build Error — Bengal",
    reload_script: str = "",
) -> str:
    """Render a self-contained HTML page for a :class:`TemplateRenderError`.

    Args:
        error: The error to display.
        page_title: ``<title>`` text. Defaults to a generic build-error label.
        reload_script: Optional ``<script>...</script>`` string injected
            after ``<body>``. A3.2 will pass an SSE listener here.

    Returns:
        A complete ``<!doctype html>`` document as a string.
    """
    template_str = _load_template()

    code_obj = getattr(error, "code", None)
    code_badge = code_obj.name if code_obj else "ERROR"

    error_type_label = _ERROR_TYPE_LABELS.get(error.error_type, "Template Error")

    title_html = html.escape(str(error.message))

    file_loc_html = _render_file_loc(error)
    frame_section = _render_frame_section(error)
    message_section = _render_message_section(error)
    hint_section = _render_hint_section(error)
    alternatives_section = _render_alternatives_section(error)
    chain_section = _render_chain_section(error)
    page_source_section = _render_page_source_section(error)
    search_paths_section = _render_search_paths_section(error)
    docs_section = _render_docs_section(error)
    stack_section = _render_stack_section(error)

    return Template(template_str).substitute(
        page_title=html.escape(page_title),
        code_badge=html.escape(code_badge),
        error_type_label=html.escape(error_type_label),
        title_html=title_html,
        file_loc_html=file_loc_html,
        frame_section=frame_section,
        message_section=message_section,
        hint_section=hint_section,
        alternatives_section=alternatives_section,
        chain_section=chain_section,
        page_source_section=page_source_section,
        search_paths_section=search_paths_section,
        docs_section=docs_section,
        stack_section=stack_section,
        reload_script=reload_script,
    )


def _load_template() -> str:
    """Read the bundled error.html template via importlib.resources."""
    return (
        resources.files("bengal.errors.overlay.templates")
        .joinpath("error.html")
        .read_text(encoding="utf-8")
    )


def _render_file_loc(error: TemplateRenderError) -> str:
    ctx = error.template_context
    if ctx.template_path:
        location = html.escape(str(ctx.template_path))
    else:
        location = html.escape(ctx.template_name or "(unknown template)")
    if ctx.line_number:
        location += f":{ctx.line_number}"
        if ctx.column:
            location += f":{ctx.column}"
    return f"<strong>{location}</strong>"


def _render_frame_section(error: TemplateRenderError) -> str:
    ctx = error.template_context
    if not ctx.surrounding_lines:
        return ""

    line_html: list[str] = []
    error_line_no = ctx.line_number
    for line_num, content in ctx.surrounding_lines:
        is_error = line_num == error_line_no
        cls = "line is-error" if is_error else "line"
        ln_html = f'<span class="ln">{line_num:>4}</span>{html.escape(content)}'
        line_html.append(f'<span class="{cls}">{ln_html}</span>')

        if is_error and ctx.source_line:
            stripped = ctx.source_line.lstrip()
            indent_offset = len(ctx.source_line) - len(stripped)
            caret_count = max(1, min(len(stripped), 40))
            caret_padding = " " * indent_offset
            caret = (
                '<span class="line">'
                '<span class="ln"></span>'
                '<span class="caret">'
                f"{caret_padding}{'^' * caret_count}"
                "</span></span>"
            )
            line_html.append(caret)

    body = "".join(line_html)
    return f'<section class="panel"><header>Code</header><pre class="frame">{body}</pre></section>'


def _render_message_section(error: TemplateRenderError) -> str:
    msg = html.escape(str(error.message))
    return f'<section class="panel"><header>Error</header><div class="body">{msg}</div></section>'


def _render_hint_section(error: TemplateRenderError) -> str:
    suggestion = getattr(error, "suggestion", None)
    if not suggestion:
        return ""
    return (
        '<section class="panel"><header>Hint</header>'
        f'<div class="body hint">{html.escape(str(suggestion))}</div></section>'
    )


def _render_alternatives_section(error: TemplateRenderError) -> str:
    alternatives = getattr(error, "available_alternatives", None) or []
    if not alternatives:
        return ""
    top, *rest = alternatives
    parts: list[str] = [
        f'<p class="alt-top">Did you mean '
        f'<code class="alt-top-name">{html.escape(str(top))}</code>?</p>'
    ]
    if rest:
        items = "".join(f"<li>{html.escape(str(alt))}</li>" for alt in rest)
        parts.append(
            f'<p class="alt-others-label">Other close matches:</p><ul class="alts">{items}</ul>'
        )
    return (
        '<section class="panel"><header>Did you mean?</header>'
        f'<div class="body">{"".join(parts)}</div></section>'
    )


def _render_chain_section(error: TemplateRenderError) -> str:
    chain = getattr(error, "inclusion_chain", None)
    if not chain:
        return ""
    items: list[str] = []
    for name, line_num in chain.entries:
        loc = f":{line_num}" if line_num else ""
        items.append(f"<li><strong>{html.escape(name)}</strong>{loc}</li>")
    return (
        '<section class="panel"><header>Template Chain</header>'
        f'<div class="body"><ol class="chain">{"".join(items)}</ol></div></section>'
    )


def _render_page_source_section(error: TemplateRenderError) -> str:
    page_source = getattr(error, "page_source", None)
    if not page_source:
        return ""
    return (
        '<section class="panel"><header>Used by Page</header>'
        f'<div class="body file-loc">{html.escape(str(page_source))}</div></section>'
    )


def _render_search_paths_section(error: TemplateRenderError) -> str:
    paths = getattr(error, "search_paths", None) or []
    if not paths:
        return ""
    ctx = error.template_context
    items: list[str] = []
    for i, path in enumerate(paths, 1):
        marker = ""
        try:
            if ctx.template_path and ctx.template_path.is_relative_to(path):
                marker = ' <span class="hint">&larr; found here</span>'
        except TypeError, ValueError:
            pass
        items.append(f"<li>{i}. {html.escape(str(path))}{marker}</li>")
    return (
        '<section class="panel"><header>Template Search Paths</header>'
        '<div class="body file-loc">'
        f'<ul style="list-style:none;margin:0;padding:0">{"".join(items)}</ul>'
        "</div></section>"
    )


def _render_docs_section(error: TemplateRenderError) -> str:
    code_obj = getattr(error, "code", None)
    if not code_obj:
        return ""
    docs_url = f"https://lbliii.github.io/bengal{code_obj.docs_url}"
    return (
        '<section class="panel"><header>Documentation</header>'
        '<div class="body">'
        f'<a href="{html.escape(docs_url)}" target="_blank" rel="noopener">'
        f"{html.escape(docs_url)}</a>"
        "</div></section>"
    )


def _render_stack_section(error: TemplateRenderError) -> str:
    if not getattr(error, "_show_traceback", False):
        return ""
    original = getattr(error, "_original_exception", None)
    if original is None:
        return ""
    import traceback as _tb

    tb_lines = _tb.format_exception(type(original), original, original.__traceback__)
    body = html.escape("".join(tb_lines))
    return (
        '<section class="panel"><header>Stack Trace</header>'
        '<div class="body">'
        '<details class="stack" open>'
        "<summary>Show full Python traceback</summary>"
        f'<pre class="stack-body">{body}</pre>'
        "</details></div></section>"
    )
