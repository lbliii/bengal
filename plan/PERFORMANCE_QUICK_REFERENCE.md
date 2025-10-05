# Performance Flaws - Quick Reference

**Date**: October 5, 2025  
**Full Analysis**: See `INITIAL_BUILD_PERFORMANCE_FLAWS.md`

## 🚨 Critical Issues (Must Fix)

### 1. Phase Ordering (BIGGEST ISSUE)
**File**: `bengal/orchestration/build.py:108-161`  
**Problem**: Taxonomies & Menus process ALL pages BEFORE incremental filtering  
**Impact**: 2-5x slower incremental builds  
**Fix**: Move incremental filtering to Phase 2 (right after Discovery)

```
Current Order:                     Proposed Order:
1. Discovery (ALL pages)          1. Discovery (ALL pages)
2. Sections (ALL)                 2. Incremental Filter (find changes)
3. Taxonomies (ALL)    ❌         3. Sections (changed only)
4. Menus (ALL)         ❌         4. Taxonomies (if needed)
5. Filter (find work)  ⬅️          5. Menus (if needed)
6. Render (filtered)              6. Render (filtered)
```

### 2. Non-Lazy Frontmatter Parsing
**File**: `bengal/discovery/content_discovery.py:147-184`  
**Problem**: Reads & parses ALL markdown files during discovery  
**Impact**: 15-25% slower discovery phase  
**Fix**: Make `Page.content` and `Page.metadata` lazy properties

```python
# Current: Parse immediately
def _create_page(self, file_path: Path) -> Page:
    content, metadata = self._parse_content_file(file_path)  # ❌ Eager
    return Page(source_path=file_path, content=content, metadata=metadata)

# Proposed: Parse on-demand
class Page:
    @property
    def content(self):
        if self._content is None:
            self._parse_file()  # ✅ Lazy
        return self._content
```

---

## ⚠️ Moderate Issues (Should Fix)

| # | Component | Problem | Impact | Complexity |
|---|-----------|---------|--------|------------|
| **3** | XRef Index | Builds 4 indices for ALL pages upfront | 5-10% (large sites) | Medium |
| **4** | Taxonomies | Re-collects ALL tags every build | 10-20% (incremental) | Low |
| **5** | Menus | Rebuilds from scratch every build | 5-10% (incremental) | Low |
| **9** | Output Paths | Sets paths for ALL pages, not filtered | 5-10% (incremental) | Low |

---

## ✅ Minor Issues (Low Priority)

| # | Component | Problem | Impact |
|---|-----------|---------|--------|
| **6** | Template Functions | Registers 80+ functions upfront | ~100ms (keep as-is) |
| **7** | sorted() Traversal | Sorts directory listings | ~20ms (keep as-is) |
| **8** | Cascades | Applies to all pages | Negligible (keep as-is) |
| **10** | Parallel Threshold | Uses parallel for 2+ pages | 10-20ms (easy fix) |

---

## 📊 Expected Impact

### After Fixing Critical Issues (1 & 2)
- **Initial builds**: 30-50% faster
- **Incremental builds (1 page changed)**: 2-5x faster
- **Incremental builds (10 pages changed)**: 50-100% faster

### Current Performance (for reference)
```
Small sites (10 pages):   0.29s full, 0.012s incremental ✅ Good
Medium sites (100 pages): 1.66s full, 0.047s incremental ✅ Good
Large sites (1000 pages): ???s full, ???s incremental ❓ Unknown
```

### Target Performance (after fixes)
```
Small sites (10 pages):   0.20s full, 0.010s incremental
Medium sites (100 pages): 1.00s full, 0.025s incremental
Large sites (1000 pages): 8.00s full, 0.100s incremental
```

---

## 🛠️ Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. **Fix parallel threshold** (Flaw #10) - 5 minutes, easy
2. **Move incremental filtering earlier** (Flaw #1) - 4 hours, medium complexity
3. **Output path optimization** (Flaw #9) - 2 hours, easy

**Expected Gain**: 2-3x for incremental builds, minimal risk

### Phase 2: Major Refactor (1 week)
4. **Lazy frontmatter parsing** (Flaw #2) - 2-3 days, high complexity
5. **Incremental taxonomy updates** (Flaw #4) - 1 day, low complexity
6. **Menu caching** (Flaw #5) - 1 day, low complexity

**Expected Gain**: 30-50% for full builds, 3-5x for incremental

### Phase 3: Advanced Optimization (as needed)
7. **Incremental XRef index** (Flaw #3) - 2 days, medium complexity
8. Profile and optimize based on real-world data

---

## 🎯 Next Steps

1. **Benchmark current performance** on 1000-page site
2. **Implement Phase 1 fixes** (2-3x incremental speedup)
3. **Re-benchmark** to validate improvements
4. **Implement Phase 2** if needed (30-50% full build speedup)
5. **Profile** to identify remaining bottlenecks

---

## 📝 Notes

- Flaws #6, #7, #8 are minor and can be kept as-is
- Focus on **phase ordering** first (biggest impact, medium effort)
- Lazy frontmatter is **high value but high complexity** - requires careful refactoring
- All estimates are based on code analysis, not profiling - validate with benchmarks!

