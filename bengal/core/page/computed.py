"""
Page Computed Properties - Free functions for cached expensive computations.

Functions accept explicit parameters (raw_content, metadata, date) instead of
accessing them through mixin self-reference.

Key Functions:
- compute_word_count: Word count from source markdown
- compute_meta_description: SEO-friendly description (max 160 chars)
- compute_reading_time: Estimated reading time in minutes
- compute_excerpt: Content excerpt for listings (max 200 chars)
- compute_age_days: Days since publication
- compute_age_months: Months since publication
- get_primary_author: Primary Author object
- get_all_authors: List of all Author objects
- get_series_info: Series object for multi-part content
- get_series_neighbor: Navigate between pages in a series

Performance:
Page class uses @cached_property wrappers that call these pure functions,
ensuring expensive operations (HTML stripping, word counting, truncation)
are only performed once per page.

Related Modules:
- bengal.rendering.pipeline: Content rendering that populates page.content
- bengal.core.author: Author dataclass for author metadata

See Also:
- bengal/core/page/__init__.py: Page class that wraps these functions as properties

"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from bengal.core.utils.text import strip_html, truncate_at_sentence, truncate_at_word

if TYPE_CHECKING:
    from bengal.core.author import Author
    from bengal.core.page import Page
    from bengal.core.series import Series
    from bengal.core.site import Site


def compute_word_count(raw_content: str) -> int:
    """Word count from source markdown.

    Counts words in the raw markdown source content. This is the
    authoritative word count for the page, representing the author's
    actual words rather than rendered HTML which may include generated
    content.

    Args:
        raw_content: Raw markdown source string

    Returns:
        Word count (integer)
    """
    if not raw_content:
        return 0
    return len(raw_content.split())


def compute_meta_description(metadata: Mapping[str, Any], raw_content: str) -> str:
    """Generate SEO-friendly meta description.

    Creates description by:
    - Using explicit 'description' from metadata if available
    - Otherwise generating from content by stripping HTML and truncating
    - Attempting to end at sentence boundary for better readability

    Args:
        metadata: Page metadata dict
        raw_content: Raw markdown source string

    Returns:
        Meta description text (max 160 chars)
    """
    # Check metadata first (explicit description)
    description = metadata.get("description")
    if description:
        return cast(str, description)

    # Generate from raw content
    if not raw_content:
        return ""

    # Strip HTML tags and normalize whitespace
    from bengal.core.utils.text import normalize_whitespace

    text = normalize_whitespace(strip_html(raw_content))

    # Truncate at sentence boundary for readability
    return truncate_at_sentence(text, length=160)


def compute_reading_time(word_count: int) -> int:
    """Calculate reading time in minutes.

    Estimates reading time at 200 words per minute.

    Args:
        word_count: Number of words in content

    Returns:
        Reading time in minutes (minimum 1)
    """
    return max(1, round(word_count / 200))


def compute_excerpt(raw_content: str) -> str:
    """Extract content excerpt.

    Creates a 200-character excerpt from content by:
    - Stripping HTML tags
    - Truncating to length
    - Respecting word boundaries (doesn't cut words in half)
    - Adding ellipsis if truncated

    Args:
        raw_content: Raw markdown source string

    Returns:
        Excerpt text with ellipsis if truncated
    """
    if not raw_content:
        return ""

    # Strip HTML and truncate at word boundary
    clean_text = strip_html(raw_content)
    return truncate_at_word(clean_text, length=200)


def compute_age_days(date: datetime | None) -> int:
    """Calculate days since publication.

    Args:
        date: Publication date (or None)

    Returns:
        Number of days since publication, or 0 if no date
    """
    if date is None:
        return 0

    # Handle timezone-aware dates
    now = datetime.now(UTC) if date.tzinfo is not None else datetime.now()
    diff = now - date
    return max(0, diff.days)


def compute_age_months(date: datetime | None) -> int:
    """Calculate months since publication.

    Uses calendar months rather than 30-day periods for more intuitive
    results. A post from January 15 accessed in March would be 2 months old.

    Args:
        date: Publication date (or None)

    Returns:
        Number of months since publication, or 0 if no date
    """
    if date is None:
        return 0

    now = datetime.now(UTC) if date.tzinfo is not None else datetime.now()
    months = (now.year - date.year) * 12 + (now.month - date.month)
    return max(0, months)


def get_primary_author(metadata: Mapping[str, Any]) -> Author | None:
    """Get primary author as Author object.

    Parses the 'author' frontmatter field into a structured Author object.
    Supports both string format ("Jane Smith") and dict format with details.

    Args:
        metadata: Page metadata dict

    Returns:
        Author object or None if no author specified
    """
    from bengal.core.author import Author

    # Check for 'author' field first
    author_data = metadata.get("author")
    if author_data:
        return Author.from_frontmatter(author_data)

    # Fall back to first author in 'authors' list
    authors_data = metadata.get("authors")
    if authors_data and isinstance(authors_data, list) and len(authors_data) > 0:
        return Author.from_frontmatter(authors_data[0])

    return None


def get_all_authors(metadata: Mapping[str, Any]) -> list[Author]:
    """Get all authors as list of Author objects.

    Parses both 'author' and 'authors' frontmatter fields, combining them
    into a single deduplicated list. Handles string and dict formats.

    Args:
        metadata: Page metadata dict

    Returns:
        List of Author objects (empty list if no authors)
    """
    from bengal.core.author import Author

    result: list[Author] = []
    seen_names: set[str] = set()

    # Process 'author' field (single author)
    author_data = metadata.get("author")
    if author_data:
        author = Author.from_frontmatter(author_data)
        if author and author.name not in seen_names:
            result.append(author)
            seen_names.add(author.name)

    # Process 'authors' field (multiple authors)
    authors_data = metadata.get("authors")
    if authors_data and isinstance(authors_data, list):
        for item in authors_data:
            author = Author.from_frontmatter(item)
            if author and author.name not in seen_names:
                result.append(author)
                seen_names.add(author.name)

    return result


def get_series_info(metadata: Mapping[str, Any]) -> Series | None:
    """Get series info as Series object.

    Parses the 'series' frontmatter field into a structured Series object
    for multi-part content navigation.

    Args:
        metadata: Page metadata dict

    Returns:
        Series object or None if not part of a series
    """
    from bengal.core.series import Series

    series_data = metadata.get("series")
    if not series_data:
        return None

    return Series.from_frontmatter(series_data)


def get_series_neighbor(
    metadata: Mapping[str, Any],
    site: Site | None,
    offset: int,
) -> Page | None:
    """Get neighboring page in series by part offset.

    Args:
        metadata: Page metadata dict
        site: Site instance (for page lookup)
        offset: Part number offset (-1 for prev, +1 for next)

    Returns:
        Neighboring Page or None
    """
    # Get series info from this page
    series_data = metadata.get("series")
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
