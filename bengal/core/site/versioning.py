"""
Versioning mixin for Site.

Provides properties and methods for versioned documentation support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.version import Version, VersionConfig


class SiteVersioningMixin:
    """
    Mixin providing versioning properties and methods for Site.

    Supports versioned documentation with multiple versions of content,
    version selectors in templates, and version-aware navigation.
    """

    # These attributes are defined on the Site dataclass
    version_config: VersionConfig

    @property
    def versioning_enabled(self) -> bool:
        """
        Check if versioned documentation is enabled.

        Returns:
            True if versioning is configured and enabled
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        return version_config is not None and version_config.enabled

    @property
    def versions(self) -> list[dict[str, Any]]:
        """
        Get list of all versions for templates (cached).

        Available in templates as `site.versions` for version selector rendering.
        Each version dict contains: id, label, latest, deprecated, url_prefix.

        Returns:
            List of version dictionaries for template use

        Example:
            {% for v in site.versions %}
                <option value="{{ v.url_prefix }}"
                        {% if v.id == site.current_version.id %}selected{% endif %}>
                    {{ v.label }}{% if v.latest %} (Latest){% endif %}
                </option>
            {% endfor %}

        Performance:
            Version dicts are cached on first access. For a 1000-page site with
            version selector in header, this eliminates ~1000 list creations.
        """
        # Return cached value if available
        cache_attr = "_versions_dict_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            return cached

        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            result: list[dict[str, Any]] = []
        else:
            result = [v.to_dict() for v in version_config.versions]

        # Cache the result
        object.__setattr__(self, cache_attr, result)
        return result

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """
        Get the latest version info for templates (cached).

        Returns:
            Latest version dictionary or None if versioning disabled

        Performance:
            Cached on first access to avoid repeated .to_dict() calls.
        """
        # Return cached value if available
        cache_attr = "_latest_version_dict_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            # None means "not cached yet", use sentinel for "cached None"
            return cached if cached != "_NO_LATEST_VERSION_" else None

        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            result = None
        else:
            latest = version_config.latest_version
            result = latest.to_dict() if latest else None

        # Cache the result (use sentinel for None to distinguish from "not cached")
        object.__setattr__(
            self, cache_attr, result if result is not None else "_NO_LATEST_VERSION_"
        )
        return result

    def get_version(self, version_id: str) -> Version | None:
        """
        Get a version by ID or alias.

        Args:
            version_id: Version ID (e.g., 'v2') or alias (e.g., 'latest')

        Returns:
            Version object or None if not found
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            return None
        return version_config.get_version_or_alias(version_id)

    def invalidate_version_caches(self) -> None:
        """
        Invalidate cached version dict lists.

        Call this when versioning configuration changes (e.g., during dev server reload).
        """
        for attr in ("_versions_dict_cache", "_latest_version_dict_cache"):
            if hasattr(self, attr):
                object.__delattr__(self, attr)
