"""
CascadeView: Immutable mapping view for cascade metadata resolution.

This module provides a Mapping implementation that resolves page metadata
by combining frontmatter with cascade values from the CascadeSnapshot.

Key Design:
    - Frontmatter values always take precedence over cascade
    - Resolution happens on access (not via mutation/copying)
    - Immutable (frozen dataclass) for thread-safety
    - Implements Mapping protocol for dict-like access

Usage:
    view = CascadeView.for_page(frontmatter, "docs/guide", snapshot)

    # Dict-like access
    view["type"]           # KeyError if not found
    view.get("type")       # None if not found
    view.get("type", "x")  # Default if not found
    "type" in view         # Membership test
    len(view)              # Count of all keys
    list(view)             # All keys (frontmatter + cascade)
    dict(view)             # Materialize to dict (for serialization)

    # Provenance tracking
    view.cascade_keys()    # Keys that came from cascade
    view.frontmatter_keys() # Keys from page frontmatter

Benefits over mutable dict:
    - No stale state (always resolves from canonical snapshot)
    - No timing bugs (works regardless of when accessed)
    - No _cascade_keys pollution in user namespace
    - Thread-safe (frozen, no mutation)
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.cascade_snapshot import CascadeSnapshot


@dataclass(frozen=True, slots=True)
class CascadeView(Mapping[str, Any]):
    """
    Immutable view combining frontmatter with cascade resolution.

    Implements the Mapping protocol for dict-like access. Frontmatter
    values always take precedence over cascade values.

    This is the core of the cascade redesign: instead of copying cascade
    values into a mutable dict (which can drift), we provide a view that
    resolves on access from the canonical snapshot.

    Attributes:
        _frontmatter: Page's own frontmatter values (frozen via MappingProxyType)
        _section_path: Normalized section path for cascade lookup
        _snapshot: Reference to the site's CascadeSnapshot

    Thread Safety:
        This class is frozen and all its attributes are immutable or frozen.
        It can be safely shared across threads in free-threaded Python.

    Example:
        >>> view = CascadeView.for_page({"title": "Guide"}, "docs/guide", snapshot)
        >>> view["title"]  # From frontmatter
        "Guide"
        >>> view["type"]  # From cascade (docs section defines type: doc)
        "doc"
        >>> view.cascade_keys()
        frozenset({'type', 'variant'})
    """

    _frontmatter: MappingProxyType[str, Any]
    _section_path: str
    _snapshot: CascadeSnapshot

    @classmethod
    def for_page(
        cls,
        frontmatter: dict[str, Any],
        section_path: str,
        snapshot: CascadeSnapshot,
    ) -> CascadeView:
        """
        Create a CascadeView for a page.

        Factory method that freezes the frontmatter dict and normalizes
        the section path.

        Args:
            frontmatter: Page's raw frontmatter dict (will be frozen)
            section_path: Section path (absolute or relative)
            snapshot: CascadeSnapshot for cascade resolution

        Returns:
            CascadeView instance for the page
        """
        # Freeze frontmatter to prevent mutation
        frozen_frontmatter = MappingProxyType(dict(frontmatter))

        # Normalize section path for consistent lookup
        normalized_path = snapshot._normalize_section_path(section_path)

        return cls(
            _frontmatter=frozen_frontmatter,
            _section_path=normalized_path,
            _snapshot=snapshot,
        )

    @classmethod
    def empty(cls) -> CascadeView:
        """
        Create an empty CascadeView with no frontmatter or cascade.

        Useful for tests or virtual pages without metadata.

        Returns:
            Empty CascadeView instance
        """
        from bengal.core.cascade_snapshot import CascadeSnapshot

        return cls(
            _frontmatter=MappingProxyType({}),
            _section_path="",
            _snapshot=CascadeSnapshot.empty(),
        )

    # =========================================================================
    # Mapping Protocol Implementation
    # =========================================================================

    def __getitem__(self, key: str) -> Any:
        """
        Get a value by key, checking frontmatter first then cascade.

        Args:
            key: The key to look up

        Returns:
            The value from frontmatter or cascade

        Raises:
            KeyError: If key not found in frontmatter or cascade
        """
        # Frontmatter always wins
        if key in self._frontmatter:
            return self._frontmatter[key]

        # Fall back to cascade resolution
        value = self._snapshot.resolve(self._section_path, key)
        if value is not None:
            return value

        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        """
        Check if key exists in frontmatter or cascade.

        Args:
            key: The key to check

        Returns:
            True if key exists in frontmatter or cascade
        """
        if not isinstance(key, str):
            return False

        if key in self._frontmatter:
            return True

        # Check if cascade has this key
        return self._snapshot.resolve(self._section_path, key) is not None

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over all keys (frontmatter + cascade).

        Yields frontmatter keys first, then cascade keys not in frontmatter.

        Yields:
            All unique keys from frontmatter and cascade
        """
        # Yield frontmatter keys first
        seen: set[str] = set()
        for key in self._frontmatter:
            seen.add(key)
            yield key

        # Yield cascade keys not already in frontmatter
        cascade_keys = self._snapshot.get_cascade_keys(self._section_path)
        for key in cascade_keys:
            if key not in seen:
                yield key

    def __len__(self) -> int:
        """
        Return count of all unique keys (frontmatter + cascade).

        Returns:
            Number of unique keys
        """
        frontmatter_keys = set(self._frontmatter.keys())
        cascade_keys = self._snapshot.get_cascade_keys(self._section_path)
        return len(frontmatter_keys | cascade_keys)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value with default fallback.

        Args:
            key: The key to look up
            default: Value to return if key not found

        Returns:
            The value from frontmatter, cascade, or default
        """
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> set[str]:
        """
        Return all keys (frontmatter + cascade).

        Returns:
            Set of all unique keys
        """
        frontmatter_keys = set(self._frontmatter.keys())
        cascade_keys = self._snapshot.get_cascade_keys(self._section_path)
        return frontmatter_keys | cascade_keys

    def values(self) -> list[Any]:
        """
        Return all values (resolved).

        Returns:
            List of all values (order matches keys())
        """
        return [self[k] for k in self.keys()]

    def items(self) -> list[tuple[str, Any]]:
        """
        Return all key-value pairs (resolved).

        Returns:
            List of (key, value) tuples
        """
        return [(k, self[k]) for k in self.keys()]

    # =========================================================================
    # Provenance Tracking (replaces _cascade_keys in metadata)
    # =========================================================================

    def cascade_keys(self) -> frozenset[str]:
        """
        Return keys that come from cascade (not frontmatter).

        This replaces the _cascade_keys metadata pollution. Instead of
        storing tracking data in the user's namespace, we compute it
        on demand.

        Returns:
            Frozenset of keys that would be resolved from cascade
        """
        all_cascade_keys = self._snapshot.get_cascade_keys(self._section_path)
        # Only include cascade keys that aren't overridden by frontmatter
        return frozenset(k for k in all_cascade_keys if k not in self._frontmatter)

    def frontmatter_keys(self) -> frozenset[str]:
        """
        Return keys that come from page frontmatter.

        Returns:
            Frozenset of keys from frontmatter
        """
        return frozenset(self._frontmatter.keys())

    def resolve_all(self) -> dict[str, Any]:
        """
        Materialize the view to a plain dict.

        Useful for serialization or when a mutable dict is required.
        The returned dict is a snapshot - mutations won't affect the view.

        Returns:
            Dict with all resolved values
        """
        return dict(self.items())

    # =========================================================================
    # Compatibility Methods
    # =========================================================================

    def copy(self) -> dict[str, Any]:
        """
        Return a mutable copy as a plain dict.

        For compatibility with code expecting dict.copy().

        Returns:
            Mutable dict copy
        """
        return self.resolve_all()

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        frontmatter_count = len(self._frontmatter)
        cascade_count = len(self.cascade_keys())
        return (
            f"CascadeView(section={self._section_path!r}, "
            f"frontmatter={frontmatter_count}, cascade={cascade_count})"
        )
