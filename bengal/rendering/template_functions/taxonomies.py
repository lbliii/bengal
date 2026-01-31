"""
Taxonomy helper functions for templates.

Provides functions for working with tags, categories, and related content,
plus normalized TagView for consistent tag data access in templates.

Architecture:
Core functions (tag_url, related_posts, etc.) are pure Python with no
engine dependencies. Context-dependent functions like tag_url_with_site
are registered via the adapter layer for engine-specific context handling.

Example (TagView):
{% for tag in site | tag_views %}
  <a href="{{ tag.href }}">{{ tag.name }} ({{ tag.count }})</a>
{% end %}

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment

logger = get_logger(__name__)


# Store site reference for filter access
_site_ref: Site | None = None


@dataclass(frozen=True, slots=True)
class TagView:
    """
    Normalized view of a tag for templates.

    Provides consistent access to tag data including name, slug, URL,
    post count, and optional description.

    Attributes:
        name: Display name of the tag
        slug: URL-safe slug
        href: URL to tag page
        count: Number of posts with this tag
        description: Tag description (if available)
        percentage: Percentage of total posts (for tag clouds)

    """

    name: str
    slug: str
    href: str
    count: int
    description: str
    percentage: float

    @classmethod
    def from_taxonomy_entry(
        cls,
        slug: str,
        tag_data: dict[str, Any],
        total_posts: int = 0,
    ) -> TagView:
        """
        Create a TagView from a taxonomy entry.

        Args:
            slug: Tag slug
            tag_data: Tag data dict with 'name', 'pages', etc.
            total_posts: Total number of posts for percentage calculation

        Returns:
            Normalized TagView instance
        """
        name = tag_data.get("name") or slug
        pages = tag_data.get("pages") or []
        count = len(pages) if hasattr(pages, "__len__") else 0
        description = tag_data.get("description") or ""

        # Calculate percentage
        percentage = (count / total_posts * 100) if total_posts > 0 else 0.0

        return cls(
            name=name,
            slug=slug,
            href=f"/tags/{slug}/",
            count=count,
            description=description,
            percentage=round(percentage, 1),
        )


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register taxonomy helper functions with template environment.

    Context-dependent functions (tag_url) are registered via the adapter
    layer which handles engine-specific context mechanisms.

    Non-context functions (related_posts, popular_tags, has_tag) are
    registered directly here.

    """
    global _site_ref
    _site_ref = site

    # Create closures that have access to site
    def related_posts_with_site(page: Any, limit: int = 5) -> list[Any]:
        return related_posts(page, site.pages, limit)

    def popular_tags_with_site(limit: int = 10) -> list[tuple[str, int]]:
        # Transform tags dict to extract pages lists from nested structure
        raw_tags = site.taxonomies.get("tags", {})
        tags_with_pages = {tag_slug: tag_data["pages"] for tag_slug, tag_data in raw_tags.items()}
        return popular_tags(tags_with_pages, limit)

    env.filters.update(
        {
            "has_tag": has_tag,
            "tag_views": tag_views_filter,
            "tag_view": tag_view_filter,
        }
    )

    env.globals.update(
        {
            "related_posts": related_posts_with_site,
            "popular_tags": popular_tags_with_site,
            # Note: tag_url is registered by the adapter layer
            # (bengal.rendering.adapters) which handles @pass_context for Jinja2
        }
    )


def tag_views_filter(
    source: Any, limit: int | None = None, sort_by: str = "count"
) -> list[TagView]:
    """
    Get all tags as normalized TagView objects.

    Args:
        source: Site object or taxonomies dict
        limit: Maximum number of tags to return (None for all)
        sort_by: Sort field ('count', 'name', 'percentage')

    Returns:
        List of TagView objects

    Example:
        {% for tag in site | tag_views %}
          <a href="{{ tag.href }}">{{ tag.name }} ({{ tag.count }})</a>
        {% end %}

        {% for tag in site | tag_views(limit=10, sort_by='name') %}
          {{ tag.name }}
        {% end %}

    """
    # Get taxonomies from site or use directly
    if hasattr(source, "taxonomies"):
        raw_tags = source.taxonomies.get("tags", {})
        total_posts = len(source.pages) if hasattr(source, "pages") else 0
    elif isinstance(source, dict):
        raw_tags = source.get("tags", source)
        total_posts = sum(len(t.get("pages", [])) for t in raw_tags.values())
    else:
        return []

    # Convert to TagViews
    views = []
    for slug, tag_data in raw_tags.items():
        if isinstance(tag_data, dict):
            views.append(TagView.from_taxonomy_entry(slug, tag_data, total_posts))

    # Sort
    if sort_by == "name":
        views.sort(key=lambda t: t.name.lower())
    elif sort_by == "percentage":
        views.sort(key=lambda t: t.percentage, reverse=True)
    else:  # count (default)
        views.sort(key=lambda t: t.count, reverse=True)

    # Apply limit
    if limit is not None:
        views = views[:limit]

    return views


def tag_view_filter(tag_slug: str) -> TagView | None:
    """
    Get a single tag as a TagView by slug.

    Args:
        tag_slug: Tag slug to look up

    Returns:
        TagView object or None if not found

    Example:
        {% let python_tag = 'python' | tag_view %}
        {% if python_tag %}
          <a href="{{ python_tag.href }}">{{ python_tag.name }}</a>
        {% end %}

    """
    if not tag_slug or not _site_ref:
        return None

    raw_tags = _site_ref.taxonomies.get("tags", {})
    tag_data = raw_tags.get(tag_slug)

    if not tag_data or not isinstance(tag_data, dict):
        return None

    total_posts = len(_site_ref.pages) if hasattr(_site_ref, "pages") else 0
    return TagView.from_taxonomy_entry(tag_slug, tag_data, total_posts)


def related_posts(page: Any, all_pages: list[Any] | None = None, limit: int = 5) -> list[Any]:
    """
    Find related posts based on shared tags.

    PERFORMANCE NOTE: This function now uses pre-computed related posts
    for O(1) access. The old O(n²) algorithm is kept as a fallback for
    backward compatibility with custom templates.

    RECOMMENDED: Use `page.related_posts` directly in templates instead
    of calling this function.

    Args:
        page: Current page
        all_pages: All site pages (optional, only needed for fallback)
        limit: Maximum number of related posts

    Returns:
        List of related pages sorted by relevance

    Example (NEW - recommended):
        {% set related = page.related_posts[:3] %}

    Example (OLD - backward compatible):
        {% set related = related_posts(page, limit=3) %}
        {% for post in related %}
          <a href="{{ url_for(post) }}">{{ post.title }}</a>
        {% endfor %}

    """
    page_slug = page.slug if hasattr(page, "slug") else "unknown"

    # FAST PATH: Use pre-computed related posts (O(1))
    if hasattr(page, "related_posts") and page.related_posts:
        logger.debug(
            "related_posts_fast_path",
            page=page_slug,
            precomputed_count=len(page.related_posts),
            limit=limit,
        )
        return page.related_posts[:limit]

    # SLOW PATH: Fallback to runtime computation for backward compatibility
    # (Only happens if related posts weren't pre-computed during build)
    logger.warning(
        "Pre-computed related posts not available, using O(n²) fallback algorithm",
        page=page_slug,
        all_pages=len(all_pages) if all_pages else 0,
        caller="template",
    )

    if all_pages is None:
        # Can't compute without all_pages
        logger.debug("related_posts_no_pages", page=page_slug)
        return []

    if not hasattr(page, "tags") or not page.tags:
        logger.debug("related_posts_no_tags", page=page_slug)
        return []

    import time

    start = time.time()

    page_tags = set(page.tags)
    scored_pages = []

    for other_page in all_pages:
        # Skip the current page
        if other_page == page:
            continue

        # Skip pages without tags
        if not hasattr(other_page, "tags") or not other_page.tags:
            continue

        # Calculate relevance score (number of shared tags)
        other_tags = set(other_page.tags)
        shared_tags = page_tags & other_tags

        if shared_tags:
            score = len(shared_tags)
            scored_pages.append((score, other_page))

    # Sort by score (descending) and return top N
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    result = [page for score, page in scored_pages[:limit]]

    duration_ms = (time.time() - start) * 1000
    logger.debug(
        "related_posts_computed",
        page=page_slug,
        duration_ms=duration_ms,
        candidates=len(scored_pages),
        result_count=len(result),
    )

    return result


def popular_tags(tags_dict: dict[str, list[Any]], limit: int = 10) -> list[tuple[str, int]]:
    """
    Get most popular tags sorted by count.

    Args:
        tags_dict: Dictionary of tag -> pages
        limit: Maximum number of tags

    Returns:
        List of (tag, count) tuples

    Example:
        {% set top_tags = popular_tags(limit=5) %}
        {% for tag, count in top_tags %}
          <a href="{{ tag_url(tag) }}">{{ tag }} ({{ count }})</a>
        {% endfor %}

    """
    if not tags_dict:
        logger.debug("popular_tags_empty", caller="template")
        return []

    # Count pages per tag
    tag_counts = [(tag, len(pages)) for tag, pages in tags_dict.items()]

    # Sort by count (descending)
    tag_counts.sort(key=lambda x: x[1], reverse=True)

    result = tag_counts[:limit]

    logger.debug(
        "popular_tags_computed", total_tags=len(tags_dict), limit=limit, result_count=len(result)
    )

    return result


def tag_url(tag: str) -> str:
    """
    Generate URL for a tag page.

    Uses bengal.utils.text.slugify for tag slug generation.

    Args:
        tag: Tag name

    Returns:
        URL path to tag page

    Example:
        <a href="{{ tag_url('python') }}">Python</a>
        # <a href="/tags/python/">Python</a>

    """
    if not tag:
        return "/tags/"

    # Convert tag to URL-safe slug
    from bengal.utils.primitives.text import slugify

    slug = slugify(tag, unescape_html=False)

    return f"/tags/{slug}/"


def has_tag(page: Any, tag: str) -> bool:
    """
    Check if page has a specific tag.

    Args:
        page: Page to check
        tag: Tag to look for

    Returns:
        True if page has the tag

    Example:
        {% if page | has_tag('tutorial') %}
          <span class="badge">Tutorial</span>
        {% endif %}

    """
    if not hasattr(page, "tags") or not page.tags:
        return False

    # Case-insensitive comparison (convert to str in case YAML parsed as int)
    # Filter out None tags (YAML parses 'null' as None)
    page_tags = [str(t).lower() for t in page.tags if t is not None]
    return str(tag).lower() in page_tags
