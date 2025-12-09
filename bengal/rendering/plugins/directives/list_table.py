"""
List table directive for Bengal SSG.

Provides MyST-style list-table directive for creating tables from nested lists,
avoiding the pipe character collision issue in type annotations.
"""

from __future__ import annotations

import re
from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["ListTableDirective", "render_list_table"]

logger = get_logger(__name__)


class ListTableDirective(DirectivePlugin):
    """
    List table directive using MyST syntax.

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
        * - Row 2, Col 1
          - Row 2, Col 2
          - Row 2, Col 3
        :::

    Supports:
    - :header-rows: number - Number of header rows (default: 0)
    - :widths: space-separated percentages - Column widths
    - :class: CSS class for the table
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["list-table"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Parse list-table directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'list_table'
        """
        # Parse options
        try:
            options = dict(self.parse_options(m))
        except Exception as e:
            logger.debug(
                "list_table_options_parse_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_empty_options",
            )
            options = {}

        # Extract content
        try:
            content = self.parse_content(m)
        except Exception as e:
            logger.debug(
                "list_table_content_parse_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_empty_content",
            )
            content = ""

        # Parse header rows option
        header_rows = int(options.get("header-rows", 0))

        # Parse widths option (space-separated percentages)
        widths_str = options.get("widths", "")
        widths = [int(w) for w in widths_str.split()] if widths_str else []

        # Parse CSS class
        css_class = options.get("class", "")

        # Parse the list content into rows
        rows = self._parse_list_rows(content)

        return {
            "type": "list_table",
            "attrs": {
                "header_rows": header_rows,
                "widths": widths,
                "css_class": css_class,
                "rows": rows,
            },
            "children": [],
        }

    def _parse_list_rows(self, content: str) -> list[list[str]]:
        """
        Parse list content into table rows.

        Args:
            content: Raw content string

        Returns:
            List of rows, where each row is a list of cell contents
        """
        rows = []
        current_row = []
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
                current_cell_lines.append("")  # Blank line for paragraph break

            # Continuation line (must be indented with 4+ spaces)
            elif line.startswith("    ") and current_cell_lines:
                content = line[4:]  # Remove 4-space indent
                current_cell_lines.append(content)

            # Empty line outside of cells - skip
            elif not stripped:
                pass  # Skip empty lines between rows/cells

            # Any other line - ignore (shouldn't happen in well-formed input)

            i += 1

        # Save last cell and row
        if current_cell_lines:
            current_row.append("\n".join(current_cell_lines).strip())
        if current_row:
            rows.append(current_row)

        return rows

    def __call__(self, directive: Any, md: Any) -> Any:
        """Register the directive and renderer."""
        directive.register("list-table", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("list_table", render_list_table)


def render_list_table(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render list table to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for list tables)
        **attrs: Table attributes from directive

    Returns:
        HTML string for list table
    """
    import html as html_lib

    import mistune

    header_rows = attrs.get("header_rows", 0)
    widths = attrs.get("widths", [])
    css_class = attrs.get("css_class", "")
    rows = attrs.get("rows", [])

    if not rows:
        return '<div class="bengal-list-table-error">List table has no rows</div>'

    # Create a simple inline markdown parser for cell content
    inline_md = mistune.create_markdown(renderer="html", plugins=[])

    def render_cell(cell_content: str) -> str:
        """Render cell content with full markdown support (lists, paragraphs, etc.)."""
        # Normalize placeholder '-' which would otherwise render as an empty list
        if cell_content.strip() == "-":
            return '<span class="table-empty">—</span>'

        # Parse as full markdown (allows paragraphs, lists, etc.)
        html_result = inline_md(cell_content)
        # Ensure html is a string (mistune returns str, but type checker sees union)
        html = html_result if isinstance(html_result, str) else str(html_result)
        html = html.strip()

        # If only a single paragraph, unwrap it for cleaner inline display
        if html.count("<p>") == 1 and html.startswith("<p>") and html.endswith("</p>"):
            html = html[3:-4]

        # Wrap in cell-content div for proper CSS styling
        if "<p>" in html or "<ul>" in html or "<ol>" in html or "<pre>" in html:
            return f'<div class="cell-content">{html}</div>'

        return html

    # Build HTML
    html_parts = []

    # Start table
    table_class = (
        f'class="bengal-list-table {css_class}"' if css_class else 'class="bengal-list-table"'
    )
    html_parts.append(f"<table {table_class}>")

    # Add colgroup if widths specified
    if widths:
        html_parts.append("  <colgroup>")
        for width in widths:
            html_parts.append(f'    <col style="width: {width}%;">')
        html_parts.append("  </colgroup>")

    # Render header rows
    if header_rows > 0:
        html_parts.append("  <thead>")
        for row_idx in range(min(header_rows, len(rows))):
            html_parts.append("    <tr>")
            for cell in rows[row_idx]:
                cell_html = render_cell(cell)
                html_parts.append(f"      <th>{cell_html}</th>")
            html_parts.append("    </tr>")
        html_parts.append("  </thead>")

    # Render body rows
    if len(rows) > header_rows:
        html_parts.append("  <tbody>")
        # Extract plain-text header labels for data-label attributes
        header_labels: list[str] = []
        if header_rows > 0:
            # Use first header row as labels
            first_header = rows[0]
            for header_cell in first_header:
                # Use the raw content (e.g., "Name") and escape for attribute usage
                label_text = header_cell.strip()
                # Remove surrounding backticks if present
                if label_text.startswith("`") and label_text.endswith("`"):
                    label_text = label_text[1:-1]
                header_labels.append(label_text)

        for row_idx in range(header_rows, len(rows)):
            html_parts.append("    <tr>")
            for col_idx, cell in enumerate(rows[row_idx]):
                cell_html = render_cell(cell)
                if header_labels and col_idx < len(header_labels):
                    data_label = html_lib.escape(header_labels[col_idx], quote=True)
                    html_parts.append(f'      <td data-label="{data_label}">{cell_html}</td>')
                else:
                    html_parts.append(f"      <td>{cell_html}</td>")
            html_parts.append("    </tr>")
        html_parts.append("  </tbody>")

    html_parts.append("</table>")

    return "\n".join(html_parts)
