"""
Data table directive for Bengal SSG.

Provides interactive tables for hardware/software support matrices and other
complex tabular data with filtering, sorting, and searching capabilities.
"""

import csv
import hashlib
import json
from pathlib import Path
from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.file_io import load_data_file
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

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
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
        path = self.parse_title(m)
        if not path:
            logger.warning(
                "data_table_no_path",
                message="data-table directive missing file path",
                state=str(state),
            )
            return {
                "type": "data_table",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        options = dict(self.parse_options(m))

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

        Args:
            path: Relative path to data file
            state: Parser state (contains site context)

        Returns:
            Dict with 'columns' and 'data' keys, or 'error' key on failure
        """
        # Try to get root_path from state (set by rendering pipeline)
        root_path = getattr(state, "root_path", None) or Path.cwd()
        file_path = Path(root_path) / path

        # Check if file exists
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        # Check file size (max 5MB)
        file_size = file_path.stat().st_size
        if file_size > 5 * 1024 * 1024:
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

            columns = [{"title": key.replace("_", " ").title(), "field": key} for key in first_row]

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
        hash_obj = hashlib.sha256(path.encode())
        return f"data-table-{hash_obj.hexdigest()[:8]}"

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
        f'  <script type="application/json" data-table-config="{table_id}">'
        f"{config_json}"
        f"  </script>"
    )

    html_parts.append("</div>")

    return "\n".join(html_parts)
