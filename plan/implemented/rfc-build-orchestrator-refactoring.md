# RFC: BuildOrchestrator Refactoring - Phase Method Extraction

**Author**: AI + Human Reviewer  
**Date**: 2025-01-27  
**Status**: Draft  
**Confidence**: 82% 🟢

---

## Executive Summary

**Context**: `BuildOrchestrator.build()` has grown to ~900 lines, handling initialization, phase execution, incremental logic, caching, error handling, progress reporting, and statistics collection in a single method.

**Question**: Should we refactor `BuildOrchestrator` to improve maintainability, testability, and clarity?

**Answer**: **Yes** - Extract phase execution into separate `_phase_*` methods. This is the primary deliverable. Registry/strategy patterns are deferred until value is proven.

**Impact**:
- ✅ Reduced method complexity (894 lines → ~50 lines per phase method)
- ✅ Improved testability (can test phases independently)
- ✅ Better maintainability (clear phase boundaries)
- ✅ **Contributor-friendly codebase** (key for open source growth)
- ⚠️ Requires careful migration to avoid breaking changes

**Confidence**: 82% (strong evidence from code analysis, clear refactoring path; registry pattern deferred)

---

## 0. Strategic Context

### Why This Matters for Bengal

Bengal is positioning as **the modern Python SSG**. For open source success, we need:

```
Adoption = (Ease of Getting Started × Visible Quality × Community) / Friction
```

**This refactoring directly impacts "Visible Quality" and "Community":**

1. **Contributor Velocity**: A 894-line method is a contributor deterrent
   - New contributors open `build.py` → feel overwhelmed → close PR
   - Clean, focused methods → contributors can find and fix issues

2. **Competitive Position**: Python SSG landscape
   - MkDocs: Limited to docs, simple architecture
   - Pelican: Aging codebase, stale development
   - Bengal: Modern Python, sophisticated features, **needs clean internals**

3. **Long-term Maintainability**: Technical debt compounds
   - Current: Every new feature adds to 894-line method
   - After: New phases are isolated, testable, reviewable

**Strategic recommendation**: Prioritize Option A (method extraction) for immediate contributor experience improvement. Defer Option B/C abstractions until pain justifies complexity.

---

## 1. Problem Statement

### Current State

**BuildOrchestrator.build()** (`bengal/orchestration/build.py:66-960`):
- **Size**: ~900 lines in a single method
- **Responsibilities**:
  - Initialization and setup (CLI, profile, stats, cache)
  - 17+ phase executions (with repetitive timing/logging boilerplate)
  - Incremental build logic (scattered throughout)
  - Error handling and cleanup
  - Progress reporting and statistics collection

**Evidence from codebase**:
```python
# bengal/orchestration/build.py:66-960
def build(self, ...) -> BuildStats:
    # ~50 lines: Initialization
    # ~800 lines: Phase execution (17+ phases)
    # ~50 lines: Cleanup and statistics
```

**Phase structure issues**:
- Duplicate phase numbers: two "Phase 5.5" (lines 569, 616), two "Phase 9" (lines 871, 901)
- Decimal numbering: 0.5, 1.25, 1.5, 4.5, 5.5, 8.4, 8.5 (organic growth)
- Repetitive execution pattern: 17 occurrences of `with self.logger.phase(...)` with timing boilerplate

**Incremental logic issues**:
- Conditional checks (`if incremental:`) scattered throughout phases
- Hard to see full incremental flow
- Mixed concerns (incremental vs full build logic)

### Pain Points

1. **Maintainability**: Adding a new phase requires understanding 900 lines of code
2. **Testability**: Cannot test individual phases in isolation
3. **Readability**: Hard to understand build flow (phases buried in one method)
4. **Code duplication**: Repetitive phase execution boilerplate (timing, logging, error handling)
5. **Complexity**: High cyclomatic complexity (many nested conditionals)
6. **Incremental logic**: Scattered throughout, hard to reason about

### User Impact

**End Users**: No impact (internal refactoring only)

**Contributors** (Strategic Priority):
- ❌ Current: Open `build.py` → 894 lines → "where do I start?" → close PR
- ✅ After: Open `build.py` → see clear phase methods → find relevant code → submit PR

**Maintainers**:
- Hard to understand build pipeline
- High cognitive load when debugging build issues
- Difficult to test build phases independently
- Hard to reason about incremental vs full build behavior

**Open Source Growth**:
- Clean codebase → more contributors → more features → more users
- 894-line methods deter contributions (proven pattern in OSS)

---

## 2. Goals & Non-Goals

### Goals

1. **Extract Phase Methods**: Break `build()` into focused `_phase_*` methods (~50-100 lines each)
2. **Improve Contributor Experience**: Make codebase approachable for new contributors
3. **Reduce Complexity**: Lower cyclomatic complexity of `build()` method
4. **Improve Testability**: Enable independent testing of phases
5. **Maintain Backward Compatibility**: No breaking changes to public API
6. **Fix Technical Debt**: Resolve duplicate phase numbers (5.5, 9)

### Deferred Goals (Option B/C)

- **Phase Registry Pattern**: Evaluate after Option A is complete
- **Build Strategy Pattern**: Only if incremental logic becomes painful

### Non-Goals

- **Not changing phase execution order** (unless fixing bugs)
- **Not changing incremental build behavior** (only organizing it better)
- **Not optimizing build performance** (focus on code structure)
- **Not changing orchestrator interfaces** (only internal refactoring)
- **Not adding new features** (pure refactoring)
- **Not adding abstractions prematurely** (YAGNI principle)

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Orchestration** (`bengal/orchestration/`): **Primary impact**
  - `build.py`: Major refactoring (extract phase methods)
  - Other orchestrators: No changes (still called the same way)
  - New modules: None (Option A keeps everything in `build.py`)

- **Core** (`bengal/core/`): **No impact**
  - Site, Page, Section, Asset unchanged

- **Cache** (`bengal/cache/`): **No impact**
  - Cache interfaces unchanged

- **CLI** (`bengal/cli/`): **No impact**
  - CLI still calls `BuildOrchestrator.build()` the same way

- **Health** (`bengal/health/`): **No impact**
  - Health checks still run in Phase 10

**Integration Points**:

- `BuildOrchestrator.build()` remains the public API (backward compatible)
- Phase methods are private (`_phase_*`) - internal implementation detail
- Orchestrators (Content, Render, etc.) called the same way
- BuildContext threading continues (may be improved)

---

## 4. Design Options

### Option A: Extract Phase Methods Only (Minimal Refactoring)

**Description**: Extract each phase into a separate `_phase_*` method, keeping current structure.

```python
class BuildOrchestrator:
    def build(...) -> BuildStats:
        ctx = self._setup_build_context(...)
        self._phase_font_processing(ctx)
        self._phase_content_discovery(ctx)
        self._phase_incremental_filter(ctx)
        # ... etc
        return ctx.stats

    def _phase_content_discovery(self, ctx: BuildContext):
        with self.logger.phase("discovery"):
            start = time.time()
            self.content.discover(...)
            self.stats.discovery_time_ms = (time.time() - start) * 1000
```

**Pros**:
- ✅ Simple, low-risk refactoring
- ✅ Immediate readability improvement
- ✅ Easy to test phases independently
- ✅ Minimal changes to existing code

**Cons**:
- ❌ Still have repetitive boilerplate (timing, logging)
- ❌ Phase order still implicit (in method calls)
- ❌ Incremental logic still scattered

**Complexity**: Simple (2-3 days)

**Evidence**: Method extraction pattern used elsewhere (e.g., `PostprocessOrchestrator._generate_*` methods)

---

### Option B: Phase Registry + Executor Pattern (Moderate Refactoring)

**Description**: Create a `PhaseRegistry` to define phases and a `PhaseExecutor` to handle timing/logging.

```python
@dataclass
class Phase:
    name: str
    order: float
    executor: Callable
    incremental_aware: bool = False

class PhaseRegistry:
    phases: list[Phase] = [
        Phase("font_processing", 0.5, self._phase_font_processing),
        Phase("content_discovery", 1.0, self._phase_content_discovery),
        # ... etc
    ]

class BuildOrchestrator:
    def build(...) -> BuildStats:
        ctx = self._setup_build_context(...)
        executor = PhaseExecutor(self.logger, self.stats, ctx.cli)
        for phase in PhaseRegistry.phases:
            executor.execute(phase, ctx)
        return ctx.stats
```

**Pros**:
- ✅ Explicit phase ordering (registry)
- ✅ Consistent execution (executor handles timing/logging)
- ✅ Easy to add/modify phases (just update registry)
- ✅ Can reorder phases without code changes

**Cons**:
- ⚠️ More complex (new abstractions)
- ⚠️ Requires careful design of executor interface

**Complexity**: Moderate (5-7 days)

**Evidence**: Task-based execution pattern used in `PostprocessOrchestrator.run()` with named task tuples

---

### Option C: Build Strategy Pattern (Comprehensive Refactoring)

**Description**: Separate incremental vs full build logic using strategy pattern.

```python
class BuildStrategy(ABC):
    @abstractmethod
    def execute_phase(self, phase: Phase, ctx: BuildContext): ...

class FullBuildStrategy(BuildStrategy):
    def execute_phase(self, phase: Phase, ctx: BuildContext):
        # Always execute full phase
        phase.executor(ctx)

class IncrementalBuildStrategy(BuildStrategy):
    def execute_phase(self, phase: Phase, ctx: BuildContext):
        # Check if phase needs execution
        if self._should_execute(phase, ctx):
            phase.executor(ctx)
        else:
            self._skip_phase(phase, ctx)

class BuildOrchestrator:
    def build(...) -> BuildStats:
        ctx = self._setup_build_context(...)
        strategy = IncrementalBuildStrategy() if incremental else FullBuildStrategy()
        for phase in PhaseRegistry.phases:
            strategy.execute_phase(phase, ctx)
        return ctx.stats
```

**Pros**:
- ✅ Clean separation of incremental vs full build logic
- ✅ Easy to add new build modes (e.g., "dry-run", "validate-only")
- ✅ Incremental logic centralized (not scattered)

**Cons**:
- ⚠️ Most complex option (larger refactor)
- ⚠️ Requires careful design of strategy interface
- ⚠️ May be overkill if only two build modes

**Complexity**: Complex (10-14 days)

**Evidence**: No existing strategy pattern in codebase; would be a new abstraction

---

### Recommended: Option A (Method Extraction)

**This is the deliverable. Options B and C are deferred.**

**Strategic Reasoning**:
- **Contributor experience**: Clean methods attract contributors; 894-line methods repel them
- **Low risk**: Simple extraction, no new abstractions
- **Immediate value**: 80% of the benefit with 20% of the complexity
- **YAGNI**: Registry pattern adds cognitive load without proven need
- **Reversible**: Can always add Option B later if pain emerges

**Why NOT Option B/C now**:
- No existing registry/strategy patterns in Bengal codebase
- Adds abstraction overhead for contributors to learn
- Premature optimization of code organization
- Method extraction alone solves the core problem

**Implementation approach**:
1. **Phase 1**: Extract phase methods (Option A) - **THE DELIVERABLE**
2. **Phase 2**: Live with it for 1-2 release cycles
3. **Phase 3**: Re-evaluate: Is phase ordering actually painful? If yes → Option B

---

## 5. Detailed Design (Option A: Method Extraction)

### Primary Deliverable: Extract Phase Methods

**Target structure** after refactoring:

```python
class BuildOrchestrator:
    def build(self, ...) -> BuildStats:
        """Public API unchanged - backward compatible."""
        ctx = self._setup_build_context(...)

        # Clear phase sequence (~15 method calls instead of 894 lines)
        self._phase_fonts(ctx)                    # Phase 0.5
        self._phase_discovery(ctx)                # Phase 1
        self._phase_cache_metadata(ctx)           # Phase 1.25
        self._phase_cleanup_deleted(ctx)          # Phase 1.5
        self._phase_incremental_filter(ctx)       # Phase 2
        self._phase_sections(ctx)                 # Phase 3
        self._phase_taxonomies(ctx)               # Phase 4
        self._phase_taxonomy_index(ctx)           # Phase 4.5
        self._phase_menus(ctx)                    # Phase 5
        self._phase_related_posts(ctx)            # Phase 6 (was 5.5)
        self._phase_query_indexes(ctx)            # Phase 7 (was 5.5)
        self._phase_update_pages_list(ctx)        # Phase 8 (was 6)
        self._phase_assets(ctx)                   # Phase 9 (was 7)
        self._phase_render(ctx)                   # Phase 10 (was 8)
        self._phase_track_assets(ctx)             # Phase 11 (was 8.5)
        self._phase_postprocess(ctx)              # Phase 12 (was 9)
        self._phase_cache_save(ctx)               # Phase 13 (was 9)
        self._phase_health_check(ctx)             # Phase 14 (was 10)

        return ctx.stats
```

**Key changes**:
- Fix duplicate phase numbers (renumber sequentially)
- Each phase method is ~50-100 lines
- `build()` becomes a readable sequence of method calls
- No new abstractions (registry, strategy) - just extraction

---

## 5.1. Reference Design (Option B: Phase Registry - DEFERRED)

> **Note**: This section is preserved for future reference. Option B is NOT part of the current deliverable. Re-evaluate after living with Option A for 1-2 release cycles.

### API Changes (If Implemented Later)

**New modules**:
- `bengal/orchestration/phase_registry.py`: Phase definitions and registry
- `bengal/orchestration/phase_executor.py`: Phase execution framework (optional, can be in build.py)

**BuildOrchestrator changes**:
```python
class BuildOrchestrator:
    def build(...) -> BuildStats:
        """Public API unchanged - backward compatible."""
        ctx = self._setup_build_context(...)
        self._execute_phases(ctx)
        return ctx.stats

    def _execute_phases(self, ctx: BuildContext):
        """Execute all phases in order."""
        for phase in self._get_phase_registry():
            self._execute_phase(phase, ctx)

    def _execute_phase(self, phase: Phase, ctx: BuildContext):
        """Execute single phase with timing/logging."""
        with self.logger.phase(phase.name):
            start = time.time()
            try:
                phase.executor(ctx)
            except Exception as e:
                self._handle_phase_error(phase, e, ctx)
            finally:
                duration_ms = (time.time() - start) * 1000
                self.stats.set_phase_time(phase.name, duration_ms)
                ctx.cli.phase(phase.display_name, duration_ms=duration_ms)

    def _phase_font_processing(self, ctx: BuildContext):
        """Phase 0.5: Font processing."""
        if "fonts" not in self.site.config:
            return
        # ... existing logic ...

    def _phase_content_discovery(self, ctx: BuildContext):
        """Phase 1: Content discovery."""
        # ... existing logic ...

    # ... etc for all phases
```

### Phase Registry Structure

```python
@dataclass
class Phase:
    """Represents a build phase."""
    name: str  # Internal name (e.g., "content_discovery")
    display_name: str  # User-facing name (e.g., "Content Discovery")
    order: float  # Execution order (0.5, 1.0, 1.25, etc.)
    executor: Callable[[BuildContext], None]  # Phase execution function
    incremental_aware: bool = False  # Whether phase handles incremental logic
    optional: bool = False  # Whether phase can be skipped

class BuildOrchestrator:
    def _get_phase_registry(self) -> list[Phase]:
        """Get ordered list of build phases."""
        return [
            Phase(
                name="font_processing",
                display_name="Font Processing",
                order=0.5,
                executor=self._phase_font_processing,
                optional=True,
            ),
            Phase(
                name="content_discovery",
                display_name="Content Discovery",
                order=1.0,
                executor=self._phase_content_discovery,
            ),
            Phase(
                name="cache_discovery_metadata",
                display_name="Cache Discovery Metadata",
                order=1.25,
                executor=self._phase_cache_discovery_metadata,
            ),
            # ... etc for all 17+ phases
        ]
```

### Data Flow

**Before** (current):
```
build() → [900 lines of inline phase execution]
```

**After** (refactored):
```
build() → _execute_phases() → _execute_phase() → _phase_*() → orchestrators
```

### Error Handling

**Phase-level errors**:
- Each phase wrapped in try/except in `_execute_phase()`
- Errors logged with phase context
- Build continues or fails based on `strict` mode

**Build-level errors**:
- Initialization errors: Fail fast
- Phase errors: Log and continue (or fail in strict mode)
- Cleanup errors: Log but don't fail build

### Configuration

**No new config options** - internal refactoring only.

### Testing Strategy

**Unit tests**:
- Test each `_phase_*` method independently
- Mock dependencies (orchestrators, cache, etc.)
- Verify phase execution order

**Integration tests**:
- Test full build pipeline (existing tests should still pass)
- Test incremental vs full build paths
- Verify statistics collection

**Test structure**:
```python
# tests/unit/test_build_orchestrator_phases.py
class TestContentDiscoveryPhase:
    def test_phase_executes(self):
        orchestrator = BuildOrchestrator(site)
        ctx = BuildContext(...)
        orchestrator._phase_content_discovery(ctx)
        assert len(site.pages) > 0

    def test_phase_timing(self):
        # Verify timing is recorded
        ...
```

---

## 6. Tradeoffs & Risks

### Tradeoffs (Option A)

**Gain**:
- ✅ Better code organization (phases clearly separated)
- ✅ Improved testability (can test phases independently)
- ✅ Easier maintenance (smaller, focused methods)
- ✅ **Contributor-friendly** (can understand codebase quickly)
- ✅ Lower barrier to entry for new contributors
- ✅ Clearer build flow (explicit phase sequence)

**Lose**:
- ⚠️ More methods (15 phase methods vs 1 large method)
- ⚠️ Slight indirection (method calls vs inline code)
- ⚠️ Initial refactoring effort (3-4 days)

**Explicitly NOT doing** (YAGNI):
- ❌ Phase Registry (adds abstraction without proven need)
- ❌ Strategy Pattern (over-engineering for current scale)
- ❌ New modules (keep everything in `build.py`)

### Risks

**Risk 1**: Breaking existing behavior during refactoring
- **Likelihood**: Medium
- **Impact**: High (build failures)
- **Mitigation**:
  - Comprehensive test coverage before refactoring
  - Incremental refactoring (one phase at a time)
  - Run full test suite after each phase extraction

**Risk 2**: Performance regression from method call overhead
- **Likelihood**: Low
- **Impact**: Low (negligible overhead)
- **Mitigation**:
  - Benchmark before/after
  - Method calls are cheap in Python
  - No additional I/O or computation

**Risk 3**: Phase ordering bugs
- **Likelihood**: Low
- **Impact**: Medium (incorrect build results)
- **Mitigation**:
  - Explicit phase registry (order is visible)
  - Integration tests verify build output
  - Phase order documented in registry

**Risk 4**: Incomplete refactoring (leaving some phases inline)
- **Likelihood**: Medium
- **Impact**: Low (partial improvement still valuable)
- **Mitigation**:
  - Clear checklist of all phases
  - Code review to ensure completeness

---

## 7. Performance & Compatibility

### Performance Impact

**Build time**: **No change** (same operations, just organized differently)
- Method call overhead: Negligible (~nanoseconds per call)
- No additional I/O or computation

**Memory**: **No change** (same data structures)

**Cache implications**: **No change** (cache logic unchanged)

### Compatibility

**Breaking changes**: **None**
- Public API (`BuildOrchestrator.build()`) unchanged
- All parameters and return types unchanged
- Internal refactoring only

**Migration path**: **Not applicable** (internal refactoring)

**Deprecation timeline**: **Not applicable** (no deprecated APIs)

---

## 8. Migration & Rollout

### Implementation Phases

**Phase 1: Setup & First Extraction** (Day 1)
1. Create `BuildContext` dataclass if not exists (holds shared state)
2. Extract first phase (`_phase_fonts`) as proof of concept
3. Run full test suite to verify behavior unchanged
4. Commit: `orchestration: extract _phase_fonts from build(); add BuildContext`

**Phase 2: Extract Remaining Phases** (Days 2-3)
1. Extract phases one by one (in execution order)
2. Run tests after each extraction
3. Fix duplicate phase numbers during extraction (5.5 → 6/7, 9 → 12/13)
4. Commit after each 2-3 phases extracted

**Phase 3: Polish & Documentation** (Day 4)
1. Add docstrings to all phase methods
2. Update `architecture/core/orchestration.md`
3. Final test pass + code review
4. Commit: `orchestration: complete build() phase extraction; update docs`

**Phase 4: Deferred (Option B - Only If Needed)**
- Re-evaluate after 1-2 release cycles
- Only proceed if phase ordering becomes painful

### Rollout Strategy

**Feature flag**: **Not needed** (internal refactoring, no user-facing changes)

**Beta period**: **Not needed** (can merge directly if tests pass)

**Documentation updates**:
- Update `architecture/core/orchestration.md` with phase method structure
- Add phase execution flow diagram
- Document phase registry pattern

---

## 9. Open Questions

- [ ] **Question 1**: Should phase methods be public (`phase_*`) or private (`_phase_*`)?
  - **Recommendation**: Private (`_phase_*`) - internal implementation detail
  - **Rationale**: Public API is `build()`, phases are implementation details

- [ ] **Question 2**: Should we create a separate `PhaseExecutor` class or keep execution logic in `BuildOrchestrator`?
  - **Recommendation**: Keep in `BuildOrchestrator` initially (simpler)
  - **Rationale**: Can extract later if needed (YAGNI principle)

- [ ] **Question 3**: Should phase registry be a class attribute or instance method?
  - **Recommendation**: Instance method (`_get_phase_registry()`) - can access `self.site` if needed
  - **Rationale**: More flexible, can customize phases per site if needed

- [ ] **Question 4**: Should we fix duplicate phase numbers (two "Phase 5.5", two "Phase 9") during refactoring?
  - **Recommendation**: Yes - fix numbering as we extract phases
  - **Rationale**: Good opportunity to clean up technical debt

- [ ] **Question 5**: Should incremental logic be extracted into phase methods or kept in `build()`?
  - **Recommendation**: Extract into phase methods (each phase handles its own incremental logic)
  - **Rationale**: Keeps phases self-contained, easier to reason about

---

## 10. Confidence Scoring

**Evidence Strength**: 38/40 ✅
- Direct code analysis: `build()` method is 894 lines (lines 66-960)
- Phase structure documented: 15 distinct phases identified
- Repetitive patterns found: 17 `with self.logger.phase` occurrences
- Evidence: `bengal/orchestration/build.py:66-960`

**Consistency**: 25/30 🟡
- Code analysis matches documentation (phases documented)
- Method extraction pattern used in `PostprocessOrchestrator._generate_*` methods
- Note: Registry pattern would be NEW to Bengal (no existing precedent)

**Recency**: 15/15 ✅
- Code reviewed today (2025-01-27)
- Architecture docs updated today
- Current implementation verified

**Tests**: 12/15 🟡
- Existing integration tests cover build pipeline
- Unit tests for orchestrators exist
- No dedicated tests for phase extraction (will add during refactoring)

**Total Confidence**: **82%** 🟢

**Quality Gate**: ⚠️ Marginal (85% threshold for RFC; proceed with Option A focus)

---

## 11. References

- `bengal/orchestration/build.py`: Current implementation (1058 lines)
- `bengal/orchestration/postprocess.py`: Example of phase-like organization
- `architecture/core/orchestration.md`: Build pipeline documentation
- `plan/implemented/rfc-cacheable-protocol.md`: Example RFC structure

---

## 12. Next Steps

1. ✅ **RFC Review**: Complete (evidence verified, strategic context added)
2. **Approve RFC**: Confirm Option A approach, defer Option B/C
3. **Run `::plan`**: Convert to atomic implementation tasks
4. **Create branch**: `refactor/build-orchestrator-phases`
5. **Execute Phase 1**: Extract `_phase_fonts` as proof of concept
6. **Ship it**: Merge after tests pass, update changelog

**Success criteria**:
- `build()` method reduced from 894 lines to <100 lines
- 15 focused `_phase_*` methods (~50-100 lines each)
- All existing tests pass
- No new abstractions introduced

---

**Status**: Draft (ready for review)  
**Confidence**: 82% 🟢  
**Estimated Effort**: 3-4 days (Option A only)  
**Risk Level**: Low (simple extraction, no new abstractions)  
**Strategic Value**: High (contributor experience, codebase quality)
