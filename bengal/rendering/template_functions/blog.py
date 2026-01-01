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
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment


@dataclass(frozen=True, slots=True)
class PostView:
    """
    Normalized view of a blog post for templates.

    Consolidates metadata extraction with fallback logic so templates
    can access properties directly without defensive chaining.

    Attributes:
        title: Post title (defaults to 'Untitled')
        href: URL to the post
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
    """

    title: str
    href: str
    date: datetime | None
    image: str
    description: str
    excerpt: str
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
        date = getattr(page, "date", None)

        # Image: try metadata.image, then metadata.cover, then params
        image = (
            meta.get("image")
            or meta.get("cover")
            or params.get("image")
            or params.get("cover")
            or ""
        )

        # Description: try metadata.description, then page excerpt
        excerpt = getattr(page, "excerpt", None) or ""
        description = meta.get("description") or params.get("description") or excerpt or ""

        # Author info
        author = meta.get("author") or params.get("author") or ""
        author_avatar = meta.get("author_avatar") or params.get("author_avatar") or ""
        author_title = meta.get("author_title") or params.get("author_title") or ""

        # Reading metrics (from page computed properties)
        reading_time = getattr(page, "reading_time", None) or 0
        word_count = getattr(page, "word_count", None) or 0

        # Tags
        tags_raw = getattr(page, "tags", None) or []
        tags = tuple(str(t) for t in tags_raw) if tags_raw else ()

        # Flags
        featured = bool(meta.get("featured") or params.get("featured"))
        draft = bool(getattr(page, "draft", False))

        # Updated date
        updated = meta.get("updated") or params.get("updated")

        return cls(
            title=title,
            href=href,
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


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register blog view filters with template environment."""
    env.filters.update(
        {
            "posts": posts_filter,
            "post_view": post_view_filter,
            "featured_posts": featured_posts_filter,
        }
    )
