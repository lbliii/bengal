
---
title: "cache"
type: "python-module"
source_file: "bengal/bengal/pipeline/cache.py"
line_number: 1
description: "Disk caching for reactive pipeline streams. This module provides persistent caching for stream items, enabling: - Fast incremental builds (skip unchanged items) - Cross-build cache persistence - Versi..."
---

# cache
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/cache.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›cache

Disk caching for reactive pipeline streams.

This module provides persistent caching for stream items, enabling:
- Fast incremental builds (skip unchanged items)
- Cross-build cache persistence
- Version-based cache invalidation

Key Components:
    - StreamCache: Disk-backed cache storage for stream items
    - DiskCachedStream: Stream wrapper that adds persistent caching
    - StreamCacheEntry: Cacheable entry for stream items

Architecture:
    Stream items are cached by their StreamKey, which includes:
    - source: Which stream produced the item
    - id: Unique identifier within the stream
    - version: Content hash for invalidation

    When a stream runs, cached items with matching key+version are
    returned without recomputing. Changed items (different version)
    are recomputed and the cache is updated.

Related:
    - bengal/cache/cacheable.py - Cacheable protocol
    - bengal/cache/cache_store.py - Generic cache storage
    - bengal/pipeline/core.py - StreamKey, StreamItem

## Classes




### `StreamCacheEntry`


**Inherits from:**`Cacheable`A single cached stream item entry.

Implements Cacheable protocol for JSON serialization.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `source` | - | Stream name that produced this item |
| `id` | - | Unique identifier within the stream |
| `version` | - | Content version (hash) for invalidation |
| `value_json` | - | JSON-serialized value |
| `cached_at` | - | Timestamp when cached |




:::{rubric} Properties
:class: rubric-properties
:::



#### `key` @property

```python
def key(self) -> StreamKey
```
Reconstruct StreamKey from entry.




## Methods



#### `key`
```python
def key(self) -> StreamKey
```


Reconstruct StreamKey from entry.



**Returns**


`StreamKey`



#### `to_cache_dict`
```python
def to_cache_dict(self) -> dict[str, Any]
```


Serialize to JSON-compatible dict.



**Returns**


`dict[str, Any]`



#### `from_cache_dict` @classmethod
```python
def from_cache_dict(cls, data: dict[str, Any]) -> StreamCacheEntry
```


Deserialize from dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







**Returns**


`StreamCacheEntry`




### `StreamCache`


Disk-backed cache for stream items.

Stores stream items as JSON in the .bengal/ directory, enabling
persistence across builds.

Cache Structure:
    .bengal/pipeline/
    ├── streams.json          # Cache index and metadata
    └── items/
        ├── {source}_{id}.json  # Individual item caches

Usage:
    >>> cache = StreamCache(Path(".bengal/pipeline"))
    >>> cache.get(key)  # Returns cached value or None
    >>> cache.put(key, value, serialize_fn)  # Store value
    >>> cache.save()  # Persist to disk

Thread Safety:
    Not thread-safe. Use separate cache instances per thread
    or synchronize access externally.









## Methods



#### `__init__`
```python
def __init__(self, cache_dir: Path) -> None
```


Initialize stream cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_dir` | `Path` | - | Directory for cache files (.bengal/pipeline) |







**Returns**


`None`




#### `get`
```python
def get(self, key: StreamKey, deserialize_fn: Callable[[str], T] | None = None) -> T | None
```


Get cached value for a stream key.

Returns None if:
- Key not in cache
- Cached version doesn't match key version


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `StreamKey` | - | StreamKey to look up |
| `deserialize_fn` | `Callable[[str], T] \| None` | - | Function to deserialize JSON value |







**Returns**


`T | None` - Cached value or None if cache miss



#### `put`
```python
def put(self, key: StreamKey, value: Any, serialize_fn: Callable[[Any], str] | None = None) -> None
```


Store value in cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `StreamKey` | - | StreamKey for this item |
| `value` | `Any` | - | Value to cache |
| `serialize_fn` | `Callable[[Any], str] \| None` | - | Function to serialize value to JSON string |







**Returns**


`None`



#### `invalidate`
```python
def invalidate(self, key: StreamKey) -> bool
```


Remove entry from cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `StreamKey` | - | StreamKey to invalidate |







**Returns**


`bool` - True if entry was removed, False if not found



#### `invalidate_source`
```python
def invalidate_source(self, source: str) -> int
```


Remove all entries from a specific source stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | Stream name to invalidate |







**Returns**


`int` - Number of entries removed



#### `clear`
```python
def clear(self) -> None
```


Clear all cache entries.



**Returns**


`None`



#### `save`
```python
def save(self) -> None
```


Persist cache to disk.

Only writes if cache has been modified since last save.



**Returns**


`None`




#### `get_stats`
```python
def get_stats(self) -> dict[str, Any]
```


Get cache statistics.



**Returns**


`dict[str, Any]`




### `DiskCachedStream`


**Inherits from:**`Stream[T]`Stream wrapper that adds persistent disk caching.

Cached items are stored to disk and reused across builds.
Only items with changed versions are recomputed.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], cache: StreamCache) -> None
```


Initialize disk-cached stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream to cache |
| `cache` | `StreamCache` | - | StreamCache instance for storage |







**Returns**


`None`




#### `get_cache_stats`
```python
def get_cache_stats(self) -> dict[str, Any]
```


Get caching statistics for this stream.



**Returns**


`dict[str, Any]`

## Functions



### `add_disk_cache_method`


```python
def add_disk_cache_method() -> None
```



Add disk_cache() method to Stream class.

This is called at module import to extend Stream with caching support.



**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/cache.py`*
