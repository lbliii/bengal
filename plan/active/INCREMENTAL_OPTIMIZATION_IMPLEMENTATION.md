
# Incremental Build Optimization Implementation Plan

## Overview
Implementing 4 targeted optimizations to improve incremental build performance from 1.33x (518ms) to 10-15x speedup (45-69ms).

## Current Baseline
- **Full build**: 688ms (100 pages)
- **Incremental no-changes**: 315ms (2.18x speedup) ✅
- **Incremental 1-page change**: 518ms (1.33x speedup) ❌

## Optimization Schedule

### Priority 1: Conditional Taxonomy Rebuild (~200ms gain, 4-6x speedup)
**File**: `bengal/orchestration/taxonomy.py` lines 195-254
**Problem**: `_rebuild_taxonomy_structure_from_cache()` always runs O(n) even when no taxonomy changed
**Solution**: Skip rebuild if no affected tags detected

**Steps**:
1. Add condition check before `_rebuild_taxonomy_structure_from_cache(cache)`
2. Only rebuild if `affected_tags` is non-empty OR cache state changed
3. Validate with test: single page change with NO tag changes should skip rebuild

**Expected Result**: 4-6x speedup (estimated 100ms saved)

---

### Priority 2: Selective Section Finalization (~80ms gain, 1.5-2x speedup)
**File**: `bengal/orchestration/build.py` lines 364-394
**Problem**: `sections.finalize_sections()` validates ALL sections for 1-page change
**Solution**: Only finalize sections affected by changed pages

**Steps**:
1. Add parameter to `finalize_sections()` to accept `affected_section_paths`
2. Pass changed page sections from incremental filter
3. Only validate affected sections when incremental

**Expected Result**: 1.5-2x speedup (estimated 80ms saved)

---

### Priority 3: Truly Incremental Related Posts (~150ms gain, 2-3x speedup)
**File**: `bengal/orchestration/build.py` lines 456-492
**Problem**: Related posts updates for ALL pages even if only 1-page changed
**Solution**: Only rebuild related posts index for changed pages

**Steps**:
1. Add condition to skip related posts if not incremental
2. OR only update for affected pages (requires RelatedPostsOrchestrator change)
3. For now: Skip related posts rebuild in incremental mode if <5 pages changed

**Expected Result**: 2-3x speedup (estimated 150ms saved)

---

### Priority 4: Conditional Postprocessing (~70ms gain, 1.2-1.5x speedup)
**File**: `bengal/orchestration/build.py` lines 500+
**Problem**: Sitemap/RSS/validation regenerate for all pages
**Solution**: Conditional regeneration based on change detection

**Steps**:
1. Skip RSS regeneration if no page content changed (check cache)
2. Update sitemap incrementally (remove deleted pages, add new/changed)
3. Skip validation if <5 pages changed

**Expected Result**: 1.2-1.5x speedup (estimated 70ms saved)

---

## Verification Strategy

### After Each Fix:
```bash
cd benchmarks
pytest test_build.py::test_incremental_single_page_change -v --benchmark-only
```

### Expected Timeline:
- **Before**: 518ms (1.33x)
- **After Priority 1**: ~410ms (1.67x)
- **After Priority 1+2**: ~330ms (2.08x)
- **After Priority 1+2+3**: ~180ms (3.82x)
- **After Priority 1+2+3+4**: ~110ms (6.25x) → Target: 10-15x

## Implementation Order
1. **Priority 1** (Taxonomy) - Highest impact, lowest risk
2. **Priority 2** (Sections) - Medium impact, low risk
3. **Priority 3** (Related Posts) - Medium impact, medium risk
4. **Priority 4** (Postprocessing) - Lower impact, medium risk

## Rollback Plan
Each fix is atomic:
- Can be reverted independently if tests fail
- Git commits allow per-fix rollback
- No breaking changes to public APIs

## Success Criteria
- ✅ Single-page incremental build: 5-8x speedup (conservative)
- ✅ No-changes incremental build: Maintains 2.18x speedup
- ✅ All benchmarks pass
- ✅ No regression in full builds
