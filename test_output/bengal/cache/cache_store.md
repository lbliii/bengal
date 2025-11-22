# cache_store

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/cache_store.py

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

*Note: Template has undefined variables. This is fallback content.*
