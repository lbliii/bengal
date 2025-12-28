"""HTML renderer using StringBuilder pattern.

Renders typed AST to HTML with O(n) performance using StringBuilder.

Thread Safety:
    All state is local to each render() call.
    Multiple threads can render concurrently without synchronization.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from html import escape as html_escape
from typing import TYPE_CHECKING, Literal

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Directive,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
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
    Math,
    MathBlock,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableRow,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.directives.registry import DirectiveRegistry
    from bengal.rendering.parsers.patitas.roles.registry import RoleRegistry


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

    __slots__ = (
        "_highlight",
        "_highlight_style",
        "_rosettes_available",
        "_directive_registry",
        "_role_registry",
    )

    def __init__(
        self,
        *,
        highlight: bool = False,
        highlight_style: Literal["semantic", "pygments"] = "semantic",
        directive_registry: DirectiveRegistry | None = None,
        role_registry: RoleRegistry | None = None,
    ) -> None:
        """Initialize renderer.

        Args:
            highlight: Enable syntax highlighting for code blocks
            highlight_style: Highlighting style ("semantic" or "pygments")
            directive_registry: Optional registry for custom directive rendering
            role_registry: Optional registry for custom role rendering
        """
        self._highlight = highlight
        self._highlight_style = highlight_style
        self._rosettes_available: bool | None = None
        self._directive_registry = directive_registry
        self._role_registry = role_registry

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
                sb.append(f"<pre><code>{_escape_html(code)}</code></pre>\n")

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

            case Directive() as directive:
                self._render_directive(directive, sb)

            case Table() as table:
                self._render_table(table, sb)

            case MathBlock(content=content):
                # Render as div with math-block class (for MathJax/KaTeX)
                sb.append('<div class="math-block">\n')
                sb.append(_escape_html(content))
                sb.append("\n</div>\n")

            case FootnoteDef():
                # Footnote definitions are collected and rendered at document end
                pass  # Handled in post-processing

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

    def _render_table(self, table: Table, sb: StringBuilder) -> None:
        """Render a table with thead and tbody."""
        sb.append("<table>\n")

        # Render header rows
        if table.head:
            sb.append("<thead>\n")
            for row in table.head:
                self._render_table_row(row, table.alignments, sb, is_header=True)
            sb.append("</thead>\n")

        # Render body rows
        if table.body:
            sb.append("<tbody>\n")
            for row in table.body:
                self._render_table_row(row, table.alignments, sb, is_header=False)
            sb.append("</tbody>\n")

        sb.append("</table>\n")

    def _render_table_row(
        self,
        row: TableRow,
        alignments: tuple[str | None, ...],
        sb: StringBuilder,
        is_header: bool,
    ) -> None:
        """Render a table row."""
        sb.append("<tr>")
        tag = "th" if is_header else "td"

        for i, cell in enumerate(row.cells):
            align = alignments[i] if i < len(alignments) else None
            if align:
                sb.append(f'<{tag} style="text-align: {align}">')
            else:
                sb.append(f"<{tag}>")
            self._render_inline_children(cell.children, sb)
            sb.append(f"</{tag}>")

        sb.append("</tr>\n")

    def _render_directive(self, node: Directive, sb: StringBuilder) -> None:
        """Render a directive block.

        Uses registered handler if available, otherwise falls back to default.
        """
        # Pre-render children
        children_sb = StringBuilder()
        for child in node.children:
            self._render_block(child, children_sb)
        rendered_children = children_sb.build()

        # Check for registered handler
        if self._directive_registry:
            handler = self._directive_registry.get(node.name)
            if handler and hasattr(handler, "render"):
                handler.render(node, rendered_children, sb)
                return

        # Default rendering
        sb.append(f'<div class="directive directive-{_escape_attr(node.name)}">')
        if node.title:
            sb.append(f'<p class="directive-title">{_escape_html(node.title)}</p>')
        sb.append(rendered_children)
        sb.append("</div>\n")

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
        """Render inline children using dict dispatch for speed."""
        # Local references for tight loop
        dispatch = _INLINE_DISPATCH
        render_children = self._render_inline_children
        for child in children:
            handler = dispatch.get(type(child))
            if handler:
                handler(child, sb, render_children)

    def _render_inline(self, node: Inline, sb: StringBuilder) -> None:
        """Render an inline node using dict dispatch."""
        handler = _INLINE_DISPATCH.get(type(node))
        if handler:
            handler(node, sb, self._render_inline_children)

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


# =============================================================================
# Inline dispatch handlers (dict dispatch is ~2x faster than match statement)
# =============================================================================


def _render_text(node: Text, sb: StringBuilder, render_children) -> None:
    sb.append(_escape_html(node.content))


def _render_emphasis(node: Emphasis, sb: StringBuilder, render_children) -> None:
    sb.append("<em>")
    render_children(node.children, sb)
    sb.append("</em>")


def _render_strong(node: Strong, sb: StringBuilder, render_children) -> None:
    sb.append("<strong>")
    render_children(node.children, sb)
    sb.append("</strong>")


def _render_link(node: Link, sb: StringBuilder, render_children) -> None:
    sb.append(f'<a href="{_escape_attr(node.url)}"')
    if node.title:
        sb.append(f' title="{_escape_attr(node.title)}"')
    sb.append(">")
    render_children(node.children, sb)
    sb.append("</a>")


def _render_image(node: Image, sb: StringBuilder, render_children) -> None:
    sb.append(f'<img src="{_escape_attr(node.url)}" alt="{_escape_attr(node.alt)}"')
    if node.title:
        sb.append(f' title="{_escape_attr(node.title)}"')
    sb.append(" />")


def _render_code_span(node: CodeSpan, sb: StringBuilder, render_children) -> None:
    sb.append(f"<code>{_escape_html(node.code)}</code>")


def _render_line_break(node: LineBreak, sb: StringBuilder, render_children) -> None:
    sb.append("<br />\n")


def _render_soft_break(node: SoftBreak, sb: StringBuilder, render_children) -> None:
    sb.append("\n")


def _render_html_inline(node: HtmlInline, sb: StringBuilder, render_children) -> None:
    sb.append(node.html)


def _render_role(node: Role, sb: StringBuilder, render_children) -> None:
    # Default role rendering - can be overridden by registry
    sb.append(
        f'<span class="role role-{_escape_attr(node.name)}">{_escape_html(node.content)}</span>'
    )


# =============================================================================
# Plugin inline dispatch handlers
# =============================================================================


def _render_strikethrough(node: Strikethrough, sb: StringBuilder, render_children) -> None:
    sb.append("<del>")
    render_children(node.children, sb)
    sb.append("</del>")


def _render_math(node: Math, sb: StringBuilder, render_children) -> None:
    # Inline math - rendered with span.math class for MathJax/KaTeX
    sb.append(f'<span class="math">{_escape_html(node.content)}</span>')


def _render_footnote_ref(node: FootnoteRef, sb: StringBuilder, render_children) -> None:
    # Footnote reference - links to footnote definition
    identifier = _escape_attr(node.identifier)
    sb.append(
        f'<sup><a href="#fn-{identifier}" id="fnref-{identifier}">{_escape_html(node.identifier)}</a></sup>'
    )


# Type -> handler dispatch table (O(1) lookup, faster than match)
_INLINE_DISPATCH = {
    Text: _render_text,
    Emphasis: _render_emphasis,
    Strong: _render_strong,
    Link: _render_link,
    Image: _render_image,
    CodeSpan: _render_code_span,
    LineBreak: _render_line_break,
    SoftBreak: _render_soft_break,
    HtmlInline: _render_html_inline,
    Role: _render_role,
    # Plugin nodes
    Strikethrough: _render_strikethrough,
    Math: _render_math,
    FootnoteRef: _render_footnote_ref,
}
