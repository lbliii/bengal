"""
WeightedPage helper for weight-based page sorting.

This module provides a simple dataclass used internally for sorting pages
by their weight metadata field.

Public API:
    WeightedPage: Helper dataclass for weight-based sorting

Related Modules:
    bengal.core.section: Section class that uses WeightedPage for sorting
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


@dataclass
class WeightedPage:
    """
    Helper for weight-based page sorting.

    Wraps a page with its weight and lowercase title for efficient
    comparison during sorting. Lower weights sort first, with title
    as secondary sort key.

    Attributes:
        page: The wrapped Page object
        weight: Sort weight (lower = first, infinity = end)
        title_lower: Lowercase title for case-insensitive sorting
    """

    page: Page
    weight: float = float("inf")
    title_lower: str = ""

    def __lt__(self, other: WeightedPage) -> bool:
        if self.weight != other.weight:
            return self.weight < other.weight
        return self.title_lower < other.title_lower
