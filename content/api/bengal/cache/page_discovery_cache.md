
---
title: "page_discovery_cache"
type: "python-module"
source_file: "bengal/bengal/cache/page_discovery_cache.py"
line_number: 1
description: "Page Discovery Cache for incremental builds. Caches page metadata (title, date, tags, section, slug) to enable lazy loading of full page content. This allows incremental builds to skip discovery of un..."
---

# page_discovery_cache
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/cache/page_discovery_cache.py#L1)



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

| Name | Type | Description |
|:-----|:-----|:------------|
| `metadata` | - | *No description provided.* |
| `cached_at` | - | *No description provided.* |
| `is_valid` | - | *No description provided.* |







## Methods



#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```


*No description provided.*



**Returns**


`dict[str, Any]`



#### `from_dict` @staticmethod
```python
def from_dict(data: dict[str, Any]) -> PageDiscoveryCacheEntry
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







**Returns**


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
```python
def __init__(self, cache_path: Path | None = None)
```


Initialize cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path \| None` | - | Path to cache file (defaults to .bengal/page_metadata.json) |









#### `save_to_disk`
```python
def save_to_disk(self) -> None
```


Save cache to disk.



**Returns**


`None`



#### `has_metadata`
```python
def has_metadata(self, source_path: Path) -> bool
```


Check if metadata is cached for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |







**Returns**


`bool` - True if valid metadata exists in cache



#### `get_metadata`
```python
def get_metadata(self, source_path: Path) -> PageMetadata | None
```


Get cached metadata for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |







**Returns**


`PageMetadata | None` - PageMetadata if found and valid, None otherwise



#### `add_metadata`
```python
def add_metadata(self, metadata: PageMetadata) -> None
```


Add or update metadata in cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `metadata` | `PageMetadata` | - | PageMetadata to cache |







**Returns**


`None`



#### `invalidate`
```python
def invalidate(self, source_path: Path) -> None
```


Mark a cache entry as invalid.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file to invalidate |







**Returns**


`None`



#### `invalidate_all`
```python
def invalidate_all(self) -> None
```


Invalidate all cache entries.



**Returns**


`None`



#### `clear`
```python
def clear(self) -> None
```


Clear all cache entries.



**Returns**


`None`



#### `get_valid_entries`
```python
def get_valid_entries(self) -> dict[str, PageMetadata]
```


Get all valid cached metadata entries.



**Returns**


`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for valid entries



#### `get_invalid_entries`
```python
def get_invalid_entries(self) -> dict[str, PageMetadata]
```


Get all invalid cached metadata entries.



**Returns**


`dict[str, PageMetadata]` - Dictionary mapping source_path to PageMetadata for invalid entries



#### `validate_entry`
```python
def validate_entry(self, source_path: Path, current_file_hash: str) -> bool
```


Validate a cache entry against current file hash.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |
| `current_file_hash` | `str` | - | Current hash of source file |







**Returns**


`bool` - True if cache entry is valid (hash matches), False otherwise



#### `stats`
```python
def stats(self) -> dict[str, int]
```


Get cache statistics.



**Returns**


`dict[str, int]` - Dictionary with cache stats (total, valid, invalid)



---
*Generated by Bengal autodoc from `bengal/bengal/cache/page_discovery_cache.py`*

