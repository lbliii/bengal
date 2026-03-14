# RFC: Split BuildOrchestrator.build() into Phase Group Methods

## Status: Draft (revised after code deep-dive)
## Created: 2026-03-14
## Revised: 2026-03-14
## Origin: Bengal DRY Refactor Plan Phase 5c (cancelled as out-of-scope)

---

## Summary

**Problem**: `BuildOrchestrator.build()` is a 708-line method (lines 143–851) that sequences ~28 distinct steps in a single control flow, using 40+ local variables as implicit shared state. Beyond the sheer size, a code deep-dive revealed two structural defects: (1) `phase_render` creates a *second* `BuildContext` and manually cherry-picks fields from the first, and (2) ~150 lines of finalization logic live inline in `build()` instead of in `finalization.py` where they belong.

**Solution**: Fix the dual-context bug, extract inline code into submodule functions, then introduce thin phase group methods so `build()` becomes a coordinator. No new state type is needed — `BuildContext` already holds 12 of the 18 fields the original `BuildRunState` proposal would have introduced.

**Priority**: Medium (code health; no user-facing change, but fixes a latent fragility)

**Scope**: ~400–600 LOC changed across 7+ files in `bengal/orchestration/build/`

---

## Motivation

### Why It Was Cancelled

During the Bengal DRY Refactor Plan (Phase 5c), splitting `build()` into phase groups was cancelled because:

1. **Shared state sprawl**: 40+ local variables are read/written across the method. The original estimate of 30+ was too low — verified count includes `build_input`, `options`, 12 options-derived flags, `cli`, `progress_manager`, `reporter`, `build_start`, `collector`, `cache`, `generated_page_cache`, `auto_reason`, `early_ctx`, `output_collector`, `config_result`, `config_changed`, `filter_result`, `pages_to_build`, `assets_to_process`, `affected_tags`, `changed_page_paths`, `affected_sections`, `ctx`, `site_snapshot`, plus 8+ timing variables.
2. **No single state container**: `BuildContext` exists but is populated incrementally and then *duplicated* — `phase_render` creates a second `BuildContext` and cherry-picks fields from the first (see Deep Dive Finding #1).
3. **Early exits**: Filter phase returns `None` (early exit at line 438); dry-run exits after snapshot (line 594). Two exit paths in a 708-line method.
4. **Risk vs. benefit**: The refactor touches the critical path; a design-first RFC reduces risk.

### Why Do It Now

- **Latent bug**: `phase_render` creates a second `BuildContext` and manually transfers fields from `early_ctx` (`_page_contents`, `changed_page_paths`, `snapshot`). Every new field added to `BuildContext` that matters across phase boundaries must be manually transferred — a fragile pattern that has already caused issues.
- **Inline code debt**: ~150 lines of finalization logic (generated page cache update, parallel cache save, reload hint computation) live inline in `build()` instead of in `finalization.py`. This code is untestable in isolation.
- **Maintainability**: A 708-line method with 40+ locals is hard to reason about and modify.
- **Testability**: Phase groups could be unit-tested in isolation. Currently only 4 unit tests cover `build()`, all using heavy mocking with no integration test validating the full state flow.
- **Future work**: Phase-level observability, parallel phase groups, or phase-level dry-run become feasible.
- **Consistency**: Other orchestrators (asset, taxonomy, postprocess) already use `ParallelProcessor` and clear phase boundaries.

---

## Current Architecture

### Phase Layout (verified against `build/__init__.py` lines 143–851)

| Group | Phases | Module | Purpose |
|-------|--------|--------|---------|
| Init | 1, 1.5, 2, 3, 4 | `initialization.py` | Fonts, template validation, discovery, cache metadata, config check |
| Filter | 5 | `provenance_filter.py` | Incremental filter → `FilterResult | None` (early exit #1) |
| Content | 6–12.5 | `content.py` + **inline** | Sections, taxonomies, menus, indexes, variant filter, URL collision |
| Parsing + Snapshot | — | `parsing.py` + **73 lines inline** | Parse markdown, create snapshot, NavTreeCache, global contexts, services |
| Dry-run exit | — | **inline** | Early exit #2 (line 594) |
| Assets | 13 | `rendering.py` | Process assets |
| Rendering | 14–16 | `rendering.py` | Render pages, update site pages, track assets |
| Finalization | 17–21 | `finalization.py` + **151 lines inline** | Postprocess, cache save, stats, health, finalize |

**Key observation**: Phases marked "inline" are code that lives directly in `build()` instead of in submodule functions. This is the primary extraction opportunity — 224 lines of inline logic that belongs in submodules.

### Shared State (Evidence)

From `bengal/orchestration/build/__init__.py` lines 162–450:

```python
# Options-derived (read-only after extraction) — 14 locals
force_sequential, incremental, verbose, quiet, profile, memory_optimized, strict,
full_output, profile_templates, changed_sources, nav_changed_sources, structural_changed,
explain, dry_run

# Callbacks — 2 locals + 2 closures
on_phase_start, on_phase_complete, notify_phase_start, notify_phase_complete

# Infrastructure — 6 locals
cli, progress_manager, reporter, build_start, collector, use_live_progress

# Mutable across phases — 10+ locals
early_ctx: BuildContext          # Created line 376, mutated through build
cache: BuildCache                # From incremental.initialize() (line 330)
output_collector                 # BuildOutputCollector (line 383)
pages_to_build: list[Page]       # From filter_result (line 441), updated in phase 12
assets_to_process: list[Asset]   # From filter_result (line 442)
incremental: bool                # Mutated in phase 4 (config_result, line 418)
generated_page_cache             # GeneratedPageCache (line 336)
ctx                              # NEW BuildContext from phase_render (line 660)
config_changed                   # From config_result (line 419)
affected_tags, affected_sections, changed_page_paths  # From filter_result
```

Instance state mutated: `self.stats`, `self.options`, `self.current_input`, `self._build_id`, `self._last_build_options`, `self._provenance_filter`, `self.site.build_state`, `self.site.build_time`, `self.site.diagnostics`.

### Existing State Types (3 types already in play)

| Type | Location | Purpose | Fields |
|------|----------|---------|--------|
| `BuildContext` | `build_context.py` | Shared context for rendering + validators | 35+ fields, 757 lines |
| `BuildState` | `build_state.py` | Per-build mutable state on Site | 20+ fields (caches, locks, render context) |
| `BuildOptions` | `build/options.py` | Input configuration | Read-only after build start |

**Critical**: `BuildContext` already has `incremental`, `pages_to_build`, `assets_to_process`, `affected_tags`, `affected_sections`, `changed_page_paths`, `config_changed`, `output_collector`, `snapshot`, `build_start`, `cache`, `build_id` — 12 of the 18 fields the original `BuildRunState` proposal would introduce.

---

## Deep Dive Findings

### Finding #1: Dual-BuildContext Bug (rendering.py:477–538)

`phase_render` creates a **new** `BuildContext` and manually transfers fields from `early_ctx`:

```python
# rendering.py lines 516-538
ctx = BuildContext(site=..., pages=..., stats=..., profile=...)
# Manual field transfers — fragile, every new field must be added here
if early_context and early_context.has_cached_content:
    ctx._page_contents = early_context._page_contents
if early_context is not None:
    ctx.changed_page_paths = set(getattr(early_context, "changed_page_paths", set()))
if early_context and hasattr(early_context, "snapshot"):
    ctx.snapshot = early_context.snapshot
```

This pattern exists in two code paths (memory_optimized and normal), duplicating the field transfer logic. Fields like `query_service` and `data_service` (set on `early_ctx` at lines 581-588) are *not* transferred, which may cause silent failures if rendering code tries to access them.

**Fix**: Pass `early_ctx` through directly instead of creating a second `BuildContext`. Populate missing fields (`pages`, `profile`, `progress_manager`, etc.) on `early_ctx` before calling `phase_render`.

### Finding #2: 151 Lines of Inline Finalization (build/__init__.py:694–845)

These blocks live directly in `build()` but should be in `finalization.py`:

| Lines | Content | LOC |
|-------|---------|-----|
| 700–739 | Generated page cache update | 39 |
| 744–767 | Parallel cache save (ThreadPoolExecutor) | 23 |
| 776–810 | Reload hint computation + output logging | 34 |
| 819–846 | Health phase group + provenance save | 27 |

These are already self-contained blocks with clear inputs and outputs — extraction requires no new types.

### Finding #3: 73 Lines of Inline Snapshot Logic (build/__init__.py:535–589)

The snapshot creation block (lines 535–589) handles:
- `create_site_snapshot()` + timing
- `NavTreeCache.set_precomputed()`
- `_get_global_contexts()` (pre-warm for parallel rendering)
- `configure_for_site()` (directive cache)
- `SnapshotCache.save()`
- `QueryService.from_snapshot()` + `DataService.from_root()`

This is a natural candidate for a `snapshot.py` submodule function.

### Finding #4: Actual Phase Boundaries Don't Match Docstring

The docstring claims 21 phases. The actual count is ~28 distinct steps including Phase 12.25 (variant filter), Phase 12.5 (URL collision), parsing, snapshot, dry-run check, provenance recording (line 675), generated page cache update, reload hint, Phase 19.5 (error session), and provenance save. The filter phase (Phase 5) is a critical boundary — it produces the work items — and should not be lumped with initialization.

---

## Proposed Design

### Option A: BuildRunState Dataclass (Original Proposal)

Introduce a `BuildRunState` dataclass that holds all mutable state for a single build execution.

```python
@dataclass
class BuildRunState:
    """Mutable state for a single build run. Passed between phase groups."""
    options: BuildOptions
    build_input: BuildInput
    build_start: float
    build_id: str
    cache: BuildCache
    incremental: bool
    config_changed: bool
    early_ctx: BuildContext
    output_collector: BuildOutputCollector
    generated_page_cache: GeneratedPageCache
    pages_to_build: list[Page] | None
    assets_to_process: list[Asset]
    affected_tags: set[str]
    affected_sections: set[str]
    changed_page_paths: set[Path]
    ctx: BuildContext | None
    on_phase_start: Callable[[str], None] | None
    on_phase_complete: Callable[[str, float, str], None] | None
```

**Pros**: Explicit contract, testable.
**Cons**: 12 of 18 fields already exist on `BuildContext` — this creates a near-duplicate type. Adds a third state container alongside `BuildContext` and `BuildState`. Migration cost is high (40+ local references).

---

### Option B: Extend BuildContext

Add remaining orchestration fields to `BuildContext` and use it as the sole state carrier.

**Pros**: Reuses existing type.
**Cons**: `BuildContext` is already 757 lines with 35+ fields. Mixes rendering context with orchestration coordination. `BuildContext` is also used by validators and post-processing — lifecycle confusion.

---

### Option C: Minimal Extraction (No New State Type)

Extract phase group methods using `SimpleNamespace` or `dict` for state.

**Pros**: Smallest change.
**Cons**: No type safety, opaque, hard to test.

---

### Option D: Extract-First, Single-Context (Recommended)

Fix the dual-context bug first, extract inline code into submodule functions, then add thin phase group methods. No new state type.

**Insight**: The biggest wins come from *extracting inline code* and *eliminating the second BuildContext*, not from introducing a new state container. Once those are done, `build()` shrinks to ~200 lines of phase calls, and phase group methods become trivial wrappers.

**Step 1 — Fix dual-context (Finding #1):**
Stop creating a second `BuildContext` in `phase_render`. Populate `early_ctx` with the remaining fields before the rendering phase:

```python
# In build(), before phase_render:
early_ctx.pages = pages_to_build
early_ctx.profile = profile
early_ctx.progress_manager = progress_manager
early_ctx.reporter = reporter
early_ctx.profile_templates = profile_templates
early_ctx.output_collector = output_collector

# phase_render receives and returns the SAME context
ctx = rendering.phase_render(self, cli, ..., context=early_ctx)
# ctx IS early_ctx — no field transfer needed
```

**Step 2 — Extract inline code into submodule functions:**

```python
# New in snapshot.py
def phase_snapshot(orchestrator, cli, early_ctx, pages_to_build, force_sequential) -> None:
    """Create site snapshot, warm caches, instantiate services."""
    ...

# New in finalization.py
def phase_update_generated_page_cache(orchestrator, pages_to_build, cache, generated_page_cache) -> None:
    """Update GeneratedPageCache for rendered tag pages."""
    ...

def phase_compute_reload_hint(stats, output_collector) -> None:
    """Compute reload_hint from output collector for dev server."""
    ...
```

**Step 3 — `build()` becomes a thin coordinator:**

```python
def build(self, options: BuildOptions | BuildInput) -> BuildStats:
    ctx = self._setup_build(options)

    ctx = self._run_init_phases(ctx)

    filter_result = self._run_filter_phase(ctx)
    if filter_result is None:
        return self.stats

    ctx = self._run_content_phases(ctx, filter_result)

    self._run_parsing_and_snapshot(ctx)
    if ctx.dry_run:
        return self._finalize_dry_run(ctx)

    self._run_rendering_phases(ctx)
    self._run_finalization_phases(ctx)
    return self.stats
```

**Pros**:
- Fixes a real bug (dual-context) as a prerequisite, not a separate task.
- No new state type — `BuildContext` is already the state carrier.
- Each step is independently shippable and testable.
- `build()` shrinks from 708 → ~100 lines.
- Inline code extraction is pure mechanical refactoring — low risk.

**Cons**:
- Adds ~6 fields to `BuildContext` (but removes the second instance, net simpler).
- Phase group methods on `BuildOrchestrator` don't have a typed input — they take `self` + `BuildContext`.

---

## Recommendation: Option D (Extract-First, Single-Context)

Option A's `BuildRunState` was designed before the code deep-dive revealed that `BuildContext` already carries 12 of 18 proposed fields. Creating a near-duplicate type adds complexity without proportional benefit.

Option D is preferred because:

1. **Fixes a real bug first**: The dual-context field-transfer pattern is a latent defect. Fixing it is prerequisite work regardless of which option is chosen.
2. **Incremental delivery**: Each step (fix dual-context → extract inline code → add phase groups) ships independently and passes CI.
3. **No new concepts**: Developers already understand `BuildContext`. A new `BuildRunState` would require explaining its relationship to `BuildContext` and `BuildState`.
4. **Lower migration cost**: ~6 fields added to `BuildContext` vs. 40+ local variable references migrated to a new type.
5. **Same end result**: `build()` becomes a thin coordinator of phase group methods either way.

---

## Implementation Plan

### Phase 1: Extract Inline Finalization Code (Low Risk, High Impact)

Move ~150 lines of inline code from `build()` into `finalization.py` functions. No new types, no state changes — pure mechanical extraction.

**Files changed**: `build/__init__.py`, `build/finalization.py`

| Extract | From (lines) | To | LOC |
|---------|--------------|-----|-----|
| Generated page cache update | 700–739 | `finalization.phase_update_generated_cache()` | 39 |
| Parallel cache save | 744–767 | `finalization.phase_cache_save_parallel()` | 23 |
| Reload hint + output logging | 776–810 | `finalization.phase_compute_reload_hint()` | 34 |
| Provenance save | 840–845 | `finalization.phase_save_provenance()` | 6 |

**Validation**: Run full test suite. `build()` shrinks by ~150 lines. Each new function is independently testable.

### Phase 2: Extract Inline Snapshot Code (Low Risk)

Move 73 lines of snapshot/service creation into a new `build/snapshot.py` submodule.

**Files changed**: `build/__init__.py`, new `build/snapshot.py`

```python
# New: build/snapshot.py
def phase_snapshot(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    early_ctx: BuildContext,
    pages_to_build: list[Page],
    force_sequential: bool,
) -> None:
    """Create site snapshot, warm caches, instantiate services on early_ctx."""
    ...
```

**Validation**: Same test suite. Snapshot behavior is unchanged.

### Phase 3: Fix Dual-BuildContext Bug (Medium Risk)

Eliminate the second `BuildContext` created in `phase_render`. Populate `early_ctx` with the remaining fields and pass it through directly.

**Files changed**: `build/__init__.py`, `build/rendering.py`

Before (current — `rendering.py:516-538`):
```python
ctx = BuildContext(site=..., pages=..., stats=...)
if early_context and early_context.has_cached_content:
    ctx._page_contents = early_context._page_contents  # Manual transfer!
```

After:
```python
def phase_render(orchestrator, cli, ..., context: BuildContext) -> BuildContext:
    """Render pages using the provided context (no new context created)."""
    # context already has all fields — use it directly
    ...
    return context
```

**Migration**: Add ~6 field assignments to `build()` before `phase_render`:
- `early_ctx.pages = pages_to_build`
- `early_ctx.profile = profile`
- `early_ctx.progress_manager = progress_manager`
- `early_ctx.reporter = reporter`
- `early_ctx.profile_templates = profile_templates`

Remove the two `BuildContext(...)` constructor calls and all field transfers in `rendering.py`.

**Validation**: Run full test suite + integration tests. Verify that `ctx` returned by `phase_render` has `_page_contents`, `snapshot`, `query_service`, and `data_service` (fields that currently get lost in the transfer).

### Phase 4: Extract Variant Filter + URL Collision (Low Risk)

Move Phase 12.25 (variant filter, 8 lines) and Phase 12.5 (URL collision, 4 lines) into `content.py`.

**Files changed**: `build/__init__.py`, `build/content.py`

### Phase 5: Add Phase Group Methods (Low Risk)

With all inline code extracted, `build()` is ~200 lines of sequential phase calls. Add thin phase group methods:

```python
def _run_init_phases(self, ctx: BuildContext) -> BuildContext:
    """Phases 1–4: Fonts, validation, discovery, cache metadata, config check."""
    initialization.phase_fonts(self, ctx.cli, collector=ctx.output_collector)
    initialization.phase_template_validation(self, ctx.cli, strict=ctx.strict)
    initialization.phase_discovery(self, ctx.cli, ctx.incremental, build_context=ctx, build_cache=ctx.cache)
    initialization.phase_cache_metadata(self)
    config_result = initialization.phase_config_check(self, ctx.cli, ctx.cache, ctx.incremental)
    ctx.incremental = config_result.incremental
    ctx.config_changed = config_result.config_changed
    return ctx

def _run_filter_phase(self, ctx: BuildContext) -> FilterResult | None:
    """Phase 5: Incremental filter. Returns None for early exit."""
    ...

def _run_content_phases(self, ctx: BuildContext, filter_result: FilterResult) -> BuildContext:
    """Phases 6–12.5: Sections, taxonomies, menus, indexes, variant filter, URL collision."""
    ...

def _run_parsing_and_snapshot(self, ctx: BuildContext) -> None:
    """Parsing + snapshot creation. Mutates ctx in place."""
    ...

def _run_rendering_phases(self, ctx: BuildContext) -> None:
    """Phases 13–16: Assets, render, update pages, track deps."""
    ...

def _run_finalization_phases(self, ctx: BuildContext) -> None:
    """Phases 17–21: Postprocess, caches, stats, health, finalize."""
    ...
```

**`build()` becomes:**

```python
def build(self, options: BuildOptions | BuildInput) -> BuildStats:
    ctx = self._setup_build(options)

    ctx = self._run_init_phases(ctx)

    filter_result = self._run_filter_phase(ctx)
    if filter_result is None:
        return self.stats

    ctx = self._run_content_phases(ctx, filter_result)

    self._run_parsing_and_snapshot(ctx)
    if options.dry_run:
        return self._finalize_dry_run(ctx)

    self._run_rendering_phases(ctx)
    self._run_finalization_phases(ctx)
    return self.stats
```

### Phase 6: Add Phase Group Tests

Add unit tests for each phase group method with minimal fixtures:

```python
def test_run_init_phases_populates_cache(mock_site):
    """Init phases should populate ctx.cache from incremental.initialize()."""
    ...

def test_run_filter_phase_returns_none_on_no_changes(mock_site):
    """Filter phase should return None when no changes detected."""
    ...

def test_run_content_phases_includes_taxonomy_pages(mock_site):
    """Content phases should add generated taxonomy pages to pages_to_build."""
    ...
```

---

## Risks and Mitigations

| Risk | Level | Evidence | Mitigation |
|------|-------|----------|------------|
| Regression in incremental builds | **High** | Filter → content → render state flow is the most fragile path. `incremental` flag mutates in Phase 4. | Run full integration test suite after each phase. Phase 3 (dual-context fix) is the highest-risk change — test with both full and incremental builds. |
| `early_ctx` → rendering field loss | **High** | `phase_render` currently drops `query_service`, `data_service` during context copy (`rendering.py:516-538`). | Phase 3 fix eliminates this class of bugs entirely. Add assertion test that all `early_ctx` fields survive into post-rendering `ctx`. |
| Dashboard callback breakage | **Low** | `notify_phase_start`/`notify_phase_complete` are closures defined in `build()` — they capture `on_phase_start`/`on_phase_complete` by closure. | Keep closures in `_setup_build()` and store on `ctx`. Phase group methods call `ctx.notify_phase_start(...)`. |
| Test coverage gaps | **Medium** | Only 4 unit tests cover `build()`, all with heavy mocking. No integration test validates the full state flow end-to-end. | Phase 6 adds phase-group-level tests. Consider adding one integration test using a real test site root. |
| BuildContext field bloat | **Medium** | `BuildContext` is already 757 lines with 35+ fields. Phase 3 adds ~6 more. | The 6 new fields replace the second `BuildContext` instance — net complexity decreases. Fields added are rendering-phase inputs that logically belong on the context. |

---

## Alternatives Considered

### Keep Monolithic build()

**Rejected**: Maintainability and testability suffer; dual-context bug persists.

### Option A: New BuildRunState Type

**Superseded by Option D**: 12 of 18 proposed fields already exist on `BuildContext`. Creating a near-duplicate adds a third state container without proportional benefit. Option D achieves the same end result (thin `build()` coordinator) without the new type.

### Extract to Separate Coordinator Class

**Deferred**: Could introduce `BuildPhaseCoordinator` that owns the phase group methods and `BuildContext`. Adds indirection; Option D achieves most benefits without a new class. Revisit if `BuildOrchestrator` grows beyond build coordination.

### Use Context Manager for BuildContext

**Already implemented**: `BuildContext` supports `__enter__`/`__exit__` for build-scoped cache lifecycle (`build_context.py:393-431`). Phase group methods should use this.

---

## Resolved Questions

1. **BuildContext vs. BuildRunState overlap**: Resolved — use `BuildContext` directly. It already has 12 of 18 proposed `BuildRunState` fields. The remaining 6 (`options`, `build_input`, `generated_page_cache`, `on_phase_start`, `on_phase_complete`, and `collector`) are added in Phase 3.

2. **Phase group boundaries**: Resolved — filter is its own phase (returns `FilterResult | None`), not lumped with initialization. Parsing + snapshot are a bridge phase (`_run_parsing_and_snapshot`) between content and rendering. This matches the actual control flow: content produces `pages_to_build`, parsing prepares content, snapshot freezes state, rendering consumes it.

3. **Dashboard integration**: Resolved — the existing dashboard callbacks fire for "discovery", "content", "assets", "rendering", "finalization", "health". Phase group methods preserve these exact boundaries. `notify_phase_start`/`notify_phase_complete` closures move to `BuildContext` fields or stay as closure locals within `_setup_build`.

## Open Questions

1. **`generated_page_cache` on BuildContext**: This cache is only used during content (Phase 12) and finalization. Should it be a `BuildContext` field, or passed as a parameter to the two phase group methods that need it? (Lean: field, for consistency.)

2. **`collector` (PerformanceCollector) lifecycle**: Currently created conditionally in `build()` and passed to `phase_finalize`. Should it move to `BuildContext` or stay as a local in `_setup_build`? (Lean: local — it's infrastructure, not build state.)

3. **Incremental test coverage**: Should Phase 6 include an integration test with a real test site root, or are mocked phase-group tests sufficient? (Lean: both — one integration test for the happy path, mocked tests for edge cases.)

---

## Phase Delivery Schedule

| Phase | Risk | Dependencies | Estimated LOC |
|-------|------|-------------|--------------|
| 1: Extract finalization inline code | Low | None | ~180 (move + add function signatures) |
| 2: Extract snapshot inline code | Low | None (parallel with Phase 1) | ~100 |
| 3: Fix dual-context bug | Medium | Phase 1, 2 (so `build()` is smaller) | ~120 (remove + add) |
| 4: Extract variant/collision | Low | Phase 1 | ~30 |
| 5: Add phase group methods | Low | Phases 1–4 | ~150 |
| 6: Add phase group tests | Low | Phase 5 | ~200 |
| **Total** | | | **~780 LOC touched** |

Phases 1 and 2 can ship independently. Phase 3 requires Phase 1 and 2 to be landed first (smaller `build()` reduces merge conflict risk). Phases 4–6 ship after Phase 3.

---

## References

- `plan/rfc-build-orchestrator-phases-5-6-plan.md` — **Implementation plan for Phases 5 & 6** (setup extraction, phase group methods, tests)
- `bengal/orchestration/build/__init__.py` — current `build()` implementation (~550 lines post Phase 1–4)
- `bengal/orchestration/build_context.py` — `BuildContext` definition (757 lines, 35+ fields)
- `bengal/orchestration/build_state.py` — `BuildState` (per-build mutable state on Site)
- `bengal/orchestration/build/rendering.py:477-538` — dual-context bug (Finding #1)
- `bengal/orchestration/build/finalization.py` — existing finalization functions
- `bengal/orchestration/build/results.py` — `FilterResult`, `ConfigCheckResult` types
- `tests/unit/orchestration/test_build_orchestrator.py` — existing tests (4 tests, heavy mocking)
- Bengal DRY Refactor Plan Phase 5c (cancelled)
- `plan/rfc-incremental-build-observability.md` — related observability work
