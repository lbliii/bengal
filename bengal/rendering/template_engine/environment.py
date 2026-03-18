"""
Theme resolution utilities for template engines.

Provides theme inheritance chain resolution and theme manifest reading.
These functions are engine-agnostic and used by both Kida and any other
template engine integrations.

Related Modules:
- bengal.rendering.engines.kida: Uses resolve_theme_chain
- bengal.core.theme: Theme package resolution

"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

# Imported at module level so tests can patch this target:
#   bengal.rendering.template_engine.environment.get_theme_package
from bengal.core.theme import get_theme_package


def resolve_theme_chain(active_theme: str | None, site: SiteLike) -> list[str]:
    """
    Resolve theme inheritance chain starting from the active theme.

    Order: child first → parent → ... (do not duplicate 'default').

    When active_theme is "default" (or None), returns ["default"] so that
    the bundled default theme assets are discovered. For child themes that
    extend "default", filters out "default" since it's added as a fallback
    separately in template loaders.

    Args:
        active_theme: Active theme name
        site: Site instance

    Returns:
        List of theme names in inheritance order

    """
    chain = []
    visited: set[str] = set()
    current = active_theme or "default"
    depth = 0
    MAX_DEPTH = 5

    while current and current not in visited and depth < MAX_DEPTH:
        visited.add(current)
        chain.append(current)
        extends = read_theme_extends(current, site)
        if not extends or extends == current:
            break
        current = extends
        depth += 1

    # When active_theme is "default" itself, keep it so assets are discovered.
    # For child themes extending default, filter out "default" since the caller
    # adds it as a fallback separately.
    if (active_theme or "default") == "default":
        return chain
    return [t for t in chain if t != "default"]


def read_theme_extends(theme_name: str, site: SiteLike) -> str | None:
    """
    Read theme.toml for 'extends' from site, installed, or bundled theme path.

    Args:
        theme_name: Theme name to look up
        site: Site instance

    Returns:
        Parent theme name if extends is set, None otherwise

    """
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)

    # Site theme manifest
    site_manifest = site.root_path / "themes" / theme_name / "theme.toml"
    if site_manifest.exists():
        try:
            with open(site_manifest, "rb") as f:
                data = tomllib.load(f)
            extends = data.get("extends")
            return str(extends) if extends else None
        except Exception as e:
            logger.debug(
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(site_manifest),
                error=str(e),
            )

    # Installed theme manifest
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            manifest_path = pkg.resolve_resource_path("theme.toml")
            if manifest_path and manifest_path.exists():
                try:
                    with open(manifest_path, "rb") as f:
                        data = tomllib.load(f)
                    extends = data.get("extends")
                    return str(extends) if extends else None
                except Exception as e:
                    logger.debug(
                        "theme_manifest_read_failed",
                        theme=theme_name,
                        path=str(manifest_path),
                        error=str(e),
                    )
    except Exception as e:
        logger.debug(
            "theme_package_resolve_failed",
            theme=theme_name,
            error=str(e),
        )

    # Bundled theme manifest
    from bengal.themes.utils import THEMES_ROOT

    bundled_manifest = THEMES_ROOT / theme_name / "theme.toml"
    if bundled_manifest.exists():
        try:
            with open(bundled_manifest, "rb") as f:
                data = tomllib.load(f)
            extends = data.get("extends")
            return str(extends) if extends else None
        except Exception as e:
            logger.debug(
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(bundled_manifest),
                error=str(e),
            )

    return None
