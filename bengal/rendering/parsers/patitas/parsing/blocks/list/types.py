"""Type definitions for list parsing.

Provides dataclasses and type aliases for list parsing state management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.nodes import Block


@dataclass
class ListMarkerInfo:
    """Information extracted from a list marker.
    
    Attributes:
        ordered: Whether this is an ordered list (1. vs -)
        bullet_char: For unordered lists, the bullet character (-, *, +)
        ordered_marker_char: For ordered lists, the marker character (. or ))
        start: Starting number for ordered lists
        indent: Indent level of the marker
        marker_length: Length of the marker including trailing space
        
    """

    ordered: bool
    bullet_char: str  # Empty for ordered lists
    ordered_marker_char: str  # Empty for unordered lists
    start: int
    indent: int
    marker_length: int


@dataclass
class ListItemState:
    """State for parsing a single list item.
    
    Tracks content accumulation, child blocks, and task list status.
        
    """

    children: list[Block] = field(default_factory=list)
    content_lines: list[str] = field(default_factory=list)
    checked: bool | None = None
    actual_content_indent: int | None = None
    saw_paragraph_content: bool = False


@dataclass
class ListParsingContext:
    """Context for list parsing operations.
    
    Encapsulates the parsing state needed by helper functions without
    exposing the full parser interface.
    
    Attributes:
        source: The full source text being parsed
        start_indent: Indent level of the list's first marker
        content_indent: Minimum indent for continuation content
        bullet_char: Bullet character for unordered lists
        ordered_marker_char: Marker character (. or )) for ordered lists
        ordered: Whether this is an ordered list
        
    """

    source: str
    start_indent: int
    content_indent: int
    bullet_char: str
    ordered_marker_char: str
    ordered: bool


class ContinueAction:
    """Sentinel for continuing the parsing loop."""

    pass


class BreakAction:
    """Sentinel for breaking out of the parsing loop."""

    pass


@dataclass
class ContentAction:
    """Action to add content to the current item."""

    content: str


@dataclass
class BlockAction:
    """Action to add a block to the current item's children."""

    block: Block


@dataclass
class NestedListAction:
    """Action indicating a nested list should be parsed."""

    pass


@dataclass
class LooseListAction:
    """Action to mark the list as loose (has blank lines between items)."""

    pass


# Type alias for parsing action results
ParseAction = (
    ContinueAction | BreakAction | ContentAction | BlockAction | NestedListAction | LooseListAction
)
