# RFC: Analysis Package Error System Adoption

**Status**: Evaluated  
**Created**: 2025-12-24  
**Evaluated**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/analysis/`, `bengal/errors/`  
**Confidence**: 92% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Foundation layer needs error consistency  
**Estimated Effort**: 0.5 days (single dev)

---

## Executive Summary

The `bengal/analysis/` package **partially adopts** the Bengal error system. Error codes (G001, G002) are used consistently, but the package lacks a dedicated exception class and has documentation drift in docstrings.

**Current state**:
- **5 files** import `BengalError, ErrorCode`
- **25 total uses** of `ErrorCode.G001/G002` across 5 files
- **3 unused codes**: G003, G004, G005 defined but never raised
- **4 files** lack any error system imports
- **No dedicated exception class** like other domains have

**Adoption Score**: 5/10

**Recommendation**: Add `BengalGraphError` exception class, fix docstring drift, and either use or remove unused error codes.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Proposed Changes](#proposed-changes)
5. [Implementation Phases](#implementation-phases)
6. [Success Criteria](#success-criteria)
7. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

The Bengal error system provides:
- **Error codes** for searchability and documentation linking
- **Build phase tracking** for investigation
- **Related test file mapping** for debugging
- **Investigation helpers** (grep commands, related files)
- **Consistent formatting** across the codebase

The analysis package uses the base `BengalError` class directly, missing:
- Automatic `BuildPhase` assignment
- Test file mapping in `get_related_test_files()`
- Domain-specific error context
- Consistent exception hierarchy

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No `BengalGraphError` | Generic error messages | No test file suggestions |
| Docstring drift | Misleading API docs | Incorrect exception handling |
| Unused codes | Wasted namespace | Confusing code catalog |
| Silent catches | Hidden failures | Hard-to-debug issues |

---

## Current State Evidence

### Error Code Definition

**File**: `bengal/errors/codes.py:208-214`

```python
# ============================================================
# Graph/Analysis errors (G001-G099)
# ============================================================
G001 = "graph_not_built"
G002 = "graph_invalid_parameter"
G003 = "graph_cycle_detected"
G004 = "graph_disconnected_component"
G005 = "graph_analysis_failed"
```

### Import Patterns

| File | Import | Status |
|------|--------|--------|
| `knowledge_graph.py` | `from bengal.errors import BengalError, ErrorCode` | ✅ |
| `graph_analysis.py` | `from bengal.errors import BengalError, ErrorCode` | ✅ |
| `graph_reporting.py` | `from bengal.errors import BengalError, ErrorCode` | ✅ |
| `graph_visualizer.py` | `from bengal.errors import BengalError, ErrorCode` | ✅ |
| `page_rank.py` | `from bengal.errors import BengalError, ErrorCode` | ✅ |
| `graph_builder.py` | — | ❌ No import |
| `community_detection.py` | — | ❌ No import |
| `link_suggestions.py` | — | ❌ No import |
| `path_analysis.py` | — | ❌ No import |

### Error Code Usage

**Total**: 25 uses of `ErrorCode.G0xx` across 5 files.

| File | G001 | G002 | Total |
|------|------|------|-------|
| `knowledge_graph.py` | 19 | 0 | 19 |
| `page_rank.py` | 0 | 3 | 3 |
| `graph_analysis.py` | 1 | 0 | 1 |
| `graph_reporting.py` | 1 | 0 | 1 |
| `graph_visualizer.py` | 1 | 0 | 1 |

**Example G001** (`graph_not_built`):

```python
# knowledge_graph.py:250-254
raise BengalError(
    "Graph not built. Call build() first.",
    code=ErrorCode.G001,
    suggestion="Call build() before accessing graph data",
)
```

**Example G002** (`graph_invalid_parameter`):

```python
# page_rank.py:158-161
raise BengalError(
    f"Invalid damping factor: {damping_factor}. Must be 0 < d < 1.",
    code=ErrorCode.G002,
)
```

**G003, G004, G005** — Defined but **never used** anywhere in codebase.

### Comparison with Other Domains

| Domain | Exception Class | Auto Build Phase | Test Mapping |
|--------|-----------------|------------------|--------------|
| Config | `BengalConfigError` | ✅ `INITIALIZATION` | ✅ |
| Content | `BengalContentError` | ✅ `PARSING` | ✅ |
| Rendering | `BengalRenderingError` | ✅ `RENDERING` | ✅ |
| Discovery | `BengalDiscoveryError` | ✅ `DISCOVERY` | ✅ |
| Cache | `BengalCacheError` | ✅ `CACHE` | ✅ |
| Server | `BengalServerError` | ✅ `SERVER` | ✅ |
| Assets | `BengalAssetError` | ✅ `ASSET_PROCESSING` | ✅ |
| **Analysis** | ❌ Uses `BengalError` | ❌ Not set | ❌ Not mapped |

---

## Gap Analysis

### 1. Missing Exception Class

**Current**: Uses base `BengalError` directly  
**Expected**: Dedicated `BengalGraphError` with auto-phase

**Evidence**: `bengal/errors/exceptions.py` defines 7 domain-specific classes but none for graph/analysis.

### 2. Missing Build Phase

**Current**: No `BuildPhase.ANALYSIS` exists  
**Expected**: Enum value in `context.py`

**Evidence**: `bengal/errors/context.py:120-128` defines 9 phases but lacks `ANALYSIS`:

```python
class BuildPhase(Enum):
    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    PARSING = "parsing"
    RENDERING = "rendering"
    POSTPROCESSING = "postprocessing"
    ASSET_PROCESSING = "asset_processing"
    CACHE = "cache"
    SERVER = "server"
    OUTPUT = "output"
    # Missing: ANALYSIS
```

### 3. Docstring Drift

Multiple methods document wrong exception types:

| File | Line | Docstring | Actual |
|------|------|-----------|--------|
| `graph_analysis.py` | 95 | `Raises: RuntimeError` | `BengalError` |
| `graph_analysis.py` | 128 | `Raises: RuntimeError` | `BengalError` |
| `graph_analysis.py` | 151 | `Raises: RuntimeError` | `BengalError` |
| `graph_analysis.py` | 184 | `Raises: RuntimeError` | `BengalError` |
| `graph_analysis.py` | 214 | `Raises: RuntimeError` | `BengalError` |
| `graph_analysis.py` | 247 | `Raises: RuntimeError` | `BengalError` |
| `graph_reporting.py` | 91 | `Raises: ValueError` | `BengalError` |

### 4. Silent Exception Swallowing

`graph_builder.py` catches exceptions and logs without propagating in **2 locations**:

**Location 1** — `graph_builder.py:278-283`:

```python
except Exception as e:
    logger.warning(
        "graph_page_analysis_failed",
        page=str(getattr(page, "source_path", page)),
        error=str(e),
    )
```

**Location 2** — `graph_builder.py:326-331`:

```python
except Exception as e:
    logger.debug(
        "knowledge_graph_link_extraction_failed",
        page=str(page.source_path),
        error=str(e),
        exc_info=True,
    )
```

Both could use `ErrorCode.G005` (`graph_analysis_failed`) with proper error context and `record_error()` for session tracking.

### 5. Unused Error Codes

| Code | Value | Usage |
|------|-------|-------|
| G003 | `graph_cycle_detected` | Never raised |
| G004 | `graph_disconnected_component` | Never raised |
| G005 | `graph_analysis_failed` | Never raised |

**Decision needed**: Use these codes or remove them.

---

## Proposed Changes

### Phase 1: Add Infrastructure (30 min)

#### 1.1 Add `BuildPhase.ANALYSIS`

**File**: `bengal/errors/context.py`

```python
class BuildPhase(Enum):
    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    PARSING = "parsing"
    RENDERING = "rendering"
    CACHE = "cache"
    ASSET_PROCESSING = "asset_processing"
    SERVER = "server"
    ANALYSIS = "analysis"  # NEW
```

#### 1.2 Add `BengalGraphError`

**File**: `bengal/errors/exceptions.py`

```python
class BengalGraphError(BengalError):
    """
    Graph analysis errors.

    Raised for issues with knowledge graph construction and analysis
    including unbuilt graphs, invalid parameters, and analysis failures.
    Automatically sets build phase to ANALYSIS.

    Common Error Codes:
        - G001: Graph not built yet
        - G002: Invalid parameter for analysis
        - G003: Cycle detected in graph
        - G004: Disconnected component found
        - G005: Analysis operation failed

    Example:
        >>> raise BengalGraphError(
        ...     "Graph not built. Call build() first.",
        ...     code=ErrorCode.G001,
        ...     suggestion="Call build() before accessing graph data",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase
            kwargs["build_phase"] = BuildPhase.ANALYSIS
        super().__init__(message, **kwargs)
```

#### 1.3 Update Test Mapping

**File**: `bengal/errors/exceptions.py` (in `get_related_test_files`)

```python
test_mapping: dict[type, list[str]] = {
    # ... existing mappings ...
    BengalGraphError: [
        "tests/unit/analysis/",
    ],
}
```

> **Note**: 12 test files exist in `tests/unit/analysis/` including `test_knowledge_graph.py`, `test_graph_analysis.py`, `test_graph_builder_parallel.py`, and `test_page_rank.py`.

#### 1.4 Export from `__init__.py`

**File**: `bengal/errors/__init__.py`

```python
from bengal.errors.exceptions import (
    # ... existing ...
    BengalGraphError,
)

__all__ = [
    # ... existing ...
    "BengalGraphError",
]
```

### Phase 2: Migrate Analysis Package (1 hour)

#### 2.1 Update Imports

Change in 5 files:

```python
# Before
from bengal.errors import BengalError, ErrorCode

# After
from bengal.errors import BengalGraphError, ErrorCode
```

#### 2.2 Migrate Raises

Change all `raise BengalError(... code=ErrorCode.G0xx ...)` to `raise BengalGraphError(...)`:

```python
# Before
raise BengalError(
    "Graph not built. Call build() first.",
    code=ErrorCode.G001,
    suggestion="Call build() before accessing graph data",
)

# After
raise BengalGraphError(
    "Graph not built. Call build() first.",
    code=ErrorCode.G001,
    suggestion="Call build() before accessing graph data",
)
```

**Files to update**:
- `knowledge_graph.py` (~20 raises)
- `graph_analysis.py` (1 raise)
- `graph_reporting.py` (1 raise)
- `graph_visualizer.py` (1 raise)
- `page_rank.py` (3 raises)

### Phase 3: Fix Docstrings (30 min)

Update all docstrings that say `RuntimeError` or `ValueError`:

```python
# Before
def get_hubs(self, threshold: int = 10) -> list[Page]:
    """
    ...
    Raises:
        RuntimeError: If graph hasn't been built yet
    """

# After
def get_hubs(self, threshold: int = 10) -> list[Page]:
    """
    ...
    Raises:
        BengalGraphError: If graph hasn't been built yet (G001)
    """
```

**Files to update**:
- `graph_analysis.py` (6 docstrings)
- `graph_reporting.py` (1 docstring)

### Phase 4: Address Unused Codes (15 min)

**Option A**: Use them where appropriate

| Code | Where to use |
|------|--------------|
| G003 | `graph_builder.py` when detecting cycles |
| G004 | `graph_analysis.py` when finding disconnected components |
| G005 | `graph_builder.py` for parallel analysis failures |

**Option B**: Remove them

Remove G003-G005 from `codes.py` if no use cases exist.

**Recommendation**: Option A — add G005 for analysis failures in `graph_builder.py`.

### Phase 5: Improve Error Propagation (30 min)

Silent failures in `graph_builder.py` hide issues during development. Proper error tracking enables:
- Error session aggregation for build summaries
- Investigation hints via `get_grep_command()`
- Test file suggestions for debugging

**Location 1** — `graph_builder.py:278`:

```python
# Before
except Exception as e:
    logger.warning("graph_page_analysis_failed", ...)

# After
except Exception as e:
    from bengal.errors import record_error, BengalGraphError, ErrorCode

    error = BengalGraphError(
        f"Page analysis failed: {page.source_path}",
        code=ErrorCode.G005,
        file_path=getattr(page, "source_path", None),
        original_error=e,
        suggestion="Check page content and link structure",
    )
    record_error(error, file_path=str(page.source_path))
    logger.warning(
        "graph_page_analysis_failed",
        page=str(getattr(page, "source_path", page)),
        error=str(e),
        code="G005",
    )
```

**Location 2** — `graph_builder.py:326`:

```python
# Before
except Exception as e:
    logger.debug("knowledge_graph_link_extraction_failed", ...)

# After
except Exception as e:
    from bengal.errors import record_error, BengalGraphError, ErrorCode

    error = BengalGraphError(
        f"Link extraction failed: {page.source_path}",
        code=ErrorCode.G005,
        file_path=page.source_path,
        original_error=e,
        suggestion="Check link syntax in page content",
    )
    record_error(error, file_path=str(page.source_path))
    logger.debug(
        "knowledge_graph_link_extraction_failed",
        page=str(page.source_path),
        error=str(e),
        code="G005",
    )
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add `BuildPhase.ANALYSIS` + `BengalGraphError` | 30 min | P1 |
| 2 | Migrate raises to `BengalGraphError` | 1 hour | P1 |
| 3 | Fix docstrings | 30 min | P2 |
| 4 | Improve error propagation (2 locations) | 30 min | P2 |
| 5 | Use or remove G003-G005 | 15 min | P3 |

**Total**: 2.5-3 hours

> **Priority rationale**: Phase 4 promoted to P2 because silent failures in `graph_builder.py` hide debugging information during development. Error session tracking requires proper `record_error()` calls.

---

## Success Criteria

### Must Have

- [ ] `BengalGraphError` class exists in `exceptions.py`
- [ ] `BuildPhase.ANALYSIS` exists in `context.py`
- [ ] All `raise BengalError(code=G0xx)` migrated to `BengalGraphError`
- [ ] `BengalGraphError` exported from `bengal.errors`
- [ ] Test mapping added for `BengalGraphError`

### Should Have

- [ ] Docstrings updated to reference `BengalGraphError`
- [ ] G003/G004/G005 either used or removed
- [ ] All analysis files import from `bengal.errors`

### Should Have (continued)

- [ ] Error propagation improved in `graph_builder.py` (2 locations)
- [ ] Error session tracking via `record_error()` for analysis failures

### Nice to Have

- [ ] Integration test for graph error handling
- [ ] Use G003 for cycle detection scenarios
- [ ] Use G004 for disconnected component warnings

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing exception handlers | Low | Medium | `BengalGraphError` extends `BengalError` — no breaking change |
| Test failures | Low | Low | Run `pytest tests/unit/analysis/` after changes |
| Missed migration | Low | Low | grep for `BengalError.*G00` to find stragglers |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/errors/context.py` | Add enum value + module mapping | +3 |
| `bengal/errors/exceptions.py` | Add class + test mapping | +35 |
| `bengal/errors/__init__.py` | Export new class | +2 |
| `bengal/analysis/knowledge_graph.py` | Migrate imports/raises | ~25 |
| `bengal/analysis/graph_analysis.py` | Migrate + fix docstrings | ~8 |
| `bengal/analysis/graph_reporting.py` | Migrate + fix docstrings | ~3 |
| `bengal/analysis/graph_visualizer.py` | Migrate | ~2 |
| `bengal/analysis/page_rank.py` | Migrate | ~4 |
| `bengal/analysis/graph_builder.py` | Add error imports + record_error | ~15 |
| **Total** | — | ~97 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 8/10 | 9/10 | G003-G005 addressed |
| Exception class | 4/10 | 10/10 | Dedicated class added |
| Build phase tracking | 2/10 | 10/10 | Auto-set via class |
| Documentation accuracy | 5/10 | 9/10 | Docstrings fixed |
| Error propagation | 4/10 | 9/10 | Both silent catch sites fixed |
| Test mapping | 0/10 | 10/10 | Maps to 12 test files |
| **Overall** | **5/10** | **9.5/10** | — |

---

## References

- `bengal/errors/codes.py:208-214` — G-series error codes
- `bengal/errors/exceptions.py` — Exception class patterns  
- `bengal/errors/context.py:95-128` — BuildPhase enum
- `bengal/analysis/knowledge_graph.py` — Primary consumer (19 G001 uses)
- `bengal/analysis/graph_builder.py:278,326` — Silent exception locations
- `tests/unit/analysis/` — 12 test files for validation
