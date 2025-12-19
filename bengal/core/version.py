"""
Version model for versioned documentation support.

This module provides the Version dataclass representing a documentation version,
and VersionConfig for managing multiple versions across the site.

Key Concepts:
    - Version: Single documentation version (e.g., v3, v2, v1)
    - VersionConfig: Site-wide versioning configuration
    - Aliases: Named references to versions (latest, stable, lts)
    - Shared content: Content included in all versions (_shared/)

Design:
    Versioning is folder-based with smart features:
    - Main content (e.g., docs/) is the "latest" version
    - Older versions live in _versions/<version>/
    - Shared content in _shared/ is included in all versions
    - Multiple aliases (latest, stable, lts) point to specific versions

URL Structure:
    - Latest version: /docs/guide/ (no version prefix)
    - Older versions: /docs/v2/guide/ (version prefix)
    - Aliases: /docs/latest/guide/ → redirects to /docs/guide/

Related:
    - plan/drafted/rfc-versioned-documentation.md: Design rationale
    - bengal/config/loader.py: Config loading
    - bengal/discovery/content_discovery.py: Version discovery

Example:
    >>> from bengal.core.version import Version, VersionConfig
    >>>
    >>> v3 = Version(id="v3", source="docs", label="3.0", latest=True)
    >>> v2 = Version(id="v2", source="_versions/v2/docs", label="2.0")
    >>>
    >>> config = VersionConfig(
    ...     enabled=True,
    ...     versions=[v3, v2],
    ...     aliases={"latest": "v3", "stable": "v3"},
    ... )
    >>> config.get_version("v2")
    Version(id='v2', ...)
    >>> config.latest_version
    Version(id='v3', ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VersionBanner:
    """
    Banner configuration for version pages.

    Displays a notice on pages for older/deprecated versions.

    Attributes:
        type: Banner type ('info', 'warning', 'danger')
        message: Custom message to display
        show_latest_link: Whether to show link to latest version
    """

    type: str = "warning"
    message: str = "You're viewing docs for an older version."
    show_latest_link: bool = True


@dataclass
class Version:
    """
    Represents a single documentation version.

    Attributes:
        id: Version identifier (e.g., 'v3', 'v2.1', '1.0')
        source: Source directory relative to content root
        label: Display label (e.g., '3.0', '2.0 LTS')
        latest: Whether this is the latest/default version
        banner: Optional banner configuration for this version
        deprecated: Whether this version is deprecated
        release_date: Optional release date for this version
        end_of_life: Optional end-of-life date

    Design Notes:
        - id is used in URLs and config references
        - source is the content directory path (relative to content root)
        - label is for display in version selector
        - latest determines URL structure (no prefix for latest)
    """

    id: str
    source: str = ""
    label: str = ""
    latest: bool = False
    banner: VersionBanner | None = None
    deprecated: bool = False
    release_date: str | None = None
    end_of_life: str | None = None

    def __post_init__(self) -> None:
        """Initialize defaults."""
        # Default label to id if not provided
        if not self.label:
            self.label = self.id

        # Default source to id if not provided (e.g., v2 → _versions/v2)
        if not self.source:
            if self.latest:
                # Latest version uses main content directory
                self.source = ""
            else:
                # Older versions use _versions/<id>
                self.source = f"_versions/{self.id}"

    @property
    def url_prefix(self) -> str:
        """
        Get URL prefix for this version.

        Latest version has no prefix, older versions have version prefix.

        Returns:
            URL prefix (empty string for latest, '/v2' for v2, etc.)
        """
        if self.latest:
            return ""
        return f"/{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for template context.

        Returns:
            Dictionary with version data for templates
        """
        return {
            "id": self.id,
            "label": self.label,
            "latest": self.latest,
            "deprecated": self.deprecated,
            "url_prefix": self.url_prefix,
            "release_date": self.release_date,
            "end_of_life": self.end_of_life,
        }


@dataclass
class VersionConfig:
    """
    Site-wide versioning configuration.

    Manages multiple documentation versions, aliases, and shared content.

    Attributes:
        enabled: Whether versioning is enabled
        versions: List of Version objects
        aliases: Named aliases to version ids (e.g., {'latest': 'v3'})
        sections: Content sections that are versioned (e.g., ['docs'])
        shared: Paths to shared content included in all versions
        url_config: URL generation configuration

    Example:
        >>> config = VersionConfig(
        ...     enabled=True,
        ...     versions=[
        ...         Version(id="v3", latest=True),
        ...         Version(id="v2"),
        ...     ],
        ...     aliases={"latest": "v3", "stable": "v3", "lts": "v2"},
        ... )
        >>> config.resolve_alias("latest")
        'v3'
    """

    enabled: bool = False
    versions: list[Version] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    sections: list[str] = field(default_factory=lambda: ["docs"])
    shared: list[str] = field(default_factory=lambda: ["_shared"])
    url_config: dict[str, Any] = field(default_factory=dict)
    seo_config: dict[str, Any] = field(default_factory=dict)

    # Computed caches
    _version_map: dict[str, Version] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Build lookup caches."""
        self._version_map = {v.id: v for v in self.versions}

        # Ensure at least one version is marked as latest
        if self.versions and not any(v.latest for v in self.versions):
            self.versions[0].latest = True
            self._version_map[self.versions[0].id] = self.versions[0]

        # Auto-add 'latest' alias if not present
        if "latest" not in self.aliases:
            latest = self.latest_version
            if latest:
                self.aliases["latest"] = latest.id

    @property
    def latest_version(self) -> Version | None:
        """
        Get the latest/default version.

        Returns:
            Version marked as latest, or first version, or None
        """
        for v in self.versions:
            if v.latest:
                return v
        return self.versions[0] if self.versions else None

    def get_version(self, version_id: str) -> Version | None:
        """
        Get version by id.

        Args:
            version_id: Version id to look up

        Returns:
            Version object or None if not found
        """
        return self._version_map.get(version_id)

    def resolve_alias(self, alias: str) -> str | None:
        """
        Resolve version alias to version id.

        Args:
            alias: Alias name (e.g., 'latest', 'stable')

        Returns:
            Version id or None if alias not found
        """
        return self.aliases.get(alias)

    def get_version_or_alias(self, id_or_alias: str) -> Version | None:
        """
        Get version by id or alias.

        First tries to find by id, then resolves alias.

        Args:
            id_or_alias: Version id or alias name

        Returns:
            Version object or None
        """
        # Try direct lookup first
        version = self.get_version(id_or_alias)
        if version:
            return version

        # Try alias resolution
        resolved_id = self.resolve_alias(id_or_alias)
        if resolved_id:
            return self.get_version(resolved_id)

        return None

    def is_versioned_section(self, section_path: str) -> bool:
        """
        Check if a section path is versioned.

        Args:
            section_path: Section path (e.g., 'docs', 'blog')

        Returns:
            True if section is versioned
        """
        # Normalize path
        section_name = Path(section_path).parts[0] if section_path else ""
        return section_name in self.sections

    def get_version_for_path(self, content_path: Path | str) -> Version | None:
        """
        Determine which version a content path belongs to.

        Args:
            content_path: Path to content file

        Returns:
            Version object or None if not in versioned content
        """
        path_str = str(content_path)

        # Check _versions/<id>/
        if "_versions/" in path_str:
            parts = path_str.split("_versions/")
            if len(parts) > 1:
                version_id = parts[1].split("/")[0]
                return self.get_version(version_id)

        # Check if in versioned section (latest version)
        for section in self.sections:
            if path_str.startswith(section) or f"/{section}" in path_str:
                return self.latest_version

        return None

    def to_template_context(self) -> dict[str, Any]:
        """
        Convert to template context dictionary.

        Returns:
            Dictionary with versioning data for templates
        """
        return {
            "enabled": self.enabled,
            "versions": [v.to_dict() for v in self.versions],
            "aliases": self.aliases,
            "sections": self.sections,
            "latest": self.latest_version.to_dict() if self.latest_version else None,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> VersionConfig:
        """
        Create VersionConfig from site configuration.

        Args:
            config: Site configuration dictionary

        Returns:
            VersionConfig instance

        Example:
            >>> config = {
            ...     "versioning": {
            ...         "enabled": True,
            ...         "versions": ["v3", "v2", "v1"],
            ...     }
            ... }
            >>> vc = VersionConfig.from_config(config)
        """
        versioning = config.get("versioning", {})

        if not versioning:
            return cls(enabled=False)

        enabled = versioning.get("enabled", False)
        if not enabled:
            return cls(enabled=False)

        # Parse versions
        versions_raw = versioning.get("versions", [])
        versions: list[Version] = []

        for i, v in enumerate(versions_raw):
            if isinstance(v, str):
                # Simple format: just version id
                versions.append(Version(id=v, latest=(i == 0)))
            elif isinstance(v, dict):
                # Full format: version config dict
                banner_config = v.get("banner")
                banner = None
                if banner_config:
                    if isinstance(banner_config, dict):
                        banner = VersionBanner(
                            type=banner_config.get("type", "warning"),
                            message=banner_config.get(
                                "message", "You're viewing docs for an older version."
                            ),
                            show_latest_link=banner_config.get("show_latest_link", True),
                        )
                    elif isinstance(banner_config, str):
                        banner = VersionBanner(message=banner_config)

                versions.append(
                    Version(
                        id=v.get("id", f"v{i + 1}"),
                        source=v.get("source", ""),
                        label=v.get("label", ""),
                        latest=v.get("latest", i == 0),
                        banner=banner,
                        deprecated=v.get("deprecated", False),
                        release_date=v.get("release_date"),
                        end_of_life=v.get("end_of_life"),
                    )
                )

        return cls(
            enabled=enabled,
            versions=versions,
            aliases=versioning.get("aliases", {}),
            sections=versioning.get("sections", ["docs"]),
            shared=versioning.get("shared", ["_shared"]),
            url_config=versioning.get("urls", {}),
            seo_config=versioning.get("seo", {}),
        )
