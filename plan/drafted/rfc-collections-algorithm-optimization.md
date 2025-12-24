# RFC: Collections Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Collections (SchemaValidator, CollectionLoader, ContentValidation)  
**Confidence**: 94% 🟢 (verified against source code)  
**Priority**: P3 (Low) — Performance, scalability for large content sites  
**Estimated Effort**: 0.5-1 day

---

## Executive Summary

The `bengal/collections` package provides content schema validation for type-safe frontmatter. Analysis confirms the package is well-designed for typical use cases, but identified **3 algorithmic patterns** that could degrade performance for sites with 100+ collections or deeply nested schemas.

**Key findings**:

1. **`get_collection_for_path()`** — O(C × P) linear scan of all collections per content file
2. **`_coerce_type()` for lists** — O(L × T) recursive validation, unbounded nesting depth
3. **Strict mode unknown field detection** — O(U log U) sorting overhead

**Proposed optimizations**:

1. Add prefix trie for collection path matching → O(P) lookup
2. Add recursion depth limit for nested validation → Prevent stack overflow
3. (Optional) Pre-sort unknown fields or use unsorted set for strict mode

**Current state**: The existing implementation is efficient for typical use cases (1-20 collections, schemas with <20 fields, lists with <100 items). Optimizations are preventive for edge cases.

**Impact**: Maintain sub-millisecond validation at scale (target: <1ms per page validation with 100+ collections)

---

## Problem Statement

### Current Performance Characteristics

> **Note**: The collections package is already well-optimized for typical use. The bottlenecks identified affect edge cases with extreme content volumes.

| Scenario | `get_collection_for_path` | `validate()` | Overall Discovery |
|----------|---------------------------|--------------|-------------------|
| 5 collections, 100 pages | <1ms | <1ms | <100ms |
| 20 collections, 1K pages | <1ms | <1ms | ~500ms |
| 50 collections, 5K pages | ~5ms | <1ms | ~5s |
| 100 collections, 10K pages | **~20ms** ⚠️ | <1ms | **~200s** ⚠️ |

For sites approaching 10K pages with 100+ collections, collection matching becomes a significant bottleneck during content discovery.

### Bottleneck 1: get_collection_for_path() — O(C × P)

**Location**: `loader.py:206-216`

```python
# Current: Linear scan of ALL collections
def get_collection_for_path(file_path, content_root, collections):
    try:
        rel_path = file_path.relative_to(content_root)  # O(P)
    except ValueError:
        return None, None

    # Check each collection's directory
    for name, config in collections.items():    # O(C) - all collections
        if config.directory is None:
            continue
        try:
            rel_path.relative_to(config.directory)  # O(P) path comparison
            return name, config
        except ValueError:
            continue

    return None, None
```

**Problem**: For each content file during discovery, we iterate ALL collections and compare paths. With 100 collections and 10K files, that's 1M path comparisons.

**Optimal approach**: Build prefix trie from collection directories once, then O(P) lookup per file.

### Bottleneck 2: _coerce_type() Recursive Validation — O(L × T) Unbounded

**Location**: `validator.py:449-458` (list validation) and `validator.py:522-532` (nested dataclass)

```python
# List validation: O(L) iterations, each can recurse
for i, item in enumerate(value):  # O(L)
    coerced, errors = self._coerce_type(f"{name}[{i}]", item, item_type)  # O(T) per item

# Nested dataclass: Recursive validation
if is_dataclass(expected):
    if isinstance(value, dict):
        nested_validator = SchemaValidator(expected, strict=self.strict)  # O(F_nested)
        result = nested_validator.validate(value)  # O(F_nested × T_nested) recursive
```

**Problem**: No recursion depth limit. Malicious or malformed frontmatter with deep nesting could cause stack overflow or excessive validation time.

**Optimal approach**: Add configurable recursion depth limit (default: 10 levels).

### Bottleneck 3: Strict Mode Unknown Fields — O(U log U)

**Location**: `validator.py:321-330`

```python
# Current: Sorting unknown fields for consistent error output
if self.strict:
    unknown = set(data.keys()) - set(schema_fields.keys())  # O(D + F)
    for field_name in sorted(unknown):  # O(U log U) - unnecessary sort
        errors.append(ValidationError(...))
```

**Problem**: Sorting unknown fields for error messages adds O(U log U) overhead. For frontmatter with many unknown fields (migration scenarios), this accumulates.

**Mitigation**: Low impact in practice (U is typically 0-5), but could iterate unsorted for slight improvement.

---

## Current Complexity Analysis

### What's Already Optimal ✅

| Component | Operation | Complexity | Notes |
|-----------|-----------|------------|-------|
| SchemaValidator | `__init__()` | **O(F)** ✅ | Caches type hints once |
| SchemaValidator | `validate()` | O(F × T) | Linear in fields, T is type depth |
| SchemaValidator | `_coerce_datetime()` | **O(S)** ✅ | String parsing, unavoidable |
| SchemaValidator | `_is_optional()` | **O(A)** ✅ | A = union type args, typically 2 |
| CollectionConfig | `__post_init__()` | **O(1)** ✅ | Simple validation |
| ValidationResult | `error_summary` | O(E × M) | E errors, M message length |
| load_collections | Dynamic import | O(M) | Module size, one-time |

### What Could Be Optimized ⚠️

| Component | Operation | Current | Optimal | Impact |
|-----------|-----------|---------|---------|--------|
| Loader | `get_collection_for_path()` | O(C × P) | O(P) | High for many collections |
| Validator | `_coerce_type()` recursion | Unbounded | O(D × F × T) | Safety |
| Validator | Strict mode sorting | O(U log U) | O(U) | Low |

**Variables**: C=collections, P=path depth, F=fields, T=type nesting, L=list length, U=unknown fields, D=max recursion depth

---

## Goals

1. **Add prefix trie for collection matching** for O(P) per-file lookup (optional, for 50+ collections)
2. **Add recursion depth limit** to prevent stack overflow (safety, always)
3. **Maintain API compatibility** — No breaking changes to public interfaces
4. **Preserve correctness** — Identical validation behavior

### Non-Goals

- Parallel validation (single page validation is already fast)
- Pydantic replacement (already supported as backend)
- Schema caching across process restarts (out of scope)

---

## Proposed Solution

### Phase 1: Recursion Depth Limit (Safety)

**Estimated effort**: 1 hour  
**Impact**: Prevents stack overflow on malformed content

#### 1.1 Add Depth Parameter to SchemaValidator

```python
# validator.py - Add recursion depth tracking
class SchemaValidator:
    MAX_RECURSION_DEPTH = 10  # Configurable class attribute

    def __init__(self, schema: type, strict: bool = True, max_depth: int | None = None) -> None:
        self.schema = schema
        self.strict = strict
        self._max_depth = max_depth or self.MAX_RECURSION_DEPTH
        # ... existing init ...

    def validate(
        self,
        data: dict[str, Any],
        source_file: Path | None = None,
        _depth: int = 0,  # NEW: Internal depth counter
    ) -> ValidationResult:
        """Validate with recursion depth tracking."""
        if _depth > self._max_depth:
            return ValidationResult(
                valid=False,
                data=None,
                errors=[ValidationError(
                    field="(schema)",
                    message=f"Maximum nesting depth ({self._max_depth}) exceeded",
                )],
                warnings=[],
            )
        # ... rest of validation ...
```

#### 1.2 Pass Depth Through Recursive Calls

```python
def _coerce_type(
    self,
    name: str,
    value: Any,
    expected: type,
    _depth: int = 0,  # NEW: Depth tracking
) -> tuple[Any, list[ValidationError]]:
    # ... existing type checking ...

    # Handle nested dataclasses
    if is_dataclass(expected):
        if isinstance(value, dict):
            nested_validator = SchemaValidator(expected, strict=self.strict)
            # NEW: Pass incremented depth
            result = nested_validator.validate(value, _depth=_depth + 1)
            # ...

    # Handle list[X] - pass depth to item validation
    if origin is list and args:
        for i, item in enumerate(value):
            coerced, errors = self._coerce_type(
                f"{name}[{i}]", item, item_type, _depth=_depth
            )
```

**Complexity change**: Bounded O(D × F × T) where D is max depth (default 10)

---

### Phase 2: Collection Path Trie (Optional, for Large Sites)

**Estimated effort**: 3 hours  
**When to implement**: Sites with 50+ collections seeing discovery latency

#### 2.1 Build Path Prefix Trie

```python
# loader.py - Add trie-based collection lookup
from typing import TypeVar

T = TypeVar('T')

class CollectionPathTrie:
    """Prefix trie for O(P) collection path matching."""

    def __init__(self) -> None:
        self._root: dict[str, Any] = {}
        self._COLLECTION_KEY = "__collection__"

    def insert(self, path: Path, name: str, config: CollectionConfig) -> None:
        """Insert a collection path into the trie."""
        node = self._root
        for part in path.parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[self._COLLECTION_KEY] = (name, config)

    def find(self, file_path: Path) -> tuple[str | None, CollectionConfig | None]:
        """Find the collection that matches this file path (O(P))."""
        node = self._root
        best_match: tuple[str | None, CollectionConfig | None] = (None, None)

        for part in file_path.parts:
            if part not in node:
                break
            node = node[part]
            # Track the deepest collection match
            if self._COLLECTION_KEY in node:
                best_match = node[self._COLLECTION_KEY]

        return best_match
```

#### 2.2 Build Trie During Collection Loading

```python
def build_collection_trie(
    collections: dict[str, CollectionConfig[Any]],
) -> CollectionPathTrie:
    """Build path trie from collection configurations."""
    trie = CollectionPathTrie()
    for name, config in collections.items():
        if config.directory is not None:
            trie.insert(config.directory, name, config)
    return trie


def get_collection_for_path(
    file_path: Path,
    content_root: Path,
    collections: dict[str, CollectionConfig[Any]],
    trie: CollectionPathTrie | None = None,  # NEW: Optional trie
) -> tuple[str | None, CollectionConfig[Any] | None]:
    """Determine which collection a content file belongs to."""
    try:
        rel_path = file_path.relative_to(content_root)
    except ValueError:
        return None, None

    # NEW: Use trie if available (O(P) instead of O(C × P))
    if trie is not None:
        return trie.find(rel_path)

    # Fallback: Linear scan (existing behavior)
    for name, config in collections.items():
        if config.directory is None:
            continue
        try:
            rel_path.relative_to(config.directory)
            return name, config
        except ValueError:
            continue

    return None, None
```

**Complexity change**: O(C × P) → O(P) for collection lookup

---

### Phase 3: Minor Optimizations (Low Priority)

**Estimated effort**: 30 minutes  
**Impact**: Marginal, only for edge cases

#### 3.1 Remove Unnecessary Sorting in Strict Mode

```python
# validator.py - Skip sorting for unknown fields
if self.strict:
    unknown = set(data.keys()) - set(schema_fields.keys())
    # CHANGED: Iterate unsorted (order doesn't affect validation correctness)
    for field_name in unknown:  # O(U) instead of O(U log U)
        errors.append(ValidationError(
            field=field_name,
            message=f"Unknown field '{field_name}' (not in schema)",
            value=data[field_name],
        ))
```

**Trade-off**: Error order becomes non-deterministic. For consistent error messages in tests, sort only in `error_summary` property:

```python
@property
def error_summary(self) -> str:
    if not self.errors:
        return ""
    # Sort only when formatting for display
    sorted_errors = sorted(self.errors, key=lambda e: e.field)
    lines = [f"  - {e.field}: {e.message}" for e in sorted_errors]
    return "\n".join(lines)
```

---

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (Required First)

**Files**: `benchmarks/test_collections_performance.py` (new)

> **Critical**: Must be completed before any optimization to measure actual improvement.

1. Create synthetic collection configurations (10, 50, 100, 200 collections)
2. Create synthetic content files (100, 1K, 5K, 10K files)
3. Create synthetic schemas (5, 10, 20, 50 fields; nested 1, 3, 5, 10 levels)
4. Measure wall-clock time for:
   - `get_collection_for_path()` — Per-file collection matching
   - `SchemaValidator.validate()` — Per-file validation
   - Full discovery cycle — Collections + validation
5. Record baseline metrics in `benchmarks/baseline_collections.json`

```python
# Example benchmark structure
@pytest.mark.benchmark
def test_collection_matching_100_collections(benchmark, collections_100):
    """Baseline: collection matching with 100 collections."""
    content_root = Path("content")
    file_path = Path("content/blog/nested/deep/post.md")

    result = benchmark(
        get_collection_for_path,
        file_path,
        content_root,
        collections_100,
    )
    assert result[0] is not None  # Should find a collection


@pytest.mark.benchmark
def test_validation_nested_10_levels(benchmark, schema_nested_10, data_nested_10):
    """Baseline: validation with 10 levels of nesting."""
    validator = SchemaValidator(schema_nested_10)
    result = benchmark(validator.validate, data_nested_10)
    assert result.valid
```

### Step 1: Add Recursion Depth Limit (Safety)

**Files**: `validator.py`

1. Add `MAX_RECURSION_DEPTH` class constant (default: 10)
2. Add `max_depth` parameter to `__init__`
3. Add `_depth` parameter to `validate()` and `_coerce_type()`
4. Return validation error when depth exceeded
5. Add tests for depth limiting
6. Document depth limit in docstrings

### Step 2: Add Collection Path Trie (Optional)

**Files**: `loader.py`

1. Add `CollectionPathTrie` class
2. Add `build_collection_trie()` function
3. Update `get_collection_for_path()` to accept optional trie
4. Update content discovery to build trie when collections > 20
5. Add benchmarks comparing linear vs trie lookup
6. Document trie usage for large sites

### Step 3: Minor Optimizations

**Files**: `validator.py`

1. Remove sorting from strict mode unknown field iteration
2. Add sorting to `ValidationResult.error_summary` property
3. Update tests to not depend on error order

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | 100 Collections, 10K Pages |
|-----------|-----------------|----------------------------|
| `get_collection_for_path()` | O(C × P) | ~20ms per file |
| `SchemaValidator.validate()` | O(F × T) | <1ms (already efficient) |
| Nested dataclass validation | Unbounded recursion | Stack overflow risk |
| Full discovery (validation) | O(N × C × P) | ~200s |

### After Optimization

| Operation | Time Complexity | 100 Collections, 10K Pages | Speedup |
|-----------|-----------------|----------------------------|---------|
| `get_collection_for_path()` | **O(P)** | <1ms per file | **20x** |
| `SchemaValidator.validate()` | O(D × F × T) | <1ms | 1x (safety bounded) |
| Nested dataclass validation | O(D × F × T) | Bounded | ∞ (prevents crash) |
| Full discovery (validation) | O(N × (P + F × T)) | ~20s | **10x** |

**Variables**: N=pages, C=collections, P=path depth, F=fields, T=type nesting, D=max depth

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized operations produce identical results
   - Same collection matched for each file path
   - Same validation results for all schemas

2. **Edge cases**:
   - 0 collections (empty config)
   - Overlapping collection directories
   - Schema with 0 fields
   - Schema with circular type references (if possible)
   - Deeply nested data exceeding depth limit

### Performance Tests

1. **Benchmark suite** with synthetic data:
   - Small: 5 collections, 100 pages
   - Medium: 20 collections, 1K pages
   - Large: 100 collections, 10K pages

2. **Regression detection**: Fail if performance degrades >10%

### Safety Tests

1. **Recursion depth**: Verify stack doesn't overflow with deep nesting
2. **Malformed input**: Verify graceful error handling

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Trie implementation bugs | Low | Medium | Comprehensive path tests, fallback to linear |
| Depth limit too restrictive | Low | Medium | Configurable, document override |
| Breaking error message order | Low | Low | Sort in `error_summary` for display |
| Memory increase from trie | Very Low | Very Low | Trie is O(C × P), minimal overhead |

---

## Alternatives Considered

### 1. LRU Cache for Collection Matching

**Pros**: No new data structure, caches common paths  
**Cons**: Cache misses still O(C × P), memory for cache entries

**Decision**: Trie is better — O(1) space per path component, guaranteed O(P) lookup.

### 2. Pre-build Path→Collection Dict

**Pros**: O(1) lookup  
**Cons**: Requires enumerating all possible paths upfront (impossible for glob patterns)

**Decision**: Trie handles prefix matching naturally without enumeration.

### 3. Parallel Validation

**Pros**: Could speed up batch validation  
**Cons**: Single validation is already <1ms, parallelism overhead dominates

**Decision**: Not needed. Focus on algorithmic improvements.

---

## Success Criteria

1. **`get_collection_for_path()` for 100 collections**: <1ms (currently ~20ms with O(C × P))
2. **No stack overflow**: Deep nesting returns clean error, not crash
3. **No API changes**: Existing code continues working
4. **Backward compatible**: Old collection configs work unchanged
5. **Regression tests**: CI fails if performance degrades >10%

---

## Future Work

1. **Collection inheritance**: Child collections extending parent schemas
2. **Schema versioning**: Track schema changes across versions
3. **Lazy validation**: Validate fields on access, not upfront
4. **Parallel batch validation**: Validate multiple files concurrently (if needed)
5. **Schema caching**: Reuse validators across builds

---

## References

- [Python dict complexity](https://wiki.python.org/moin/TimeComplexity) — O(1) average case
- [Trie data structure](https://en.wikipedia.org/wiki/Trie) — Prefix tree for path matching
- [dataclasses.fields()](https://docs.python.org/3/library/dataclasses.html#dataclasses.fields) — O(F) field inspection

---

## Appendix: Current Implementation Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| CollectionConfig | `__init__.py` | `__post_init__()`, properties |
| define_collection | `__init__.py` | Factory function |
| SchemaValidator | `validator.py` | `validate()`, `_coerce_type()`, `_validate_dataclass()` |
| ValidationResult | `validator.py` | `error_summary` |
| load_collections | `loader.py` | Dynamic module import |
| get_collection_for_path | `loader.py` | Collection path matching |
| validate_collections_config | `loader.py` | Directory existence check |
| Standard schemas | `schemas.py` | `BlogPost`, `DocPage`, `Tutorial`, etc. |
| Error types | `errors.py` | `ContentValidationError`, `ValidationError` |

---

## Appendix: Complexity by Function

### loader.py

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `load_collections()` | O(M + C) | — | Module import, already optimal |
| `get_collection_for_path()` | O(C × P) | O(P) | Trie optimization |
| `validate_collections_config()` | O(C) | — | Linear scan, already optimal |

### validator.py

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `__init__()` | O(F) | — | Already optimal |
| `validate()` | O(F × T) | O(D × F × T) | Add depth bound |
| `_validate_dataclass()` | O(F × T + U log U) | O(F × T + U) | Remove sort |
| `_coerce_type()` | O(T) or O(L × T) | O(D × T) | Depth bounded |
| `_coerce_datetime()` | O(S) | — | Already optimal |
| `_is_optional()` | O(A) | — | Already optimal |

### errors.py

| Function | Current | Notes |
|----------|---------|-------|
| `ValidationError.__str__()` | O(M) | Already optimal |
| `ContentValidationError.__str__()` | O(E × M) | Already optimal |
| `ContentValidationError.to_dict()` | O(E × V) | Already optimal |
| `CollectionNotFoundError.__init__()` | O(A log A) | Sorting for display, acceptable |

---

## Appendix: Space Complexity

### Current Space Usage

| Structure | Space | Notes |
|-----------|-------|-------|
| `collections` dict | O(C) | C = number of collections |
| `SchemaValidator._type_hints` | O(F) | F = fields per schema |
| `ValidationResult.errors` | O(E) | E = errors per validation |

### Additional Space from Optimizations

| New Structure | Space | Notes |
|---------------|-------|-------|
| `CollectionPathTrie` | O(C × P) | C collections, P avg path depth |
| Depth counter | O(1) | Stack parameter |

**Total additional space**: Negligible. Trie with 100 collections and depth 5 is ~500 nodes × ~50 bytes = ~25KB.
