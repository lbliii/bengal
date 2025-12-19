# RFC: Stats Architecture Refactor

**Status**: Implemented ✅  
**Created**: 2025-12-19  
**Implemented**: 2025-12-19  
**Author**: AI Assistant  
**Confidence**: 88% 🟢
**Priority**: P2 (Medium)  

---

## Executive Summary

Refactor Bengal's build statistics system from a monolithic dataclass into a composable, protocol-based architecture. This eliminates the brittleness caused by having multiple incompatible stats representations (`BuildStats`, `BuildResult`, local `_Stats` stubs) that break at runtime when attributes don't match.

---

## Problem Statement

### Current State

Bengal has **three different stats types** that must stay synchronized manually:

| Type | Location | Purpose | Attributes |
|------|----------|---------|------------|
| `BuildStats` | `build_stats.py:40` | Full canonical stats | 30+ attributes |
| `BuildResult` | `build_executor.py:67` | Subprocess IPC (picklable) | 5 attributes |
| `_Stats` (local) | `build_trigger.py:374` | Manual adapter | ~15 attributes |

**Evidence**:
- `bengal/utils/build_stats.py:40-104`: Monolithic dataclass with 30+ fields
- `bengal/server/build_executor.py:67-85`: Minimal picklable result
- `bengal/server/build_trigger.py:374-393`: Manual stub that broke (missing `discovery_time_ms`)

### The Architecture Gap

```
┌─────────────────────────────────────────────────────────────────┐
│ In-process build path (dev_server.py initial build)            │
│                                                                 │
│   site.build() ──► BuildStats ──► display_build_stats() ✅     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Subprocess build path (build_trigger.py rebuilds)              │
│                                                                 │
│   executor.submit() ──► BuildResult ──► _Stats adapter ──►     │
│                              ▲               ▲                  │
│                              │               │                  │
│                    (minimal, picklable)  (manual, breaks!)      │
│                                                                 │
│   ... ──► display_build_stats() 💥 AttributeError              │
└─────────────────────────────────────────────────────────────────┘
```

### Root Causes

1. **Monolithic design**: `BuildStats` grew to 30+ fields organically
2. **No shared contract**: `display_build_stats()` expects `BuildStats` but duck-types at runtime
3. **Manual adapters**: `_Stats` must replicate all attributes display might access
4. **Silent failures**: Type checker can't catch mismatches—they explode at runtime
5. **IPC constraint**: `BuildResult` is intentionally minimal for subprocess pickling

### Pain Points

1. **Fragile**: Adding a field to `BuildStats` breaks adapters silently
2. **Duplicated**: Same data defined in multiple places
3. **Untestable**: No way to verify adapter completeness
4. **Opaque**: Unclear which attributes are actually required vs optional

---

## Goals & Non-Goals

**Goals**:
- Type-safe stats contract that catches mismatches at static analysis time
- Composable stats components (timing, counts, cache, health)
- Graceful degradation when optional data is unavailable
- Single source of truth for attribute definitions
- Backward-compatible migration path

**Non-Goals**:
- Change the subprocess IPC mechanism
- Add new stats metrics (separate concern)
- Modify the CLI output format
- Real-time stats streaming

---

## Design Options

### Option A: Protocol-Based Layering ⭐ Recommended

Define explicit protocols for different stats "views":

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class CoreStats(Protocol):
    """Minimal stats every build must provide."""
    total_pages: int
    build_time_ms: float
    incremental: bool
    parallel: bool

@runtime_checkable  
class DisplayableStats(CoreStats, Protocol):
    """Stats sufficient for display_build_stats()."""
    # Core counts
    regular_pages: int
    generated_pages: int
    total_assets: int
    total_sections: int
    taxonomies_count: int
    total_directives: int
    directives_by_type: dict[str, int]
    skipped: bool
    warnings: list[Any]

    # Phase timings (display handles 0 gracefully)
    discovery_time_ms: float
    taxonomy_time_ms: float
    rendering_time_ms: float
    assets_time_ms: float
    postprocess_time_ms: float
    health_check_time_ms: float
```

**Pros**:
- Type-safe: `display_build_stats(stats: DisplayableStats)` catches mismatches
- Self-documenting: Protocol defines the exact contract
- Composable: Can mix protocols (`CoreStats`, `HasTimings`, `HasCache`)
- Backward-compatible: `BuildStats` already implements `DisplayableStats`

**Cons**:
- Protocols can't enforce defaults (still need adapter logic)
- Requires updating type hints across codebase

### Option B: Composition Pattern

Break `BuildStats` into focused dataclasses composed together:

```python
@dataclass
class CountStats:
    """Page and asset counts."""
    total_pages: int = 0
    regular_pages: int = 0
    generated_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0

@dataclass
class TimingStats:
    """Phase timing breakdown."""
    build_time_ms: float = 0
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0
    health_check_time_ms: float = 0

@dataclass
class BuildStats:
    """Full stats composed from components."""
    counts: CountStats = field(default_factory=CountStats)
    timing: TimingStats = field(default_factory=TimingStats)
    cache: CacheStats | None = None
    health: HealthStats | None = None
    # ... flags
    incremental: bool = False
    parallel: bool = True
```

**Pros**:
- Clear separation of concerns
- Components can be passed independently
- Easy to add new stat categories

**Cons**:
- Breaking change to attribute access (`stats.counts.total_pages` vs `stats.total_pages`)
- Requires widespread codebase changes
- More verbose

### Option C: Factory + Adapter Pattern

Create a factory that produces the right stats type for each context:

```python
class StatsFactory:
    @staticmethod
    def from_build_result(result: BuildResult) -> DisplayableStats:
        """Convert subprocess result to displayable stats."""
        return _MinimalStats(
            total_pages=result.pages_built,
            build_time_ms=result.build_time_ms,
            # ... with sensible defaults for missing fields
        )

    @staticmethod  
    def from_orchestrator(orchestrator: BuildOrchestrator) -> BuildStats:
        """Extract full stats from orchestrator."""
        return orchestrator.stats
```

**Pros**:
- Centralizes adapter logic
- Clear conversion points
- Testable in isolation

**Cons**:
- Still need to define what `DisplayableStats` requires
- Factory can get out of sync with display function

### Option D: Defensive Access (Band-Aid)

Make `display_build_stats()` use `getattr()` with defaults everywhere:

```python
def display_build_stats(stats: Any, ...) -> None:
    discovery = getattr(stats, 'discovery_time_ms', 0.0)
    if discovery > 0:
        cli.print(f"Discovery: {format_time(discovery)}")
```

**Pros**:
- Simple, immediate fix
- No architectural changes

**Cons**:
- Hides bugs rather than preventing them
- No type safety
- "Any" type defeats static analysis
- Technical debt accumulation

---

## Recommended Solution: Protocol + Factory (A + C)

Combine Protocol-Based Layering with Factory Pattern for the cleanest solution:

### Phase 1: Define Protocols (Low Risk)

```python
# bengal/utils/stats_protocol.py

from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class CoreStats(Protocol):
    """Minimal contract for any stats object."""
    total_pages: int
    build_time_ms: float
    incremental: bool

@runtime_checkable
class DisplayableStats(CoreStats, Protocol):
    """Contract for display_build_stats()."""
    # Counts
    regular_pages: int
    generated_pages: int
    total_assets: int
    total_sections: int
    taxonomies_count: int
    total_directives: int
    directives_by_type: dict[str, int]

    # Flags
    parallel: bool
    skipped: bool
    warnings: list[Any]

    # Timings (display checks > 0 before showing)
    discovery_time_ms: float
    taxonomy_time_ms: float
    rendering_time_ms: float
    assets_time_ms: float
    postprocess_time_ms: float
    health_check_time_ms: float
```

### Phase 2: Create Minimal Stats Implementation

```python
# bengal/utils/stats_minimal.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class MinimalStats:
    """
    Lightweight stats for subprocess results.

    Implements DisplayableStats protocol with sensible defaults
    for attributes not available from BuildResult.
    """
    # From BuildResult
    total_pages: int
    build_time_ms: float
    incremental: bool

    # Defaults for display compatibility
    regular_pages: int = 0
    generated_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0
    total_directives: int = 0
    directives_by_type: dict[str, int] = field(default_factory=dict)
    parallel: bool = True
    skipped: bool = False
    warnings: list[Any] = field(default_factory=list)

    # Timings default to 0 (display skips if 0)
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0
    health_check_time_ms: float = 0

    @classmethod
    def from_build_result(cls, result: "BuildResult", incremental: bool = True) -> "MinimalStats":
        """Create MinimalStats from subprocess BuildResult."""
        return cls(
            total_pages=result.pages_built,
            regular_pages=result.pages_built,  # Assume all regular for subprocess
            build_time_ms=result.build_time_ms,
            incremental=incremental,
        )
```

### Phase 3: Update Type Hints

```python
# bengal/utils/build_stats.py

from bengal.utils.stats_protocol import DisplayableStats

def display_build_stats(
    stats: DisplayableStats,  # Was: BuildStats
    show_art: bool = True,
    output_dir: str | None = None,
) -> None:
    """Display build statistics."""
    # Implementation unchanged - already accesses via attributes
    ...
```

### Phase 4: Replace Local Stub

```python
# bengal/server/build_trigger.py

from bengal.utils.stats_minimal import MinimalStats

def _display_stats(self, result: BuildResult, incremental: bool) -> None:
    """Display build statistics."""
    stats = MinimalStats.from_build_result(result, incremental)
    display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
```

---

## Architecture Impact

**Affected Subsystems**:
- **Utils** (`bengal/utils/`): New protocol and minimal stats modules
- **Server** (`bengal/server/`): Replace local `_Stats` stub
- **CLI** (`bengal/cli/`): Update type hints (optional, for completeness)

**New Components**:
- `bengal/utils/stats_protocol.py` - Protocol definitions
- `bengal/utils/stats_minimal.py` - Lightweight stats implementation

**Modified Components**:
- `bengal/utils/build_stats.py` - Update type hint for `display_build_stats()`
- `bengal/server/build_trigger.py` - Remove local `_Stats`, use `MinimalStats`

---

## Migration Path

### Step 1: Add Protocols (Non-Breaking)
- Create `stats_protocol.py` with `CoreStats` and `DisplayableStats`
- No changes to existing code yet

### Step 2: Add MinimalStats (Non-Breaking)
- Create `stats_minimal.py` with `MinimalStats` dataclass
- Add `from_build_result()` factory method

### Step 3: Replace Local Stub (Bug Fix)
- Remove `_Stats` class from `build_trigger.py`
- Use `MinimalStats.from_build_result()` instead
- This is effectively the fix we just applied, but formalized

### Step 4: Update Type Hints (Optional, Improves Safety)
- Change `display_build_stats(stats: BuildStats)` to `display_build_stats(stats: DisplayableStats)`
- Type checker will now catch protocol violations

### Step 5: Verify Protocol Compliance (Testing)
- Add test that verifies `BuildStats` implements `DisplayableStats`
- Add test that verifies `MinimalStats` implements `DisplayableStats`

---

## Testing Strategy

```python
# tests/unit/utils/test_stats_protocol.py

from bengal.utils.stats_protocol import DisplayableStats
from bengal.utils.build_stats import BuildStats
from bengal.utils.stats_minimal import MinimalStats

def test_build_stats_implements_displayable():
    """BuildStats must implement DisplayableStats protocol."""
    stats = BuildStats()
    assert isinstance(stats, DisplayableStats)

def test_minimal_stats_implements_displayable():
    """MinimalStats must implement DisplayableStats protocol."""
    stats = MinimalStats(total_pages=10, build_time_ms=100.0, incremental=True)
    assert isinstance(stats, DisplayableStats)

def test_minimal_stats_from_build_result():
    """Factory should create valid DisplayableStats."""
    result = BuildResult(success=True, pages_built=50, build_time_ms=500.0)
    stats = MinimalStats.from_build_result(result)

    assert stats.total_pages == 50
    assert stats.build_time_ms == 500.0
    assert isinstance(stats, DisplayableStats)
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protocol definition incomplete | Low | Medium | Derive from actual `display_build_stats()` accesses |
| Breaking existing code | Low | High | Phased rollout, no changes to `BuildStats` structure |
| Performance overhead | Very Low | Low | Protocols have negligible runtime cost |
| Adoption friction | Low | Low | Old code continues to work |

---

## Success Criteria

1. **No more AttributeErrors**: Subprocess rebuilds display stats without errors
2. **Type-safe contract**: `mypy` catches protocol violations
3. **Single definition**: `DisplayableStats` is the source of truth for display requirements
4. **Testable**: Protocol compliance is verified in tests
5. **Minimal changes**: `BuildStats` structure unchanged, migration is additive

---

## Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Add protocols | 1 hour | None |
| Phase 2: Add MinimalStats | 1 hour | None |
| Phase 3: Replace stub | 30 min | Low |
| Phase 4: Update type hints | 30 min | Low |
| Phase 5: Add tests | 1 hour | None |
| **Total** | **4 hours** | **Low** |

---

## Future Considerations

### Potential Extensions

1. **Richer BuildResult**: If subprocess builds gain timing data, `MinimalStats.from_build_result()` can extract it without changing the protocol

2. **Streaming stats**: Protocol could be extended for real-time stats updates

3. **Stats serialization**: Protocol could add `to_dict()` / `from_dict()` for JSON export

4. **Composition refactor**: If `BuildStats` grows beyond 40 fields, consider Option B (composition) as a follow-up

### Related Work

- **rfc-build-profiler.md**: May add new timing metrics; protocol ensures they integrate cleanly
- **Performance tracking**: Stats protocols could formalize the performance reporting contract

---

## References

- `bengal/utils/build_stats.py`: Current monolithic implementation
- `bengal/server/build_executor.py:67`: BuildResult definition
- `bengal/server/build_trigger.py:374`: Broken local stub (now fixed)
- Python Protocols: [PEP 544](https://peps.python.org/pep-0544/)
