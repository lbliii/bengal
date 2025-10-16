
---
title: "cache.page_discovery_cache"
type: python-module
source_file: "bengal/cache/page_discovery_cache.py"
css_class: api-content
description: "Page Discovery Cache for incremental builds.  Caches page metadata (title, date, tags, section, slug) to enable lazy loading of full page content. This allows incremental builds to skip discovery o..."
---

# cache.page_discovery_cache

Page Discovery Cache for incremental builds.

Caches page metadata (title, date, tags, section, slug) to enable lazy loading
of full page content. This allows incremental builds to skip discovery of
unchanged pages and only load full content when needed.

Architecture:
- Metadata: source_path → PageMetadata (minimal data needed for navigation/filtering)
- Lazy Loading: Full content loaded on first access via PageProxy
- Storage: .bengal/page_metadata.json (compact format)
- Validation: Hash-based validation to detect stale cache entries

Performance Impact:
- Full page discovery skipped for unchanged pages (~80ms saved per 100 pages)
- Lazy loading ensures correctness (full content available when needed)
- Incremental builds only load changed pages fresh

---

## Classes

### `PageMetadata`


Minimal page metadata needed for navigation and filtering.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 9 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `source_path`
  - `str`
  - -
* - `title`
  - `str`
  - -
* - `date`
  - `str | None`
  - -
* - `tags`
  - `list[str]`
  - -
* - `section`
  - `str | None`
  - -
* - `slug`
  - `str | None`
  - -
* - `weight`
  - `int | None`
  - -
* - `lang`
  - `str | None`
  - -
* - `file_hash`
  - `str | None`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

Convert to dictionary for JSON serialization.



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
#### `from_dict` @staticmethod
```python
def from_dict(data: dict[str, Any]) -> 'PageMetadata'
```

Create from dictionary.



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
* - `data`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'PageMetadata'`




---

### `PageDiscoveryCacheEntry`


Cache entry with metadata and validity information.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `metadata`
  - `PageMetadata`
  - -
* - `cached_at`
  - `str`
  - -
* - `is_valid`
  - `bool`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

*No description provided.*



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
#### `from_dict` @staticmethod
```python
def from_dict(data: dict[str, Any]) -> 'PageDiscoveryCacheEntry'
```

*No description provided.*



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
* - `data`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'PageDiscoveryCacheEntry'`




---

### `PageDiscoveryCache`


Persistent cache for page metadata enabling lazy page loading.

Purpose:
- Store page metadata (title, date, tags, section, slug)
- Enable incremental discovery (only load changed pages)
- Support lazy loading of full page content on demand
- Validate cache entries to detect stale data

Cache Format (JSON):
{
    "version": 1,
    "pages": {
        "content/index.md": {
            "metadata": {
                "source_path": "content/index.md",
                "title": "Home",
                ...
            },
            "cached_at": "2025-10-16T12:00:00",
            "is_valid": true
        }
    }
}




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, cache_path: Path | None = None)
```

Initialize cache.



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
* - `cache_path`
  - `Path | None`
  - `None`
  - Path to cache file (defaults to .bengal/page_metadata.json)
:::

::::




---
#### `save_to_disk`
```python
def save_to_disk(self) -> None
```

Save cache to disk.



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
#### `has_metadata`
```python
def has_metadata(self, source_path: Path) -> bool
```

Check if metadata is cached for a page.



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
* - `source_path`
  - `Path`
  - -
  - Path to source file
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if valid metadata exists in cache




---
#### `get_metadata`
```python
def get_metadata(self, source_path: Path) -> PageMetadata | None
```

Get cached metadata for a page.



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
* - `source_path`
  - `Path`
  - -
  - Path to source file
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PageMetadata | None` - PageMetadata if found and valid, None otherwise




---
#### `add_metadata`
```python
def add_metadata(self, metadata: PageMetadata) -> None
```

Add or update metadata in cache.



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
* - `metadata`
  - `PageMetadata`
  - -
  - PageMetadata to cache
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `invalidate`
```python
def invalidate(self, source_path: Path) -> None
```

Mark a cache entry as invalid.



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
* - `source_path`
  - `Path`
  - -
  - Path to source file to invalidate
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `invalidate_all`
```python
def invalidate_all(self) -> None
```

Invalidate all cache entries.



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
#### `clear`
```python
def clear(self) -> None
```

Clear all cache entries.



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
#### `get_valid_entries`
```python
def get_valid_entries(self) -> dict[str, PageMetadata]
```

Get all valid cached metadata entries.



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

`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for valid entries




---
#### `get_invalid_entries`
```python
def get_invalid_entries(self) -> dict[str, PageMetadata]
```

Get all invalid cached metadata entries.



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

`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for invalid entries




---
#### `validate_entry`
```python
def validate_entry(self, source_path: Path, current_file_hash: str) -> bool
```

Validate a cache entry against current file hash.



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
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source file
* - `current_file_hash`
  - `str`
  - -
  - Current hash of source file
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if cache entry is valid (hash matches), False otherwise




---
#### `stats`
```python
def stats(self) -> dict[str, int]
```

Get cache statistics.



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

`dict[str, int]` - Dictionary with cache stats (total, valid, invalid)




---
