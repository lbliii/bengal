"""Data table directive for interactive tables.

Provides interactive tables for hardware/software support matrices and other
complex tabular data with filtering, sorting, and searching capabilities.

Syntax:
:::{data-table} path/to/data.yaml
:search: true
:filter: true
:sort: true
:pagination: 50
:height: 400px
:columns: col1,col2,col3
:::

Supports:
- YAML files (with metadata and column definitions)
- CSV files (auto-detect headers)
- Interactive filtering, sorting, searching
- Responsive design via Tabulator.js

Context Requirements:
Requires FileResolver for loading data files.

Thread Safety:
Stateless handler. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's data-table directive exactly for parity.

"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["DataTableDirective"]


@dataclass(frozen=True, slots=True)
class DataTableOptions(DirectiveOptions):
    """Options for data-table directive."""

    search: bool = True
    filter: bool = True
    sort: bool = True
    pagination: int | bool = 50
    height: str = "auto"
    columns: str = ""  # Comma-separated visible columns

    # Computed attributes (populated during parse)
    file_path: str = ""
    table_id: str = ""
    visible_columns: list[str] | None = None
    error: str = ""
    # These will be populated by integration layer
    table_columns: list[str] = field(default_factory=list)
    table_data: list[dict[str, Any]] = field(default_factory=list)


class DataTableDirective:
    """
    Interactive data table directive.
    
    Syntax:
        :::{data-table} path/to/data.yaml
        :search: true
        :filter: true
        :sort: true
        :pagination: 50
        :height: 400px
        :columns: col1,col2,col3
        :::
    
    Supported file formats:
        - YAML: Must have 'columns' and 'data' keys
        - CSV: Headers auto-detected from first row
    
    Options:
        :search: Enable search box (default: true)
        :filter: Enable column filters (default: true)
        :sort: Enable column sorting (default: true)
        :pagination: Page size or false (default: 50)
        :height: Table height CSS value (default: auto)
        :columns: Comma-separated list of visible columns
    
    Requires:
        FileResolver for loading data files.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("data-table",)
    token_type: ClassVar[str] = "data_table"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[DataTableOptions]] = DataTableOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: DataTableOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build data-table AST node.

        Note: Actual data loading happens in integration layer.
        The parse method captures the configuration.
        """
        file_path = title.strip() if title else ""

        # Parse visible columns
        visible_columns = None
        if options.columns:
            visible_columns = [col.strip() for col in options.columns.split(",") if col.strip()]

        # Generate table ID
        try:
            from bengal.utils.hashing import hash_str

            table_id = f"data-table-{hash_str(file_path, truncate=8)}"
        except ImportError:
            import hashlib

            table_id = f"data-table-{hashlib.sha256(file_path.encode()).hexdigest()[:8]}"

        # Store configuration
        computed_opts = replace(
            options,
            file_path=file_path,
            table_id=table_id,
            visible_columns=visible_columns,
            error="" if file_path else "No file path specified",
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=(),
        )

    def render(
        self,
        node: Directive[DataTableOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render data table to HTML."""
        opts = node.options

        error = getattr(opts, "error", "")
        file_path = getattr(opts, "file_path", "unknown")

        if error:
            sb.append(
                f'<div class="bengal-data-table-error" role="alert">\n'
                f"    <strong>Data Table Error:</strong> {html_escape(error)}\n"
                f"    <br><small>File: {html_escape(file_path)}</small>\n"
                f"</div>"
            )
            return

        table_id = getattr(opts, "table_id", "data-table")
        columns: list[dict[str, Any]] = getattr(opts, "table_columns", [])
        data: list[dict[str, Any]] = getattr(opts, "table_data", [])
        visible_columns: list[str] | None = getattr(opts, "visible_columns", None)

        search = opts.search
        filter_enabled = opts.filter
        pagination = opts.pagination
        height = opts.height

        # Filter columns if specified
        if visible_columns and columns:
            columns = [col for col in columns if col.get("field") in visible_columns]

        # Build Tabulator config
        config: dict[str, Any] = {
            "columns": columns,
            "data": data,
            "layout": "fitColumns",
            "responsiveLayout": "collapse",
            "pagination": pagination if pagination else False,
            "paginationSize": pagination if isinstance(pagination, int) else 50,
            "movableColumns": True,
            "resizableColumnFit": True,
        }

        # Add height if specified
        if height and height != "auto":
            config["height"] = height

        # Add header filter if enabled
        if filter_enabled:
            for col in config["columns"]:
                col["headerFilter"] = "input"

        # Convert config to JSON
        config_json = json.dumps(config, indent=None)

        # Build HTML
        sb.append(f'<div class="bengal-data-table-wrapper" data-table-id="{table_id}">\n')

        # Search box (if enabled)
        if search:
            sb.append(
                f'  <div class="bengal-data-table-toolbar">'
                f'    <input type="text" id="{table_id}-search" '
                f'class="bengal-data-table-search" '
                f'placeholder="Search table..." '
                f'aria-label="Search table">'
                f"  </div>\n"
            )

        # Table container
        sb.append(f'  <div id="{table_id}" class="bengal-data-table"></div>\n')

        # Initialization script
        sb.append(
            f'  <script type="application/json" data-table-config="{table_id}">'
            f"{config_json}</script>\n"
        )

        sb.append("</div>")
