
---
title: "schemas"
type: "python-module"
source_file: "bengal/collections/schemas.py"
line_number: 1
description: "Standard collection schemas for common content types. Provides ready-to-use schemas for blog posts, documentation pages, and API references. Users can import and use these directly or as a starting po..."
---

# schemas
**Type:** Module
**Source:** [View source](bengal/collections/schemas.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[collections](/api/bengal/collections/) ›schemas

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

## Aliases

### `Post` 🔗

:::{info} Alias
This is an alias of [`bengal.collections.schemas.BlogPost`](#blogpost)
:::

Defined at line 217 in `bengal/collections/schemas.py`


### `Doc` 🔗

:::{info} Alias
This is an alias of [`bengal.collections.schemas.DocPage`](#docpage)
:::

Defined at line 218 in `bengal/collections/schemas.py`


### `API` 🔗

:::{info} Alias
This is an alias of [`bengal.collections.schemas.APIReference`](#apireference)
:::

Defined at line 219 in `bengal/collections/schemas.py`

## Classes




### `BlogPost`


:::{note} Also known as
This element has aliases:`Post`:::

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


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`title`
: 

`date`
: 

`author`
: 

`tags`
: 

`draft`
: 

`description`
: 

`image`
: 

`excerpt`
: 

:::










### `DocPage`


:::{note} Also known as
This element has aliases:`Doc`:::

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


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`title`
: 

`weight`
: 

`category`
: 

`tags`
: 

`toc`
: 

`description`
: 

`deprecated`
: 

`since`
: 

:::










### `APIReference`


:::{note} Also known as
This element has aliases:`API`:::

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


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`title`
: 

`endpoint`
: 

`method`
: 

`version`
: 

`deprecated`
: 

`auth_required`
: 

`rate_limit`
: 

`description`
: 

:::










### `Changelog`


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


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`title`
: 

`date`
: 

`version`
: 

`breaking`
: 

`draft`
: 

`summary`
: 

:::










### `Tutorial`


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


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`title`
: 

`difficulty`
: 

`duration`
: 

`prerequisites`
: 

`tags`
: 

`series`
: 

`order`
: 

:::



---
*Generated by Bengal autodoc from `bengal/collections/schemas.py`*

