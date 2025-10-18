# Extensible Query System Design

**Status:** Design  
**Created:** 2025-10-18  
**Builds on:** hugo-style-collection-functions.md  
**Leverages:** Existing BuildCache and TaxonomyIndex infrastructure

---

## Overview

Design an extensible query/index system that:
1. **Leverages existing cache infrastructure** (BuildCache, TaxonomyIndex)
2. **Allows custom index registration** (users can add their own)
3. **Incrementally updates** (only rebuild changed indexes)
4. **Provides both O(1) indexes and O(n) queries** (safe defaults + power user options)

---

## Current Cache Infrastructure Analysis

### What We Have ✅

#### 1. BuildCache (`bengal/cache/build_cache.py`)
```python
class BuildCache:
    file_hashes: dict[str, str]              # File change detection
    dependencies: dict[str, set[str]]        # Dependency tracking
    page_tags: dict[str, set[str]]           # page_path → tags
    tag_to_pages: dict[str, set[str]]        # tag_slug → page_paths (inverted index)
    known_tags: set[str]                     # All tag slugs
    parsed_content: dict[str, dict]          # Cached HTML/TOC

    # Key methods
    def is_changed(file_path) -> bool
    def update_page_tags(page_path, tags) -> set[str]  # Returns affected tags
    def get_pages_for_tag(tag_slug) -> set[str]
```

**Capabilities:**
- ✅ File change detection (SHA256 hashes)
- ✅ Dependency tracking (templates, partials)
- ✅ Incremental tag index updates
- ✅ Bidirectional page↔tag mapping
- ✅ Parsed content caching

#### 2. TaxonomyIndex (`bengal/cache/taxonomy_index.py`)
```python
class TaxonomyIndex:
    tags: dict[str, TagEntry]  # tag_slug → TagEntry

    class TagEntry:
        tag_slug: str
        tag_name: str
        page_paths: list[str]
        updated_at: str
        is_valid: bool

    # Key methods
    def pages_changed(tag_slug, new_page_paths) -> bool  # Skip unchanged tags!
    def update_tag(tag_slug, tag_name, page_paths)
    def save_to_disk() / _load_from_disk()
```

**Capabilities:**
- ✅ Persistent tag-to-pages index
- ✅ Detects unchanged tags (skip regeneration)
- ✅ Incremental updates
- ✅ Validity tracking

### What We Can Build On This 🚀

Both systems use **similar patterns**:
- JSON serialization
- Incremental updates
- Change detection
- Bidirectional indexes
- Path-based keys (not object references)

We can **extend this pattern** to support arbitrary indexes!

---

## Proposed Architecture: QueryIndexRegistry

### Design Principles

1. **Extensible:** Users can register custom indexes
2. **Incremental:** Only update affected indexes
3. **Safe:** Pre-computed indexes (O(1) template access)
4. **Cacheable:** Persist to disk like TaxonomyIndex
5. **Pluggable:** Integrate with existing BuildCache

---

## Core Design

### 1. QueryIndex Base Class

```python
# bengal/cache/query_index.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from pathlib import Path

T = TypeVar('T')

@dataclass
class IndexEntry(Generic[T]):
    """Generic index entry."""
    key: str                    # Index key (e.g., 'blog', 'jane')
    values: list[str]           # Page paths
    metadata: dict[str, Any]    # Extra data (e.g., display_name)
    updated_at: str            # ISO timestamp
    hash: str                  # Content hash for change detection

class QueryIndex(ABC):
    """
    Base class for queryable indexes.

    Subclasses define:
    - What to index (e.g., by_section, by_author)
    - How to extract keys from pages
    - How to serialize/deserialize
    """

    def __init__(self, name: str, cache_path: Path):
        self.name = name
        self.cache_path = cache_path
        self.entries: dict[str, IndexEntry] = {}
        self._load_from_disk()

    @abstractmethod
    def extract_keys(self, page: "Page") -> list[tuple[str, Any]]:
        """
        Extract index keys from a page.

        Returns:
            List of (key, metadata) tuples

        Example:
            # SectionIndex
            return [('blog', {'title': 'Blog'})]

            # AuthorIndex
            author = page.metadata.get('author')
            return [(author, {'display_name': author})] if author else []
        """
        pass

    def update_page(self, page: "Page", build_cache: "BuildCache") -> set[str]:
        """
        Update index for a single page.

        Returns affected index keys for incremental regeneration.
        """
        page_path = str(page.source_path)

        # Get old keys for this page
        old_keys = self._get_keys_for_page(page_path)

        # Get new keys
        new_keys_data = self.extract_keys(page)
        new_keys = {k for k, _ in new_keys_data}

        # Find changes
        removed = old_keys - new_keys
        added = new_keys - old_keys
        unchanged = old_keys & new_keys

        # Update index
        for key in removed:
            self._remove_page_from_key(key, page_path)

        for key, metadata in new_keys_data:
            self._add_page_to_key(key, page_path, metadata)

        # Return affected keys
        return removed | added | unchanged

    def get(self, key: str) -> list[str]:
        """Get page paths for index key (O(1))."""
        entry = self.entries.get(key)
        return entry.values.copy() if entry else []

    def keys(self) -> list[str]:
        """Get all index keys."""
        return list(self.entries.keys())

    def has_changed(self, key: str, page_paths: list[str]) -> bool:
        """Check if index entry changed (for skip optimization)."""
        entry = self.entries.get(key)
        if not entry:
            return True  # New key

        # Compare as sets
        return set(entry.values) != set(page_paths)

    def save_to_disk(self) -> None:
        """Persist index to disk."""
        data = {
            'version': 1,
            'name': self.name,
            'entries': {
                key: {
                    'key': entry.key,
                    'values': entry.values,
                    'metadata': entry.metadata,
                    'updated_at': entry.updated_at,
                    'hash': entry.hash,
                }
                for key, entry in self.entries.items()
            }
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_disk(self) -> None:
        """Load index from disk."""
        if not self.cache_path.exists():
            return

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            for key, entry_data in data.get('entries', {}).items():
                self.entries[key] = IndexEntry(
                    key=entry_data['key'],
                    values=entry_data['values'],
                    metadata=entry_data.get('metadata', {}),
                    updated_at=entry_data['updated_at'],
                    hash=entry_data['hash'],
                )
        except Exception as e:
            logger.warning(f"Failed to load index {self.name}: {e}")
            self.entries = {}

    def _get_keys_for_page(self, page_path: str) -> set[str]:
        """Reverse lookup: page → keys."""
        keys = set()
        for key, entry in self.entries.items():
            if page_path in entry.values:
                keys.add(key)
        return keys

    def _add_page_to_key(self, key: str, page_path: str, metadata: dict) -> None:
        """Add page to index key."""
        if key not in self.entries:
            self.entries[key] = IndexEntry(
                key=key,
                values=[],
                metadata=metadata,
                updated_at=datetime.now().isoformat(),
                hash='',
            )

        if page_path not in self.entries[key].values:
            self.entries[key].values.append(page_path)
            self.entries[key].updated_at = datetime.now().isoformat()

    def _remove_page_from_key(self, key: str, page_path: str) -> None:
        """Remove page from index key."""
        if key in self.entries and page_path in self.entries[key].values:
            self.entries[key].values.remove(page_path)
            self.entries[key].updated_at = datetime.now().isoformat()

            # Remove empty entries
            if not self.entries[key].values:
                del self.entries[key]
```

---

### 2. Built-in Indexes

#### SectionIndex
```python
# bengal/cache/indexes/section_index.py

class SectionIndex(QueryIndex):
    """Index pages by section."""

    def __init__(self, cache_path: Path):
        super().__init__('section', cache_path)

    def extract_keys(self, page: "Page") -> list[tuple[str, Any]]:
        section_name = page._section.name if page._section else None
        if section_name:
            return [(section_name, {'title': page._section.title})]
        return []
```

**Template usage:**
```jinja2
{% set blog_posts = site.indexes.section.get('blog') %}
```

#### AuthorIndex
```python
class AuthorIndex(QueryIndex):
    """Index pages by author."""

    def extract_keys(self, page: "Page") -> list[tuple[str, Any]]:
        author = page.metadata.get('author')
        if author:
            # Support both string and object
            if isinstance(author, dict):
                name = author.get('name', '')
                email = author.get('email', '')
                return [(name, {'email': email})]
            else:
                return [(author, {})]
        return []
```

**Template usage:**
```jinja2
{% set jane_posts = site.indexes.author.get('Jane Smith') %}
```

#### CategoryIndex
```python
class CategoryIndex(QueryIndex):
    """Index pages by category (single-valued taxonomy)."""

    def extract_keys(self, page: "Page") -> list[tuple[str, Any]]:
        category = page.metadata.get('category')
        if category:
            return [(category, {})]
        return []
```

#### DateRangeIndex
```python
class DateRangeIndex(QueryIndex):
    """Index pages by date range (year, month)."""

    def extract_keys(self, page: "Page") -> list[tuple[str, Any]]:
        if not page.date:
            return []

        year = page.date.year
        month = f"{year}-{page.date.month:02d}"

        return [
            (str(year), {'type': 'year'}),
            (month, {'type': 'month'}),
        ]
```

**Template usage:**
```jinja2
{% set posts_2024 = site.indexes.date_range.get('2024') %}
{% set posts_jan = site.indexes.date_range.get('2024-01') %}
```

---

### 3. QueryIndexRegistry

```python
# bengal/cache/query_index_registry.py

class QueryIndexRegistry:
    """
    Registry for all query indexes.

    Manages index lifecycle:
    - Registration (built-in + custom)
    - Building (full + incremental)
    - Persistence
    - Template access
    """

    def __init__(self, site: "Site", cache_dir: Path):
        self.site = site
        self.cache_dir = cache_dir
        self.indexes: dict[str, QueryIndex] = {}

        # Register built-in indexes
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register default indexes."""
        from bengal.cache.indexes.section_index import SectionIndex
        from bengal.cache.indexes.author_index import AuthorIndex
        from bengal.cache.indexes.category_index import CategoryIndex
        from bengal.cache.indexes.date_range_index import DateRangeIndex

        self.register('section', SectionIndex(self.cache_dir / 'section_index.json'))
        self.register('author', AuthorIndex(self.cache_dir / 'author_index.json'))
        self.register('category', CategoryIndex(self.cache_dir / 'category_index.json'))
        self.register('date_range', DateRangeIndex(self.cache_dir / 'date_range_index.json'))

    def register(self, name: str, index: QueryIndex) -> None:
        """Register a custom index."""
        self.indexes[name] = index
        logger.debug(f"Registered index: {name}")

    def build_all(self, pages: list["Page"], build_cache: "BuildCache") -> None:
        """Build all indexes (full build)."""
        for name, index in self.indexes.items():
            logger.info(f"Building index: {name}")
            for page in pages:
                if not page.metadata.get('_generated'):
                    index.update_page(page, build_cache)
            index.save_to_disk()

    def update_incremental(
        self,
        changed_pages: list["Page"],
        build_cache: "BuildCache"
    ) -> dict[str, set[str]]:
        """
        Update indexes incrementally.

        Returns:
            Dict mapping index_name → affected_keys
        """
        affected = {}

        for name, index in self.indexes.items():
            affected_keys = set()
            for page in changed_pages:
                if not page.metadata.get('_generated'):
                    keys = index.update_page(page, build_cache)
                    affected_keys.update(keys)

            affected[name] = affected_keys
            index.save_to_disk()

        return affected

    def get(self, index_name: str) -> QueryIndex | None:
        """Get index by name."""
        return self.indexes.get(index_name)

    def save_all(self) -> None:
        """Save all indexes to disk."""
        for index in self.indexes.values():
            index.save_to_disk()
```

---

### 4. Site Integration

```python
# bengal/core/site.py

@dataclass
class Site:
    # ... existing fields ...

    # New: Query index registry
    _query_registry: QueryIndexRegistry | None = field(default=None, repr=False)

    @property
    def indexes(self) -> QueryIndexRegistry:
        """
        Access to query indexes.

        Usage in templates:
            {% set blog_posts = site.indexes.section.get('blog') %}
            {% set jane_posts = site.indexes.author.get('Jane Smith') %}
        """
        if self._query_registry is None:
            cache_dir = self.root_path / '.bengal' / 'indexes'
            self._query_registry = QueryIndexRegistry(self, cache_dir)
        return self._query_registry
```

---

### 5. Build Integration

```python
# bengal/orchestration/build.py

class BuildOrchestrator:
    def build(self, ...):
        # ... existing phases ...

        # Phase 4.5: Build/Update Query Indexes
        with self.logger.phase("query_indexes"):
            if incremental and pages_to_build:
                # Incremental: only update affected indexes
                affected = self.site.indexes.update_incremental(
                    pages_to_build,
                    build_cache
                )
                logger.info(f"Updated indexes incrementally", affected_keys=affected)
            else:
                # Full build: rebuild all indexes
                self.site.indexes.build_all(self.site.pages, build_cache)
                logger.info(f"Built all indexes")
```

---

## User-Extensible Indexes

### Custom Index Example

```python
# mysite/indexes/status_index.py

from bengal.cache.query_index import QueryIndex

class StatusIndex(QueryIndex):
    """Index pages by status field."""

    def __init__(self, cache_path):
        super().__init__('status', cache_path)

    def extract_keys(self, page):
        status = page.metadata.get('status', 'published')
        return [(status, {})]
```

### Registration in Config

```toml
# bengal.toml

[indexes]
enabled = true

# Custom indexes (optional)
[indexes.custom]
status = "mysite.indexes.status_index:StatusIndex"
priority = "mysite.indexes.priority_index:PriorityIndex"
```

### Programmatic Registration

```python
# In custom build script or plugin
from mysite.indexes.status_index import StatusIndex

def register_custom_indexes(site):
    cache_dir = site.root_path / '.bengal' / 'indexes'
    site.indexes.register('status', StatusIndex(cache_dir / 'status_index.json'))
```

---

## Template Access Patterns

### O(1) Index Lookups (Recommended)

```jinja2
{# Get all blog posts - O(1) #}
{% set blog_posts = site.indexes.section.get('blog') %}

{# Get posts by author - O(1) #}
{% set author_posts = site.indexes.author.get(page.metadata.author) %}

{# Get posts from 2024 - O(1) #}
{% set recent = site.indexes.date_range.get('2024') %}

{# Get posts by category - O(1) #}
{% set tutorials = site.indexes.category.get('tutorial') %}

{# Resolve paths to Page objects #}
{% set blog_pages = blog_posts | map(attribute='pages') | first %}
```

### O(n) Collection Queries (Power Users)

```jinja2
{# Fallback to O(n) filtering when index doesn't exist #}
{% set draft_posts = site.pages | where('draft', true) %}
{% set recent = site.pages | where_gt('date', cutoff) %}
```

---

## Performance Characteristics

### Index Building (Build-Time)

| Operation | Complexity | Cost (10K pages) |
|-----------|-----------|------------------|
| Full index build | O(n × i) | ~1s (n=pages, i=indexes) |
| Incremental update | O(m × i) | ~50ms (m=changed pages) |
| Save to disk | O(n) | ~100ms (JSON serialization) |

### Template Access (Render-Time)

| Operation | Complexity | Cost (10K pages) |
|-----------|-----------|------------------|
| Index lookup | O(1) | < 0.1ms |
| Collection filter | O(n) | 1-10ms |
| Set operations | O(n) | 1-5ms |

**Key Insight:** Indexes are **10-100x faster** than collection filters.

---

## Incremental Build Optimization

### Skip Unchanged Index Entries

```python
class QueryIndex:
    def needs_regeneration(self, key: str, page_paths: list[str]) -> bool:
        """Check if index entry needs regeneration."""
        entry = self.entries.get(key)
        if not entry:
            return True  # New entry

        # Compare page lists
        if set(entry.values) != set(page_paths):
            return True  # Pages changed

        # Check if any page content changed
        for page_path in page_paths:
            if build_cache.is_changed(Path(page_path)):
                return True  # Page content changed

        return False  # Skip regeneration
```

**Benefit:** Skip regeneration of unchanged author pages, category pages, etc.

---

## Configuration Options

```toml
# bengal.toml

[indexes]
enabled = true                    # Enable query indexes

# Built-in indexes (can be disabled)
section = true
author = true
category = true
date_range = true

# Custom indexes
[indexes.custom]
status = "mysite.indexes:StatusIndex"

# Performance tuning
[indexes.performance]
cache_results = true              # Cache query results within template
max_entries = 10000               # Max entries per index
```

---

## Migration Path

### Phase 1: Core Infrastructure (Week 1)
- Implement `QueryIndex` base class
- Implement `QueryIndexRegistry`
- Add `site.indexes` property
- Integrate with build pipeline

### Phase 2: Built-in Indexes (Week 2)
- `SectionIndex`
- `AuthorIndex`
- `CategoryIndex`
- `DateRangeIndex`

### Phase 3: Collection Functions (Week 3)
- Add safe collection functions (where_gt, where_lt, etc.)
- Add set operations (intersect, union)
- Performance warnings

### Phase 4: User Extensions (Week 4)
- Config-based custom index registration
- Documentation & examples
- Migration guide from Hugo

---

## Extensibility Points

### 1. Custom Index Types
Users can create indexes for any page attribute:
- By language (i18n)
- By reading time
- By word count
- By custom taxonomy
- By geographic location
- By any metadata field

### 2. Custom Key Extraction
```python
class GeographicIndex(QueryIndex):
    def extract_keys(self, page):
        location = page.metadata.get('location', {})
        country = location.get('country')
        city = location.get('city')

        keys = []
        if country:
            keys.append((f"country:{country}", {}))
        if city:
            keys.append((f"city:{city}", {'country': country}))
        return keys
```

### 3. Custom Aggregations
```python
class ReadingTimeIndex(QueryIndex):
    """Index by reading time ranges."""

    def extract_keys(self, page):
        words = len(page.content.split())
        reading_time = words / 200  # 200 wpm

        if reading_time < 5:
            return [('quick', {'max_minutes': 5})]
        elif reading_time < 15:
            return [('medium', {'max_minutes': 15})]
        else:
            return [('long', {'max_minutes': 999})]
```

---

## Advantages Over Dynamic Queries

| Feature | Indexes (Our Approach) | Dynamic Queries (Hugo) |
|---------|------------------------|------------------------|
| **Performance** | O(1) lookup | O(n) filtering |
| **Safety** | Can't create O(n²) | Easy to create O(n²) |
| **Incremental** | Only update changed | Must run on all pages |
| **Extensible** | Register new indexes | Limited to built-in ops |
| **Caching** | Persistent to disk | Runtime only |
| **Memory** | ~10-20MB for 10K pages | No overhead |

---

## Comparison: Index vs Query

### Use Index When:
- ✅ Lookup is by known field (section, author, tag)
- ✅ Query runs on every page render
- ✅ Large site (1000+ pages)
- ✅ Performance is critical

### Use Collection Query When:
- ✅ One-off or rare query
- ✅ Small collection (< 100 items)
- ✅ Complex conditions not worth indexing
- ✅ Prototype/experiment

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/cache/test_query_index.py

def test_section_index_extract_keys():
    """Test key extraction."""

def test_index_incremental_update():
    """Test incremental index update."""

def test_index_persistence():
    """Test save/load from disk."""

def test_registry_registration():
    """Test custom index registration."""
```

### Integration Tests
```python
# tests/integration/test_query_indexes.py

def test_full_build_with_indexes(tmp_site):
    """Test indexes built during full build."""

def test_incremental_update_indexes(tmp_site):
    """Test indexes updated incrementally."""

def test_template_index_access(tmp_site):
    """Test site.indexes access in templates."""
```

### Performance Tests
```python
# tests/performance/test_index_performance.py

def test_index_build_time():
    """Measure index build time at scale."""

def test_index_lookup_time():
    """Measure O(1) lookup performance."""

def test_index_memory_usage():
    """Measure index memory overhead."""
```

---

## Documentation Plan

### User Guide
- `docs/indexes/overview.md` - Introduction to indexes
- `docs/indexes/built-in-indexes.md` - Section, author, category, date_range
- `docs/indexes/custom-indexes.md` - Creating custom indexes
- `docs/indexes/template-usage.md` - Using indexes in templates

### API Reference
- `docs/api/query-index.md` - QueryIndex base class
- `docs/api/index-registry.md` - QueryIndexRegistry

### Migration Guide
- `docs/migration/hugo-indexes.md` - Hugo → Bengal patterns

---

## Success Metrics

1. ✅ Users can access common queries with O(1) lookups
2. ✅ Users can register custom indexes without code changes
3. ✅ Indexes update incrementally (< 100ms for single page change)
4. ✅ No performance regression on builds
5. ✅ Zero O(n²) patterns possible with recommended approach

---

## Conclusion

This design:

1. **Leverages existing cache infrastructure** (BuildCache, TaxonomyIndex patterns)
2. **Provides O(1) lookups** (no performance bombs possible)
3. **Is fully extensible** (users can register custom indexes)
4. **Updates incrementally** (like TaxonomyIndex)
5. **Is backward compatible** (no changes to existing code)

**Key Innovation:** Instead of exposing dangerous O(n) queries in templates (like Hugo), we provide safe, fast, extensible indexes that update incrementally.

**For Bengal's performance profile (100 pps vs Hugo's 1000 pps), this is the RIGHT trade-off.**
