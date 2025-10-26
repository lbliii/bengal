# RFC: Generic Cacheable Protocol for Type-Safe Cache Contracts

**Author**: AI + Human Reviewer  
**Date**: 2025-10-26  
**Status**: Draft  
**Confidence**: 82% 🟡

---

## Executive Summary

**Context**: PageCore successfully solved the Page/PageMetadata/PageProxy synchronization problem by introducing a shared base class for cacheable fields.

**Question**: Should we create similar `*Core` classes for other Bengal types (Section, Asset, MenuItem)?

**Answer**: **No** - most types don't have the same live/cached/proxy split that caused Page issues. Instead, propose a **generic Cacheable protocol** that provides type-safe caching contracts for all cacheable types without requiring individual base classes.

**Impact**:
- ✅ Prevents future cache contract bugs across all types
- ✅ Type-safe serialization/deserialization
- ✅ Minimal refactoring (~2-3 days vs weeks for individual *Core classes)
- ⚠️ Doesn't solve object reference stability (that's a separate concern)

**Confidence**: 82% (strong evidence, moderate implementation complexity)

---

## 1. Problem Statement

### What We Learned from PageCore

**PageCore solved a specific problem** (`plan/active/plan-pagecore-refactoring.md`):

```python
# Before: 3 separate representations, manual sync
Page (live object) → manual copying → PageMetadata (cache) → manual copying → PageProxy (lazy)
# Risk: Forget to update one = cache bugs

# After: Single source of truth
PageCore (shared) ← Page extends, PageMetadata IS, PageProxy wraps
# Benefit: Impossible to have mismatched fields
```

**Success metrics**:
- ✅ Adding new field: 3 changes (PageCore + 2 property delegates) instead of 10+
- ✅ Cache save/load: 1 line instead of 15
- ✅ Type checker catches missing fields at compile time

### Question: Do Other Types Need This?

From `architecture/object-model.md`, Bengal has these core types:

| Type | Current State | Cache? | Proxy? | Needs *Core? |
|------|--------------|--------|--------|-------------|
| **Page** | ✅ Has PageCore | Yes | Yes | ✅ Done |
| **Section** | No caching yet | No | No | 🟡 Maybe later |
| **Asset** | Simple files | No | No | ❌ No |
| **MenuItem** | Built from config | No | No | ❌ No |
| **TagEntry** | Cache-only | Yes | No | ❌ No (no live object) |

**Key insight**: Only Page had the problematic **three-way split** (live → cache → proxy). Other types don't have this pattern.

### Evidence from Codebase

**Section** (`bengal/core/section.py:32-63`):
```python
@dataclass
class Section:
    name: str = "root"
    path: Path = Path(".")
    pages: list[Page] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: Page | None = None
    parent: Section | None = None
```

**Observation**: No `SectionMetadata` or `SectionProxy` exists. Sections are always loaded fully because:
1. Section structure is lightweight (just metadata, not content)
2. Site discovery needs full section tree anyway
3. No incremental section loading (yet)

**Asset** (`bengal/core/asset.py:20-42`):
```python
@dataclass
class Asset:
    source_path: Path
    output_path: Path | None = None
    asset_type: str | None = None
    fingerprint: str | None = None
    minified: bool = False
    optimized: bool = False
    bundled: bool = False
```

**Observation**: Assets are processing metadata only. No lazy loading, no caching, no proxy pattern.

**TagEntry** (`bengal/cache/taxonomy_index.py:34-61`):
```python
@dataclass
class TagEntry:
    tag_slug: str
    tag_name: str
    page_paths: list[str]
    updated_at: str
    is_valid: bool = True

    def to_dict(self) -> dict[str, Any]: ...
    @staticmethod
    def from_dict(data: dict[str, Any]) -> TagEntry: ...
```

**Observation**: Already cache-only (no separate live object). Has serialization methods but manual.

### The Real Pattern: Cache Serialization

Looking at all cache types in `bengal/cache/`:

```python
# page_discovery_cache.py
class PageMetadata:  # Now alias to PageCore
    def to_dict() -> dict: ...  # Auto from dataclass

# taxonomy_index.py
class TagEntry:
    def to_dict(self) -> dict: ...  # Manual
    @staticmethod
    def from_dict(data: dict) -> TagEntry: ...  # Manual

# build_cache.py
class BuildCache:
    # No explicit to_dict/from_dict, uses __dict__

# asset_dependency_map.py
class AssetDependencyEntry:
    # No serialization methods, manual in parent class
```

**Problem**: Inconsistent serialization patterns, no type safety, no contract enforcement.

---

## 2. Goals & Non-Goals

### Goals

1. **Type-Safe Caching**: All cacheable types implement a standard protocol
2. **Consistent Serialization**: Uniform to_dict/from_dict pattern across codebase
3. **Compiler Validation**: Type checker catches missing serialization methods
4. **Future-Proof**: Easy to add new cacheable types without reinventing serialization
5. **Minimal Refactoring**: Don't require splitting existing types into *Core classes

### Non-Goals

1. **Not forcing *Core pattern**: Section/Asset/MenuItem don't need base classes
2. **Not solving object references**: PageProxy stability is separate concern
3. **Not changing cache formats**: Keep existing JSON structures
4. **Not adding features**: Pure refactoring, no new capabilities
5. **Not unifying all caches**: Some caches (like BuildCache) are fine as-is

---

## 3. Design Options

### Option 1: Individual *Core Classes (NOT RECOMMENDED)

**Approach**: Create SectionCore, AssetCore, MenuItemCore like PageCore

```python
# bengal/core/section_core.py
@dataclass
class SectionCore:
    path: Path
    name: str
    title: str
    weight: int | None
    metadata: dict[str, Any]

# bengal/core/section.py
@dataclass
class Section:
    core: SectionCore
    pages: list[Page]
    subsections: list[Section]
    # ... delegate properties
```

**Benefits**:
- ✅ Consistent with PageCore pattern
- ✅ Clear separation of cacheable vs non-cacheable

**Drawbacks**:
- ❌ Massive refactoring (weeks of work)
- ❌ Breaks existing API (`section.name` → `section.core.name`)
- ❌ Solves a problem that doesn't exist (Section has no cache/proxy split)
- ❌ Property delegation overhead for no benefit

**Confidence Impact**: -20% (over-engineering, high cost for low benefit)

---

### Option 2: Generic Cacheable Protocol (RECOMMENDED)

**Approach**: Define a protocol that cacheable types implement

```python
# bengal/cache/cacheable.py
from typing import Protocol, TypeVar, Any, runtime_checkable

T = TypeVar('T', bound='Cacheable')

@runtime_checkable
class Cacheable(Protocol):
    """
    Protocol for types that can be cached to disk.

    Types implementing this protocol can be automatically serialized
    to JSON and deserialized, with type checker validation.

    Example:
        @dataclass
        class PageCore(Cacheable):
            title: str
            date: datetime | None

            def to_cache_dict(self) -> dict[str, Any]:
                return {
                    'title': self.title,
                    'date': self.date.isoformat() if self.date else None
                }

            @classmethod
            def from_cache_dict(cls, data: dict[str, Any]) -> 'PageCore':
                return cls(
                    title=data['title'],
                    date=datetime.fromisoformat(data['date']) if data['date'] else None
                )
    """

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize to cache-friendly dictionary.

        Must return JSON-serializable types (str, int, float, bool, None, list, dict).
        Complex types (Path, datetime) must be converted to strings.

        Returns:
            Dictionary suitable for JSON serialization
        """
        ...

    @classmethod
    def from_cache_dict(cls: type[T], data: dict[str, Any]) -> T:
        """
        Deserialize from cache dictionary.

        Must be inverse of to_cache_dict():
        assert obj == cls.from_cache_dict(obj.to_cache_dict())

        Args:
            data: Dictionary from cache (JSON-deserialized)

        Returns:
            Reconstructed instance
        """
        ...
```

**Usage Example 1: PageCore (already exists, adopt protocol)**

```python
# bengal/core/page/page_core.py
from bengal.cache.cacheable import Cacheable

@dataclass
class PageCore(Cacheable):  # Explicitly implement protocol
    source_path: str
    title: str
    date: datetime | None
    tags: list[str]
    # ... other fields

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dict."""
        return {
            'source_path': self.source_path,
            'title': self.title,
            'date': self.date.isoformat() if self.date else None,
            'tags': self.tags,
            # ... other fields
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> 'PageCore':
        """Deserialize from cache dict."""
        return cls(
            source_path=data['source_path'],
            title=data['title'],
            date=datetime.fromisoformat(data['date']) if data['date'] else None,
            tags=data['tags'],
            # ... other fields
        )
```

**Usage Example 2: TagEntry (retrofit existing)**

```python
# bengal/cache/taxonomy_index.py
from bengal.cache.cacheable import Cacheable

@dataclass
class TagEntry(Cacheable):  # Add protocol
    tag_slug: str
    tag_name: str
    page_paths: list[str]
    updated_at: str
    is_valid: bool = True

    # Rename to match protocol (backward compat alias below)
    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "tag_slug": self.tag_slug,
            "tag_name": self.tag_name,
            "page_paths": self.page_paths,
            "updated_at": self.updated_at,
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> 'TagEntry':
        return cls(
            tag_slug=data["tag_slug"],
            tag_name=data["tag_name"],
            page_paths=data["page_paths"],
            updated_at=data["updated_at"],
            is_valid=data.get("is_valid", True),
        )

    # Backward compatibility (deprecate later)
    def to_dict(self) -> dict[str, Any]:
        return self.to_cache_dict()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'TagEntry':
        return TagEntry.from_cache_dict(data)
```

**Usage Example 3: Generic Cache Helper**

```python
# bengal/cache/cache_store.py
from pathlib import Path
import json
from typing import TypeVar, Type
from bengal.cache.cacheable import Cacheable

T = TypeVar('T', bound=Cacheable)

class CacheStore:
    """Generic cache storage for Cacheable types."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path

    def save(self, entries: list[Cacheable], version: int = 1) -> None:
        """Save entries to cache (type-safe)."""
        data = {
            'version': version,
            'entries': [entry.to_cache_dict() for entry in entries]
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, entry_type: Type[T], expected_version: int = 1) -> list[T]:
        """Load entries from cache (type-safe)."""
        if not self.cache_path.exists():
            return []

        with open(self.cache_path) as f:
            data = json.load(f)

        if data.get('version') != expected_version:
            return []  # Version mismatch

        return [
            entry_type.from_cache_dict(entry_data)
            for entry_data in data.get('entries', [])
        ]

# Usage:
store = CacheStore(Path('.bengal/tags.json'))
store.save([tag_entry1, tag_entry2], version=1)
tags = store.load(TagEntry, expected_version=1)
```

**Benefits**:
- ✅ Type-safe: `mypy` validates protocol implementation
- ✅ Minimal refactoring: Add protocol to existing types
- ✅ Consistent: All caches use same pattern
- ✅ Testable: Protocol ensures to_cache_dict/from_cache_dict are inverses
- ✅ Future-proof: Easy to add new cacheable types

**Drawbacks**:
- ⚠️ Protocol adoption is gradual (can't force overnight)
- ⚠️ Need to retrofit existing types

**Confidence Impact**: +15% (practical, low-risk, high-value)

---

### Option 3: Pydantic Models (Industry Standard)

**Approach**: Use Pydantic BaseModel for all cacheable types

```python
from pydantic import BaseModel, Field
from datetime import datetime

class PageCore(BaseModel):
    """Cacheable page metadata."""
    source_path: str
    title: str
    date: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        # Auto-convert from dict/object
        from_attributes = True
        # JSON serialization
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# Usage (automatic serialization!)
page_core = PageCore(source_path="content/post.md", title="Hello")
json_str = page_core.model_dump_json()  # Auto serialize
loaded = PageCore.model_validate_json(json_str)  # Auto deserialize
```

**Benefits**:
- ✅ Industry standard (FastAPI, Django Ninja use this)
- ✅ Auto JSON serialization/deserialization
- ✅ Built-in validation (type checking at runtime)
- ✅ Great documentation and ecosystem
- ✅ Handles complex types (datetime, Path) automatically

**Drawbacks**:
- ❌ New dependency (~600KB, pulls in typing-extensions)
- ❌ Slower than dataclasses (~2-3x overhead)
- ❌ Requires learning Pydantic patterns
- ❌ May be overkill for internal caching

**Confidence Impact**: +5% (proven tech, but adds complexity)

---

### Option 4: Dataclass with Auto-Serialization Decorator

**Approach**: Decorator that auto-generates to_cache_dict/from_cache_dict

```python
# bengal/cache/auto_cacheable.py
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, get_type_hints

def cacheable(cls):
    """
    Decorator that auto-generates cache serialization methods.

    Works with @dataclass to automatically create to_cache_dict/from_cache_dict
    based on field types.

    Example:
        @cacheable
        @dataclass
        class PageCore:
            title: str
            date: datetime | None
            # to_cache_dict/from_cache_dict auto-generated!
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass")

    def to_cache_dict(self) -> dict[str, Any]:
        """Auto-generated cache serialization."""
        result = {}
        for field in fields(self):
            value = getattr(self, field.name)

            # Handle special types
            if isinstance(value, datetime):
                result[field.name] = value.isoformat() if value else None
            elif isinstance(value, Path):
                result[field.name] = str(value)
            elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                result[field.name] = value
            else:
                # Fallback: try to convert to dict
                result[field.name] = str(value)

        return result

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]):
        """Auto-generated cache deserialization."""
        hints = get_type_hints(cls)
        kwargs = {}

        for field in fields(cls):
            value = data.get(field.name)
            hint = hints.get(field.name)

            # Handle special types
            if hint == datetime or hint == datetime | None:
                kwargs[field.name] = datetime.fromisoformat(value) if value else None
            elif hint == Path or hint == Path | None:
                kwargs[field.name] = Path(value) if value else None
            else:
                kwargs[field.name] = value

        return cls(**kwargs)

    # Attach methods to class
    cls.to_cache_dict = to_cache_dict
    cls.from_cache_dict = from_cache_dict

    return cls

# Usage:
@cacheable
@dataclass
class PageCore:
    title: str
    date: datetime | None
    tags: list[str]
    # Serialization auto-generated from field types!
```

**Benefits**:
- ✅ Zero boilerplate (auto-generates from dataclass fields)
- ✅ Type-safe (uses type hints)
- ✅ No dependencies
- ✅ Fast (generates code at class definition time)

**Drawbacks**:
- ⚠️ Magic (harder to debug than explicit methods)
- ⚠️ Limited to simple types (complex types need custom handling)
- ⚠️ Type hints must be accurate

**Confidence Impact**: +10% (elegant, but magic can be tricky)

---

## 4. Recommended Approach

### Primary: Option 2 (Cacheable Protocol)

**Why**:
1. **Solves the real problem**: Type-safe cache contracts without over-engineering
2. **Practical**: Gradual adoption, doesn't require massive refactoring
3. **Type-safe**: Mypy validates protocol implementation
4. **Consistent**: All caches use same pattern

**Implementation Plan** (2-3 days):

#### Phase 1: Create Protocol (Day 1, 4 hours)

1. **Task 1.1**: Create `bengal/cache/cacheable.py` with protocol definition
2. **Task 1.2**: Add comprehensive docstrings with examples
3. **Task 1.3**: Add unit tests for protocol validation
4. **Task 1.4**: Add `CacheStore` generic helper class

#### Phase 2: Adopt in Existing Types (Day 1-2, 8 hours)

1. **Task 2.1**: PageCore implements protocol (already has methods, just add protocol)
2. **Task 2.2**: TagEntry adopts protocol (rename to_dict → to_cache_dict)
3. **Task 2.3**: AssetDependencyEntry adopts protocol
4. **Task 2.4**: BuildCache considers adoption (may not need it)

#### Phase 3: Documentation (Day 2-3, 4 hours)

1. **Task 3.1**: Update CONTRIBUTING.md with Cacheable pattern
2. **Task 3.2**: Add examples to architecture/cache.md
3. **Task 3.3**: Update CHANGELOG.md

**Success Criteria**:
- ✅ All cacheable types implement protocol
- ✅ Mypy validates protocol implementation
- ✅ to_cache_dict/from_cache_dict are inverses (property tests)
- ✅ CacheStore works with all cacheable types

### Secondary: Option 4 (Auto-Serialization Decorator)

**When to use**: If Option 2 feels too manual, add `@cacheable` decorator on top of protocol for types with simple fields.

**Hybrid approach**:
```python
# Simple types: Use decorator
@cacheable
@dataclass
class TagEntry(Cacheable):  # Protocol for type checking
    tag_slug: str
    tag_name: str
    page_paths: list[str]
    # to_cache_dict/from_cache_dict auto-generated!

# Complex types: Manual implementation
@dataclass
class PageCore(Cacheable):
    title: str
    date: datetime | None
    _section: Section | None  # Complex reference

    def to_cache_dict(self) -> dict[str, Any]:
        # Custom logic for Section reference
        return {
            'title': self.title,
            'date': self.date.isoformat() if self.date else None,
            'section_path': str(self._section.path) if self._section else None
        }
```

---

## 5. When to Create *Core Classes

Based on PageCore success, here are criteria for when to create a `*Core` base class:

### ✅ DO Create *Core When:

1. **Three-way split exists**: Live object → Cache metadata → Lazy proxy
2. **Template access**: Templates access many properties (lazy loading matters)
3. **Manual sync pain**: Adding fields requires updates in 3+ places
4. **Cache bugs occur**: Mismatched fields cause production issues

**Example**: PageCore solved all 4 problems

### ❌ DON'T Create *Core When:

1. **No caching**: Type is always loaded fully (Section, Asset currently)
2. **Cache-only**: No separate live object (TagEntry)
3. **Simple fields**: Just file paths and flags (Asset)
4. **No proxy pattern**: No lazy loading needed

### 🟡 MAYBE Create *Core When:

1. **Future caching planned**: If you anticipate adding caching later (Section?)
2. **Performance bottleneck**: If loading becomes slow (MenuItem builds?)

**Recommendation**: Use Cacheable protocol first, promote to *Core only if three-way split emerges.

---

## 6. Future: SectionCore?

**Should we create SectionCore?**

**Current State** (`bengal/core/section.py:32`):
- Sections always fully loaded (no proxy)
- No SectionMetadata cache exists
- Discovery needs full section tree anyway

**When SectionCore would make sense**:
1. **If** we add section caching for faster dev server startup
2. **If** we add lazy section loading (only load when accessed)
3. **If** section hierarchy becomes performance bottleneck

**Evidence from architecture**:
```python
# From architecture/object-model.md:436
Section:
  - Represents folder-based grouping
  - Properties: regular_pages, sections, metadata
  - No mention of caching or lazy loading
```

**Recommendation**: **Defer SectionCore** until we have evidence that section caching is needed. Use Cacheable protocol if we add caching.

---

## 7. Architecture Impact

### Affected Subsystems

#### **Cache** (`bengal/cache/`)
**Impact**: MEDIUM - Add protocol and helpers

- **New files**:
  - `cacheable.py` - Protocol definition
  - `cache_store.py` - Generic cache helper

- **Modified files**:
  - `page_discovery_cache.py` - PageCore implements protocol
  - `taxonomy_index.py` - TagEntry implements protocol
  - `asset_dependency_map.py` - AssetDependencyEntry implements protocol

#### **Core** (`bengal/core/`)
**Impact**: LOW - PageCore adopts protocol

- **Modified files**:
  - `page/page_core.py` - Add protocol implementation

#### **Documentation**
**Impact**: LOW - Document new pattern

- **Modified files**:
  - `CONTRIBUTING.md` - Add Cacheable pattern guidelines
  - `architecture/cache.md` - Document protocol usage

---

## 8. Evidence & Confidence

### Evidence Supporting Recommendation

**From PageCore refactoring** (`plan/active/plan-pagecore-refactoring.md:22-27`):
```
Key Benefits:
- ✅ Type-safe field contract (compiler enforces)
- ✅ Single source of truth (add field once, works everywhere)
- ✅ Zero runtime overhead (direct field access)
- ✅ Prevents cache bugs (impossible to have mismatched Page/PageMetadata/PageProxy)
```

**From RFC cache-proxy contract** (`plan/active/rfc-cache-proxy-contract.md:83-89`):
```
Another bug (same week):
1. Cascading frontmatter added `type: doc` to pages
2. ❌ PageMetadata didn't include `type` field → cache saved `type: None`
3. ❌ Cache was saved BEFORE cascades applied → wrong timing
4. ❌ Dev server loaded wrong page types → wrong layouts
```

**From codebase grep**:
- `PageDiscoveryCacheEntry` - Has to_dict (manual)
- `TagEntry` - Has to_dict/from_dict (manual)
- `IndexEntry` - Generic but no serialization protocol
- `AssetDependencyEntry` - Manual serialization in parent

### Confidence Breakdown

```
Confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)

Evidence (35/40):
- ✅ PageCore proves pattern works (10)
- ✅ Examined all core types in codebase (10)
- ✅ Grep'd all cache dataclasses (10)
- ⚠️ No evidence SectionCore needed (yet) (-5)

Consistency (28/30):
- ✅ Consistent with PageCore success (10)
- ✅ Protocol pattern used elsewhere in Python (typing) (10)
- ✅ Matches architecture principles (modularity) (8)

Recency (13/15):
- ✅ Based on current codebase (Oct 2025) (10)
- ⚠️ Future Section caching is speculation (-2)

Tests (10/15):
- ✅ PageCore implementation is tested (5)
- ⚠️ Protocol would need new tests (0)
- ⚠️ No integration tests for generic pattern yet (-5)

Total: 86/100 = 86% → Rounded to 82% (conservative)
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Protocol adoption slow | Medium | Start with new code, retrofit gradually |
| Mypy doesn't catch bugs | Low | Add runtime checks with `isinstance(obj, Cacheable)` |
| Over-engineering | Low | Protocol is lightweight, easy to remove if not useful |
| Breaking changes | Low | Protocol is additive, doesn't change existing APIs |

---

## 9. Alternatives Considered

### Do Nothing (Keep Manual Serialization)

**Pros**:
- No work required
- Existing code works

**Cons**:
- Inconsistent patterns across codebase
- No type safety for cache contracts
- Manual serialization error-prone

**Verdict**: Not recommended - PageCore success shows value of enforced contracts

### Create *Core for Everything

**Pros**:
- Consistent pattern across all types
- Clear separation of cacheable/non-cacheable

**Cons**:
- Massive refactoring effort (weeks)
- Solves problems that don't exist (Section has no proxy)
- Property delegation overhead for no benefit

**Verdict**: Not recommended - over-engineering

---

## 10. Success Metrics

### Phase 1 Success (Protocol Created)
- ✅ `bengal/cache/cacheable.py` exists with Protocol
- ✅ `CacheStore` generic helper works
- ✅ Unit tests validate protocol contract
- ✅ Mypy validates protocol implementation

### Phase 2 Success (Adoption)
- ✅ PageCore implements Cacheable
- ✅ TagEntry implements Cacheable
- ✅ At least 2 cache types use protocol
- ✅ All protocol implementations have roundtrip tests

### Phase 3 Success (Documentation)
- ✅ CONTRIBUTING.md documents Cacheable pattern
- ✅ Examples in architecture/cache.md
- ✅ CHANGELOG.md updated
- ✅ Contributors know when to use protocol

### Long-term Success (6 months)
- ✅ All new cache types use protocol
- ✅ No cache contract bugs (like PageMetadata.type issue)
- ✅ Code reviews catch missing protocol implementation
- ✅ Pattern feels natural to contributors

---

## 11. Open Questions

1. **Should we add runtime validation?**
   - Option: `assert isinstance(obj, Cacheable)` before caching
   - Trade-off: Safety vs performance overhead

2. **Should @cacheable decorator be part of initial release?**
   - Pro: Less boilerplate for simple types
   - Con: Magic can be confusing

3. **Should we version the protocol?**
   - Option: `CacheableV1`, `CacheableV2` for breaking changes
   - Trade-off: Flexibility vs complexity

4. **Should BuildCache adopt this?**
   - BuildCache uses pickle, not JSON
   - May not need same serialization pattern

---

## 12. Decision

**Recommendation**: Implement **Option 2 (Cacheable Protocol)** with gradual adoption.

**Rationale**:
1. Solves real problem (inconsistent cache serialization) without over-engineering
2. Type-safe and testable
3. Low risk (additive, doesn't break existing code)
4. Practical (2-3 days vs weeks for *Core classes)

**Next Steps**:
1. Get approval from human reviewer
2. Create implementation plan similar to `plan-pagecore-refactoring.md`
3. Start with Phase 1 (protocol definition)
4. Adopt incrementally in existing types

---

## 13. Appendix: When You Actually Need *Core

### Decision Tree

```
Does the type have a three-way split?
(Live Object → Cache Metadata → Lazy Proxy)
│
├─ YES → Consider *Core base class
│   │
│   ├─ Templates access many properties? → *Core highly recommended
│   └─ Simple type with few properties? → Cacheable protocol sufficient
│
└─ NO → Use Cacheable protocol only
    │
    ├─ Cache-only type (no live object)? → Cacheable protocol
    ├─ Always fully loaded? → No caching needed
    └─ Simple files (Asset-like)? → No caching needed
```

### Examples

| Type | Three-way? | Templates? | Recommendation |
|------|-----------|-----------|----------------|
| Page | ✅ Yes | ✅ Yes | ✅ PageCore (done!) |
| Section | ❌ No (yet) | 🟡 Some | 🟡 Defer until caching added |
| Asset | ❌ No | ❌ No | ❌ No *Core needed |
| MenuItem | ❌ No | ✅ Yes | 🟡 Cacheable if menu caching added |
| TagEntry | ❌ Cache-only | N/A | ✅ Cacheable protocol |

---

**Status**: Ready for review  
**Next Command**: `::plan` to break down into implementation tasks  
**Estimated Effort**: 2-3 days (16-24 hours)


## 14. Protocol Contract and Guidelines

This section formalizes the serialization contract, versioning rules, testing expectations, and migration guidance to ensure consistent adoption of the Cacheable protocol across caches.

### 14.1 Serialization Contract (MUST)

All `Cacheable` implementations MUST adhere to the following rules:

- JSON primitives only: `str`, `int`, `float`, `bool`, `None`, `list`, `dict`.
- Datetime values MUST be serialized as ISO-8601 strings (e.g., via `datetime.isoformat()`), and parsed on load.
- `Path` values MUST be serialized as `str`.
- `set` values MUST be serialized as sorted `list` for stability across runs.
- No object references: Never persist live objects (`Page`, `Section`, `Asset`, etc.). Use stable identifiers (usually string paths).
- Stable keys: Field names are the contract; adding/removing fields requires a version bump as described below.

Invariant:

- `T.from_cache_dict(obj.to_cache_dict())` MUST reconstruct an equivalent object (`==` by fields) for all `Cacheable` types.

### 14.2 Versioning Guidelines (SHOULD)

- Each cache file SHOULD include a top-level integer `version` field.
- On version mismatch or malformed content, loaders SHOULD return an empty/fresh structure and log a warning, then proceed (tolerant load).
- Existing caches:
  - `taxonomy_index.json` and `asset_deps.json` already use `version`. Keep current behavior (warn, then rebuild empty on mismatch).
  - `page_metadata.json` currently omits a version. Recommendation: introduce `version = 1` when adopting `CacheStore` (or equivalent) for this file. Until then, tolerate format changes by failing load and rebuilding (current behavior).

### 14.3 Backward Compatibility and Deprecations (MUST/SHOULD)

- Renames: When adopting the protocol, prefer `to_cache_dict` / `from_cache_dict` method names.
- For existing types with `to_dict` / `from_dict`:
  - Provide shim methods that delegate to the new names for one minor release.
  - Emit a deprecation warning (once-per-process) on use of legacy methods.
  - Remove shims in the subsequent minor release.

### 14.4 Test Contract (MUST)

For each `Cacheable` type:

- Roundtrip test: Assert `obj == T.from_cache_dict(obj.to_cache_dict())` for representative instances (including optional/edge fields).
- Property tests (where applicable):
  - Order-insensitivity for sets serialized as lists (e.g., compare as sets after load).
  - Datetime roundtrip via ISO strings.
  - Paths roundtrip from `str`.

Cache file tests:

- Loader tolerance: On malformed JSON or version mismatch, loaders return an empty/fresh structure and log a warning.

### 14.5 Naming Conventions and Helpers (SHOULD)

- Method names: `to_cache_dict(self) -> dict[str, Any]` and `@classmethod from_cache_dict(cls, data: dict[str, Any]) -> T`.
- Generic helper: Provide `bengal/cache/cache_store.py` implementing a typed `CacheStore` with `save(List[Cacheable])` and `load(Type[T])` that handles top-level `version` and directory creation.

### 14.6 Timing Guarantees (MUST for Page Discovery)

- `PageCore` serialization for `page_metadata.json` MUST occur AFTER cascades are applied (section-derived fields like `type`, `layout`, etc.), to prevent stale or default values from being persisted. This matches current build behavior and must be preserved.

### 14.7 Scope Clarification: BuildCache (OUT OF SCOPE)

- `BuildCache` persists sets and various derived structures with a tolerant loader and custom save semantics. Adopting the `Cacheable` protocol here is optional and NOT recommended at this time.

### 14.8 Optional Runtime Validation (MAY)

- A lightweight helper (development-only) MAY be introduced: `require_cacheable(obj)` that verifies presence of `to_cache_dict`/`from_cache_dict` and checks that `to_cache_dict` only emits JSON-compatible values. This can be gated by a debug flag to avoid runtime overhead in production.
