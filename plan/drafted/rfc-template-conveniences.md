# RFC: Template Convenience Functions for Blog & Content Sites

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Subsystems**: core, rendering/template_functions, cache/indexes

---

## Executive Summary

Add a suite of template convenience functions, dataclasses, and page properties that simplify common blog and content site patterns. These additions reduce boilerplate in templates and enable polished author pages, archive views, series navigation, and social sharing with minimal configuration.

**Key Additions**:
- Author dataclass and page properties
- Date grouping helpers for archive pages
- Series/multi-part content support
- Social share URL generators
- Featured posts accessor
- Content age helpers
- Section statistics

---

## Problem Statement

While Bengal provides 80+ template functions, several common blog patterns require verbose workarounds:

| Pattern | Current Approach | Pain Point |
|---------|-----------------|------------|
| Author pages | `site.indexes.author.get(name)` + manual metadata | No structured author data |
| Archive by year | Manual Jinja loops with dict updates | Verbose, error-prone |
| Multi-part series | `weight` + section workaround | No series navigation |
| Social sharing | External JS or manual URL building | No built-in helpers |
| Featured posts | `site.pages \| where('featured', true)` | Verbose, repeated pattern |
| Content freshness | `page is outdated(90)` boolean only | No numeric age access |

These gaps force template authors to write repetitive boilerplate or rely on external solutions.

---

## Goals

1. **Reduce template complexity** - Common patterns should be one-liners
2. **Maintain type safety** - Use dataclasses with proper types
3. **Preserve performance** - Pre-compute where possible, cache results
4. **Stay backward compatible** - New features don't break existing templates
5. **Follow Bengal conventions** - Consistent with existing API patterns

## Non-Goals

- Complex content recommendation algorithms (beyond tag-based)
- Real-time analytics or user tracking
- Third-party API integrations (beyond URL generation)
- Full CMS features (comments, user accounts)

---

## Design Overview

### New Dataclasses

```
bengal/core/
├── author.py          # Author dataclass
└── series.py          # Series dataclass
```

### New Template Functions

```
bengal/rendering/template_functions/
├── share.py           # Social sharing URLs
├── dates.py           # + group_by_year, group_by_month, age helpers
└── collections.py     # + archive_years
```

### New Page Properties

```python
# Page properties (in computed.py or new mixin)
page.author            # Author | None
page.authors           # list[Author]
page.age_days          # int
page.series            # Series | None
page.series_position   # int | None
page.prev_in_series    # Page | None
page.next_in_series    # Page | None
```

### New Site Properties

```python
# Site properties
site.featured_posts    # list[Page] (cached)
site.authors           # dict[str, Author] (cached)
```

---

## Detailed Design

### 1. Author Support

#### 1.1 Author Dataclass

```python
# bengal/core/author.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Author:
    """
    Structured author data with social links.

    Extracted from frontmatter during discovery:
        author: "Jane Smith"

        # Or with details:
        author:
          name: "Jane Smith"
          email: "jane@example.com"
          bio: "Python enthusiast and tech writer"
          avatar: "/images/authors/jane.jpg"
          twitter: "janesmith"
          github: "janesmith"

    Template Usage:
        {{ page.author.name }}
        {{ page.author.avatar | default('/images/default-avatar.png') }}
        <a href="{{ author_url(page.author) }}">All posts</a>
    """
    name: str
    slug: str = ""  # URL-safe slug, auto-generated if not provided
    email: str | None = None
    bio: str | None = None
    avatar: str | None = None

    # Social links
    twitter: str | None = None
    github: str | None = None
    linkedin: str | None = None
    mastodon: str | None = None
    website: str | None = None

    # Extensible for custom social links
    social: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate slug if not provided."""
        if not self.slug:
            from bengal.utils.text import slugify
            self.slug = slugify(self.name)

    @classmethod
    def from_frontmatter(cls, data: str | dict) -> Author:
        """
        Create Author from frontmatter data.

        Supports:
            author: "Jane Smith"  # String
            author:               # Dict with details
              name: "Jane Smith"
              bio: "..."
        """
        if isinstance(data, str):
            return cls(name=data)

        if isinstance(data, dict):
            return cls(
                name=data.get("name", "Unknown"),
                slug=data.get("slug", ""),
                email=data.get("email"),
                bio=data.get("bio"),
                avatar=data.get("avatar"),
                twitter=data.get("twitter"),
                github=data.get("github"),
                linkedin=data.get("linkedin"),
                mastodon=data.get("mastodon"),
                website=data.get("website"),
                social=data.get("social", {}),
            )

        return cls(name="Unknown")
```

#### 1.2 Page Author Properties

```python
# In bengal/core/page/computed.py or new author_mixin.py

@property
def author(self) -> Author | None:
    """
    Get primary author as Author object.

    Returns:
        Author object or None if no author specified

    Example:
        {% if page.author %}
          <span class="author">{{ page.author.name }}</span>
        {% endif %}
    """
    from bengal.core.author import Author

    # Check 'author' field first
    author_data = self.metadata.get("author")
    if author_data:
        return Author.from_frontmatter(author_data)

    # Fall back to first of 'authors' list
    authors_data = self.metadata.get("authors")
    if authors_data and isinstance(authors_data, list) and authors_data:
        return Author.from_frontmatter(authors_data[0])

    return None


@property
def authors(self) -> list[Author]:
    """
    Get all authors as list of Author objects.

    Returns:
        List of Author objects (may be empty)

    Example:
        {% for author in page.authors %}
          <span class="author">{{ author.name }}</span>
        {% endfor %}
    """
    from bengal.core.author import Author

    result = []

    # Single author
    author_data = self.metadata.get("author")
    if author_data:
        result.append(Author.from_frontmatter(author_data))

    # Multiple authors
    authors_data = self.metadata.get("authors")
    if authors_data and isinstance(authors_data, list):
        for author in authors_data:
            result.append(Author.from_frontmatter(author))

    return result
```

#### 1.3 Template Functions

```python
# bengal/rendering/template_functions/authors.py

def register(env: Environment, site: Site) -> None:
    """Register author template functions."""

    def author_url_with_site(author: Author | str) -> str:
        return author_url(author, site)

    def get_author_with_site(name: str) -> Author | None:
        return get_author(name, site)

    env.globals.update({
        "author_url": author_url_with_site,
        "get_author": get_author_with_site,
        "author_posts": lambda name: author_posts(name, site),
    })


def author_url(author: Author | str, site: Site) -> str:
    """
    Generate URL for author archive page.

    Args:
        author: Author object or name string
        site: Site instance

    Returns:
        URL path to author page

    Example:
        <a href="{{ author_url(page.author) }}">All posts by {{ page.author.name }}</a>
    """
    from bengal.utils.text import slugify

    if isinstance(author, str):
        slug = slugify(author)
    else:
        slug = author.slug

    baseurl = site.baseurl or ""
    return f"{baseurl}/authors/{slug}/"


def get_author(name: str, site: Site) -> Author | None:
    """
    Get Author object by name from site's author registry.

    Uses AuthorIndex metadata if available.

    Args:
        name: Author name
        site: Site instance

    Returns:
        Author object or None
    """
    from bengal.core.author import Author

    # Check if we have cached author metadata
    if hasattr(site, "_author_cache") and name in site._author_cache:
        return site._author_cache[name]

    # Build from index if available
    author_index = site.indexes.get("author")
    if author_index:
        metadata = author_index.get_metadata(name)
        if metadata:
            return Author(name=name, **metadata)

    # Fallback to simple Author
    return Author(name=name)


def author_posts(name: str, site: Site) -> list[Page]:
    """
    Get all posts by an author.

    Args:
        name: Author name
        site: Site instance

    Returns:
        List of pages by author, sorted by date (newest first)

    Example:
        {% set posts = author_posts('Jane Smith') %}
    """
    author_index = site.indexes.get("author")
    if not author_index:
        return []

    paths = author_index.get(name)
    if not paths:
        return []

    # Resolve paths to pages
    page_map = site.get_page_path_map()
    pages = [page_map.get(p) for p in paths if page_map.get(p)]

    # Sort by date, newest first
    return sorted(pages, key=lambda p: p.date or datetime.min, reverse=True)
```

#### 1.4 Site Authors Property

```python
# In bengal/core/site/properties.py

@property
def authors(self) -> dict[str, Author]:
    """
    Get all authors across the site.

    Returns:
        Dictionary mapping author name to Author object

    Example:
        {% for name, author in site.authors.items() %}
          <a href="{{ author_url(author) }}">{{ name }}</a>
        {% endfor %}
    """
    if hasattr(self, "_authors_cache"):
        return self._authors_cache

    from bengal.core.author import Author

    authors = {}
    author_index = self.indexes.get("author")

    if author_index:
        for name in author_index.keys():
            metadata = author_index.get_metadata(name)
            authors[name] = Author(name=name, **(metadata or {}))

    self._authors_cache = authors
    return authors
```

---

### 2. Date Grouping Helpers

#### 2.1 Collection Filters

```python
# Add to bengal/rendering/template_functions/collections.py

def group_by_year(pages: list[Any]) -> dict[int, list[Any]]:
    """
    Group pages by publication year.

    Args:
        pages: List of pages with date attribute

    Returns:
        Dictionary mapping year (int) to list of pages

    Example:
        {% set by_year = posts | group_by_year %}
        {% for year, posts in by_year | dictsort(reverse=true) %}
          <h2>{{ year }}</h2>
          {% for post in posts %}...{% endfor %}
        {% endfor %}
    """
    result: dict[int, list[Any]] = {}

    for page in pages:
        date = getattr(page, "date", None)
        if date:
            year = date.year
            if year not in result:
                result[year] = []
            result[year].append(page)

    return result


def group_by_month(pages: list[Any]) -> dict[tuple[int, int], list[Any]]:
    """
    Group pages by publication year and month.

    Args:
        pages: List of pages with date attribute

    Returns:
        Dictionary mapping (year, month) tuple to list of pages

    Example:
        {% set by_month = posts | group_by_month %}
        {% for (year, month), posts in by_month | dictsort(reverse=true) %}
          <h2>{{ month_name(month) }} {{ year }}</h2>
          {% for post in posts %}...{% endfor %}
        {% endfor %}
    """
    result: dict[tuple[int, int], list[Any]] = {}

    for page in pages:
        date = getattr(page, "date", None)
        if date:
            key = (date.year, date.month)
            if key not in result:
                result[key] = []
            result[key].append(page)

    return result


def archive_years(pages: list[Any]) -> list[tuple[int, int]]:
    """
    Get archive years with post counts.

    Args:
        pages: List of pages with date attribute

    Returns:
        List of (year, count) tuples, sorted newest first

    Example:
        {% set years = posts | archive_years %}
        {% for year, count in years %}
          <a href="/archive/{{ year }}/">{{ year }} ({{ count }})</a>
        {% endfor %}
    """
    by_year = group_by_year(pages)
    years = [(year, len(posts)) for year, posts in by_year.items()]
    return sorted(years, key=lambda x: x[0], reverse=True)
```

#### 2.2 Date Utilities

```python
# Add to bengal/rendering/template_functions/dates.py

def days_ago(date: datetime | str | None) -> int:
    """
    Calculate days since a date.

    Args:
        date: Date to calculate from

    Returns:
        Number of days since date (0 if today)

    Example:
        {{ page.date | days_ago }} days ago
    """
    if not date:
        return 0

    if isinstance(date, str):
        from bengal.utils.dates import parse_date
        date = parse_date(date)

    if not isinstance(date, datetime):
        return 0

    return max(0, (datetime.now() - date).days)


def months_ago(date: datetime | str | None) -> int:
    """
    Calculate months since a date.

    Args:
        date: Date to calculate from

    Returns:
        Number of months since date (0 if this month)

    Example:
        {{ page.date | months_ago }} months ago
    """
    if not date:
        return 0

    if isinstance(date, str):
        from bengal.utils.dates import parse_date
        date = parse_date(date)

    if not isinstance(date, datetime):
        return 0

    now = datetime.now()
    return max(0, (now.year - date.year) * 12 + (now.month - date.month))


def month_name(month: int, short: bool = False) -> str:
    """
    Get month name from month number.

    Args:
        month: Month number (1-12)
        short: Return abbreviated name (Jan, Feb, etc.)

    Returns:
        Month name string

    Example:
        {{ 3 | month_name }}        -> "March"
        {{ 3 | month_name(true) }}  -> "Mar"
    """
    import calendar
    if short:
        return calendar.month_abbr[month]
    return calendar.month_name[month]
```

#### 2.3 Page Age Property

```python
# In bengal/core/page/computed.py

@property
def age_days(self) -> int:
    """
    Days since page publication.

    Returns:
        Number of days since page.date (0 if no date or today)

    Example:
        {% if page.age_days > 365 %}
          <span class="badge">📜 Classic</span>
        {% elif page.age_days < 7 %}
          <span class="badge">🆕 New</span>
        {% endif %}
    """
    if not self.date:
        return 0

    from datetime import datetime
    return max(0, (datetime.now() - self.date).days)


@property
def age_months(self) -> int:
    """
    Months since page publication.

    Returns:
        Number of months since page.date (0 if no date or this month)
    """
    if not self.date:
        return 0

    from datetime import datetime
    now = datetime.now()
    return max(0, (now.year - self.date.year) * 12 + (now.month - self.date.month))
```

---

### 3. Series/Multi-Part Content

#### 3.1 Series Dataclass

```python
# bengal/core/series.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


@dataclass
class Series:
    """
    Multi-part content series.

    Frontmatter:
        series: "Building a Blog"
        series_part: 1

    Or with metadata:
        series:
          name: "Building a Blog"
          part: 1
          description: "A complete guide to building a blog with Bengal"

    Template Usage:
        {% if page.series %}
          <nav class="series-nav">
            Part {{ page.series_position }} of {{ page.series.total }}
            {% if page.prev_in_series %}
              <a href="{{ page.prev_in_series.href }}">← Previous</a>
            {% endif %}
          </nav>
        {% endif %}
    """
    name: str
    slug: str = ""
    description: str = ""
    parts: list[Page] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.slug:
            from bengal.utils.text import slugify
            self.slug = slugify(self.name)

    @property
    def total(self) -> int:
        """Total number of parts in series."""
        return len(self.parts)

    def get_position(self, page: Page) -> int | None:
        """Get position of page in series (1-indexed)."""
        for i, p in enumerate(self.parts):
            if p.source_path == page.source_path:
                return i + 1
        return None

    def get_prev(self, page: Page) -> Page | None:
        """Get previous page in series."""
        pos = self.get_position(page)
        if pos and pos > 1:
            return self.parts[pos - 2]
        return None

    def get_next(self, page: Page) -> Page | None:
        """Get next page in series."""
        pos = self.get_position(page)
        if pos and pos < len(self.parts):
            return self.parts[pos]
        return None
```

#### 3.2 Series Index

```python
# bengal/cache/indexes/series_index.py

class SeriesIndex(QueryIndex):
    """
    Index pages by series.

    Frontmatter formats:
        series: "Building a Blog"
        series_part: 1

        # Or with metadata:
        series:
          name: "Building a Blog"
          part: 1

    Template Usage:
        {% set all_series = site.indexes.series.keys() %}
        {% set series_posts = site.indexes.series.get('Building a Blog') %}
    """

    def __init__(self, cache_path: Path):
        super().__init__("series", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract series from page metadata."""
        series = page.metadata.get("series")
        if not series:
            return []

        if isinstance(series, str):
            name = series
            part = page.metadata.get("series_part", 0)
        elif isinstance(series, dict):
            name = series.get("name", "")
            part = series.get("part", 0)
        else:
            return []

        if name:
            return [(name, {"part": part})]

        return []
```

#### 3.3 Page Series Properties

```python
# In bengal/core/page/computed.py

@property
def series(self) -> Series | None:
    """
    Get series this page belongs to.

    Returns:
        Series object or None
    """
    if not self._site:
        return None

    series_data = self.metadata.get("series")
    if not series_data:
        return None

    from bengal.core.series import Series

    # Get series name
    if isinstance(series_data, str):
        name = series_data
        description = ""
    elif isinstance(series_data, dict):
        name = series_data.get("name", "")
        description = series_data.get("description", "")
    else:
        return None

    if not name:
        return None

    # Get all pages in series from index
    series_index = self._site.indexes.get("series")
    if not series_index:
        return None

    paths = series_index.get(name)
    if not paths:
        return None

    # Resolve pages and sort by part number
    page_map = self._site.get_page_path_map()
    pages_with_part = []

    for path in paths:
        page = page_map.get(path)
        if page:
            # Get part number
            part_data = page.metadata.get("series")
            if isinstance(part_data, str):
                part = page.metadata.get("series_part", 0)
            elif isinstance(part_data, dict):
                part = part_data.get("part", 0)
            else:
                part = 0
            pages_with_part.append((part, page))

    # Sort by part number
    pages_with_part.sort(key=lambda x: x[0])
    sorted_pages = [p for _, p in pages_with_part]

    return Series(name=name, description=description, parts=sorted_pages)


@property
def series_position(self) -> int | None:
    """
    Get position in series (1-indexed).

    Returns:
        Position number or None if not in series
    """
    series = self.series
    if series:
        return series.get_position(self)
    return None


@property
def prev_in_series(self) -> Page | None:
    """
    Get previous page in series.

    Returns:
        Previous page or None
    """
    series = self.series
    if series:
        return series.get_prev(self)
    return None


@property
def next_in_series(self) -> Page | None:
    """
    Get next page in series.

    Returns:
        Next page or None
    """
    series = self.series
    if series:
        return series.get_next(self)
    return None
```

---

### 4. Social Share URLs

```python
# bengal/rendering/template_functions/share.py
"""
Social sharing URL generators.

Provides functions to generate share URLs for various platforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register social sharing functions."""
    base_url = site.config.get("baseurl", "")

    def share_url_with_site(
        platform: str,
        page: Any,
        text: str | None = None,
        hashtags: list[str] | None = None,
    ) -> str:
        return share_url(platform, page, base_url, text, hashtags)

    env.globals.update({
        "share_url": share_url_with_site,
    })

    env.filters.update({
        "share_url": lambda page, platform, **kw: share_url_with_site(platform, page, **kw),
    })


def share_url(
    platform: str,
    page: Any,
    base_url: str = "",
    text: str | None = None,
    hashtags: list[str] | None = None,
) -> str:
    """
    Generate share URL for a platform.

    Args:
        platform: Platform name (twitter, facebook, linkedin, reddit, email, hackernews)
        page: Page object with title and href
        base_url: Site base URL
        text: Custom share text (defaults to page title)
        hashtags: List of hashtags (for Twitter)

    Returns:
        Share URL for the platform

    Example:
        <a href="{{ share_url('twitter', page) }}">Share on Twitter</a>
        <a href="{{ page | share_url('facebook') }}">Share on Facebook</a>

        {# With custom text #}
        {{ share_url('twitter', page, text='Check this out!', hashtags=['python', 'web']) }}
    """
    title = text or getattr(page, "title", "")
    href = getattr(page, "href", "")

    # Build full URL
    if href and not href.startswith(("http://", "https://")):
        full_url = base_url.rstrip("/") + "/" + href.lstrip("/")
    else:
        full_url = href

    platform = platform.lower()

    if platform == "twitter" or platform == "x":
        params = {
            "text": title,
            "url": full_url,
        }
        if hashtags:
            params["hashtags"] = ",".join(hashtags)
        return f"https://twitter.com/intent/tweet?{urlencode(params)}"

    elif platform == "facebook":
        params = {"u": full_url}
        return f"https://www.facebook.com/sharer/sharer.php?{urlencode(params)}"

    elif platform == "linkedin":
        params = {
            "url": full_url,
            "title": title,
        }
        return f"https://www.linkedin.com/shareArticle?mini=true&{urlencode(params)}"

    elif platform == "reddit":
        params = {
            "url": full_url,
            "title": title,
        }
        return f"https://www.reddit.com/submit?{urlencode(params)}"

    elif platform == "hackernews" or platform == "hn":
        params = {
            "u": full_url,
            "t": title,
        }
        return f"https://news.ycombinator.com/submitlink?{urlencode(params)}"

    elif platform == "email":
        subject = quote(title)
        body = quote(f"Check out this article: {full_url}")
        return f"mailto:?subject={subject}&body={body}"

    elif platform == "copy":
        # Return just the URL for copy-to-clipboard functionality
        return full_url

    elif platform == "mastodon":
        # Mastodon requires user's instance, so we use a share intent service
        params = {"text": f"{title} {full_url}"}
        return f"https://mastodon.social/share?{urlencode(params)}"

    elif platform == "bluesky":
        params = {"text": f"{title} {full_url}"}
        return f"https://bsky.app/intent/compose?{urlencode(params)}"

    else:
        # Unknown platform - return empty
        return ""


# Convenience functions for direct use
def twitter_share_url(page: Any, base_url: str = "", **kw) -> str:
    """Generate Twitter share URL."""
    return share_url("twitter", page, base_url, **kw)


def facebook_share_url(page: Any, base_url: str = "") -> str:
    """Generate Facebook share URL."""
    return share_url("facebook", page, base_url)


def linkedin_share_url(page: Any, base_url: str = "") -> str:
    """Generate LinkedIn share URL."""
    return share_url("linkedin", page, base_url)
```

---

### 5. Featured Posts Accessor

```python
# In bengal/core/site/properties.py

@property
def featured_posts(self) -> list[Page]:
    """
    Get featured posts across the site.

    Pages are featured if they have 'featured' in tags or
    featured: true in frontmatter.

    Returns:
        List of featured pages, sorted by date (newest first)

    Example:
        {% for post in site.featured_posts[:3] %}
          <article>{{ post.title }}</article>
        {% endfor %}
    """
    if hasattr(self, "_featured_posts_cache"):
        return self._featured_posts_cache

    from datetime import datetime

    featured = []

    for page in self.pages:
        # Check tags
        tags = getattr(page, "tags", []) or []
        if "featured" in tags:
            featured.append(page)
            continue

        # Check metadata
        metadata = getattr(page, "metadata", {}) or {}
        if metadata.get("featured"):
            featured.append(page)

    # Sort by date, newest first
    featured.sort(key=lambda p: getattr(p, "date", None) or datetime.min, reverse=True)

    self._featured_posts_cache = featured
    return featured
```

---

### 6. Section Statistics

```python
# In bengal/core/section.py (add to Section class)

@property
def post_count(self) -> int:
    """
    Number of pages in this section.

    Example:
        {{ section.post_count }} posts in this section
    """
    return len(list(self.pages))


@property
def total_word_count(self) -> int:
    """
    Total word count across all pages in section.

    Example:
        {{ section.total_word_count | number_format }} words total
    """
    total = 0
    for page in self.pages:
        content = getattr(page, "content", "") or ""
        total += len(content.split())
    return total


@property
def date_range(self) -> tuple[datetime | None, datetime | None]:
    """
    Date range of pages in section (oldest, newest).

    Returns:
        Tuple of (oldest_date, newest_date) or (None, None)

    Example:
        {% set oldest, newest = section.date_range %}
        Posts from {{ oldest | dateformat('%Y') }} to {{ newest | dateformat('%Y') }}
    """
    from datetime import datetime

    dates = []
    for page in self.pages:
        date = getattr(page, "date", None)
        if date:
            dates.append(date)

    if not dates:
        return (None, None)

    return (min(dates), max(dates))


@property
def last_updated(self) -> datetime | None:
    """
    Most recent page date in section.

    Example:
        Last updated: {{ section.last_updated | dateformat('%B %d, %Y') }}
    """
    _, newest = self.date_range
    return newest
```

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `bengal/core/author.py` | Author dataclass |
| `bengal/core/series.py` | Series dataclass |
| `bengal/cache/indexes/series_index.py` | Series index for O(1) lookup |
| `bengal/rendering/template_functions/share.py` | Social sharing URLs |
| `bengal/rendering/template_functions/authors.py` | Author template functions |

### Modified Files

| File | Changes |
|------|---------|
| `bengal/core/page/computed.py` | Add `author`, `authors`, `age_days`, `series`, `series_position`, `prev_in_series`, `next_in_series` |
| `bengal/core/site/properties.py` | Add `featured_posts`, `authors` |
| `bengal/core/section.py` | Add `post_count`, `total_word_count`, `date_range`, `last_updated` |
| `bengal/rendering/template_functions/collections.py` | Add `group_by_year`, `group_by_month`, `archive_years` |
| `bengal/rendering/template_functions/dates.py` | Add `days_ago`, `months_ago`, `month_name` |
| `bengal/rendering/template_functions/__init__.py` | Register new modules |
| `bengal/cache/indexes/__init__.py` | Register SeriesIndex |

---

## Implementation Phases

### Phase 1: Quick Wins (2-3 hours)

- [ ] `group_by_year`, `group_by_month`, `archive_years` filters
- [ ] `days_ago`, `months_ago`, `month_name` filters
- [ ] `page.age_days` property
- [ ] `site.featured_posts` property

### Phase 2: Author Support (4-6 hours)

- [ ] `Author` dataclass
- [ ] `page.author`, `page.authors` properties
- [ ] `author_url()`, `get_author()`, `author_posts()` functions
- [ ] `site.authors` property

### Phase 3: Social Sharing (2-3 hours)

- [ ] `share.py` template functions
- [ ] Support for Twitter, Facebook, LinkedIn, Reddit, HN, Email, Mastodon, Bluesky

### Phase 4: Series Support (6-8 hours)

- [ ] `Series` dataclass
- [ ] `SeriesIndex` for O(1) lookup
- [ ] `page.series`, `page.series_position` properties
- [ ] `page.prev_in_series`, `page.next_in_series` navigation

### Phase 5: Section Statistics (2 hours)

- [ ] `section.post_count`
- [ ] `section.total_word_count`
- [ ] `section.date_range`, `section.last_updated`

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/core/test_author.py
def test_author_from_string():
    author = Author.from_frontmatter("Jane Smith")
    assert author.name == "Jane Smith"
    assert author.slug == "jane-smith"

def test_author_from_dict():
    author = Author.from_frontmatter({
        "name": "Jane Smith",
        "twitter": "janesmith",
    })
    assert author.name == "Jane Smith"
    assert author.twitter == "janesmith"


# tests/unit/template_functions/test_collections_extended.py
def test_group_by_year():
    pages = [
        FakePage(date=datetime(2025, 1, 1)),
        FakePage(date=datetime(2025, 6, 1)),
        FakePage(date=datetime(2024, 1, 1)),
    ]
    result = group_by_year(pages)
    assert len(result[2025]) == 2
    assert len(result[2024]) == 1


def test_archive_years():
    pages = [...]  # Similar setup
    result = archive_years(pages)
    assert result[0] == (2025, 2)  # Newest first
    assert result[1] == (2024, 1)


# tests/unit/template_functions/test_share.py
def test_twitter_share_url():
    page = FakePage(title="My Post", href="/posts/my-post/")
    url = share_url("twitter", page, "https://example.com")
    assert "twitter.com/intent/tweet" in url
    assert "text=My+Post" in url
    assert "url=https" in url
```

### Integration Tests

```python
# tests/integration/test_author_pages.py
def test_author_archive_generation(tmp_path):
    """Test that author archive pages are generated correctly."""
    # Create test content with authors
    # Build site
    # Verify author pages exist
    # Verify author posts are listed correctly


# tests/integration/test_series_navigation.py
def test_series_prev_next(tmp_path):
    """Test series prev/next navigation works."""
    # Create 3-part series
    # Build site
    # Verify prev_in_series and next_in_series work
    # Verify series.parts order
```

---

## Migration Path

### Backward Compatibility

All new features are **additive** - no existing templates break:

- `page.author` returns `None` if no author in frontmatter (safe)
- `group_by_year` is a new filter (no conflicts)
- `share_url` is a new global (no conflicts)
- `site.featured_posts` is a new property (no conflicts)

### Feature Flag (Optional)

For cautious rollout, add to `features.yaml`:

```yaml
features:
  template_conveniences:
    author_support: true
    series_support: true
    share_urls: true
    archive_helpers: true
```

---

## Alternatives Considered

### 1. Third-Party Integrations

**Rejected**: Social sharing via AddThis/ShareThis adds external dependencies and tracking.

**Decision**: Built-in URL generators are simpler, faster, and privacy-respecting.

### 2. Complex Related Posts Algorithm

**Rejected**: TF-IDF or ML-based related posts is complex and slow.

**Decision**: Current tag-based algorithm is fast (O(1) pre-computed) and effective for most sites. Can enhance later if needed.

### 3. Author as PageCore Field

**Rejected**: Adding author to PageCore would require cache migration.

**Decision**: Keep author in `page.metadata` and compute `Author` objects on access. Caching via `site._author_cache` if needed.

---

## Success Metrics

1. **Template Simplification**: Archive pages reduced from 15+ lines to 3-5 lines
2. **Author Pages**: Can create author pages with zero custom Python
3. **Series Navigation**: Multi-part content has automatic prev/next
4. **Social Sharing**: Single-line share buttons without external JS
5. **Test Coverage**: >90% coverage on new functions

---

## Open Questions

1. **Should `Author` be cached in PageCore?**
   - Pro: Faster incremental builds
   - Con: Increases cache size, requires migration
   - **Recommendation**: No, compute on access for now

2. **Should series ordering support non-numeric parts?**
   - E.g., `series_part: "introduction"` vs `series_part: 1`
   - **Recommendation**: Support both, numeric first, then by date

3. **Should social share icons be bundled?**
   - Current icon system has Twitter, Facebook, etc.
   - **Recommendation**: Yes, verify icons exist for all supported platforms

---

## Related Work

- **RFC: Blog Layout Quality Parity** - This RFC provides the backend for many features in that RFC
- **AuthorIndex** - Already exists, this RFC builds on it
- **Taxonomy Functions** - `related_posts`, `popular_tags` - Similar patterns
- **Page Navigation** - `page.prev`, `page.next` - Similar approach for series

---

## Appendix: Template Examples

### Archive Page

```jinja
{# Before #}
{% set years = {} %}
{% for post in posts %}
  {% set year = post.date.strftime('%Y') %}
  {% if year not in years %}
    {% set _ = years.update({year: []}) %}
  {% endif %}
  {% set _ = years[year].append(post) %}
{% endfor %}
{% for year in years | sort(reverse=true) %}
  <h2>{{ year }}</h2>
  {% for post in years[year] | sort(attribute='date', reverse=true) %}
    <a href="{{ post.href }}">{{ post.title }}</a>
  {% endfor %}
{% endfor %}

{# After #}
{% for year, posts in posts | group_by_year | dictsort(reverse=true) %}
  <h2>{{ year }}</h2>
  {% for post in posts | sort(attribute='date', reverse=true) %}
    <a href="{{ post.href }}">{{ post.title }}</a>
  {% endfor %}
{% endfor %}
```

### Author Card

```jinja
{# Author card in blog post #}
{% set author = page.author %}
{% if author %}
<aside class="author-card">
  {% if author.avatar %}
    <img src="{{ author.avatar }}" alt="{{ author.name }}" class="author-avatar">
  {% endif %}
  <div class="author-info">
    <a href="{{ author_url(author) }}" class="author-name">{{ author.name }}</a>
    {% if author.bio %}
      <p class="author-bio">{{ author.bio }}</p>
    {% endif %}
    <div class="author-social">
      {% if author.twitter %}
        <a href="https://twitter.com/{{ author.twitter }}">{{ icon('twitter') }}</a>
      {% endif %}
      {% if author.github %}
        <a href="https://github.com/{{ author.github }}">{{ icon('github') }}</a>
      {% endif %}
    </div>
  </div>
</aside>
{% endif %}
```

### Series Navigation

```jinja
{% if page.series %}
<nav class="series-nav" aria-label="Series navigation">
  <div class="series-header">
    <span class="series-label">Part of series:</span>
    <strong>{{ page.series.name }}</strong>
    <span class="series-position">({{ page.series_position }} of {{ page.series.total }})</span>
  </div>

  <div class="series-links">
    {% if page.prev_in_series %}
      <a href="{{ page.prev_in_series.href }}" class="series-prev">
        ← {{ page.prev_in_series.title }}
      </a>
    {% endif %}
    {% if page.next_in_series %}
      <a href="{{ page.next_in_series.href }}" class="series-next">
        {{ page.next_in_series.title }} →
      </a>
    {% endif %}
  </div>

  <details class="series-toc">
    <summary>All parts in this series</summary>
    <ol>
      {% for part in page.series.parts %}
        <li {% if part == page %}class="current"{% endif %}>
          <a href="{{ part.href }}">{{ part.title }}</a>
        </li>
      {% endfor %}
    </ol>
  </details>
</nav>
{% endif %}
```

### Social Share Buttons

```jinja
<div class="share-buttons">
  <a href="{{ share_url('twitter', page, hashtags=['python', 'webdev']) }}"
     target="_blank" rel="noopener" class="share-twitter">
    {{ icon('twitter') }} Tweet
  </a>
  <a href="{{ share_url('linkedin', page) }}"
     target="_blank" rel="noopener" class="share-linkedin">
    {{ icon('linkedin') }} Share
  </a>
  <a href="{{ share_url('email', page) }}" class="share-email">
    {{ icon('email') }} Email
  </a>
  <button onclick="navigator.clipboard.writeText('{{ share_url('copy', page) }}')"
          class="share-copy">
    {{ icon('link') }} Copy Link
  </button>
</div>
```

---

**Version**: 1.0  
**Last Updated**: 2025-12-23  
**Status**: Draft - Ready for Review
