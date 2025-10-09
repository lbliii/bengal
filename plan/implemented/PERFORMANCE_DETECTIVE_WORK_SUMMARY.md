# Performance Detective Work - Executive Summary

**Date:** 2025-10-09  
**Investigation:** Health check performance analysis from `bengal build --debug`

---

## 🔍 What We Found

### The N+1 URL Problem
- **Evidence:** `section_url_from_index` logged **1,016 times** for 198 pages (~5× per page)
- **Root Cause:** `Section.url` and `Page.url` are `@property` decorators with no caching
- **Impact:** Every access recalculates URL from output_path or index_page
- **Where:** Menu validation, navigation checks, link validation, template rendering

### O(n²) Validator Patterns
Multiple validators independently iterate through `site.pages`:
- **MenuValidator:** O(menu_items × pages) for URL lookups
- **NavigationValidator:** 5 separate iterations when 1 would work
- **TaxonomyValidator:** 4 separate iterations over pages

### Health Check Dominance
```
health_check:   3,209ms (52.9%) 🔥 <- More than rendering!
rendering:      2,290ms (37.8%)
```

### Scaling Projection
For 2,000 pages (10× showcase):
- **Rendering:** ~29s (linear scaling) ✅
- **Health checks:** **5+ minutes** (O(n²) patterns) 🔥

---

## ✅ Proposed Quick Wins (2-3 hours implementation)

### 1. Cache URL Properties (30 min)
**Change:** `@property` → `@cached_property` for `Page.url` and `Section.url`
**Impact:** 1,016 calculations → ~40 unique calculations
**Benefit:** ~30% faster health checks, 80% less log noise

### 2. Decouple Debug from Health Checks (45 min)
**Change:** `--debug` uses WRITER profile (fast checks), not DEVELOPER (all checks)
**Impact:** Debug builds 50-70% faster
**Benefit:** Better dev experience, explicit opt-in for comprehensive checks

### 3. Batch Health Check Context (90 min)
**Change:** Pre-compute page categorizations in O(n), share across validators
**Impact:** Eliminates O(n²) patterns in menu/navigation validators
**Benefit:** ~50% additional speedup, scales linearly to 2K+ pages

### Combined Impact
- **Before:** 3.2s health checks
- **After:** 0.8-1.0s health checks
- **At 2K pages:** ~8s instead of ~320s

---

## 🏗️ Long-Term Solutions (future)

### URLRegistry
Centralized URL management with:
- Explicit cache management
- O(1) reverse lookups (URL → Page)
- Foundation for URL rewrites, redirects

### Incremental Health Checks
Skip validators based on what changed:
- Content change → Run links, navigation
- Config change → Run config, menu
- Nothing changed → Skip most validators

### Parallel Execution
Run independent validators concurrently:
- 2-4× speedup on multi-core systems
- Better CI/CD performance

---

## 🎯 Why This Fits Bengal's Design

### Aligns with Existing Patterns
- **Caching:** Already used for `toc_items` (line 142 in `page/metadata.py`)
- **Profiles:** Already implemented for logging/metrics
- **Context:** Similar to `DependencyTracker` pattern

### Backward Compatible
- `cached_property` is standard library (Python 3.8+)
- Context parameter is optional for validators
- Gradual migration path for all changes

### Maintains Philosophy
- Health checks remain comprehensive
- Users control trade-offs (speed vs depth)
- Fast by default, detailed on demand

---

## 📊 Detailed Analysis

See complete documentation:
- **Full Analysis:** `plan/completed/PERFORMANCE_OPTIMIZATION_ANALYSIS.md`
- **Implementation Guide:** `plan/completed/PERFORMANCE_QUICK_WINS_IMPLEMENTATION.md`

---

## 🚀 Recommendation

**Start with Quick Win #1** (URL caching) - lowest risk, immediate 30% improvement, foundation for other wins.

Once validated, proceed with #2 and #3 for cumulative ~75% improvement in health check time.

