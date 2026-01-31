"""Inline rendering dispatch handlers.

Provides high-performance inline node rendering using dict dispatch.
Dict dispatch is ~2x faster than match statements for inline rendering.

Thread-safe: all handlers are pure functions with no shared mutable state.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from patitas.nodes import (
    CodeSpan,
    Emphasis,
    FootnoteRef,
    HtmlInline,
    Image,
    LineBreak,
    Link,
    Math,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Text,
)
from patitas.stringbuilder import StringBuilder

from bengal.parsing.backends.patitas.accumulator import get_metadata
from bengal.parsing.backends.patitas.renderers.utils import (
    encode_url,
    escape_attr,
    escape_html,
    escape_link_title,
)

if TYPE_CHECKING:
    pass

# Type alias for inline render handler
InlineHandler = Callable[[Any, StringBuilder, Callable], None]


def render_text(node: Text, sb: StringBuilder, render_children: Callable) -> None:
    """Render text node with optional transformation."""
    # Use text_transformer if provided (e.g., for variable substitution)
    # This happens BEFORE HTML escaping to allow variables to contain HTML (e.g. icons)
    # but the renderer will then escape the result for safety.
    # Note: VariableSubstitutionPlugin handles its own safety checks.
    content = node.content
    renderer = getattr(render_children, "__self__", None)
    if renderer and hasattr(renderer, "_text_transformer") and renderer._text_transformer:
        content = renderer._text_transformer(content)

    # Accumulate word count if metadata context is active
    meta = get_metadata()
    if meta:
        meta.add_words(content)

    sb.append(escape_html(content))


def render_emphasis(node: Emphasis, sb: StringBuilder, render_children: Callable) -> None:
    """Render emphasis (<em>)."""
    sb.append("<em>")
    render_children(node.children, sb)
    sb.append("</em>")


def render_strong(node: Strong, sb: StringBuilder, render_children: Callable) -> None:
    """Render strong emphasis (<strong>)."""
    sb.append("<strong>")
    render_children(node.children, sb)
    sb.append("</strong>")


def render_link(node: Link, sb: StringBuilder, render_children: Callable) -> None:
    """Render link (<a>)."""
    # Accumulate link metadata if context is active
    meta = get_metadata()
    if meta:
        if node.url.startswith(("http://", "https://")):
            meta.add_external_link(node.url)
        else:
            meta.add_internal_link(node.url)

    sb.append(f'<a href="{encode_url(node.url)}"')
    if node.title:
        sb.append(f' title="{escape_link_title(node.title)}"')
    sb.append(">")
    render_children(node.children, sb)
    sb.append("</a>")


def render_image(node: Image, sb: StringBuilder, render_children: Callable) -> None:
    """Render image (<img>)."""
    # Accumulate image metadata if context is active
    meta = get_metadata()
    if meta:
        meta.add_image(node.url)

    sb.append(f'<img src="{encode_url(node.url)}" alt="{escape_attr(node.alt)}"')
    if node.title:
        sb.append(f' title="{escape_link_title(node.title)}"')
    sb.append(" />")


def render_code_span(node: CodeSpan, sb: StringBuilder, render_children: Callable) -> None:
    """Render inline code (<code>)."""
    sb.append(f"<code>{escape_html(node.code)}</code>")


def render_line_break(node: LineBreak, sb: StringBuilder, render_children: Callable) -> None:
    """Render hard line break (<br />)."""
    sb.append("<br />\n")


def render_soft_break(node: SoftBreak, sb: StringBuilder, render_children: Callable) -> None:
    """Render soft line break (newline)."""
    sb.append("\n")


def render_html_inline(node: HtmlInline, sb: StringBuilder, render_children: Callable) -> None:
    """Render raw HTML inline."""
    sb.append(node.html)


def render_role(node: Role, sb: StringBuilder, render_children: Callable) -> None:
    """Render default role (can be overridden by registry)."""
    sb.append(
        f'<span class="role role-{escape_attr(node.name)}">{escape_html(node.content)}</span>'
    )


def render_strikethrough(node: Strikethrough, sb: StringBuilder, render_children: Callable) -> None:
    """Render strikethrough (<del>)."""
    sb.append("<del>")
    render_children(node.children, sb)
    sb.append("</del>")


def render_math(node: Math, sb: StringBuilder, render_children: Callable) -> None:
    """Render inline math."""
    # Accumulate math metadata if context is active
    meta = get_metadata()
    if meta:
        meta.has_math = True

    # Inline math - rendered with span.math class for MathJax/KaTeX
    sb.append(f'<span class="math">{escape_html(node.content)}</span>')


def render_footnote_ref(node: FootnoteRef, sb: StringBuilder, render_children: Callable) -> None:
    """Render footnote reference (links to footnote definition, Mistune-compatible)."""
    identifier = escape_attr(node.identifier)
    sb.append(
        f'<sup class="footnote-ref" id="fnref-{identifier}">'
        f'<a href="#fn-{identifier}">{escape_html(node.identifier)}</a></sup>'
    )


# Type -> handler dispatch table (O(1) lookup, faster than match)
INLINE_DISPATCH: dict[type, InlineHandler] = {
    Text: render_text,
    Emphasis: render_emphasis,
    Strong: render_strong,
    Link: render_link,
    Image: render_image,
    CodeSpan: render_code_span,
    LineBreak: render_line_break,
    SoftBreak: render_soft_break,
    HtmlInline: render_html_inline,
    Role: render_role,
    # Plugin nodes
    Strikethrough: render_strikethrough,
    Math: render_math,
    FootnoteRef: render_footnote_ref,
}
