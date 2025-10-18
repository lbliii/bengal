# Repository Cleanup Plan

**Date:** 2025-10-18  
**Purpose:** Archive completed work, update docs, clean up stale plans

---

## 1. ARCHITECTURE.md Updates Needed

### Update Line 2403-2406: Page Caching Status

**Current:**
```markdown
3. **Page Subset Caching** (Added 2025-10-12)
   - `Site.regular_pages` - cached content pages  
   - `Site.generated_pages` - cached generated pages
   - **Impact**: 50% reduction in equality checks (446K → 223K at 400 pages)
```

**Should be:**
```markdown
3. **Page Subset Caching** (Added 2025-10-12, Completed 2025-10-18)
   - `Site.regular_pages` - cached content pages  
   - `Site.generated_pages` - cached generated pages
   - **Impact**: 75% reduction in equality checks (446K → 112K at 400 pages)
   - **Status**: ✅ All code paths now use cached properties
```

### Update Line 2445-2446: File I/O Status

**Current:**
```markdown
2. **Batch File I/O**: Use `ThreadPoolExecutor` for concurrent reads (~20-30% faster I/O)
3. **Memory-Mapped Reads**: For large files (>100KB) (~10-15% faster)
```

**Should be:**
```markdown
2. ~~**Batch File I/O**~~: ✅ Already implemented
   - Page rendering: Parallel (ThreadPoolExecutor)
   - Asset processing: Parallel (ThreadPoolExecutor)
   - Content discovery: Parallel (ThreadPoolExecutor, 8 workers)
   - Post-processing: Parallel (ThreadPoolExecutor)
3. **Memory-Mapped Reads**: For large files (>100KB) - Low priority, marginal gains
```

### Add New Section: Performance Audit Results (2025-10-18)

After line 2448, add:

```markdown
### Performance Audit (2025-10-18)

**Comprehensive scan revealed:**
- ✅ No O(n²) patterns in codebase
- ✅ All file I/O already parallelized
- ✅ Proper use of sets for O(1) membership checks
- ✅ Dict-based indexes for O(1) lookups
- ✅ Page caching complete across all code paths

**Bottlenecks are CPU-bound, not I/O-bound:**
1. Markdown parsing (40-50%) - already using fastest parser
2. Template rendering (30-40%) - already parallel + cached
3. No remaining algorithmic inefficiencies found

See: `plan/implemented/PERFORMANCE_SCAN_RESULTS.md`
```

---

## 2. Plans to Move to plan/implemented/

These documents represent **completed work** and should be archived:

### Recently Completed (2025-10-18)
- ✅ `PERFORMANCE_FIX_COMPLETE.md` - Page caching complete
- ✅ `PERFORMANCE_AUDIT_RESULTS.md` - Full performance scan done
- ✅ `PERFORMANCE_SCAN_RESULTS.md` - Duplicate/redundant
- ✅ `FILE_IO_BATCHING_ANALYSIS.md` - Analysis complete, no work needed

### Previously Completed (2025-10-12)
- ✅ `OPTIMIZATION_SUMMARY.md` - Initial page caching
- ✅ `IMPLEMENTATION_COMPLETE.md` - Initial performance work
- ✅ `ANSWER_TO_USER.md` - Historical Q&A
- ✅ `FIXES_SUMMARY.md` - Historical bug fixes
- ✅ `FIX_SUMMARY.md` - Duplicate

### Phase Completions
- ✅ `PHASE1_COMPLETION_SUMMARY.md` - Phase 1 done
- ✅ `PHASE2a_FOUNDATION_PROGRESS.md` - Phase 2a done
- ✅ `PHASE2b_COMPLETION.md` - Phase 2b done
- ✅ `PHASE2b_INTEGRATION_STRATEGY.md` - Implemented
- ✅ `PHASE2c1_COMPLETE_SUMMARY.md` - Phase 2c.1 done
- ✅ `PHASE2c2_COMPLETE_SUMMARY.md` - Phase 2c.2 done
- ✅ `SESSION_SUMMARY_PHASE2C_COMPLETE.md` - Session summary
- ✅ `SESSION_SUMMARY_2025-10-16.md` - Session summary

### Feature Implementations
- ✅ `MARIMO_IMPLEMENTATION_COMPLETE.md` - Marimo support complete
- ✅ `hidden-pages-implementation.md` - Hidden pages implemented
- ✅ `cascade-incremental-build-fix.md` - Cascade fix implemented
- ✅ `query-index-implementation-summary.md` - Query indexes implemented

### Bug Fixes & Analysis
- ✅ `BENCHMARK_RESULTS_ANALYSIS.md` - Benchmarks run and analyzed
- ✅ `INCREMENTAL_BUILD_BOTTLENECK_ANALYSIS.md` - Fixed
- ✅ `INCREMENTAL_OPTIMIZATION_IMPLEMENTATION.md` - Implemented
- ✅ `CACHE_INVALIDATION_FIX.md` - Fixed
- ✅ `ATOMIC_WRITE_RACE_CONDITION.md` - Fixed
- ✅ `ASSET_BUG_ANALYSIS.md` - Fixed
- ✅ `BUG_TRACKER_2025-10-15.md` - Historical
- ✅ `CODE_REVIEW_2025-10-16.md` - Historical
- ✅ `CRITICAL_ISSUES.md` - All resolved

### Documentation/Planning
- ✅ `BENCHMARK_SUITE_ENHANCEMENTS.md` - Benchmarks enhanced
- ✅ `STATEFUL_AND_INTEGRATION_TEST_COVERAGE_V0_1_2.md` - Coverage documented
- ✅ `SITE_CREATION_PATTERNS.md` - Patterns documented
- ✅ `API_LINK_INDEX_REFINED.md` - Index working

---

## 3. Plans to Keep in plan/active/

These represent **ongoing or future work**:

### High Priority - Current Work
- `hugo-style-collection-functions.md` - Under consideration for implementation
- `extensible-query-system-design.md` - Query system design (in progress)
- `query-system-practical-examples.md` - Examples for query system
- `query-index-theme-use-cases.md` - Use cases documentation

### Planning & Strategy
- `PHASE2_ARCHITECTURE_OPTIMIZATION_PLAN.md` - Overall Phase 2 plan
- `PHASE2_HANDOFF.md` - Handoff documentation
- `PHASE2c_OVERVIEW.md` - Phase 2c overview
- `decoupling-roadmap.md` - Future architecture work
- `build-soundness-plan.md` - Future hardening work
- `feature-solidification-plan.md` - Future solidification

### Technical Decisions
- `python-3.13-feature-adoption.md` - Python 3.13+ features
- `python-3.13-parallel-strategy.md` - Parallelism strategy
- `free-threaded-parallelism-opportunities.md` - Free-threading analysis
- `jit-adoption-decision.md` - JIT analysis

### Future Features
- `modern-executable-docs.md` - Future notebook integration
- `notebook-support-analysis.md` - Notebook analysis
- `marimo-support-analysis.md` - Marimo analysis (keep for reference)
- `github-notebook-directive.md` - GitHub notebook directive
- `marimo-implementation-plan.md` - Original plan (can archive)
- `docs-scale-roadmap.md` - Scaling plan
- `MOTION_STRATEGY.md` - Motion integration
- `OUTPUT_FORMATS.md` - Output format plan
- `TEST_PLAN_baseurl_portability.md` - Test plan
- `cascade-system-refactor.md` - Future refactor

### Reference Documents
- `PERFORMANCE_REALITY_CHECK.md` - Keep for reference
- `PYTHON_PERFORMANCE_CONTEXT.md` - Keep for reference
- `SCALE_DEGRADATION_ANALYSIS.md` - Keep for analysis reference
- `SPHINX_MIGRATION_CASE.md` - Keep for migration reference
- `REAL_USER_CASE_STUDY.md` - Keep for user stories
- `CURRENT_STATUS.md` - Update regularly
- `QUICK_SUMMARY.md` - Update regularly

### Possibly Stale/Review
- `PHASE2c_CACHE_USAGE_PLAN.md` - May be redundant with completion
- `PHASE2c_BENCHMARK_RESULTS.md` - May be redundant with completion
- `CACHE_STRATEGY_PROPOSAL.md` - Check if implemented
- `BUG_BASH_PROGRESS.md` - Check if still relevant
- `BUG_FIX_SESSION_SUMMARY.md` - Probably archive
- `FIX_TEST_DRIVEN_COMPROMISES.md` - Probably archive
- `IMPROVED_MESSAGING.md` - Check status
- `INCREMENTAL_BUILD_FIX.md` - Probably archive (fixed)
- `INCREMENTAL_BUILD_BUG_ROOT_CAUSE.md` - Probably archive (fixed)
- `FINAL_BUG_STATUS.md` - Check if still relevant
- `2025-10-15-build-context-and-incremental-bridge.md` - Check status
- `FUTURE_REFACTOR_TEST_HELPERS.md` - Keep or archive?

---

## 4. CHANGELOG Update Needed

Add entry for next release (v0.1.3 or v0.2.0):

```markdown
## [Unreleased]

### Performance
- Completed page caching optimization (75% reduction in equality checks)
- All file I/O operations now fully parallelized
- Comprehensive performance audit: no O(n²) patterns remaining
- Fixed 5 remaining manual page iterations to use cached properties

### Documentation
- Updated ARCHITECTURE.md with performance audit results
- Archived 40+ completed planning documents
- Cleaned up stale implementation plans
```

---

## 5. Execution Plan

```bash
# 1. Create plan/implemented/ directory if needed
mkdir -p plan/implemented

# 2. Move completed plans (do this carefully, one at a time to review)
git mv plan/active/PERFORMANCE_FIX_COMPLETE.md plan/implemented/
git mv plan/active/PERFORMANCE_AUDIT_RESULTS.md plan/implemented/
# ... etc for all completed plans

# 3. Update ARCHITECTURE.md
# (edit file with changes documented above)

# 4. Update CHANGELOG.md
# (add entry for next release)

# 5. Commit
git add -A
git commit -m "docs: complete performance audit cleanup and archive 40+ completed plans"
```

---

## 6. Future Cleanup Tasks

- Review `plan/completed/` for very old plans that could be deleted
- Consider moving benchmark results to a separate `benchmarks/results/` directory
- Review test coverage documents for staleness
- Update README if performance numbers changed significantly
