"""
Version models for versioned documentation support.

Provides dataclasses for managing multiple documentation versions, supporting
both folder-based and Git-based versioning modes.

Public API:
    Version: Single documentation version (id, label, latest flag, banner)
    VersionConfig: Site-wide versioning configuration and lookup methods
    VersionBanner: Banner configuration for older version pages
    GitVersionConfig: Git-specific versioning configuration
    GitBranchPattern: Pattern matching for Git branches/tags

Versioning Modes:
    Folder Mode (default):
        Main content (docs/) is the "latest" version. Older versions live
        in _versions/<version>/. Shared content in _shared/ is included
        in all versions.

    Git Mode:
        Versions discovered from Git branches/tags via pattern matching.
        No folder duplication—builds directly from Git history. Supports
        parallel builds for all versions.

URL Structure:
    Latest version: /docs/guide/ (no version prefix)
    Older versions: /docs/v2/guide/ (version prefix after section)
    Aliases: /docs/latest/guide/ → redirects to /docs/guide/

Example:
    # Folder mode configuration
    config = VersionConfig(
        enabled=True,
        versions=[
            Version(id="v3", latest=True, label="3.0"),
            Version(id="v2", label="2.0"),
        ],
        aliases={"latest": "v3", "stable": "v3"},
    )

    # Git mode configuration
    config = VersionConfig(
        enabled=True,
        mode="git",
        git_config=GitVersionConfig(
            branches=[
                GitBranchPattern(name="main", latest=True),
                GitBranchPattern(pattern="release/*", strip_prefix="release/"),
            ],
        ),
    )

Related Packages:
    bengal.config.loader: Configuration loading from bengal.toml
    bengal.discovery.content_discovery: Version discovery during content scan
    bengal.discovery.git_version_adapter: Git branch/tag discovery
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
class GitBranchPattern:
    """
    Pattern for matching Git branches/tags to versions.

    Attributes:
        pattern: Glob pattern to match (e.g., "release/*", "v*")
        version_from: How to extract version ("branch", "tag", or regex)
        strip_prefix: Prefix to remove from branch name for version ID
        latest: Whether matching branches should be marked as latest
        name: Explicit branch name (alternative to pattern)

    Example:
        >>> pattern = GitBranchPattern(
        ...     pattern="release/*",
        ...     version_from="branch",
        ...     strip_prefix="release/",
        ... )
        >>> # Matches: release/0.1.6 → version "0.1.6"
    """

    pattern: str = ""
    version_from: str = "branch"  # "branch", "tag", or regex pattern
    strip_prefix: str = ""
    latest: bool = False
    name: str = ""  # Explicit branch name (alternative to pattern)

    def matches(self, ref_name: str) -> bool:
        """Check if a git ref matches this pattern."""
        import fnmatch

        if self.name:
            return ref_name == self.name
        if self.pattern:
            return fnmatch.fnmatch(ref_name, self.pattern)
        return False

    def extract_version_id(self, ref_name: str) -> str:
        """Extract version ID from a matching ref name."""
        if self.strip_prefix and ref_name.startswith(self.strip_prefix):
            return ref_name[len(self.strip_prefix) :]
        return ref_name


@dataclass
class GitVersionConfig:
    """
    Git-specific versioning configuration.

    Attributes:
        branches: List of branch patterns to match
        tags: List of tag patterns to match
        default_branch: Branch to use as "latest" (default: main)
        cache_worktrees: Whether to cache git worktrees for speed
        parallel_builds: Number of parallel version builds

    Example:
        >>> config = GitVersionConfig(
        ...     branches=[
        ...         GitBranchPattern(name="main", latest=True),
        ...         GitBranchPattern(pattern="release/*", strip_prefix="release/"),
        ...     ],
        ... )
    """

    branches: list[GitBranchPattern] = field(default_factory=list)
    tags: list[GitBranchPattern] = field(default_factory=list)
    default_branch: str = "main"
    cache_worktrees: bool = True
    parallel_builds: int = 4


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
    Supports two modes: folder-based (default) and git-based.

    Attributes:
        enabled: Whether versioning is enabled
        mode: Versioning mode ('folder' or 'git')
        versions: List of Version objects (for folder mode or discovered)
        aliases: Named aliases to version ids (e.g., {'latest': 'v3'})
        sections: Content sections that are versioned (e.g., ['docs'])
        shared: Paths to shared content included in all versions
        url_config: URL generation configuration
        git_config: Git-specific configuration (for git mode)

    Example (Folder Mode):
        >>> config = VersionConfig(
        ...     enabled=True,
        ...     versions=[
        ...         Version(id="v3", latest=True),
        ...         Version(id="v2"),
        ...     ],
        ...     aliases={"latest": "v3", "stable": "v3", "lts": "v2"},
        ... )

    Example (Git Mode):
        >>> config = VersionConfig(
        ...     enabled=True,
        ...     mode="git",
        ...     git_config=GitVersionConfig(
        ...         branches=[
        ...             GitBranchPattern(name="main", latest=True),
        ...             GitBranchPattern(pattern="release/*", strip_prefix="release/"),
        ...         ],
        ...     ),
        ... )
    """

    enabled: bool = False
    mode: str = "folder"  # "folder" or "git"
    versions: list[Version] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    sections: list[str] = field(default_factory=lambda: ["docs"])
    shared: list[str] = field(default_factory=lambda: ["_shared"])
    url_config: dict[str, Any] = field(default_factory=dict)
    seo_config: dict[str, Any] = field(default_factory=dict)
    git_config: GitVersionConfig | None = None

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
    def is_git_mode(self) -> bool:
        """Check if using git-based versioning."""
        return self.mode == "git" and self.git_config is not None

    def add_discovered_version(self, version: Version) -> None:
        """
        Add a dynamically discovered version (from git).

        Args:
            version: Version discovered from git branches/tags
        """
        self.versions.append(version)
        self._version_map[version.id] = version

        # Update latest alias if this is the latest version
        if version.latest and "latest" not in self.aliases:
            self.aliases["latest"] = version.id

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

        # Parse mode
        mode = versioning.get("mode", "folder")

        # Parse git configuration if in git mode
        git_config = None
        if mode == "git":
            git_raw = versioning.get("git", {})
            if git_raw:
                branches: list[GitBranchPattern] = []
                for b in git_raw.get("branches", []):
                    if isinstance(b, str):
                        # Simple format: just branch name
                        branches.append(GitBranchPattern(name=b))
                    elif isinstance(b, dict):
                        branches.append(
                            GitBranchPattern(
                                pattern=b.get("pattern", ""),
                                version_from=b.get("version_from", "branch"),
                                strip_prefix=b.get("strip_prefix", ""),
                                latest=b.get("latest", False),
                                name=b.get("name", ""),
                            )
                        )

                tags: list[GitBranchPattern] = []
                for t in git_raw.get("tags", []):
                    if isinstance(t, str):
                        tags.append(GitBranchPattern(pattern=t))
                    elif isinstance(t, dict):
                        tags.append(
                            GitBranchPattern(
                                pattern=t.get("pattern", ""),
                                version_from=t.get("version_from", "tag"),
                                strip_prefix=t.get("strip_prefix", ""),
                                latest=t.get("latest", False),
                                name=t.get("name", ""),
                            )
                        )

                git_config = GitVersionConfig(
                    branches=branches,
                    tags=tags,
                    default_branch=git_raw.get("default_branch", "main"),
                    cache_worktrees=git_raw.get("cache_worktrees", True),
                    parallel_builds=git_raw.get("parallel_builds", 4),
                )

        return cls(
            enabled=enabled,
            mode=mode,
            versions=versions,
            aliases=versioning.get("aliases", {}),
            sections=versioning.get("sections", ["docs"]),
            shared=versioning.get("shared", ["_shared"]),
            url_config=versioning.get("urls", {}),
            seo_config=versioning.get("seo", {}),
            git_config=git_config,
        )
