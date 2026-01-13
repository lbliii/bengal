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
- author: Primary Author object
- authors: List of all Author objects
- series: Series object for multi-part content

Performance:
All properties use @cached_property decorator, ensuring expensive operations
(HTML stripping, word counting, truncation) are only performed once per page.

Related Modules:
- bengal.rendering.pipeline: Content rendering that populates page.content
- bengal.core.author: Author dataclass for author metadata

See Also:
- bengal/core/page/__init__.py: Page class that uses this mixin

"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

if TYPE_CHECKING:
    from bengal.core.author import Author
    from bengal.core.page.frontmatter import Frontmatter
    from bengal.core.series import Series
    from bengal.core.site import Site


@runtime_checkable
class HasMetadata(Protocol):
    """Protocol for objects that have metadata and content attributes."""

    metadata: dict[str, Any]
    _raw_content: str


@runtime_checkable
class HasDate(Protocol):
    """Protocol for objects that have a date attribute."""

    date: datetime | None


@runtime_checkable
class HasSiteAndMetadata(Protocol):
    """Protocol for objects with site reference and metadata."""

    metadata: dict[str, Any]
    _site: Site | None
    source_path: Path


@runtime_checkable
class PageLike(Protocol):
    """
    Protocol for page-like objects.
    
    Provides a unified interface for objects that can be treated as pages
    in templates, navigation, and rendering. This enables type-safe access
    to page properties without depending on the concrete Page class.
    
    Use Cases:
        - Template rendering: Functions accept PageLike for flexibility
        - Navigation building: Menu items work with any PageLike
        - Testing: Create minimal page-like objects for unit tests
    
    Example:
            >>> def render_page(page: PageLike) -> str:
            ...     return f"<h1>{page.title}</h1>{page.content}"
        
    """

    @property
    def title(self) -> str:
        """Page title from frontmatter or filename."""
        ...

    @property
    def href(self) -> str:
        """URL path to the page (e.g., '/docs/guide/')."""
        ...

    @property
    def content(self) -> str:
        """Rendered HTML content (template-ready)."""
        ...

    @property
    def frontmatter(self) -> Frontmatter:
        """Page frontmatter object."""
        ...

    @property
    def date(self) -> datetime | None:
        """Publication date, if set."""
        ...

    @property
    def draft(self) -> bool:
        """Whether this is a draft page."""
        ...

    @property
    def weight(self) -> int:
        """Sort weight for ordering."""
        ...

    @property
    def source_path(self) -> Path:
        """Path to source file."""
        ...


class PageComputedMixin:
    """
    Mixin providing cached computed properties for pages.
    
    This mixin handles expensive operations that are cached after first access:
    - meta_description - SEO-friendly description
    - word_count - Word count from source content
    - reading_time - Estimated reading time
    - excerpt - Content excerpt
    
    Underscore Convention:
        Properties prefixed with `_` are for internal/advanced use:
        - _source: Raw markdown source (for plugins, custom analysis)
        Properties without `_` are template-ready:
        - word_count, reading_time: Pre-computed for templates
        
    """

    @property
    def _source(self: HasMetadata) -> str:
        """
        Raw markdown source content.

        This property provides access to the original markdown source content.
        Use this for:
        - Plugins that need raw markdown
        - Custom analysis or transformation
        - Internal comparisons and hashing

        For template use, prefer the computed properties:
        - page.word_count - Pre-computed word count
        - page.reading_time - Pre-computed reading time

        Returns:
            Raw markdown source string

        Example:
            >>> len(page._source)  # Character count
            1523
            >>> page._source[:100]  # First 100 chars
            '# My Page Title\\n\\nThis is the introduction...'

        Note:
            Following the underscore convention, this property is for
            internal/advanced use. Templates should use page.word_count
            and page.reading_time instead of accessing _source directly.
        """
        return self._raw_content

    @cached_property
    def word_count(self: HasMetadata) -> int:
        """
        Word count from source markdown (computed once, cached).

        Counts words in the raw markdown source content. This is the
        authoritative word count for the page, representing the author's
        actual words rather than rendered HTML which may include generated
        content.

        The result is cached after first access for efficient repeated use.

        Returns:
            Word count (integer)

        Example:
            <span>{{ page.word_count }} words</span>

        See Also:
            - page.reading_time: Estimated reading time based on word_count
            - page._source: Raw markdown source (internal use only)
        """
        # Use _source (raw markdown) for accurate word count
        source = self._source
        if not source:
            return 0
        return len(source.split())

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

        # Generate from raw content
        text = self._raw_content
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

        Estimates reading time based on word_count at 200 words per minute.
        Uses the source markdown word count (via word_count property) for
        accurate estimation of author's actual writing.

        The result is cached after first access for efficient repeated use.

        Returns:
            Reading time in minutes (minimum 1)

        Example:
            <span class="reading-time">{{ page.reading_time }} min read</span>

        See Also:
            - page.word_count: The word count used for this calculation
        """
        # Use word_count property (based on _source markdown)
        return max(1, round(self.word_count / 200))

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
        if not self._raw_content:
            return ""

        # Strip HTML first
        clean_text = re.sub(r"<[^>]+>", "", self._raw_content)

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

    @cached_property
    def author(self: HasMetadata) -> Author | None:
        """
        Get primary author as Author object (computed once, cached).

        Parses the 'author' frontmatter field into a structured Author object.
        Supports both string format ("Jane Smith") and dict format with details.

        Returns:
            Author object or None if no author specified

        Example:
            {% if page.author %}
              <span class="author">{{ page.author.name }}</span>
              {% if page.author.avatar %}
                <img src="{{ page.author.avatar }}" alt="{{ page.author.name }}">
              {% endif %}
            {% endif %}
        """
        from bengal.core.author import Author

        # Check for 'author' field first
        author_data = self.metadata.get("author")
        if author_data:
            return Author.from_frontmatter(author_data)

        # Fall back to first author in 'authors' list
        authors_data = self.metadata.get("authors")
        if authors_data and isinstance(authors_data, list) and len(authors_data) > 0:
            return Author.from_frontmatter(authors_data[0])

        return None

    @cached_property
    def authors(self: HasMetadata) -> list[Author]:
        """
        Get all authors as list of Author objects (computed once, cached).

        Parses both 'author' and 'authors' frontmatter fields, combining them
        into a single deduplicated list. Handles string and dict formats.

        Returns:
            List of Author objects (empty list if no authors)

        Example:
            {% for author in page.authors %}
              <a href="/authors/{{ author.name | slugify }}/">
                {{ author.name }}
              </a>
            {% endfor %}
        """
        from bengal.core.author import Author

        result: list[Author] = []
        seen_names: set[str] = set()

        # Process 'author' field (single author)
        author_data = self.metadata.get("author")
        if author_data:
            author = Author.from_frontmatter(author_data)
            if author and author.name not in seen_names:
                result.append(author)
                seen_names.add(author.name)

        # Process 'authors' field (multiple authors)
        authors_data = self.metadata.get("authors")
        if authors_data and isinstance(authors_data, list):
            for item in authors_data:
                author = Author.from_frontmatter(item)
                if author and author.name not in seen_names:
                    result.append(author)
                    seen_names.add(author.name)

        return result

    @cached_property
    def series(self: HasMetadata) -> Series | None:
        """
        Get series info as Series object (computed once, cached).

        Parses the 'series' frontmatter field into a structured Series object
        for multi-part content navigation.

        Returns:
            Series object or None if not part of a series

        Example:
            {% if page.series %}
              <div class="series-nav">
                <h4>{{ page.series.name }}</h4>
                <p>Part {{ page.series.part }} of {{ page.series.total }}</p>
              </div>
            {% endif %}
        """
        from bengal.core.series import Series

        series_data = self.metadata.get("series")
        if not series_data:
            return None

        return Series.from_frontmatter(series_data)

    @cached_property
    def prev_in_series(self: HasSiteAndMetadata) -> Any | None:
        """
        Get previous page in series (computed once, cached).

        Looks up other pages in the same series via the SeriesIndex and
        returns the page with part number one less than this page.

        Returns:
            Previous Page in series, or None if first/not in series

        Example:
            {% if page.prev_in_series %}
              <a href="{{ page.prev_in_series.href }}">
                ← {{ page.prev_in_series.title }}
              </a>
            {% endif %}
        """
        return self._get_series_neighbor(-1)

    @cached_property
    def next_in_series(self: HasSiteAndMetadata) -> Any | None:
        """
        Get next page in series (computed once, cached).

        Looks up other pages in the same series via the SeriesIndex and
        returns the page with part number one more than this page.

        Returns:
            Next Page in series, or None if last/not in series

        Example:
            {% if page.next_in_series %}
              <a href="{{ page.next_in_series.href }}">
                {{ page.next_in_series.title }} →
              </a>
            {% endif %}
        """
        return self._get_series_neighbor(1)

    def _get_series_neighbor(self: HasSiteAndMetadata, offset: int) -> Any | None:
        """
        Get neighboring page in series by part offset.

        Args:
            offset: Part number offset (-1 for prev, +1 for next)

        Returns:
            Neighboring Page or None
        """
        # Get series info from this page
        series_data = self.metadata.get("series")
        if not series_data:
            return None

        # Extract series name and current part
        if isinstance(series_data, str):
            series_name = series_data
            current_part = 1
        elif isinstance(series_data, dict):
            series_name = series_data.get("name", "")
            current_part = int(series_data.get("part", 1))
        else:
            return None

        if not series_name:
            return None

        target_part = current_part + offset
        if target_part < 1:
            return None

        # Access site's series index
        site = getattr(self, "_site", None)
        if site is None:
            return None

        # Get series index
        indexes = getattr(site, "indexes", None)
        if indexes is None:
            return None

        series_index = getattr(indexes, "series", None)
        if series_index is None:
            return None

        # Get all page paths in this series
        page_paths = series_index.get(series_name)
        if not page_paths:
            return None

        # Get page lookup map
        page_map = site.get_page_path_map()

        # Find the page with the target part number
        for path in page_paths:
            page = page_map.get(path)
            if page is None:
                continue

            # Check this page's part number
            page_series = page.metadata.get("series")
            page_part = int(page_series.get("part", 1)) if isinstance(page_series, dict) else 1

            if page_part == target_part:
                return page

        return None
