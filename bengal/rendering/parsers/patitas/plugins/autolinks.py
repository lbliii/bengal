"""Autolinks plugin for Patitas.

Adds support for automatic URL and email detection.

Usage:
    >>> md = create_markdown(plugins=["autolinks"])
    >>> md("Visit https://example.com for more info.")
    '<p>Visit <a href="https://example.com">https://example.com</a> for more info.</p>'

Syntax:
    URLs are automatically linked:
    - http://example.com
    - https://example.com
    - www.example.com

    Emails are automatically linked:
    - user@example.com

    Explicit autolinks (CommonMark):
    - <https://example.com>
    - <user@example.com>

Notes:
    - URLs in code spans are not autolinked
    - URLs in explicit links are not double-linked
    - Trailing punctuation is handled smartly

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


@register_plugin("autolinks")
class AutolinksPlugin:
    """Plugin for automatic URL and email linking.

    Extends inline parsing to detect URLs and emails without
    explicit markdown link syntax.
    """

    @property
    def name(self) -> str:
        return "autolinks"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """No lexer extension needed."""
        pass

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Enable autolink detection in inline parser."""
        parser_class._autolinks_enabled = True

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Autolink rendering uses standard link rendering."""
        pass


# Autolink detection is integrated into inline parsing.
# See:
# - parser.py: _parse_autolink() in inline content handling
# - Uses Link node with auto-generated children
