"""List parsing subpackage for Patitas parser.

Provides modular list parsing with support for:
- Ordered and unordered lists
- Nested lists
- Task lists with [ ] and [x] markers
- Multi-line list items (continuation paragraphs)
- Loose/tight list detection
- Block elements within list items

Architecture:
List parsing is split into focused modules:
- mixin: Main ListParsingMixin class
- types: Type definitions and dataclasses
- marker: Marker detection and classification
- indent: Indent calculation utilities
- blank_line: Blank line handling
- item_blocks: Block elements in list items
- nested: Nested list handling

"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.parsing.blocks.list.mixin import ListParsingMixin

__all__ = ["ListParsingMixin"]
