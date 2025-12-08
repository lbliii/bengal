"""
Installed theme discovery and utilities.

Discovers uv/pip-installed themes via entry points (group: "bengal.themes").
Provides theme package lookup and resource access for installed themes.

Key Concepts:
    - Entry points: Python package entry points for theme discovery
    - Package naming: Prefer "bengal-theme-<slug>" format
    - Resource access: PackageLoader for template/asset access
    - Theme packages: ThemePackage dataclass for theme metadata

Conventions:
    - Package name: prefer "bengal-theme-<slug>"; accept "<slug>-bengal-theme".
    - Entry point name: slug (e.g., "acme") → value: import path (e.g., "bengal_themes.acme").

Related Modules:
    - bengal.utils.theme_resolution: Theme inheritance chain resolution
    - bengal.rendering.template_engine: Template engine using theme packages
    - bengal.core.theme: Theme configuration object

See Also:
    - bengal/utils/theme_registry.py:get_theme_package() for theme lookup
    - bengal/utils/theme_registry.py:ThemePackage for theme representation
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import metadata, resources
from pathlib import Path

from jinja2 import PackageLoader

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ThemePackage:
    slug: str
    package: str  # importable package providing the theme resources (e.g., "bengal_themes.acme")
    distribution: str | None  # distribution/project name on PyPI (best effort)
    version: str | None

    def templates_exists(self) -> bool:
        # Fallback: direct module import (works for test packages in sys.path)
        # Try this FIRST because it's more reliable for non-installed packages
        try:
            import importlib

            module = importlib.import_module(self.package)
            if hasattr(module, "__file__") and module.__file__:
                pkg_dir = Path(module.__file__).parent
                templates_dir = pkg_dir / "templates"
                if templates_dir.is_dir():
                    return True
        except Exception as e:
            logger.debug(
                "theme_templates_dir_check_failed",
                package=self.package,
                method="importlib_import",
                error=str(e),
                error_type=type(e).__name__,
            )
            pass

        # Try importlib.resources (for properly installed packages)
        try:
            traversable = resources.files(self.package) / "templates"
            # Try calling is_dir() directly - if it exists, it should work
            return bool(traversable.is_dir())
        except Exception as e:
            logger.debug(
                "theme_templates_dir_check_failed",
                package=self.package,
                method="importlib_resources",
                error=str(e),
                error_type=type(e).__name__,
            )
            pass

        return False

    def assets_exists(self) -> bool:
        # Fallback: direct module import (works for test packages in sys.path)
        # Try this FIRST because it's more reliable for non-installed packages
        try:
            import importlib

            module = importlib.import_module(self.package)
            if hasattr(module, "__file__") and module.__file__:
                pkg_dir = Path(module.__file__).parent
                assets_dir = pkg_dir / "assets"
                if assets_dir.is_dir():
                    return True
        except Exception as e:
            logger.debug(
                "theme_assets_dir_check_failed",
                package=self.package,
                method="importlib_import",
                error=str(e),
                error_type=type(e).__name__,
            )
            pass

        # Try importlib.resources (for properly installed packages)
        try:
            traversable = resources.files(self.package) / "assets"
            # Try calling is_dir() directly - if it exists, it should work
            return bool(traversable.is_dir())
        except Exception:
            pass

        return False

    def manifest_exists(self) -> bool:
        # Fallback: direct module import (works for test packages in sys.path)
        # Try this FIRST because it's more reliable for non-installed packages
        try:
            import importlib

            module = importlib.import_module(self.package)
            if hasattr(module, "__file__") and module.__file__:
                pkg_dir = Path(module.__file__).parent
                manifest_file = pkg_dir / "theme.toml"
                if manifest_file.is_file():
                    return True
        except Exception:
            pass

        # Try importlib.resources (for properly installed packages)
        try:
            traversable = resources.files(self.package) / "theme.toml"
            # Try calling is_file() directly - if it exists, it should work
            return bool(traversable.is_file())
        except Exception:
            pass

        return False

    def jinja_loader(self) -> PackageLoader:
        return PackageLoader(self.package, "templates")

    def resolve_resource_path(self, relative: str) -> Path | None:
        # Fallback: direct module import (works for test packages in sys.path)
        # Try this FIRST because it's more reliable for non-installed packages
        try:
            import importlib

            module = importlib.import_module(self.package)
            if hasattr(module, "__file__") and module.__file__:
                pkg_dir = Path(module.__file__).parent
                full_path = pkg_dir / relative
                if full_path.exists():
                    return full_path
        except Exception:
            pass

        # Try importlib.resources (for properly installed packages)
        try:
            target = resources.files(self.package)
            traversable = target.joinpath(relative)
            if traversable.exists():
                # Try to get a persistent filesystem path
                try:
                    # Check if it's already a real Path (not in a zip)
                    if hasattr(traversable, "__fspath__"):
                        return Path(traversable)
                except Exception:
                    pass

                # For packages in zip files, we need as_file
                try:
                    with resources.as_file(traversable) as path:
                        return Path(path)
                except Exception:
                    pass
        except Exception:
            pass

        logger.debug("theme_resource_resolve_failed", package=self.package, rel=relative)
        return None


@lru_cache(maxsize=1)
def get_installed_themes() -> dict[str, ThemePackage]:
    """
    Discover installed themes via entry points.

    Returns:
        Mapping of slug -> ThemePackage
    """
    themes: dict[str, ThemePackage] = {}
    try:
        eps = metadata.entry_points(group="bengal.themes")
    except Exception as e:
        logger.debug("entry_point_discovery_failed", error=str(e))
        eps = []

    for ep in eps:
        slug = ep.name
        package = ep.value  # import path of theme package/module

        dist_name: str | None = None
        version: str | None = None
        try:
            # Best-effort: find the owning distribution
            distributions = metadata.packages_distributions()
            # ep.module contains top-level package; use first segment
            top_pkg = package.split(".")[0]
            owning = (distributions.get(top_pkg) or [None])[0]
            if owning:
                dist_name = owning
                try:
                    version = metadata.version(dist_name)
                except Exception:
                    version = None
        except Exception:
            pass

        themes[slug] = ThemePackage(
            slug=slug, package=package, distribution=dist_name, version=version
        )

    logger.debug("installed_themes_discovered", count=len(themes), slugs=list(themes.keys()))
    return themes


def get_theme_package(slug: str) -> ThemePackage | None:
    return get_installed_themes().get(slug)


def clear_theme_cache() -> None:
    get_installed_themes.cache_clear()
