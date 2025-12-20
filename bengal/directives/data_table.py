"""
Data table directive for Bengal SSG.

Provides interactive tables for hardware/software support matrices and other
complex tabular data with filtering, sorting, and searching capabilities.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.file_io import load_data_file
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

__all__ = ["DataTableDirective", "render_data_table"]

logger = get_logger(__name__)


class DataTableDirective(DirectivePlugin):
    """
    Data table directive using Mistune's fenced syntax.

    Syntax:
        ```{data-table} path/to/data.yaml
        :search: true
        :filter: true
        :sort: true
        :pagination: 50
        :height: 400px
        :columns: col1,col2,col3
        ```

    Supports:
    - YAML files (with metadata and column definitions)
    - CSV files (auto-detect headers)
    - Interactive filtering, sorting, searching
    - Responsive design
    - Keyboard navigation
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["data-table"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Parse data-table directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'data_table'
        """
        # Get file path from title
        # Try to use parse_title if parser is available OR if parse_title was mocked/overridden
        path: Any = None
        try:
            # Check if we can safely call parse_title
            # Either parser exists (real mistune usage) or parse_title was overridden (test mock)
            if (hasattr(self, "parser") and self.parser) or (
                hasattr(self, "parse_title") and self.parse_title != DirectivePlugin.parse_title
            ):
                path = self.parse_title(m)
            else:
                # Fallback: extract from match object
                path = m.group() if hasattr(m, "group") else None
        except (AttributeError, TypeError):
            # If parse_title fails, fallback to match.group()
            path = m.group() if hasattr(m, "group") else None

        path_str: str | None = str(path) if path else None
        if not path_str or not path_str.strip():
            logger.warning(
                "data_table_no_path",
                reason="data-table directive missing file path",
                state=str(state),
            )
            return {
                "type": "data_table",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        # Similar logic: use parse_options if parser exists OR if it was mocked/overridden
        try:
            if (hasattr(self, "parser") and self.parser) or (
                hasattr(self, "parse_options")
                and self.parse_options != DirectivePlugin.parse_options
            ):
                options = dict(self.parse_options(m))
            else:
                options = {}
        except (AttributeError, TypeError):
            options = {}

        # Load data from file
        data_result = self._load_data(path, state)

        if "error" in data_result:
            logger.error(
                "data_table_load_error",
                path=path,
                error=data_result["error"],
            )
            return {
                "type": "data_table",
                "attrs": {"error": data_result["error"], "path": path},
                "children": [],
            }

        # Generate unique table ID
        table_id = self._generate_table_id(path)

        # Build attributes for renderer
        attrs = {
            "table_id": table_id,
            "path": path,
            "columns": data_result["columns"],
            "data": data_result["data"],
            "search": self._parse_bool(options.get("search", "true")),
            "filter": self._parse_bool(options.get("filter", "true")),
            "sort": self._parse_bool(options.get("sort", "true")),
            "pagination": self._parse_pagination(options.get("pagination", "50")),
            "height": options.get("height", "auto"),
            "visible_columns": self._parse_columns(options.get("columns", "")),
        }

        return {"type": "data_table", "attrs": attrs, "children": []}

    def _load_data(self, path: str, state: Any) -> dict[str, Any]:
        """
        Load data from YAML or CSV file.

        Path Resolution:
            - root_path MUST be provided via state (set by rendering pipeline)
            - No fallback to Path.cwd() - eliminates CWD-dependent behavior
            - See: plan/active/rfc-path-resolution-architecture.md

        Args:
            path: Relative path to data file
            state: Parser state (must contain root_path from rendering pipeline)

        Returns:
            Dict with 'columns' and 'data' keys, or 'error' key on failure
        """
        # Get root_path from state (MUST be set by rendering pipeline)
        # No CWD fallback - path resolution must be explicit
        root_path = getattr(state, "root_path", None)
        if not root_path:
            logger.warning(
                "data_table_missing_root_path",
                path=path,
                action="returning_error",
                hint="Ensure rendering pipeline passes root_path in state",
            )
            return {"error": "Site context not available for path resolution"}
        file_path = Path(root_path) / path

        # Check if file exists
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        # Check file size (threshold 1MB per tests)
        file_size = file_path.stat().st_size
        if file_size > 1 * 1024 * 1024:
            return {"error": f"File too large: {path} ({file_size / 1024 / 1024:.1f}MB)"}

        # Load based on extension
        suffix = file_path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            return self._load_yaml_data(file_path)
        elif suffix == ".csv":
            return self._load_csv_data(file_path)
        else:
            return {"error": f"Unsupported file format: {suffix} (use .yaml, .yml, or .csv)"}

    def _load_yaml_data(self, file_path: Path) -> dict[str, Any]:
        """
        Load data from YAML file.

        Expected structure:
            columns:
              - title: Column Name
                field: field_name
              - title: Another Column
                field: another_field
            data:
              - field_name: value1
                another_field: value2
              - field_name: value3
                another_field: value4

        Args:
            file_path: Path to YAML file

        Returns:
            Dict with 'columns' and 'data' keys, or 'error' key
        """
        try:
            data = load_data_file(file_path, on_error="raise", caller="data_table")

            if not isinstance(data, dict):
                return {"error": "YAML must contain a dictionary"}

            # Extract columns
            if "columns" in data:
                columns = data["columns"]
                if not isinstance(columns, list):
                    return {"error": "columns must be a list"}
            else:
                # Auto-generate columns from first data row
                if "data" not in data or not data["data"]:
                    return {"error": "YAML must contain 'columns' or 'data'"}

                first_row = data["data"][0]
                if not isinstance(first_row, dict):
                    return {"error": "data rows must be dictionaries"}

                columns = [
                    {"title": key.replace("_", " ").title(), "field": key} for key in first_row
                ]

            # Extract data
            if "data" not in data:
                return {"error": "YAML must contain 'data'"}

            table_data = data["data"]
            if not isinstance(table_data, list):
                return {"error": "data must be a list"}

            return {"columns": columns, "data": table_data}

        except Exception as e:
            logger.error("yaml_load_error", path=str(file_path), error=str(e))
            return {"error": f"Failed to parse YAML: {e}"}

    def _load_csv_data(self, file_path: Path) -> dict[str, Any]:
        """
        Load data from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            Dict with 'columns' and 'data' keys, or 'error' key
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                # Use DictReader to auto-detect headers
                reader = csv.DictReader(f)

                # Get column names from headers
                if not reader.fieldnames:
                    return {"error": "CSV file has no headers"}

                columns = [{"title": name, "field": name} for name in reader.fieldnames]

                # Read all rows
                data = list(reader)

                if not data:
                    return {"error": "CSV file has no data rows"}

                return {"columns": columns, "data": data}

        except Exception as e:
            logger.error("csv_load_error", path=str(file_path), error=str(e))
            return {"error": f"Failed to parse CSV: {e}"}

    def _generate_table_id(self, path: str) -> str:
        """
        Generate unique table ID from path.

        Args:
            path: File path

        Returns:
            Unique table ID
        """
        # Use first 8 chars of SHA256 hash
        return f"data-table-{hash_str(path, truncate=8)}"

    def _parse_bool(self, value: str) -> bool:
        """Parse boolean option value."""
        if isinstance(value, bool):
            return value
        return value.lower() in ("true", "1", "yes", "on")

    def _parse_pagination(self, value: str) -> int | bool:
        """
        Parse pagination option.

        Args:
            value: Pagination value (number or "false")

        Returns:
            Int for page size, False to disable pagination
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value

        # Check for false/no/off
        if value.lower() in ("false", "0", "no", "off"):
            return False

        # Try to parse as int
        try:
            page_size = int(value)
            return max(0, page_size)  # Ensure non-negative
        except ValueError:
            logger.warning("data_table_invalid_pagination", value=value)
            return 50  # Default

    def _parse_columns(self, value: str) -> list[str] | None:
        """
        Parse visible columns option.

        Args:
            value: Comma-separated column list

        Returns:
            List of column names, or None for all columns
        """
        if not value or not value.strip():
            return None

        return [col.strip() for col in value.split(",") if col.strip()]

    def __call__(self, directive: Any, md: Any) -> Any:
        """Register the directive and renderer."""
        directive.register("data-table", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("data_table", render_data_table)


def render_data_table(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render data table to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for data tables)
        **attrs: Table attributes from directive

    Returns:
        HTML string for data table
    """
    # Check for error
    if "error" in attrs:
        error_msg = attrs["error"]
        path = attrs.get("path", "unknown")
        return f"""<div class="bengal-data-table-error" role="alert">
    <strong>Data Table Error:</strong> {error_msg}
    <br><small>File: {path}</small>
</div>"""

    table_id = attrs["table_id"]
    columns = attrs["columns"]
    data = attrs["data"]
    search = attrs["search"]
    filter_enabled = attrs["filter"]
    pagination = attrs["pagination"]
    height = attrs["height"]
    visible_columns = attrs.get("visible_columns")

    # Filter columns if specified
    if visible_columns:
        columns = [col for col in columns if col["field"] in visible_columns]

    # Build Tabulator config
    config = {
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
    html_parts = [
        f'<div class="bengal-data-table-wrapper" data-table-id="{table_id}">',
    ]

    # Search box (if enabled)
    if search:
        html_parts.append(
            f'  <div class="bengal-data-table-toolbar">'
            f'    <input type="text" id="{table_id}-search" '
            f'           class="bengal-data-table-search" '
            f'           placeholder="Search table..." '
            f'           aria-label="Search table">'
            f"  </div>"
        )

    # Table container
    html_parts.append(f'  <div id="{table_id}" class="bengal-data-table"></div>')

    # Initialization script
    html_parts.append(
        f'  <script type="application/json" data-table-config="{table_id}">{config_json}</script>'
    )

    html_parts.append("</div>")

    return "\n".join(html_parts)
