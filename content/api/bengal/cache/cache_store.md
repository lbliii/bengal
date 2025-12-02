
---
title: "cache_store"
type: "python-module"
source_file: "bengal/bengal/cache/cache_store.py"
line_number: 1
description: "Generic cache storage for Cacheable types. This module provides a type-safe, generic cache storage mechanism that works with any type implementing the Cacheable protocol. It handles: - JSON serializat..."
---

# cache_store
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/cache/cache_store.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›cache_store

Generic cache storage for Cacheable types.

This module provides a type-safe, generic cache storage mechanism that works
with any type implementing the Cacheable protocol. It handles:

- JSON serialization/deserialization
- Version management (tolerant loading)
- Directory creation
- Type-safe load/save operations

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

Usage Example:
    from bengal.cache.cache_store import CacheStore
    from bengal.cache.taxonomy_index import TagEntry

    # Create store
    store = CacheStore(Path('.bengal/tags.json'))

    # Save entries (type-safe)
    tags = [
        TagEntry(tag_slug='python', tag_name='Python', page_paths=[], updated_at='...'),
        TagEntry(tag_slug='web', tag_name='Web', page_paths=[], updated_at='...'),
    ]
    store.save(tags, version=1)

    # Load entries (type-safe, tolerant)
    loaded_tags = store.load(TagEntry, expected_version=1)
    # Returns [] if file missing or version mismatch

See Also:
    - bengal/cache/cacheable.py - Cacheable protocol definition
    - bengal/cache/taxonomy_index.py - Example usage (TagEntry)
    - bengal/cache/asset_dependency_map.py - Example usage (AssetDependencyEntry)

## Classes




### `CacheStore`


Generic cache storage for types implementing the Cacheable protocol.

Provides type-safe save/load operations with version management and
tolerant loading (returns empty list on version mismatch or missing file).



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `cache_path` | - | Path to cache file (e.g., .bengal/taxonomy_index.json) Cache File Format: { "version": 1, "entries": [ {...}, // Serialized Cacheable objects {...} ] } Version Management: - Each cache file has a top-level "version" field - On version mismatch, load() returns empty list and logs warning - On missing file, load() returns empty list (no warning) - On malformed JSON, load() returns empty list and logs error This "tolerant loading" approach ensures that stale or incompatible caches don't crash the build - they just rebuild from scratch. Type Safety: - save() accepts list of any Cacheable type - load() requires explicit type parameter for deserialization - mypy validates that type implements Cacheable protocol |







## Methods



#### `__init__`
```python
def __init__(self, cache_path: Path)
```


Initialize cache store.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path` | - | Path to cache file (e.g., .bengal/taxonomy_index.json). Parent directory will be created if missing. |








#### `save`
```python
def save(self, entries: list[Cacheable], version: int = 1, indent: int = 2) -> None
```


Save entries to cache file.

Serializes all entries to JSON and writes to cache file. Creates
parent directory if missing.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `entries` | `list[Cacheable]` | - | List of Cacheable objects to save |
| `version` | `int` | `1` | Cache version number (default: 1). Increment when format changes (new fields, removed fields, etc.) |
| `indent` | `int` | `2` | JSON indentation (default: 2). Use None for compact output. |







**Returns**


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
    store.save(tags, version=1)
```




#### `load`
```python
def load(self, entry_type: type[T], expected_version: int = 1) -> list[T]
```


Load entries from cache file (tolerant).

Deserializes entries from JSON and validates version. If version
mismatch or file missing, returns empty list (doesn't crash).

This "tolerant loading" approach ensures that builds never fail due
to stale or incompatible caches - they just rebuild from scratch.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `entry_type` | `type[T]` | - | Type to deserialize (must implement Cacheable protocol). Used to call from_cache_dict() classmethod. |
| `expected_version` | `int` | `1` | Expected cache version (default: 1). If file version doesn't match, returns empty list. |







**Returns**


`list[T]` - List of deserialized entries, or [] if:
    - File doesn't exist (no warning, normal for first build)
    - Version mismatch (warning logged)
    - Malformed JSON (error logged)
    - Deserialization fails (error logged)
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Normal load
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
```python
def exists(self) -> bool
```


Check if cache file exists.



**Returns**


`bool` - True if cache file exists, False otherwise



#### `clear`
```python
def clear(self) -> None
```


Delete cache file if it exists.

Used to force cache rebuild (e.g., after format changes).



**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
store = CacheStore(Path('.bengal/tags.json'))
    store.clear()  # Force rebuild on next build
```



---
*Generated by Bengal autodoc from `bengal/bengal/cache/cache_store.py`*

