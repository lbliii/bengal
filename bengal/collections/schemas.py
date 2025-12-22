"""
Standard collection schemas for common content types.

Provides ready-to-use dataclass schemas for blog posts, documentation pages,
API references, tutorials, and changelogs. Use these directly or extend them
for custom content types.

Available Schemas:
    - :class:`BlogPost` (alias: ``Post``): Blog posts with date, author, tags
    - :class:`DocPage` (alias: ``Doc``): Documentation with weight, category, toc
    - :class:`APIReference` (alias: ``API``): API endpoint documentation
    - :class:`Tutorial`: Guides with difficulty, duration, prerequisites
    - :class:`Changelog`: Release notes with version, breaking changes

Quick Start:
    Use schemas directly in your collections:

    >>> from bengal.collections import define_collection
    >>> from bengal.collections.schemas import BlogPost, DocPage
    >>>
    >>> collections = {
    ...     "blog": define_collection(schema=BlogPost, directory="content/blog"),
    ...     "docs": define_collection(schema=DocPage, directory="content/docs"),
    ... }

Extending Schemas:
    Create custom schemas by subclassing:

    >>> from dataclasses import dataclass
    >>> from bengal.collections.schemas import BlogPost
    >>>
    >>> @dataclass
    ... class MyBlogPost(BlogPost):
    ...     '''Extended blog post with custom fields.'''
    ...     series: str | None = None
    ...     reading_time: int | None = None

Custom Schemas:
    For complete control, define your own dataclass:

    >>> from dataclasses import dataclass, field
    >>> from datetime import datetime
    >>>
    >>> @dataclass
    ... class Product:
    ...     name: str
    ...     price: float
    ...     sku: str
    ...     in_stock: bool = True
    ...     categories: list[str] = field(default_factory=list)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BlogPost:
    """
    Standard schema for blog posts.

    Provides common fields for blog content including publication metadata,
    authorship, and categorization.

    Attributes:
        title: Post title displayed in listings and page header. **Required.**
        date: Publication date used for sorting and display. **Required.**
            Accepts ISO 8601 strings (e.g., ``"2025-01-15"``) or datetime objects.
        author: Post author name. Defaults to ``"Anonymous"``.
        tags: List of tags for categorization and filtering.
        draft: If ``True``, page is excluded from production builds.
        description: Short description for meta tags, social sharing, and listings.
        image: Featured image path (relative to assets) or absolute URL.
        excerpt: Manual excerpt. If not set, Bengal auto-generates from content.

    Example:
        Frontmatter for a blog post:

        .. code-block:: yaml

            ---
            title: Getting Started with Bengal
            date: 2025-01-15
            author: Jane Doe
            tags: [tutorial, beginner]
            description: Learn how to build your first Bengal site
            ---
    """

    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    description: str | None = None
    image: str | None = None
    excerpt: str | None = None


@dataclass
class DocPage:
    """
    Standard schema for documentation pages.

    Optimized for technical documentation with navigation ordering,
    categorization, and version tracking.

    Attributes:
        title: Page title. **Required.**
        weight: Sort order within section. Lower values appear first.
            Defaults to ``0``.
        category: Category for grouping in navigation (e.g., ``"Reference"``).
        tags: List of tags for cross-referencing and filtering.
        toc: Whether to show the table of contents. Defaults to ``True``.
        description: Page description for meta tags and search results.
        deprecated: If ``True``, displays a deprecation warning banner.
        since: Version when the documented feature was introduced
            (e.g., ``"1.2.0"``).

    Example:
        Frontmatter for a documentation page:

        .. code-block:: yaml

            ---
            title: Configuration Reference
            weight: 10
            category: Reference
            toc: true
            since: "1.0.0"
            ---
    """

    title: str
    weight: int = 0
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    toc: bool = True
    description: str | None = None
    deprecated: bool = False
    since: str | None = None


@dataclass
class APIReference:
    """
    Standard schema for API reference documentation.

    Designed for REST API endpoint documentation with HTTP method,
    authentication, and rate limiting metadata.

    Attributes:
        title: Human-readable name for the endpoint. **Required.**
        endpoint: API endpoint path (e.g., ``"/api/v1/users"``). **Required.**
        method: HTTP method. Defaults to ``"GET"``. Common values:
            ``"GET"``, ``"POST"``, ``"PUT"``, ``"PATCH"``, ``"DELETE"``.
        version: API version string. Defaults to ``"v1"``.
        deprecated: If ``True``, marks the endpoint as deprecated.
        auth_required: Whether authentication is required. Defaults to ``True``.
        rate_limit: Rate limit description (e.g., ``"100 req/min"``).
        description: Endpoint description for listings and meta tags.

    Example:
        Frontmatter for an API endpoint:

        .. code-block:: yaml

            ---
            title: List Users
            endpoint: /api/v1/users
            method: GET
            version: v1
            auth_required: true
            rate_limit: 100 req/min
            ---
    """

    title: str
    endpoint: str
    method: str = "GET"
    version: str = "v1"
    deprecated: bool = False
    auth_required: bool = True
    rate_limit: str | None = None
    description: str | None = None


@dataclass
class Changelog:
    """
    Standard schema for changelog entries.

    Designed for release notes and version history, with support for
    semantic versioning and breaking change indicators.

    Attributes:
        title: Release title (e.g., ``"v1.2.0"`` or ``"Version 1.2.0"``).
            **Required.**
        date: Release date. **Required.** Accepts ISO 8601 strings or datetime.
        version: Semantic version string (e.g., ``"1.2.0"``). Optional but
            recommended for automated version tracking.
        breaking: If ``True``, indicates the release contains breaking changes.
        draft: If ``True``, the release is not yet published.
        summary: Short release summary for listings and feeds.

    Example:
        Frontmatter for a changelog entry:

        .. code-block:: yaml

            ---
            title: Version 1.2.0
            date: 2025-01-15
            version: 1.2.0
            breaking: false
            summary: New features and bug fixes
            ---
    """

    title: str
    date: datetime
    version: str | None = None
    breaking: bool = False
    draft: bool = False
    summary: str | None = None


@dataclass
class Tutorial:
    """
    Standard schema for tutorial and guide pages.

    Designed for step-by-step learning content with difficulty levels,
    time estimates, and series organization.

    Attributes:
        title: Tutorial title. **Required.**
        difficulty: Skill level. Recommended values: ``"beginner"``,
            ``"intermediate"``, ``"advanced"``.
        duration: Estimated completion time (e.g., ``"30 minutes"``).
        prerequisites: List of prerequisite knowledge or tutorials.
        tags: List of tags for categorization and filtering.
        series: Name of the tutorial series this belongs to.
        order: Position within the series (1, 2, 3, ...). Used for
            navigation ordering.

    Example:
        Frontmatter for a tutorial:

        .. code-block:: yaml

            ---
            title: Building Your First Site
            difficulty: beginner
            duration: 30 minutes
            prerequisites:
              - Python basics
              - Command line familiarity
            series: Getting Started
            order: 1
            ---
    """

    title: str
    difficulty: str | None = None
    duration: str | None = None
    prerequisites: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    series: str | None = None
    order: int | None = None


# Convenience aliases for shorter imports
Post = BlogPost  #: Alias for :class:`BlogPost`
Doc = DocPage  #: Alias for :class:`DocPage`
API = APIReference  #: Alias for :class:`APIReference`
