---
title: Content Collections
nav_title: Collections
description: Validate frontmatter with typed schemas
draft: false
weight: 30
lang: en
tags:
- collections
- schemas
- validation
keywords:
- collections
- schemas
- validation
- frontmatter
- types
category: guide
icon: check-circle
card_color: purple
---
# Content Collections

Define typed schemas for your content to ensure consistency and catch errors early.

## Do I Need This?

No. Collections are optional. Your site works fine without them.

**Use collections when:**

- You want typos caught at build time, not in production
- Multiple people edit content and need guardrails
- You want consistent frontmatter across content types

## Quick Setup

```bash
bengal collections init
```

This creates `collections.py` at your project root. Edit it to uncomment what you need:

```python
from bengal.collections import define_collection, BlogPost, DocPage

collections = {
    "blog": define_collection(schema=BlogPost, directory="blog"),
    "docs": define_collection(schema=DocPage, directory="docs"),
}
```

Done. Build as normal—validation happens automatically.

## Built-in Schemas

Bengal provides schemas for common content types:

| Schema | Alias | Required Fields | Optional Fields |
|--------|-------|-----------------|-----------------|
| `BlogPost` | `Post` | title, date | author, tags, draft, description, image, excerpt |
| `DocPage` | `Doc` | title | weight, category, tags, toc, deprecated, description, since |
| `APIReference` | `API` | title, endpoint | method, version, auth_required, rate_limit, deprecated, description |
| `Tutorial` | — | title | difficulty, duration, prerequisites, series, tags, order |
| `Changelog` | — | title, date | version, breaking, summary, draft |

Import any of these:

```python
from bengal.collections import BlogPost, DocPage, APIReference, Tutorial, Changelog
# Or use short aliases:
from bengal.collections import Post, Doc, API
```

## Custom Schemas

Define your own using Python dataclasses:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class ProjectPage:
    title: str
    status: str  # "active", "completed", "archived"
    started: datetime
    tech_stack: list[str] = field(default_factory=list)
    github_url: Optional[str] = None

collections = {
    "projects": define_collection(
        schema=ProjectPage,
        directory="projects",
    ),
}
```

## Validation Modes

By default, validation **warns** but doesn't fail builds:

```tree
⚠ content/blog/my-post.md
  └─ date: Required field 'date' is missing
```

### Strict Mode

To fail builds on validation errors, add to `bengal.toml`:

```toml
[build]
strict_collections = true
```

### Lenient Mode (Extra Fields)

To allow frontmatter fields not defined in your schema:

```python
define_collection(
    schema=BlogPost,
    directory="blog",
    strict=False,       # Don't reject unknown fields
    allow_extra=True,   # Store extra fields in _extra dict
)
```

With `strict=False`, unknown fields are silently ignored. Add `allow_extra=True` to preserve them in a `_extra` attribute on the validated instance.

## CLI Commands

```bash
# List defined collections and their schemas
bengal collections list

# Validate content without building
bengal collections validate

# Validate specific collection
bengal collections validate --collection blog
```

## Advanced Options

### Custom File Pattern

By default, collections match all markdown files (`**/*.md`). To match specific files:

```python
define_collection(
    schema=BlogPost,
    directory="blog",
    glob="*.md",  # Only top-level, not subdirectories
)
```

## Migration Tips

**Existing site with inconsistent frontmatter?**

1. Start with `strict=False` to allow extra fields
2. Run `bengal collections validate` to find issues
3. Fix content or adjust schema
4. Enable `strict=True` when ready

**Transform legacy field names:**

```python
def migrate_legacy(data: dict) -> dict:
    if "post_title" in data:
        data["title"] = data.pop("post_title")
    return data

collections = {
    "blog": define_collection(
        schema=BlogPost,
        directory="blog",
        transform=migrate_legacy,
    ),
}
```

## Remote Content

Collections work with remote content too. Use a loader instead of a directory:

```python
from bengal.collections import define_collection, DocPage
from bengal.content.sources import github_loader

collections = {
    "api-docs": define_collection(
        schema=DocPage,
        loader=github_loader(repo="myorg/api-docs", path="docs/"),
    ),
}
```

See [Content Sources](/docs/content/sources/) for GitHub, Notion, REST API loaders.

:::{seealso}
- [Content Sources](/docs/content/sources/) — GitHub, Notion, REST API loaders
:::
