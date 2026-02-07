"""
Theme service - pure functions for theme resolution.

Pure functions that resolve theme assets and templates from
root_path + theme_name. No hidden state, thread-safe.

Usage:
    >>> from bengal.services.theme import get_theme_assets_dir
    >>> assets = get_theme_assets_dir(root_path, "default")
"""

from __future__ import annotations

from pathlib import Path

from bengal.services.utils import get_bengal_dir


def get_theme_assets_dir(root_path: Path, theme_name: str | None) -> Path | None:
    """
    Get the assets directory for a theme.

    Pure function: no hidden state.

    Search order:
    1. Site's themes directory (site/themes/{theme}/assets)
    2. Bengal's bundled themes (bengal/themes/{theme}/assets)

    Args:
        root_path: Site root path
        theme_name: Theme name (or None)

    Returns:
        Path to theme assets directory, or None if not found
    """
    if not theme_name:
        return None

    # Check site's themes directory first
    site_theme_dir = root_path / "themes" / theme_name / "assets"
    if site_theme_dir.exists():
        return site_theme_dir

    # Check Bengal's bundled themes
    bundled_theme_dir = get_bengal_dir() / "themes" / theme_name / "assets"
    if bundled_theme_dir.exists():
        return bundled_theme_dir

    return None


def get_theme_assets_chain(root_path: Path, theme_name: str | None) -> list[Path]:
    """
    Get theme asset directories from inheritance chain.

    Pure function: no hidden state.

    Returns asset directories in order from parent themes to child theme
    (low → high priority). Site assets override all theme assets.

    Args:
        root_path: Site root path
        theme_name: Theme name (or None)

    Returns:
        List of Path objects for theme asset directories
    """
    if not theme_name:
        return []

    from bengal.core.theme import iter_theme_asset_dirs, resolve_theme_chain

    chain = resolve_theme_chain(root_path, theme_name)
    dirs: list[Path] = []

    for name in reversed(chain):
        dirs.extend(iter_theme_asset_dirs(root_path, [name]))

    return dirs


def get_theme_templates_chain(root_path: Path, theme_name: str | None) -> list[Path]:
    """
    Get theme template directories from inheritance chain.

    Pure function: no hidden state.

    Args:
        root_path: Site root path
        theme_name: Theme name (or None)

    Returns:
        List of Path objects for theme template directories
    """
    if not theme_name:
        return []

    from bengal.core.theme import resolve_theme_chain

    chain = resolve_theme_chain(root_path, theme_name)
    dirs: list[Path] = []
    bengal_dir = get_bengal_dir()

    for name in reversed(chain):
        # Check site's themes directory first
        site_dir = root_path / "themes" / name / "templates"
        if site_dir.exists():
            dirs.append(site_dir)
            continue

        # Check Bengal's bundled themes
        bundled_dir = bengal_dir / "themes" / name / "templates"
        if bundled_dir.exists():
            dirs.append(bundled_dir)

    return dirs
