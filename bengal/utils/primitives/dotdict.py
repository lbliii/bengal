"""
DotDict - Dictionary with dot notation access.

Provides clean attribute-style access to dictionary data while avoiding
Jinja2 template gotchas (like .items, .keys, .values accessing methods).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import ItemsView, Iterator, KeysView, ValuesView


def _wrap_dict_value(cache: dict[str, Any], key: str, value: Any) -> Any:
    """Lazily wrap a dict value as DotDict, caching for identity stability."""
    if isinstance(value, dict) and not isinstance(value, DotDict):
        if key not in cache:
            cache[key] = DotDict(value)
        return cache[key]
    return value


class DotDict:
    """
    Dictionary wrapper that allows dot notation access without method name conflicts.

    This class solves a common Jinja2 gotcha: when using dot notation
    on a regular dict, Jinja2 will access dict methods (like .items())
    instead of dictionary keys named "items".

    Example Problem:
            >>> data = {"skills": [{"category": "Programming", "items": ["Python"]}]}
            >>> # In Jinja2 template:
            >>> # {{ skill_group.items }}  # Accesses .items() method! ❌

    Solution with DotDict:
            >>> data = DotDict({"skills": [{"category": "Programming", "items": ["Python"]}]})
            >>> # In Jinja2 template:
            >>> # {{ skill_group.items }}  # Accesses "items" field! ✅

    Features:
        - Dot notation: obj.key
        - Bracket notation: obj['key']
        - Recursive wrapping of nested dicts (with caching for performance)
        - Dict-like interface (but not inheriting from dict)
        - No method name collisions
        - Returns '' for missing keys (consistent with ParamsContext) — note
          this means ``hasattr(d, key)`` is always True; use ``key in d`` or
          ``d.get(key)`` to test membership.

    Usage:
            >>> # Create from dict
            >>> data = DotDict({"name": "Alice", "age": 30})
            >>> data.name
            'Alice'

            >>> # Nested dicts auto-wrapped
            >>> data = DotDict({"user": {"name": "Bob"}})
            >>> data.user.name
            'Bob'

            >>> # Lists preserved
            >>> data = DotDict({"items": ["a", "b", "c"]})
            >>> data.items  # Returns list, not a method!
        ['a', 'b', 'c']

            >>> # Missing keys return empty string
            >>> data = DotDict({"name": "Alice"})
            >>> data.missing
            ''

    Implementation Note:
        Unlike traditional dict subclasses, DotDict does NOT inherit from dict.
        This avoids method name collisions. We implement the dict interface
        manually to work with Jinja2 and other dict-expecting code.

    Performance:
        Nested dictionaries are wrapped lazily and cached on first access.
        This prevents repeatedly creating new DotDict objects for the same
        nested data, which is especially important for deeply nested structures
        or when accessed in template loops.

    """

    def __init__(self, data: dict[str, Any] | None = None):
        """Initialize with a dictionary and a cache for wrapped nested objects."""
        object.__setattr__(self, "_data", data or {})
        object.__setattr__(self, "_cache", {})

    def __getattribute__(self, key: str) -> Any:
        """
        Intercept attribute access to prioritize data fields over methods.

        This ensures that if a data field has the same name as a method
        (like 'items', 'keys', 'values'), the data field is returned.

        For Jinja2 compatibility, missing keys return ``""`` (empty string),
        not ``None`` and not ``AttributeError``. This is intentional and
        load-bearing — see ``themes/default/templates/SAFE_PATTERNS.md`` —
        but a side effect is that ``hasattr(d, key)`` is **always True** on
        a DotDict. Use ``key in d`` or ``d.get(key)`` to test for membership.

        Args:
            key: The attribute name

        Returns:
            The data value if it exists, a real attribute, or ``""`` on miss.
        """
        # Special case: internal attributes need normal access
        if key in ("_data", "_cache", "__class__", "__dict__"):
            return object.__getattribute__(self, key)

        # Check if key exists in data first
        data = object.__getattribute__(self, "_data")
        if key in data:
            return _wrap_dict_value(object.__getattribute__(self, "_cache"), key, data[key])

        # Try to get as a real attribute (methods like .get(), .keys())
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            # Miss — empty string preserves Jinja2 falsy-chain ergonomics.
            return ""

    def __setattr__(self, key: str, value: Any) -> None:
        """Allow dot notation assignment. Invalidates cache for the key."""
        if key in ("_data", "_cache"):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value
            # Invalidate cached wrapped object if it exists
            if key in self._cache:
                del self._cache[key]

    def __delattr__(self, key: str) -> None:
        """Allow dot notation deletion. Invalidates cache for the key."""
        if key in self._data:
            del self._data[key]
            # Invalidate cached wrapped object if it exists
            if key in self._cache:
                del self._cache[key]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    # Dict interface methods
    def __getitem__(self, key: str) -> Any:
        """Bracket notation access with caching."""
        return _wrap_dict_value(self._cache, key, self._data[key])

    def __setitem__(self, key: str, value: Any) -> None:
        """Bracket notation assignment. Invalidates cache for the key."""
        self._data[key] = value
        # Invalidate cached wrapped object if it exists
        if key in self._cache:
            del self._cache[key]

    def __delitem__(self, key: str) -> None:
        """Bracket notation deletion. Invalidates cache for the key."""
        del self._data[key]
        # Invalidate cached wrapped object if it exists
        if key in self._cache:
            del self._cache[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data

    def __len__(self) -> int:
        """Return number of keys."""
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._data)

    def __repr__(self) -> str:
        """Custom repr showing it's a DotDict."""
        return f"DotDict({self._data!r})"

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default."""
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> KeysView[str]:
        """Return dict keys."""
        return cast("KeysView[str]", self._data.keys())

    def values(self) -> ValuesView[Any]:
        """Return dict values."""
        return cast("ValuesView[Any]", self._data.values())

    def items(self) -> ItemsView[str, Any]:
        """Return dict items - note this is the METHOD, not a field."""
        return cast("ItemsView[str, Any]", self._data.items())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DotDict:
        """
        Create DotDict from a regular dict, recursively wrapping nested dicts.

        The eager recursion (and especially the dict-in-list wrap below) is
        required: ``__getattribute__`` only lazily wraps top-level dict
        *values*, not dicts nested inside lists. Templates iterate
        list-of-dicts (e.g. ``site.data.tracks``) and access ``.attr`` on
        each item, which only works if those items are pre-wrapped here.
        See ``plan/foundation-leaf-hygiene.md`` Sprint 0 Q2 for details.

        Args:
            data: Source dictionary

        Returns:
            DotDict with all nested dicts also wrapped
        """
        result = cls()
        for key, value in data.items():
            if isinstance(value, dict) and not isinstance(value, DotDict):
                result[key] = cls.from_dict(value)
            elif isinstance(value, list):
                # Wrap dicts in lists too
                result[key] = [
                    cls.from_dict(item)
                    if isinstance(item, dict) and not isinstance(item, DotDict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert back to regular dict."""
        return dict(self._data)


def wrap_data(data: Any) -> Any:
    """
    Recursively wrap dictionaries in DotDict for clean access.

    This is the main helper function for wrapping data loaded from
    YAML/JSON files before passing to templates.

    Args:
        data: Data to wrap (can be dict, list, or primitive)

    Returns:
        Wrapped data with DotDict for all dicts

    Example:
            >>> data = {
            ...     "team": [
            ...         {"name": "Alice", "skills": {"items": ["Python"]}},
            ...         {"name": "Bob", "skills": {"items": ["JavaScript"]}}
            ...     ]
            ... }
            >>> wrapped = wrap_data(data)
            >>> wrapped.team[0].skills.items  # Clean access!
        ['Python']

    """
    if isinstance(data, dict) and not isinstance(data, DotDict):
        return DotDict.from_dict(data)
    if isinstance(data, list):
        return [wrap_data(item) for item in data]
    return data
