"""
Version-aware content path resolution.

This module provides the VersionResolver class that handles versioned content
path resolution, shared content injection, and cross-version linking.

Key Concepts:
    - **Source paths**: Physical location (e.g., `_versions/v2/docs/guide.md`)
    - **Logical paths**: Version-agnostic path (e.g., `docs/guide.md`)
    - **Output paths**: Build output (e.g., `public/docs/v2/guide/index.html`)
    - **Shared content**: Content in `_shared/` is included in all versions

Features:
    - Determine which version a content path belongs to
    - Resolve shared content paths for each version
    - Compute output paths with version prefixes
    - Handle cross-version content linking (`[[v2:path/to/page]]` syntax)
    - Strip/add version prefixes based on URL strategy

Architecture:
    VersionResolver is used during discovery to assign version information
    to pages and during URL generation to compute version-aware paths. It
    integrates with Bengal's URLStrategy for consistent URL handling.

Related:
    - bengal/core/version.py: Version and VersionConfig models
    - bengal/discovery/content_discovery.py: Content discovery
    - bengal/discovery/git_version_adapter.py: Git-based version discovery
    - bengal/utils/url_strategy.py: URL generation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.version import Version, VersionConfig


class VersionResolver:
    """
    Resolves versioned content paths and manages shared content.

    This class handles the mapping between source paths, logical paths, and
    output paths for versioned documentation. It also manages shared content
    that appears in all versions.

    Responsibilities:
        - Determine which version a content path belongs to
        - Resolve shared content paths for each version
        - Compute output paths with version prefixes
        - Handle cross-version content linking

    Attributes:
        version_config: Site versioning configuration
        root_path: Site root directory
        enabled: Whether versioning is enabled (read-only property)

    Example:
        >>> from bengal.discovery import VersionResolver
        >>> from bengal.core.version import VersionConfig
        >>> from pathlib import Path
        >>>
        >>> config = VersionConfig.from_config(site_config)
        >>> resolver = VersionResolver(config, Path("."))
        >>>
        >>> # Determine version for a path
        >>> version = resolver.get_version_for_path("_versions/v2/docs/guide.md")
        >>> print(version.id)  # "v2"
        >>>
        >>> # Get logical path (without version prefix)
        >>> logical = resolver.get_logical_path("_versions/v2/docs/guide.md")
        >>> print(logical)  # Path("docs/guide.md")
        >>>
        >>> # Resolve cross-version link
        >>> url = resolver.resolve_cross_version_link("[[v2:guide]]", current_version)
        >>> print(url)  # "/docs/v2/guide/"
    """

    def __init__(
        self,
        version_config: VersionConfig,
        root_path: Path,
    ) -> None:
        """
        Initialize the version resolver.

        Args:
            version_config: Site versioning configuration
            root_path: Site root directory
        """
        self.version_config = version_config
        self.root_path = root_path
        self.logger = get_logger(__name__)

        # Build source -> version mapping for fast lookups
        self._source_version_map: dict[str, Version] = {}
        if version_config.enabled:
            for version in version_config.versions:
                if version.source:
                    # Normalize source path
                    source = version.source.rstrip("/")
                    self._source_version_map[source] = version

    @property
    def enabled(self) -> bool:
        """Check if versioning is enabled."""
        return self.version_config.enabled

    def get_version_for_path(self, content_path: Path | str) -> Version | None:
        """
        Determine which version a content path belongs to.

        Handles:
            - _versions/<id>/* paths → maps to specific version
            - Versioned section paths → maps to latest version
            - Non-versioned paths → returns None

        Args:
            content_path: Path to content file (relative or absolute)

        Returns:
            Version object or None if not versioned

        Example:
            >>> resolver.get_version_for_path("_versions/v2/docs/guide.md")
            Version(id='v2', ...)
            >>> resolver.get_version_for_path("docs/guide.md")
            Version(id='v3', latest=True, ...)  # latest version
        """
        if not self.enabled:
            return None

        path_str = str(content_path)

        # Check for explicit version paths (_versions/<id>/...)
        if "_versions/" in path_str:
            parts = path_str.split("_versions/")
            if len(parts) > 1:
                # Extract version id from path
                version_id = parts[1].split("/")[0]
                return self.version_config.get_version(version_id)

        # Check if path is in a versioned section (implies latest version)
        for section in self.version_config.sections:
            if path_str.startswith(section) or f"/{section}/" in path_str:
                return self.version_config.latest_version

        return None

    def get_logical_path(self, content_path: Path | str) -> Path:
        """
        Get the logical path for a versioned content file.

        Strips version-specific prefixes to get the canonical path.

        Args:
            content_path: Source content path

        Returns:
            Logical path without version prefix

        Example:
            >>> resolver.get_logical_path("_versions/v2/docs/guide.md")
            Path("docs/guide.md")
            >>> resolver.get_logical_path("docs/guide.md")
            Path("docs/guide.md")  # unchanged
        """
        path = Path(content_path)
        path_str = str(path)

        # Handle _versions/<id>/<section>/... paths
        if "_versions/" in path_str:
            parts = path_str.split("_versions/")
            if len(parts) > 1:
                # Remove version id, keep rest
                # _versions/v2/docs/guide.md → docs/guide.md
                version_and_rest = parts[1]
                # Skip version id part
                rest_parts = version_and_rest.split("/", 1)
                if len(rest_parts) > 1:
                    return Path(rest_parts[1])
                return Path("")

        return path

    def get_shared_content_paths(self) -> list[Path]:
        """
        Get paths to shared content directories.

        Shared content is included in all versions (e.g., common images,
        reusable snippets, shared partials).

        Returns:
            List of absolute paths to shared content directories
        """
        if not self.enabled:
            return []

        paths = []
        for shared_path in self.version_config.shared:
            full_path = self.root_path / shared_path
            if full_path.exists() and full_path.is_dir():
                paths.append(full_path)
            else:
                self.logger.debug(
                    "shared_content_path_not_found",
                    path=str(full_path),
                )

        return paths

    def should_include_shared_content(self, version: Version) -> bool:
        """
        Check if shared content should be included for a version.

        By default, shared content is included in all versions.
        Can be disabled per-version via configuration.

        Args:
            version: Version to check

        Returns:
            True if shared content should be included
        """
        # All versions include shared content by default
        return True

    def resolve_cross_version_link(
        self,
        link_target: str,
        current_version: Version | None,
    ) -> str | None:
        """
        Resolve a cross-version link reference.

        Handles links like [[v2:path/to/page]] or [[latest:path/to/page]].

        Args:
            link_target: Link target with optional version prefix
            current_version: Current page's version context

        Returns:
            Resolved URL path or None if not a version link

        Example:
            >>> resolver.resolve_cross_version_link("[[v2:guide]]", current_v3)
            "/docs/v2/guide/"
            >>> resolver.resolve_cross_version_link("[[latest:guide]]", current_v2)
            "/docs/guide/"  # latest has no prefix
        """
        # Must look like [[version:path]]
        if not link_target.startswith("[[") or not link_target.endswith("]]"):
            return None

        # Parse [[version:path]] format
        content = link_target[2:-2]  # Remove [[ and ]]
        if ":" not in content:
            return None
        version_id, path = content.split(":", 1)

        target_version = self.version_config.get_version_or_alias(version_id)
        if not target_version:
            return None

        # Build URL with version prefix
        if target_version.latest:
            return f"/{path}/"
        else:
            return f"/{target_version.id}/{path}/"

    def assign_version_to_page(
        self,
        page: Page,
        source_path: Path,
    ) -> None:
        """
        Assign version information to a page based on its source path.

        Updates page.core.version if the page belongs to a versioned section.

        Args:
            page: Page to update
            source_path: Source content path
        """
        version = self.get_version_for_path(source_path)
        if version and hasattr(page, "core") and page.core is not None:
            # Create new PageCore with version set
            # Note: PageCore is immutable, so we need to check if this is mutable
            if hasattr(page.core, "__dict__"):
                # Mutable - can set directly
                object.__setattr__(page.core, "version", version.id)
            elif hasattr(page, "metadata"):
                # Fallback to metadata
                page.metadata["version"] = version.id

    def get_version_url_prefix(self, version: Version | None) -> str:
        """
        Get the URL prefix for a version.

        Args:
            version: Version object (None for unversioned content)

        Returns:
            URL prefix string (empty for latest, "/v2" for v2, etc.)
        """
        if version is None or version.latest:
            return ""
        return f"/{version.id}"
