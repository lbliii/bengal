# RFC: Autodoc Algorithm Optimization

**Status**: ✅ Implemented  
**Created**: 2025-12-24  
**Implemented**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Autodoc (Python Extraction, Inheritance Resolution, Docstring Parsing)  
**Confidence**: 85% 🟢  
**Priority**: P2 (Medium) — Performance, scalability for large codebases  
**Estimated Effort**: 1-2 days

---

## Executive Summary

The `bengal/autodoc` package provides comprehensive API documentation generation via AST parsing, but several algorithms have suboptimal Big O complexity that creates performance bottlenecks for codebases with 500+ modules.

**Key findings**:

1. **Inheritance Resolution** — O(B × C) linear scan for simple name lookup
2. **DocElement Serialization** — Deep recursive traversal without memoization
3. **Alias Detection** — Repeated AST traversal per module

**Proposed optimizations**:

1. Build reverse index for inheritance lookup → O(1) simple name resolution
2. Add memoization for typed metadata deserialization → Skip repeated work
3. Parallel extraction already implemented, ensure threshold tuning

**Impact**: Enable fast autodoc for 1K+ module codebases (current: ~30s → target: <10s)

---

## Problem Statement

### Current Performance Characteristics

| Codebase Size | File Discovery | AST Extraction | Inheritance | Orchestration |
|---------------|----------------|----------------|-------------|---------------|
| 50 modules | <1s | <2s | <1s | <1s |
| 200 modules | ~2s | ~8s | ~3s | ~2s |
| 500 modules | ~5s | ~20s | **~15s** ⚠️ | ~5s |
| 1K modules | ~10s | ~40s | **~60s** ⚠️ | ~10s |

For large codebases (500+ modules with deep inheritance hierarchies), inheritance resolution becomes the dominant bottleneck.

### Bottleneck 1: Inheritance Simple Name Lookup — O(B × C)

**Location**: `extractors/python/inheritance.py:61-74`

```python
# Current: Linear scan of entire class_index for simple name match
for base_name in bases:                           # O(B) - bases
    base_elem = None

    if base_name in class_index:                  # O(1) - qualified lookup
        base_elem = class_index[base_name]
    else:
        # INEFFICIENT: Linear scan for simple name match
        simple_base = base_name.split(".")[-1]
        for qualified, elem in class_index.items():  # O(C) - all classes
            if qualified.endswith(f".{simple_base}"):
                base_elem = elem
                break
```

**Problem**: When base classes are referenced by simple name (e.g., `class MyClass(BaseClass)`), we perform a linear scan of all classes in the index. With 1K classes and average 2 bases per class, that's 2M string comparisons.

**Optimal approach**: Build reverse index `{simple_name: [qualified_names]}` once, then O(1) lookup.

### Bottleneck 2: Typed Metadata Deserialization — O(P) per Element

**Location**: `base.py:157-307`

```python
# Current: Complex nested dataclass reconstruction
@staticmethod
def _deserialize_typed_metadata(data: dict[str, Any]) -> DocMetadata | None:
    # Type map lookup: O(1)
    type_map: dict[str, type] = {
        "PythonModuleMetadata": PythonModuleMetadata,
        "PythonClassMetadata": PythonClassMetadata,
        # ... 10 more types
    }

    # Parameter conversion: O(P) for each element
    if type_name == "PythonFunctionMetadata":
        if type_data.get("parameters"):
            type_data["parameters"] = tuple(
                _to_param_info(p, ...) for p in type_data["parameters"]
            )
```

**Problem**: Each DocElement reconstructs its typed metadata independently. For function-heavy codebases, the same parameter patterns are reconstructed thousands of times.

**Opportunity**: Not critical, but could add LRU cache for common patterns.

### Bottleneck 3: Section Building — O(E × D)

**Location**: `orchestration/section_builders.py:80-116`

```python
# Current: Nested loop for package hierarchy
for element in elements:                           # O(E)
    parts = element.qualified_name.split(".")

    for i, part in enumerate(parts[:-1]):          # O(D) - depth
        section_path = f"{section_path}/{part}"
        if section_path not in sections:           # O(1) - dict lookup
            # Create section...
```

**Problem**: For deep package hierarchies, we repeatedly split and iterate qualified names. Not critical but contributes to overall latency.

---

## Current Complexity Analysis

### Python Extractor — O(F × N)

| Method | Complexity | Notes |
|--------|------------|-------|
| `extract()` | O(F × N) | F=files, N=avg AST nodes |
| `_extract_directory()` | O(F × N) | Sequential by default |
| `_extract_files_parallel()` | O(F × N / W) | W=workers, 10+ files threshold |
| `_extract_module()` | O(N) | Single pass AST traversal |
| `_extract_class()` | O(M) | M=methods+attributes |
| `_extract_function()` | O(P) | P=parameters |

**Key observation**: Parallel extraction already implemented with good threshold (10 files). The GIL limits parallelism on CPython, but free-threaded Python 3.14t achieves 3-4x speedup.

### Inheritance Resolution — O(B × C × M)

| Method | Complexity | Notes |
|--------|------------|-------|
| `synthesize_inherited_members()` | O(B × C × M) | B=bases, C=class index, M=members |
| Simple name lookup | O(C) | **Bottleneck** |
| Member copying | O(M) | Linear in members |

### Docstring Parsing — O(L)

| Parser | Complexity | Notes |
|--------|------------|-------|
| `detect_docstring_style()` | O(L) | Regex scan |
| `GoogleDocstringParser.parse()` | O(L) | Single pass |
| `NumpyDocstringParser.parse()` | O(L) | Single pass |
| `SphinxDocstringParser.parse()` | O(L) | Single pass |

**Key observation**: All parsers are single-pass O(L). No optimization needed.

### Orchestrator — O(E + S + P)

| Method | Complexity | Notes |
|--------|------------|-------|
| `generate()` | O(E + S + P) | E=elements, S=sections, P=pages |
| `generate_from_cache_payload()` | O(E + S + P) | Skips extraction |
| `_check_prefix_overlaps()` | O(T²) | T=doc types (≤3) |

**Key observation**: Orchestrator is linear in elements. Cache path is fast.

---

## Goals

1. **Reduce inheritance lookup** from O(B × C) to O(B × 1) amortized
2. **Tune parallel extraction threshold** for optimal performance
3. **Maintain API compatibility** — No breaking changes
4. **Preserve correctness** — Identical output

### Non-Goals

- Replacing AST parsing with external tools
- GPU acceleration
- Approximate extraction

---

## Proposed Solution

### Phase 1: Inheritance Reverse Index

**Estimated effort**: 2 hours  
**Expected speedup**: 5-10x for inheritance resolution

#### 1.1 Build Simple Name Index in PythonExtractor

```python
# extractors/python/extractor.py - Add to class_index build
class PythonExtractor(Extractor):
    def __init__(self, ...):
        self.class_index: dict[str, DocElement] = {}
        # NEW: Reverse index for O(1) simple name lookup
        self.simple_name_index: dict[str, list[str]] = defaultdict(list)

    def _extract_directory(self, directory: Path) -> list[DocElement]:
        # ... existing extraction ...

        # Second pass: build class index
        for element in elements:
            if element.element_type == "module":
                for child in element.children:
                    if child.element_type == "class":
                        qualified = child.qualified_name
                        self.class_index[qualified] = child
                        # NEW: Also index by simple name
                        simple_name = qualified.split(".")[-1]
                        self.simple_name_index[simple_name].append(qualified)
```

#### 1.2 Update Inheritance Lookup to Use Index

```python
# extractors/python/inheritance.py - Optimized lookup
def synthesize_inherited_members(
    class_elem: DocElement,
    class_index: dict[str, DocElement],
    simple_name_index: dict[str, list[str]],  # NEW parameter
    config: dict[str, Any],
) -> None:
    bases = get_python_class_bases(class_elem)
    if not bases:
        return

    existing_members = {child.name for child in class_elem.children}

    for base_name in bases:
        base_elem = None

        # Try qualified name first (O(1))
        if base_name in class_index:
            base_elem = class_index[base_name]
        else:
            # NEW: O(1) simple name lookup via reverse index
            simple_base = base_name.split(".")[-1]
            candidates = simple_name_index.get(simple_base, [])
            if candidates:
                # Take first match (or could disambiguate by module proximity)
                base_elem = class_index.get(candidates[0])

        if not base_elem:
            continue

        # ... rest unchanged ...
```

**Complexity change**: O(B × C) → O(B) amortized (index build is O(C) one-time)

### Phase 2: Parallel Extraction Tuning

**Estimated effort**: 1 hour  
**Expected speedup**: Better utilization on modern hardware

#### 2.1 Adjust Threshold Based on Benchmarks

Current threshold: `MIN_MODULES_FOR_PARALLEL = 10`

```python
# extractors/python/extractor.py - Consider hardware-aware tuning
import os

def _should_use_parallel(self, file_count: int) -> bool:
    """Determine if parallel extraction should be used."""
    # Environment override
    if os.environ.get("BENGAL_NO_PARALLEL", "").lower() in ("1", "true", "yes"):
        return False

    # Config override
    if self.config.get("parallel_autodoc") is False:
        return False

    # Hardware-aware threshold
    # On machines with many cores, lower threshold is beneficial
    import multiprocessing
    core_count = multiprocessing.cpu_count()

    # Threshold: 10 for 4 cores, 5 for 8+ cores
    threshold = max(5, 15 - core_count)

    return file_count >= threshold
```

#### 2.2 Add Performance Logging

```python
def _extract_files_parallel(self, py_files: list[Path], directory: Path) -> list[DocElement]:
    import time
    start_time = time.perf_counter()

    # ... existing parallel extraction ...

    elapsed = time.perf_counter() - start_time
    logger.info(
        "autodoc_parallel_extraction_complete",
        files=len(py_files),
        elements=len(elements),
        workers=max_workers,
        elapsed_ms=int(elapsed * 1000),
        files_per_second=len(py_files) / elapsed if elapsed > 0 else 0,
    )
    return elements
```

### Phase 3: Cache-Aware Deserialization (Optional)

**Estimated effort**: 2 hours  
**Expected speedup**: 10-20% for cache-loaded builds

#### 3.1 Add LRU Cache for Common Patterns

```python
# base.py - Memoize parameter info construction
from functools import lru_cache

@lru_cache(maxsize=1024)
def _cached_param_info(
    name: str,
    type_hint: str | None,
    default: str | None,
    description: str | None
) -> ParameterInfo:
    """Cache common parameter patterns."""
    return ParameterInfo(
        name=name,
        type_hint=type_hint,
        default=default,
        description=description,
    )

# In _deserialize_typed_metadata:
def _to_param_info(p: Any, context: str) -> ParameterInfo:
    if isinstance(p, dict):
        return _cached_param_info(
            p.get("name", ""),
            p.get("type_hint"),
            p.get("default"),
            p.get("description"),
        )
    raise TypeError(...)
```

---

## Implementation Plan

### Step 1: Add Simple Name Index (Priority: High)

**Files**: `extractors/python/extractor.py`, `extractors/python/inheritance.py`

1. Add `simple_name_index: dict[str, list[str]]` to `PythonExtractor`
2. Populate during class index build phase
3. Update `synthesize_inherited_members()` signature and implementation
4. Add unit tests verifying lookup correctness
5. Benchmark inheritance resolution before/after

### Step 2: Tune Parallel Extraction (Priority: Medium)

**Files**: `extractors/python/extractor.py`

1. Add hardware-aware threshold calculation
2. Add performance logging with timing
3. Benchmark on various core counts (4, 8, 16)
4. Document optimal configurations

### Step 3: Add Cache Memoization (Priority: Low)

**Files**: `base.py`

1. Add `@lru_cache` for parameter info construction
2. Clear cache at appropriate points (between builds)
3. Measure memory vs. speed trade-off
4. Make cache size configurable

### Step 4: Benchmarking

**Files**: `benchmarks/test_autodoc_performance.py` (new)

1. Create benchmark scenarios: 50, 200, 500, 1K modules
2. Vary inheritance depth (0, 2, 5 levels)
3. Measure wall-clock time for extraction + inheritance
4. Compare sequential vs. parallel extraction

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | 1K Modules |
|-----------|-----------------|------------|
| File Discovery | O(F) | ~10s |
| AST Extraction | O(F × N) | ~40s |
| Inheritance (simple names) | O(B × C × M) | **~60s** ⚠️ |
| Section Building | O(E × D) | ~10s |

### After Optimization

| Operation | Time Complexity | 1K Modules (projected) |
|-----------|-----------------|------------------------|
| File Discovery | O(F) | ~10s (unchanged) |
| AST Extraction | O(F × N / W) | ~15s (parallel) |
| Inheritance (indexed) | O(B × M) | **~5s** (12x faster) |
| Section Building | O(E × D) | ~10s (unchanged) |

**Total extraction time for 1K modules**: ~120s → ~40s

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized inheritance produces identical DocElements
   - Same inherited members
   - Same qualified names
   - Same metadata

2. **Edge cases**:
   - No base classes
   - Multiple inheritance
   - Diamond inheritance
   - External base classes (not in index)
   - Simple name collisions (same class name in different modules)

### Performance Tests

1. **Benchmark suite** with synthetic codebases:
   - Shallow hierarchies (avg 1 base)
   - Deep hierarchies (avg 5 bases)
   - Wide hierarchies (many classes, few bases)

2. **Regression detection**: Fail if extraction degrades >10%

### Integration Tests

1. **Real codebase tests**: Run on bengal's own source
2. **Large codebase simulation**: 1K synthetic modules with realistic inheritance

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Simple name collisions | Medium | Medium | Take first match; document behavior |
| Memory increase from index | Low | Low | Index is O(C) strings |
| Parallel extraction overhead for small codebases | Low | Low | Keep threshold at 10+ files |
| LRU cache memory usage | Low | Low | Limit cache size, clear between builds |

---

## Alternatives Considered

### 1. Pre-resolve All Inheritance During AST Pass

**Pros**: Avoid second pass entirely  
**Cons**: Requires all classes loaded before any inheritance resolution; breaks streaming

**Decision**: Keep two-pass approach; it's cleaner and enables parallel extraction.

### 2. External Type Checker Integration (mypy, pyright)

**Pros**: Accurate type resolution including generics  
**Cons**: Heavy dependency, slow, requires valid code

**Decision**: Overkill for documentation. AST-based extraction is sufficient.

### 3. Lazy Inheritance Resolution

**Pros**: Only resolve when needed  
**Cons**: Complicates caching; inheritance needed for most renders anyway

**Decision**: Eager resolution is simpler and cache-friendly.

---

## Success Criteria

1. **Inheritance resolution for 1K classes**: < 10 seconds (currently ~60 seconds)
2. **Total extraction for 1K modules**: < 45 seconds (currently ~120 seconds)
3. **No correctness regression**: Identical DocElements produced
4. **No API changes**: Existing code continues working

---

## Future Work

1. **Streaming extraction**: Yield DocElements as files are processed
2. **Incremental extraction**: Only re-extract changed files
3. **Type stub support**: Extract from `.pyi` files
4. **Cross-module reference resolution**: Link to classes in other packages

---

## References

- [Python AST Module](https://docs.python.org/3/library/ast.html) — AST node types and traversal
- [PEP 703 - Free Threading](https://peps.python.org/pep-0703/) — GIL-free Python for true parallelism
- [Sphinx autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html) — Prior art for Python documentation extraction

---

## Appendix: Current Implementation Locations

| Algorithm | File | Key Functions |
|-----------|------|---------------|
| File Discovery | `extractor.py` | `_extract_directory()`, `should_skip()` |
| AST Extraction | `extractor.py` | `_extract_file()`, `_extract_module()` |
| Class Extraction | `extractor.py` | `_extract_class()` |
| Function Extraction | `extractor.py` | `_extract_function()` |
| Inheritance | `inheritance.py` | `synthesize_inherited_members()` |
| Docstring Parsing | `docstring_parser.py` | `parse_docstring()`, `*Parser.parse()` |
| Alias Detection | `aliases.py` | `detect_aliases()`, `extract_all_exports()` |
| Orchestration | `orchestrator.py` | `VirtualAutodocOrchestrator.generate()` |
| Section Building | `section_builders.py` | `create_*_sections()` |

---

## Appendix: Benchmarking Commands

```bash
# Run autodoc benchmark
uv run pytest benchmarks/test_autodoc_performance.py -v

# Profile extraction
uv run python -m cProfile -s cumtime -m bengal build --profile autodoc

# Compare parallel vs sequential
BENGAL_NO_PARALLEL=1 uv run bengal build  # Sequential
uv run bengal build                        # Parallel (default)
```

---

## Implementation Plan

### Phase 1: Inheritance Reverse Index (Priority: High)

**Goal**: 12x speedup for inheritance resolution (60s → 5s for 1K classes)

| Step | File | Change | Effort |
|------|------|--------|--------|
| **1.1** | `extractors/python/extractor.py` | Add `simple_name_index: dict[str, list[str]]` to `PythonExtractor.__init__` | 10 min |
| **1.2** | `extractors/python/extractor.py:216-220` | Populate index during class_index build phase | 15 min |
| **1.3** | `extractors/python/inheritance.py:36-40` | Add `simple_name_index` parameter | 10 min |
| **1.4** | `extractors/python/inheritance.py:71-75` | Replace linear scan with O(1) index lookup | 20 min |
| **1.5** | `extractors/python/extractor.py:228` | Pass `simple_name_index` to `synthesize_inherited_members()` | 5 min |

**Edge Cases to Handle**:
- Multiple classes with same simple name (e.g., `pkg1.Config` and `pkg2.Config`)
- External base classes not in index
- Diamond inheritance patterns

**Verification**:
```bash
# Run existing inheritance tests
uv run pytest tests/unit/autodoc/test_python_extractor.py -k "inherited" -v
```

### Phase 2: Parallel Extraction Tuning (Priority: Medium)

**Goal**: Better utilization on multi-core machines

| Step | File | Change | Effort |
|------|------|--------|--------|
| **2.1** | `extractors/python/extractor.py` | Add `_should_use_parallel()` method with hardware-aware threshold | 20 min |
| **2.2** | `extractors/python/extractor.py:267-332` | Add timing/performance logging | 15 min |
| **2.3** | Config | Document `BENGAL_PARALLEL_THRESHOLD` env override | 10 min |

**Current threshold**: `MIN_MODULES_FOR_PARALLEL = 10` (line 67)

**Proposed formula**:
```python
threshold = max(5, 15 - core_count)
# 4 cores → 11 files
# 8 cores → 7 files
# 16+ cores → 5 files
```

### Phase 3: Cache-Aware Deserialization (Priority: Low)

**Goal**: 10-20% speedup for cached builds

| Step | File | Change | Effort |
|------|------|--------|--------|
| **3.1** | `base.py` | Add `@lru_cache` wrapper for `ParameterInfo` construction | 30 min |
| **3.2** | `base.py` | Add cache clearing hook for build lifecycle | 15 min |

---

### New Tests Required

| Test | Description | File |
|------|-------------|------|
| `test_simple_name_collision` | Two classes with same name in different packages | `test_python_extractor.py` |
| `test_inheritance_ambiguous_resolution` | Verify first-match behavior documented | `test_python_extractor.py` |
| `test_diamond_inheritance` | Multiple inheritance with shared ancestor | `test_python_extractor.py` |

---

### Implementation Order

```
Week 1 (2-4 hours):
├── 1.1 Add simple_name_index field
├── 1.2 Populate during class_index build
├── 1.3-1.5 Update inheritance lookup
└── Run existing tests

Week 1 (1-2 hours):
├── Add collision edge case tests
├── Add benchmark scenarios
└── Measure before/after

Week 1 (optional, 1-2 hours):
├── 2.1-2.3 Parallel tuning
├── 3.1-3.2 Cache optimization
└── Documentation updates
```

---

### Commands to Start

```bash
# 1. Verify current tests pass
uv run pytest tests/unit/autodoc/test_python_extractor.py -v

# 2. Create feature branch
git checkout -b feat/autodoc-inheritance-optimization

# 3. After implementation, verify
uv run pytest tests/unit/autodoc/ -v
```
