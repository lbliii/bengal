"""Footnotes plugin for Patitas.

Adds support for footnote references and definitions.

Usage:
    >>> md = create_markdown(plugins=["footnotes"])
    >>> md("Text with footnote[^1].\\n\\n[^1]: Footnote content.")
    '<p>Text with footnote<sup><a href="#fn-1">1</a></sup>.</p>...'

Syntax:
    Reference: [^identifier]
    Definition: [^identifier]: Content here

    Multi-line definitions:
    [^note]:
        First paragraph of footnote.

        Second paragraph with indent.

Features:
    - Numeric or named identifiers: [^1], [^note]
    - Footnotes collected and rendered at end
    - Back-references from footnote to text
    - Multi-paragraph footnotes with indentation

Thread Safety:
    This plugin is stateless and thread-safe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.plugins import register_plugin

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.lexer import Lexer
    from bengal.rendering.parsers.patitas.parser import Parser
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer


@register_plugin("footnotes")
class FootnotesPlugin:
    """Plugin adding [^1] footnote support.

    Footnotes are:
    1. Parsed as inline references [^id]
    2. Defined as block elements [^id]: content
    3. Rendered as a footnotes section at document end
    """

    @property
    def name(self) -> str:
        return "footnotes"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """Enable footnote detection in lexer."""
        lexer_class._footnotes_enabled = True

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Enable footnote parsing."""
        parser_class._footnotes_enabled = True

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Enable footnote section rendering."""
        renderer_class._footnotes_enabled = True


# Footnote parsing is integrated into lexer and parser.
# See:
# - lexer.py: _scan_footnote_def()
# - parser.py: _parse_footnote_ref(), _parse_footnote_def()
# - nodes.py: FootnoteRef, FootnoteDef
# - html.py: _render_footnotes_section()
