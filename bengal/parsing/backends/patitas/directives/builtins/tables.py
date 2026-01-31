"""Table directives for structured data display.

Provides:
- list-table: MyST-style tables from nested lists

Use cases:
- Complex tables with multi-line cells
- Tables avoiding pipe character issues with type annotations
- Responsive mobile-friendly tables

Example:
:::{list-table}
:header-rows: 1
:widths: 30 70

* - Header 1
  - Header 2
* - Cell 1
  - Cell 2
:::

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's list-table directive exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["ListTableDirective"]


# =============================================================================
# Typed Options
# =============================================================================


@dataclass(frozen=True, slots=True)
class ListTableOptions(DirectiveOptions):
    """
    Options for list-table directive.

    Attributes:
        header_rows: Number of header rows (default: 0)
        widths: Column width percentages (space-separated string)
        css_class: Additional CSS classes

    """

    header_rows: int = 0
    widths: str = ""
    css_class: str = ""


# =============================================================================
# List Table Directive Handler
# =============================================================================


class ListTableDirective:
    """
    MyST-style list-table for creating tables from nested lists.

    Syntax:
        :::{list-table}
        :header-rows: 1
        :widths: 20 30 50

        * - Header 1
          - Header 2
          - Header 3
        * - Row 1, Col 1
          - Row 1, Col 2
          - Row 1, Col 3
        :::

    Options:
        :header-rows: Number of header rows (default: 0)
        :widths: Space-separated column width percentages
        :class: Additional CSS classes

    Row syntax: "* -" starts a new row
    Cell syntax: "  -" continues with next cell in row

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("list-table",)
    token_type: ClassVar[str] = "list_table"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ListTableOptions]] = ListTableOptions
    preserves_raw_content: ClassVar[bool] = True  # Needs raw content for list parsing

    def parse(
        self,
        name: str,
        title: str | None,
        options: ListTableOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build list-table AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(children),
            raw_content=content,  # Preserve raw content for list parsing
        )

    def render(
        self,
        node: Directive[ListTableOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render list-table to HTML."""
        opts = node.options  # Direct typed access!

        header_rows = opts.header_rows
        widths_str = opts.widths
        widths: list[int] = []
        if widths_str:
            try:
                widths = [int(w) for w in widths_str.split()]
            except ValueError:
                widths = []

        css_class = opts.css_class

        # Parse the list content into rows
        rows = self._parse_list_rows(node.raw_content or "")

        if not rows:
            sb.append('<div class="bengal-list-table-error">List table has no rows</div>')
            return

        # Build class string
        table_class = f"bengal-list-table {css_class}" if css_class else "bengal-list-table"

        sb.append(f'<table class="{table_class}">\n')

        # Add colgroup if widths specified
        if widths:
            sb.append("  <colgroup>\n")
            for width in widths:
                sb.append(f'    <col style="width: {width}%;">\n')
            sb.append("  </colgroup>\n")

        # Render header rows
        if header_rows > 0:
            sb.append("  <thead>\n")
            for row_idx in range(min(header_rows, len(rows))):
                sb.append("    <tr>\n")
                for cell in rows[row_idx]:
                    cell_html = self._render_cell(cell)
                    sb.append(f"      <th>{cell_html}</th>\n")
                sb.append("    </tr>\n")
            sb.append("  </thead>\n")

        # Extract header labels for data-label attributes (responsive tables)
        header_labels: list[str] = []
        if header_rows > 0 and rows:
            first_header = rows[0]
            for header_cell in first_header:
                label_text = header_cell.strip()
                # Remove surrounding backticks if present
                if label_text.startswith("`") and label_text.endswith("`"):
                    label_text = label_text[1:-1]
                header_labels.append(label_text)

        # Render body rows
        if len(rows) > header_rows:
            sb.append("  <tbody>\n")
            for row_idx in range(header_rows, len(rows)):
                sb.append("    <tr>\n")
                for col_idx, cell in enumerate(rows[row_idx]):
                    cell_html = self._render_cell(cell)
                    if header_labels and col_idx < len(header_labels):
                        data_label = html_escape(header_labels[col_idx])
                        sb.append(f'      <td data-label="{data_label}">{cell_html}</td>\n')
                    else:
                        sb.append(f"      <td>{cell_html}</td>\n")
                sb.append("    </tr>\n")
            sb.append("  </tbody>\n")

        sb.append("</table>")

    def _parse_list_rows(self, content: str) -> list[list[str]]:
        """Parse list content into table rows."""
        rows: list[list[str]] = []
        current_row: list[str] = []
        current_cell_lines: list[str] = []

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check for new row marker: "* -" at start
            if re.match(r"^\*\s+-\s*", line):
                # Save previous cell and row if they exist
                if current_cell_lines:
                    current_row.append("\n".join(current_cell_lines).strip())
                    current_cell_lines = []
                if current_row:
                    rows.append(current_row)
                    current_row = []

                # Start new row with first cell
                cell_content = re.sub(r"^\*\s+-\s*", "", line).strip()
                current_cell_lines = [cell_content] if cell_content else []

            # Check for new cell marker: "  -" (2 spaces + dash)
            elif re.match(r"^  -\s*", line):
                # Save previous cell
                if current_cell_lines:
                    current_row.append("\n".join(current_cell_lines).strip())
                    current_cell_lines = []

                # Start new cell
                cell_content = re.sub(r"^  -\s*", "", line).strip()
                current_cell_lines = [cell_content] if cell_content else []

            # Blank line inside a cell - preserve for paragraph breaks
            elif not stripped and current_cell_lines:
                current_cell_lines.append("")

            # Continuation line (must be indented with 4+ spaces)
            elif line.startswith("    ") and current_cell_lines:
                content_part = line[4:]  # Remove 4-space indent
                current_cell_lines.append(content_part)

            # Empty line outside of cells - skip
            elif not stripped:
                pass

            i += 1

        # Save last cell and row
        if current_cell_lines:
            current_row.append("\n".join(current_cell_lines).strip())
        if current_row:
            rows.append(current_row)

        return rows

    def _render_cell(self, cell_content: str) -> str:
        """Render cell content with basic markdown support."""
        # Normalize placeholder '-' which would otherwise render as an empty list
        if cell_content.strip() == "-":
            return '<span class="table-empty">—</span>'

        # For now, escape HTML and handle simple inline markdown
        html = html_escape(cell_content)

        # Handle inline code
        html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

        # Handle bold
        html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)

        # Handle italic
        html = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html)

        # Handle links
        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

        return html
