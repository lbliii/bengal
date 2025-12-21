"""
Table functions for templates.

Provides functions for rendering interactive data tables from YAML/CSV files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jinja2 import pass_environment
from markupsafe import Markup

from bengal.directives.data_table import (
    DataTableDirective,
    render_data_table,
)
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)

__all__ = ["register", "data_table"]


def register(env: Environment, site: Site) -> None:
    """
    Register table functions with Jinja2 environment.

    Args:
        env: Jinja2 environment
        site: Site instance
    """
    env.globals.update(
        {
            "data_table": data_table,
        }
    )


@pass_environment
def data_table(env: Environment, path: str, **options: Any) -> Markup:
    """
    Render interactive data table from YAML or CSV file.

    Uses the same underlying implementation as the data-table directive,
    but can be called directly from templates for more flexibility.

    Args:
        env: Jinja2 environment (injected)
        path: Relative path to data file (YAML or CSV)
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
        logger.warning("data_table_empty_path", caller="template")
        return Markup(
            '<div class="bengal-data-table-error" role="alert">'
            "<strong>Data Table Error:</strong> No file path specified"
            "</div>"
        )

    # Get site from environment globals
    # Use duck typing - only root_path is needed
    site = env.globals["site"]
    if not hasattr(site, "root_path"):
        raise TypeError("Site object missing required 'root_path' attribute")

    # Create a mock state object with root_path
    class State:
        root_path: Any = None

    state = State()
    state.root_path = site.root_path

    # Create directive instance to use its parsing logic
    directive = DataTableDirective()

    # Build options dict from kwargs
    options_dict = {}

    # Convert Python bool/int to string for directive parser
    if "search" in options:
        options_dict["search"] = str(options["search"]).lower()
    if "filter" in options:
        options_dict["filter"] = str(options["filter"]).lower()
    if "sort" in options:
        options_dict["sort"] = str(options["sort"]).lower()
    if "pagination" in options:
        options_dict["pagination"] = str(options["pagination"])
    if "height" in options:
        options_dict["height"] = options["height"]
    if "columns" in options:
        options_dict["columns"] = options["columns"]

    # Load data using directive's method
    data_result = directive._load_data(path, state)

    if "error" in data_result:
        logger.error(
            "data_table_load_error",
            path=path,
            error=data_result["error"],
            caller="template",
        )
        return Markup(
            f'<div class="bengal-data-table-error" role="alert">'
            f"<strong>Data Table Error:</strong> {data_result['error']}"
            f"<br><small>File: {path}</small>"
            f"</div>"
        )

    # Generate table ID
    table_id = directive._generate_table_id(path)

    # Build attributes
    attrs = {
        "table_id": table_id,
        "path": path,
        "columns": data_result["columns"],
        "data": data_result["data"],
        "search": directive._parse_bool(options_dict.get("search", "true")),
        "filter": directive._parse_bool(options_dict.get("filter", "true")),
        "sort": directive._parse_bool(options_dict.get("sort", "true")),
        "pagination": directive._parse_pagination(options_dict.get("pagination", "50")),
        "height": options_dict.get("height", "auto"),
        "visible_columns": directive._parse_columns(options_dict.get("columns", "")),
    }

    # Render using directive's renderer
    html = render_data_table(None, "", **attrs)

    return Markup(html)
