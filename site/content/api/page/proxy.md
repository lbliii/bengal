
---
title: "page.proxy"
type: python-module
source_file: "bengal/core/page/proxy.py"
css_class: api-content
description: "PageProxy - Lazy-loaded page placeholder for incremental builds.  A PageProxy holds minimal page metadata (title, date, tags, etc.) loaded from the PageDiscoveryCache and defers loading full page c..."
---

# page.proxy

PageProxy - Lazy-loaded page placeholder for incremental builds.

A PageProxy holds minimal page metadata (title, date, tags, etc.) loaded from
the PageDiscoveryCache and defers loading full page content until needed.

This enables incremental builds to skip disk I/O and parsing for unchanged
pages while maintaining transparent access (code doesn't know it's lazy).

Architecture:
- Metadata loaded immediately from cache (fast)
- Full content loaded on first access to .content or other lazy properties
- Transparent to callers - behaves like a normal Page object
- Falls back to eager load if cascades or complex operations detected

---

## Classes

### `PageProxy`


Lazy-loaded page placeholder.

Holds page metadata from cache and defers loading full content until
accessed. Transparent to callers - implements Page-like interface.

Usage:
    # Create from cached metadata
    page = PageProxy(
        source_path=Path("content/post.md"),
        metadata=cached_metadata,
        loader=load_page_from_disk,  # Callable that loads full page
    )

    # Access metadata (instant, from cache)
    print(page.title)  # "My Post"
    print(page.tags)   # ["python", "web"]

    # Access full content (triggers lazy load)
    print(page.content)  # Loads from disk and parses

    # After first access, it's fully loaded
    assert page._lazy_loaded  # True



:::{rubric} Properties
:class: rubric-properties
:::
#### `content` @property

```python
@property
def content(self) -> str
```

Get page content (lazy-loaded from disk).
#### `metadata` @property

```python
@property
def metadata(self) -> dict[str, Any]
```

Get full metadata dict (lazy-loaded).
#### `rendered_html` @property

```python
@property
def rendered_html(self) -> str
```

Get rendered HTML (lazy-loaded).
#### `links` @property

```python
@property
def links(self) -> list[str]
```

Get extracted links (lazy-loaded).
#### `version` @property

```python
@property
def version(self) -> str | None
```

Get version (lazy-loaded).
#### `toc` @property

```python
@property
def toc(self) -> str | None
```

Get table of contents (lazy-loaded).
#### `toc_items` @property

```python
@property
def toc_items(self) -> list[dict[str, Any]]
```

Get TOC items (lazy-loaded).
#### `output_path` @property

```python
@property
def output_path(self) -> Path | None
```

Get output path (lazy-loaded).
#### `parsed_ast` @property

```python
@property
def parsed_ast(self) -> Any
```

Get parsed AST (lazy-loaded).
#### `related_posts` @property

```python
@property
def related_posts(self) -> list
```

Get related posts (lazy-loaded).
#### `translation_key` @property

```python
@property
def translation_key(self) -> str | None
```

Get translation key.
#### `url` @property

```python
@property
def url(self) -> str
```

Get the URL path for the page (lazy-loaded, cached after first access).
#### `meta_description` @property

```python
@property
def meta_description(self) -> str
```

Get meta description (lazy-loaded from full page).
#### `reading_time` @property

```python
@property
def reading_time(self) -> str
```

Get reading time estimate (lazy-loaded from full page).
#### `excerpt` @property

```python
@property
def excerpt(self) -> str
```

Get content excerpt (lazy-loaded from full page).
#### `keywords` @property

```python
@property
def keywords(self) -> list[str]
```

Get keywords (lazy-loaded from full page).
#### `is_home` @property

```python
@property
def is_home(self) -> bool
```

Check if this page is the home page.
#### `is_section` @property

```python
@property
def is_section(self) -> bool
```

Check if this page is a section page.
#### `is_page` @property

```python
@property
def is_page(self) -> bool
```

Check if this is a regular page (not a section).
#### `kind` @property

```python
@property
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.
#### `description` @property

```python
@property
def description(self) -> str
```

Get page description from metadata.
#### `draft` @property

```python
@property
def draft(self) -> bool
```

Check if page is marked as draft.
#### `next` @property

```python
@property
def next(self) -> Page | None
```

Get next page in site collection.
#### `prev` @property

```python
@property
def prev(self) -> Page | None
```

Get previous page in site collection.

:::{rubric} Methods
:class: rubric-methods
:::
#### `content`
```python
def content(self) -> str
```

Get page content (lazy-loaded from disk).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `metadata`
```python
def metadata(self) -> dict[str, Any]
```

Get full metadata dict (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `rendered_html`
```python
def rendered_html(self) -> str
```

Get rendered HTML (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `links`
```python
def links(self) -> list[str]
```

Get extracted links (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]`




---
#### `version`
```python
def version(self) -> str | None
```

Get version (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `toc`
```python
def toc(self) -> str | None
```

Get table of contents (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `toc_items`
```python
def toc_items(self) -> list[dict[str, Any]]
```

Get TOC items (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[dict[str, Any]]`




---
#### `output_path`
```python
def output_path(self) -> Path | None
```

Get output path (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path | None`




---
#### `parsed_ast`
```python
def parsed_ast(self) -> Any
```

Get parsed AST (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any`




---
#### `related_posts`
```python
def related_posts(self) -> list
```

Get related posts (lazy-loaded).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list`




---
#### `translation_key`
```python
def translation_key(self) -> str | None
```

Get translation key.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `url`
```python
def url(self) -> str
```

Get the URL path for the page (lazy-loaded, cached after first access).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `meta_description`
```python
def meta_description(self) -> str
```

Get meta description (lazy-loaded from full page).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `reading_time`
```python
def reading_time(self) -> str
```

Get reading time estimate (lazy-loaded from full page).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `excerpt`
```python
def excerpt(self) -> str
```

Get content excerpt (lazy-loaded from full page).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `keywords`
```python
def keywords(self) -> list[str]
```

Get keywords (lazy-loaded from full page).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]`




---
#### `is_home`
```python
def is_home(self) -> bool
```

Check if this page is the home page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `is_section`
```python
def is_section(self) -> bool
```

Check if this page is a section page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `is_page`
```python
def is_page(self) -> bool
```

Check if this is a regular page (not a section).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `kind`
```python
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `description`
```python
def description(self) -> str
```

Get page description from metadata.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `draft`
```python
def draft(self) -> bool
```

Check if page is marked as draft.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `next`
```python
def next(self) -> Page | None
```

Get next page in site collection.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None`




---
#### `prev`
```python
def prev(self) -> Page | None
```

Get previous page in site collection.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None`




---
#### `__init__`
```python
def __init__(self, source_path: Path, metadata: Any, loader: callable)
```

Initialize PageProxy with metadata and loader.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source content file
* - `metadata`
  - `Any`
  - -
  - PageMetadata from cache (has title, date, tags, etc.)
* - `loader`
  - `callable`
  - -
  - Callable that loads full Page(source_path) -> Page
:::

::::




---
#### `rendered_html`
```python
def rendered_html(self, value: str) -> None
```

Set rendered HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `value`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `toc`
```python
def toc(self, value: str | None) -> None
```

Set table of contents.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `value`
  - `str | None`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `output_path`
```python
def output_path(self, value: Path | None) -> None
```

Set output path.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `value`
  - `Path | None`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `parsed_ast`
```python
def parsed_ast(self, value: Any) -> None
```

Set parsed AST.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `value`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `related_posts`
```python
def related_posts(self, value: list) -> None
```

Set related posts.

In incremental mode, allow setting on proxy without forcing a full load.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `value`
  - `list`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `extract_links`
```python
def extract_links(self) -> None
```

Extract links from content.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `__hash__`
```python
def __hash__(self) -> int
```

Hash based on source_path (same as Page).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int`




---
#### `__eq__`
```python
def __eq__(self, other: Any) -> bool
```

Equality based on source_path.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `other`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `__repr__`
```python
def __repr__(self) -> str
```

String representation.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `__str__`
```python
def __str__(self) -> str
```

String conversion.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `get_load_status`
```python
def get_load_status(self) -> dict[str, Any]
```

Get debugging info about proxy state.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `from_page` @classmethod
```python
def from_page(cls, page: Page, metadata: Any) -> PageProxy
```

Create proxy from full page (for testing).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
* - `page`
  - `Page`
  - -
  - -
* - `metadata`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PageProxy`




---
