"""
Bidirectional index consistency checking utilities.

Used by TaxonomyIndex and QueryIndex to verify forward/reverse index sync.

Forward index: key → set[pages] (e.g., tag → pages with that tag)
Reverse index: page → set[keys] (e.g., page → tags on that page)

The invariant is:
- For every (key, page) in forward, (page, key) must be in reverse
- For every (page, key) in reverse, (key, page) must be in forward

Usage:
    violations = check_bidirectional_invariants(
        forward=self.entries,  # key → page_paths
        reverse=self._page_to_keys,  # page → keys
        forward_getter=lambda e: e.page_paths,
    )
    if violations:
        logger.warning("Index corruption detected", violations=violations[:5])

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def check_bidirectional_invariants(
    forward: dict[str, Any],
    reverse: dict[str, set[str]],
    forward_getter: Callable[[Any], set[str]] | None = None,
) -> list[str]:
    """
    Verify bidirectional index consistency.

    Checks that forward and reverse indexes are perfectly in sync.
    Detects corruption early before it causes subtle bugs.

    Args:
        forward: Forward index (key → entry or key → set[pages])
        reverse: Reverse index (page → set[keys])
        forward_getter: Function to extract page set from forward entry.
                       If None, assumes forward[key] is already set[str].

    Returns:
        List of violation messages (empty if consistent)

    Example:
        # For TaxonomyIndex
        violations = check_bidirectional_invariants(
            forward={tag: entry for tag, entry in self.tags.items()},
            reverse=self._page_to_tags,
            forward_getter=lambda entry: set(entry.page_paths),
        )

        # For QueryIndex
        violations = check_bidirectional_invariants(
            forward={key: entry for key, entry in self.entries.items()},
            reverse=self._page_to_keys,
            forward_getter=lambda entry: entry.page_paths,
        )

    """
    violations: list[str] = []

    # Default getter: assume forward value is already a set
    if forward_getter is None:

        def forward_getter(v: Any) -> set[str]:
            return v if isinstance(v, set) else set(v)

    # Check 1: Every (page, key) in reverse exists in forward
    for page, keys in reverse.items():
        for key in keys:
            if key not in forward:
                violations.append(
                    f"Reverse has key '{key}' for page '{page}' but key not in forward"
                )
            else:
                forward_pages = forward_getter(forward[key])
                if page not in forward_pages:
                    violations.append(
                        f"Page '{page}' in reverse for key '{key}' but not in forward['{key}']"
                    )

    # Check 2: Every (key, page) in forward exists in reverse
    for key, entry in forward.items():
        forward_pages = forward_getter(entry)
        for page in forward_pages:
            if page not in reverse:
                violations.append(
                    f"Page '{page}' in forward for key '{key}' but page not in reverse"
                )
            elif key not in reverse[page]:
                violations.append(
                    f"Key '{key}' for page '{page}' in forward but not in reverse['{page}']"
                )

    return violations


def repair_bidirectional_index(
    forward: dict[str, set[str]],
    reverse: dict[str, set[str]],
) -> tuple[int, int]:
    """
    Repair bidirectional index by rebuilding reverse from forward.

    This is the standard repair strategy: trust the forward index
    and rebuild the reverse index from scratch.

    Args:
        forward: Forward index (key → set[pages]) - source of truth
        reverse: Reverse index (page → set[keys]) - will be rebuilt

    Returns:
        Tuple of (entries_added, entries_removed) from reverse

    """
    # Build expected reverse from forward
    expected_reverse: dict[str, set[str]] = {}
    for key, pages in forward.items():
        for page in pages:
            if page not in expected_reverse:
                expected_reverse[page] = set()
            expected_reverse[page].add(key)

    # Count changes
    added = 0
    removed = 0

    # Remove pages not in expected
    pages_to_remove = set(reverse.keys()) - set(expected_reverse.keys())
    for page in pages_to_remove:
        removed += len(reverse[page])
        del reverse[page]

    # Add/update pages
    for page, expected_keys in expected_reverse.items():
        if page not in reverse:
            reverse[page] = expected_keys.copy()
            added += len(expected_keys)
        else:
            current = reverse[page]
            to_add = expected_keys - current
            to_remove = current - expected_keys
            added += len(to_add)
            removed += len(to_remove)
            reverse[page] = expected_keys.copy()

    return added, removed
