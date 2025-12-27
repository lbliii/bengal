"""Role classification for template blocks.

Heuristic classification based on block name and emitted landmarks.
Returns "unknown" when classification is ambiguous.
"""

from __future__ import annotations

from typing import Literal

RoleType = Literal["navigation", "content", "sidebar", "header", "footer", "unknown"]


def classify_role(
    block_name: str,
    landmarks: frozenset[str],
) -> RoleType:
    """Classify block role based on name and emitted landmarks.

    This is a heuristic, not semantic truth. Returns "unknown" when
    classification is ambiguous.

    Priority:
        1. Landmarks (most reliable signal)
        2. Block name patterns (fallback)

    Args:
        block_name: Block identifier (e.g., "nav", "content", "sidebar")
        landmarks: HTML5 landmarks emitted by this block

    Returns:
        Inferred role or "unknown"

    Example:
        >>> classify_role("sidebar", frozenset({"nav"}))
        'navigation'  # Landmark takes precedence

        >>> classify_role("navigation", frozenset())
        'navigation'  # Name-based fallback

        >>> classify_role("custom_block", frozenset())
        'unknown'  # Cannot classify
    """
    # Landmark-based classification (strongest signal)
    if "nav" in landmarks and len(landmarks) == 1:
        return "navigation"
    if "main" in landmarks:
        return "content"
    if "aside" in landmarks:
        return "sidebar"
    if "header" in landmarks and "main" not in landmarks:
        return "header"
    if "footer" in landmarks:
        return "footer"

    # Name-based classification (fallback)
    name_lower = block_name.lower()

    if name_lower in ("nav", "navigation", "menu", "navbar", "topnav", "sidenav"):
        return "navigation"
    if name_lower in ("content", "main", "body", "article", "post", "entry"):
        return "content"
    if name_lower in ("sidebar", "aside", "toc", "left", "right"):
        return "sidebar"
    if name_lower in ("header", "head", "masthead", "banner", "hero"):
        return "header"
    if name_lower in ("footer", "foot", "colophon", "bottom"):
        return "footer"

    return "unknown"
