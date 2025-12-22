"""
Path utilities for Bengal SSG - compatibility shim.

This module re-exports path utilities from their canonical locations for
backward compatibility. New code should import directly from the canonical
locations:

    - ``BengalPaths``: from bengal.cache.paths

For legacy compatibility, this module also provides ``LegacyBengalPaths``
with static methods for path resolution.

Canonical Locations:
    - bengal/cache/paths.py: BengalPaths (instance-based), STATE_DIR_NAME
    - bengal/utils/text.py: format_path_for_display

See Also:
    - architecture/file-organization.md: Overall file organization
"""

from __future__ import annotations

from pathlib import Path

# Re-export from canonical location for backward compatibility
from bengal.cache.paths import BengalPaths as BengalPaths

__all__ = ["BengalPaths", "LegacyBengalPaths"]


class LegacyBengalPaths:
    """
    Legacy static method interface for Bengal path resolution.

    This class provides backward-compatible static methods for accessing
    Bengal state directory paths. New code should use the instance-based
    ``BengalPaths`` class from ``bengal.cache.paths`` instead.

    Example (legacy pattern)::

        from bengal.utils.paths import LegacyBengalPaths
        log_path = LegacyBengalPaths.get_build_log_path(source_dir)

    Example (recommended pattern)::

        from bengal.cache.paths import BengalPaths
        paths = BengalPaths(source_dir)
        log_path = paths.build_log

    .. deprecated::
        Use ``bengal.cache.paths.BengalPaths`` instead.
    """

    @staticmethod
    def get_profile_dir(source_dir: Path) -> Path:
        """Get the directory for storing performance profiles."""
        paths = BengalPaths(source_dir)
        paths.profiles_dir.mkdir(parents=True, exist_ok=True)
        return paths.profiles_dir

    @staticmethod
    def get_log_dir(source_dir: Path) -> Path:
        """Get the directory for storing build and server logs."""
        paths = BengalPaths(source_dir)
        paths.logs_dir.mkdir(parents=True, exist_ok=True)
        return paths.logs_dir

    @staticmethod
    def get_build_log_path(source_dir: Path, custom_path: Path | None = None) -> Path:
        """Get the path for the build log file."""
        if custom_path:
            return custom_path
        log_dir = LegacyBengalPaths.get_log_dir(source_dir)
        return log_dir / "build.log"

    @staticmethod
    def get_serve_log_path(source_dir: Path, custom_path: Path | None = None) -> Path:
        """Get the path for the dev server log file."""
        if custom_path:
            return custom_path
        log_dir = LegacyBengalPaths.get_log_dir(source_dir)
        return log_dir / "serve.log"

    @staticmethod
    def get_profile_path(
        source_dir: Path, custom_path: Path | None = None, filename: str = "build_profile.stats"
    ) -> Path:
        """Get the path for a performance profile file."""
        if custom_path:
            return custom_path
        profile_dir = LegacyBengalPaths.get_profile_dir(source_dir)
        return profile_dir / filename

    @staticmethod
    def get_cache_path(output_dir: Path) -> Path:
        """Get the path for the legacy build cache file."""
        return output_dir / ".bengal-cache.json"

    @staticmethod
    def get_template_cache_dir(output_dir: Path) -> Path:
        """Get the directory for Jinja2 bytecode cache."""
        cache_dir = output_dir / ".bengal-cache" / "templates"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
