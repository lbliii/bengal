
---
title: "page_discovery_cache"
type: "python-module"
source_file: "bengal/cache/page_discovery_cache.py"
line_number: 1
description: "Page Discovery Cache for incremental builds. Caches page metadata (title, date, tags, section, slug) to enable lazy loading of full page content. This allows incremental builds to skip discovery of un..."
---

# page_discovery_cache
**Type:** Module
**Source:** [View source](bengal/cache/page_discovery_cache.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›page_discovery_cache

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

## Classes




### `PageDiscoveryCacheEntry`


Cache entry with metadata and validity information.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`metadata`
: 

`cached_at`
: 

`is_valid`
: 

:::







## Methods



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


*No description provided.*



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-staticmethod">staticmethod</span>:::

```python
def from_dict(data: dict[str, Any]) -> PageDiscoveryCacheEntry
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`PageDiscoveryCacheEntry`




### `PageDiscoveryCache`


Persistent cache for page metadata enabling lazy page loading.

Purpose:
- Store page metadata (title, date, tags, section, slug)
- Enable incremental discovery (only load changed pages)
- Support lazy loading of full page content on demand
- Validate cache entries to detect stale data

Cache Format (JSON):
{
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

Note: If cache format changes, load will fail and cache rebuilds automatically.









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, cache_path: Path | None = None)
```


Initialize cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path \| None` | - | Path to cache file (defaults to .bengal/page_metadata.json) |









#### `save_to_disk`

:::{div} api-badge-group
:::

```python
def save_to_disk(self) -> None
```


Save cache to disk.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `has_metadata`

:::{div} api-badge-group
:::

```python
def has_metadata(self, source_path: Path) -> bool
```


Check if metadata is cached for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if valid metadata exists in cache



#### `get_metadata`

:::{div} api-badge-group
:::

```python
def get_metadata(self, source_path: Path) -> PageMetadata | None
```


Get cached metadata for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |







:::{rubric} Returns
:class: rubric-returns
:::


`PageMetadata | None` - PageMetadata if found and valid, None otherwise



#### `add_metadata`

:::{div} api-badge-group
:::

```python
def add_metadata(self, metadata: PageMetadata) -> None
```


Add or update metadata in cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `metadata` | `PageMetadata` | - | PageMetadata to cache |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `invalidate`

:::{div} api-badge-group
:::

```python
def invalidate(self, source_path: Path) -> None
```


Mark a cache entry as invalid.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file to invalidate |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `invalidate_all`

:::{div} api-badge-group
:::

```python
def invalidate_all(self) -> None
```


Invalidate all cache entries.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `clear`

:::{div} api-badge-group
:::

```python
def clear(self) -> None
```


Clear all cache entries.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_valid_entries`

:::{div} api-badge-group
:::

```python
def get_valid_entries(self) -> dict[str, PageMetadata]
```


Get all valid cached metadata entries.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for valid entries



#### `get_invalid_entries`

:::{div} api-badge-group
:::

```python
def get_invalid_entries(self) -> dict[str, PageMetadata]
```


Get all invalid cached metadata entries.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for invalid entries



#### `validate_entry`

:::{div} api-badge-group
:::

```python
def validate_entry(self, source_path: Path, current_file_hash: str) -> bool
```


Validate a cache entry against current file hash.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |
| `current_file_hash` | `str` | - | Current hash of source file |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if cache entry is valid (hash matches), False otherwise



#### `stats`

:::{div} api-badge-group
:::

```python
def stats(self) -> dict[str, int]
```


Get cache statistics.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, int]` - Dictionary with cache stats (total, valid, invalid)



---
*Generated by Bengal autodoc from `bengal/cache/page_discovery_cache.py`*

