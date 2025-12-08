"""
Taxonomy helper functions for templates.

Provides 4 functions for working with tags, categories, and related content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from jinja2 import pass_context
except Exception:  # pragma: no cover
    from collections.abc import Callable
    from typing import Any, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])

    def pass_context(fn: F) -> F:
        return fn


from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register taxonomy helper functions with Jinja2 environment."""

    # Create closures that have access to site
    def related_posts_with_site(page: Any, limit: int = 5) -> list[Any]:
        return related_posts(page, site.pages, limit)

    def popular_tags_with_site(limit: int = 10) -> list[tuple[str, int]]:
        # Transform tags dict to extract pages lists from nested structure
        raw_tags = site.taxonomies.get("tags", {})
        tags_with_pages = {tag_slug: tag_data["pages"] for tag_slug, tag_data in raw_tags.items()}
        return popular_tags(tags_with_pages, limit)

    @pass_context
    def tag_url_with_site(ctx: Any, tag: str) -> str:
        page = ctx.get("page") if hasattr(ctx, "get") else None
        # Locale-aware prefix for i18n prefix strategy
        i18n = site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))
        lang = getattr(page, "lang", None)
        prefix = ""
        if strategy == "prefix" and lang and (default_in_subdir or lang != default_lang):
            prefix = f"/{lang}"

        # Generate tag URL and apply base URL
        relative_url = f"{prefix}{tag_url(tag)}"

        # Apply base URL prefix if configured
        # Use site.baseurl property which handles config access correctly
        baseurl = site.baseurl or ""
        if baseurl:
            baseurl = baseurl.rstrip("/")
            # Ensure relative_url starts with /
            if not relative_url.startswith("/"):
                relative_url = "/" + relative_url
            # Handle absolute vs path-only base URLs
            if baseurl.startswith(("http://", "https://", "file://")):
                return f"{baseurl}{relative_url}"
            else:
                base_path = "/" + baseurl.lstrip("/")
                return f"{base_path}{relative_url}"

        return relative_url

    env.filters.update(
        {
            "has_tag": has_tag,
        }
    )

    env.globals.update(
        {
            "related_posts": related_posts_with_site,
            "popular_tags": popular_tags_with_site,
            "tag_url": tag_url_with_site,
        }
    )


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
    from bengal.utils.text import slugify

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
    page_tags = [str(t).lower() for t in page.tags]
    return str(tag).lower() in page_tags
