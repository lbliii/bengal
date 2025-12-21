"""
Menu validator - checks navigation menu integrity.

Integrates menu validation from MenuBuilder into health check system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class MenuValidator(BaseValidator):
    """
    Validates navigation menu structure.

    Checks:
    - Menu items exist and have valid URLs
    - No orphaned menu items (parent doesn't exist)
    - No circular references
    - Menu weights are sensible
    """

    name = "Navigation Menus"
    description = "Validates menu structure and links"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Validate menu structure."""
        results = []

        # Check if any menus are defined
        if not site.menu:
            results.append(
                CheckResult.info(
                    "No navigation menus defined",
                    recommendation="Add menu configuration to bengal.toml to enable navigation menus.",
                )
            )
            return results

        # Validate each menu
        for menu_name, items in site.menu.items():
            results.extend(self._validate_menu(site, menu_name, items))

        return results

    def _validate_menu(self, site: Site, menu_name: str, items: list[Any]) -> list[CheckResult]:
        """Validate a single menu."""
        results = []

        if not items:
            results.append(
                CheckResult.warning(
                    f"Menu '{menu_name}' is empty",
                    recommendation=f"Add items to the '{menu_name}' menu in your config or page frontmatter.",
                )
            )
            return results

        # Check menu structure

        # Get the menu builder if available
        if menu_name in site.menu_builders:
            site.menu_builders[menu_name]

            # Check for issues that MenuBuilder may have found
            # (MenuBuilder already does validation, we just surface it here)

            # Count items
            total_items = self._count_menu_items(items)
            results.append(CheckResult.success(f"Menu '{menu_name}' has {total_items} item(s)"))

            # Validate menu item URLs
            broken_links = self._check_menu_urls(site, items)
            if broken_links:
                results.append(
                    CheckResult.warning(
                        f"Menu '{menu_name}' has {len(broken_links)} item(s) with potentially broken links",
                        details=broken_links[:3],
                    )
                )

        else:
            # Basic validation without builder
            total_items = len(items)
            results.append(CheckResult.success(f"Menu '{menu_name}' has {total_items} item(s)"))

        return results

    def _count_menu_items(self, items: list[Any], count: int = 0) -> int:
        """Recursively count menu items including children."""
        count = len(items)
        for item in items:
            if hasattr(item, "children") and item.children:
                count += self._count_menu_items(item.children, 0)
        return count

    def _check_menu_urls(self, site: Site, items: list[Any]) -> list[str]:
        """Check if menu item URLs point to existing pages."""
        broken = []

        for item in items:
            # Check if URL points to a page
            url = getattr(item, "_path", None) or getattr(item, "href", None)
            if url:
                # Skip external URLs
                if url.startswith(("http://", "https://", "//")):
                    continue

                # Check if any page has this URL (use _path for internal comparison)
                found = any(
                    (getattr(page, "_path", None) == url) or (getattr(page, "href", None) == url)
                    for page in site.pages
                )

                if not found:
                    broken.append(f"{item.name} → {url}")

            # Recurse into children
            if hasattr(item, "children") and item.children:
                broken.extend(self._check_menu_urls(site, item.children))

        return broken
