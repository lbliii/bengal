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

The `bengal/collections` package provides content schema validation for type-safe frontmatter. Analysis confirms the package is well-designed for typical use cases, but identified **2 algorithmic patterns** requiring attention:

**Key findings**:

1. **`get_collection_for_path()`** — O(C × P) linear scan of all collections per content file
2. **`_coerce_type()` for nested types** — Unbounded recursion depth (safety issue)

**Proposed optimizations**:

1. **Phase 1 (Safety)**: Add recursion depth limit for nested validation → Prevent stack overflow
2. **Phase 2 (Scale)**: Add prefix trie for collection path matching → O(P) lookup

**Current state**: The existing implementation is efficient for typical use cases (1-20 collections, schemas with <20 fields, lists with <100 items). Phase 1 is a safety fix; Phase 2 is preventive for edge cases.

**Impact**: Prevent DoS from malformed content; maintain sub-millisecond validation at scale

---

## Problem Statement

### Current Performance Characteristics

> **Note**: The collections package is already well-optimized for typical use. The bottlenecks identified affect edge cases with extreme content volumes.

> ⚠️ **Performance projections below are theoretical estimates.** Actual measurements required before optimization (see Step 0).

| Scenario | `get_collection_for_path` | `validate()` | Overall Discovery |
|----------|---------------------------|--------------|-------------------|
| 5 collections, 100 pages | <1ms | <1ms | <100ms |
| 20 collections, 1K pages | <1ms | <1ms | ~500ms |
| 50 collections, 5K pages | ~5ms (est.) | <1ms | ~5s (est.) |
| 100 collections, 10K pages | **~20ms (est.)** ⚠️ | <1ms | **~200s (est.)** ⚠️ |

For sites approaching 10K pages with 100+ collections, collection matching may become a bottleneck during content discovery. Benchmarks will validate these estimates.

### Bottleneck 1: get_collection_for_path() — O(C × P)

**Location**: `loader.py:199-217`

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
            return name, config  # Returns FIRST match
        except ValueError:
            continue

    return None, None
```

**Problem**: For each content file during discovery, we iterate ALL collections and compare paths. With 100 collections and 10K files, that's 1M path comparisons.

**Optimal approach**: Build prefix trie from collection directories once, then O(P) lookup per file.

### Bottleneck 2: _coerce_type() Recursive Validation — Unbounded Depth

**Location**: `validator.py:449-458` (list validation) and `validator.py:522-542` (nested dataclass)

```python
# List validation: O(L) iterations, each can recurse
for i, item in enumerate(value):  # O(L)
    coerced, errors = self._coerce_type(f"{name}[{i}]", item, item_type)  # Recursive

# Nested dataclass: Creates NEW validator, recurses without depth limit
if is_dataclass(expected):
    if isinstance(value, dict):
        nested_validator = SchemaValidator(expected, strict=self.strict)  # New instance
        result = nested_validator.validate(value)  # No depth tracking!
```

**Problem**: No recursion depth limit. Malicious or malformed frontmatter with deep nesting could cause stack overflow or excessive validation time.

**Optimal approach**: Add configurable recursion depth limit (default: 10 levels), tracked through `_coerce_type()` chain.

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
| Validator | `_coerce_type()` recursion | Unbounded | O(D × F × T) | **Safety** |

**Variables**: C=collections, P=path depth, F=fields, T=type nesting, L=list length, D=max recursion depth

---

## Goals

1. **Add recursion depth limit** to prevent stack overflow (safety, always) — **Phase 1**
2. **Add prefix trie for collection matching** for O(P) per-file lookup (optional, for 50+ collections) — **Phase 2**
3. **Maintain API compatibility** — No breaking changes to public interfaces
4. **Preserve correctness** — Identical validation behavior

### Non-Goals

- Parallel validation (single page validation is already fast)
- Pydantic replacement (already supported as backend)
- Schema caching across process restarts (out of scope)
- Removing sorting from strict mode (negligible impact, breaks test determinism)

---

## Proposed Solution

### Phase 1: Recursion Depth Limit (Safety) — REQUIRED

**Estimated effort**: 2 hours  
**Impact**: Prevents stack overflow on malformed content  
**Priority**: High — Safety fix

#### 1.1 Add Depth Tracking to SchemaValidator

```python
# validator.py - Add recursion depth tracking
class SchemaValidator:
    MAX_RECURSION_DEPTH = 10  # Configurable class attribute

    def __init__(
        self,
        schema: type,
        strict: bool = True,
        max_depth: int | None = None,
    ) -> None:
        self.schema = schema
        self.strict = strict
        self._max_depth = max_depth if max_depth is not None else self.MAX_RECURSION_DEPTH
        self._is_pydantic = hasattr(schema, "model_validate")
        self._type_hints: dict[str, Any] = {}
        # ... existing init ...
```

#### 1.2 Thread Depth Through _coerce_type() Chain

The key insight: depth must flow through `_coerce_type()`, not `validate()`, because nested dataclass validation creates a **new** `SchemaValidator` instance. We track depth internally within the validation call.

```python
def _validate_dataclass(
    self,
    data: dict[str, Any],
    source_file: Path | None,
    _depth: int = 0,  # NEW: Internal depth counter
) -> ValidationResult:
    """Validate data using a dataclass schema with depth tracking."""
    # Check depth limit BEFORE validation
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

    errors: list[ValidationError] = []
    warnings: list[str] = []
    validated_data: dict[str, Any] = {}

    # ... existing field processing, passing _depth to _coerce_type ...

    for name, field_info in schema_fields.items():
        type_hint = self._type_hints.get(name, Any)
        if name in data:
            value = data[name]
            # Pass depth through coercion chain
            coerced, type_errors = self._coerce_type(name, value, type_hint, _depth=_depth)
            # ...


def _coerce_type(
    self,
    name: str,
    value: Any,
    expected: type,
    _depth: int = 0,  # NEW: Depth tracking
) -> tuple[Any, list[ValidationError]]:
    # ... existing type checking ...

    # Handle nested dataclasses - FIXED: pass depth and max_depth
    if is_dataclass(expected):
        if _depth >= self._max_depth:
            return value, [ValidationError(
                field=name,
                message=f"Maximum nesting depth ({self._max_depth}) exceeded at '{name}'",
            )]
        if isinstance(value, dict):
            # Pass max_depth to nested validator
            nested_validator = SchemaValidator(
                expected,
                strict=self.strict,
                max_depth=self._max_depth,
            )
            # Pass incremented depth to internal validation
            result = nested_validator._validate_dataclass(value, None, _depth=_depth + 1)
            if result.valid:
                return result.data, []
            else:
                for error in result.errors:
                    error.field = f"{name}.{error.field}"
                return value, result.errors

    # Handle list[X] - pass depth to item validation (depth doesn't increase for lists)
    if origin is list and args:
        for i, item in enumerate(value):
            coerced, errors = self._coerce_type(
                f"{name}[{i}]", item, item_type, _depth=_depth
            )
            # ...
```

**Key changes from original proposal**:
- Depth check happens in `_coerce_type()` before creating nested validator
- `max_depth` passed to nested `SchemaValidator` constructor
- Depth tracked through internal `_validate_dataclass()` call
- List validation passes depth but doesn't increment (lists don't increase nesting depth)

**Complexity change**: Bounded O(D × F × T) where D is max depth (default 10)

---

### Phase 2: Collection Path Trie (Optional, for Large Sites)

**Estimated effort**: 3 hours  
**When to implement**: Sites with 50+ collections seeing discovery latency in benchmarks  
**Priority**: Medium — Performance optimization

> ⚠️ **Behavior Change**: Current implementation returns **first matching** collection. Trie returns **deepest matching** collection. Document this difference; it's arguably more correct for overlapping directories like `docs/` and `docs/api/`.

#### 2.1 Build Path Prefix Trie

```python
# loader.py - Add trie-based collection lookup
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.collections import CollectionConfig


class CollectionPathTrie:
    """
    Prefix trie for O(P) collection path matching.

    For overlapping directories (e.g., `docs/` and `docs/api/`), returns the
    **deepest** matching collection. This differs from linear scan which
    returns the **first** match based on dict iteration order.
    """
    _COLLECTION_KEY = "__collection__"

    def __init__(self) -> None:
        self._root: dict[str, Any] = {}

    def insert(self, path: Path, name: str, config: CollectionConfig[Any]) -> None:
        """Insert a collection path into the trie. O(P) where P = path depth."""
        node = self._root
        for part in path.parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[self._COLLECTION_KEY] = (name, config)

    def find(self, file_path: Path) -> tuple[str | None, CollectionConfig[Any] | None]:
        """
        Find the deepest collection that matches this file path. O(P).

        Returns (None, None) if no collection matches.
        """
        node = self._root
        best_match: tuple[str | None, CollectionConfig[Any] | None] = (None, None)

        for part in file_path.parts:
            if part not in node:
                break
            node = node[part]
            # Track the deepest collection match (not just any match)
            if self._COLLECTION_KEY in node:
                best_match = node[self._COLLECTION_KEY]

        return best_match

    def __len__(self) -> int:
        """Return number of collections in trie (for debugging)."""
        count = 0
        stack = [self._root]
        while stack:
            node = stack.pop()
            if self._COLLECTION_KEY in node:
                count += 1
            stack.extend(v for k, v in node.items() if k != self._COLLECTION_KEY)
        return count
```

#### 2.2 Build Trie During Collection Loading

```python
def build_collection_trie(
    collections: dict[str, CollectionConfig[Any]],
) -> CollectionPathTrie:
    """Build path trie from collection configurations. O(C × P)."""
    trie = CollectionPathTrie()
    for name, config in collections.items():
        if config.directory is not None:
            trie.insert(config.directory, name, config)
    return trie


def get_collection_for_path(
    file_path: Path,
    content_root: Path,
    collections: dict[str, CollectionConfig[Any]],
    trie: CollectionPathTrie | None = None,  # NEW: Optional trie for O(P) lookup
) -> tuple[str | None, CollectionConfig[Any] | None]:
    """
    Determine which collection a content file belongs to.

    Args:
        file_path: Path to the content file.
        content_root: Root content directory.
        collections: Dictionary of collection configurations.
        trie: Optional pre-built trie for O(P) lookup. If None, uses O(C × P) linear scan.

    Returns:
        Tuple of (collection_name, config) or (None, None) if no match.

    Note:
        With trie: Returns deepest matching collection (most specific).
        Without trie: Returns first matching collection (dict order).
    """
    try:
        rel_path = file_path.relative_to(content_root)
    except ValueError:
        return None, None

    # Use trie if available: O(P) instead of O(C × P)
    if trie is not None:
        return trie.find(rel_path)

    # Fallback: Linear scan (existing behavior, first match wins)
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

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (REQUIRED FIRST)

**Files**: `benchmarks/test_collections_performance.py` (new)

> ⚠️ **Critical**: Must be completed before any optimization to validate performance projections and measure actual improvement.

1. Create synthetic collection configurations (10, 50, 100, 200 collections)
2. Create synthetic content files (100, 1K, 5K, 10K files)
3. Create synthetic schemas (5, 10, 20, 50 fields; nested 1, 3, 5, 10 levels)
4. Measure wall-clock time for:
   - `get_collection_for_path()` — Per-file collection matching
   - `SchemaValidator.validate()` — Per-file validation with varying nesting
   - Full discovery cycle — Collections + validation
5. Record baseline metrics in `benchmarks/baseline_collections.json`

```python
# Example benchmark structure
import pytest
from pathlib import Path
from bengal.collections import SchemaValidator, define_collection
from bengal.collections.loader import get_collection_for_path


@pytest.fixture
def collections_100():
    """Generate 100 collection configurations."""
    from dataclasses import dataclass

    @dataclass
    class GenericSchema:
        title: str

    return {
        f"collection_{i}": define_collection(
            schema=GenericSchema,
            directory=f"content/section_{i}",
        )
        for i in range(100)
    }


@pytest.mark.benchmark(group="collection-matching")
def test_collection_matching_100_collections(benchmark, collections_100):
    """Baseline: collection matching with 100 collections."""
    content_root = Path("content")
    file_path = Path("content/section_50/nested/deep/post.md")

    result = benchmark(
        get_collection_for_path,
        file_path,
        content_root,
        collections_100,
    )
    assert result[0] == "collection_50"


@pytest.fixture
def deeply_nested_schema():
    """Generate schema with 10 levels of nesting."""
    from dataclasses import dataclass

    @dataclass
    class Level10:
        value: str

    @dataclass
    class Level9:
        nested: Level10

    # ... generate programmatically ...
    return Level1


@pytest.mark.benchmark(group="validation-depth")
def test_validation_nested_10_levels(benchmark, deeply_nested_schema, nested_data):
    """Baseline: validation with 10 levels of nesting."""
    validator = SchemaValidator(deeply_nested_schema)
    result = benchmark(validator.validate, nested_data)
    assert result.valid
```

### Step 1: Add Recursion Depth Limit (Safety)

**Files**: `bengal/collections/validator.py`

1. Add `MAX_RECURSION_DEPTH = 10` class constant
2. Add `max_depth` parameter to `__init__`
3. Add `_depth` parameter to `_validate_dataclass()` (internal)
4. Add `_depth` parameter to `_coerce_type()`
5. Check depth before nested dataclass validation in `_coerce_type()`
6. Return `ValidationError` when depth exceeded
7. Add tests for:
   - Normal nested validation (depth < limit)
   - Validation at exactly max depth
   - Validation exceeding max depth (should fail gracefully)
   - Custom max_depth parameter
8. Document depth limit in docstrings

### Step 2: Add Collection Path Trie (Conditional)

**Files**: `bengal/collections/loader.py`

> Only implement if Step 0 benchmarks show significant latency with 50+ collections.

1. Add `CollectionPathTrie` class
2. Add `build_collection_trie()` function
3. Update `get_collection_for_path()` to accept optional trie
4. Document behavior difference (deepest vs first match)
5. Add tests for:
   - Simple path matching
   - Overlapping directories (`docs/` vs `docs/api/`)
   - No match cases
   - Empty trie
6. Add benchmarks comparing linear vs trie lookup
7. Update content discovery to build trie when `len(collections) > 20`

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| `get_collection_for_path()` | O(C × P) | Linear scan all collections |
| `SchemaValidator.validate()` | O(F × T) | Already efficient |
| Nested dataclass validation | **Unbounded** ⚠️ | Stack overflow risk |

### After Optimization

| Operation | Time Complexity | Change |
|-----------|-----------------|--------|
| `get_collection_for_path()` | **O(P)** | C eliminated via trie |
| `SchemaValidator.validate()` | O(D × F × T) | Bounded by max_depth |
| Nested dataclass validation | **O(D × F × T)** | Crash → clean error |

**Variables**: N=pages, C=collections, P=path depth, F=fields, T=type nesting, D=max depth

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized operations produce identical results
   - Same collection matched for each file path
   - Same validation results for all schemas

2. **Edge cases**:
   - 0 collections (empty config)
   - Overlapping collection directories (document first-match vs deepest-match)
   - Schema with 0 fields
   - Deeply nested data at exactly max depth (should pass)
   - Deeply nested data exceeding depth limit (should fail with clear error)
   - Custom `max_depth` values (1, 5, 20, 100)

3. **Trie-specific**:
   - Overlapping prefixes: `docs/` and `docs/api/` should return `docs/api/` for `docs/api/endpoint.md`
   - Non-overlapping prefixes work correctly
   - Files not matching any collection return `(None, None)`

### Performance Tests

1. **Benchmark suite** with synthetic data:
   - Small: 5 collections, 100 pages
   - Medium: 20 collections, 1K pages
   - Large: 100 collections, 10K pages

2. **Regression detection**: Fail if performance degrades >10%

### Safety Tests

1. **Recursion depth**: Verify stack doesn't overflow with deep nesting
2. **Malformed input**: Verify graceful error handling
3. **DoS resistance**: Verify deeply nested malicious input returns error, not crash

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Trie implementation bugs | Low | Medium | Comprehensive path tests, fallback to linear scan |
| Depth limit too restrictive | Low | Medium | Configurable via `max_depth`, default 10 is generous |
| Trie behavior change (deepest vs first) | Medium | Low | Document clearly, arguably more correct |
| Memory increase from trie | Very Low | Very Low | O(C × P) nodes, ~25KB for 100 collections |

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

### 4. Remove Sorting in Strict Mode

**Pros**: O(U) instead of O(U log U) for unknown field errors  
**Cons**: Non-deterministic error order breaks test assertions, U is typically 0-5

**Decision**: Not worth the churn. Keep sorted for deterministic behavior.

---

## Success Criteria

1. **No stack overflow**: Deep nesting returns clean error, not crash ✅
2. **Depth limit configurable**: Users can adjust `max_depth` if needed ✅
3. **`get_collection_for_path()` for 100 collections**: <1ms (if trie implemented) ✅
4. **No API changes**: Existing code continues working ✅
5. **Backward compatible**: Old collection configs work unchanged ✅
6. **Benchmarks exist**: CI tracks performance regression ✅

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

| Component | File | Line Range | Key Functions |
|-----------|------|------------|---------------|
| CollectionConfig | `__init__.py` | 96-192 | `__post_init__()`, properties |
| define_collection | `__init__.py` | 194-290 | Factory function |
| SchemaValidator | `validator.py` | 99-706 | `validate()`, `_coerce_type()`, `_validate_dataclass()` |
| ValidationResult | `validator.py` | 50-97 | `error_summary` |
| load_collections | `loader.py` | 49-159 | Dynamic module import |
| get_collection_for_path | `loader.py` | 162-217 | Collection path matching |
| validate_collections_config | `loader.py` | 220-261 | Directory existence check |
| Standard schemas | `schemas.py` | — | `BlogPost`, `DocPage`, `Tutorial`, etc. |
| Error types | `errors.py` | — | `ContentValidationError`, `ValidationError` |

---

## Appendix: Complexity by Function

### loader.py

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `load_collections()` | O(M + C) | — | Module import, already optimal |
| `get_collection_for_path()` | O(C × P) | O(P) | Trie optimization (Phase 2) |
| `validate_collections_config()` | O(C) | — | Linear scan, already optimal |

### validator.py

| Function | Current | Optimal | Notes |
|----------|---------|---------|-------|
| `__init__()` | O(F) | — | Already optimal |
| `validate()` | O(F × T) | O(D × F × T) | Add depth bound (Phase 1) |
| `_validate_dataclass()` | O(F × T) | O(D × F × T) | Depth tracking (Phase 1) |
| `_coerce_type()` | Unbounded | O(D × T) | Depth bounded (Phase 1) |
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
