# Cascade System Refactor & Incremental Build Fix

**Date**: October 16, 2025  
**Status**: DRAFT - Ready for review  
**Priority**: High (blocks incremental build fix, prevents maintenance debt)  
**Estimated Time**: 4-5 hours  
**Risk Level**: Medium (touches core build logic, but well-tested)

---

## Overview

The cascade system works correctly but has three interconnected problems:

1. **Code Duplication**: Identical implementation in `Site` and `ContentOrchestrator`
2. **Performance**: O(n²) root-level cascade detection runs twice
3. **Incremental Build Bug**: Cascade changes don't trigger child page rebuilds in `bengal serve`

This plan consolidates the logic, fixes performance, and adds incremental build support.

---

## Problem Analysis

### 1. Code Duplication (Lines 81)

**Locations**:
- `bengal/core/site.py:377-457` - `_apply_cascades()` + `_apply_section_cascade()`
- `bengal/orchestration/content.py:193-343` - Identical copies

**Why this is bad**:
- Bug in one place needs fixing in both
- They could diverge and cause inconsistent behavior
- Tests only verify Site version
- Maintenance burden

**Solution**: Extract into shared utility class

---

### 2. O(n²) Performance Issue (Current: O(sections × pages) twice)

**Current code** (lines 400-402, 415-421 in site.py):
```python
# First loop - checking if page is top-level
for page in self.pages:
    is_top_level = not any(page in section.pages for section in self.sections)
    #              ^^^ O(sections) search for each page
    if is_top_level and "cascade" in page.metadata:
        # Found cascade

# Second loop - applying same check again
for page in self.pages:
    is_top_level = not any(page in section.pages for section in self.sections)
    #              ^^^ Same O(sections) search again!
```

**Cost**:
- 1000 pages × 50 sections = 50,000 searches
- Done twice = 100,000 searches
- For large sites: unacceptable

**Solution**: Pre-compute set of pages in sections once

---

### 3. Incremental Build Cascade Bug (Known issue)

**Current behavior**:
```
User changes: content/docs/_index.md (cascade metadata)
↓
Incremental system detects: docs/_index.md changed
↓
Marks for rebuild: Only docs/_index.md
↓
Does NOT mark for rebuild: docs/guide.md, docs/tutorial.md, etc.
↓
Result: Their cached HTML is stale (old cascade values)
```

**Root cause**: 
- `IncrementalOrchestrator.find_work_early()` doesn't understand cascade dependencies
- When section index changes, descendants should be auto-marked for rebuild

**Solution**: Add cascade dependency tracking to incremental system

---

## Implementation Plan

### Phase 1: Extract Shared Cascade Utility (1 hour)

**Location**: Create `bengal/core/cascade_engine.py`

**New class**:
```python
class CascadeEngine:
    """Isolated cascade application logic (no Site/Orchestrator coupling)."""
    
    def __init__(self, pages: list[Page], sections: list[Section]):
        """Initialize with page and section lists."""
        # Pre-compute for O(1) lookups
        self._pages_in_sections = self._compute_pages_in_sections(sections)
        self.pages = pages
        self.sections = sections
    
    def _compute_pages_in_sections(self, sections) -> set[Page]:
        """Pre-compute set of all pages that belong to any section."""
        pages = set()
        for section in sections:
            pages.update(section.get_all_pages())
        return pages
    
    def is_top_level_page(self, page: Page) -> bool:
        """O(1) check if page is top-level (not in any section)."""
        return page not in self._pages_in_sections
    
    def apply(self) -> None:
        """Apply all cascades to site."""
        # Logic from Site._apply_cascades(), but using pre-computed set
        # This runs ONCE from ContentOrchestrator
```

**Changes**:
- ✅ Move `_apply_cascades()` logic into `CascadeEngine`
- ✅ Move `_apply_section_cascade()` helper into engine
- ✅ Use pre-computed `_pages_in_sections` set (O(1) lookups)
- ✅ Remove duplicate implementations

**Files to modify**:
- Create: `bengal/core/cascade_engine.py` (150 lines)
- Update: `bengal/core/site.py` (remove duplication)
- Update: `bengal/orchestration/content.py` (use engine)
- Update: `tests/unit/test_cascade.py` (adjust imports, keep tests)

**Tests**:
- Run existing cascade tests (verify no behavior change)
- Add performance test: verify O(n) not O(n²)

---

### Phase 2: Add Cascade Dependency Tracking (2 hours)

**Location**: `bengal/orchestration/incremental.py` - `IncrementalOrchestrator.find_work_early()`

**New method**:
```python
def _find_cascade_affected_pages(self, index_page: Page) -> set[Path]:
    """
    Find all pages affected by cascade change in an index page.
    
    When content/docs/_index.md cascade changes, return paths of all
    pages in docs/ and subsections (docs/advanced/, etc.).
    
    Args:
        index_page: The _index.md or index.md page with cascade
    
    Returns:
        Set of source paths to rebuild
    """
    affected = set()
    
    # Find the section this index page belongs to
    for section in self.site.sections:
        if section.index_page == index_page:
            # Get all regular pages (not sections) in this section recursively
            for page in section.regular_pages_recursive:
                if not page.metadata.get("_generated"):
                    affected.add(page.source_path)
            break
    
    return affected
```

**Integration into `find_work_early()`**:
```python
# After detecting changed pages, check for cascade changes
for changed_path in list(pages_to_rebuild):  # Snapshot
    page_obj = self._find_page_by_path(changed_path)
    
    if page_obj and self._is_index_page(page_obj):
        # Check if this page has cascade metadata
        old_metadata = self.cache.get_old_page_metadata(changed_path)
        new_cascade = page_obj.metadata.get("cascade", {})
        old_cascade = old_metadata.get("cascade", {}) if old_metadata else {}
        
        if new_cascade != old_cascade:
            # Cascade changed - mark all descendants for rebuild
            affected = self._find_cascade_affected_pages(page_obj)
            pages_to_rebuild.update(affected)
            
            if verbose:
                change_summary["Cascade affects"].append(
                    f"{changed_path.name}: {len(affected)} pages"
                )
```

**Handle edge cases**:

1. **Root-level cascade change** (from top-level `content/index.md`):
```python
# If this is a root-level page with cascade
if self._is_root_level_page(page_obj):
    # Mark ALL non-generated pages for rebuild
    for page in self.site.pages:
        if not page.metadata.get("_generated"):
            pages_to_rebuild.add(page.source_path)
```

2. **Cascade removal**: Handled automatically (old != new)

3. **Nested cascade changes**: Parent and child both affected
```python
# Already works - child section pages marked when child cascade changes
```

**Files to modify**:
- Update: `bengal/orchestration/incremental.py` (add methods + integration)

**Tests**:
- Add unit tests for cascade dependency detection
- Test nested section cascade changes
- Test root-level cascade changes
- Test performance (large site with many affected pages)

---

### Phase 3: Add Cascade Logging & Monitoring (1 hour)

**Goal**: Make cascade issues debuggable

**Changes to CascadeEngine**:
```python
def apply(self, verbose: bool = False) -> dict[str, int]:
    """
    Apply cascades and return statistics.
    
    Returns:
        {
            "pages_processed": 1000,
            "pages_with_cascade": 850,
            "cascade_keys_applied": {"layout": 450, "type": 800, ...},
            "root_cascade_pages": 150,
        }
    """
    stats = {...}
    
    # Log each cascade application
    for page in section.pages:
        applied_keys = []
        for key, value in accumulated_cascade.items():
            if key not in page.metadata:
                page.metadata[key] = value
                applied_keys.append(key)
        
        if applied_keys and verbose:
            logger.debug(
                "cascade_applied",
                page=page.source_path,
                keys=applied_keys,
                from_section=section.name
            )
    
    return stats
```

**ContentOrchestrator logging**:
```python
def discover(self):
    # ... discovery ...
    
    stats = self._apply_cascades()
    logger.info(
        "cascades_applied",
        pages_processed=stats["pages_processed"],
        pages_affected=stats["pages_with_cascade"],
        root_cascade_pages=stats["root_cascade_pages"],
    )
```

**Files to modify**:
- Update: `bengal/core/cascade_engine.py` (add stats/logging)
- Update: `bengal/orchestration/content.py` (log results)

---

## Phase-by-Phase Execution

### Phase 1: Extract & Deduplicate (1 hour)

**Commits**:
1. `core: extract CascadeEngine from Site and ContentOrchestrator`
   - Add `cascade_engine.py`
   - Pre-compute pages-in-sections set (O(1) lookups)
   - Move logic into engine
   - Tests pass ✅

2. `orchestration: use CascadeEngine in ContentOrchestrator`
   - Replace duplicated code
   - Use pre-computed sets
   - Tests pass ✅

3. `core: remove duplicate _apply_cascades from Site`
   - Site now delegates to engine
   - Backward compatibility maintained
   - Tests pass ✅

---

### Phase 2: Incremental Build Integration (2 hours)

**Commits**:
1. `orchestration(incremental): add cascade dependency tracking`
   - Add `_find_cascade_affected_pages()`
   - Add `_is_index_page()` helper
   - Add `_is_root_level_page()` helper
   - Integrate into `find_work_early()`
   - Unit tests for dependency detection ✅

2. `tests(incremental): add cascade change detection tests`
   - Test root cascade marks all pages
   - Test section cascade marks descendants
   - Test nested cascade changes
   - Test cascade removal
   - All tests pass ✅

---

### Phase 3: Monitoring (1 hour)

**Commit**:
1. `core(cascade): add logging and statistics tracking`
   - Return stats from CascadeEngine
   - Log cascade applications
   - Log summary in ContentOrchestrator
   - Add verbose mode for debugging

---

## Testing Strategy

### Unit Tests (Phase 1)
```bash
pytest tests/unit/core/test_cascade_engine.py -v
# Test: O(1) top-level page checks
# Test: Cascade accumulation through levels
# Test: Override behavior
```

### Unit Tests (Phase 2)
```bash
pytest tests/unit/orchestration/test_incremental_orchestrator.py::TestCascadeDependencyTracking -v
# Test: Cascade change detection
# Test: Affected pages identification
# Test: Root-level cascade handling
# Test: Nested cascade changes
```

### Integration Tests
```bash
pytest tests/integration/test_cascade_integration.py -v
# Test: Full build with cascades
# Test: Incremental build with cascade changes
# Test: Large site performance
```

### Performance Benchmark
```python
# Before: O(n²) for 1000 pages, 50 sections
# Expected: 100,000 searches
# After: O(n) - 1000 searches + cascade application
# Expected: 5-10x faster on large sites
```

---

## Files to Create/Modify

| File | Action | Lines | Impact |
|------|--------|-------|--------|
| `bengal/core/cascade_engine.py` | Create | 150 | New shared logic |
| `bengal/core/site.py` | Modify | -80 | Delegate to engine |
| `bengal/orchestration/content.py` | Modify | -140 | Use engine |
| `bengal/orchestration/incremental.py` | Modify | +80 | Add dependency tracking |
| `tests/unit/core/test_cascade_engine.py` | Create | 100 | Unit tests |
| `tests/unit/orchestration/test_incremental_cascade.py` | Create | 120 | Incremental tests |
| `tests/unit/test_cascade.py` | Modify | Minimal | Adjust imports |

**Net change**: +150 new loc, -220 duplicate removed = cleaner codebase

---

## Rollout Strategy

### Option A: Full Implementation (Recommended)
- All three phases in one PR
- Comprehensive testing
- One code review cycle
- **Time**: 4-5 hours

### Option B: Phase by Phase
- Phase 1 → Phase 2 → Phase 3 (separate PRs)
- Easier to review
- Can merge Phase 1 early (no behavior change, just refactoring)
- **Time**: 5-6 hours (overhead of multiple reviews)

### Option C: Critical Path Only
- Phase 1 (deduplication)
- Phase 2 (incremental fix)
- Skip Phase 3 (monitoring can be added later)
- **Time**: 3-4 hours
- **Trade-off**: Harder to debug cascade issues

**Recommendation**: Option A (full implementation)

---

## Success Criteria

- [ ] All existing cascade tests pass
- [ ] No behavior changes to cascade application
- [ ] O(1) top-level page checks (O(n²) → O(n))
- [ ] Incremental builds rebuild descendants when cascade changes
- [ ] `bengal serve` works correctly with cascade changes
- [ ] Cascade stats logged during discovery
- [ ] No new linter errors
- [ ] Code coverage maintained (>90% for cascade code)

---

## Follow-Up Work

After this PR:

1. **Optimization**: Cache section→pages mapping for even faster lookups
2. **Configuration**: Allow disabling cascade per-field
3. **Validation**: Warn on invalid cascade values
4. **Documentation**: Add cascade troubleshooting guide
5. **Monitoring**: Dashboard to visualize cascade propagation

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing cascade behavior | HIGH | Comprehensive tests before merge |
| Performance regression | MEDIUM | Benchmark before/after |
| Incremental build conflicts | MEDIUM | Test with live server workflow |
| Code complexity | LOW | CascadeEngine is self-contained |

**Overall Risk**: Medium (but well-mitigated by testing)

---

## Time Breakdown

| Phase | Task | Time |
|-------|------|------|
| 1 | Extract CascadeEngine | 45 min |
| 1 | Refactor Site + ContentOrchestrator | 15 min |
| 2 | Add incremental tracking | 60 min |
| 2 | Write incremental tests | 60 min |
| 3 | Add logging/stats | 30 min |
| - | Testing & debugging | 30 min |
| **Total** | | **4-5 hours** |

---

## Approval Checklist

- [ ] Review problem analysis (correct?)
- [ ] Approve Phase 1 approach (CascadeEngine design?)
- [ ] Approve Phase 2 approach (incremental detection logic?)
- [ ] Confirm testing strategy
- [ ] Choose rollout strategy (A/B/C)
- [ ] Ready to implement?
