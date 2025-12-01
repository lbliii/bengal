# Plan: BuildOrchestrator Phase Method Extraction

**RFC**: [rfc-build-orchestrator-refactoring.md](rfc-build-orchestrator-refactoring.md)  
**Branch**: `refactor/build-orchestrator-phases`  
**Estimated Effort**: 3-4 days  
**Risk Level**: Low  

---

## Overview

Extract the 894-line `BuildOrchestrator.build()` method into focused `_phase_*` methods. This is a pure refactoring with no behavior changes.

**Success Criteria**:
- [ ] `build()` reduced from 894 lines to <100 lines
- [ ] 15 focused `_phase_*` methods (~50-100 lines each)
- [ ] All existing tests pass
- [ ] No new abstractions introduced

---

## Phase 1: Setup & First Extraction (Day 1)

### Task 1.1: Verify/Create BuildContext
**File**: `bengal/utils/build_context.py`  
**Status**: ⬜ Pending

Check if `BuildContext` dataclass exists with required fields. If not, create or extend it.

**Required fields**:
```python
@dataclass
class BuildContext:
    site: Site
    pages: list[Page]
    tracker: DependencyTracker | None
    stats: BuildStats
    profile: BuildProfile
    progress_manager: Any | None
    reporter: Any | None
    cli: CLIOutput
    cache: BuildCache | None
    incremental: bool
    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    affected_sections: set[str] | None
```

**Commit**: `orchestration: verify BuildContext has all fields needed for phase extraction`

---

### Task 1.2: Extract `_phase_fonts`
**File**: `bengal/orchestration/build.py`  
**Lines**: 188-209  
**Status**: ⬜ Pending

Extract Phase 0.5 (Font Processing) into `_phase_fonts(self, ctx: BuildContext)`.

**Before** (in `build()`):
```python
# Phase 0.5: Font Processing (before asset discovery)
if "fonts" in self.site.config:
    with self.logger.phase("fonts"):
        # ~20 lines of font processing
```

**After**:
```python
def _phase_fonts(self, ctx: BuildContext) -> None:
    """Phase 1: Font processing (download Google Fonts, generate CSS)."""
    if "fonts" not in self.site.config:
        return

    with self.logger.phase("fonts"):
        fonts_start = time.time()
        # ... existing logic ...
        self.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
```

**Verification**:
- [ ] Run `pytest tests/` - all tests pass
- [ ] Run `bengal build` on test site - same output

**Commit**: `orchestration: extract _phase_fonts from build() as proof of concept`

---

## Phase 2: Extract Discovery & Setup Phases (Day 2)

### Task 2.1: Extract `_phase_discovery`
**File**: `bengal/orchestration/build.py`  
**Lines**: 211-242  
**Status**: ⬜ Pending

Extract Phase 1 (Content Discovery).

**Commit**: `orchestration: extract _phase_discovery from build()`

---

### Task 2.2: Extract `_phase_cache_metadata`
**File**: `bengal/orchestration/build.py`  
**Lines**: 244-274  
**Status**: ⬜ Pending

Extract Phase 1.25 (Cache Discovery Metadata).

**Commit**: `orchestration: extract _phase_cache_metadata from build()`

---

### Task 2.3: Extract `_phase_config_check`
**File**: `bengal/orchestration/build.py`  
**Lines**: 276-315  
**Status**: ⬜ Pending

Extract config change checking logic.

**Commit**: `orchestration: extract _phase_config_check from build()`

---

### Task 2.4: Extract `_phase_cleanup_deleted`
**File**: `bengal/orchestration/build.py`  
**Lines**: 300-308  
**Status**: ⬜ Pending

Extract Phase 1.5 (Clean up deleted files).

**Commit**: `orchestration: extract _phase_cleanup_deleted from build()`

---

### Task 2.5: Extract `_phase_incremental_filter`
**File**: `bengal/orchestration/build.py`  
**Lines**: 317-423  
**Status**: ⬜ Pending

Extract Phase 2 (Determine what to build). This is a larger phase (~100 lines).

**Commit**: `orchestration: extract _phase_incremental_filter from build()`

---

### Task 2.6: Run Tests - Checkpoint 1
**Status**: ⬜ Pending

- [ ] Run `pytest tests/` - all tests pass
- [ ] Run `pytest tests/integration/` - integration tests pass
- [ ] Run `bengal build` on `site/` - same output as before

**Commit**: (none - verification only)

---

## Phase 3: Extract Content Processing Phases (Day 2-3)

### Task 3.1: Extract `_phase_sections`
**File**: `bengal/orchestration/build.py`  
**Lines**: 425-461  
**Status**: ⬜ Pending

Extract Phase 3 (Section Finalization).

**Commit**: `orchestration: extract _phase_sections from build()`

---

### Task 3.2: Extract `_phase_taxonomies`
**File**: `bengal/orchestration/build.py`  
**Lines**: 463-506  
**Status**: ⬜ Pending

Extract Phase 4 (Taxonomies & Dynamic Pages).

**Commit**: `orchestration: extract _phase_taxonomies from build()`

---

### Task 3.3: Extract `_phase_taxonomy_index`
**File**: `bengal/orchestration/build.py`  
**Lines**: 508-552  
**Status**: ⬜ Pending

Extract Phase 4.5 (Save Taxonomy Index).

**Commit**: `orchestration: extract _phase_taxonomy_index from build()`

---

### Task 3.4: Extract `_phase_menus`
**File**: `bengal/orchestration/build.py`  
**Lines**: 554-567  
**Status**: ⬜ Pending

Extract Phase 5 (Menus).

**Commit**: `orchestration: extract _phase_menus from build()`

---

### Task 3.5: Extract `_phase_related_posts`
**File**: `bengal/orchestration/build.py`  
**Lines**: 569-614 (First "Phase 5.5")  
**Status**: ⬜ Pending

Extract first Phase 5.5 (Related Posts Index). **Renumber to Phase 6**.

**Commit**: `orchestration: extract _phase_related_posts from build(); renumber to Phase 6`

---

### Task 3.6: Extract `_phase_query_indexes`
**File**: `bengal/orchestration/build.py`  
**Lines**: 616-649 (Second "Phase 5.5")  
**Status**: ⬜ Pending

Extract second Phase 5.5 (Query Indexes). **Renumber to Phase 7**.

**Commit**: `orchestration: extract _phase_query_indexes from build(); renumber to Phase 7`

---

### Task 3.7: Run Tests - Checkpoint 2
**Status**: ⬜ Pending

- [ ] Run `pytest tests/` - all tests pass
- [ ] Run `bengal build --incremental` - incremental builds work

**Commit**: (none - verification only)

---

## Phase 4: Extract Rendering Phases (Day 3)

### Task 4.1: Extract `_phase_update_pages_list`
**File**: `bengal/orchestration/build.py`  
**Lines**: 651-678  
**Status**: ⬜ Pending

Extract Phase 6 (Update filtered pages list). **Renumber to Phase 8**.

**Commit**: `orchestration: extract _phase_update_pages_list from build()`

---

### Task 4.2: Extract `_phase_assets`
**File**: `bengal/orchestration/build.py`  
**Lines**: 680-707  
**Status**: ⬜ Pending

Extract Phase 7 (Process Assets). **Renumber to Phase 9**.

**Commit**: `orchestration: extract _phase_assets from build()`

---

### Task 4.3: Extract `_phase_render`
**File**: `bengal/orchestration/build.py`  
**Lines**: 709-792  
**Status**: ⬜ Pending

Extract Phase 8 (Render Pages). This is a larger phase (~80 lines). **Renumber to Phase 10**.

**Commit**: `orchestration: extract _phase_render from build()`

---

### Task 4.4: Extract `_phase_update_site_pages`
**File**: `bengal/orchestration/build.py`  
**Lines**: 794-836  
**Status**: ⬜ Pending

Extract Phase 8.4 (Update site.pages with rendered pages). **Renumber to Phase 11**.

**Commit**: `orchestration: extract _phase_update_site_pages from build()`

---

### Task 4.5: Extract `_phase_track_assets`
**File**: `bengal/orchestration/build.py`  
**Lines**: 838-869  
**Status**: ⬜ Pending

Extract Phase 8.5 (Track Asset Dependencies). **Renumber to Phase 12**.

**Commit**: `orchestration: extract _phase_track_assets from build()`

---

### Task 4.6: Run Tests - Checkpoint 3
**Status**: ⬜ Pending

- [ ] Run `pytest tests/` - all tests pass
- [ ] Run `bengal build` on `site/` - verify rendered output

**Commit**: (none - verification only)

---

## Phase 5: Extract Final Phases (Day 3)

### Task 5.1: Extract `_phase_postprocess`
**File**: `bengal/orchestration/build.py`  
**Lines**: 871-898 (First "Phase 9")  
**Status**: ⬜ Pending

Extract first Phase 9 (Post-processing). **Renumber to Phase 13**.

**Commit**: `orchestration: extract _phase_postprocess from build(); renumber to Phase 13`

---

### Task 5.2: Extract `_phase_cache_save`
**File**: `bengal/orchestration/build.py`  
**Lines**: 901-905 (Second "Phase 9")  
**Status**: ⬜ Pending

Extract second Phase 9 (Update cache). **Renumber to Phase 14**.

**Commit**: `orchestration: extract _phase_cache_save from build(); renumber to Phase 14`

---

### Task 5.3: Extract `_phase_collect_stats`
**File**: `bengal/orchestration/build.py`  
**Lines**: 907-922  
**Status**: ⬜ Pending

Extract stats collection logic. **Phase 15**.

**Commit**: `orchestration: extract _phase_collect_stats from build()`

---

### Task 5.4: Extract `_phase_health_check`
**File**: `bengal/orchestration/build.py`  
**Lines**: 924-926 (Phase 10)  
**Status**: ⬜ Pending

Extract Phase 10 (Health Check). **Renumber to Phase 16**.

**Commit**: `orchestration: extract _phase_health_check from build(); renumber to Phase 16`

---

### Task 5.5: Extract `_phase_finalize`
**File**: `bengal/orchestration/build.py`  
**Lines**: 928-959  
**Status**: ⬜ Pending

Extract finalization logic (memory metrics, logging). **Phase 17**.

**Commit**: `orchestration: extract _phase_finalize from build()`

---

### Task 5.6: Run Tests - Final Verification
**Status**: ⬜ Pending

- [ ] Run `pytest tests/` - ALL tests pass
- [ ] Run `pytest tests/integration/` - integration tests pass
- [ ] Run `bengal build` on `site/` - full build works
- [ ] Run `bengal build --incremental` - incremental works
- [ ] Run `bengal serve` - dev server works

**Commit**: (none - verification only)

---

## Phase 6: Polish & Documentation (Day 4)

### Task 6.1: Update `build()` Method Structure
**File**: `bengal/orchestration/build.py`  
**Status**: ⬜ Pending

Ensure `build()` is now a clean sequence of phase calls:

```python
def build(self, ...) -> BuildStats:
    """Execute full build pipeline."""
    ctx = self._setup_build_context(...)

    # Phase 1-5: Discovery & Setup
    self._phase_fonts(ctx)
    self._phase_discovery(ctx)
    self._phase_cache_metadata(ctx)
    self._phase_config_check(ctx)
    self._phase_cleanup_deleted(ctx)
    self._phase_incremental_filter(ctx)

    # Early exit if no changes
    if ctx.stats.skipped:
        return ctx.stats

    # Phase 6-12: Content Processing
    self._phase_sections(ctx)
    self._phase_taxonomies(ctx)
    self._phase_taxonomy_index(ctx)
    self._phase_menus(ctx)
    self._phase_related_posts(ctx)
    self._phase_query_indexes(ctx)
    self._phase_update_pages_list(ctx)

    # Phase 13-17: Rendering & Finalization
    self._phase_assets(ctx)
    self._phase_render(ctx)
    self._phase_update_site_pages(ctx)
    self._phase_track_assets(ctx)
    self._phase_postprocess(ctx)
    self._phase_cache_save(ctx)
    self._phase_collect_stats(ctx)
    self._phase_health_check(ctx)
    self._phase_finalize(ctx)

    return ctx.stats
```

**Commit**: `orchestration: finalize build() as clean phase sequence`

---

### Task 6.2: Add Docstrings to All Phase Methods
**File**: `bengal/orchestration/build.py`  
**Status**: ⬜ Pending

Add comprehensive docstrings to each `_phase_*` method explaining:
- What the phase does
- Key side effects
- Dependencies on other phases

**Commit**: `orchestration: add docstrings to all _phase_* methods`

---

### Task 6.3: Update Architecture Documentation
**File**: `architecture/core/orchestration.md`  
**Status**: ⬜ Pending

Update docs to reflect new phase structure:
- Add phase method list
- Update build flow diagram
- Document phase dependencies

**Commit**: `docs(architecture): update orchestration.md with phase method structure`

---

### Task 6.4: Final Code Review Checklist
**Status**: ⬜ Pending

- [ ] All phases extracted
- [ ] No duplicate phase numbers
- [ ] All tests pass
- [ ] Docstrings complete
- [ ] `build()` method is <100 lines
- [ ] No new abstractions introduced
- [ ] Type hints preserved

**Commit**: (none - review only)

---

### Task 6.5: Update Changelog
**File**: `changelog.md`  
**Status**: ⬜ Pending

Add entry:
```markdown
### Changed
- Refactored `BuildOrchestrator.build()` from 894 lines to ~80 lines by extracting 17 focused `_phase_*` methods
- Fixed duplicate phase numbers (two "Phase 5.5", two "Phase 9")
- Improved code organization for contributor experience
```

**Commit**: `docs: add build orchestrator refactoring to changelog`

---

## Summary

| Phase | Tasks | Days | Focus |
|-------|-------|------|-------|
| 1 | 1.1-1.2 | Day 1 | Setup & first extraction (proof of concept) |
| 2 | 2.1-2.6 | Day 2 | Discovery & setup phases |
| 3 | 3.1-3.7 | Day 2-3 | Content processing phases |
| 4 | 4.1-4.6 | Day 3 | Rendering phases |
| 5 | 5.1-5.6 | Day 3 | Final phases |
| 6 | 6.1-6.5 | Day 4 | Polish & documentation |

**Total Tasks**: 23  
**Total Commits**: ~20 atomic commits  
**Verification Checkpoints**: 4  

---

## Pre-Implementation Checklist

Before starting:
- [ ] Create branch: `git checkout -b refactor/build-orchestrator-phases`
- [ ] Run baseline tests: `pytest tests/`
- [ ] Build test site: `bengal build` (save output for comparison)
- [ ] Review `BuildContext` dataclass fields

---

## Post-Implementation Checklist

After completing:
- [ ] All 23 tasks completed
- [ ] All tests pass
- [ ] `build()` is <100 lines
- [ ] 17 `_phase_*` methods created
- [ ] Changelog updated
- [ ] Architecture docs updated
- [ ] PR created for review
- [ ] Move this plan to `plan/implemented/`
