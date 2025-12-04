"""
Menu stream for building navigation menus from pages and sections.

This module provides stream-based menu building that replaces MenuOrchestrator
with a declarative, reactive approach.

Flow:
    pages + sections → build_menu_structure → site.menu populated
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from bengal.pipeline.core import Stream
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_menu_stream(
    pages_stream: Stream[Page],
    site: Site,
) -> Stream[Page]:
    """
    Create a stream that builds navigation menus from pages and sections.

    This stream:
    1. Collects all pages
    2. Builds menu structure from config and page frontmatter
    3. Populates site.menu with built menus
    4. Returns pages unchanged (menus are side-effect on site)

    Args:
        pages_stream: Stream of Page objects
        site: Site instance (menus are stored here)

    Returns:
        Stream emitting same pages (menus built as side-effect)

    Example:
        >>> pages = Stream.from_iterable(site.pages)
        >>> menu_stream = create_menu_stream(pages, site)
        >>> # After iterating, site.menu is populated
        >>> list(menu_stream.iterate())
    """
    # Collect all pages first (barrier operation)
    collected_pages = pages_stream.collect(name="collect_pages_for_menu")

    # Build menus and return pages unchanged
    def build_menus(pages: list[Page]) -> list[Page]:
        """
        Build menus from pages and sections.

        This function:
        1. Builds menu structure from config and page frontmatter
        2. Populates site.menu with built menus
        3. Returns pages unchanged (menus are side-effect)

        Args:
            pages: List of all pages

        Returns:
            Same list of pages (menus built as side-effect)
        """
        # Populate site.pages temporarily (menu building expects this)
        original_pages = site.pages
        site.pages = pages

        try:
            # Build menus
            _build_menus(site)
        finally:
            # Restore original pages
            site.pages = original_pages

        return pages

    # Build menus and flatten back to individual pages
    processed_stream = collected_pages.map(build_menus, name="build_menus")

    # Flatten back to individual pages
    flattened_stream = processed_stream.flat_map(
        lambda pages: iter(pages), name="flatten_menu_pages"
    )

    return flattened_stream


def _build_menus(site: Site) -> None:
    """
    Build all menus from config and page frontmatter.

    This populates site.menu with built menu structures.

    Args:
        site: Site instance (menus are stored here)
    """
    from bengal.core.menu import MenuBuilder

    # Get menu definitions from config (make deep copy to avoid mutating site config)
    raw_menu_config = site.config.get("menu", {})
    menu_config = copy.deepcopy(raw_menu_config)

    # For "main" menu, integrate auto-nav and dev bundling directly
    if "main" not in menu_config or not menu_config["main"]:
        # Auto mode: build menu from sections with dev bundling
        menu_config["main"] = _build_auto_menu_with_dev_bundling(site)

    i18n = site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    # When i18n enabled, build per-locale menus keyed by site.menu_localized[lang]
    languages: set[str] = set()
    if strategy != "none":
        langs_cfg = i18n.get("languages") or []
        for entry in langs_cfg:
            if isinstance(entry, dict) and "code" in entry:
                languages.add(entry["code"])
            elif isinstance(entry, str):
                languages.add(entry)
        default_lang = i18n.get("default_language", "en")
        languages.add(default_lang)

    if not menu_config:
        # No menus defined, skip
        return

    logger.info("menu_build_start", menu_count=len(menu_config))

    for menu_name, items in menu_config.items():
        if strategy == "none":
            builder = MenuBuilder()
            if isinstance(items, list):
                builder.add_from_config(items)
            for page in site.pages:
                page_menu = page.metadata.get("menu", {})
                if menu_name in page_menu:
                    builder.add_from_page(page, menu_name, page_menu[menu_name])
            site.menu[menu_name] = builder.build_hierarchy()
            site.menu_builders[menu_name] = builder
            logger.info("menu_built", menu_name=menu_name, item_count=len(site.menu[menu_name]))
        else:
            # Build per-locale
            site.menu_localized.setdefault(menu_name, {})
            for lang in sorted(languages):
                builder = MenuBuilder()
                # Config-defined items may have optional 'lang'
                if isinstance(items, list):
                    filtered_items = []
                    for it in items:
                        if isinstance(it, dict) and "lang" in it and it["lang"] not in (lang, "*"):
                            continue
                        filtered_items.append(it)
                    builder.add_from_config(filtered_items)
                # Pages in this language
                for page in site.pages:
                    if getattr(page, "lang", None) and page.lang != lang:
                        continue
                    page_menu = page.metadata.get("menu", {})
                    if menu_name in page_menu:
                        builder.add_from_page(page, menu_name, page_menu[menu_name])
                menu_tree = builder.build_hierarchy()
                site.menu_localized[menu_name][lang] = menu_tree
                site.menu_builders_localized.setdefault(menu_name, {})[lang] = builder
            logger.info("menu_built_localized", menu_name=menu_name, languages=len(languages))


def _build_auto_menu_with_dev_bundling(site: Site) -> list[dict]:
    """
    Build auto-discovered menu with dev assets bundled into dropdown.

    This is the single source of truth for auto menu generation.
    Integrates section discovery, dev bundling, and menu structure in one place.

    Args:
        site: Site instance

    Returns:
        List of menu item dicts ready for MenuBuilder (with deduplication)
    """
    from bengal.rendering.template_functions.navigation import get_auto_nav

    # Detect dev assets first
    dev_assets = []
    dev_sections_to_remove = set()

    params = site.config.get("params", {})

    # Check for GitHub repo URL
    if repo_url := params.get("repo_url"):
        dev_assets.append({"name": "GitHub", "url": repo_url, "type": "github"})

    # Check for API section
    api_section = _find_section_by_name(site, "api")
    if api_section:
        # Use relative_url (templates apply baseurl via | absolute_url filter)
        api_url = getattr(api_section, "relative_url", "/api/")
        dev_assets.append({"name": "API Reference", "url": api_url, "type": "api"})
        dev_sections_to_remove.add("api")

    # Check for CLI section
    cli_section = _find_section_by_name(site, "cli")
    if cli_section:
        # Use relative_url (templates apply baseurl via | absolute_url filter)
        cli_url = getattr(cli_section, "relative_url", "/cli/")
        dev_assets.append({"name": "bengal CLI", "url": cli_url, "type": "cli"})
        dev_sections_to_remove.add("cli")

    # Mark dev sections to exclude from auto-nav
    if dev_sections_to_remove:
        if not hasattr(site, "_dev_menu_metadata"):
            site._dev_menu_metadata = {}
        site._dev_menu_metadata["exclude_sections"] = list(dev_sections_to_remove)

    # Get auto-discovered sections (will exclude dev sections)
    auto_items = get_auto_nav(site)

    # Clear the exclude flag after use
    if hasattr(site, "_dev_menu_metadata") and "exclude_sections" in site._dev_menu_metadata:
        del site._dev_menu_metadata["exclude_sections"]

    # Build menu items list with deduplication
    menu_items = []
    seen_identifiers = set()
    seen_urls = set()
    seen_names = set()

    # Add auto items with deduplication
    for item in auto_items:
        item_id = item.get("identifier")
        item_url = item.get("url", "").rstrip("/")
        item_name = item.get("name", "").lower()

        # Skip duplicates
        if item_id and item_id in seen_identifiers:
            continue
        if item_url and item_url in seen_urls:
            continue
        if item_name and item_name in seen_names:
            continue

        menu_items.append(item)
        if item_id:
            seen_identifiers.add(item_id)
        if item_url:
            seen_urls.add(item_url)
        if item_name:
            seen_names.add(item_name)

    # Bundle dev assets if 2+ exist
    if len(dev_assets) >= 2:
        parent_id = "dev-auto"

        # Check if Dev already exists
        if parent_id not in seen_identifiers:
            # Add Dev parent item
            menu_items.append(
                {
                    "name": "Dev",
                    "url": "#",
                    "identifier": parent_id,
                    "weight": 90,
                }
            )
            seen_identifiers.add(parent_id)

        # Add dev asset children in order
        order_map = {"github": 1, "api": 2, "cli": 3}
        dev_assets.sort(key=lambda x: order_map.get(x["type"], 99))

        for i, asset in enumerate(dev_assets):
            asset_url = asset["url"].rstrip("/")
            asset_name = asset["name"].lower()

            # Skip if duplicate
            if asset_url in seen_urls or asset_name in seen_names:
                continue

            menu_items.append(
                {
                    "name": asset["name"],
                    "url": asset["url"],
                    "parent": parent_id,
                    "weight": i + 1,
                }
            )
            seen_urls.add(asset_url)
            seen_names.add(asset_name)

        # Store metadata for template
        if not hasattr(site, "_dev_menu_metadata"):
            site._dev_menu_metadata = {}
        site._dev_menu_metadata["github_bundled"] = any(a["type"] == "github" for a in dev_assets)

    return menu_items


def _find_section_by_name(site: Site, section_name: str) -> Any | None:
    """
    Find a section by its name/slug.

    Args:
        site: Site instance
        section_name: Section name to find (e.g., 'api', 'cli')

    Returns:
        Section object if found, None otherwise
    """
    for section in site.sections:
        if not hasattr(section, "name"):
            continue
        if section.name == section_name:
            return section
    return None
