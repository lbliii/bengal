"""
Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter.
"""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class MenuOrchestrator:
    """
    Handles navigation menu building with incremental caching.

    Responsibilities:
        - Build menus from config definitions
        - Add items from page frontmatter
        - Mark active menu items for current page
        - Cache menus when config/pages unchanged (incremental optimization)
    """

    def __init__(self, site: "Site"):
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
                        "url": page.url,
                    }
                )

        # Create cache key data
        cache_data = {"config": menu_config, "pages": menu_pages}

        # Hash to create cache key
        data_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _build_full(self) -> bool:
        """
        Build all menus from scratch.

        Returns:
            True (menus were rebuilt)
        """
        from bengal.core.menu import MenuBuilder

        # Get menu definitions from config
        menu_config = self.site.config.get("menu", {})
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
                builder = MenuBuilder()
                if isinstance(items, list):
                    builder.add_from_config(items)
                for page in self.site.pages:
                    page_menu = page.metadata.get("menu", {})
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
                    builder = MenuBuilder()
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
                        if menu_name in page_menu:
                            builder.add_from_page(page, menu_name, page_menu[menu_name])
                    menu_tree = builder.build_hierarchy()
                    self.site.menu_localized[menu_name][lang] = menu_tree
                    self.site.menu_builders_localized.setdefault(menu_name, {})[lang] = builder
                logger.info("menu_built_localized", menu_name=menu_name, languages=len(languages))

        # Update cache key
        self._menu_cache_key = self._compute_menu_cache_key()

        return True

    def mark_active(self, current_page: "Page") -> None:
        """
        Mark active menu items for the current page being rendered.
        Called during rendering for each page.

        Args:
            current_page: Page currently being rendered
        """
        current_url = current_page.url
        for menu_name, builder in self.site.menu_builders.items():
            builder.mark_active_items(current_url, self.site.menu[menu_name])
