"""
Service functions for Bengal SSG.

Pure functions and service classes that operate on SiteSnapshot:
- QueryService → query.py (O(1) page/section lookups)
- ThemeService → theme.py (theme resolution)
- DataService → data.py (data directory loading)

Usage:
    >>> from bengal.services import get_section, get_page
    >>> section = get_section(snapshot, "/docs/")
    >>> page = get_page(snapshot, "/docs/getting-started/")
"""

from bengal.services.data import (
    DataService,
    get_data,
    get_data_file,
    load_data_directory,
)
from bengal.services.query import (
    QueryService,
    get_children_pages,
    get_page,
    get_page_by_path,
    get_page_by_url,
    get_pages_by_section,
    get_pages_by_tag,
    get_section,
    get_section_by_path,
    get_section_by_url,
)
from bengal.services.theme import (
    ThemeService,
    get_theme_assets_chain,
    get_theme_assets_dir,
    get_theme_templates_chain,
)

__all__ = [
    # Data services
    "DataService",
    # Query services
    "QueryService",
    # Theme services
    "ThemeService",
    "get_children_pages",
    "get_data",
    "get_data_file",
    "get_page",
    "get_page_by_path",
    "get_page_by_url",
    "get_pages_by_section",
    "get_pages_by_tag",
    "get_section",
    "get_section_by_path",
    "get_section_by_url",
    "get_theme_assets_chain",
    "get_theme_assets_dir",
    "get_theme_templates_chain",
    "load_data_directory",
]
