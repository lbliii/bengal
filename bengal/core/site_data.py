"""
Site Data - Immutable site configuration and paths.

Provides SiteData frozen dataclass for immutable configuration storage.
Created once from config, never modified. Enables caching and thread-safe
access without locks.

Public API:
    SiteData: Immutable site configuration container

Key Concepts:
    Immutability: All configuration is frozen after construction.
        MappingProxyType wraps config dict for read-only access.

    Path Computation: All paths are computed at construction time
        and stored as resolved absolute paths.

    Thread Safety: Fully thread-safe for reads without locks.
        Safe to share across parallel rendering threads.

Usage:
    data = SiteData.from_config(root_path, config)
    print(data.title)  # Access config values
    print(data.output_dir)  # Access computed paths

Related Packages:
    bengal.core.site.core: Site dataclass using SiteData
    bengal.config.loader: Config loading that populates SiteData

See Also:
    plan/drafted/rfc-site-responsibility-separation.md
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from bengal.core.version import VersionConfig


@dataclass(frozen=True)
class SiteData:
    """
    Immutable site configuration and paths.

    Created once from config, never modified. Enables caching and
    thread-safe access without locks.

    Immutability Guarantees:
        - frozen=True prevents attribute assignment
        - MappingProxyType wraps config dict for read-only access
        - All Path attributes are computed at construction time

    Thread Safety:
        - Fully thread-safe for reads (immutable)
        - No locks required
        - Safe to share across parallel rendering threads

    Attributes:
        root_path: Site root directory (absolute path)
        output_dir: Output directory for built site (absolute path)
        config: Immutable view of configuration dictionary
        theme_name: Name of the active theme
        version_config: Versioning configuration
        content_dir: Content directory path
        assets_dir: Assets directory path
        data_dir: Data directory path
        cache_dir: Cache directory path (.bengal)
    """

    root_path: Path
    output_dir: Path
    config: MappingProxyType[str, Any]
    theme_name: str
    version_config: VersionConfig

    # Computed paths
    content_dir: Path
    assets_dir: Path
    data_dir: Path
    cache_dir: Path

    @classmethod
    def from_config(cls, root_path: Path, config: dict[str, Any]) -> SiteData:
        """
        Create SiteData from config dict.

        Args:
            root_path: Site root directory (will be resolved to absolute)
            config: Configuration dictionary (will be wrapped as immutable)

        Returns:
            Frozen SiteData instance

        Example:
            data = SiteData.from_config(Path("/site"), {"title": "My Site"})
        """
        root = root_path.resolve()

        # Extract theme name from nested config
        theme_section = config.get("theme", {})
        if isinstance(theme_section, dict):
            theme_name = theme_section.get("name", "default")
        else:
            theme_name = str(theme_section) if theme_section else "default"

        # Resolve output directory
        output_dir_str = config.get("output_dir", "public")
        output_dir = Path(output_dir_str)
        if not output_dir.is_absolute():
            output_dir = root / output_dir

        # Resolve content directory
        content_dir_str = config.get("content_dir", "content")
        content_dir = Path(content_dir_str)
        if not content_dir.is_absolute():
            content_dir = root / content_dir

        return cls(
            root_path=root,
            output_dir=output_dir,
            config=MappingProxyType(config),
            theme_name=theme_name,
            version_config=VersionConfig.from_config(config),
            content_dir=content_dir,
            assets_dir=root / "assets",
            data_dir=root / "data",
            cache_dir=root / ".bengal",
        )

    @property
    def baseurl(self) -> str:
        """Get baseurl from config."""
        return str(self.config.get("baseurl", ""))

    @property
    def title(self) -> str:
        """Get site title from config."""
        return str(self.config.get("title", ""))

    @property
    def author(self) -> str | None:
        """Get site author from config."""
        author = self.config.get("author")
        return str(author) if author else None

    @property
    def description(self) -> str | None:
        """Get site description from config."""
        desc = self.config.get("description")
        return str(desc) if desc else None

    @property
    def language(self) -> str:
        """Get default language from config."""
        return str(self.config.get("language", "en"))

    def get_config_section(self, section: str) -> Mapping[str, Any]:
        """
        Get a config section with type safety.

        Args:
            section: Config section name (e.g., "build", "assets", "i18n")

        Returns:
            Config section as read-only mapping (empty dict if missing)

        Example:
            build_cfg = data.get_config_section("build")
            if build_cfg.get("strict_mode"):
                # strict mode handling
        """
        value = self.config.get(section)
        if isinstance(value, dict):
            return MappingProxyType(value)
        return MappingProxyType({})

    def __repr__(self) -> str:
        return f"SiteData(root={self.root_path.name!r}, theme={self.theme_name!r})"
