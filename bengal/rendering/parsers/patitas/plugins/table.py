"""Table plugin for Patitas (GFM-style pipe tables).

Adds support for GitHub-Flavored Markdown tables.

Usage:
    >>> md = create_markdown(plugins=["table"])
    >>> md("| A | B |\n|---|---|\n| 1 | 2 |")
    '<table><thead><tr><th>A</th><th>B</th></tr></thead>...'

Syntax:
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

Alignment:
| Left | Center | Right |
|:-----|:------:|------:|
| L    |   C    |     R |

Features:
- Column alignment via :--- :--: ---:
- Inline markdown in cells
- Pipes can be escaped with \|

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


@register_plugin("table")
class TablePlugin:
    """Plugin adding GFM table support.
    
    Tables are detected at the block level when a line starts with |
    and is followed by a delimiter row (|---|---|).
        
    """

    @property
    def name(self) -> str:
        return "table"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """Enable table detection in lexer."""
        # Mark that tables are enabled
        lexer_class._tables_enabled = True

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Enable table parsing."""
        parser_class._tables_enabled = True

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Table rendering is handled in base renderer."""
        pass


# Table parsing is integrated into the lexer and parser.
# See:
# - lexer.py: _is_table_row(), _scan_table()
# - parser.py: _parse_table()
# - nodes.py: Table, TableRow, TableCell
