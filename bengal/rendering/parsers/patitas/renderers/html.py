"""HTML renderer using StringBuilder pattern.

Renders typed AST to HTML with O(n) performance using StringBuilder.

Thread Safety:
    All state is local to each render() call.
    Multiple threads can render concurrently without synchronization.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from html import escape as html_escape
from typing import Literal

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Directive,
    Emphasis,
    FencedCode,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    LineBreak,
    Link,
    List,
    ListItem,
    Paragraph,
    Role,
    SoftBreak,
    Strong,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


class HtmlRenderer:
    """Render AST to HTML using StringBuilder pattern.

    O(n) rendering using StringBuilder for string accumulation.
    All state is local to each render() call.

    Usage:
        >>> from bengal.rendering.parsers.patitas import parse_to_ast
        >>> ast = parse_to_ast("# Hello **World**")
        >>> renderer = HtmlRenderer()
        >>> html = renderer.render(ast)
        '<h1>Hello <strong>World</strong></h1>\\n'

    Thread Safety:
        Multiple threads can render concurrently without synchronization.
        Each call creates independent StringBuilder.
    """

    __slots__ = ("_highlight", "_highlight_style", "_rosettes_available")

    def __init__(
        self,
        *,
        highlight: bool = False,
        highlight_style: Literal["semantic", "pygments"] = "semantic",
    ) -> None:
        """Initialize renderer.

        Args:
            highlight: Enable syntax highlighting for code blocks
            highlight_style: Highlighting style ("semantic" or "pygments")
        """
        self._highlight = highlight
        self._highlight_style = highlight_style
        self._rosettes_available: bool | None = None

    def render(self, nodes: Sequence[Block]) -> str:
        """Render AST nodes to HTML.

        Args:
            nodes: Sequence of Block AST nodes

        Returns:
            Rendered HTML string
        """
        sb = StringBuilder()
        for node in nodes:
            self._render_block(node, sb)
        return sb.build()

    def _render_block(self, node: Block, sb: StringBuilder) -> None:
        """Render a block node to StringBuilder."""
        match node:
            case Heading(level=level, children=children):
                sb.append(f"<h{level}>")
                self._render_inline_children(children, sb)
                sb.append(f"</h{level}>\n")

            case Paragraph(children=children):
                sb.append("<p>")
                self._render_inline_children(children, sb)
                sb.append("</p>\n")

            case FencedCode(code=code, info=info):
                self._render_fenced_code(code, info, sb)

            case IndentedCode(code=code):
                sb.append("<pre><code>")
                sb.append(_escape_html(code))
                sb.append("</code></pre>\n")

            case BlockQuote(children=children):
                sb.append("<blockquote>\n")
                for child in children:
                    self._render_block(child, sb)
                sb.append("</blockquote>\n")

            case List(items=items, ordered=ordered, start=start, tight=tight):
                if ordered:
                    if start != 1:
                        sb.append(f'<ol start="{start}">\n')
                    else:
                        sb.append("<ol>\n")
                else:
                    sb.append("<ul>\n")

                for item in items:
                    self._render_list_item(item, sb, tight)

                if ordered:
                    sb.append("</ol>\n")
                else:
                    sb.append("</ul>\n")

            case ThematicBreak():
                sb.append("<hr />\n")

            case HtmlBlock(html=html):
                sb.append(html)
                if not html.endswith("\n"):
                    sb.append("\n")

            case Directive(name=name, title=title, children=children):
                # Basic directive rendering (can be extended)
                sb.append(f'<div class="directive directive-{_escape_attr(name)}">')
                if title:
                    sb.append(f'<p class="directive-title">{_escape_html(title)}</p>')
                for child in children:
                    self._render_block(child, sb)
                sb.append("</div>\n")

    def _render_list_item(self, item: ListItem, sb: StringBuilder, tight: bool) -> None:
        """Render a list item."""
        sb.append("<li>")

        if item.checked is not None:
            # Task list item
            checked = "checked" if item.checked else ""
            sb.append(f'<input type="checkbox" disabled {checked}/> ')

        if tight:
            # Tight list: render children without paragraph wrapper
            for child in item.children:
                if isinstance(child, Paragraph):
                    self._render_inline_children(child.children, sb)
                else:
                    self._render_block(child, sb)
        else:
            # Loose list: include paragraph wrappers
            for child in item.children:
                self._render_block(child, sb)

        sb.append("</li>\n")

    def _render_fenced_code(self, code: str, info: str | None, sb: StringBuilder) -> None:
        """Render fenced code block with optional highlighting."""
        if self._highlight and info:
            highlighted = self._try_highlight(code, info)
            if highlighted:
                sb.append(highlighted)
                return

        # Plain code block
        sb.append("<pre><code")
        if info:
            # Extract language (first word of info string)
            lang = info.split()[0] if info else ""
            if lang:
                sb.append(f' class="language-{_escape_attr(lang)}"')
        sb.append(">")
        sb.append(_escape_html(code))
        sb.append("</code></pre>\n")

    def _try_highlight(self, code: str, info: str) -> str | None:
        """Try to highlight code using rosettes.

        Returns highlighted HTML or None if highlighting unavailable.
        """
        # Check rosettes availability (cached)
        if self._rosettes_available is None:
            try:
                import rosettes  # noqa: F401

                self._rosettes_available = True
            except ImportError:
                self._rosettes_available = False

        if not self._rosettes_available:
            return None

        lang = info.split()[0] if info else ""
        if not lang:
            return None

        try:
            from rosettes import highlight

            return highlight(
                code,
                lang,
                css_class_style=self._highlight_style,
            )
        except (LookupError, ValueError):
            # Language not supported or other error
            return None

    def _render_inline_children(self, children: Sequence[Inline], sb: StringBuilder) -> None:
        """Render inline children."""
        for child in children:
            self._render_inline(child, sb)

    def _render_inline(self, node: Inline, sb: StringBuilder) -> None:
        """Render an inline node."""
        match node:
            case Text(content=content):
                sb.append(_escape_html(content))

            case Emphasis(children=children):
                sb.append("<em>")
                self._render_inline_children(children, sb)
                sb.append("</em>")

            case Strong(children=children):
                sb.append("<strong>")
                self._render_inline_children(children, sb)
                sb.append("</strong>")

            case Link(url=url, title=title, children=children):
                sb.append(f'<a href="{_escape_attr(url)}"')
                if title:
                    sb.append(f' title="{_escape_attr(title)}"')
                sb.append(">")
                self._render_inline_children(children, sb)
                sb.append("</a>")

            case Image(url=url, alt=alt, title=title):
                sb.append(f'<img src="{_escape_attr(url)}" alt="{_escape_attr(alt)}"')
                if title:
                    sb.append(f' title="{_escape_attr(title)}"')
                sb.append(" />")

            case CodeSpan(code=code):
                sb.append("<code>")
                sb.append(_escape_html(code))
                sb.append("</code>")

            case LineBreak():
                sb.append("<br />\n")

            case SoftBreak():
                sb.append("\n")

            case HtmlInline(html=html):
                sb.append(html)

            case Role(name=name, content=content):
                # Basic role rendering
                sb.append(f'<span class="role role-{_escape_attr(name)}">')
                sb.append(_escape_html(content))
                sb.append("</span>")

    def iter_blocks(self, nodes: Sequence[Block]) -> Iterator[str]:
        """Iterate over rendered blocks.

        Yields HTML for each block node. Useful for streaming.

        Args:
            nodes: Sequence of Block AST nodes

        Yields:
            HTML string for each block
        """

        for node in nodes:
            sb = StringBuilder()
            self._render_block(node, sb)
            yield sb.build()


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html_escape(text, quote=False)


def _escape_attr(text: str) -> str:
    """Escape HTML attribute value."""
    return html_escape(text, quote=True)
