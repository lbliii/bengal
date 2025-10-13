
---
title: "page"
type: python-module
source_file: "bengal/core/page/__init__.py"
css_class: api-content
description: "Page Object - Represents a single content page.  This module provides the main Page class, which combines multiple mixins to provide a complete page interface while maintaining separation of concerns."
---

# page

Page Object - Represents a single content page.

This module provides the main Page class, which combines multiple mixins
to provide a complete page interface while maintaining separation of concerns.

---

## Classes

### `Page`

**Inherits from:** `PageMetadataMixin`, `PageNavigationMixin`, `PageComputedMixin`, `PageRelationshipsMixin`, `PageOperationsMixin`
Represents a single content page.

HASHABILITY:
============
Pages are hashable based on their source_path, allowing them to be stored
in sets and used as dictionary keys. This enables:
- Fast membership tests (O(1) instead of O(n))
- Automatic deduplication with sets
- Set operations for page analysis
- Direct use as dictionary keys

Two pages with the same source_path are considered equal, even if their
content differs. The hash is stable throughout the page lifecycle because
source_path is immutable. Mutable fields (content, rendered_html, etc.)
do not affect the hash or equality.

BUILD LIFECYCLE:
================
Pages progress through distinct build phases. Properties have different
availability depending on the current phase:

1. Discovery (content_discovery.py)
   ✅ Available: source_path, content, metadata, title, slug, date
   ❌ Not available: toc, parsed_ast, toc_items, rendered_html

2. Parsing (pipeline.py)
   ✅ Available: All Stage 1 + toc, parsed_ast
   ✅ toc_items can be accessed (will extract from toc)

3. Rendering (pipeline.py)
   ✅ Available: All previous + rendered_html, output_path
   ✅ All properties fully populated

Note: Some properties like toc_items can be accessed early (returning [])
but won't cache empty results, allowing proper extraction after parsing.

Attributes:
    source_path: Path to the source content file
    content: Raw content (Markdown, etc.)
    metadata: Frontmatter metadata (title, date, tags, etc.)
    parsed_ast: Abstract Syntax Tree from parsed content
    rendered_html: Rendered HTML output
    output_path: Path where the rendered page will be written
    links: List of links found in the page
    tags: Tags associated with the page
    version: Version information for versioned content
    toc: Table of contents HTML (auto-generated from headings)
    toc_items: Structured TOC data for custom rendering
    related_posts: Related pages (pre-computed during build based on tag overlap)

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`source_path`** (`Path`)- **`content`** (`str`)- **`metadata`** (`dict[str, Any]`)- **`parsed_ast`** (`Any | None`)- **`rendered_html`** (`str`)- **`output_path`** (`Path | None`)- **`links`** (`list[str]`)- **`tags`** (`list[str]`)- **`version`** (`str | None`)- **`toc`** (`str | None`)- **`related_posts`** (`list['Page']`)- **`lang`** (`str | None`)- **`translation_key`** (`str | None`)- **`_site`** (`Any | None`)- **`_section`** (`Any | None`)- **`_toc_items_cache`** (`list[dict[str, Any]] | None`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__post_init__`
```python
def __post_init__(self) -> None
```

Initialize computed fields.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `__hash__`
```python
def __hash__(self) -> int
```

Hash based on source_path for stable identity.

The hash is computed from the page's source_path, which is immutable
throughout the page lifecycle. This allows pages to be stored in sets
and used as dictionary keys.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int` - Integer hash of the source path




---
#### `__eq__`
```python
def __eq__(self, other: Any) -> bool
```

Pages are equal if they have the same source path.

Equality is based on source_path only, not on content or other
mutable fields. This means two Page objects representing the same
source file are considered equal, even if their processed content
differs.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`other`** (`Any`) - Object to compare with

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if other is a Page with the same source_path




---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
