# RFC: Remaining Coupling Fixes

**Status**: Draft  
**Created**: 2026-01-14  
**Updated**: 2026-02-14  
**Author**: AI Assistant  
**Depends On**: rfc-module-coupling-reduction.md (Phase 1-2 status unverified — re-run `check_cycles.py` and `check_dependencies.py` before implementing)

## Summary

Following the initial module coupling reduction (utils split, protocol extraction), automated analysis identified **8 circular imports** and **83 layer violations** requiring attention. This RFC proposes targeted fixes to complete the decoupling effort.

## Problem Statement

### Circular Imports Detected

**Real Cycles (8)** — require fixes:

| Cycle | Modules | Severity | Root Cause |
|-------|---------|----------|------------|
| 1 | `logger ↔ rich_console` | Low | Mutual formatting needs |
| 2 | `graph_reporting ↔ knowledge_graph` | Medium | Mixed orchestration/data |
| 3 | `graph_analysis ↔ knowledge_graph` | Medium | Mixed orchestration/data |
| 4 | `graph_reporting → path_analysis → knowledge_graph` | Medium | Transitive 3-node cycle |
| 5 | `live_reload ↔ request_handler` | Medium | Server state sharing |
| 6 | `image ↔ processor` | High | Tightly coupled resources |
| 7 | `directives ↔ html` (patitas renderers) | Medium | Renderer composition |
| 8 | `blocks ↔ html` (patitas renderers) | Medium | Renderer composition |

**TYPE_CHECKING-only Cycles (4)** — safe, no action needed:

| Cycle | Modules | Status |
|-------|---------|--------|
| TC-1 | `knowledge_graph ↔ link_suggestions` | ✅ Safe |
| TC-2 | `knowledge_graph ↔ page_rank` | ✅ Safe |
| TC-3 | `community_detection ↔ knowledge_graph` | ✅ Safe |
| TC-4 | `errors.context ↔ errors.exceptions` | ✅ Safe |

### Layer Violations by Category

```
Layer Architecture (bottom → top):
  1. primitives     - Pure functions, no Bengal imports
  2. protocols      - Interface definitions  
  3. errors         - Error types
  4. core           - Domain models (Page, Site, Section)
  5. infrastructure - cache, assets, discovery, themes, utils
  6. rendering      - Template and content rendering
  7. orchestration  - Build coordination
  8. cli            - Command-line interface
  9. server         - Development server
```

**Violations Summary:**

| From Layer | To Layer | Count | Primary Offenders |
|------------|----------|-------|-------------------|
| errors (3) | utils (5) | 10 | Logger usage in error handling |
| errors (3) | rendering (6) | 1 | `rendering.errors` import |
| errors (3) | orchestration (7) | 1 | `stats.models` import |
| core (4) | utils (5) | 5 | Cache registry, LRU cache |
| core (4) | rendering (6) | 3 | `page.operations` → template_engine, renderer |
| protocols (2) | core (4) | 3 | Type annotations in protocol definitions |
| protocols (2) | rendering (6) | 1 | Engine errors |
| discovery (5) | orchestration (7) | 3 | BuildContext access |
| discovery (5) | cli (8) | 3 | Error display helpers |
| orchestration (7) | cli (8) | 3 | Progress display |
| rendering (6) | orchestration (7) | 4 | BuildContext, stats access |
| postprocess (6) | orchestration (7) | 4 | BuildContext access |
| analysis (6) | orchestration (7) | 1 | Stats access |
| themes (5) | rendering (6) | 1 | Engine access |
| utils (5) | server (9) | 1 | Build executor |
| utils (5) | orchestration (7) | 1 | Stats collector |
| cache (5) | orchestration (7) | 1 | Constants |
| cache (5) | health (7) | 1 | Health report |

## Proposed Solutions

### Phase 1: Quick Wins (Low Risk)

#### 1.1 Move `cli.helpers.error_display` → `errors/display.py`

**Rationale**: Error display is logically part of error handling, not CLI.

**Changes**:
```
bengal/cli/helpers/error_display.py → bengal/errors/display.py
```

**Impact**: Fixes 3 violations in `discovery/`

#### 1.2 Move `cli.progress` → `utils/observability/cli_progress.py`

**Rationale**: Progress reporting is observability, not CLI-specific.

**Changes**:
```
bengal/cli/progress.py → bengal/utils/observability/cli_progress.py
```

**Impact**: Fixes 3 violations in `orchestration/`

#### 1.3 Accept `errors` → `utils.observability.logger`

**Rationale**: Logging is a cross-cutting concern. Error modules need logging.

**Decision**: Document as acceptable exception to layer rules.

**Impact**: 10 "violations" reclassified as acceptable

### Phase 2: Protocol Extraction (Medium Risk)

#### 2.1 Create `protocols/resources.py`

**Problem**: `core.resources.image ↔ core.resources.processor` cycle

**Solution**: Extract shared resource types to protocols.

```python
# bengal/protocols/resources.py
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class ImageResourceProtocol(Protocol):
    """Protocol for image resources."""
    path: Path
    width: int | None
    height: int | None
    
    def get_dimensions(self) -> tuple[int, int] | None: ...

@runtime_checkable  
class ResourceProcessorProtocol(Protocol):
    """Protocol for resource processors."""
    def process(self, resource: ImageResourceProtocol) -> Path: ...
```

**Impact**: Breaks `image ↔ processor` cycle

#### 2.2 Create `protocols/analysis.py`

**Problem**: Multiple analysis modules import `KnowledgeGraph` for type hints

**Solution**: Extract graph protocol for type annotations.

```python
# bengal/protocols/analysis.py
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core import Page

class KnowledgeGraphProtocol(Protocol):
    """Protocol for knowledge graph access."""
    
    @property
    def incoming_refs(self) -> dict[Page, float]: ...
    
    @property  
    def outgoing_refs(self) -> dict[Page, set[Page]]: ...
    
    def get_hubs(self, threshold: int = 10) -> list[Page]: ...
    def get_orphans(self) -> list[Page]: ...
```

**Impact**: Analysis modules can use protocol instead of concrete class

#### 2.3 Create `rendering/parsers/patitas/protocols.py`

**Problem**: `directives ↔ html` and `blocks ↔ html` cycles in patitas renderers

**Solution**: Extract renderer protocols.

```python
# bengal/rendering/parsers/patitas/protocols.py
from typing import Protocol, Any

class HTMLRendererProtocol(Protocol):
    """Protocol for HTML rendering."""
    def render_children(self, node: Any) -> str: ...
    def render_node(self, node: Any) -> str: ...

class DirectiveRendererProtocol(Protocol):
    """Protocol for directive rendering."""
    def render_directive(self, name: str, args: dict) -> str: ...
```

**Impact**: Breaks renderer cycles

**Note**: Patitas renderers are internal to Bengal's markdown parsing. Changes here are self-contained and do not affect external APIs.

#### 2.4 Fix Protocol Layer Violations

**Problem**: Protocol modules import concrete types from higher layers:

```
bengal.protocols.rendering:30 → bengal.core
bengal.protocols.core:33 → bengal.core.page.frontmatter
bengal.protocols.infrastructure:33 → bengal.core.output.types
```

**Solution**: Use `TYPE_CHECKING` guards for all concrete type imports in protocols.

```python
# bengal/protocols/core.py
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bengal.core.page.frontmatter import Frontmatter

class PageProtocol(Protocol):
    """Protocol for page access."""
    @property
    def frontmatter(self) -> "Frontmatter": ...
```

**Impact**: Fixes 3 protocol layer violations; maintains type safety via forward references

### Phase 3: Architectural Decisions (Discussion Needed)

#### 3.1 BuildContext Location

**Current**: `orchestration/build_context.py`  
**Problem**: Imported by `discovery/`, `postprocess/`, `rendering/` (lower layers) — 8+ violations

**Options**:
1. **Keep in orchestration** - Accept violations as necessary coupling
2. **Move to core** - BuildContext is a domain model, not orchestration
3. **Split** - Extract read-only `BuildState` to core, keep mutable `BuildContext` in orchestration

**Recommendation**: Option 3 (Split)

```python
# bengal/core/build_state.py (read-only, immutable view)
@dataclass(frozen=True)
class BuildState:
    parallel: bool
    incremental: bool
    strict_mode: bool
    profile: str | None

# bengal/orchestration/build_context.py (mutable, orchestration)
class BuildContext:
    state: BuildState  # Immutable config
    changed_sources: set[Path]  # Mutable tracking
    ...
```

**Impact**: Lower layers import `BuildState` from core; only orchestration uses mutable `BuildContext`

#### 3.2 Stats Models Location

**Current**: `orchestration/stats/models.py`  
**Problem**: Imported by `errors/reporter.py`, `utils/observability/`

**Options**:
1. **Move to protocols** - Stats are cross-cutting
2. **Keep and accept** - Error reporting needs build stats
3. **Create stats protocol** - `protocols/stats.py`

**Recommendation**: Option 3 (Create protocol)

```python
# bengal/protocols/stats.py
from typing import Protocol

class BuildStatsProtocol(Protocol):
    """Protocol for build statistics access."""
    @property
    def total_pages(self) -> int: ...
    @property
    def errors_count(self) -> int: ...
    @property
    def warnings_count(self) -> int: ...
```

#### 3.3 Rendering Errors Location

**Current**: `rendering/errors.py`  
**Problem**: Imported by `errors/aggregation.py`

**Analysis**: This is actually correct! The `errors` module aggregates errors from all modules, including rendering-specific errors. The layer rule is too strict here.

**Decision**: Reclassify as acceptable (errors module naturally aggregates from higher layers)

#### 3.4 Core → Rendering Violations

**Problem**: Core modules import from rendering layer:

```
bengal.core.page.metadata:381 → bengal.rendering.pipeline
bengal.core.page.operations:31 → bengal.rendering.template_engine
bengal.core.page.operations:67 → bengal.rendering.renderer
```

**Analysis**: `page.operations` contains render-related methods that logically belong in rendering, not core.

**Options**:
1. **Move operations to rendering** - If tightly coupled, move to `rendering/page_operations.py`
2. **Dependency injection** - Pass renderer as parameter to operations
3. **Protocol** - Use `RendererProtocol` in core

**Recommendation**: Option 1 (Move operations)

The `page.operations` module contains rendering logic that should live in the rendering layer. Moving it eliminates 3 violations and improves cohesion.

```python
# BEFORE: bengal/core/page/operations.py imports rendering
# AFTER:  bengal/rendering/page_operations.py (natural home)
```

**Migration**:
1. Move `core/page/operations.py` → `rendering/page_operations.py`
2. Update imports (grep shows ~12 importers)
3. Add re-export in `core/page/__init__.py` for backward compatibility

### Phase 4: Script Updates

#### 4.1 Update `check_dependencies.py`

Add configurable exceptions:

```python
# Acceptable cross-layer imports
ALLOWED_VIOLATIONS = {
    # Logging is cross-cutting
    ("bengal.errors", "bengal.utils.observability.logger"),
    # Error aggregation needs error types from all modules
    ("bengal.errors.aggregation", "bengal.rendering.errors"),
    # CLI naturally imports server for coordination
    ("bengal.cli", "bengal.server"),
}
```

#### 4.2 Add Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-cycles
      name: Check circular imports
      entry: python scripts/check_cycles.py
      language: system
      pass_filenames: false
      
    - id: check-deps
      name: Check dependency layers
      entry: python scripts/check_dependencies.py
      language: system
      pass_filenames: false
```

## Implementation Plan

### Sprint 1: Quick Wins (1-2 days)

| Task | Files | Risk | Violations Fixed |
|------|-------|------|------------------|
| Move error_display to errors/ | 4 | Low | 3 |
| Move cli.progress to observability/ | 3 | Low | 3 |
| Update check_dependencies.py exceptions | 1 | None | 10 (reclassified) |

**Total**: ~16 violations addressed

### Sprint 2: Protocol Extraction (3-5 days)

| Task | Files | Risk | Cycles Fixed | Violations Fixed |
|------|-------|------|--------------|------------------|
| Create protocols/resources.py | 3 | Medium | 1 | — |
| Create protocols/analysis.py | 8 | Medium | 3 | — |
| Create patitas/protocols.py | 4 | Medium | 2 | — |
| Fix protocol TYPE_CHECKING | 3 | Low | — | 3 |

**Total**: 6 cycles fixed, 3 violations fixed

### Sprint 3: Architecture (5-8 days)

| Task | Files | Risk | Violations Fixed |
|------|-------|------|------------------|
| Split BuildContext/BuildState | 15+ | High | 8 |
| Create protocols/stats.py | 5 | Medium | 2 |
| Move page.operations to rendering | 12 | Medium | 3 |
| Add pre-commit hooks | 2 | None | Prevention |

**Total**: 13 violations fixed + future prevention

## Success Metrics

| Metric | Before | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|--------|---------------|---------------|---------------|
| Circular imports (real) | 8 | 8 | 2 | 1* |
| TYPE_CHECKING cycles | 4 | 4 | 4 | 4 |
| Layer violations | 83 | 67 | 64 | 51 |
| Acceptable exceptions | 0 | 16 | 16 | 19 |

*Remaining cycle: `logger ↔ rich_console` (handled via lazy imports or config extraction)

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import breakage | Medium | High | Run full test suite after each change; add re-exports |
| Performance regression | Low | Medium | Lazy imports where needed; benchmark before/after |
| Over-abstraction | Medium | Low | Protocols only where cycles exist |
| BuildContext split complexity | Medium | Medium | Phase incrementally; extensive testing |

## Alternatives Considered

### 1. Aggressive Protocol Extraction

Extract protocols for everything, eliminating all cycles.

**Rejected**: Over-engineering. Some coupling is natural and acceptable.

### 2. Monorepo Split

Split Bengal into separate packages (bengal-core, bengal-cli, etc.).

**Rejected**: Too disruptive. Internal module boundaries sufficient for now.

### 3. Status Quo

Accept current coupling as technical debt.

**Rejected**: Cycles cause real import issues; violations make architecture unclear.

## Open Questions

1. Should `BuildContext` be split or moved entirely to core?
2. Are there other "acceptable" violations we should codify?
3. Should we add cycle/layer checks to CI (blocking) or just as warnings?
4. Is the `page.operations` move too disruptive, or should we use dependency injection instead?

## References

- [rfc-module-coupling-reduction.md](./rfc-module-coupling-reduction.md) - Completed Phase 1-2
- [scripts/check_cycles.py](../scripts/check_cycles.py) - Cycle detection tool
- [scripts/check_dependencies.py](../scripts/check_dependencies.py) - Layer enforcement tool

## Appendix: Verification Commands

```bash
# Verify current state
uv run python scripts/check_cycles.py --format=simple
uv run python scripts/check_dependencies.py --format=simple

# After Phase 1
uv run pytest tests/ -v
uv run python scripts/check_dependencies.py  # Should show 67 violations

# After Phase 2
uv run python scripts/check_cycles.py  # Should show 2 real cycles

# After Phase 3
uv run python scripts/check_cycles.py  # Should show 1 real cycle
uv run python scripts/check_dependencies.py  # Should show ~51 violations
```
