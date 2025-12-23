"""
Page Computed Properties Mixin - Cached expensive computations.

This mixin provides cached computed properties for pages. Each property is
computed once on first access and cached using @cached_property decorator.

Key Properties:
    - meta_description: SEO-friendly description (max 160 chars)
    - reading_time: Estimated reading time in minutes
    - excerpt: Content excerpt for listings (max 200 chars)
    - age_days: Days since publication
    - age_months: Months since publication

Performance:
    All properties use @cached_property decorator, ensuring expensive operations
    (HTML stripping, word counting, truncation) are only performed once per page.

Related Modules:
    - bengal.rendering.pipeline: Content rendering that populates page.content

See Also:
    - bengal/core/page/__init__.py: Page class that uses this mixin
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from functools import cached_property
from typing import Any, Protocol, cast


class HasMetadata(Protocol):
    """Protocol for objects that have metadata and content attributes."""

    metadata: dict[str, Any]
    content: str


class HasDate(Protocol):
    """Protocol for objects that have a date attribute."""

    date: datetime | None


class PageComputedMixin:
    """
    Mixin providing cached computed properties for pages.

    This mixin handles expensive operations that are cached after first access:
    - meta_description - SEO-friendly description
    - reading_time - Estimated reading time
    - excerpt - Content excerpt
    """

    @cached_property
    def meta_description(self: HasMetadata) -> str:
        """
        Generate SEO-friendly meta description (computed once, cached).

        Creates description by:
        - Using explicit 'description' from metadata if available
        - Otherwise generating from content by stripping HTML and truncating
        - Attempting to end at sentence boundary for better readability

        The result is cached after first access, so multiple template uses
        (meta tag, og:description, twitter:description) only compute once.

        Returns:
            Meta description text (max 160 chars)

        Example:
            <meta name="description" content="{{ page.meta_description }}">
            <meta property="og:description" content="{{ page.meta_description }}">
        """
        # Check metadata first (explicit description)
        description = self.metadata.get("description")
        if description:
            return cast(str, description)

        # Generate from content
        text = self.content
        if not text:
            return ""

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        length = 160
        if len(text) <= length:
            return text

        # Truncate to length
        truncated = text[:length]

        # Try to end at sentence boundary
        sentence_end = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))

        if sentence_end > length * 0.6:  # At least 60% of desired length
            return truncated[: sentence_end + 1].strip()

        # Try to end at word boundary
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space].strip() + "…"

        return truncated + "…"

    @cached_property
    def reading_time(self: HasMetadata) -> int:
        """
        Calculate reading time in minutes (computed once, cached).

        Estimates reading time based on word count at 200 words per minute.
        Strips HTML before counting to ensure accurate word count.

        The result is cached after first access for efficient repeated use.

        Returns:
            Reading time in minutes (minimum 1)

        Example:
            <span class="reading-time">{{ page.reading_time }} min read</span>
        """
        if not self.content:
            return 1

        # Strip HTML if present
        clean_text = re.sub(r"<[^>]+>", "", self.content)

        # Count words
        words = len(clean_text.split())

        # Calculate reading time at 200 WPM
        minutes = words / 200

        # Always return at least 1 minute
        return max(1, round(minutes))

    @cached_property
    def excerpt(self: HasMetadata) -> str:
        """
        Extract content excerpt (computed once, cached).

        Creates a 200-character excerpt from content by:
        - Stripping HTML tags
        - Truncating to length
        - Respecting word boundaries (doesn't cut words in half)
        - Adding ellipsis if truncated

        The result is cached after first access for efficient repeated use.

        Returns:
            Excerpt text with ellipsis if truncated

        Example:
            <p class="excerpt">{{ page.excerpt }}</p>
        """
        if not self.content:
            return ""

        # Strip HTML first
        clean_text = re.sub(r"<[^>]+>", "", self.content)

        length = 200
        if len(clean_text) <= length:
            return clean_text

        # Find the last space before the limit (respect word boundaries)
        excerpt_text = clean_text[:length].rsplit(" ", 1)[0]
        return excerpt_text + "..."

    @cached_property
    def age_days(self: HasDate) -> int:
        """
        Calculate days since publication (computed once, cached).

        Returns the number of days since the page's date. Useful for
        determining content freshness and applying age-based styling.

        Returns:
            Number of days since publication, or 0 if no date

        Example:
            {% if page.age_days < 7 %}
              <span class="badge">New</span>
            {% endif %}
        """
        page_date = getattr(self, "date", None)
        if page_date is None:
            return 0

        # Handle timezone-aware dates
        now = datetime.now(UTC) if page_date.tzinfo is not None else datetime.now()
        diff = now - page_date
        return max(0, diff.days)

    @cached_property
    def age_months(self: HasDate) -> int:
        """
        Calculate months since publication (computed once, cached).

        Uses calendar months rather than 30-day periods for more intuitive
        results. A post from January 15 accessed in March would be 2 months old.

        Returns:
            Number of months since publication, or 0 if no date

        Example:
            {% if page.age_months > 6 %}
              <div class="notice">This content may be outdated.</div>
            {% endif %}
        """
        page_date = getattr(self, "date", None)
        if page_date is None:
            return 0

        now = datetime.now(UTC) if page_date.tzinfo is not None else datetime.now()
        months = (now.year - page_date.year) * 12 + (now.month - page_date.month)
        return max(0, months)
