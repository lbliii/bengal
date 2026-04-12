# Epic: Wire Incremental Build Dependencies — Close the Effect Gap

**Status**: Complete
**Created**: 2026-04-12
**Target**: v0.4.x
**Estimated Effort**: 12-18 hours
**Dependencies**: None (all infrastructure already exists)
**Source**: rfc-incremental-build-dependency-gaps.md (stale), investigation of 4 xfail integration tests

---

## Why This Matters

Bengal's incremental build system has **all the infrastructure** for effect-traced dependency tracking but **4 integration gaps** cause stale content during warm rebuilds:

1. **Data file changes go undetected** — changing `data/team.yaml` doesn't rebuild pages that accessed `site.data.team`
2. **Taxonomy listings show stale metadata** — changing a post's title doesn't update the `/tags/python/` listing page
3. **Taxonomy listings show stale ordering** — changing a post's date doesn't reorder the listing
4. **Cascade changes don't propagate** — changing `cascade: type: doc` in `_index.md` doesn't rebuild child pages

These are **correctness bugs**, not performance issues. Users see stale content and must manually trigger full rebuilds to fix it.

### Evidence Table

| Source | Finding | Proposal Impact |
|--------|---------|----------------|
| `tests/integration/warm_build/test_dependency_gaps.py` | 4 tests marked `@pytest.mark.xfail` since 2026-01 | **FIXES** — all 4 become passing |
| `effect_detector.py:109-112` | `_pages_for_data_file()` IS called and returns results | **FIXES** — results already flow through `detect_changes()` return value |
| `orchestration/taxonomy.py:228-239` | Taxonomy rebuild already fires for `pages_with_tags` changes | **MITIGATES** — taxonomy structure rebuilds, but term pages may not re-render |
| `provenance_filter.py:617-649` | Gap 2 taxonomy cascade code exists but depends on `result.affected_tags` | **FIXES** — ensure `affected_tags` populated for metadata-only changes |
| `coordinator.py:253` | `invalidate_taxonomy_cascade()` exists but is never called | **FIXES** — wire call at correct integration point |
| `provenance_filter.py:368-377` | `_get_taxonomy_term_pages_for_member()` already finds term pages for changed content | **FIXES** — this code runs but depends on `forced_changed` being populated |

### Three Invariants

These must remain true throughout or we stop and reassess:

1. **Full builds stay identical.** No behavioral change to cold builds. Only warm builds gain new dependency edges.
2. **Rebuild set stays minimal.** Data file change rebuilds only dependent pages, not all pages. Taxonomy metadata change rebuilds only affected term pages, not all term pages.
3. **No performance regression.** Incremental detection stays under 100ms for a 500-page site. Effect recording adds zero overhead to rendering (already frozen data).

---

## Target Architecture

After this epic, the dependency graph has these edges:

```
data/team.yaml changed
  → EffectTracer.outputs_needing_rebuild({data/team.yaml})
  → finds Effect with depends_on including data/team.yaml
  → maps to source .md paths
  → pages rebuilt ✅

post1.md title changed (tags unchanged)
  → post1.md detected as content change
  → provenance_filter expands: find taxonomy term pages listing post1
  → term pages added to rebuild set
  → term pages re-rendered with new title ✅

_index.md cascade changed
  → _detect_cascade_changes() finds all descendant pages
  → descendants added to rebuild set (ALREADY WORKS — verify only)
```

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| **0** | Verify existing wiring, identify exact failure points | 2-3h | Low | Yes (diagnosis only) |
| **1** | Fix Gap 1: data file → dependent page rebuild | 3-4h | Low | Yes |
| **2** | Fix Gap 2: taxonomy metadata propagation | 4-6h | Medium | Yes |
| **3** | Fix Gap 4: cascade propagation (verify/fix) | 2-3h | Low | Yes |
| **4** | Remove xfail markers, harden with edge-case tests | 1-2h | Low | Yes (after 1-3) |

---

## Sprint 0: Diagnose Exact Failure Points

**Goal**: Run the 4 xfail tests with verbose logging to confirm root cause matches investigation.

### Task 0.1 — Run xfail tests with tracing

Run each test with `--runxfail -s -vv` and capture:
- Does EffectTracer have effects with data file in `depends_on`?
- Does `_pages_for_data_file()` return the correct pages?
- Does `detect_changes()` include those pages in its return value?
- Does `provenance_filter` receive the pages?

**Acceptance**: Written diagnosis in `.context/notes.md` confirming or correcting the root cause for each gap.

### Task 0.2 — Trace taxonomy metadata path

For Gap 2: Run taxonomy test and trace:
- Does `changed_pages` include the modified post?
- Does `pages_with_tags` on line 233 include it?
- Does taxonomy structure rebuild fire (line 236)?
- Does `provenance_filter` expand to include term pages (line 368-377)?

**Acceptance**: Root cause confirmed for each taxonomy test failure.

---

## Sprint 1: Data File Dependency Wiring (Gap 1)

**Goal**: When `data/team.yaml` changes, pages that accessed `site.data.team` via templates rebuild.

### Task 1.1 — Verify EffectTracer records data file dependencies

Check that `TrackedData` (in `bengal/rendering/context/data_tracking.py`) calls `record_data_file_access()` during rendering, and that `Effect.for_page_render()` includes data files in `depends_on`.

**Files**: `bengal/rendering/context/data_tracking.py`, `bengal/effects/render_integration.py`, `bengal/effects/effect.py`
**Acceptance**: Add a unit test that renders a page accessing `site.data.team` and asserts the resulting Effect has `Path("data/team.yaml")` in `depends_on`.

### Task 1.2 — Verify EffectBasedDetector returns data-dependent pages

`detect_changes()` at `effect_detector.py:109-112` already calls `_pages_for_data_file()` for yaml/json/toml changes in `data/`. Verify this returns the correct page set.

**Files**: `bengal/orchestration/incremental/effect_detector.py`
**Acceptance**: Unit test that creates an EffectBasedDetector with a tracer containing a data-file effect, calls `detect_changes({data/team.yaml})`, and asserts the dependent page is in the result.

### Task 1.3 — Wire data file detection into orchestrator

If Sprint 0 reveals the gap is in orchestrator integration (e.g., `find_work_early()` not passing data file paths to detector, or cache bypass logic filtering them out), fix the wiring.

**Files**: `bengal/orchestration/incremental/orchestrator.py`
**Acceptance**: `rg 'data.*file' bengal/orchestration/incremental/orchestrator.py` shows data file handling. `test_data_file_change_triggers_incremental_rebuild` passes with `--runxfail`.

---

## Sprint 2: Taxonomy Metadata Propagation (Gap 2)

**Goal**: When a post's title or date changes (but tags don't), taxonomy term pages listing that post rebuild.

### Task 2.1 — Ensure taxonomy term pages enter rebuild set

The code at `provenance_filter.py:368-377` already calls `_get_taxonomy_term_pages_for_member()` for changed content pages. Verify this fires for the test scenario and that `term_pages` is non-empty.

**Files**: `bengal/orchestration/build/provenance_filter.py`
**Acceptance**: Debug trace showing `_get_taxonomy_term_pages_for_member()` returns term page paths for the changed post.

### Task 2.2 — Wire CacheCoordinator.invalidate_taxonomy_cascade

`invalidate_taxonomy_cascade()` at `coordinator.py:253` exists but is never called from production code (only tested in `tests/unit/cache/test_coordinator.py:201`). Wire it into the taxonomy rebuild path so cache layers are properly invalidated.

**Files**: `bengal/orchestration/build/coordinator.py`, `bengal/orchestration/taxonomy.py`
**Acceptance**: `rg 'invalidate_taxonomy_cascade' bengal/orchestration/ --type py` shows at least one call site beyond the coordinator definition.

### Task 2.3 — Ensure term page re-render uses current metadata

Verify that when a taxonomy term page is in the rebuild set, it renders with the **current** page metadata (new title, new date), not a cached version.

**Files**: `bengal/orchestration/taxonomy.py`, `bengal/snapshots/persistence.py`
**Acceptance**: Both taxonomy xfail tests pass with `--runxfail`:
- `test_taxonomy_term_page_updates_on_member_title_change`
- `test_taxonomy_term_page_updates_on_member_date_change`

---

## Sprint 3: Cascade Propagation (Gap 4)

**Goal**: When `_index.md` cascade frontmatter changes, child pages rebuild with updated cascade values.

### Task 3.1 — Verify _detect_cascade_changes catches the scenario

`orchestrator.py:355-356` already calls `_detect_cascade_changes()` which should find descendant pages when an `_index.md` changes. Verify this works for the cascade test case.

**Files**: `bengal/orchestration/incremental/orchestrator.py`
**Acceptance**: `test_cascade_change_triggers_child_page_rebuild` passes with `--runxfail`.

### Task 3.2 — Fix nested cascade propagation if needed

If `test_nested_cascade_change_propagates_to_deep_children` still fails, the cascade detection may only go one level deep. Ensure it walks the full descendant tree.

**Files**: `bengal/orchestration/incremental/orchestrator.py`
**Acceptance**: Both cascade tests pass with `--runxfail`.

---

## Sprint 4: Remove Xfail Markers and Harden

**Goal**: All 4 gap tests run as normal (non-xfail) tests. Add edge cases.

### Task 4.1 — Remove xfail markers

Remove `@pytest.mark.xfail` and `@pytest.mark.known_gap` from all 4 test classes in `test_dependency_gaps.py`.

**Files**: `tests/integration/warm_build/test_dependency_gaps.py`
**Acceptance**: `rg 'xfail.*dependency-gaps' tests/` returns zero hits.

### Task 4.2 — Add edge-case tests

Add tests for:
- Data file change + content change in same build (both should rebuild correctly)
- Multiple taxonomy terms affected by one post change
- Cascade change affecting 3+ levels of nesting

**Files**: `tests/integration/warm_build/test_dependency_gaps.py`
**Acceptance**: `pytest tests/integration/warm_build/test_dependency_gaps.py -v` all green, 8+ tests.

### Task 4.3 — Update stale RFC

Update `plan/rfc-incremental-build-dependency-gaps.md` status from "Stale" to "Complete" with references to the implementing PRs.

**Files**: `plan/rfc-incremental-build-dependency-gaps.md`
**Acceptance**: Status line reads "Complete".

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| EffectTracer doesn't record data file deps in practice | Low | High | Sprint 0 verifies before any code changes |
| Taxonomy rebuild is too aggressive (rebuilds all term pages instead of affected ones) | Medium | Low | Sprint 2 acceptance requires `cache_misses < total_pages` |
| Cascade detection already works and tests fail for a different reason | Medium | Low | Sprint 0 runs tests with tracing to confirm |
| Performance regression from additional dependency checking | Low | Medium | Invariant 3: benchmark detection time before/after on 500-page test root |

---

## Success Metrics

| Metric | Current | After Sprint 2 | After Sprint 4 |
|--------|---------|----------------|----------------|
| xfail tests in test_dependency_gaps.py | 4 | 2 (Gaps 1+2 fixed) | 0 |
| Incremental detection time (500-page site) | <50ms | <50ms | <100ms |
| Data file change: correct pages rebuilt | No | Yes | Yes + edge cases |
| Taxonomy metadata change: term pages updated | No | Yes | Yes + edge cases |
| Cascade change: child pages updated | Unknown | Unknown | Yes |

---

## Relationship to Existing Work

- **rfc-incremental-build-dependency-gaps.md** — supersedes (architecture evolved, but gaps remain)
- **epic-immutable-page-pipeline.md** — parallel / independent (Sprint 6 Page deletion is unrelated)
- **epic-protocol-migration.md** — independent (protocol adoption doesn't affect incremental detection)
- **rfc-effect-traced-incremental-builds.md** — builds on (this epic wires the effect infrastructure that RFC designed)

---

## Changelog

- **2026-04-12**: Initial draft from codebase investigation. All infrastructure exists; gaps are wiring issues, not architectural ones.
- **2026-04-12**: Sprint 0 diagnosis revealed only Gap 1 (data file) actually failed. Gaps 2, 3, 4 already pass. Root cause: `_get_pages_for_data_file()` queried BuildCache.dependencies (empty for data files) instead of EffectTracer. One-line fix in `provenance_filter.py`. All 8 tests pass, xfail markers removed.
