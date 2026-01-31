"""
Validity tracking mixin for cache entries.

Provides a common pattern for caches that track entry validity:
- invalidate(key) - mark single entry as invalid
- invalidate_all() - mark all entries as invalid
- get_valid_entries() - filter to valid entries
- get_invalid_entries() - filter to invalid entries

Usage:
    @dataclass
    class MyEntry:
        data: str
        is_valid: bool = True

    class MyCache(ValidityTrackingMixin[str, MyEntry]):
        def __init__(self):
            self.entries: dict[str, MyEntry] = {}

        def _get_entries(self) -> dict[str, MyEntry]:
            return self.entries

        def _is_entry_valid(self, entry: MyEntry) -> bool:
            return entry.is_valid

        def _set_entry_valid(self, entry: MyEntry, valid: bool) -> None:
            entry.is_valid = valid

"""

from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Entry type


@runtime_checkable
class HasValidity(Protocol):
    """Protocol for entries with validity tracking."""

    is_valid: bool


class ValidityTrackingMixin(Generic[K, V]):
    """
    Mixin providing entry validity tracking operations.

    Subclasses must implement:
    - _get_entries() -> dict[K, V]: Return the entries dict
    - _is_entry_valid(entry: V) -> bool: Check if entry is valid
    - _set_entry_valid(entry: V, valid: bool) -> None: Set entry validity

    Provides:
    - invalidate(key): Mark single entry as invalid
    - invalidate_all(): Mark all entries as invalid
    - get_valid_entries(): Get dict of valid entries
    - get_invalid_entries(): Get dict of invalid entries
    - valid_count: Property returning count of valid entries
    - invalid_count: Property returning count of invalid entries

    """

    def _get_entries(self) -> dict[K, V]:
        """Return the entries dictionary. Override in subclass."""
        raise NotImplementedError("Subclass must implement _get_entries")

    def _is_entry_valid(self, entry: V) -> bool:
        """Check if entry is valid. Override in subclass."""
        raise NotImplementedError("Subclass must implement _is_entry_valid")

    def _set_entry_valid(self, entry: V, valid: bool) -> None:
        """Set entry validity. Override in subclass."""
        raise NotImplementedError("Subclass must implement _set_entry_valid")

    def invalidate(self, key: K) -> bool:
        """
        Mark a single entry as invalid.

        Args:
            key: Entry key to invalidate

        Returns:
            True if entry was found and invalidated, False if not found
        """
        entries = self._get_entries()
        if key in entries:
            self._set_entry_valid(entries[key], False)
            return True
        return False

    def invalidate_all(self) -> int:
        """
        Mark all entries as invalid.

        Returns:
            Number of entries invalidated
        """
        entries = self._get_entries()
        count = 0
        for entry in entries.values():
            if self._is_entry_valid(entry):
                self._set_entry_valid(entry, False)
                count += 1
        return count

    def get_valid_entries(self) -> dict[K, V]:
        """
        Get all valid entries.

        Returns:
            Dictionary of key → entry for valid entries only
        """
        return {k: v for k, v in self._get_entries().items() if self._is_entry_valid(v)}

    def get_invalid_entries(self) -> dict[K, V]:
        """
        Get all invalid entries.

        Returns:
            Dictionary of key → entry for invalid entries only
        """
        return {k: v for k, v in self._get_entries().items() if not self._is_entry_valid(v)}

    @property
    def valid_count(self) -> int:
        """Count of valid entries."""
        return sum(1 for e in self._get_entries().values() if self._is_entry_valid(e))

    @property
    def invalid_count(self) -> int:
        """Count of invalid entries."""
        return sum(1 for e in self._get_entries().values() if not self._is_entry_valid(e))

    def get_entry_value(self, key: K) -> Any | None:
        """
        Get entry value if valid, None otherwise.

        This is a helper for the common pattern of checking validity before returning.

        Args:
            key: Entry key

        Returns:
            Entry value if found and valid, None otherwise
        """
        entries = self._get_entries()
        if key not in entries:
            return None
        entry = entries[key]
        if not self._is_entry_valid(entry):
            return None
        return entry
