"""
Author view filters for templates.

Provides normalized AuthorView dataclass and `author_view` filter to simplify
author page development. Handles merging data from multiple sources:
- site.data.authors (author registry)
- Page params/metadata
- Social link extraction

Example:
    {% let author = page | author_view(site) %}
    <h1>{{ author.name }}</h1>
    <p>{{ author.bio }}</p>
    {% if author.github %}
      <a href="https://github.com/{{ author.github }}">GitHub</a>
    {% end %}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment


@dataclass(frozen=True, slots=True)
class AuthorView:
    """
    Normalized view of an author for templates.

    Consolidates author data from multiple sources:
    - site.data.authors registry
    - Page metadata/params
    - Social link extraction

    Attributes:
        name: Author display name
        key: Author key/slug for lookups
        bio: Author biography
        avatar: Avatar image URL
        company: Company/organization
        location: Geographic location
        title: Job title/role
        twitter: Twitter handle (without @)
        github: GitHub username
        linkedin: LinkedIn profile slug
        website: Personal website URL
        email: Email address
        href: URL to author page
        post_count: Number of posts by author

    """

    name: str
    key: str
    bio: str
    avatar: str
    company: str
    location: str
    title: str
    twitter: str
    github: str
    linkedin: str
    website: str
    email: str
    href: str
    post_count: int

    @classmethod
    def from_page(
        cls,
        page: Any,
        site_data: dict[str, Any] | None = None,
        author_index: dict[str, list[Any]] | None = None,
    ) -> AuthorView:
        """
        Create an AuthorView from an author page.

        Merges data from:
        1. site.data.authors[author_key] (if available)
        2. Page metadata/params
        3. Social links array (if present)

        Args:
            page: Author page object
            site_data: site.data.authors dict (optional)
            author_index: site.indexes.author dict for post counts (optional)

        Returns:
            Normalized AuthorView instance
        """
        # Get params and metadata safely
        params = getattr(page, "params", None) or {}
        if not hasattr(params, "get"):
            params = {}

        metadata = getattr(page, "metadata", None) or {}
        if not hasattr(metadata, "get"):
            metadata = {}

        # Determine author key
        author_key = (
            params.get("author_name")
            or metadata.get("author_name")
            or getattr(page, "title", None)
            or ""
        )

        # Get author data from registry
        author_data: dict[str, Any] = {}
        if site_data and author_key and author_key in site_data:
            author_data = site_data.get(author_key, {})

        # Merge sources (registry > metadata > params)
        name = (
            author_data.get("name")
            or metadata.get("name")
            or getattr(page, "title", None)
            or "Unknown Author"
        )

        bio = author_data.get("bio") or metadata.get("bio") or params.get("bio") or ""

        avatar = author_data.get("avatar") or metadata.get("avatar") or params.get("avatar") or ""

        company = author_data.get("company") or metadata.get("company") or ""
        location = author_data.get("location") or metadata.get("location") or ""
        title = author_data.get("title") or metadata.get("title") or ""

        # Social links - check both nested social dict and direct properties
        social = author_data.get("social") or metadata.get("social") or params.get("social") or {}
        if not hasattr(social, "get"):
            social = {}

        # Extract social handles (check registry, then metadata, then social dict)
        twitter = _extract_handle(
            author_data.get("twitter") or metadata.get("twitter") or social.get("twitter") or ""
        )
        github = _extract_github(
            author_data.get("github") or metadata.get("github") or social.get("github") or ""
        )
        linkedin = social.get("linkedin") or ""
        website = social.get("website") or author_data.get("website") or ""
        email = social.get("email") or author_data.get("email") or ""

        # Check links array for additional social links
        links = author_data.get("links") or []
        for link in links:
            if not isinstance(link, dict):
                continue
            link_url = link.get("href") or link.get("url") or ""
            if "github.com" in link_url and not github:
                github = link_url.replace("https://github.com/", "").strip("/")
            elif "twitter.com" in link_url and not twitter:
                twitter = link_url.replace("https://twitter.com/", "").strip("/")
            elif "linkedin.com" in link_url and not linkedin:
                linkedin = link_url.replace("https://linkedin.com/in/", "").strip("/")

        # Get page href
        href = getattr(page, "href", None) or f"/authors/{author_key}/"

        # Get post count from index
        post_count = 0
        if author_index and author_key:
            posts = author_index.get(author_key, [])
            post_count = len(posts) if posts else 0

        return cls(
            name=name,
            key=author_key,
            bio=bio,
            avatar=avatar,
            company=company,
            location=location,
            title=title,
            twitter=twitter,
            github=github,
            linkedin=linkedin,
            website=website,
            email=email,
            href=href,
            post_count=post_count,
        )

    @classmethod
    def from_data(
        cls,
        author_key: str,
        author_data: dict[str, Any],
        author_index: dict[str, list[Any]] | None = None,
    ) -> AuthorView:
        """
        Create an AuthorView from author registry data.

        Args:
            author_key: Author key/slug
            author_data: Author dict from site.data.authors
            author_index: site.indexes.author for post counts

        Returns:
            Normalized AuthorView instance
        """
        social = author_data.get("social") or {}
        if not hasattr(social, "get"):
            social = {}

        # Extract social handles
        twitter = _extract_handle(author_data.get("twitter") or social.get("twitter") or "")
        github = _extract_github(author_data.get("github") or social.get("github") or "")
        linkedin = social.get("linkedin") or ""
        website = social.get("website") or author_data.get("website") or ""
        email = social.get("email") or author_data.get("email") or ""

        # Check links array
        links = author_data.get("links") or []
        for link in links:
            if not isinstance(link, dict):
                continue
            link_url = link.get("href") or link.get("url") or ""
            if "github.com" in link_url and not github:
                github = link_url.replace("https://github.com/", "").strip("/")
            elif "twitter.com" in link_url and not twitter:
                twitter = link_url.replace("https://twitter.com/", "").strip("/")
            elif "linkedin.com" in link_url and not linkedin:
                linkedin = link_url.replace("https://linkedin.com/in/", "").strip("/")

        # Get post count
        post_count = 0
        if author_index and author_key:
            posts = author_index.get(author_key, [])
            post_count = len(posts) if posts else 0

        return cls(
            name=author_data.get("name") or author_key,
            key=author_key,
            bio=author_data.get("bio") or "",
            avatar=author_data.get("avatar") or "",
            company=author_data.get("company") or "",
            location=author_data.get("location") or "",
            title=author_data.get("title") or "",
            twitter=twitter,
            github=github,
            linkedin=linkedin,
            website=website,
            email=email,
            href=f"/authors/{author_key}/",
            post_count=post_count,
        )


def _extract_handle(value: str) -> str:
    """Extract handle from Twitter username or URL."""
    if not value:
        return ""
    # Remove @ prefix
    value = value.lstrip("@")
    # Extract from URL
    if "twitter.com" in value:
        value = value.replace("https://twitter.com/", "").replace("http://twitter.com/", "")
    return value.strip("/")


def _extract_github(value: str) -> str:
    """Extract username from GitHub username or URL."""
    if not value:
        return ""
    if "github.com" in value:
        value = value.replace("https://github.com/", "").replace("http://github.com/", "")
    return value.strip("/")


# Store site reference for filter access
_site_ref: SiteLike | None = None


def _get_site_enrichment() -> tuple[dict[str, Any] | None, dict[str, list[Any]] | None]:
    """Extract author enrichment data from the module-level site reference.

    Isolates all ``_site_ref`` access so that a stale or partially-torn-down
    site (common when ``pytest-xdist`` reuses workers) never poisons callers.

    Returns:
        (site_data, author_index) — both ``None`` when unavailable.
    """
    if not _site_ref:
        return None, None

    site_data = None
    author_index = None
    try:
        data = getattr(_site_ref, "data", None) or {}
        site_data = data.get("authors") if hasattr(data, "get") else None
    except (AttributeError, TypeError, KeyError):
        pass
    try:
        indexes = getattr(_site_ref, "indexes", None) or {}
        author_index = indexes.get("author") if hasattr(indexes, "get") else None
    except (AttributeError, TypeError, KeyError):
        pass
    return site_data, author_index


def author_view_filter(page: Any) -> AuthorView | None:
    """
    Convert an author page to an AuthorView.

    Uses site.data.authors and site.indexes.author for enrichment.

    Args:
        page: Author page object

    Returns:
        AuthorView object or None if conversion fails

    Example:
        {% let author = page | author_view %}
        <h1>{{ author.name }}</h1>

    """
    if not page:
        return None

    try:
        site_data, author_index = _get_site_enrichment()
        return AuthorView.from_page(page, site_data, author_index)
    except (AttributeError, TypeError, KeyError, ValueError):
        return None


def authors_filter(pages: Any) -> list[AuthorView]:
    """
    Convert a list of author pages to AuthorView objects.

    Args:
        pages: List of author Page objects

    Returns:
        List of AuthorView objects

    Example:
        {% for author in pages | authors %}
          <a href="{{ author.href }}">{{ author.name }}</a>
        {% end %}

    """
    if not pages:
        return []

    site_data, author_index = _get_site_enrichment()

    result = []
    for page in pages:
        try:
            result.append(AuthorView.from_page(page, site_data, author_index))
        except (AttributeError, TypeError, KeyError, ValueError):
            continue

    return result


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register author view filters with template environment."""
    global _site_ref
    _site_ref = site

    env.filters.update(
        {
            "author_view": author_view_filter,
            "authors": authors_filter,
        }
    )
