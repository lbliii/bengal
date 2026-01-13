"""Inline parsing subsystem for Patitas parser.

Provides mixins for parsing inline Markdown content:
- Emphasis and strong (*, _)
- Code spans (`)
- Links and images
- Footnote references
- HTML inline
- Roles ({role}`content`)
- Math ($expression$)
- Strikethrough (~~)

Architecture:
Uses CommonMark delimiter stack algorithm for proper emphasis parsing.
See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis

"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.parsing.inline.core import InlineParsingCoreMixin
from bengal.rendering.parsers.patitas.parsing.inline.emphasis import EmphasisMixin
from bengal.rendering.parsers.patitas.parsing.inline.links import LinkParsingMixin
from bengal.rendering.parsers.patitas.parsing.inline.match_registry import (
    DelimiterMatch,
    MatchRegistry,
)
from bengal.rendering.parsers.patitas.parsing.inline.special import SpecialInlineMixin
from bengal.rendering.parsers.patitas.parsing.inline.tokens import (
    CodeSpanToken,
    DelimiterToken,
    HardBreakToken,
    InlineToken,
    NodeToken,
    SoftBreakToken,
    TextToken,
)


class InlineParsingMixin(
    InlineParsingCoreMixin,
    EmphasisMixin,
    LinkParsingMixin,
    SpecialInlineMixin,
):
    """Combined inline parsing mixin.
    
    Combines all inline parsing functionality into a single mixin
    that can be inherited by the Parser class.
    
    Required Host Attributes:
        - _source: str
        - _math_enabled: bool
        - _strikethrough_enabled: bool
        - _footnotes_enabled: bool
        - _link_refs: dict[str, tuple[str, str]]
        
    """

    pass


__all__ = [
    # Mixins
    "InlineParsingMixin",
    "InlineParsingCoreMixin",
    "EmphasisMixin",
    "LinkParsingMixin",
    "SpecialInlineMixin",
    # Match registry
    "MatchRegistry",
    "DelimiterMatch",
    # Typed tokens
    "InlineToken",
    "DelimiterToken",
    "TextToken",
    "CodeSpanToken",
    "NodeToken",
    "HardBreakToken",
    "SoftBreakToken",
]
