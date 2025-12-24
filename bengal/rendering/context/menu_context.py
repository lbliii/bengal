"""
Menu context wrapper for templates.

Provides cached access to navigation menus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site


class MenusContext:
    """
    Smart access to navigation menus.

    Example:
        {% for item in menus.main %}
        {% for item in menus.footer %}
        {% for item in menus.get('sidebar') %}

    Performance:
        Menu dicts are cached on first access to avoid repeated .to_dict() calls.
        For a 1000-page site accessing menus 3x per page, this eliminates
        ~3000 unnecessary dict creations per build.
    """

    __slots__ = ("_site", "_cache")

    def __init__(self, site: Site):
        self._site = site
        self._cache: dict[str, list] = {}

    def __getattr__(self, name: str) -> list:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self.get(name)

    def get(self, name: str, lang: str = "") -> list:
        """
        Get menu by name, optionally filtered by language (cached).

        Args:
            name: Menu name (e.g., 'main', 'footer', 'sidebar')
            lang: Optional language code for i18n menus

        Returns:
            List of menu item dicts (cached after first access)
        """
        cache_key = f"{name}:{lang}" if lang else name

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check for localized menu if language specified
        if lang:
            localized = self._site.menu_localized.get(name, {}).get(lang)
            if localized is not None:
                self._cache[cache_key] = [
                    item.to_dict() if hasattr(item, "to_dict") else item for item in localized
                ]
                return self._cache[cache_key]

        # Default menu
        menu = self._site.menu.get(name, [])
        self._cache[cache_key] = [
            item.to_dict() if hasattr(item, "to_dict") else item for item in menu
        ]
        return self._cache[cache_key]

    def invalidate(self) -> None:
        """
        Clear the menu cache.

        Call this when menus are rebuilt (e.g., during dev server reload).
        """
        self._cache.clear()


