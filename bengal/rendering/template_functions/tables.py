"""
Table functions for templates.

Provides functions for rendering interactive data tables from YAML/CSV files.
Core emits a renderer-agnostic table contract; the default theme adapts it to
Tabulator when the vendored runtime is present.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from kida import Markup

from bengal.errors import ErrorCode
from bengal.utils.io.file_io import load_data_file
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import SiteConfig, TemplateEnvironment

logger = get_logger(__name__)

__all__ = [
    "DataTableColumn",
    "DataTableOptions",
    "DataTableSpec",
    "build_data_table_spec",
    "data_table",
    "load_data_table",
    "register",
    "render_data_table_html",
    "spec_to_contract",
]


@dataclass(frozen=True, slots=True)
class DataTableColumn:
    """Renderer-agnostic column descriptor."""

    field: str
    title: str


@dataclass(frozen=True, slots=True)
class DataTableOptions:
    """Renderer-agnostic table behavior flags."""

    search: bool = True
    filterable: bool = True
    sortable: bool = True
    paginated: int | bool = 50
    height: str = "auto"
    visible_columns: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class DataTableSpec:
    """Canonical data-table payload consumed by theme renderers."""

    table_id: str
    columns: tuple[DataTableColumn, ...]
    rows: tuple[dict[str, Any], ...]
    options: DataTableOptions


def register(env: TemplateEnvironment, site: SiteConfig) -> None:
    """
    Register functions with template environment.

    Args:
        env: Template environment
        site: Site instance

    """

    def _data_table(path: str, **options: Any) -> Markup:
        return data_table(path, site=site, **options)

    env.globals.update(
        {
            "data_table": _data_table,
        }
    )


# ---------------------------------------------------------------------------
# Standalone data-loading helpers (extracted from Mistune DataTableDirective)
# ---------------------------------------------------------------------------


def _load_data(path: str, root_path: Path) -> dict[str, Any]:
    """Load data from YAML or CSV file."""
    file_path = root_path / path

    if not file_path.exists():
        return {"error": f"File not found: {path}"}

    file_size = file_path.stat().st_size
    if file_size > 1 * 1024 * 1024:
        return {"error": f"File too large: {path} ({file_size / 1024 / 1024:.1f}MB)"}

    suffix = file_path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        return _load_yaml_data(file_path)
    if suffix == ".csv":
        return _load_csv_data(file_path)
    return {"error": f"Unsupported file format: {suffix} (use .yaml, .yml, or .csv)"}


def load_data_table(path: str, root_path: Path) -> dict[str, Any]:
    """Load table columns and rows from a data file."""
    return _load_data(path, root_path)


def _load_yaml_data(file_path: Path) -> dict[str, Any]:
    """Load data from YAML file."""
    try:
        data = load_data_file(file_path, on_error="raise", caller="data_table")

        if not isinstance(data, dict):
            return {"error": "YAML must contain a dictionary"}

        if "columns" in data:
            columns = data["columns"]
            if not isinstance(columns, list):
                return {"error": "columns must be a list"}
        else:
            if "data" not in data or not data["data"]:
                return {"error": "YAML must contain 'columns' or 'data'"}

            first_row = data["data"][0]
            if not isinstance(first_row, dict):
                return {"error": "data rows must be dictionaries"}

            columns = [{"title": key.replace("_", " ").title(), "field": key} for key in first_row]

        if "data" not in data:
            return {"error": "YAML must contain 'data'"}

        table_data = data["data"]
        if not isinstance(table_data, list):
            return {"error": "data must be a list"}

        return {"columns": columns, "data": table_data}

    except Exception as e:
        logger.error("yaml_load_error", path=str(file_path), error=str(e))
        return {"error": f"Failed to parse YAML: {e}"}


def _load_csv_data(file_path: Path) -> dict[str, Any]:
    """Load data from CSV file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return {"error": "CSV file has no headers"}

            columns = [{"title": name, "field": name} for name in reader.fieldnames]
            data = list(reader)

            if not data:
                return {"error": "CSV file has no data rows"}

            return {"columns": columns, "data": data}

    except Exception as e:
        logger.error("csv_load_error", path=str(file_path), error=str(e))
        return {"error": f"Failed to parse CSV: {e}"}


def _generate_table_id(path: str) -> str:
    """Generate unique table ID from path."""
    return f"data-table-{hash_str(path, truncate=8)}"


def _parse_bool(value: str | bool) -> bool:
    """Parse boolean option value."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")


def _parse_pagination(value: str | bool | int) -> int | bool:
    """Parse pagination option."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value

    if str(value).lower() in ("false", "0", "no", "off"):
        return False

    try:
        page_size = int(value)
        return max(0, page_size)
    except ValueError:
        logger.warning("data_table_invalid_pagination", value=value)
        return 50


def _parse_columns(value: str) -> tuple[str, ...] | None:
    """Parse visible columns option."""
    if not value or not value.strip():
        return None
    return tuple(col.strip() for col in value.split(",") if col.strip())


def build_data_table_spec(
    path: str, root_path: Path, **options: Any
) -> DataTableSpec | dict[str, Any]:
    """Load data and build a renderer-agnostic table spec."""
    data_result = _load_data(path, root_path)
    if "error" in data_result:
        return data_result

    table_options = DataTableOptions(
        search=_parse_bool(options.get("search", True)),
        filterable=_parse_bool(options.get("filter", True)),
        sortable=_parse_bool(options.get("sort", True)),
        paginated=_parse_pagination(options.get("pagination", 50)),
        height=str(options.get("height", "auto")),
        visible_columns=_parse_columns(str(options.get("columns", ""))),
    )

    columns = tuple(
        DataTableColumn(field=str(col["field"]), title=str(col.get("title", col["field"])))
        for col in data_result["columns"]
    )
    rows = tuple(dict(row) for row in data_result["data"])

    return DataTableSpec(
        table_id=_generate_table_id(path),
        columns=columns,
        rows=rows,
        options=table_options,
    )


def spec_to_contract(spec: DataTableSpec) -> dict[str, Any]:
    """Serialize a table spec to the generic JSON contract."""
    columns = [{"field": col.field, "title": col.title} for col in spec.columns]
    if spec.options.visible_columns:
        visible = set(spec.options.visible_columns)
        columns = [col for col in columns if col["field"] in visible]

    paginated = spec.options.paginated
    return {
        "table_id": spec.table_id,
        "columns": columns,
        "rows": list(spec.rows),
        "options": {
            "search": spec.options.search,
            "filterable": spec.options.filterable,
            "sortable": spec.options.sortable,
            "paginated": paginated if paginated else False,
            "page_size": paginated if isinstance(paginated, int) else 50,
            "height": spec.options.height,
        },
    }


def render_data_table_html(spec: DataTableSpec) -> str:
    """Render a data table wrapper with the generic JSON contract embedded."""
    contract = spec_to_contract(spec)
    contract_json = json.dumps(contract, indent=None, sort_keys=True)
    table_id = spec.table_id

    html_parts = [
        f'<div class="bengal-data-table-wrapper" data-table-id="{table_id}">',
    ]

    if spec.options.search:
        html_parts.append(
            f'  <div class="bengal-data-table-toolbar">'
            f'    <input type="text" id="{table_id}-search" '
            f'           class="bengal-data-table-search" '
            f'           placeholder="Search table..." '
            f'           aria-label="Search table">'
            f"  </div>"
        )

    html_parts.append(f'  <div id="{table_id}" class="bengal-data-table"></div>')
    html_parts.append(
        f'  <script type="application/json" data-table-spec="{table_id}">{contract_json}</script>'
    )
    html_parts.append("</div>")

    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Template function
# ---------------------------------------------------------------------------


def data_table(path: str, site: Any, **options: Any) -> Markup:
    """
    Render interactive data table from YAML or CSV file.

    Uses standalone data-loading and rendering logic.

    Args:
        path: Relative path to data file (YAML or CSV)
        site: Site instance (provides root_path)
        **options: Table options
            - search (bool): Enable search box (default: True)
            - filter (bool): Enable column filters (default: True)
            - sort (bool): Enable column sorting (default: True)
            - pagination (int|False): Rows per page, or False to disable (default: 50)
            - height (str): Table height like "400px" (default: "auto")
            - columns (str): Comma-separated list of columns to show (default: all)

    Returns:
        Markup object with rendered HTML table

    Example:
        {# Basic usage #}
        {{ data_table('data/browser-support.yaml') }}

        {# With options #}
        {{ data_table('data/hardware-specs.csv',
                      pagination=100,
                      height='500px',
                      search=True) }}

        {# Show specific columns only #}
        {{ data_table('data/support-matrix.yaml',
                      columns='Feature,Chrome,Firefox') }}

    """
    if not path:
        logger.warning(
            "data_table_empty_path",
            caller="template",
            error_code=ErrorCode.R003.value,
            suggestion="Provide a valid data file path to data_table()",
        )
        return Markup(
            '<div class="bengal-data-table-error" role="alert">'
            "<strong>Data Table Error:</strong> No file path specified"
            "</div>"
        )

    if not hasattr(site, "root_path"):
        raise TypeError("Site object missing required 'root_path' attribute")

    spec_result = build_data_table_spec(path, site.root_path, **options)
    if isinstance(spec_result, dict) and "error" in spec_result:
        logger.error(
            "data_table_load_error",
            path=path,
            error=spec_result["error"],
            caller="template",
            error_code=ErrorCode.R003.value,
            suggestion="Check that data file exists and is valid JSON/YAML/CSV",
        )
        return Markup(
            f'<div class="bengal-data-table-error" role="alert">'
            f"<strong>Data Table Error:</strong> {spec_result['error']}"
            f"<br><small>File: {path}</small>"
            f"</div>"
        )

    return Markup(render_data_table_html(spec_result))
