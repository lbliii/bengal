"""
Standard collection schemas for common content types.

Provides ready-to-use schemas for blog posts, documentation pages,
and API references. Users can import and use these directly or
as a starting point for custom schemas.

Usage:
    from bengal.collections import define_collection
    from bengal.collections.schemas import BlogPost, DocPage

    collections = {
        "blog": define_collection(schema=BlogPost, directory="content/blog"),
        "docs": define_collection(schema=DocPage, directory="content/docs"),
    }

Or extend standard schemas:
    from dataclasses import dataclass, field
    from bengal.collections.schemas import BlogPost

    @dataclass
    class MyBlogPost(BlogPost):
        '''Extended blog post with custom fields.'''
        series: str | None = None
        reading_time: int | None = None
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BlogPost:
    """
    Standard schema for blog posts.

    Required:
        title: Post title (displayed in listings and page header)
        date: Publication date (used for sorting and display)

    Optional:
        author: Post author (defaults to "Anonymous")
        tags: List of tags for categorization
        draft: If True, page excluded from production builds
        description: Short description for meta tags and listings
        image: Featured image path (relative to assets or absolute URL)
        excerpt: Manual excerpt (auto-generated from content if not set)

    Example frontmatter:
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

    Required:
        title: Page title

    Optional:
        weight: Sort order within section (lower = earlier, default 0)
        category: Category for grouping in navigation
        tags: List of tags for cross-referencing
        toc: Whether to show table of contents (default True)
        description: Page description for meta tags
        deprecated: Mark page as deprecated (shows warning banner)
        since: Version when feature was introduced (e.g., "1.2.0")

    Example frontmatter:
        ---
        title: Configuration Reference
        weight: 10
        category: Reference
        toc: true
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

    Required:
        title: API endpoint or method name
        endpoint: API endpoint path (e.g., "/api/v1/users")

    Optional:
        method: HTTP method (default "GET")
        version: API version (default "v1")
        deprecated: Mark endpoint as deprecated
        auth_required: Whether authentication is required (default True)
        rate_limit: Rate limit description (e.g., "100 req/min")
        description: Endpoint description

    Example frontmatter:
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

    Required:
        title: Release title (e.g., "v1.2.0" or "Version 1.2.0")
        date: Release date

    Optional:
        version: Semantic version string
        breaking: Whether this release has breaking changes
        draft: If True, not published yet
        summary: Short release summary

    Example frontmatter:
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
    Standard schema for tutorial/guide pages.

    Required:
        title: Tutorial title

    Optional:
        difficulty: Skill level (beginner, intermediate, advanced)
        duration: Estimated completion time (e.g., "30 minutes")
        prerequisites: List of prerequisite knowledge/tutorials
        tags: List of tags
        series: Name of tutorial series this belongs to
        order: Order within series (1, 2, 3, ...)

    Example frontmatter:
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
    difficulty: str | None = None  # beginner, intermediate, advanced
    duration: str | None = None
    prerequisites: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    series: str | None = None
    order: int | None = None


# Aliases for convenience
Post = BlogPost
Doc = DocPage
API = APIReference

