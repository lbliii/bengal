from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import toml

from bengal.utils.logger import get_logger
from bengal.utils.theme_registry import get_theme_package

logger = get_logger(__name__)


def _read_theme_extends(site_root: Path, theme_name: str) -> str | None:
    """Read theme.toml for 'extends' from site, installed, or bundled theme path."""
    # Site theme manifest
    site_manifest = site_root / "themes" / theme_name / "theme.toml"
    if site_manifest.exists():
        try:
            data = toml.load(str(site_manifest))
            return data.get("extends")
        except Exception:
            pass

    # Installed theme manifest
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            manifest_path = pkg.resolve_resource_path("theme.toml")
            if manifest_path and manifest_path.exists():
                data = toml.load(str(manifest_path))
                return data.get("extends")
    except Exception:
        pass

    # Bundled theme manifest
    bundled_manifest = Path(__file__).parent.parent / "themes" / theme_name / "theme.toml"
    if bundled_manifest.exists():
        try:
            data = toml.load(str(bundled_manifest))
            return data.get("extends")
        except Exception:
            pass

    return None


def resolve_theme_chain(site_root: Path, active_theme: str | None) -> list[str]:
    """
    Resolve theme inheritance chain starting from the active theme.

    Order: child first → parent → ... (does not duplicate 'default').
    """
    chain: list[str] = []
    visited: set[str] = set()
    current = active_theme or "default"
    depth = 0
    MAX_DEPTH = 5

    while current and current not in visited and depth < MAX_DEPTH:
        visited.add(current)
        chain.append(current)
        extends = _read_theme_extends(site_root, current)
        if not extends or extends == current:
            break
        current = extends
        depth += 1

    # Do not include 'default' twice; caller may add fallback separately
    return [t for t in chain if t != "default"]


def iter_theme_asset_dirs(site_root: Path, theme_chain: Iterable[str]) -> list[Path]:
    """
    Return list of theme asset directories from parents to child (low → high priority).
    Site assets can still override these.
    """
    dirs: list[Path] = []

    for theme_name in theme_chain:
        # Site theme assets
        site_dir = site_root / "themes" / theme_name / "assets"
        if site_dir.exists():
            dirs.append(site_dir)
            continue

        # Installed theme assets
        try:
            pkg = get_theme_package(theme_name)
            if pkg:
                resolved = pkg.resolve_resource_path("assets")
                if resolved and resolved.exists():
                    dirs.append(resolved)
                    continue
        except Exception:
            pass

        # Bundled theme assets
        try:
            bundled_dir = Path(__file__).parent.parent / "themes" / theme_name / "assets"
            if bundled_dir.exists():
                dirs.append(bundled_dir)
        except Exception:
            pass

    return dirs
