"""Block parsing subsystem for Patitas parser.

Provides mixins for parsing block-level Markdown content:
- Headings (ATX and setext)
- Code blocks (fenced and indented)
- Block quotes
- Lists (ordered, unordered, task lists)
- Tables (GFM)
- Directives
- Footnote definitions
- Paragraphs

Architecture:
    Block parsing is split into logical modules:
    - core: Block dispatch and basic blocks
    - list: Complex list parsing with nesting
    - table: GFM table parsing
    - directive: Directive parsing with contracts
    - footnote: Footnote definition parsing
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.parsing.blocks.core import BlockParsingCoreMixin
from bengal.rendering.parsers.patitas.parsing.blocks.directive import DirectiveParsingMixin
from bengal.rendering.parsers.patitas.parsing.blocks.footnote import FootnoteParsingMixin
from bengal.rendering.parsers.patitas.parsing.blocks.list import (
    ListParsingMixin,  # Now from list/ subpackage
)
from bengal.rendering.parsers.patitas.parsing.blocks.table import TableParsingMixin


class BlockParsingMixin(
    BlockParsingCoreMixin,
    ListParsingMixin,
    TableParsingMixin,
    DirectiveParsingMixin,
    FootnoteParsingMixin,
):
    """Combined block parsing mixin.

    Combines all block parsing functionality into a single mixin
    that can be inherited by the Parser class.

    Required Host Attributes:
        - _source: str
        - _tokens: list[Token]
        - _pos: int
        - _current: Token | None
        - _tables_enabled: bool
        - _directive_registry: DirectiveRegistry | None
        - _directive_stack: list[str]
        - _strict_contracts: bool

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_inline(text, location) -> tuple[Inline, ...]
    """

    pass


__all__ = [
    "BlockParsingMixin",
    "BlockParsingCoreMixin",
    "ListParsingMixin",
    "TableParsingMixin",
    "DirectiveParsingMixin",
    "FootnoteParsingMixin",
]
