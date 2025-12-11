# RFC: Incremental Build & Hot Reload Invariants

- **Status:** Draft (revised)
- **Owner:** AI (pairing with llane)
- **Date:** 2025-12-11
- **Scope:** Dev server incremental builds, cache validity, change classification, and reload delivery

## Problem

Recent hot-reload regressions showed that stale content can surface when any of these layers disagree: file watching, change classification, incremental filtering, cache validity, rendering/cache bypass, and reload delivery.

Key pain points from debugging:
- **Layer coupling:** Watch events → incremental filter → cache checks → rendering cache reuse → reload. A miss in any step leads to stale pages; no single invariant enforced.
- **Section index scope:** `_index.md` edits can fan out widely; distinguishing body-only vs nav/cascade changes requires metadata hash comparison (now implemented but not extended to all section indexes).
- **Cache bypass fragmentation:** `is_changed` alone isn't sufficient (revert-to-same-content, hash update timing). The `changed_sources` signal exists but bypass logic is duplicated across modules.
- **Structural changes implicit:** File creates/deletes/moves trigger full rebuilds, but `structural_changed` isn't a formal signal threaded through the pipeline.

## Current State (What's Already Implemented)

Several invariants from prior work are already in place:

| Invariant | Status | Evidence |
|-----------|--------|----------|
| `changed_sources` + `nav_changed_sources` threaded | ✅ Done | `incremental.py:274-275`, `build_handler.py:437-438` |
| Section filter safety (forced/nav pages bypass) | ✅ Done | `incremental.py:312-348` |
| Hash update ordering (after render) | ✅ Done | `save_cache()` at `incremental.py:1022-1074` |
| Metadata hash in parsed_content cache | ✅ Done | `parsed_content_cache.py:83,98` |
| Metadata hash comparison for nav-changed paths | ✅ Done | `incremental.py:417-434` |
| Reload decision logging | ✅ Done | `build_handler.py:520-528` |
| Rebuild trigger logging | ✅ Done | `build_handler.py:381-388` |

**What's missing:**
- Centralized cache bypass helper (logic duplicated in `pipeline/core.py:196-201` and `incremental.py:366`)
- `structural_changed` as explicit signal (currently inferred from `pending_event_types`)
- Cache bypass hit/miss counters per-build
- Metadata hash comparison for ALL section indexes (not just explicitly nav-changed)

## Goals

1. Centralize cache bypass logic into a single helper
2. Add `structural_changed` as explicit build parameter
3. Extend metadata hash comparison to all `_index.md` files
4. Fill specific observability gaps (cache bypass counters, change classification breakdown)

## Non-Goals

- No change to production (non-dev) build semantics
- No redesign of SSE transport; focus on correctness and visibility
- No new caching layers; leverage existing `parsed_content` and `rendered_output` caches

## Proposed Invariants

### Already Enforced (maintain these)

1. **Structured change set:** Build pipeline receives `{changed_sources, nav_changed_sources}` threaded through incremental filtering and rendering.

2. **Section filter safety:** Forced/nav-changed pages always included in `pages_to_check`; their sections are always in the changed set.

3. **Hash update ordering:** File hashes update only after successful render (`save_cache`), never before cache checks.

4. **Reload emission:** After any non-skipped build, emit structured reload payload with action/reason/changed_paths_count.

### New Invariants (to implement)

5. **Structural change signal:** Add `structural_changed: bool` parameter to `BuildOrchestrator.build()`. When true, forces full content discovery (new files may exist, deleted files must be cleaned).

6. **Centralized cache bypass:** Single helper `cache.should_bypass(source_path, changed_sources)` replaces duplicated logic. Returns true when `source in changed_sources OR is_changed(source)`.

7. **Universal frontmatter diff:** For ALL `_index.md` files, compare current metadata hash against cached. If nav/cascade keys differ → section rebuild; otherwise page-only. Currently only applied to explicitly nav-changed paths.

## Implementation Plan

### Phase 1: Cache Bypass Centralization (~2 hours)

**Goal:** Single source of truth for cache bypass decisions.

**Tasks:**
- [ ] Add `should_bypass(source_path: Path, changed_sources: set[Path]) -> bool` to `BuildCache`
- [ ] Replace inline logic in `RenderingPipeline.process_page()` (`pipeline/core.py:196-201`)
- [ ] Replace inline logic in `IncrementalOrchestrator.find_work_early()` (`incremental.py:366`)
- [ ] Add `cache_bypass_hits` and `cache_bypass_misses` counters to `BuildStats`
- [ ] Log cache bypass summary in `rebuild_complete` event

**Test:** Existing tests should pass; add unit test for `should_bypass()` helper.

### Phase 2: Structural Change Signal (~1 hour)

**Goal:** Make structural changes explicit, not inferred.

**Tasks:**
- [ ] Add `structural_changed: bool = False` parameter to `Site.build()` and `BuildOrchestrator.build()`
- [ ] Thread through to `IncrementalOrchestrator.find_work_early()`
- [ ] In `BuildHandler._trigger_build()`, set `structural_changed=True` when `pending_event_types & {"created", "deleted", "moved"}`
- [ ] Log `structural_changed` in `rebuild_triggered` event

**Test:** Integration test: create new file → verify full discovery runs.

### Phase 3: Extended Frontmatter Diff (~2 hours)

**Goal:** Body-only `_index.md` edits don't trigger section-wide rebuilds.

**Tasks:**
- [ ] In `find_work_early()`, check ALL `_index.md` files for metadata hash changes (not just nav-changed)
- [ ] Extract nav-affecting keys (`title`, `slug`, `hidden`, `draft`, `weight`, `menu`, `cascade`) into constant
- [ ] Only trigger section rebuild if nav-affecting keys actually changed
- [ ] Keep prev/next propagation logic unchanged

**Test:**
- Body-only section index edit → only that page rebuilds
- Title change in section index → section pages rebuild

### Phase 4: Test Suite & Documentation (~2 hours)

**Goal:** Comprehensive test coverage for invariants.

**Unit tests** (extend `tests/unit/orchestration/test_incremental_orchestrator.py`):
- [ ] `test_should_bypass_changed_sources` - bypass when in changed_sources
- [ ] `test_should_bypass_is_changed` - bypass when hash differs
- [ ] `test_should_bypass_both_false` - cache hit when neither condition
- [ ] `test_frontmatter_body_only_no_section_rebuild`
- [ ] `test_frontmatter_nav_change_triggers_section_rebuild`

**Integration tests** (using `tests/roots/test-basic/`):
- [ ] `test_body_only_page_edit` - single page rebuilds
- [ ] `test_body_only_section_index_edit` - section index only rebuilds
- [ ] `test_nav_changing_section_index_edit` - section pages rebuild
- [ ] `test_css_only_change` - reload-css sent, no page rebuild
- [ ] `test_revert_to_same_content` - page rebuilds (not stale)
- [ ] `test_file_create_triggers_structural` - full discovery

**Documentation:**
- [ ] Add "Incremental Build Invariants" section to dev docs
- [ ] Document the cache bypass contract

### Phase 5: Cleanup (~1 hour)

**Goal:** Remove legacy patterns replaced by new invariants.

**Tasks:**
- [ ] Remove any remaining ad-hoc `skip_cache` flags not using the helper
- [ ] Consolidate nav-affecting frontmatter keys into single constant (used by both `build_handler.py` and `incremental.py`)
- [ ] Review and remove deprecated comments referencing old patterns

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Metadata hash compare overhead | Low | Low | Already implemented; cheap YAML serialize + hash |
| Cache miss on first build after upgrade | Low | Low | Falls back to conservative (full) rebuild |
| Log volume increase | Medium | Low | Keep path lists truncated (already capped to 5-10) |
| Breaking existing incremental behavior | Medium | High | Comprehensive test suite in Phase 4 |

## Success Metrics

1. **Body-only Markdown edits** rebuild only the target page (plus nav adjacency), not entire sections
2. **Nav changes** rebuild only affected sections, not whole site
3. **Zero stale renders** after edits without manual refresh
4. **Observability:** Logs show cache bypass hits/misses, change classification, reload sends
5. **Test coverage:** All invariants have explicit test cases

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Per-key nav hashes? | No (for now) | Metadata hash comparison is fast enough; per-key adds complexity |
| Max-pages-per-incremental safeguard? | No | Section-level filtering already limits blast radius |
| Reload payload with page count? | Yes | Add `changed_pages_count` to reload payload for debugging |

## Open Questions

1. **Should `structural_changed` disable all caches?** Current thinking: No, only triggers full content discovery. Caches remain valid for unchanged files.

2. **Should we distinguish "nav-changed" from "cascade-changed"?** Cascade changes affect descendants; nav changes affect siblings. May need separate handling for precision.

## References

- `bengal/orchestration/incremental.py` - IncrementalOrchestrator
- `bengal/rendering/pipeline/core.py` - RenderingPipeline.process_page()
- `bengal/server/build_handler.py` - BuildHandler._trigger_build()
- `bengal/cache/build_cache/parsed_content_cache.py` - metadata_hash storage
- `tests/unit/orchestration/test_incremental_orchestrator.py` - existing test patterns
- `tests/roots/test-basic/` - integration test fixtures
