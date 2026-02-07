"""Version service for site versioning support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.version import Version, VersionConfig


class VersionService:
    """
    Standalone versioning service.

    Encapsulates version resolution, caching, and template-facing version
    data.  Composed into Site rather than mixed in.

    Args:
        version_config: Versioning configuration loaded from site config.
    """

    __slots__ = ("_version_config", "_versions_dict_cache", "_latest_version_dict_cache")

    def __init__(self, version_config: VersionConfig) -> None:
        self._version_config = version_config
        self._versions_dict_cache: list[dict[str, Any]] | None = None
        self._latest_version_dict_cache: dict[str, Any] | None | str = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def versioning_enabled(self) -> bool:
        """
        Check if versioned documentation is enabled.

        Returns:
            True if versioning is configured and enabled
        """
        return self._version_config is not None and self._version_config.enabled

    @property
    def versions(self) -> list[dict[str, Any]]:
        """
        Get list of all versions for templates (cached).

        Available in templates as ``site.versions`` for version selector rendering.
        Each version dict contains: id, label, latest, deprecated, url_prefix.

        Returns:
            List of version dictionaries for template use

        Performance:
            Version dicts are cached on first access. For a 1000-page site with
            version selector in header, this eliminates ~1000 list creations.
        """
        if self._versions_dict_cache is not None:
            return self._versions_dict_cache

        if not self._version_config or not self._version_config.enabled:
            result: list[dict[str, Any]] = []
        else:
            result = [v.to_dict() for v in self._version_config.versions]

        self._versions_dict_cache = result
        return result

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """
        Get the latest version info for templates (cached).

        Returns:
            Latest version dictionary or None if versioning disabled

        Performance:
            Cached on first access to avoid repeated ``.to_dict()`` calls.
        """
        if self._latest_version_dict_cache is not None:
            # None means "not cached yet"; sentinel distinguishes "cached None"
            return self._latest_version_dict_cache if self._latest_version_dict_cache != "_NO_LATEST_VERSION_" else None

        if not self._version_config or not self._version_config.enabled:
            result = None
        else:
            latest = self._version_config.latest_version
            result = latest.to_dict() if latest else None

        self._latest_version_dict_cache = result if result is not None else "_NO_LATEST_VERSION_"
        return result

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def get_version(self, version_id: str) -> Version | None:
        """
        Get a version by ID or alias.

        Args:
            version_id: Version ID (e.g., 'v2') or alias (e.g., 'latest')

        Returns:
            Version object or None if not found
        """
        if not self._version_config or not self._version_config.enabled:
            return None
        return self._version_config.get_version_or_alias(version_id)

    def invalidate_caches(self) -> None:
        """
        Invalidate cached version dict lists.

        Call this when versioning configuration changes (e.g., during dev
        server reload).
        """
        self._versions_dict_cache = None
        self._latest_version_dict_cache = None
