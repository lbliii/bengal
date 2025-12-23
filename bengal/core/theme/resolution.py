"""
Theme resolution and inheritance chain building.

Resolves theme inheritance chains by reading theme.toml files and following
extends relationships. Supports site themes, installed themes, and bundled themes.
Builds complete inheritance chains for template and asset discovery.

Key Concepts:
    - Theme inheritance: Child themes extend parent themes
    - Resolution order: Site themes → installed themes → bundled themes
    - Chain building: Recursive resolution of extends relationships
    - Template discovery: Uses inheritance chain for template lookup

Related Modules:
    - bengal.core.theme.registry: Installed theme discovery
    - bengal.rendering.template_engine: Template engine using inheritance chains
    - bengal.core.theme.config: Theme configuration object

See Also:
    - bengal/core/theme/resolution.py:resolve_theme_chain() for chain resolution
    - plan/active/rfc-theme-inheritance.md: Theme inheritance design
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from bengal.core.diagnostics import emit
from bengal.core.theme.registry import get_theme_package


def _read_theme_extends(site_root: Path, theme_name: str) -> str | None:
    """Read theme.toml for 'extends' from site, installed, or bundled theme path."""
    # Site theme manifest
    site_manifest = site_root / "themes" / theme_name / "theme.toml"
    if site_manifest.exists():
        try:
            with open(site_manifest, "rb") as f:
                data = tomllib.load(f)
            if isinstance(data, dict):
                extends = data.get("extends")
                return cast(str | None, extends) if extends is not None else None
            return None
        except Exception as e:
            emit(
                None,
                "debug",
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(site_manifest),
                error=str(e),
                error_type=type(e).__name__,
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
                    extends_val = data.get("extends")
                    return str(extends_val) if extends_val else None
                except Exception as e:
                    emit(
                        None,
                        "debug",
                        "theme_manifest_read_failed",
                        theme=theme_name,
                        path=str(manifest_path),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
    except Exception as e:
        emit(
            None,
            "debug",
            "theme_package_resolve_failed",
            theme=theme_name,
            error=str(e),
            error_type=type(e).__name__,
        )

    # Bundled theme manifest
    bundled_manifest = Path(__file__).parent.parent.parent / "themes" / theme_name / "theme.toml"
    if bundled_manifest.exists():
        try:
            with open(bundled_manifest, "rb") as f:
                data = tomllib.load(f)
            extends_val = data.get("extends")
            return str(extends_val) if extends_val else None
        except Exception as e:
            emit(
                None,
                "debug",
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(bundled_manifest),
                error=str(e),
                error_type=type(e).__name__,
            )

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


def resolve_theme_templates_path(
    theme_name: str,
    site_root: Path,
    bundled_themes_root: Path | None = None,
) -> Path | None:
    """
    Resolve the templates directory path for a theme.

    Checks site themes, installed themes, and bundled themes in order.
    This is the canonical function for finding theme template directories,
    used by all template engines (Jinja2, Mako, etc.) for cross-theme extends.

    Args:
        theme_name: Theme name to look up (e.g., "default", "docs")
        site_root: Site root directory
        bundled_themes_root: Optional root for bundled themes. If None,
            defaults to bengal/themes/ relative to this module.

    Returns:
        Path to theme's templates directory, or None if not found

    Example:
        >>> path = resolve_theme_templates_path("default", site.root_path)
        >>> path
        PosixPath('/path/to/bengal/themes/default/templates')

    Used by:
        - bengal.rendering.engines.jinja: PrefixLoader for cross-theme extends
        - bengal.rendering.engines.mako: (future) similar functionality
        - Any custom engine implementing TemplateEngineProtocol
    """
    # Site-level theme directory
    site_theme_templates = site_root / "themes" / theme_name / "templates"
    if site_theme_templates.exists():
        return site_theme_templates

    # Installed theme directory (via entry point)
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            resolved = pkg.resolve_resource_path("templates")
            if resolved and resolved.exists():
                return resolved
    except Exception as e:
        emit(
            None,
            "debug",
            "theme_templates_resolution_installed_failed",
            theme=theme_name,
            error=str(e),
        )

    # Bundled theme directory
    if bundled_themes_root is None:
        bundled_themes_root = Path(__file__).parent.parent.parent / "themes"
    bundled_theme_templates = bundled_themes_root / theme_name / "templates"
    if bundled_theme_templates.exists():
        return bundled_theme_templates

    return None


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
        except Exception as e:
            emit(
                None,
                "debug",
                "installed_theme_assets_resolution_failed",
                theme=theme_name,
                error=str(e),
            )

        # Bundled theme assets
        try:
            bundled_dir = Path(__file__).parent.parent.parent / "themes" / theme_name / "assets"
            if bundled_dir.exists():
                dirs.append(bundled_dir)
        except Exception as e:
            emit(
                None,
                "debug",
                "bundled_theme_assets_resolution_failed",
                theme=theme_name,
                error=str(e),
            )

    return dirs
