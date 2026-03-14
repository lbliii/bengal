"""
Shared metadata helpers for weight and nav_title resolution.

Extracted to reduce duplication across Page, Section, PageProxy, and
weight-based sorting. Ensures consistent behavior for sortable weights
and navigation title fallbacks.

Functions:
    sortable_weight: Convert raw weight to sortable float (None → inf)
    resolve_nav_title: Resolve nav_title with title/fallback chain

"""

from __future__ import annotations


def sortable_weight(raw: int | float | None) -> float:
    """
    Convert raw weight to sortable float.

    Returns float(raw) if raw is not None, otherwise float("inf") so
    unweighted items sort last. Handles ValueError/TypeError for
    malformed YAML (e.g. string "ten").

    Args:
        raw: Weight from metadata (int, float, or None).

    Returns:
        Sortable float; infinity for None or invalid input.

    Example:
        >>> sortable_weight(10)
        10.0
        >>> sortable_weight(None)
        inf
        >>> sortable_weight("bad")
        inf
    """
    if raw is None:
        return float("inf")
    try:
        return float(raw)
    except ValueError, TypeError:
        return float("inf")


def resolve_nav_title(
    nav_title: str | None,
    title: str | None,
    fallback: str = "",
) -> str:
    """
    Resolve navigation title with fallback chain.

    Returns nav_title if set, else title, else fallback. Use for
    consistent nav display across Page, Section, and menu items.

    Args:
        nav_title: Explicit nav title from metadata.
        title: Regular title (fallback if nav_title empty).
        fallback: Final fallback if both empty.

    Returns:
        Resolved string (never None).

    Example:
        >>> resolve_nav_title("Authoring", "Content Authoring Guide", "")
        'Authoring'
        >>> resolve_nav_title(None, "Getting Started", "")
        'Getting Started'
    """
    return nav_title or title or fallback
