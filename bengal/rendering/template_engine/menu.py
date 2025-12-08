"""
Menu helper functions for template engine.

Provides menu access functions with caching for template use.

Related Modules:
    - bengal.rendering.template_engine.core: Uses these helpers
    - bengal.core.menu: Menu data model
"""

from __future__ import annotations

from typing import Any


class MenuHelpersMixin:
    """
    Mixin providing menu helper methods for TemplateEngine.

    Requires these attributes on the host class:
        - site: Site instance
        - _menu_dict_cache: dict[str, list[dict]]
    """

    site: Any
    _menu_dict_cache: dict[str, list[dict[str, Any]]]

    def invalidate_menu_cache(self) -> None:
        """
        Invalidate the menu dict cache.

        Call this after menus are rebuilt to ensure fresh dicts are generated.
        """
        self._menu_dict_cache.clear()

    def _get_menu(self, menu_name: str = "main") -> list[dict[str, Any]]:
        """
        Get menu items as dicts for template access (cached).

        Args:
            menu_name: Name of the menu to get (e.g., 'main', 'footer')

        Returns:
            List of menu item dicts

        Performance:
            Menu dicts are cached to avoid repeated to_dict() calls on every
            page render. Cache is invalidated when menus are rebuilt.
        """
        # If i18n enabled and current_language set, prefer localized menu
        i18n = self.site.config.get("i18n", {}) or {}
        lang = getattr(self.site, "current_language", None)
        if lang and i18n.get("strategy") != "none":
            localized = self.site.menu_localized.get(menu_name, {}).get(lang)
            if localized is not None:
                cache_key = f"{menu_name}:{lang}"
                if cache_key not in self._menu_dict_cache:
                    self._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
                return self._menu_dict_cache[cache_key]

        # Check cache for non-localized menu
        if menu_name not in self._menu_dict_cache:
            menu = self.site.menu.get(menu_name, [])
            self._menu_dict_cache[menu_name] = [item.to_dict() for item in menu]
        return self._menu_dict_cache[menu_name]

    def _get_menu_lang(self, menu_name: str = "main", lang: str = "") -> list[dict[str, Any]]:
        """
        Get menu items for a specific language (cached).

        Args:
            menu_name: Name of the menu to get
            lang: Language code

        Returns:
            List of menu item dicts for the specified language
        """
        if not lang:
            return self._get_menu(menu_name)

        cache_key = f"{menu_name}:{lang}"
        if cache_key in self._menu_dict_cache:
            return self._menu_dict_cache[cache_key]

        localized = self.site.menu_localized.get(menu_name, {}).get(lang)
        if localized is None:
            # Fallback to default
            return self._get_menu(menu_name)

        self._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
        return self._menu_dict_cache[cache_key]
