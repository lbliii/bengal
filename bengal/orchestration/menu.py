"""
Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter. Supports
incremental menu building with caching, i18n localization, and active state
tracking. Menus are built during content discovery and cached for template access.

Key Concepts:
    - Menu sources: Config definitions, page frontmatter, section structure
    - Incremental caching: Menu cache invalidation on content changes
    - i18n menus: Localized menu variants per language
    - Active state: Current page and active trail tracking

Related Modules:
    - bengal.core.menu: Menu data structures (MenuItem, MenuBuilder)
    - bengal.core.site: Site container that holds menus
    - bengal.rendering.template_functions.navigation: Template access to menus

See Also:
    - bengal/orchestration/menu.py:MenuOrchestrator for menu building logic
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class MenuOrchestrator:
    """
    Orchestrates navigation menu building with incremental caching.

    Handles menu building from config definitions, page frontmatter, and section
    structure. Supports incremental menu building by caching menus when config
    and menu-related pages are unchanged.

    Creation:
        Direct instantiation: MenuOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with pages and config populated

    Attributes:
        site: Site instance containing menu configuration and pages
        _menu_cache_key: Cache key for incremental menu building

    Relationships:
        - Uses: MenuBuilder for menu construction
        - Uses: MenuItem for menu item representation
        - Used by: BuildOrchestrator for menu building phase
        - Updates: site.menu with built menus

    Thread Safety:
        Not thread-safe. Should be used from single thread during build.

    Examples:
        orchestrator = MenuOrchestrator(site)
        rebuilt = orchestrator.build(changed_pages=changed, config_changed=False)
    """

    def __init__(self, site: Site):
        """
        Initialize menu orchestrator.

        Args:
            site: Site instance containing menu configuration
        """
        self.site = site
        self._menu_cache_key: str | None = None

    def build(self, changed_pages: set[Path] | None = None, config_changed: bool = False) -> bool:
        """
        Build all menus from config and page frontmatter.

        With incremental building:
        - If config unchanged AND no pages with menu frontmatter changed
        - Skip rebuild and reuse cached menus

        Args:
            changed_pages: Set of paths for pages that changed (for incremental builds)
            config_changed: Whether config file changed (forces rebuild)

        Returns:
            True if menus were rebuilt, False if cached menus reused

        Called during site.build() after content discovery.
        """
        # Check if we can skip menu rebuild
        if (
            not config_changed
            and changed_pages is not None
            and self._can_skip_rebuild(changed_pages)
        ):
            logger.debug("menu_rebuild_skipped", reason="cache_valid")
            return False

        # Full menu rebuild needed
        return self._build_full()

    def _can_skip_rebuild(self, changed_pages: set[Path]) -> bool:
        """
        Check if menu rebuild can be skipped (incremental optimization).

        Menus need rebuild only if:
        1. Config changed (menu definitions)
        2. Pages with 'menu' frontmatter changed

        Args:
            changed_pages: Set of changed page paths

        Returns:
            True if rebuild can be skipped (menus unchanged)
        """
        # No existing menus - need full build
        if not self.site.menu:
            return False

        # Check if any changed pages have menu frontmatter
        for page in self.site.pages:
            if page.source_path in changed_pages and "menu" in page.metadata:
                # Menu-related page changed - need rebuild
                return False

        # Compute cache key based on menu config and pages with menu frontmatter
        current_key = self._compute_menu_cache_key()

        # Compare with previous cache key
        if self._menu_cache_key is None:
            # First build - need full rebuild
            self._menu_cache_key = current_key
            return False

        if current_key == self._menu_cache_key:
            # Menu config and pages unchanged - can skip!
            return True

        # Config or pages changed - need rebuild
        self._menu_cache_key = current_key
        return False

    def _compute_menu_cache_key(self) -> str:
        """
        Compute cache key for current menu configuration.

        Key includes:
        - Menu config from bengal.toml
        - List of pages with menu frontmatter and their menu data
        - Dev params (repo_url)
        - Dev section names (api, cli) that affect dev menu bundling

        Returns:
            SHA256 hash of menu-related data
        """
        # Get menu config
        menu_config = self.site.config.get("menu", {})

        # Get pages with menu frontmatter
        menu_pages = []
        for page in self.site.pages:
            if "menu" in page.metadata:
                menu_pages.append(
                    {
                        "path": str(page.source_path),
                        "menu": page.metadata["menu"],
                        "title": page.title,
                        "url": getattr(page, "href", "/"),
                    }
                )

        # Include dev params and section names in cache key
        # (sections affect dev menu bundling)
        params = self.site.config.get("params", {})
        dev_params = {
            "repo_url": params.get("repo_url"),
        }

        # Include section names that affect dev menu (api, cli)
        dev_section_names = []
        for section in self.site.sections:
            if hasattr(section, "name") and section.name in ("api", "cli"):
                dev_section_names.append(section.name)
        dev_section_names.sort()

        # Create cache key data
        cache_data = {
            "config": menu_config,
            "pages": menu_pages,
            "dev_params": dev_params,
            "dev_sections": dev_section_names,
        }

        # Hash to create cache key
        data_str = json.dumps(cache_data, sort_keys=True)
        return hash_str(data_str)

    def _build_auto_menu_with_dev_bundling(self) -> list[dict[str, Any]]:
        """
        Build auto-discovered menu with dev assets bundled into dropdown.

        This is the single source of truth for auto menu generation.
        Integrates section discovery, dev bundling, and menu structure in one place.

        Returns:
            List of menu item dicts ready for MenuBuilder (with deduplication)
        """
        from bengal.rendering.template_functions.navigation import get_auto_nav

        # Detect dev assets first
        dev_assets = []
        dev_sections_to_remove = set()

        params = self.site.config.get("params", {})

        # Check for GitHub repo URL
        if repo_url := params.get("repo_url"):
            dev_assets.append({"name": "GitHub", "url": repo_url, "type": "github"})

        # Check for API section
        api_section = self._find_section_by_name("api")
        if api_section:
            # Use _path (templates apply baseurl via | absolute_url filter)
            api_url = getattr(api_section, "_path", None) or "/api/"
            dev_assets.append({"name": "API Reference", "url": api_url, "type": "api"})
            dev_sections_to_remove.add("api")

        # Check for CLI section
        cli_section = self._find_section_by_name("cli")
        if cli_section:
            # Use _path (templates apply baseurl via | absolute_url filter)
            cli_url = getattr(cli_section, "_path", None) or "/cli/"
            dev_assets.append({"name": "bengal CLI", "url": cli_url, "type": "cli"})
            dev_sections_to_remove.add("cli")

        # Only exclude API/CLI sections from auto-nav when we are actually bundling them
        # into the Dev dropdown (2+ dev assets). If there is only one dev asset, it should
        # remain visible as a normal top-level nav item.
        should_bundle = len(dev_assets) >= 2

        # Mark dev sections to exclude from auto-nav (only when bundling is active)
        if should_bundle and dev_sections_to_remove:
            if self.site._dev_menu_metadata is None:
                self.site._dev_menu_metadata = {}
            self.site._dev_menu_metadata["exclude_sections"] = list(dev_sections_to_remove)

        # Get auto-discovered sections (will exclude dev sections)
        auto_items = get_auto_nav(self.site)

        # Clear the exclude flag after use
        if should_bundle and (
            self.site._dev_menu_metadata is not None
            and "exclude_sections" in self.site._dev_menu_metadata
        ):
            del self.site._dev_menu_metadata["exclude_sections"]

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
        if should_bundle:
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
            if self.site._dev_menu_metadata is None:
                self.site._dev_menu_metadata = {}
            self.site._dev_menu_metadata["github_bundled"] = any(
                a["type"] == "github" for a in dev_assets
            )
        else:
            # Single dev asset case: do NOT hide it behind Dev (Dev requires 2+), but also
            # do NOT rely on section auto-nav for virtual autodoc sections (path=None).
            #
            # If the only available dev asset is API or CLI, expose it as a normal top-level
            # menu item so it remains discoverable.
            for asset in dev_assets:
                if asset.get("type") not in {"api", "cli"}:
                    continue

                asset_url = asset.get("url", "").rstrip("/")
                asset_name = asset.get("name", "").lower()

                if (asset_url and asset_url in seen_urls) or (
                    asset_name and asset_name in seen_names
                ):
                    continue

                menu_items.append(
                    {
                        "name": asset["name"],
                        "url": asset["url"],
                        "identifier": asset["type"],
                        "weight": 90,
                    }
                )
                if asset_url:
                    seen_urls.add(asset_url)
                if asset_name:
                    seen_names.add(asset_name)

        return menu_items

    def _find_section_by_name(self, section_name: str) -> Any | None:
        """
        Find a section by its name/slug.

        Args:
            section_name: Section name to find (e.g., 'api', 'cli')

        Returns:
            Section object if found, None otherwise
        """
        for section in self.site.sections:
            if not hasattr(section, "name"):
                continue
            if section.name == section_name:
                return section
        return None

    def _build_full(self) -> bool:
        """
        Build all menus from scratch.

        Returns:
            True (menus were rebuilt)
        """
        import copy

        from bengal.core.menu import MenuBuilder

        # Get menu definitions from config (make deep copy to avoid mutating site config)
        raw_menu_config = self.site.config.get("menu", {})
        menu_config = copy.deepcopy(raw_menu_config)

        # For "main" menu, integrate auto-nav and dev bundling directly
        # This ensures single source of truth - no separate injection step
        if "main" not in menu_config or not menu_config["main"]:
            # Auto mode: build menu from sections with dev bundling
            menu_config["main"] = self._build_auto_menu_with_dev_bundling()

        i18n = self.site.config.get("i18n", {}) or {}
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
            return False

        logger.info("menu_build_start", menu_count=len(menu_config))

        for menu_name, items in menu_config.items():
            if strategy == "none":
                builder = MenuBuilder(diagnostics=getattr(self.site, "diagnostics", None))
                if isinstance(items, list):
                    builder.add_from_config(items)
                for page in self.site.pages:
                    page_menu = page.metadata.get("menu", {})
                    # Skip if menu is False or not a dict (menu: false means hide from menu)
                    if not isinstance(page_menu, dict):
                        continue
                    if menu_name in page_menu:
                        builder.add_from_page(page, menu_name, page_menu[menu_name])
                self.site.menu[menu_name] = builder.build_hierarchy()
                self.site.menu_builders[menu_name] = builder
                logger.info(
                    "menu_built", menu_name=menu_name, item_count=len(self.site.menu[menu_name])
                )
            else:
                # Build per-locale
                self.site.menu_localized.setdefault(menu_name, {})
                for lang in sorted(languages):
                    builder = MenuBuilder(diagnostics=getattr(self.site, "diagnostics", None))
                    # Config-defined items may have optional 'lang'
                    if isinstance(items, list):
                        filtered_items = []
                        for it in items:
                            if (
                                isinstance(it, dict)
                                and "lang" in it
                                and it["lang"] not in (lang, "*")
                            ):
                                continue
                            filtered_items.append(it)
                        builder.add_from_config(filtered_items)
                    # Pages in this language
                    for page in self.site.pages:
                        if getattr(page, "lang", None) and page.lang != lang:
                            continue
                        page_menu = page.metadata.get("menu", {})
                        # Skip if menu is False or not a dict (menu: false means hide from menu)
                        if not isinstance(page_menu, dict):
                            continue
                        if menu_name in page_menu:
                            builder.add_from_page(page, menu_name, page_menu[menu_name])
                    menu_tree = builder.build_hierarchy()
                    self.site.menu_localized[menu_name][lang] = menu_tree
                    self.site.menu_builders_localized.setdefault(menu_name, {})[lang] = builder
                logger.info("menu_built_localized", menu_name=menu_name, languages=len(languages))

        # Update cache key
        self._menu_cache_key = self._compute_menu_cache_key()

        return True

    def mark_active(self, current_page: Page) -> None:
        """
        Mark active menu items for the current page being rendered.
        Called during rendering for each page.

        Args:
            current_page: Page currently being rendered
        """
        # Use _path for comparison (menu items store site-relative paths)
        current_url = getattr(current_page, "_path", None) or "/"
        for menu_name, builder in self.site.menu_builders.items():
            builder.mark_active_items(current_url, self.site.menu[menu_name])
