# Bengal SSG - Strategic Plan & Next Steps

**Date:** October 3, 2025  
**Current Status:** Performance audit complete, incremental build issue identified  
**Decision Point:** What to work on next?

---

## 🔍 Current State Analysis

### ✅ What's Working Well

1. **Core SSG Architecture** ✅ EXCELLENT
   - Clean, modular design
   - Type-safe, well-documented
   - No linter errors
   - ~3,500 lines of quality code

2. **Full Build Performance** ✅ MEETS ALL TARGETS
   - Small sites (10 pages): 0.293s → **Target: <1s** ✅
   - Medium sites (100 pages): 1.655s → **Target: 1-5s** ✅
   - Large sites (500 pages): 7.953s → **Target: 5-15s** ✅

3. **Parallel Processing** ✅ VALIDATED
   - Assets: 4.21x speedup (100 assets) ✅
   - Post-processing: 2.01x speedup ✅
   - All benchmarks passing

4. **Default Theme** ✅ COMPLETE
   - Responsive, accessible, modern
   - Dark mode, pagination, mobile nav
   - SEO optimized

5. **Benchmarking Infrastructure** ✅ NEW
   - 3 comprehensive benchmark suites
   - Parallel processing benchmark
   - Incremental build benchmark
   - Full build benchmark

### ⚠️ Critical Issue Found: Incremental Builds

**Expected:** 50-900x speedup  
**Actual:** 2.4-2.6x speedup ❌

**Root Cause Identified:** `site.py` lines 547-560
```python
# When ANY page with tags changes, rebuild ALL generated pages
if has_taxonomy_changes:
    for page in self.pages:
        if page.metadata.get('_generated'):
            pages_to_rebuild.add(page.source_path)
```

**Impact:**
- Small site (10 pages): Rebuilds 5-6 pages instead of 1
- Medium site (50 pages): Rebuilds 21-22 pages instead of 1
- Large site (100 pages): Rebuilds 41-42 pages instead of 1

**This is the #1 blocker to achieving the promised 50-900x speedup.**

---

## 📊 Performance Breakdown

### Full Build Time Distribution (500 pages):
- **Rendering: 98.0%** ← Main bottleneck
- Discovery: 1.0%
- Assets: 0.8%
- Post-processing: 0.3%

**Key Insight:** Discovery, assets, and post-processing are already optimal. Further speedup requires either:
1. Optimizing rendering (complex, diminishing returns)
2. Fixing incremental builds (high impact, clear path)

---

## 🎯 Three Strategic Options

### Option A: Fix Incremental Builds (HIGH IMPACT)
**Goal:** Achieve promised 50-900x speedup  
**Effort:** 4-6 hours  
**Confidence:** High (clear root cause identified)

**Tasks:**
1. Implement smart generated page dependency tracking
2. Only rebuild tag pages when their specific tags change
3. Only rebuild archives when section membership changes
4. Track pagination page dependencies properly
5. Update benchmarks to validate 50-900x claim

**Impact:**
- ✅ Validates the 50-900x performance claim
- ✅ Makes incremental builds truly useful
- ✅ Critical for large site support (1000+ pages)
- ✅ Competitive with Hugo's incremental builds

**Risk:** Low (well-understood problem, clear solution)

---

### Option B: Optimize Rendering (MEDIUM IMPACT)
**Goal:** Speed up full builds further  
**Effort:** 8-12 hours  
**Confidence:** Medium (many unknowns)

**Tasks:**
1. Cache parsed Markdown AST
2. Pre-compile Jinja templates
3. Optimize markdown parsing
4. Profile rendering pipeline for hotspots

**Impact:**
- ⚠️ Maybe 1.5-2x speedup (diminishing returns)
- ⚠️ Full builds already meet targets
- ⚠️ Adds complexity to codebase

**Risk:** Medium (may not achieve meaningful speedup)

---

### Option C: Documentation & Polish (HIGH VALUE)
**Goal:** Make Bengal usable by others  
**Effort:** 12-16 hours  
**Confidence:** High (straightforward work)

**Tasks:**
1. Build comprehensive docs site (using Bengal itself)
2. Write user guides (Getting Started, Configuration, Themes)
3. Create 3-4 example sites
4. API reference documentation
5. Plugin development guide

**Impact:**
- ✅ Makes Bengal accessible to users
- ✅ Demonstrates Bengal's capabilities
- ✅ Drives adoption
- ⚠️ Doesn't fix the incremental build issue

**Risk:** Low (just needs time and effort)

---

## 💡 Recommended Path: Option A + Option C

### Phase 1: Fix Incremental Builds (Week 1)
**Why First?**
- Critical blocker for large sites
- Performance claim currently unvalidated
- Clear path to solution
- High confidence we can fix it

**Deliverables:**
1. Smart dependency tracking for generated pages
2. Granular tag page rebuilding
3. Updated benchmarks showing 50-900x speedup
4. Documentation of incremental build behavior

**Success Criteria:**
- ✅ Incremental benchmark shows 50x+ speedup for medium sites
- ✅ Incremental benchmark shows 100x+ speedup for large sites
- ✅ Only truly affected pages rebuilt

---

### Phase 2: Documentation (Week 2-3)
**Why Second?**
- With performance validated, can market it
- Shows Bengal eating its own dog food
- Creates complete package: fast + documented

**Deliverables:**
1. Documentation site built with Bengal
2. Comprehensive guides (5-6 major guides)
3. 3-4 polished example sites
4. API reference

**Success Criteria:**
- ✅ Docs site live and beautiful
- ✅ Clear getting started path for new users
- ✅ Multiple example templates

---

## 🔧 Technical Deep-Dive: Fixing Incremental Builds

### Current Behavior (TOO CONSERVATIVE)
```python
# ANY tag change → rebuild ALL generated pages
if page_with_tags_changed:
    rebuild_all_tag_pages()
    rebuild_all_archive_pages()
```

### Desired Behavior (GRANULAR)
```python
# Track which tags actually changed
old_tags = cache.get_page_tags(page.source_path)
new_tags = set(page.tags)
added_tags = new_tags - old_tags
removed_tags = old_tags - new_tags

# Only rebuild affected tag pages
for tag in (added_tags | removed_tags):
    rebuild_tag_page(tag)

# Only rebuild archives if section membership changed
if page.section_changed():
    rebuild_section_archive(page.section)
```

### Implementation Plan

#### Step 1: Track Previous Tag State (1 hour)
```python
# In BuildCache
def get_previous_tags(self, page_path: Path) -> Set[str]:
    """Get tags from previous build."""
    return self.taxonomy_state.get(str(page_path), set())

def update_tags(self, page_path: Path, tags: Set[str]):
    """Store current tags for next build."""
    self.taxonomy_state[str(page_path)] = tags
```

#### Step 2: Detect Specific Tag Changes (1 hour)
```python
# In _find_incremental_work()
tag_changes = {}  # tag_slug -> (added_pages, removed_pages)

for page in changed_pages:
    old_tags = cache.get_previous_tags(page.source_path)
    new_tags = set(page.tags or [])
    
    added = new_tags - old_tags
    removed = old_tags - new_tags
    
    for tag in added:
        tag_changes.setdefault(tag, {'added': [], 'removed': []})
        tag_changes[tag]['added'].append(page)
    
    for tag in removed:
        tag_changes.setdefault(tag, {'added': [], 'removed': []})
        tag_changes[tag]['removed'].append(page)
```

#### Step 3: Rebuild Only Affected Generated Pages (2 hours)
```python
# Only rebuild tag pages that actually changed
for tag_slug, changes in tag_changes.items():
    # Find all pages for this tag
    for generated_page in self.pages:
        if (generated_page.metadata.get('_generated') and
            generated_page.metadata.get('_tag_slug') == tag_slug):
            pages_to_rebuild.add(generated_page.source_path)

# Only rebuild archives if section membership changed
for page in changed_pages:
    if page_changed_sections(page):
        rebuild_section_archives(page.section)
```

#### Step 4: Update Tests & Benchmarks (1 hour)
- Update incremental build benchmark
- Add test for granular tag rebuilding
- Validate 50-900x speedup

---

## 📈 Expected Results After Fix

### Incremental Build Performance (After Fix):

| Site Size | Full Build | Incremental | Speedup | Current | Target | Status |
|-----------|------------|-------------|---------|---------|--------|--------|
| Small (10) | 0.27s | **0.015s** | **18x** | 2.6x | 10x+ | ✅ |
| Medium (50) | 0.84s | **0.012s** | **70x** | 2.6x | 50x+ | ✅ |
| Large (100) | 1.71s | **0.010s** | **171x** | 2.4x | 100x+ | ✅ |
| Very Large (1000) | 17s | **0.015s** | **1133x** | N/A | 500x+ | ✅ |

**Key Insight:** Once fixed, incremental time becomes CONSTANT (~10-15ms) regardless of site size, because we only rebuild 1-2 pages.

---

## 🎯 Success Metrics

### Technical Metrics (After Phase 1)
- ✅ Incremental builds: 50x+ speedup (medium sites)
- ✅ Incremental builds: 100x+ speedup (large sites)
- ✅ Single page change rebuilds <3 pages
- ✅ All benchmarks passing

### User Experience Metrics (After Phase 2)
- ✅ Documentation site live
- ✅ 3+ complete example sites
- ✅ <5 minute getting started time
- ✅ Clear migration guides

### Competitive Position
- ✅ Match Hugo's incremental build speed
- ✅ Better architecture (cleaner, more modular)
- ✅ Python ecosystem (vs Go, Ruby, JS)
- ✅ Production-ready claim validated

---

## 🚧 Known Limitations (Post-Fix)

Even after fixing incremental builds:

1. **Rendering is 98% of time** - Further speedup requires:
   - AST caching
   - Template pre-compilation
   - These are v2.0 features, not critical

2. **No Plugin System Yet** - Planned for later:
   - Plugin architecture designed
   - Can be added without breaking changes
   - Not blocking current use cases

3. **Limited Examples** - After docs phase:
   - Will have 4-5 polished examples
   - Community can contribute more
   - Not a technical blocker

---

## 🎯 Decision Matrix

| Criterion | Option A (Incremental) | Option B (Rendering) | Option C (Docs) |
|-----------|----------------------|---------------------|-----------------|
| **Impact** | ⭐⭐⭐⭐⭐ Critical | ⭐⭐ Marginal | ⭐⭐⭐⭐ High |
| **Effort** | 4-6 hours | 8-12 hours | 12-16 hours |
| **Risk** | Low (clear path) | Medium (unknowns) | Low (straightforward) |
| **Urgency** | High (claim invalid) | Low (targets met) | High (adoption) |
| **Dependencies** | None | None | Better with A done |
| **ROI** | **Very High** | Low-Medium | **High** |

**Recommendation:** **Option A first** (fix incremental builds), then **Option C** (documentation).

---

## 📅 Proposed Timeline

### Week 1: Fix Incremental Builds
- **Day 1:** Implement tag state tracking in BuildCache
- **Day 2:** Implement granular change detection
- **Day 3:** Update rebuild logic to be selective
- **Day 4:** Test and validate with benchmarks
- **Day 5:** Document behavior, update ARCHITECTURE.md

**Deliverable:** Incremental builds achieving 50-900x speedup ✅

---

### Week 2-3: Documentation
- **Days 1-2:** Set up docs site structure with Bengal
- **Days 3-5:** Write core guides (Getting Started, Config, Themes)
- **Days 6-8:** Create 3 example sites (blog, docs, portfolio)
- **Days 9-10:** API reference and polish

**Deliverable:** Comprehensive docs site live ✅

---

## 🎉 Vision: Bengal v1.0

After completing both phases, Bengal will be:

✅ **Fast**
- Full builds: Meeting all targets
- Incremental builds: 50-900x speedup (validated)
- Parallel processing: 2-4x speedup (validated)

✅ **Well-Documented**
- Beautiful docs site (built with Bengal)
- Multiple complete examples
- Clear getting started path

✅ **Production-Ready**
- Handles sites of all sizes
- Competitive with Hugo/Jekyll/11ty
- Clean architecture, well-tested

✅ **Python-Native**
- Leverages Python ecosystem
- Easy to extend and customize
- Type-safe and modern

---

## 🤔 Open Questions

1. **Should we also add:**
   - Progress bars for large builds?
   - Build profiling mode?
   - Memory usage tracking?
   
   **Answer:** Not critical, can be v1.1 features

2. **Should we optimize rendering now?**
   
   **Answer:** No, incremental builds make this less important. With incremental builds working, full build speed is less critical.

3. **Should we wait for plugin system?**
   
   **Answer:** No, core functionality is more important. Plugins can come in v1.1.

---

## 💬 Recommendation Summary

**IMMEDIATE NEXT STEP:** Fix incremental builds (Option A)

**Why:**
1. Critical performance claim currently invalid (2.6x vs 50-900x)
2. Clear root cause identified in site.py
3. High confidence we can fix it (4-6 hours)
4. Blocke for large site support
5. Low risk, high impact

**Then:** Build documentation site (Option C)

**Why:**
1. With performance validated, can confidently market Bengal
2. Demonstrates Bengal eating its own dog food
3. Enables community adoption
4. Creates complete package: fast + documented

**Later:** Consider rendering optimizations (Option B) if needed

**Result After 2-3 Weeks:**
- ✅ Bengal v1.0: Fast, documented, production-ready
- ✅ Competitive with established SSGs
- ✅ Ready for real-world use and community growth

---

## 🚀 Next Action

**Create detailed implementation plan for incremental build fix:**
1. Write technical specification
2. Create task breakdown
3. Implement solution
4. Validate with benchmarks
5. Update documentation

**Ready to proceed?** Yes! ✅

---

*This document provides strategic direction based on current state analysis and benchmark results. The recommendation is data-driven and considers both technical merit and user impact.*

