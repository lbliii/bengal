"""
Data file access tracking for incremental builds.

Provides a wrapper around site.data that records which data files are
accessed during page rendering. This enables incremental builds to
rebuild only pages affected by data file changes.

Key Concepts:
- TrackedData: Wrapper that intercepts attribute access on site.data
- Thread-local tracking: Uses DependencyTracker's current_page for thread-safety
- File-level granularity: Tracks at data file level, not key level

Related Modules:
- bengal.cache.dependency_tracker: Records dependencies
- bengal.core.site.data: DataLoadingMixin that populates site.data
- bengal.utils.dotdict: DotDict for dot-notation access

See Also:
- plan/rfc-incremental-build-dependency-gaps.md: Design rationale
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.utils.primitives.dotdict import DotDict

logger = get_logger(__name__)


class TrackedData:
    """
    Wrapper around site.data that tracks data file access for incremental builds.
    
    When a template accesses `site.data.team`, this wrapper records that the
    current page depends on `data/team.yaml`. During incremental builds, if
    `data/team.yaml` changes, pages that accessed it will be rebuilt.
    
    Thread Safety:
        Uses DependencyTracker's thread-local `current_page` for thread-safe
        tracking during parallel rendering.
    
    Creation:
        Internal use only. Created by Site when dependency tracking is enabled.
    
    Example:
        # In template: {{ site.data.team.members }}
        # This records: page depends on data/team.yaml
    """

    def __init__(
        self,
        data: DotDict,
        data_dir: Path,
        tracker: DependencyTracker | None = None,
    ) -> None:
        """
        Initialize tracked data wrapper.
        
        Args:
            data: Original site.data DotDict
            data_dir: Path to data/ directory (for file path resolution)
            tracker: DependencyTracker instance for recording dependencies
        """
        # Use object.__setattr__ to bypass our __setattr__
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_data_dir", data_dir)
        object.__setattr__(self, "_tracker", tracker)
        # Cache resolved file paths for common data files
        object.__setattr__(self, "_file_cache", {})

    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access to track data file dependencies.
        
        When accessing `site.data.team`, records that the current page
        depends on `data/team.yaml` (or .yml/.json/.toml).
        """
        data = object.__getattribute__(self, "_data")
        tracker = object.__getattribute__(self, "_tracker")
        data_dir = object.__getattribute__(self, "_data_dir")
        file_cache = object.__getattribute__(self, "_file_cache")

        # Get the actual value
        try:
            value = getattr(data, name)
        except AttributeError:
            raise AttributeError(f"'site.data' has no attribute '{name}'")

        # Track the dependency if tracker is available and we're in a page context
        if tracker and hasattr(tracker.current_page, "value"):
            # Resolve the data file path (with caching)
            if name not in file_cache:
                file_cache[name] = self._resolve_data_file(name, data_dir)

            data_file = file_cache[name]
            if data_file:
                current_page = tracker.current_page.value
                tracker.track_data_file(current_page, data_file)

        return value

    def _resolve_data_file(self, key: str, data_dir: Path) -> Path | None:
        """
        Resolve a top-level data key to its source file.
        
        Args:
            key: Top-level key (e.g., "team" for site.data.team)
            data_dir: Path to data/ directory
        
        Returns:
            Path to data file if found, None otherwise
        """
        # Check common extensions
        extensions = [".yaml", ".yml", ".json", ".toml"]
        
        for ext in extensions:
            file_path = data_dir / f"{key}{ext}"
            if file_path.exists():
                return file_path

        # Check if it's a directory (data/team/members.yaml would be site.data.team.members)
        dir_path = data_dir / key
        if dir_path.is_dir():
            # For directories, we return None and don't track
            # (nested files are harder to track accurately)
            return None

        return None

    def __repr__(self) -> str:
        data = object.__getattribute__(self, "_data")
        return f"TrackedData({data!r})"

    def __str__(self) -> str:
        data = object.__getattribute__(self, "_data")
        return str(data)

    def __bool__(self) -> bool:
        data = object.__getattribute__(self, "_data")
        return bool(data)

    def __iter__(self):
        """Iterate over data keys."""
        data = object.__getattribute__(self, "_data")
        return iter(data)

    def __contains__(self, item) -> bool:
        """Check if key exists in data."""
        data = object.__getattribute__(self, "_data")
        return item in data

    def keys(self):
        """Get data keys."""
        data = object.__getattribute__(self, "_data")
        if hasattr(data, "keys"):
            return data.keys()
        return []

    def values(self):
        """Get data values."""
        data = object.__getattribute__(self, "_data")
        if hasattr(data, "values"):
            return data.values()
        return []

    def items(self):
        """Get data items."""
        data = object.__getattribute__(self, "_data")
        if hasattr(data, "items"):
            return data.items()
        return []

    def get(self, key: str, default: Any = None) -> Any:
        """Get data with optional default."""
        try:
            return self.__getattr__(key)
        except AttributeError:
            return default


def wrap_data_for_tracking(
    data: DotDict,
    data_dir: Path,
    tracker: DependencyTracker | None = None,
) -> TrackedData | DotDict:
    """
    Wrap site.data for dependency tracking.
    
    If a tracker is provided, wraps data in TrackedData to record
    data file access. Otherwise, returns the original data unchanged.
    
    Args:
        data: Original site.data DotDict
        data_dir: Path to data/ directory
        tracker: Optional DependencyTracker for recording dependencies
    
    Returns:
        TrackedData wrapper if tracker provided, else original data
    """
    if tracker is None:
        return data

    return TrackedData(data, data_dir, tracker)
