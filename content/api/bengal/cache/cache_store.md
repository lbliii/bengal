
---
title: "cache_store"
type: "python-module"
source_file: "bengal/cache/cache_store.py"
line_number: 1
description: "Generic cache storage for Cacheable types. This module provides a type-safe, generic cache storage mechanism that works with any type implementing the Cacheable protocol. It handles: - JSON serializat..."
---

# cache_store
**Type:** Module
**Source:** [View source](bengal/cache/cache_store.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›cache_store

Generic cache storage for Cacheable types.

This module provides a type-safe, generic cache storage mechanism that works
with any type implementing the Cacheable protocol. It handles:

- JSON serialization/deserialization
- Zstandard compression (92-93% size reduction)
- Version management (tolerant loading)
- Directory creation
- Type-safe load/save operations
- Backward compatibility (reads both compressed and uncompressed)

Design Philosophy:
    CacheStore provides a reusable cache storage layer that works with any
    Cacheable type. This eliminates the need for each cache (TaxonomyIndex,
    AssetDependencyMap, etc.) to implement its own save/load logic.

    Benefits:
    - Consistent version handling across all caches
    - Type-safe operations (mypy validates)
    - Tolerant loading (returns empty on mismatch, doesn't crash)
    - Automatic directory creation
    - Single source of truth for cache file format
    - 12-14x compression ratio with Zstandard (PEP 784)

Usage Example:
    from bengal.cache.cache_store import CacheStore
    from bengal.cache.taxonomy_index import TagEntry

    # Create store (compression enabled by default)
    store = CacheStore(Path('.bengal/tags.json'))

    # Save entries (type-safe, compressed)
    tags = [
        TagEntry(tag_slug='python', tag_name='Python', page_paths=[], updated_at='...'),
        TagEntry(tag_slug='web', tag_name='Web', page_paths=[], updated_at='...'),
    ]
    store.save(tags, version=1)

    # Load entries (auto-detects format: .json.zst or .json)
    loaded_tags = store.load(TagEntry, expected_version=1)
    # Returns [] if file missing or version mismatch

See Also:
    - bengal/cache/cacheable.py - Cacheable protocol definition
    - bengal/cache/compression.py - Zstandard compression utilities
    - bengal/cache/taxonomy_index.py - Example usage (TagEntry)
    - bengal/cache/asset_dependency_map.py - Example usage (AssetDependencyEntry)
    - plan/active/rfc-zstd-cache-compression.md - Compression RFC

## Classes




### `CacheStore`


Generic cache storage for types implementing the Cacheable protocol.

Provides type-safe save/load operations with version management,
Zstandard compression, and tolerant loading (returns empty list on
version mismatch or missing file).



**Attributes:**

:::{div} api-attributes
`cache_path`
: Path to cache file (e.g., .bengal/taxonomy_index.json)

`compress`
: Whether to use Zstandard compression (default: True) Cache File Format:

`Compressed`
: Zstd-compressed JSON with same structure as below 92-93% smaller, 12-14x compression ratio

`Uncompressed`
: { "version": 1, "entries": [ {...},  // Serialized Cacheable objects {...} ] } Version Management: - Each cache file has a top-level "version" field - On version mismatch, load() returns empty list and logs warning - On missing file, load() returns empty list (no warning) - On malformed data, load() returns empty list and logs error This "tolerant loading" approach ensures that stale or incompatible caches don't crash the build - they just rebuild from scratch.

`Compression`
: - Enabled by default (Python 3.14+ with compression.zstd) - 92-93% size reduction on typical cache files - <1ms compress time, <0.3ms decompress time - Auto-detects format on load (reads both .json.zst and .json) - Backward compatible: reads old uncompressed caches Type Safety: - save() accepts list of any Cacheable type - load() requires explicit type parameter for deserialization - mypy validates that type implements Cacheable protocol

:::







## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, cache_path: Path, compress: bool = True)
```


Initialize cache store.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path` | - | Path to cache file (e.g., .bengal/taxonomy_index.json). Parent directory will be created if missing. With compression enabled, actual file will be .json.zst |
| `compress` | `bool` | `True` | Whether to use Zstandard compression (default: True). Set to False for debugging or compatibility. |








#### `save`

:::{div} api-badge-group
:::

```python
def save(self, entries: list[Cacheable], version: int = 1, indent: int = 2) -> None
```


Save entries to cache file.

Serializes all entries to JSON and writes to cache file. Creates
parent directory if missing. Uses Zstandard compression by default.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `entries` | `list[Cacheable]` | - | List of Cacheable objects to save |
| `version` | `int` | `1` | Cache version number (default: 1). Increment when format changes (new fields, removed fields, etc.) |
| `indent` | `int` | `2` | JSON indentation (default: 2). Only used when compression is disabled; compressed files always use compact JSON. |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`OSError`**:If directory creation or file write fails
- **`TypeError`**:If entries contain non-JSON-serializable data

:::{rubric} Examples
:class: rubric-examples
:::


```python
tags = [
        TagEntry(tag_slug='python', ...),
        TagEntry(tag_slug='web', ...),
    ]
    store.save(tags, version=1)  # Saves as .json.zst
```




#### `load`

:::{div} api-badge-group
:::

```python
def load(self, entry_type: type[T], expected_version: int = 1) -> list[T]
```


Load entries from cache file (tolerant).

Deserializes entries and validates version. Automatically detects
format (compressed .json.zst or uncompressed .json). If version
mismatch or file missing, returns empty list (doesn't crash).

This "tolerant loading" approach ensures that builds never fail due
to stale or incompatible caches - they just rebuild from scratch.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `entry_type` | `type[T]` | - | Type to deserialize (must implement Cacheable protocol). Used to call from_cache_dict() classmethod. |
| `expected_version` | `int` | `1` | Expected cache version (default: 1). If file version doesn't match, returns empty list. |







:::{rubric} Returns
:class: rubric-returns
:::


`list[T]` - List of deserialized entries, or [] if:
    - File doesn't exist (no warning, normal for first build)
    - Version mismatch (warning logged)
    - Malformed data (error logged)
    - Deserialization fails (error logged)
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Normal load (auto-detects .json.zst or .json)
    tags = store.load(TagEntry, expected_version=1)

    # Version mismatch (returns [])
    store.save(tags, version=2)  # Bump version
    loaded = store.load(TagEntry, expected_version=1)  # []

Type Safety:
    mypy validates that entry_type implements Cacheable:

        store.load(TagEntry, ...)  # ✅ OK (TagEntry implements Cacheable)
        store.load(Page, ...)      # ❌ Error (Page doesn't implement Cacheable)
```





#### `exists`

:::{div} api-badge-group
:::

```python
def exists(self) -> bool
```


Check if cache file exists (compressed or uncompressed).



:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if cache file exists in either format, False otherwise



#### `clear`

:::{div} api-badge-group
:::

```python
def clear(self) -> None
```


Delete cache file if it exists (both compressed and uncompressed).

Used to force cache rebuild (e.g., after format changes).



:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
store = CacheStore(Path('.bengal/tags.json'))
    store.clear()  # Force rebuild on next build
```



---
*Generated by Bengal autodoc from `bengal/cache/cache_store.py`*

