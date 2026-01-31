"""
Theme service - pure functions for theme resolution.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)

Replaces ThemeIntegrationMixin with pure functions that operate on
ConfigSnapshot instead of mutable Site.

Key Principles:
- Pure functions: no hidden state
- Explicit inputs: root_path + theme_name
- Cacheable results: same inputs → same outputs
- Thread-safe: no shared mutable state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.services.utils import get_bengal_dir

if TYPE_CHECKING:
    from bengal.config.snapshot import ConfigSnapshot
    from bengal.snapshots.types import SiteSnapshot


@dataclass(frozen=True, slots=True)
class ThemeService:
    """
    Cached theme resolution service.

    Provides theme asset and template resolution with caching.
    Operates on ConfigSnapshot for thread-safety.

    Usage:
        >>> service = ThemeService(root_path, config_snapshot)
        >>> assets_dir = service.get_assets_dir()
        >>> asset_chain = service.get_assets_chain()
    """

    root_path: Path
    theme_name: str | None

    # Cached results
    _assets_chain: tuple[Path, ...] = field(default=(), repr=False)
    _templates_chain: tuple[Path, ...] = field(default=(), repr=False)

    @classmethod
    def from_config(cls, root_path: Path, config: ConfigSnapshot) -> ThemeService:
        """
        Create service from ConfigSnapshot.

        Args:
            root_path: Site root path
            config: Frozen config snapshot

        Returns:
            ThemeService instance
        """
        theme_name = config.theme.name if config.theme else None
        return cls(root_path=root_path, theme_name=theme_name)

    @classmethod
    def from_snapshot(cls, snapshot: SiteSnapshot) -> ThemeService:
        """
        Create service from SiteSnapshot.

        Args:
            snapshot: Site snapshot

        Returns:
            ThemeService instance
        """
        theme_name = None
        if snapshot.config_snapshot and snapshot.config_snapshot.theme:
            theme_name = snapshot.config_snapshot.theme.name
        return cls(root_path=snapshot.root_path, theme_name=theme_name)

    def get_assets_dir(self) -> Path | None:
        """
        Get the assets directory for the current theme.

        Returns:
            Path to theme assets directory, or None if not found
        """
        return get_theme_assets_dir(self.root_path, self.theme_name)

    def get_assets_chain(self) -> list[Path]:
        """
        Get theme asset directories in inheritance order.

        Returns:
            List of Paths, parent themes first (lowest priority),
            child theme last (highest priority)
        """
        return get_theme_assets_chain(self.root_path, self.theme_name)

    def get_templates_chain(self) -> list[Path]:
        """
        Get theme template directories in inheritance order.

        Returns:
            List of Paths, parent themes first (lowest priority),
            child theme last (highest priority)
        """
        return get_theme_templates_chain(self.root_path, self.theme_name)


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
