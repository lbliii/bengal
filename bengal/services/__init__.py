"""
Service functions for Bengal SSG.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)

Replaces 7 Site mixins with pure functions that operate on SiteSnapshot:
- ThemeService → theme.py
- QueryService → query.py
- DataService → data.py

Key Benefits:
- Pure functions: no hidden state, easier to test
- Operates on immutable SiteSnapshot: thread-safe by construction
- Explicit dependencies: functions declare what they need
- Testable in isolation: no need for full Site instance

Migration Path:
1. Services implemented with both Site and SiteSnapshot support
2. Site mixins delegate to services (compatibility layer)
3. New code uses services directly with SiteSnapshot
4. Eventually mixins can be deprecated

Usage:
    >>> from bengal.services import get_section, get_page, get_theme_assets
    >>>
    >>> # With SiteSnapshot
    >>> section = get_section(snapshot, "/docs/")
    >>> page = get_page(snapshot, "/docs/getting-started/")
    >>>
    >>> # With Site (compatibility)
    >>> section = get_section(site, "/docs/")
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
