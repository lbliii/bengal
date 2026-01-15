"""
Data file access tracking for incremental builds.

Provides a wrapper around site.data that records which data files are
accessed during page rendering. This enables incremental builds to
rebuild only pages affected by data file changes.

Key Concepts:
- TrackedData: Wrapper that intercepts attribute access on site.data
- Thread-local tracking: Uses DependencyTracker's current_page for thread-safety
- File-level granularity: Tracks at data file level, not key level
- ContextVar pattern: Tracker is accessed via ContextVar for thread safety

Related Modules:
- bengal.build.tracking: Records dependencies
- bengal.core.site.data: DataLoadingMixin that populates site.data
- bengal.utils.dotdict: DotDict for dot-notation access

See Also:
- plan/rfc-incremental-build-dependency-gaps.md: Design rationale
- plan/rfc-free-threading-patterns.md: ContextVar pattern

RFC: rfc-incremental-build-dependency-gaps (Phase 1)
RFC: rfc-free-threading-patterns (ContextVar pattern)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.tracking import DependencyTracker
    from bengal.utils.primitives.dotdict import DotDict

logger = get_logger(__name__)

__all__ = [
    # ContextVar functions for tracker management
    "get_current_tracker",
    "set_current_tracker",
    "reset_current_tracker",
    "tracker_context",
    # Data wrapper
    "TrackedData",
    "wrap_data_for_tracking",
]


# =============================================================================
# ContextVar for Dependency Tracker (Thread-Safe)
# =============================================================================
# This allows SiteContext to access the current tracker without needing
# it passed through the entire call stack. Each thread/async task gets
# its own tracker via ContextVar.
#
# RFC: rfc-free-threading-patterns.md
# - ContextVars are thread-local by design (PEP 567)
# - ~8M ops/sec throughput
# - Zero lock contention

_current_tracker: ContextVar[DependencyTracker | None] = ContextVar(
    "current_tracker",
    default=None,
)


def get_current_tracker() -> DependencyTracker | None:
    """Get the current dependency tracker for this thread/context.
    
    Returns:
        DependencyTracker if set, None otherwise.
        
    Thread Safety:
        Uses ContextVar - each thread/async task has independent storage.
    """
    return _current_tracker.get()


def set_current_tracker(tracker: DependencyTracker | None) -> Token[DependencyTracker | None]:
    """Set the dependency tracker for the current context.
    
    Args:
        tracker: DependencyTracker instance or None to clear.
        
    Returns:
        Token for restoring previous value via reset_current_tracker().
    """
    return _current_tracker.set(tracker)


def reset_current_tracker(token: Token[DependencyTracker | None] | None = None) -> None:
    """Reset the tracker to its previous value.
    
    Args:
        token: Token from set_current_tracker() for proper nesting.
               If None, sets tracker to None.
    """
    if token is not None:
        _current_tracker.reset(token)
    else:
        _current_tracker.set(None)


@contextmanager
def tracker_context(tracker: DependencyTracker | None) -> Iterator[DependencyTracker | None]:
    """Context manager for scoped tracker usage.
    
    Properly restores previous tracker on exit (supports nesting).
    
    Usage:
        with tracker_context(dependency_tracker):
            # All rendering in this context can access tracker
            # via get_current_tracker()
            render_pages(pages)
    
    Args:
        tracker: DependencyTracker to use within the context.
        
    Yields:
        The tracker that was set.
    """
    token = set_current_tracker(tracker)
    try:
        yield tracker
    finally:
        reset_current_tracker(token)


class TrackedData:
    """
    Wrapper around site.data that tracks data file access for incremental builds.
    
    When a template accesses `site.data.team`, this wrapper records that the
    current page depends on `data/team.yaml`. During incremental builds, if
    `data/team.yaml` changes, pages that accessed it will be rebuilt.
    
    Thread Safety:
        Uses ContextVar to get the current tracker at access time. Each thread
        has its own tracker context, enabling parallel rendering.
    
    Creation:
        Internal use only. Created by SiteContext when data is accessed.
    
    Example:
        # In template: {{ site.data.team.members }}
        # This records: page depends on data/team.yaml
    """

    def __init__(
        self,
        data: DotDict,
        data_dir: Path,
    ) -> None:
        """
        Initialize tracked data wrapper.
        
        Args:
            data: Original site.data DotDict
            data_dir: Path to data/ directory (for file path resolution)
        
        Note:
            Tracker is NOT stored here - looked up via get_current_tracker()
            at access time for thread-safety.
        """
        # Use object.__setattr__ to bypass our __setattr__
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_data_dir", data_dir)
        # Cache resolved file paths for common data files
        object.__setattr__(self, "_file_cache", {})

    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access to track data file dependencies.
        
        When accessing `site.data.team`, records that the current page
        depends on `data/team.yaml` (or .yml/.json/.toml).
        
        Thread Safety:
            Gets tracker from ContextVar at access time, not from init.
            This ensures each thread uses its own tracker during parallel rendering.
        """
        data = object.__getattribute__(self, "_data")
        data_dir = object.__getattribute__(self, "_data_dir")
        file_cache = object.__getattribute__(self, "_file_cache")
        
        # Get tracker from ContextVar (thread-safe)
        tracker = get_current_tracker()

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
) -> TrackedData:
    """
    Wrap site.data for dependency tracking.
    
    Creates a TrackedData wrapper that will record data file access
    when a tracker is available via get_current_tracker().
    
    Args:
        data: Original site.data DotDict
        data_dir: Path to data/ directory
    
    Returns:
        TrackedData wrapper (tracker looked up at access time)
    """
    return TrackedData(data, data_dir)
