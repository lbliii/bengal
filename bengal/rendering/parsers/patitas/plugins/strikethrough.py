"""Strikethrough plugin for Patitas.

Adds support for ~~deleted~~ syntax.

Usage:
    >>> md = create_markdown(plugins=["strikethrough"])
    >>> md("~~deleted text~~")
    '<p><del>deleted text</del></p>'

Syntax:
~~text~~ → <del>text</del>

Strikethrough can contain other inline elements:
~~**bold deleted**~~ → <del><strong>bold deleted</strong></del>

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


@register_plugin("strikethrough")
class StrikethroughPlugin:
    """Plugin adding ~~strikethrough~~ support.
    
    Extends inline parsing to recognize ~~ delimiters.
        
    """

    @property
    def name(self) -> str:
        return "strikethrough"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """No lexer extension needed - handled in inline parsing."""
        pass

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Add strikethrough to inline special characters."""
        # Add ~ to inline special chars for recognition
        # The parser will handle the actual parsing
        pass

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """No renderer extension needed - handled in base renderer."""
        pass


# The actual parsing is integrated into the parser's inline handling.
# See parser.py _parse_inline_content() for the ~~ handling.
# The Strikethrough node is defined in nodes.py.
