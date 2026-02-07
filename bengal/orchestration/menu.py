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

from bengal.orchestration.utils.i18n import get_i18n_config
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str

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
        menu_config = self.site.menu_config

        # Get pages with menu frontmatter
        menu_pages = [
            {
                "path": str(page.source_path),
                "menu": page.metadata["menu"],
                "title": page.title,
                "url": getattr(page, "href", "/"),
            }
            for page in self.site.pages
            if "menu" in page.metadata
        ]

        # Include dev params and section names in cache key
        # (sections affect dev menu bundling)
        params = self.site.config.get("params", {})
        dev_params = {
            "repo_url": params.get("repo_url"),
        }

        # Include section names that affect dev menu (api, cli)
        dev_section_names = sorted(
            section.name
            for section in self.site.sections
            if hasattr(section, "name") and section.name in ("api", "cli")
        )

        # Include dropdown configurations from section frontmatter
        dropdown_configs = []
        for section in self.site.sections:
            if hasattr(section, "index_page") and section.index_page:
                metadata = getattr(section.index_page, "metadata", {})
                menu_cfg = metadata.get("menu", {})
                if isinstance(menu_cfg, dict) and menu_cfg.get("dropdown"):
                    dropdown_cfg = menu_cfg["dropdown"]
                    dropdown_configs.append(
                        {
                            "section": section.name,
                            "dropdown": str(dropdown_cfg),
                        }
                    )
                    # If data-driven, include the data keys
                    if isinstance(dropdown_cfg, str) and dropdown_cfg.startswith("data:"):
                        data_key = dropdown_cfg[5:]
                        if hasattr(self.site.data, data_key):
                            data = getattr(self.site.data, data_key)
                            if isinstance(data, dict):
                                dropdown_configs[-1]["data_keys"] = sorted(data.keys())

        # Include bundles config
        bundles_config = self.site.config.get("menu", {}).get("bundles", {})
        auto_dev_bundle = self.site.config.get("menu", {}).get("auto_dev_bundle", True)

        # Create cache key data
        cache_data = {
            "config": menu_config,
            "pages": menu_pages,
            "dev_params": dev_params,
            "dev_sections": dev_section_names,
            "dropdowns": dropdown_configs,
            "bundles": bundles_config,
            "auto_dev_bundle": auto_dev_bundle,
        }

        # Hash to create cache key
        data_str = json.dumps(cache_data, sort_keys=True)
        return hash_str(data_str)

    def _build_auto_menu_with_dev_bundling(self) -> list[dict[str, Any]]:
        """
        Build auto-discovered menu with configurable bundling.

        Processing hierarchy (most specific wins):
        1. Config bundles [menu.bundles.xxx] - Synthetic dropdowns
        2. Section frontmatter menu.dropdown - Per-section dropdowns
        3. Auto-discovery defaults - Dev bundling when 2+ items

        Returns:
            List of menu item dicts ready for MenuBuilder (with deduplication)
        """
        from bengal.rendering.template_functions.navigation import get_auto_nav

        # Get menu config for bundles
        menu_config = self.site.config.get("menu", {})
        bundles_config = menu_config.get("bundles", {})

        # Detect available assets for bundling
        available_assets = self._detect_bundleable_assets()

        # Determine which sections to exclude from auto-nav (they'll be in bundles)
        sections_to_exclude = set()

        # Process config-defined bundles first (highest priority for bundles)
        config_bundles = self._process_config_bundles(bundles_config, available_assets)
        for bundle in config_bundles:
            sections_to_exclude.update(bundle.get("_exclude_sections", []))

        # Check if Dev bundle should be auto-created (default behavior)
        # Skip if explicitly disabled or if a custom dev bundle is defined in config
        auto_dev_enabled = menu_config.get("auto_dev_bundle", True)
        has_custom_dev_bundle = "dev" in bundles_config

        dev_bundle = None
        if auto_dev_enabled and not has_custom_dev_bundle:
            dev_bundle = self._create_default_dev_bundle(available_assets)
            if dev_bundle:
                sections_to_exclude.update(dev_bundle.get("_exclude_sections", []))

        # Mark sections to exclude from auto-nav
        if sections_to_exclude:
            if self.site._dev_menu_metadata is None:
                self.site._dev_menu_metadata = {}
            self.site._dev_menu_metadata["exclude_sections"] = list(sections_to_exclude)

        # Get auto-discovered sections (will exclude bundled sections)
        auto_items = get_auto_nav(self.site)

        # Clear the exclude flag after use
        if sections_to_exclude and self.site._dev_menu_metadata:
            self.site._dev_menu_metadata.pop("exclude_sections", None)

        # Build menu items list with deduplication
        menu_items = []
        seen_identifiers: set[str] = set()
        seen_urls: set[str] = set()
        seen_names: set[str] = set()

        # Add auto items with deduplication
        for item in auto_items:
            if self._add_item_if_unique(item, menu_items, seen_identifiers, seen_urls, seen_names):
                pass  # Item added

        # Add config-defined bundles
        for bundle in config_bundles:
            self._add_bundle_to_menu(bundle, menu_items, seen_identifiers, seen_urls, seen_names)

        # Add default Dev bundle if applicable
        if dev_bundle:
            self._add_bundle_to_menu(
                dev_bundle, menu_items, seen_identifiers, seen_urls, seen_names
            )
            # Store metadata for template
            if self.site._dev_menu_metadata is None:
                self.site._dev_menu_metadata = {}
            self.site._dev_menu_metadata["github_bundled"] = any(
                item.get("type") == "github" for item in dev_bundle.get("items", [])
            )

        # Process sections with dropdown frontmatter (lowest priority - after bundles)
        menu_items = self._process_dropdown_sections(
            menu_items, seen_identifiers, seen_urls, seen_names
        )

        # Append extra items from menu.extra config (allows adding one-off links in auto mode)
        extra_items = menu_config.get("extra", [])
        if extra_items and isinstance(extra_items, list):
            for item in extra_items:
                if isinstance(item, dict) and "name" in item and "url" in item:
                    self._add_item_if_unique(
                        item, menu_items, seen_identifiers, seen_urls, seen_names
                    )

        return menu_items

    def _detect_bundleable_assets(self) -> dict[str, dict[str, Any]]:
        """
        Detect all assets that can be bundled into dropdowns.

        Returns:
            Dict mapping asset type to asset info (name, url, section if applicable)
        """
        assets: dict[str, dict[str, Any]] = {}
        params = self.site.config.get("params", {})

        # GitHub repo URL
        if repo_url := params.get("repo_url"):
            assets["github"] = {"name": "GitHub", "url": repo_url, "type": "github"}

        # API section
        api_section = self._find_section_by_name("api")
        if api_section:
            api_url = getattr(api_section, "_path", None) or "/api/"
            assets["api"] = {
                "name": api_section.title or "API Reference",
                "url": api_url,
                "type": "api",
                "section": "api",
            }

        # CLI section
        cli_section = self._find_section_by_name("cli")
        if cli_section:
            cli_url = getattr(cli_section, "_path", None) or "/cli/"
            assets["cli"] = {
                "name": cli_section.title or "CLI Reference",
                "url": cli_url,
                "type": "cli",
                "section": "cli",
            }

        return assets

    def _process_config_bundles(
        self, bundles_config: dict[str, Any], available_assets: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Process config-defined bundles from [menu.bundles.xxx].

        Config format:
            [menu.bundles.dev]
            name = "Developer"
            weight = 90
            items = ["github", "api", "cli"]
            min_items = 2

        Args:
            bundles_config: Dict of bundle configurations
            available_assets: Available assets that can be bundled

        Returns:
            List of bundle dicts with name, url, items, weight, _exclude_sections
        """
        bundles = []

        for bundle_id, config in bundles_config.items():
            if not isinstance(config, dict):
                continue

            # Check if bundle is enabled (default true)
            if not config.get("enabled", True):
                continue

            # Get bundle settings
            bundle_name = config.get("name", bundle_id.title())
            bundle_weight = config.get("weight", 90)
            bundle_url = config.get("url", "#")
            requested_items = config.get("items", [])
            min_items = config.get("min_items", 2)

            # Collect available items for this bundle
            bundle_items = []
            exclude_sections = []

            for item_type in requested_items:
                if item_type in available_assets:
                    asset = available_assets[item_type]
                    bundle_items.append(asset)
                    if "section" in asset:
                        exclude_sections.append(asset["section"])

            # Only create bundle if enough items
            if len(bundle_items) >= min_items:
                bundles.append(
                    {
                        "identifier": f"{bundle_id}-bundle",
                        "name": bundle_name,
                        "url": bundle_url,
                        "weight": bundle_weight,
                        "items": bundle_items,
                        "_exclude_sections": exclude_sections,
                    }
                )

        return bundles

    def _create_default_dev_bundle(
        self, available_assets: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Create the default Dev bundle if conditions are met.

        Default behavior: Bundle GitHub, API, CLI into "Dev" dropdown
        when 2+ of these assets exist.

        Args:
            available_assets: Available assets

        Returns:
            Bundle dict or None if conditions not met
        """
        dev_item_types = ["github", "api", "cli"]
        dev_items = []
        exclude_sections = []

        for item_type in dev_item_types:
            if item_type in available_assets:
                asset = available_assets[item_type]
                dev_items.append(asset)
                if "section" in asset:
                    exclude_sections.append(asset["section"])

        # Only bundle if 2+ items
        if len(dev_items) < 2:
            return None

        return {
            "identifier": "dev-auto",
            "name": "Dev",
            "url": "#",
            "weight": 90,
            "items": dev_items,
            "_exclude_sections": exclude_sections,
        }

    def _add_item_if_unique(
        self,
        item: dict[str, Any],
        menu_items: list[dict[str, Any]],
        seen_identifiers: set[str],
        seen_urls: set[str],
        seen_names: set[str],
    ) -> bool:
        """
        Add item to menu if it's unique (not a duplicate).

        Returns:
            True if item was added, False if duplicate
        """
        item_id = item.get("identifier")
        item_url = item.get("url", "").rstrip("/")
        item_name = item.get("name", "").lower()

        # Check for duplicates
        if item_id and item_id in seen_identifiers:
            return False
        if item_url and item_url in seen_urls:
            return False
        if item_name and item_name in seen_names:
            return False

        # Add item
        menu_items.append(item)
        if item_id:
            seen_identifiers.add(item_id)
        if item_url:
            seen_urls.add(item_url)
        if item_name:
            seen_names.add(item_name)

        return True

    def _add_bundle_to_menu(
        self,
        bundle: dict[str, Any],
        menu_items: list[dict[str, Any]],
        seen_identifiers: set[str],
        seen_urls: set[str],
        seen_names: set[str],
    ) -> None:
        """
        Add a bundle (parent + children) to the menu.

        Args:
            bundle: Bundle dict with identifier, name, url, items, weight
            menu_items: Menu items list to append to
            seen_*: Deduplication sets
        """
        parent_id = bundle["identifier"]

        # Add parent item if not already present
        if parent_id not in seen_identifiers:
            parent_item = {
                "name": bundle["name"],
                "url": bundle["url"],
                "identifier": parent_id,
                "weight": bundle["weight"],
            }
            menu_items.append(parent_item)
            seen_identifiers.add(parent_id)

        # Add child items
        order_map = {"github": 1, "api": 2, "cli": 3}
        items = sorted(bundle.get("items", []), key=lambda x: order_map.get(x.get("type", ""), 99))

        for i, item in enumerate(items):
            item_url = item["url"].rstrip("/")
            item_name = item["name"].lower()

            # Skip if duplicate
            if item_url in seen_urls or item_name in seen_names:
                continue

            menu_items.append(
                {
                    "name": item["name"],
                    "url": item["url"],
                    "parent": parent_id,
                    "weight": i + 1,
                }
            )
            seen_urls.add(item_url)
            seen_names.add(item_name)

    def _process_dropdown_sections(
        self,
        menu_items: list[dict[str, Any]],
        seen_identifiers: set[str],
        seen_urls: set[str],
        seen_names: set[str],
    ) -> list[dict[str, Any]]:
        """
        Process sections with dropdown configuration in their _index.md frontmatter.

        Supports two dropdown modes:
        - dropdown: true - Shows subsections as dropdown children
        - dropdown: data:filename - Shows items from data/filename.yaml

        Example frontmatter:
            ---
            title: Learning Tracks
            menu:
              dropdown: data:tracks
            ---

            ---
            title: Documentation
            menu:
              dropdown: true
            ---

        Args:
            menu_items: Current list of menu items
            seen_identifiers: Set of seen identifiers for deduplication
            seen_urls: Set of seen URLs for deduplication
            seen_names: Set of seen names for deduplication

        Returns:
            Updated menu items list with dropdown children added
        """
        # Find sections with dropdown configuration
        for section in self.site.sections:
            if not hasattr(section, "index_page") or not section.index_page:
                continue

            index_page = section.index_page
            metadata = getattr(index_page, "metadata", {})
            menu_config = metadata.get("menu", {})

            # Skip if no dropdown config
            if not isinstance(menu_config, dict):
                continue

            dropdown_config = menu_config.get("dropdown")
            if not dropdown_config:
                continue

            # Find this section in menu items
            section_url = getattr(section, "_path", None) or f"/{section.name}/"
            section_item = None
            for item in menu_items:
                item_url = item.get("url", "").rstrip("/")
                if item_url == section_url.rstrip("/") or item.get("identifier") == section.name:
                    section_item = item
                    break

            if not section_item:
                continue

            # Ensure section item has an identifier for parent reference
            parent_id = section_item.get("identifier") or section.name
            section_item["identifier"] = parent_id

            # Process based on dropdown type
            if dropdown_config is True:
                # dropdown: true - add subsections as children
                self._add_subsection_children(
                    section, parent_id, menu_items, seen_identifiers, seen_urls, seen_names
                )
            elif isinstance(dropdown_config, str) and dropdown_config.startswith("data:"):
                # dropdown: data:filename - load from data file
                data_key = dropdown_config[5:]  # Remove "data:" prefix
                self._add_data_children(
                    section,
                    parent_id,
                    data_key,
                    menu_items,
                    seen_identifiers,
                    seen_urls,
                    seen_names,
                )

        return menu_items

    def _add_subsection_children(
        self,
        section: Any,
        parent_id: str,
        menu_items: list[dict[str, Any]],
        seen_identifiers: set[str],
        seen_urls: set[str],
        seen_names: set[str],
    ) -> None:
        """
        Add subsections as dropdown children.

        Args:
            section: Parent section
            parent_id: Parent menu item identifier
            menu_items: Menu items list to append to
            seen_*: Deduplication sets
        """
        from bengal.rendering.template_functions.navigation.helpers import get_nav_title

        if not hasattr(section, "subsections"):
            return

        for i, subsection in enumerate(section.subsections):
            # Get subsection info
            sub_name = getattr(subsection, "name", "")
            sub_url = getattr(subsection, "_path", None) or f"/{section.name}/{sub_name}/"
            sub_title = get_nav_title(subsection, sub_name.replace("-", " ").title())

            # Check for nav_title in index page
            if hasattr(subsection, "index_page") and subsection.index_page:
                sub_title = get_nav_title(subsection.index_page, sub_title)

            # Skip if duplicate
            if sub_url.rstrip("/") in seen_urls or sub_title.lower() in seen_names:
                continue

            # Check if subsection is hidden from menu
            if hasattr(subsection, "index_page") and subsection.index_page:
                sub_metadata = getattr(subsection.index_page, "metadata", {})
                sub_menu = sub_metadata.get("menu", True)
                if sub_menu is False:
                    continue

            menu_items.append(
                {
                    "name": sub_title,
                    "url": sub_url,
                    "parent": parent_id,
                    "weight": getattr(subsection, "weight", i + 1),
                    "identifier": f"{parent_id}-{sub_name}",
                }
            )
            seen_urls.add(sub_url.rstrip("/"))
            seen_names.add(sub_title.lower())

    def _add_data_children(
        self,
        section: Any,
        parent_id: str,
        data_key: str,
        menu_items: list[dict[str, Any]],
        seen_identifiers: set[str],
        seen_urls: set[str],
        seen_names: set[str],
    ) -> None:
        """
        Add children from a data file.

        Loads data from site.data[data_key] and creates menu items.
        Expects data to be a dict where keys are slugs and values have 'title'.

        Args:
            section: Parent section
            parent_id: Parent menu item identifier
            data_key: Key to look up in site.data (e.g., 'tracks')
            menu_items: Menu items list to append to
            seen_*: Deduplication sets
        """
        # Get data from site.data
        if not hasattr(self.site.data, data_key):
            return

        data = getattr(self.site.data, data_key)
        if not data or not isinstance(data, dict):
            return

        section_url = getattr(section, "_path", None) or f"/{section.name}/"

        # Add each data item as a child
        for i, (item_id, item_info) in enumerate(data.items()):
            if isinstance(item_info, dict):
                item_title = item_info.get("title", item_id.replace("-", " ").title())
            else:
                item_title = item_id.replace("-", " ").title()

            item_url = f"{section_url.rstrip('/')}/{item_id}/"

            # Skip if duplicate
            if item_url.rstrip("/") in seen_urls or item_title.lower() in seen_names:
                continue

            menu_items.append(
                {
                    "name": item_title,
                    "url": item_url,
                    "parent": parent_id,
                    "weight": i + 1,
                    "identifier": f"{parent_id}-{item_id}",
                }
            )
            seen_urls.add(item_url.rstrip("/"))
            seen_names.add(item_title.lower())

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

        Raises:
            BengalError: If menu building fails with configuration or page errors
        """
        import copy

        from bengal.core.menu import MenuBuilder
        from bengal.errors import BengalError, ErrorCode, ErrorContext, enrich_error

        # Get menu definitions from config (make deep copy to avoid mutating site config)
        try:
            raw_menu_config = self.site.menu_config
            menu_config = copy.deepcopy(raw_menu_config)
        except Exception as e:
            context = ErrorContext(
                operation="loading menu configuration",
                suggestion="Check menu config syntax in bengal.toml",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalError)
            logger.error(
                "menu_build_failed",
                menu_name="config",
                error=str(enriched),
                error_type=type(e).__name__,
                error_code=ErrorCode.B004.value,
                suggestion="Check menu configuration in site config",
            )
            raise enriched from e

        # For "main" menu, integrate auto-nav and dev bundling directly
        # This ensures single source of truth - no separate injection step
        if "main" not in menu_config or not menu_config["main"]:
            # Auto mode: build menu from sections with dev bundling
            menu_config["main"] = self._build_auto_menu_with_dev_bundling()

        # Get i18n configuration using utility
        i18n_config = get_i18n_config(self.site.config)
        strategy = i18n_config.strategy
        # When i18n enabled, build per-locale menus keyed by site.menu_localized[lang]
        languages: set[str] = set(i18n_config.languages) if i18n_config.is_enabled else set()

        if not menu_config:
            # No menus defined, skip
            return False

        logger.info("menu_build_start", menu_count=len(menu_config))

        for menu_name, items in menu_config.items():
            if strategy == "none":
                try:
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
                except KeyError as e:
                    context = ErrorContext(
                        operation=f"building menu '{menu_name}'",
                        suggestion="Check menu config for missing or misspelled page references",
                        original_error=e,
                    )
                    enriched = enrich_error(e, context, BengalError)
                    logger.error(
                        "menu_build_failed",
                        menu_name=menu_name,
                        error=str(enriched),
                        error_type=type(e).__name__,
                        error_code=ErrorCode.B004.value,
                        suggestion="Verify menu config syntax and ensure referenced pages exist",
                    )
                    raise enriched from e
                except Exception as e:
                    logger.error(
                        "menu_build_failed",
                        menu_name=menu_name,
                        error=str(e),
                        error_type=type(e).__name__,
                        error_code=ErrorCode.B004.value,
                        suggestion="Check menu configuration in site config",
                    )
                    raise
            else:
                # Build per-locale
                self.site.menu_localized.setdefault(menu_name, {})
                for lang in sorted(languages):
                    try:
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
                    except KeyError as e:
                        context = ErrorContext(
                            operation=f"building localized menu '{menu_name}' for language '{lang}'",
                            suggestion="Check menu config for missing or misspelled page references",
                            original_error=e,
                        )
                        enriched = enrich_error(e, context, BengalError)
                        logger.error(
                            "menu_build_failed",
                            menu_name=menu_name,
                            lang=lang,
                            error=str(enriched),
                            error_type=type(e).__name__,
                            error_code=ErrorCode.B004.value,
                            suggestion="Verify menu config syntax and ensure referenced pages exist",
                        )
                        raise enriched from e
                    except Exception as e:
                        logger.error(
                            "menu_build_failed",
                            menu_name=menu_name,
                            lang=lang,
                            error=str(e),
                            error_type=type(e).__name__,
                            error_code=ErrorCode.B004.value,
                            suggestion="Check menu configuration in site config",
                        )
                        raise
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
