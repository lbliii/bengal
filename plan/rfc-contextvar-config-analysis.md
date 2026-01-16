# RFC: ContextVar Config Pattern - Bengal Analysis

**Status**: ✅ Validated via Benchmark  
**Created**: 2026-01-13  
**Related**: `patitas/plan/rfc-contextvar-config.md`, `patitas/plan/rfc-free-threading-patterns.md`

---

## Executive Summary

Analysis and **benchmark validation** of Bengal's codebase for ContextVar config pattern opportunities.

**Benchmark Results** (Python 3.12, 100K iterations):

| Class | Speedup | Slot Reduction |
|-------|---------|----------------|
| **Parser** | **1.93x** | 50% (18→9) |
| **Renderer** | **1.32x** | 43% (14→8) |

**ContextVar Lookup**: 57.8M ops/sec (negligible overhead)

---

## Methodology

1. Grep for `__slots__` declarations
2. Identify config-like vs per-instance attributes
3. Estimate slot reduction and instantiation frequency
4. Calculate potential impact

---

## Candidates Analyzed

### 🎯 High Impact: Parser (Embedded Patitas)

**Location**: `bengal/rendering/parsers/patitas/parser.py:63-88`

```python
# Current: 18 slots (identical to standalone Patitas)
__slots__ = (
    "_source",
    "_tokens",
    "_pos",
    "_current",
    "_source_file",
    "_text_transformer",        # Config ← EXTRACT
    "_tables_enabled",          # Config ← EXTRACT
    "_strikethrough_enabled",   # Config ← EXTRACT
    "_task_lists_enabled",      # Config ← EXTRACT
    "_footnotes_enabled",       # Config ← EXTRACT
    "_math_enabled",            # Config ← EXTRACT
    "_autolinks_enabled",       # Config ← EXTRACT
    "_directive_registry",      # Config ← EXTRACT
    "_directive_stack",
    "_strict_contracts",        # Config ← EXTRACT
    "_link_refs",
    "_containers",
    "_allow_setext_headings",
)
```

**Benchmark Results** (validated):
| Metric | Current | After ContextVar | Improvement |
|--------|---------|------------------|-------------|
| Slots | 18 | 9 | **50%** |
| Instantiation | 36.3ms/100K | 18.8ms/100K | **1.93x faster** |
| Instances/Build | 1K+ (1 per page) | Same | — |

**Verdict**: ✅ **High Impact** — Validated via benchmark.

---

### 🎯 High Impact: HTMLRenderer

**Location**: `bengal/rendering/parsers/patitas/renderers/html.py:96-111`

```python
# Current: 14 slots
__slots__ = (
    "_source",
    "_highlight",               # Config ← EXTRACT
    "_highlight_style",         # Config ← EXTRACT
    "_rosettes_available",      # Config ← EXTRACT (derived)
    "_directive_registry",      # Config ← EXTRACT
    "_directive_cache",         # Could share via ContextVar
    "_role_registry",           # Config ← EXTRACT
    "_text_transformer",        # Config ← EXTRACT
    "_delegate",
    "_headings",                # Per-render state
    "_slugify",                 # Config ← EXTRACT
    "_seen_slugs",              # Per-render state
    "_page_context",            # Per-render state
    "_current_page",            # Alias for _page_context
)
```

**Proposed RenderConfig**:

```python
@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Immutable render configuration."""
    highlight: bool = False
    highlight_style: Literal["semantic", "pygments"] = "semantic"
    directive_registry: DirectiveRegistry | None = None
    role_registry: RoleRegistry | None = None
    text_transformer: Callable[[str], str] | None = None
    slugify: Callable[[str], str] | None = None

_render_config: ContextVar[RenderConfig] = ContextVar('render_config')

# After: 8 slots
__slots__ = (
    "_source",
    "_delegate",
    "_headings",
    "_seen_slugs",
    "_page_context",
    "_current_page",
    "_directive_cache",  # Per-site cache
    "_rosettes_available",  # Computed once
)
```

**Benchmark Results** (validated):
| Metric | Current | After ContextVar | Improvement |
|--------|---------|------------------|-------------|
| Slots | 14 | 8 | **43%** |
| Instantiation | 23.5ms/100K | 17.8ms/100K | **1.32x faster** |
| Instances/Build | 1K+ | Same | — |

**Verdict**: ✅ **High Impact** — Validated via benchmark.

---

### ⚠️ Medium Impact: Lexer

**Location**: `bengal/rendering/parsers/patitas/lexer/core.py:81-106`

```python
# Current: 19 slots
__slots__ = (
    "_source",
    "_source_len",
    "_pos",
    "_lineno",
    "_col",
    "_mode",
    "_source_file",
    "_fence_char",
    "_fence_count",
    "_fence_info",
    "_fence_indent",
    "_consumed_newline",
    "_saved_lineno",
    "_saved_col",
    "_directive_stack",
    "_text_transformer",        # Config ← Only 1 extractable
    "_html_block_type",
    "_html_block_content",
    "_html_block_start",
    "_html_block_indent",
    "_previous_line_blank",
)
```

**Analysis**:
| Metric | Current | After ContextVar | Improvement |
|--------|---------|------------------|-------------|
| Slots | 19 | 18 | **5%** |
| Benefit | Minimal | — | Not worth complexity |

**Verdict**: ⚠️ **Skip** — Only 1 config attribute, not worth extraction.

---

### ⚠️ Low Impact: RenderingPipeline

**Location**: `bengal/rendering/pipeline/core.py:109`

- Uses regular attributes (no `__slots__`)
- Thread-local caching: 1 instance per worker thread
- Not frequently instantiated

**Verdict**: ⚠️ **Skip** — Low instantiation frequency.

---

### ⚠️ Low Impact: LRUCache

**Location**: `bengal/utils/primitives/lru_cache.py:59-69`

```python
__slots__ = (
    "_cache",
    "_maxsize",      # Could extract
    "_ttl",          # Could extract
    "_lock",
    "_timestamps",
    "_hits",
    "_misses",
    "_enabled",      # Could extract
    "_name",         # Could extract
)
```

- 9 slots, ~4 config-like
- But: Created once per cache, not per operation
- Minimal instantiation overhead

**Verdict**: ⚠️ **Skip** — Low instantiation frequency.

---

## Impact Summary (Validated)

| Class | Slots Reduction | Instantiation Speedup | Instances/Build | Priority |
|-------|-----------------|----------------------|-----------------|----------|
| **Parser** | 18→9 (50%) | **1.93x** ✅ | 1K+ | 🔴 High |
| **HTMLRenderer** | 14→8 (43%) | **1.32x** ✅ | 1K+ | 🔴 High |
| Lexer | 19→18 (5%) | ~1.05x | 1K+ | ⚪ Skip |
| RenderingPipeline | N/A | N/A | ~8 | ⚪ Skip |
| LRUCache | 9→5 (44%) | ~1.5x | ~20 | ⚪ Skip |

---

## Benchmark Results

**Environment**: Python 3.12.2, 100,000 iterations

```
PARSER INSTANTIATION
  Current (18 slots):        36.30ms
  ContextVar (9 slots):      18.78ms
  Speedup:                    1.93x

RENDERER INSTANTIATION
  Current (14 slots):        23.48ms
  ContextVar (8 slots):      17.83ms
  Speedup:                    1.32x

CONTEXTVAR LOOKUP OVERHEAD
  100,000 lookups:            1.73ms
  Throughput:                57.80M ops/sec
```

**Combined Impact** (1,000 page build):
| Metric | Current | ContextVar | Saved |
|--------|---------|------------|-------|
| Instantiation | 0.60ms | 0.37ms | **0.23ms** |

**Note**: This is instantiation time only. Memory savings (smaller objects) provide additional GC benefits.

---

## Recommended Implementation

### Phase 1: Parser (Sync with Patitas)

Since Bengal embeds Patitas, the Parser optimization should mirror `patitas/plan/rfc-contextvar-config.md`:

1. Create `ParseConfig` frozen dataclass
2. Create `_parse_config: ContextVar[ParseConfig]`
3. Reduce Parser slots from 18→9
4. Add property accessors for config fields

**Effort**: Low (copy from Patitas implementation)

### Phase 2: HTMLRenderer

1. Create `RenderConfig` frozen dataclass
2. Create `_render_config: ContextVar[RenderConfig]`
3. Reduce HTMLRenderer slots from 14→8
4. Add property accessors

**Effort**: Medium (new implementation)

### Phase 3: Validation

1. Run build benchmarks (100K instantiations)
2. Verify thread safety with parallel builds
3. Profile memory usage reduction

---

## Cross-References

- **Patitas RFC**: `patitas/plan/rfc-contextvar-config.md` — Original pattern and benchmarks
- **Free-Threading RFC**: `patitas/plan/rfc-free-threading-patterns.md` — Pattern validation
- **Bengal Stdlib RFC**: `bengal/plan/rfc-stdlib-acceleration-audit.md` — ContextVars future consideration

---

## Conclusion

**✅ Recommended**: Implement ContextVar config pattern for **Parser** and **HTMLRenderer**.

**Validated Impact** (benchmark confirmed):
- Parser: 50% slot reduction, **1.93x faster** instantiation
- HTMLRenderer: 43% slot reduction, **1.32x faster** instantiation
- ContextVar lookup: **57.8M ops/sec** (negligible overhead)
- Combined: ~0.23ms saved per 1K pages (instantiation only)
- Memory: Smaller object footprint, reduced GC pressure

**Not Recommended**: Lexer, RenderingPipeline, LRUCache (low instantiation frequency or minimal config attributes).

---

## Appendix: Benchmark Script

See `benchmarks/test_contextvar_config.py` for reproducible benchmarks.
