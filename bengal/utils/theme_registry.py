"""
Installed theme discovery and utilities.

Discovers uv/pip-installed themes via entry points (group: "bengal.themes").

Conventions:
- Package name: prefer "bengal-theme-<slug>"; accept "<slug>-bengal-theme".
- Entry point name: slug (e.g., "acme") → value: import path (e.g., "bengal_themes.acme").
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
        try:
            traversable = resources.files(self.package) / "templates"
            return traversable.is_dir()
        except Exception:
            # Fallback for packages in sys.path but not installed (e.g., tests)
            try:
                import importlib

                module = importlib.import_module(self.package)
                if hasattr(module, "__file__") and module.__file__:
                    pkg_dir = Path(module.__file__).parent
                    return (pkg_dir / "templates").is_dir()
            except Exception:
                pass
            return False

    def assets_exists(self) -> bool:
        try:
            traversable = resources.files(self.package) / "assets"
            return traversable.is_dir()
        except Exception:
            # Fallback for packages in sys.path but not installed (e.g., tests)
            try:
                import importlib

                module = importlib.import_module(self.package)
                if hasattr(module, "__file__") and module.__file__:
                    pkg_dir = Path(module.__file__).parent
                    return (pkg_dir / "assets").is_dir()
            except Exception:
                pass
            return False

    def manifest_exists(self) -> bool:
        try:
            traversable = resources.files(self.package) / "theme.toml"
            return traversable.is_file()
        except Exception:
            # Fallback for packages in sys.path but not installed (e.g., tests)
            try:
                import importlib

                module = importlib.import_module(self.package)
                if hasattr(module, "__file__") and module.__file__:
                    pkg_dir = Path(module.__file__).parent
                    return (pkg_dir / "theme.toml").is_file()
            except Exception:
                pass
            return False

    def jinja_loader(self) -> PackageLoader:
        return PackageLoader(self.package, "templates")

    def resolve_resource_path(self, relative: str) -> Path | None:
        try:
            target = resources.files(self.package)
            traversable = target.joinpath(relative)
            if not traversable.exists():
                return None

            # Try to get a persistent filesystem path
            # For properly installed packages, this works
            try:
                # Check if it's already a real Path (not in a zip)
                if hasattr(traversable, "__fspath__"):
                    return Path(traversable)
            except Exception:
                pass

            # For packages in zip files, we need as_file, but the path is temporary
            # Store a persistent copy or just return the temp path
            # Note: Caller should handle this carefully
            with resources.as_file(traversable) as path:
                # Make a copy of the path (the actual Path object, not the file)
                return Path(path)
        except Exception:
            # Fallback for packages in sys.path but not installed (e.g., tests)
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
