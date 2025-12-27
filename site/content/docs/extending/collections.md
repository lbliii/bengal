---
title: Content Collections
description: Define typed schemas for frontmatter validation and IDE support
weight: 30
---

Content collections let you define typed schemas for your content's frontmatter. Bengal validates content against these schemas during discovery, catching errors early and providing IDE autocompletion.

## Quick Start

Create a `collections.py` file in your project root:

```python
from dataclasses import dataclass, field
from datetime import datetime
from bengal.collections import define_collection

@dataclass
class BlogPost:
    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
    draft: bool = False

collections = {
    "blog": define_collection(
        schema=BlogPost,
        directory="content/blog",
    ),
}
```

Now any file in `content/blog/` must have valid frontmatter:

```yaml
---
title: My First Post
date: 2025-01-15
author: Jane Doe
tags: [python, tutorial]
---
```

## Schema Definition

### Using Dataclasses

Define your schema as a Python dataclass:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class DocPage:
    title: str                              # Required
    weight: int = 0                         # Optional with default
    description: str | None = None          # Optional, nullable
    tags: list[str] = field(default_factory=list)  # Mutable default
```

### Field Types

Bengal automatically coerces frontmatter values to these types:

| Type | YAML Example | Notes |
|------|--------------|-------|
| `str` | `title: "Hello"` | Basic string |
| `int` | `weight: 10` | Integer |
| `float` | `rating: 4.5` | Float |
| `bool` | `draft: true` | Boolean |
| `datetime` | `date: 2025-01-15` | ISO date string |
| `date` | `published: 2025-01-15` | Date only |
| `list[str]` | `tags: [a, b, c]` | List of strings |
| `T \| None` | `author: null` | Optional/nullable |

### Nested Schemas

Schemas can contain nested dataclasses:

```python
@dataclass
class Author:
    name: str
    email: str | None = None

@dataclass
class BlogPost:
    title: str
    author: Author  # Nested schema
```

Frontmatter:

```yaml
---
title: My Post
author:
  name: Jane Doe
  email: jane@example.com
---
```

## Collection Configuration

### define_collection Options

```python
define_collection(
    schema=BlogPost,           # Required: dataclass or Pydantic model
    directory="content/blog",  # Directory containing content
    glob="**/*.md",            # File matching pattern (default: all .md)
    strict=True,               # Reject unknown fields (default: True)
    allow_extra=False,         # Store extra fields in _extra (default: False)
    transform=None,            # Frontmatter transform function
    loader=None,               # Custom content source
)
```

### Strict vs Lenient Mode

**Strict mode** (default) rejects content with unknown frontmatter fields:

```python
# Strict: unknown fields cause validation errors
collections = {
    "docs": define_collection(schema=DocPage, directory="content/docs", strict=True),
}
```

**Lenient mode** allows extra fields:

```python
# Lenient: extra fields are ignored or stored
collections = {
    "docs": define_collection(
        schema=DocPage,
        directory="content/docs",
        strict=False,
        allow_extra=True,  # Store extras in _extra dict
    ),
}
```

### Transform Functions

Transform frontmatter before validation to normalize legacy formats:

```python
def normalize_legacy(data: dict) -> dict:
    """Normalize old field names to new schema."""
    if "post_title" in data:
        data["title"] = data.pop("post_title")
    if "publish_date" in data:
        data["date"] = data.pop("publish_date")
    return data

collections = {
    "blog": define_collection(
        schema=BlogPost,
        directory="content/blog",
        transform=normalize_legacy,
    ),
}
```

## Built-in Schemas

Bengal provides ready-to-use schemas for common content types:

```python
from bengal.collections.schemas import (
    BlogPost,      # Blog posts with title, date, author, tags
    DocPage,       # Documentation with weight, category, toc
    APIReference,  # API endpoint documentation
    Tutorial,      # Tutorials with difficulty, duration
    Changelog,     # Release notes with version, breaking changes
)

collections = {
    "blog": define_collection(schema=BlogPost, directory="content/blog"),
    "docs": define_collection(schema=DocPage, directory="content/docs"),
}
```

### Extending Built-in Schemas

Add custom fields by subclassing:

```python
from dataclasses import dataclass
from bengal.collections.schemas import BlogPost

@dataclass
class MyBlogPost(BlogPost):
    """Extended blog post with custom fields."""
    series: str | None = None
    reading_time: int | None = None
    featured: bool = False
```

## Validation Errors

When content fails validation, Bengal reports detailed errors:

```text
ContentValidationError: Validation failed for content/blog/my-post.md

  Schema: BlogPost
  Errors:
    - title: Field required but not provided
    - date: Invalid datetime format: 'January 15'
    - author.email: Invalid email format: 'not-an-email'

  Suggestion: Check frontmatter in content/blog/my-post.md
```

### Validation Result

The validator returns a `ValidationResult`:

```python
from bengal.collections import SchemaValidator, ValidationResult

validator = SchemaValidator(BlogPost)
result: ValidationResult = validator.validate(frontmatter_dict)

if result.valid:
    post: BlogPost = result.data  # Typed instance
else:
    for error in result.errors:
        print(f"{error.field}: {error.message}")
```

## Using with Remote Sources

Collections work with remote content sources:

```python
from bengal.content_layer import github_loader, notion_loader

collections = {
    # Local content
    "docs": define_collection(
        schema=DocPage,
        directory="content/docs",
    ),

    # GitHub repository
    "api-docs": define_collection(
        schema=APIReference,
        loader=github_loader(repo="myorg/api-docs", path="docs/"),
    ),

    # Notion database
    "wiki": define_collection(
        schema=WikiPage,
        loader=notion_loader(database_id="abc123"),
    ),
}
```

## IDE Support

With typed collections, your IDE provides:

- **Autocompletion** for frontmatter fields
- **Type checking** for field values
- **Go to definition** for schema classes
- **Inline documentation** from docstrings

## Pydantic Support

Bengal also supports Pydantic models for advanced validation:

```python
from pydantic import BaseModel, EmailStr, HttpUrl

class Author(BaseModel):
    name: str
    email: EmailStr
    website: HttpUrl | None = None

class BlogPost(BaseModel):
    title: str
    author: Author

    class Config:
        extra = "forbid"  # Strict mode
```

## Best Practices

### 1. Start with Built-in Schemas

Use Bengal's built-in schemas and extend as needed:

```python
from bengal.collections.schemas import DocPage

@dataclass
class MyDocPage(DocPage):
    custom_field: str | None = None
```

### 2. Use Strict Mode in Production

Catch frontmatter errors early:

```python
define_collection(schema=DocPage, directory="content/docs", strict=True)
```

### 3. Document Your Schemas

Add docstrings for IDE support:

```python
@dataclass
class BlogPost:
    """
    Blog post content schema.

    Attributes:
        title: Post title displayed in listings and page header
        date: Publication date (ISO format: YYYY-MM-DD)
        author: Author name for byline
        tags: List of topic tags for categorization
    """
    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
```

### 4. Use Transform for Migrations

When updating schemas, use transforms to support old content:

```python
def migrate_v1_to_v2(data: dict) -> dict:
    # Migrate from schema v1 to v2
    if "category" in data and "tags" not in data:
        data["tags"] = [data.pop("category")]
    return data
```

## Related

- [Custom Content Sources](/docs/extending/custom-sources/) for remote content
- [Cheatsheet](/docs/reference/cheatsheet/) for frontmatter field quick reference
