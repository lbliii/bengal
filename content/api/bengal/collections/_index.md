
---
title: "collections"
type: "python-module"
source_file: "bengal/collections/__init__.py"
line_number: 1
description: "Content Collections - Type-safe content schemas for Bengal. This module provides content collections with schema validation, enabling type-safe frontmatter and early error detection during content dis..."
---

# collections
**Type:** Module
**Source:** [View source](bengal/collections/__init__.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›collections

Content Collections - Type-safe content schemas for Bengal.

This module provides content collections with schema validation, enabling
type-safe frontmatter and early error detection during content discovery.

Usage (Local Content):
    # collections.py (project root)
    from dataclasses import dataclass, field
    from datetime import datetime
    from typing import Optional
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

Usage (Remote Content - Content Layer):
    from bengal.collections import define_collection
    from bengal.content_layer import github_loader, notion_loader

    collections = {
        # Local content (default)
        "docs": define_collection(schema=Doc, directory="content/docs"),

        # Remote content from GitHub
        "api": define_collection(
            schema=APIDoc,
            loader=github_loader(repo="myorg/api-docs", path="docs/"),
        ),

        # Remote content from Notion
        "blog": define_collection(
            schema=BlogPost,
            loader=notion_loader(database_id="abc123"),
        ),
    }

Architecture:
    - Collections are opt-in (backward compatible)
    - Schemas use Python dataclasses or Pydantic models
    - Validation happens during discovery phase (fail fast)
    - Supports both strict and lenient modes
    - Remote sources via Content Layer (zero-cost if unused)

Related:
    - bengal/discovery/content_discovery.py: Integration point
    - bengal/content_layer/: Remote content sources
    - bengal/core/page/metadata.py: Frontmatter access

## Classes




### `CollectionConfig`


**Inherits from:**`Generic[T]`Configuration for a content collection.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`schema`
: Dataclass or Pydantic model defining frontmatter structure

`directory`
: Directory containing collection content (relative to content root). Required for local content, optional when using a remote loader.

`glob`
: Glob pattern for matching files (local content only)

`strict`
: If True, reject unknown frontmatter fields

`allow_extra`
: If True, store extra fields in _extra attribute

`transform`
: Optional function to transform frontmatter before validation

`loader`
: Optional ContentSource for remote content (Content Layer). When provided, content is fetched from the remote source instead of the local directory. Install extras: pip install bengal[github]

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `is_remote` @property

```python
def is_remote(self) -> bool
```
Check if this collection uses a remote loader.

#### `source_type` @property

```python
def source_type(self) -> str
```
Get the source type for this collection.




## Methods



#### `__post_init__`

:::{div} api-badge-group
:::

```python
def __post_init__(self) -> None
```


Validate configuration and normalize directory.



:::{rubric} Returns
:class: rubric-returns
:::


`None`

## Functions



### `define_collection`


```python
def define_collection(schema: type[T], directory: str | Path | None = None) -> CollectionConfig[T]
```



Define a content collection with typed schema.

Collections provide type-safe frontmatter validation during content
discovery, catching errors early and enabling IDE autocompletion.

Supports both local content (via directory) and remote content (via loader).
Remote loaders are part of the Content Layer - install extras as needed:
    pip install bengal[github]   # GitHub loader
    pip install bengal[notion]   # Notion loader


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `schema` | `type[T]` | - | Dataclass or Pydantic model defining frontmatter structure. Required fields must not have defaults. Optional fields should have defaults or use Optional[T] type hints. |
| `directory` | `str \| Path \| None` | - | Directory containing collection content (relative to content root). Required for local content, optional when using a remote loader. |







**Returns**


`CollectionConfig[T]` - CollectionConfig instance for use in collections dict.

Example (Local Content):
    >>> from dataclasses import dataclass, field
    >>> from datetime import datetime
    >>> from typing import Optional
    >>>
    >>> @dataclass
    ... class BlogPost:
    ...     title: str
    ...     date: datetime
    ...     author: str = "Anonymous"
    ...     tags: list[str] = field(default_factory=list)
    ...     draft: bool = False
    ...
    >>> blog = define_collection(
    ...     schema=BlogPost,
    ...     directory="content/blog",
    ... )

Example (Remote Content - GitHub):
    >>> from bengal.content_layer import github_loader
    >>>
    >>> api_docs = define_collection(
    ...     schema=APIDoc,
    ...     loader=github_loader(repo="myorg/api-docs", path="docs/"),
    ... )

Example (Remote Content - Notion):
    >>> from bengal.content_layer import notion_loader
    >>>
    >>> blog = define_collection(
    ...     schema=BlogPost,
    ...     loader=notion_loader(database_id="abc123..."),
    ... )

Example with transform:
    >>> def normalize_legacy(data: dict) -> dict:
    ...     if 'post_title' in data:
    ...         data['title'] = data.pop('post_title')
    ...     return data
    ...
    >>> blog = define_collection(
    ...     schema=BlogPost,
    ...     directory="content/blog",
    ...     transform=normalize_legacy,
    ... )



---
*Generated by Bengal autodoc from `bengal/collections/__init__.py`*

