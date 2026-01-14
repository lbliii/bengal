# RFC: Remaining Coupling Fixes

**Status**: Draft  
**Created**: 2026-01-14  
**Author**: AI Assistant  
**Depends On**: rfc-module-coupling-reduction.md (Phase 1-2 completed)

## Summary

Following the initial module coupling reduction (utils split, protocol extraction), automated analysis identified **8 circular imports** and **83 layer violations** requiring attention. This RFC proposes targeted fixes to complete the decoupling effort.

## Problem Statement

### Circular Imports Detected

| Cycle | Modules | Severity | Root Cause |
|-------|---------|----------|------------|
| 1 | `logger ↔ rich_console` | Low | Mutual formatting needs |
| 2 | `graph_reporting ↔ knowledge_graph` | Medium | Mixed orchestration/data |
| 3 | `graph_analysis ↔ knowledge_graph` | Medium | Mixed orchestration/data |
| 4 | `live_reload ↔ request_handler` | Medium | Server state sharing |
| 5 | `image ↔ processor` | High | Tightly coupled resources |
| 6 | `directives ↔ html` (patitas) | Medium | Renderer composition |
| 7 | `blocks ↔ html` (patitas) | Medium | Renderer composition |
| 8 | `path_analysis ↔ knowledge_graph` | Low | TYPE_CHECKING boundary |

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
| protocols (2) | core (4) | 2 | Type annotations |
| protocols (2) | rendering (6) | 1 | Engine errors |
| discovery (5) | orchestration (7) | 3 | BuildContext access |
| discovery (5) | cli (8) | 3 | Error display helpers |
| orchestration (7) | cli (8) | 2 | Progress display |
| analysis (6) | orchestration (7) | 1 | Stats access |
| themes (5) | rendering (6) | 1 | Engine access |
| utils (5) | server (9) | 1 | Build executor |
| postprocess (6) | orchestration (7) | 1 | BuildContext access |

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

**Impact**: Fixes 2 violations in `orchestration/`

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

**Problem**: `directives ↔ html` and `blocks ↔ html` cycles in patitas

**Solution**: Extract renderer protocols.

```python
# bengal/rendering/parsers/patitas/protocols.py
from typing import Protocol

class HTMLRendererProtocol(Protocol):
    """Protocol for HTML rendering."""
    def render_children(self, node: Node) -> str: ...
    def render_node(self, node: Node) -> str: ...

class DirectiveRendererProtocol(Protocol):
    """Protocol for directive rendering."""
    def render_directive(self, name: str, args: dict) -> str: ...
```

**Impact**: Breaks renderer cycles

### Phase 3: Architectural Decisions (Discussion Needed)

#### 3.1 BuildContext Location

**Current**: `orchestration/build_context.py`  
**Problem**: Imported by `discovery/` and `postprocess/` (lower layers)

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

#### 3.2 Stats Models Location

**Current**: `orchestration/stats/models.py`  
**Problem**: Imported by `errors/reporter.py`

**Options**:
1. **Move to protocols** - Stats are cross-cutting
2. **Keep and accept** - Error reporting needs build stats
3. **Create stats protocol** - `protocols/stats.py`

**Recommendation**: Option 3 (Create protocol)

#### 3.3 Rendering Errors Location

**Current**: `rendering/errors.py`  
**Problem**: Imported by `errors/aggregation.py`

**Analysis**: This is actually correct! The `errors` module aggregates errors from all modules, including rendering-specific errors. The layer rule is too strict here.

**Decision**: Reclassify as acceptable (errors module naturally aggregates from higher layers)

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
    # Protocols need type references
    ("bengal.protocols", "bengal.core"),
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
| Move cli.progress to observability/ | 3 | Low | 2 |
| Update check_dependencies.py exceptions | 1 | None | 10 (reclassified) |

**Total**: ~15 violations addressed

### Sprint 2: Protocol Extraction (3-5 days)

| Task | Files | Risk | Cycles Fixed |
|------|-------|------|--------------|
| Create protocols/resources.py | 3 | Medium | 1 |
| Create protocols/analysis.py | 8 | Medium | 2 |
| Create patitas/protocols.py | 4 | Medium | 2 |

**Total**: 5 cycles fixed

### Sprint 3: Architecture (5-7 days)

| Task | Files | Risk | Violations Fixed |
|------|-------|------|------------------|
| Split BuildContext/BuildState | 15+ | High | 4 |
| Create protocols/stats.py | 5 | Medium | 1 |
| Add pre-commit hooks | 2 | None | Prevention |

**Total**: 5 violations fixed + future prevention

## Success Metrics

| Metric | Before | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|--------|---------------|---------------|---------------|
| Circular imports | 8 | 8 | 3 | 1* |
| Layer violations | 83 | 68 | 60 | 50 |
| Acceptable exceptions | 0 | 15 | 15 | 20 |

*Remaining cycle: `logger ↔ rich_console` (handled via lazy imports)

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import breakage | Medium | High | Run full test suite after each change |
| Performance regression | Low | Medium | Lazy imports where needed |
| Over-abstraction | Medium | Low | Protocols only where cycles exist |

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
3. Should we add cycle/layer checks to CI?

## References

- [rfc-module-coupling-reduction.md](./rfc-module-coupling-reduction.md) - Completed Phase 1-2
- [scripts/check_cycles.py](../scripts/check_cycles.py) - Cycle detection tool
- [scripts/check_dependencies.py](../scripts/check_dependencies.py) - Layer enforcement tool
