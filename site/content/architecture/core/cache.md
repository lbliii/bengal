---
title: Build Cache
description: Intelligent caching system for incremental builds.
weight: 20
category: core
tags: [core, caching, incremental-builds, performance, dependency-tracking, cache]
keywords: [cache, caching, incremental builds, dependency tracking, file hashing, performance]
---

# Cache System

Bengal implements an intelligent caching system that enables sub-second incremental rebuilds.

## How It Works

The build cache (`.bengal-cache.json`) tracks the state of your project to determine exactly what needs to be rebuilt.

```mermaid
flowchart TD
    Start[Start Build] --> Load[Load Cache]
    Load --> Detect[Detect Changes]

    Detect --> Config{Config Changed?}
    Config -->|Yes| Full[Full Rebuild]

    Config -->|No| Hash[Check File Hashes]
    Hash --> DepGraph[Query Dependency Graph]

    DepGraph --> Filter[Filter Work]
    Filter --> Render[Render Affected Pages]

    Render --> Update[Update Cache]
    Update --> Save[Save to Disk]
```

## Caching Strategies

::::{tab-set}
:::{tab-item} File Hashing
**Change Detection**

We use **SHA256** hashing to detect file changes.
- Content files (`.md`)
- Templates (`.html`, `.jinja2`)
- Config files (`.toml`)
- Assets (`.css`, `.js`)
:::

:::{tab-item} Dependency Graph
**Impact Analysis**

We track relationships to know what to rebuild.
- **Page → Template**: If `post.html` changes, rebuild all blog posts.
- **Tag → Pages**: If `python` tag changes, rebuild `tags/python/` page.
- **Page → Partial**: If `header.html` changes, rebuild everything.
:::

:::{tab-item} Inverted Index
**Taxonomy Lookup**

We store an inverted index of tags to avoid parsing all pages.
- **Stored**: `tag_to_pages['python'] = ['post1.md', 'post2.md']`
- **Benefit**: O(1) lookup for taxonomy page generation.
:::
::::

## The "No Object References" Rule

:::{card} Architecture Principle
**Never persist object references across builds.**
:::

The cache **only** stores:
1.  File paths (strings)
2.  Hashes (strings)
3.  Simple metadata (dicts/lists)

This ensures cache stability. When a build starts, we load the cache and **reconstruct** the relationships with fresh live objects.

## Cacheable Protocol

Bengal uses a `Cacheable` protocol to enforce type-safe cache contracts across all cacheable types. This ensures consistent serialization, prevents cache bugs, and enables compile-time validation.

### Protocol Definition

```python
@runtime_checkable
class Cacheable(Protocol):
    """Protocol for types that can be cached to disk."""

    def to_cache_dict(self) -> dict[str, Any]:
        """Return JSON-serializable data only."""
        ...

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> Cacheable:
        """Reconstruct object from data."""
        ...
```

### Contract Requirements

1. **JSON Primitives Only**: `to_cache_dict()` must return only JSON-serializable types (str, int, float, bool, None, list, dict)
2. **Type Conversion**: Complex types must be converted:
   - `datetime` → ISO-8601 string (via `datetime.isoformat()`)
   - `Path` → str (via `str(path)`)
   - `set` → sorted list (for stability)
3. **No Object References**: Never serialize live objects (Page, Section, Asset). Use stable identifiers (usually string paths) instead.
4. **Round-trip Invariant**: `T.from_cache_dict(obj.to_cache_dict())` must reconstruct an equivalent object (== by fields)
5. **Stable Keys**: Field names in `to_cache_dict()` are the contract. Adding/removing fields requires version bump in cache file.

### Types Implementing Cacheable

| Type | Location | Purpose |
|------|----------|---------|
| `PageCore` | `bengal/core/page/page_core.py` | Cacheable page metadata (title, date, tags, etc.) |
| `TagEntry` | `bengal/cache/taxonomy_index.py` | Taxonomy index entries |
| `IndexEntry` | `bengal/cache/query_index.py` | Query index entries |
| `AssetDependencyEntry` | `bengal/cache/asset_dependency_map.py` | Asset dependency tracking |

### Example Implementation

```python
@dataclass
class PageCore(Cacheable):
    source_path: str
    title: str
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize PageCore to cache-friendly dictionary."""
        return {
            "source_path": self.source_path,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "tags": self.tags,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> PageCore:
        """Deserialize PageCore from cache dictionary."""
        return cls(
            source_path=data["source_path"],
            title=data["title"],
            date=datetime.fromisoformat(data["date"]) if data.get("date") else None,
            tags=data.get("tags", []),
        )
```

### Generic CacheStore Helper

Bengal provides a generic `CacheStore` helper for type-safe cache operations:

```python
from bengal.cache.cache_store import CacheStore

# Type-safe cache operations
store = CacheStore[PageCore](cache_path)
store.save([page1.core, page2.core])  # List of Cacheable objects
entries = store.load()  # Returns list[PageCore]
```

### Benefits

- **Type Safety**: Static type checkers (mypy) validate cache contracts at compile time
- **Consistency**: All cache entries follow the same serialization pattern
- **Versioning**: Built-in version checking for cache invalidation
- **Safety**: Prevents accidental pickling of complex objects that might break across versions
- **Performance**: Protocol has zero runtime overhead (structural typing)

### PageCore Serialization

With PageCore, cache serialization is simplified:

```python
# Before: Manual field mapping (error-prone)
cache_data = {
    "source_path": str(page.source_path),
    "title": page.title,
    "date": page.date.isoformat() if page.date else None,
    # ... 10+ more fields
}

# After: Single line using PageCore
from dataclasses import asdict
cache_data = asdict(page.core)  # All cacheable fields serialized
```

### Runtime Validation

The `@runtime_checkable` decorator allows `isinstance()` checks:

```python
from bengal.cache.cacheable import Cacheable

if isinstance(obj, Cacheable):
    data = obj.to_cache_dict()
    # Safe to serialize
```

However, static type checking via mypy is the primary validation method.

See: `bengal/cache/cacheable.py` for full protocol definition and examples.
