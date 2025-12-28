"""Math plugin for Patitas.

Adds support for LaTeX-style math expressions.

Usage:
    >>> md = create_markdown(plugins=["math"])
    >>> md("Inline: $E = mc^2$")
    '<p>Inline: <span class="math">E = mc^2</span></p>'
    >>> md("$$\\nE = mc^2\\n$$")
    '<div class="math-block">E = mc^2</div>'

Syntax:
    Inline math: $expression$
    Block math: $$expression$$ (on separate lines)

    Escaping:
    - \\$ for literal dollar sign
    - Inside code spans, $ is literal

Notes:
    - This plugin outputs semantic HTML classes
    - Actual math rendering (MathJax, KaTeX) is done client-side
    - Block math with display mode is on separate lines

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


@register_plugin("math")
class MathPlugin:
    """Plugin adding $math$ and $$math$$ support.

    Inline math uses $...$ syntax.
    Block math uses $$...$$ on separate lines.
    """

    @property
    def name(self) -> str:
        return "math"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """Enable math detection in lexer."""
        lexer_class._math_enabled = True

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Enable math parsing."""
        parser_class._math_enabled = True

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Math rendering is handled in base renderer."""
        pass


# Math parsing is integrated into lexer and parser.
# See:
# - lexer.py: _scan_math_block()
# - parser.py: _parse_inline_math(), _parse_math_block()
# - nodes.py: Math, MathBlock
