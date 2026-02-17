"""
Blog view filters for templates.

Provides normalized PostView dataclass and `posts` filter to simplify
blog template development. Handles the defensive chaining and fallback
logic that theme developers would otherwise need to implement.

Example:
    {% for post in posts | posts %}
      <h3><a href="{{ post.href }}">{{ post.title }}</a></h3>
      {% if post.image %}<img src="{{ post.image }}">{% end %}
      <time>{{ post.date | dateformat }}</time>
      <span>{{ post.reading_time }} min read</span>
    {% end %}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment


@dataclass(frozen=True, slots=True)
class PostView:
    """
    Normalized view of a blog post for templates.

    Consolidates metadata extraction with fallback logic so templates
    can access properties directly without defensive chaining.

    Attributes:
        title: Post title (defaults to 'Untitled')
        href: URL to the post (includes baseurl when configured)
        path: Site-relative path without baseurl (use for internal links)
        date: Publication date (None if not set)
        image: Featured image URL (from metadata.image or metadata.cover)
        description: Post description (from metadata.description or excerpt)
        excerpt: Raw excerpt text
        author: Author name
        author_avatar: Author avatar URL
        author_title: Author title/role
        reading_time: Estimated reading time in minutes
        word_count: Total word count
        tags: Tuple of tag names
        featured: Whether post is featured
        draft: Whether post is a draft
        updated: Last updated date (None if not set)
        excerpt_words: Max words for card excerpt (None = use config default)

    """

    title: str
    href: str
    path: str
    date: datetime | None
    image: str
    description: str
    excerpt: str
    excerpt_words: int | None
    author: str
    author_avatar: str
    author_title: str
    reading_time: int
    word_count: int
    tags: tuple[str, ...]
    featured: bool
    draft: bool
    updated: datetime | None

    @classmethod
    def from_page(cls, page: Any) -> PostView:
        """
        Create a PostView from a Page object.

        Handles all the defensive access patterns:
        - metadata.image with cover fallback
        - metadata.description with excerpt fallback
        - Author info from metadata
        - Reading time and word count from page properties

        Args:
            page: Page object (or dict-like) to extract from

        Returns:
            Normalized PostView instance
        """
        # Get metadata safely
        metadata = getattr(page, "metadata", None) or {}
        meta = metadata if hasattr(metadata, "get") else {}

        # Get params (alternative metadata location)
        params = getattr(page, "params", None) or {}
        if not hasattr(params, "get"):
            params = {}

        # Extract with fallbacks
        title = getattr(page, "title", None) or "Untitled"
        href = getattr(page, "href", None) or "#"
        path = getattr(page, "_path", None) or href or "#"
        date = getattr(page, "date", None)

        # Image: try metadata.image, then metadata.cover, then params
        image = (
            meta.get("image")
            or meta.get("cover")
            or params.get("image")
            or params.get("cover")
            or ""
        )

        # Description: try metadata.description, then page excerpt (strip HTML when using excerpt)
        excerpt = getattr(page, "excerpt", None) or ""
        raw_desc = meta.get("description") or params.get("description") or excerpt or ""
        if raw_desc and raw_desc == excerpt:
            from bengal.core.utils.text import strip_html

            description = strip_html(raw_desc)
        else:
            description = raw_desc

        # Author info: resolve slug from site.data.authors when params.author is set
        author_slug = params.get("author") or meta.get("params", {}).get("author") or ""
        author_data: dict[str, Any] = {}
        if author_slug and _site_ref:
            try:
                data = getattr(_site_ref, "data", None) or {}
                authors_registry = data.get("authors") if hasattr(data, "get") else {}
                author_data = authors_registry.get(author_slug, {}) if author_slug else {}
            except AttributeError, TypeError, KeyError:
                pass
        author = author_data.get("name") or meta.get("author") or params.get("author") or ""
        author_avatar = (
            author_data.get("avatar")
            or meta.get("author_avatar")
            or params.get("author_avatar")
            or ""
        )
        author_title = (
            author_data.get("title")
            or author_data.get("company")
            or meta.get("author_title")
            or params.get("author_title")
            or ""
        )

        # Reading metrics (from page computed properties; coerce to int for template comparisons)
        rt = getattr(page, "reading_time", None) or 0
        wc = getattr(page, "word_count", None) or 0
        try:
            reading_time = int(rt)
        except (TypeError, ValueError):
            reading_time = 0
        try:
            word_count = int(wc)
        except (TypeError, ValueError):
            word_count = 0

        # Tags
        tags_raw = getattr(page, "tags", None) or []
        tags = tuple(str(t) for t in tags_raw) if tags_raw else ()

        # Flags
        featured = bool(meta.get("featured") or params.get("featured"))
        draft = bool(getattr(page, "draft", False))

        # Updated date
        updated = meta.get("updated") or params.get("updated")

        # Excerpt words: per-article override (None = use config in template)
        ew = meta.get("excerpt_words") or params.get("excerpt_words")
        if ew is not None:
            try:
                excerpt_words = int(ew)
            except (TypeError, ValueError):
                excerpt_words = None
        else:
            excerpt_words = None

        return cls(
            title=title,
            href=href,
            path=path,
            date=date,
            image=image,
            description=description,
            excerpt=excerpt,
            author=author,
            author_avatar=author_avatar,
            author_title=author_title,
            reading_time=reading_time,
            word_count=word_count,
            tags=tags,
            featured=featured,
            draft=draft,
            updated=updated,
            excerpt_words=excerpt_words,
        )


def posts_filter(pages: Any) -> list[PostView]:
    """
    Convert a list of pages to normalized PostView objects.

    Args:
        pages: List of Page objects or iterable

    Returns:
        List of PostView objects

    Example:
        {% for post in posts | posts %}
          {{ post.title }} - {{ post.reading_time }} min
        {% end %}

    """
    if not pages:
        return []

    result = []
    for page in pages:
        try:
            result.append(PostView.from_page(page))
        except Exception:
            # Skip pages that can't be converted
            continue

    return result


def post_view_filter(page: Any) -> PostView | None:
    """
    Convert a single page to a PostView.

    Args:
        page: Single Page object

    Returns:
        PostView object or None if conversion fails

    Example:
        {% let p = page | post_view %}
        <h1>{{ p.title }}</h1>

    """
    if not page:
        return None

    try:
        return PostView.from_page(page)
    except Exception:
        return None


def featured_posts_filter(pages: Any, limit: int = 3) -> list[PostView]:
    """
    Get featured posts from a list of pages.

    Args:
        pages: List of Page objects
        limit: Maximum number of featured posts to return

    Returns:
        List of featured PostView objects

    Example:
        {% for post in posts | featured_posts(3) %}
          {{ post.title }}
        {% end %}

    """
    all_posts = posts_filter(pages)
    featured = [p for p in all_posts if p.featured]
    return featured[:limit]


_site_ref: SiteLike | None = None


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register blog view filters with template environment."""
    global _site_ref
    _site_ref = site
    env.filters.update(
        {
            "posts": posts_filter,
            "post_view": post_view_filter,
            "featured_posts": featured_posts_filter,
        }
    )
