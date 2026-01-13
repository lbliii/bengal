# RFC: C-Accelerated Stdlib Audit & Final Optimizations

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2026-01-13  
**Updated**: 2026-01-13  
**Target**: Bengal 0.2.0  
**Python Version**: 3.14.2+

## Executive Summary

This RFC documents Bengal's current utilization of Python 3.14's C-accelerated standard library modules and proposes targeted improvements to maximize performance and code clarity. The audit confirms Bengal already leverages most acceleration opportunities effectively.

**Key Findings**:
- ✅ Bengal uses 15+ C-accelerated stdlib modules effectively
- ✅ Full PEP 784 (`compression.zstd`) and PEP 703 (free-threading) support
- ⚡ 3 minor improvement opportunities identified (code clarity, error diagnostics)

**Goal**: Document stdlib acceleration patterns, close remaining gaps, and establish guidelines for future development.

---

## Background

### Python 3.14 C-Accelerated Modules

Python's standard library includes modules implemented in C for performance-critical operations. These provide 10-100x speedup over pure Python equivalents:

| Module | C Implementation | Typical Speedup |
|--------|------------------|-----------------|
| `hashlib` | OpenSSL/libtomcrypt | 100x+ |
| `re` | PCRE-style engine | 50-100x |
| `json` | C scanner/encoder | 10-50x |
| `collections` | C data structures | 5-20x |
| `heapq` | C heap operations | 10-20x |
| `itertools` | C iterators | 5-15x |
| `compression.zstd` | Zstandard (PEP 784) | 50-100x |
| `tomllib` | C TOML parser | 10-30x |
| `xml.etree` | C ElementTree | 10-20x |
| `bisect` | C binary search | 10-20x |

### Audit Methodology

1. **Grep analysis**: Systematic search for import patterns with counts
2. **File inspection**: Manual review of critical paths
3. **Evidence verification**: `file:line` references for all claims

---

## Current State: What Bengal Does Well

### Tier 1: Core Performance (Fully Utilized)

#### 1. `compression.zstd` (PEP 784) ✅

**Location**: `bengal/cache/compression.py:24`

```python
from compression import zstd

def save_compressed(data: dict[str, Any], path: Path, level: int = 3) -> int:
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    compressed = zstd.compress(json_bytes, level=level)
    # ...
```

**Impact**: 92-93% cache size reduction, <1ms compress/decompress

**Evidence**: `grep "from compression import zstd"` → 2 production files

#### 2. `hashlib` ✅

**Location**: `bengal/utils/hashing.py`

```python
import hashlib

def hash_str(content: str, truncate: int | None = None, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()[:truncate] if truncate else hasher.hexdigest()
```

**Usage**: 21 imports across 19 files (cache keys, fingerprinting, content hashing)

**Evidence**: `grep "import hashlib\|from hashlib" --count`

#### 3. `re.compile()` ✅

**Usage**: 161 pre-compiled patterns across 56 files

**Pattern**: All regex patterns are compiled at module load time:

```python
# Good: Pre-compiled at import
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

# Avoided: Runtime compilation
# re.match(r"^(#{1,6})\s+(.+)$", line)  # Don't do this
```

**Evidence**: `grep "re\.compile\(" --count` → 161 matches, 56 files

#### 4. `collections.OrderedDict` ✅

**Location**: `bengal/utils/lru_cache.py`

```python
from collections import OrderedDict

class LRUCache[K, V]:
    def __init__(self, maxsize: int = 128, ttl: float | None = None):
        self._cache: OrderedDict[K, V] = OrderedDict()
    
    def get(self, key: K) -> V | None:
        # C-accelerated move_to_end() - O(1)
        self._cache.move_to_end(key)
        return self._cache[key]
```

**Impact**: O(1) LRU operations with C-accelerated `move_to_end()` and `popitem()`

#### 5. `functools.lru_cache` / `@cache` ✅

**Usage**: 68 decorators across 21 files

**Pattern**: Used for expensive computations:

```python
from functools import lru_cache

@lru_cache(maxsize=400)
def load_icon(name: str) -> str:
    """Load icon SVG with caching."""
    return _read_icon_file(name)
```

**Evidence**: `grep "@lru_cache\|@cache" --count` → 68 matches, 21 files

### Tier 2: Supporting Performance (Fully Utilized)

| Module | Files | Pattern | Evidence |
|--------|-------|---------|----------|
| `collections.defaultdict/Counter/deque` | 33 | Collection operations | `grep "from collections"` |
| `heapq.nlargest()` | 1 | RSS feed top-N selection | `bengal/postprocess/rss.py:146` |
| `tomllib` | 4 | TOML config parsing | `grep "import tomllib"` |
| `xml.etree.ElementTree` | 5 | RSS/sitemap generation | `grep "xml.etree"` |
| `itertools.groupby` | 2 | Template collection grouping | `grep "itertools"` |
| `operator.attrgetter` | 1 | Section query sorting | `bengal/core/section/queries.py:153` |

### Tier 3: Python 3.14 Modernizations (Adopted)

#### Free-Threaded Python (PEP 703) ✅

**Location**: `bengal/orchestration/render.py:43-69`

```python
def _is_free_threaded() -> bool:
    """Detect if running on free-threaded Python (PEP 703)."""
    if hasattr(sys, "_is_gil_enabled"):
        try:
            return not sys._is_gil_enabled()
        except (AttributeError, TypeError):
            pass
    
    try:
        import sysconfig
        return sysconfig.get_config_var("Py_GIL_DISABLED") == 1
    except (ImportError, AttributeError):
        pass
    
    return False
```

**Impact**: ~1.78x speedup on multi-core (1000 pages: 1.94s vs 3.46s with GIL)

#### Memory Optimizations ✅

| Feature | Count | Evidence | Purpose |
|---------|-------|----------|---------|
| `@dataclass(frozen=True)` | 143 | `grep "frozen=True"` | Immutable, thread-safe |
| `@dataclass(slots=True)` | 18 | `grep "dataclass(slots=True"` | Memory-efficient |
| `__slots__` | 23 files | `grep "__slots__\s*="` | Reduced instance memory |
| PEP 695 type syntax | Adopted | — | Cleaner generics |

**Thread-Safety Validation**: The Patitas `rfc-free-threading-patterns.md` validated that frozen dataclasses are optimal for free-threaded Python:

> "Lock-free reads: Once created, AST can be shared across threads"
> "Patitas scales linearly with threads because: No shared mutable state"

Bengal's 143 frozen dataclasses follow this validated pattern.

---

## Proposal: Remaining Optimizations

### Proposal 1: `str.removeprefix()` / `str.removesuffix()` Expansion

**Status**: Ready to implement

**Problem**: Manual string slicing is error-prone and less readable.

**Current Usage**: 1 file (`bengal/rendering/external_refs/resolver.py:558`)

```python
# Current usage
path_str = url.removeprefix("file://")
```

**Solution**: Systematic replacement of `startswith() + slice` patterns.

**Candidate Locations** (verified):

1. `bengal/orchestration/incremental/version_detector.py:110-120`
   ```python
   # Before
   if path_str.startswith(content_prefix):
       path_str = path_str[len(content_prefix):]
   
   # After
   path_str = path_str.removeprefix(content_prefix)
   ```

2. Similar patterns exist in path manipulation code

**Impact**: Code clarity (performance equivalent)

**Effort**: Very Low (1 hour, grep + targeted replacement)

### Proposal 2: `ExceptionGroup` for Enhanced Error Context

**Status**: Evaluate against existing solution

**Current State**: Bengal already has sophisticated error aggregation via `ErrorAggregator`:

**Location**: `bengal/errors/aggregation.py:62-280`

```python
class ErrorAggregator:
    """
    Aggregates similar errors during batch processing to reduce noise.
    
    Groups errors by signature (error message + context) and provides
    summary logging when threshold is exceeded.
    """
    
    def add_error(self, error: Exception, *, context: dict[str, Any] | None = None) -> None:
        # Groups by signature, keeps sample contexts
        ...
    
    def should_log_individual(self, error, context, threshold=5, max_samples=3) -> bool:
        # Smart deduplication - log first N samples, then aggregate
        ...
    
    def log_summary(self, logger, *, threshold=5, error_type="processing") -> None:
        # Single consolidated log with top errors, percentages, suggestions
        ...
```

**Benefits of Current Approach**:
- ✅ Error deduplication (by signature)
- ✅ Threshold-based logging (reduces noise)
- ✅ Sample context preservation
- ✅ Aggregated summaries with percentages
- ✅ Actionable suggestions

**What `ExceptionGroup` Would Add**:
- Native traceback preservation for all errors
- `except*` handling support
- Standard library compatibility

**Recommendation**: Keep `ErrorAggregator` for logging aggregation, but optionally wrap final errors in `ExceptionGroup` for programmatic handling:

```python
# Proposed enhancement to ErrorAggregator
def as_exception_group(self, message: str) -> ExceptionGroup | None:
    """Return errors as ExceptionGroup for programmatic handling."""
    if not self._errors:
        return None
    return ExceptionGroup(message, self._errors)
```

**Impact**: Better programmatic error handling while preserving current logging benefits

**Effort**: Low (2 hours)

### Proposal 3: `typing.Self` Expansion

**Problem**: Return type annotations for methods returning `self` are verbose.

**Current Usage**: 3 files use `Self`

**TypeVar patterns to replace**: 7 locations

**Candidate Locations** (verified):

1. `bengal/cache/cache_store.py:69`
   ```python
   # Current
   T = TypeVar("T", bound=Cacheable)
   ```

2. `bengal/rendering/parsers/patitas/directives/decorator.py:30-31`
   ```python
   # Current
   TOptions = TypeVar("TOptions", bound="DirectiveOptions")
   TClass = TypeVar("TClass", bound=type)
   ```

3. `bengal/cli/helpers/validation.py:28`, `metadata.py:38`, `error_handling.py:35`
   ```python
   # Current (decorator pattern)
   F = TypeVar("F", bound=Callable[..., Any])
   ```

4. `bengal/cache/cacheable.py:44`
   ```python
   T = TypeVar("T", bound="Cacheable")
   ```

**Note**: Not all `TypeVar` patterns should use `Self`:
- `F = TypeVar("F", bound=Callable)` is for decorators preserving function types
- Only method return types returning `self` should use `Self`

**Impact**: Type clarity for builder patterns (no runtime impact)

**Effort**: Low (1 hour, selective replacement)

---

## Future Consideration: ContextVars Migration

**Status**: Deferred (evaluate post-0.2.0)

**Background**: The Patitas `rfc-free-threading-patterns.md` benchmarked synchronization patterns and recommends:

> "For Bengal (SSG Core): ContextVars for build context"

**Current State**: Bengal uses `threading.local()` extensively (50+ uses):
- `bengal/orchestration/render.py:81` - Pipeline caching
- `bengal/rendering/highlighting/tree_sitter.py:181` - Parser instances
- `bengal/rendering/template_functions/get_page.py:32` - Render cache
- `bengal/cache/dependency_tracker.py:151` - Current page tracking

**ContextVars Benefits** (per Patitas RFC benchmarks):
- ~8M ops/sec throughput
- 1.4x speedup vs locks (no contention)
- Cleaner API (`ContextVar.get/set` vs `getattr/setattr`)
- Async-compatible (future-proofing)

**Concrete Validation**: Patitas Parser achieved **2.2x faster instantiation** and **50% slot reduction** by extracting config flags to ContextVar (18 slots → 9 slots).

**Why Deferred**:
- Current `threading.local()` is valid for ThreadPoolExecutor
- Migration requires careful testing across all parallel paths
- No immediate performance issue identified
- Higher risk than other proposals

**Proposed Pattern** (from Patitas RFC):

```python
from contextvars import ContextVar

# Per-thread build context
build_context: ContextVar[BuildContext] = ContextVar('build_context')

def worker():
    build_context.set(BuildContext())
    ctx = build_context.get()
    # Thread-local, no lock needed
```

**Cross-Reference**: See `patitas/plan/rfc-free-threading-patterns.md` for full benchmark data.

---

## Non-Goals: Evaluated and Rejected

### `bisect` Module

**Consideration**: Binary search for O(log n) lookups in sorted data.

**Decision**: Not applicable to current codebase.

**Rationale**:
- Version lookups use hash-based dictionaries (already O(1))
- Sorted operations are for display ordering, not lookup
- Stack traversals (parsers) aren't sorted-data problems
- No identified linear-search-through-sorted-data patterns

### `orjson` / `ujson` (Third-Party JSON)

**Consideration**: 2-10x faster JSON for large files.

**Decision**: Not needed.

**Rationale**:
- Bengal's JSON operations are small (config, cache metadata)
- Stdlib `json` with `separators=(",", ":")` is sufficient
- Adds external dependency
- `compression.zstd` already handles large cache files

### `struct` Module

**Consideration**: Binary serialization for cache.

**Decision**: Not needed.

**Rationale**:
- JSON + Zstandard compression is sufficient
- `struct` requires schema management
- Debugging binary caches is harder

### `array` Module

**Consideration**: Typed arrays for numeric data.

**Decision**: Not applicable.

**Rationale**:
- Bengal doesn't process large numeric datasets
- Existing data structures are appropriate

---

## Implementation Roadmap

### Sprint 1: Quick Wins (0.5 day)

- [ ] **P1**: `removeprefix()`/`removesuffix()` expansion
  - Grep for `startswith()` + slice patterns: `\.startswith\([^)]+\).*\[len\(`
  - Replace with `removeprefix()` where cleaner
  - Focus on: `version_detector.py`, path handling code

- [ ] **P3**: `typing.Self` expansion (selective)
  - Review 7 TypeVar locations
  - Replace only method-return-self patterns
  - Skip decorator TypeVars (`F = TypeVar("F", bound=Callable)`)
  - mypy verification

**Exit Criteria**: All tests pass, type checking clean

### Sprint 2: Error Handling Enhancement (0.5 day)

- [ ] **P2**: Add `as_exception_group()` to ErrorAggregator
  - Preserve existing aggregation behavior
  - Add optional ExceptionGroup export
  - Update orchestrators to optionally use it

**Exit Criteria**: Existing tests pass, new tests for ExceptionGroup

### Sprint 3: Documentation (0.5 day)

- [ ] Update `TYPE_CHECKING_GUIDE.md` with `Self` patterns
- [ ] Add "Performance Patterns" section to developer docs
- [ ] Document stdlib module usage guidelines

**Exit Criteria**: Guidelines documented

**Total Time**: 1.5 days

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| `removeprefix`/`removesuffix` | 1 file | 5+ files | grep |
| `typing.Self` usage | 3 files | 6+ files | grep |
| ErrorAggregator.as_exception_group | N/A | Available | API exists |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `Self` breaks mypy | Very Low | Low | Run mypy in CI |
| `removeprefix` edge cases | Very Low | Very Low | Unit tests |
| ExceptionGroup changes error display | Low | Low | Keep existing logging, add as optional |

---

## Appendix A: Stdlib Acceleration Inventory

### Fully Utilized

| Module | Evidence | Count |
|--------|----------|-------|
| `compression.zstd` | `bengal/cache/compression.py:24` | 2 files |
| `hashlib` | `grep "import hashlib"` | 19 files |
| `re.compile()` | `grep "re\.compile\("` | 161 patterns, 56 files |
| `collections` | `grep "from collections"` | 33 files |
| `functools` | `grep "@lru_cache\|@cache"` | 68 decorators, 21 files |
| `heapq` | `bengal/postprocess/rss.py:146` | 1 file |
| `tomllib` | `grep "import tomllib"` | 4 files |
| `xml.etree` | `grep "xml.etree"` | 5 files |

### Already Modern

| Feature | Evidence | Count |
|---------|----------|-------|
| `dataclass(frozen=True)` | `grep "frozen=True"` | 143 uses (thread-safe) |
| `removeprefix` | `bengal/rendering/external_refs/resolver.py:558` | 1 file |
| `typing.Self` | `grep "from typing import.*Self"` | 3 files |
| `dataclass(slots=True)` | `grep` | 18 uses |
| `__slots__` | `grep "__slots__\s*="` | 23 files |

### Not Applicable

| Module | Reason |
|--------|--------|
| `bisect` | No sorted-list lookup patterns |
| `struct` | No binary protocols |
| `array` | No numeric workloads |
| `pickle` | Security concerns, JSON preferred |
| `ctypes` | No native library calls needed |

---

## Appendix B: Verification Commands

```bash
# Run these to verify current state

# Compression
grep -r "from compression import zstd" bengal/

# Hashlib usage
grep -r "import hashlib\|from hashlib" bengal/ | wc -l

# Regex compilation
grep -r "re\.compile(" bengal/ | wc -l

# LRU cache decorators
grep -r "@lru_cache\|@cache" bengal/ | wc -l

# Collections usage
grep -r "from collections import" bengal/ | wc -l

# removeprefix/removesuffix
grep -r "removeprefix\|removesuffix" bengal/

# TypeVar bound patterns (Self candidates)
grep -r "TypeVar.*bound=" bengal/

# typing.Self usage
grep -r "from typing import.*Self" bengal/

# Slots and frozen usage
grep -r "dataclass(slots=True" bengal/ | wc -l
grep -r "__slots__\s*=" bengal/ | wc -l
grep -r "frozen=True" bengal/ | wc -l

# ContextVars usage (currently 0, future consideration)
grep -r "ContextVar\|contextvars" bengal/

# threading.local usage (migration candidates)
grep -r "threading\.local" bengal/ | wc -l
```

---

## References

### PEPs

- [PEP 784 – Adding Zstandard to the Standard Library](https://peps.python.org/pep-0784/)
- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 673 – Self Type](https://peps.python.org/pep-0673/)
- [PEP 654 – Exception Groups](https://peps.python.org/pep-0654/)
- [Python 3.14 Release Notes](https://docs.python.org/3.14/whatsnew/3.14.html)

### Related RFCs

- `patitas/plan/rfc-free-threading-patterns.md` – Synchronization pattern benchmarks validating immutable architecture and ContextVars recommendations for Bengal ecosystem
