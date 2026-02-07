"""
Series model for multi-part content grouping.

Provides a structured dataclass for representing content series (multi-part
tutorials, article series, etc.) with navigation support.

Public API:
Series: Content series representation with parts navigation

Frontmatter Format:
    series:
  name: "Building a Blog with Bengal"
  part: 1
  total: 5

Or with optional description:
    series:
  name: "Building a Blog with Bengal"
  part: 2
  total: 5
  description: "A comprehensive guide to building a blog"

Template Usage:
{% if page.series %}
  <div class="series-nav">
    <h4>{{ page.series.name }}</h4>
    <p>Part {{ page.series.part }} of {{ page.series.total }}</p>
    {% if page.prev_in_series %}
      <a href="{{ page.prev_in_series.href }}">← Previous</a>
    {% endif %}
    {% if page.next_in_series %}
      <a href="{{ page.next_in_series.href }}">Next →</a>
    {% endif %}
  </div>
{% endif %}

Related Modules:
- bengal.core.page.computed: Page computed properties using Series
- bengal.cache.indexes.series_index: Series-based page index

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Series:
    """
    Content series with part tracking and navigation support.

    This dataclass represents a multi-part content series with:
    - Series identification (name/slug)
    - Part positioning (current part, total parts)
    - Optional description

    The class is frozen (immutable) for hashability and cache safety.

    Attributes:
        name: Series name/title (required)
        part: Current part number (1-indexed)
        total: Total number of parts (optional, 0 if unknown)
        description: Series description (optional)
        slug: URL-safe identifier (auto-generated from name if not provided)

    Example:
            >>> series = Series(
            ...     name="Building a Blog with Bengal",
            ...     part=1,
            ...     total=5,
            ...     description="A comprehensive guide",
            ... )
            >>> series.name
            'Building a Blog with Bengal'
            >>> series.is_first
        True

    """

    name: str
    part: int = 1
    total: int = 0
    description: str = ""
    slug: str = ""

    def __post_init__(self) -> None:
        """Generate slug from name if not provided."""
        if not self.slug and self.name:
            # Generate slug - since frozen, use object.__setattr__
            from bengal.utils.primitives.text import slugify

            object.__setattr__(self, "slug", slugify(self.name))

    @property
    def is_first(self) -> bool:
        """Check if this is the first part in the series."""
        return self.part == 1

    @property
    def is_last(self) -> bool:
        """Check if this is the last part in the series (if total is known)."""
        return self.total > 0 and self.part >= self.total

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous part."""
        return self.part > 1

    @property
    def has_next(self) -> bool:
        """Check if there's a next part (if total is known)."""
        return self.total == 0 or self.part < self.total

    @property
    def progress_percent(self) -> int:
        """
        Calculate progress through series as percentage.

        Returns 0 if total is unknown.
        """
        if self.total <= 0:
            return 0
        return int((self.part / self.total) * 100)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for template context or serialization.

        Returns:
            Dictionary with series data
        """
        return {
            "name": self.name,
            "part": self.part,
            "total": self.total,
            "description": self.description,
            "slug": self.slug,
            "is_first": self.is_first,
            "is_last": self.is_last,
            "has_prev": self.has_prev,
            "has_next": self.has_next,
            "progress_percent": self.progress_percent,
        }

    @classmethod
    def from_frontmatter(cls, data: str | dict[str, Any]) -> Series | None:
        """
        Create Series from frontmatter data.

        Handles both string format (just name) and dict format (with details).

        Args:
            data: Series data from frontmatter (string or dict)

        Returns:
            Series instance or None if invalid data

        Examples:
            >>> Series.from_frontmatter("My Series")
            Series(name='My Series', part=1, ...)

            >>> Series.from_frontmatter({
            ...     "name": "My Series",
            ...     "part": 2,
            ...     "total": 5,
            ... })
            Series(name='My Series', part=2, total=5, ...)
        """
        if isinstance(data, str):
            # Simple string format - just series name
            return cls(name=data)

        if not isinstance(data, dict):
            return None

        name = data.get("name", "")
        if not name:
            # Try alternative keys
            name = data.get("title", "") or data.get("series_name", "")

        if not name:
            return None

        return cls(
            name=str(name),
            part=int(data.get("part", 1)),
            total=int(data.get("total", 0)),
            description=str(data.get("description", "")),
            slug=str(data.get("slug", "")),
        )

    def __str__(self) -> str:
        """Return series name for string representation."""
        return self.name

    def __bool__(self) -> bool:
        """Series is truthy if name is set."""
        return bool(self.name)
