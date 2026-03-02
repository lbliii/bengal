"""Block-level rendering mixin.

Provides block node rendering methods as a mixin class.
Uses mixin pattern to avoid method call overhead in the hot render path.

Thread-safe: all state is local to each render() call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from patitas.nodes import (
    Block,
    BlockQuote,
    FencedCode,
    FootnoteDef,
    Heading,
    HtmlBlock,
    IndentedCode,
    List,
    ListItem,
    MathBlock,
    Paragraph,
    Table,
    TableRow,
    ThematicBreak,
)
from patitas.stringbuilder import StringBuilder

from bengal.parsing.backends.patitas.accumulator import get_metadata
from bengal.parsing.backends.patitas.renderers.utils import (
    HeadingInfo,
    escape_attr,
    escape_html,
)
from bengal.utils.primitives.code import HL_LINES_PATTERN, parse_hl_lines

if TYPE_CHECKING:
    from bengal.parsing.backends.patitas.renderers.protocols import HtmlRendererProtocol

# Alias for internal use (maintains backward compatibility)
_HL_LINES_PATTERN = HL_LINES_PATTERN
_parse_hl_lines = parse_hl_lines


def _parse_code_info(info: str) -> tuple[str, list[int]]:
    """Parse code fence info string for language and line highlights.

    Args:
        info: Code fence info string (e.g., "python {1,3-5}")

    Returns:
        Tuple of (language, hl_lines list)
    """
    if not info:
        return "", []

    match = _HL_LINES_PATTERN.match(info.strip())
    if match:
        lang = match.group(1)
        hl_spec = match.group(2)
        hl_lines = _parse_hl_lines(hl_spec) if hl_spec else []
        return lang, hl_lines

    # Fallback: just take first word as language
    return info.split()[0], []


class BlockRendererMixin:
    """Mixin providing block-level rendering methods.

    Expects the parent class to provide:
    - _source: str
    - _headings: list[HeadingInfo]
    - _seen_slugs: dict[str, int]
    - _highlight: bool
    - _highlight_style: str
    - _rosettes_available: bool
    - _delegate: Optional[LexerDelegate]
    - _heading_slugify: Callable[[str], str]
    - _render_inline_children(children, sb): method
    - _render_directive(node, sb): method
    - _extract_plain_text(children): method
    - _get_unique_slug(text): method
    """

    def _render_block(self: HtmlRendererProtocol, node: Block, sb: StringBuilder) -> None:
        """Render a block node to StringBuilder."""
        match node:
            case Heading(level=level, children=children, explicit_id=explicit_id):
                # Extract text and generate slug during AST walk
                text = self._extract_plain_text(children)

                # Use explicit ID if provided (parsed from {#custom-id} syntax)
                slug = explicit_id or self._get_unique_slug(text)

                # Collect heading info for TOC generation
                self._headings.append(HeadingInfo(level=level, text=text, slug=slug))

                # Emit heading with ID already included
                sb.append(f'<h{level} id="{slug}">')
                self._render_inline_children(children, sb)
                sb.append(f"</h{level}>\n")

            case Paragraph(children=children):
                sb.append("<p>")
                self._render_inline_children(children, sb)
                sb.append("</p>\n")

            case FencedCode() as node:
                self._render_fenced_code(node, sb)

            case IndentedCode(code=code):
                # CommonMark: code block content always ends with newline before </code>
                escaped = escape_html(code)
                if not escaped.endswith("\n"):
                    escaped += "\n"
                sb.append(f"<pre><code>{escaped}</code></pre>\n")

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

            case Table() as table:
                self._render_table(table, sb)

            case MathBlock(content=content):
                # Accumulate metadata if context is active
                meta = get_metadata()
                if meta:
                    meta.has_math = True

                # Render as div with math-block class (for MathJax/KaTeX)
                sb.append('<div class="math-block">\n')
                sb.append(escape_html(content))
                sb.append("\n</div>\n")

            case FootnoteDef():
                # Footnote definitions are collected and rendered at document end
                pass  # Handled in post-processing

            case _:
                # Handle Directive separately (to avoid circular import)
                from patitas.nodes import Directive

                if isinstance(node, Directive):
                    self._render_directive(node, sb)

    def _render_list_item(
        self: HtmlRendererProtocol, item: ListItem, sb: StringBuilder, tight: bool
    ) -> None:
        """Render a list item.

        Tight list items unwrap paragraphs but still render block elements with newlines.
        """
        if item.checked is not None:
            # Task list item - match Mistune's class names
            sb.append('<li class="task-list-item">')
            checked_attr = " checked" if item.checked else ""
            sb.append(
                f'<input class="task-list-item-checkbox" type="checkbox" disabled{checked_attr}/>'
            )
        else:
            sb.append("<li>")
            # Empty list items should render as <li></li> without newline
            if not item.children:
                sb.append("</li>\n")
                return

            # For tight lists: add newline if item has non-paragraph block elements
            # For loose lists: always add newline
            if not tight:
                sb.append("\n")
            elif item.children and not isinstance(item.children[0], Paragraph):
                # Tight list but first child is a block element (like thematic break)
                sb.append("\n")

        if tight:
            # Tight list: render children without paragraph wrapper
            for i, child in enumerate(item.children):
                if isinstance(child, Paragraph):
                    self._render_inline_children(child.children, sb)
                    # Add newline before next block element (like nested list)
                    if i + 1 < len(item.children) and not isinstance(
                        item.children[i + 1], Paragraph
                    ):
                        sb.append("\n")
                else:
                    self._render_block(child, sb)
        else:
            # Loose list: include paragraph wrappers
            for child in item.children:
                self._render_block(child, sb)

        sb.append("</li>\n")

    def _render_table(self: HtmlRendererProtocol, table: Table, sb: StringBuilder) -> None:
        """Render a table with thead and tbody."""
        # Accumulate metadata if context is active
        meta = get_metadata()
        if meta:
            meta.has_tables = True

        # Wrap in table-wrapper for horizontal scrolling on narrow screens
        sb.append('<div class="table-wrapper"><table>\n')

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

        sb.append("</table></div>")

    def _render_table_row(
        self: HtmlRendererProtocol,
        row: TableRow,
        alignments: tuple[str | None, ...],
        sb: StringBuilder,
        is_header: bool,
    ) -> None:
        """Render a table row with pretty-printing (matching Mistune)."""
        sb.append("<tr>\n")
        tag = "th" if is_header else "td"

        for i, cell in enumerate(row.cells):
            align = alignments[i] if i < len(alignments) else None
            if align:
                sb.append(f'  <{tag} style="text-align: {align}">')
            else:
                sb.append(f"  <{tag}>")
            self._render_inline_children(cell.children, sb)
            sb.append(f"</{tag}>\n")

        sb.append("</tr>\n")

    def _render_footnotes_section(
        self: HtmlRendererProtocol, footnotes: list[FootnoteDef], sb: StringBuilder
    ) -> None:
        """Render footnote definitions as a section at the end of the document."""
        sb.append('<section class="footnotes">\n<ol>\n')

        for fn in footnotes:
            identifier = escape_attr(fn.identifier)
            sb.append(f'<li id="fn-{identifier}">')

            # Render footnote content
            if fn.children:
                for child in fn.children:
                    if isinstance(child, Paragraph):
                        # Inline the paragraph content with back-reference
                        sb.append("<p>")
                        self._render_inline_children(child.children, sb)
                        sb.append(f'<a href="#fnref-{identifier}" class="footnote">&#8617;</a>')
                        sb.append("</p>")
                    else:
                        self._render_block(child, sb)

            sb.append("</li>\n")

        sb.append("</ol>\n</section>\n")

    def _render_fenced_code(
        self: HtmlRendererProtocol,
        node: FencedCode,
        sb: StringBuilder,
    ) -> None:
        """Render fenced code block with optional zero-copy highlighting."""
        from html import unescape as html_unescape

        info = node.info
        lang = info.split()[0].lower() if info else None

        # Accumulate metadata if context is active
        meta = get_metadata()
        if meta:
            meta.add_code_block(lang)

        if lang == "mermaid":
            sb.append(f'<div class="mermaid">{escape_html(node.get_code(self._source))}</div>\n')
            return

        # Attempt syntax highlighting via delegate (ZCLH protocol)
        if self._delegate and info:
            lang = info.split()[0].lower()
            if self._delegate.supports_language(lang):
                tokens = self._delegate.tokenize_range(
                    self._source,
                    node.source_start,
                    node.source_end,
                    lang,
                )
                self._render_highlighted_tokens(tokens, lang, sb)
                return

        # Fallback: internal highlighting or plain code
        if self._highlight and info:
            # Strip trailing newline from code range before highlighting
            end = node.source_end
            if end > node.source_start and self._source[end - 1] == "\n":
                end -= 1
            highlighted = self._try_highlight_range(node.source_start, end, info)
            if highlighted:
                # Rosettes parity: ensure trailing newline before closing tags
                if highlighted.endswith("</code></pre></div>"):
                    highlighted = highlighted[:-19] + "\n</code></pre></div>"
                sb.append(highlighted)
                return

        # Plain code block extraction
        code = node.get_code(self._source)
        # Strip trailing newline from last line (parity with IndentedCode)
        if code.endswith("\n"):
            code = code[:-1]
        sb.append("<pre><code")
        if info:
            # CommonMark: decode HTML entities in info string before using as class
            lang = html_unescape(info.split()[0])
            if lang:
                sb.append(f' class="language-{escape_attr(lang)}"')
        sb.append(">")
        sb.append(escape_html(code))
        # CommonMark: empty code blocks have no trailing newline
        if code:
            sb.append("\n</code></pre>\n")
        else:
            sb.append("</code></pre>\n")

    def _render_highlighted_tokens(
        self: HtmlRendererProtocol,
        tokens: Any,
        language: str,
        sb: StringBuilder,
    ) -> None:
        """Render tokens from a sub-lexer delegate."""
        # This assumes tokens are compatible with rosettes format
        # but we wrap them in standard containers for safety.
        sb.append(f'<div class="highlight {self._highlight_style}"><pre>')
        sb.append(f'<code class="language-{escape_attr(language)}">')

        # Basic token rendering if not already stringified
        for token in tokens:
            if hasattr(token, "html"):
                sb.append(token.html)
            elif hasattr(token, "value"):
                # Handle basic token objects (type, value)
                cls = f' class="token {getattr(token, "type", "text")}"'
                sb.append(f"<span{cls}>{escape_html(token.value)}</span>")
            else:
                sb.append(escape_html(str(token)))

        sb.append("\n</code></pre></div>\n")

    def _try_highlight_range(
        self: HtmlRendererProtocol, start: int, end: int, info: str
    ) -> str | None:
        """Try to highlight a source range using internal rosettes.

        Uses rosettes_available from RenderConfig (computed once at module import).

        Supports line highlighting syntax: python {1,3-5}
        """
        if not self._rosettes_available:
            return None

        lang, hl_lines = _parse_code_info(info)
        if not lang:
            return None

        try:
            from rosettes import highlight

            return highlight(
                self._source,
                lang,
                css_class_style=self._highlight_style,
                start=start,
                end=end,
                hl_lines=frozenset(hl_lines) if hl_lines else None,
            )
        except (LookupError, ValueError):
            return None
