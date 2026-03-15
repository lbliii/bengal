# Plan: RFC Build Orchestrator Phase Groups — Phases 5 & 6

## Status: Draft
## Created: 2026-03-14
## Revised: 2026-03-14
## Prerequisites: Phases 1–4 implemented (commit 967e1995e)

---

## Summary

This plan details implementation of **Phase 5** (phase group methods) and **Phase 6** (phase group tests) from `plan/rfc-build-orchestrator-phase-groups.md`. Phases 1–4 are complete; this document provides the concrete design for the remaining work.

**Goal**: Reduce `build()` from ~390 lines to ~35–50 lines by extracting setup and phase logic into `_setup_build()`, `_run_*` methods, and `_finalize_dry_run()`. Add unit tests for each phase group.

**Current state** (verified 2026-03-14): `build()` is ~390 lines (lines 141–530). Phases 1–4 (finalization extraction, snapshot extraction, dual-context fix, variant/collision) are complete.

---

## Phase 5: Add Phase Group Methods

### 5.1 BuildContext Additions

Add fields to `BuildContext` so it carries all state between phase groups. No new type.

| Field | Type | Set By | Used By |
|-------|------|--------|---------|
| `options` | `BuildOptions` | `_setup_build` | All (dry_run, strict, etc.) |
| `build_input` | `BuildInput` | `_setup_build` | Debugging, serialization |
| `generated_page_cache` | `GeneratedPageCache` | `_setup_build` | Content, finalization |
| `notify_phase_start` | `Callable[[str], None]` | `_setup_build` | All phase groups |
| `notify_phase_complete` | `Callable[[str, float, str], None]` | `_setup_build` | All phase groups |
| `dry_run` | `bool` | `_setup_build` | Coordinator (early exit) |

**File**: `bengal/orchestration/build_context.py`

**Note**: `BuildContext` already has `cache`, `output_collector`, `cli`, `incremental`, `config_changed`, `pages_to_build`, `assets_to_process`, `affected_tags`, `affected_sections`, `changed_page_paths`, `build_start`, `build_id`. The 6 new fields complete the state carrier.

### 5.2 _setup_build(options) → BuildContext

**Responsibility**: Normalize input, initialize infrastructure, create and populate `BuildContext`.

**Extract from `build()`** (lines ~160–376):

1. Normalize `BuildInput` / `BuildOptions`
2. Store `self.options`, `self.current_input`
3. Extract option-derived flags (force_sequential, incremental, verbose, …)
4. Create `notify_phase_start` / `notify_phase_complete` closures
5. Initialize profile, CLI, progress_manager, reporter
6. Start timing, `_build_id`, clear dir cache
7. Initialize `collector` (PerformanceCollector) if enabled
8. Initialize `self.stats`, diagnostics, build header
9. Create `BuildState`, call `incremental.initialize()`
10. Create `GeneratedPageCache`
11. Resolve `incremental` (auto mode)
12. Create `BuildContext` with all fields populated
13. Create `output_collector`

**Returns**: `BuildContext` (early_ctx) with:
- `site`, `stats`, `profile`, `cli`, `progress_manager`, `reporter`
- `cache`, `generated_page_cache`, `output_collector`
- `incremental`, `strict`, `verbose`, `quiet`, `memory_optimized`, `profile_templates`
- `options`, `build_input`, `dry_run`
- `build_start`, `build_id`
- `notify_phase_start`, `notify_phase_complete`
- `options.changed_sources`, `options.nav_changed_sources` (for filter phase; read from ctx.options)

**Side effects**: Mutates `self.stats`, `self.site.build_state`, `self._build_id`, etc.

### 5.3 Phase Group Method Signatures

```python
def _run_init_phases(self, ctx: BuildContext) -> BuildContext:
    """Phases 1–4: Fonts, validation, discovery, cache metadata, config check."""

def _run_filter_phase(self, ctx: BuildContext) -> FilterResult | None:
    """Phase 5: Incremental filter. Returns None for early exit."""

def _run_content_phases(self, ctx: BuildContext, filter_result: FilterResult) -> BuildContext:
    """Phases 6–12.5: Sections, taxonomies, menus, indexes, variant filter, URL collision."""

def _run_parsing_and_snapshot(self, ctx: BuildContext) -> None:
    """Parsing + snapshot creation. Mutates ctx in place."""

def _run_rendering_phases(self, ctx: BuildContext) -> None:
    """Phases 13–16: Assets, render, update pages, track deps, record provenance."""

def _run_finalization_phases(self, ctx: BuildContext) -> None:
    """Phases 17–21: Postprocess, caches, stats, error session, reload hint, health, finalize."""

def _finalize_dry_run(self, ctx: BuildContext) -> BuildStats:
    """Dry-run early exit: set stats, clear build state, return."""
```

### 5.4 State Flow Between Phase Groups

| Phase Group | Reads from ctx | Writes to ctx | Returns |
|-------------|----------------|---------------|---------|
| `_setup_build` | — | All initial fields | `BuildContext` |
| `_run_init_phases` | cli, output_collector, incremental, cache, strict | incremental, config_changed | `BuildContext` |
| `_run_filter_phase` | cli, cache, incremental, verbose, build_start, changed_sources, nav_changed_sources | — | `FilterResult \| None` |
| `_run_content_phases` | filter_result, cli, cache, incremental, force_sequential, generated_page_cache | pages_to_build, affected_tags | `BuildContext` |
| `_run_parsing_and_snapshot` | pages_to_build, cli, force_sequential | snapshot, query_service, data_service | — |
| `_run_rendering_phases` | pages_to_build, assets_to_process, cli, incremental, output_collector, … | — | — |
| `_run_finalization_phases` | ctx (full), pages_to_build, assets_to_process | — | — |

**Filter → content handoff**: `_run_filter_phase` returns `FilterResult | None`. `_run_content_phases` receives `filter_result` and **populates ctx at the start** (`ctx.pages_to_build`, `ctx.assets_to_process`, `ctx.affected_tags`, `ctx.changed_page_paths`, `ctx.affected_sections`) before running content phase functions. The filter phase does not mutate ctx.

### 5.5 build() Final Shape

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

**Target**: ~35 lines (excluding docstring).

### 5.6 Implementation Order

1. Add 6 fields to `BuildContext` (5.1)
2. Extract `_setup_build()` — largest block (~220 lines)
3. Extract `_finalize_dry_run()` — small, isolated
4. Extract `_run_init_phases()` — straightforward
5. Extract `_run_filter_phase()` — returns `FilterResult | None` (does not mutate ctx)
6. Extract `_run_content_phases()` — uses filter_result to populate ctx
7. Extract `_run_parsing_and_snapshot()` — calls parsing + snapshot modules
8. Extract `_run_rendering_phases()` — assets, render, update pages, track
9. Extract `_run_finalization_phases()` — postprocess through phase_save_provenance
10. Wire `build()` to call phase groups in order

### 5.7 Dashboard Callback Preservation

`notify_phase_start` and `notify_phase_complete` are stored on `ctx` and called by each `_run_*` method at the same boundaries as today:
- discovery, content, assets, rendering, finalization, health

No change to dashboard integration.

### 5.8 Phase Group Implementation Details

Each `_run_*` method delegates to existing submodule functions. This section documents the exact calls to ensure nothing is dropped during extraction.

**`_run_init_phases`**:
- `initialization.phase_fonts(self, ctx.cli, collector=ctx.output_collector)`
- `initialization.phase_template_validation(self, ctx.cli, strict=ctx.strict)`
- `notify_phase_start("discovery")` … `initialization.phase_discovery(...)` … `notify_phase_complete("discovery", ...)`
- `initialization.phase_cache_metadata(self)`
- `config_result = initialization.phase_config_check(...)` → update `ctx.incremental`, `ctx.config_changed`

**`_run_filter_phase`**:
- `phase_incremental_filter_provenance(self, ctx.cli, ctx.cache, ctx.incremental, ctx.verbose, ctx.build_start, changed_sources=ctx.options.changed_sources or None, nav_changed_sources=ctx.options.nav_changed_sources or None)`
- Returns `FilterResult | None`; does not mutate ctx

**`_run_content_phases`**:
- Populate ctx from filter_result (pages_to_build, assets_to_process, affected_tags, changed_page_paths, affected_sections)
- `notify_phase_start("content")` … content phases … `notify_phase_complete("content", ...)`
- `content.phase_sections`, `phase_taxonomies`, `phase_taxonomy_index`, `phase_menus`, `phase_related_posts`, `phase_query_indexes`, `phase_update_pages_list`, `phase_variant_filter`, `phase_url_collision_check`

**`_run_parsing_and_snapshot`**:
- `parsing.phase_parse_content(self, ctx.cli, ctx.pages_to_build, parallel=not ctx.options.force_sequential)`
- `snapshot.phase_snapshot(self, ctx.cli, ctx, ctx.pages_to_build, ctx.options.force_sequential)`
- Mutates ctx (snapshot, query_service, data_service)

**`_run_rendering_phases`**:
- `notify_phase_start("assets")` … `rendering.phase_assets(...)` … `notify_phase_complete("assets", ...)`
- `notify_phase_start("rendering")` … populate `ctx.pages`, `ctx.profile`, etc. … `rendering.phase_render(...)`
- `rendering.phase_update_site_pages`, `rendering.phase_track_assets`
- `record_all_page_builds(self, ctx.pages_to_build, ...)` (provenance_filter) when `_provenance_filter` exists

**`_run_finalization_phases`**:
- `notify_phase_start("finalization")` … `finalization.phase_postprocess`, `phase_update_generated_cache`, `phase_cache_save_parallel`, `phase_collect_stats`
- `self._finalize_error_session()` (Phase 19.5)
- `finalization.phase_compute_reload_hint`, `notify_phase_complete("finalization", ...)`
- `notify_phase_start("health")` … `finalization.run_health_check` … `notify_phase_complete("health", ...)`
- `finalization.phase_finalize`, `phase_save_provenance`
- `self.site.set_build_state(None)`

---

## Phase 6: Add Phase Group Tests

### 6.1 Test File

**File**: `tests/unit/orchestration/test_build_orchestrator.py` (extend existing)

### 6.2 Test Strategy

- Use `mock_site` and `mock_orchestrators` fixtures from existing tests
- Patch submodule functions to isolate phase group logic
- Assert phase group methods call the right submodules with expected args
- One integration-style test with real site root (optional, mark `@pytest.mark.integration`)

### 6.3 Test Cases

| Test | Purpose |
|------|---------|
| `test_setup_build_populates_context` | `_setup_build` returns ctx with options, cache, output_collector, etc. |
| `test_setup_build_resolves_incremental_auto` | When incremental=None, resolves from cache presence |
| `test_run_init_phases_updates_incremental_from_config` | Config check result updates ctx.incremental, ctx.config_changed |
| `test_run_filter_phase_returns_none_on_no_changes` | Filter returns None → early exit |
| `test_run_filter_phase_populates_context_on_success` | Filter returns FilterResult → ctx gets pages_to_build, etc. |
| `test_run_content_phases_includes_taxonomy_pages` | Content phases add generated pages to ctx.pages_to_build |
| `test_run_content_phases_applies_variant_filter` | When params.edition set, pages filtered |
| `test_run_parsing_and_snapshot_populates_snapshot` | ctx.snapshot, ctx.query_service set after snapshot |
| `test_run_rendering_phases_calls_assets_and_render` | Assets and render phases invoked |
| `test_run_finalization_phases_calls_postprocess_and_health` | Postprocess, cache save, health, finalize invoked |
| `test_finalize_dry_run_clears_build_state` | Dry-run exit clears site.build_state |
| `test_build_coordinator_early_exit_on_filter_none` | build() returns early when filter returns None |
| `test_run_rendering_phases_records_provenance` | When _provenance_filter exists, record_all_page_builds called |
| `test_run_finalization_phases_calls_error_session` | _finalize_error_session invoked during finalization |

### 6.4 Fixture Requirements

- **Minimal BuildContext**: Factory or helper to create `BuildContext` with required fields for phase group tests. Example:
  ```python
  def make_minimal_ctx(site, stats, cache=None) -> BuildContext:
      return BuildContext(site=site, stats=stats, cache=cache, incremental=False, strict=False)
  ```
- **FilterResult fixture**: `FilterResult(pages_to_build=[], assets_to_process=[], affected_tags=set(), changed_page_paths=set(), affected_sections=None)` — reuse pattern from existing `test_full_build_sequence`

### 6.5 Optional Integration Test

Use `site_factory` from `tests/_testing/fixtures.py` (creates Site from `tests/roots/`). No `roots_minimal_content` fixture exists.

```python
@pytest.mark.integration
def test_build_full_flow_with_real_site(site_factory):
    """Full build with real site root validates end-to-end state flow."""
    site = site_factory("test-basic")
    orch = BuildOrchestrator(site)
    stats = orch.build(BuildOptions(incremental=False, force_sequential=True))
    assert stats.total_pages > 0
```

**Alternative**: Use `minimal_site` fixture pattern from `tests/integration/test_incremental_cache_stability.py` (tmp_path with bengal.toml + content) for a lighter integration test.

---

### 6.6 Migration Notes for Existing Tests

The 4 existing tests (`test_full_build_sequence`, `test_incremental_build_sequence`, etc.) patch `phase_incremental_filter_provenance` and mock orchestrators. After extraction:

- Tests continue to call `orchestrator.build(options)` — no change to test entry point
- Phase group methods are internal; tests need not call them directly unless testing isolation
- Verify `mock_orchestrators["incremental"].return_value.save_cache` assertion: `phase_cache_save_parallel` may call `incremental.save_cache` indirectly — confirm call path and update assertion if needed

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `_setup_build` too large | Extract in sub-steps: (1) input normalization, (2) CLI/profile, (3) cache/state, (4) BuildContext creation |
| Callback closure capture | Store `notify_phase_start`/`notify_phase_complete` on ctx; phase groups call `ctx.notify_phase_start(...)` |
| Options vs ctx.dry_run | Use `ctx.dry_run` in coordinator; set from `options.dry_run` in `_setup_build` |
| Test brittleness | Mock at submodule boundary (initialization.phase_*, content.phase_*, etc.); avoid mocking internals |
| Dropping `_finalize_error_session` or `record_all_page_builds` | Section 5.8 documents every call; use as extraction checklist |
| `changed_sources` / `nav_changed_sources` access | Store on ctx from `ctx.options.changed_sources` (options is on ctx after 5.1) |

---

## Post-Extraction Verification

Before considering Phase 5 complete, diff the pre-extraction `build()` control flow against the phase group calls:

1. **Init**: fonts, template_validation, discovery (with notify), cache_metadata, config_check
2. **Filter**: phase_incremental_filter_provenance → early return if None
3. **Content**: sections through url_collision_check (with notify)
4. **Parsing**: phase_parse_content, phase_snapshot
5. **Dry-run**: early exit with _finalize_dry_run
6. **Assets**: phase_assets (with notify)
7. **Rendering**: phase_render, phase_update_site_pages, phase_track_assets, record_all_page_builds (with notify)
8. **Finalization**: phase_postprocess, phase_update_generated_cache, phase_cache_save_parallel, phase_collect_stats, _finalize_error_session, phase_compute_reload_hint (with notify)
9. **Health**: run_health_check (with notify)
10. **Cleanup**: phase_finalize, phase_save_provenance, set_build_state(None)

---

## Validation Checklist

- [ ] `build()` is ~35–50 lines
- [ ] All existing unit tests pass
- [ ] Full site build succeeds (e.g. `site/` root)
- [ ] Incremental build succeeds
- [ ] Dry-run early exit works
- [ ] Dashboard phase callbacks fire at same boundaries
- [ ] Phase 6 tests pass
- [ ] No new public API; all new methods are `_`-prefixed

---

## Estimated Effort

| Task | LOC | Risk | Time |
|------|-----|------|------|
| BuildContext additions | ~15 | Low | 15 min |
| _setup_build extraction | ~220 | Medium | 45 min |
| _finalize_dry_run | ~10 | Low | 5 min |
| _run_init_phases | ~25 | Low | 15 min |
| _run_filter_phase | ~30 | Low | 15 min |
| _run_content_phases | ~55 | Low | 20 min |
| _run_parsing_and_snapshot | ~25 | Low | 10 min |
| _run_rendering_phases | ~80 | Low | 25 min |
| _run_finalization_phases | ~90 | Low | 25 min |
| build() coordinator | ~35 | Low | 10 min |
| Phase 6 tests | ~200 | Low | 45 min |
| **Total** | **~785** | | **~4 hours** |

---

## References

- `plan/rfc-build-orchestrator-phase-groups.md` — parent RFC
- `bengal/orchestration/build/__init__.py` — current build() (~390 lines post Phase 1–4)
- `bengal/orchestration/build_context.py` — BuildContext definition
- `bengal/orchestration/build/results.py` — FilterResult, ConfigCheckResult
- `bengal/orchestration/build/provenance_filter.py` — `phase_incremental_filter_provenance`, `record_all_page_builds`
- `tests/unit/orchestration/test_build_orchestrator.py` — existing tests (4 tests, mock_orchestrators fixture)
- `tests/_testing/fixtures.py` — `site_factory`, `rootdir`
- `tests/integration/test_incremental_cache_stability.py` — `minimal_site` fixture pattern
