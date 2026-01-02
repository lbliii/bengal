"""Table parsing for Patitas parser.

Handles GFM (GitHub Flavored Markdown) table parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import Table, TableCell, TableRow

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class TableParsingMixin:
    """Mixin for GFM table parsing.

    Required Host Attributes: None

    Required Host Methods:
        - _parse_inline(text, location) -> tuple[Inline, ...]
    """

    def _try_parse_table(self, lines: list[str], location: SourceLocation) -> Table | None:
        """Try to parse lines as a GFM table.

        GFM table structure:
        | Header 1 | Header 2 |   <- header row
        |----------|----------|   <- delimiter row (required)
        | Cell 1   | Cell 2   |   <- body rows

        Returns Table if valid, None if not a table.
        """
        if len(lines) < 2:
            return None

        # Parse potential header row
        header_cells = self._parse_table_row(lines[0])
        if not header_cells:
            return None

        # Check delimiter row (second line)
        delimiter_row = lines[1].strip()
        alignments = self._parse_table_delimiter(delimiter_row, len(header_cells))
        if alignments is None:
            return None

        # Parse header row cells as inline content
        header_row = TableRow(
            location=location,
            cells=tuple(
                TableCell(
                    location=location,
                    children=self._parse_inline(cell.strip(), location),
                    is_header=True,
                    align=alignments[i] if i < len(alignments) else None,
                )
                for i, cell in enumerate(header_cells)
            ),
            is_header=True,
        )

        # Parse body rows
        body_rows: list[TableRow] = []
        for line in lines[2:]:
            row_cells = self._parse_table_row(line)
            if row_cells:
                body_rows.append(
                    TableRow(
                        location=location,
                        cells=tuple(
                            TableCell(
                                location=location,
                                children=self._parse_inline(cell.strip(), location),
                                is_header=False,
                                align=alignments[i] if i < len(alignments) else None,
                            )
                            for i, cell in enumerate(row_cells)
                        ),
                        is_header=False,
                    )
                )

        return Table(
            location=location,
            head=(header_row,),
            body=tuple(body_rows),
            alignments=alignments,
        )

    def _parse_table_row(self, line: str) -> list[str] | None:
        """Parse a table row into cells.

        Returns list of cell contents, or None if not a valid row.
        """
        line = line.strip()

        # Must contain at least one pipe
        if "|" not in line:
            return None

        # Remove leading/trailing pipes
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        # Split on unescaped pipes
        cells: list[str] = []
        current_cell: list[str] = []
        i = 0
        while i < len(line):
            if line[i] == "\\" and i + 1 < len(line) and line[i + 1] == "|":
                # Escaped pipe
                current_cell.append("|")
                i += 2
            elif line[i] == "|":
                cells.append("".join(current_cell))
                current_cell = []
                i += 1
            else:
                current_cell.append(line[i])
                i += 1

        # Add last cell
        cells.append("".join(current_cell))

        return cells if cells else None

    def _parse_table_delimiter(
        self, line: str, expected_cols: int
    ) -> tuple[str | None, ...] | None:
        """Parse table delimiter row and extract alignments.

        Delimiter format: |:---|:---:|---:|
        Returns tuple of alignments ('left', 'center', 'right', None).
        Returns None if not a valid delimiter row.
        """
        line = line.strip()

        # Remove leading/trailing pipes
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        parts = line.split("|")
        if not parts:
            return None

        alignments: list[str | None] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for valid delimiter pattern: at least one dash
            has_left_colon = part.startswith(":")
            has_right_colon = part.endswith(":")

            # Remove colons to check dashes
            inner = part
            if has_left_colon:
                inner = inner[1:]
            if has_right_colon:
                inner = inner[:-1]

            # Must have at least one dash
            if not inner or not all(c == "-" for c in inner):
                return None

            # Determine alignment
            if has_left_colon and has_right_colon:
                alignments.append("center")
            elif has_left_colon:
                alignments.append("left")
            elif has_right_colon:
                alignments.append("right")
            else:
                alignments.append(None)

        # Must have at least one column
        if not alignments:
            return None

        return tuple(alignments)
