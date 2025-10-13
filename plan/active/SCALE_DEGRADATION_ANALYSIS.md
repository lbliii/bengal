# Scale Degradation Analysis

## The Problem

Performance collapses as site size increases:
- 1K pages: **141 pps** (9.4s) ✅
- 5K pages: **71 pps** (92s) ⚠️ 50% slower
- 10K pages: **29 pps** (451s = 7.5 min) ❌ 79% slower

**This suggests an O(n²) or worse algorithm somewhere.**

---

## Likely Culprits

### 1. Related Posts Calculation
```python
# In related_posts.py
for page in self.site.pages:  # O(n)
    for other_page in self.site.pages:  # O(n)
        # Calculate tag overlap
        overlap = len(page_tags & other_tags)  # O(t)
```

**Complexity**: O(n² × t) where n = pages, t = tags  
**At 10K pages**: 100M comparisons!

### 2. Cross-Reference Resolution
```python
# In rendering pipeline
for page in pages:  # O(n)
    for link in page.links:  # O(l)
        resolve_link(link, all_pages)  # O(n) if linear search
```

**Complexity**: O(n² × l) where l = links per page  
**At 10K pages with 10 links each**: 1B operations!

### 3. Taxonomy Updates
```python
# In taxonomy orchestrator
for page in self.site.pages:  # O(n)
    for tag in page.tags:  # O(t)
        if tag not in taxonomies:  # O(n) if not using dict
            # Add to taxonomy
```

**Complexity**: O(n × t × m) where m = taxonomy checks  
**At 10K pages**: Potentially millions of operations

### 4. Page Equality Checks (Already Fixed!)
The 446K equality checks I already optimized with caching.  
**Impact**: Reduced by 50%, but may still contribute at scale.

### 5. Memory Pressure & GC Thrashing
- 10K Page objects = ~500MB-1GB RAM
- Python GC overhead increases with object count
- Potential swap thrashing on low-memory systems

---

## Diagnostic Plan

### Step 1: Profile 10K Build
```bash
cd /Users/llane/Documents/github/python/bengal
python tests/performance/profile_rendering.py
```

Look for:
- Functions called > 1M times
- Functions consuming > 30% total time
- O(n²) patterns in call counts

### Step 2: Check Related Posts
```python
# If related_posts is O(n²), disable it and retest
# Expected: ~2x speedup if this is the culprit
```

### Step 3: Check Memory Usage
```bash
# Profile memory during 10K build
python -m memory_profiler tests/performance/benchmark_incremental_scale.py
```

Look for:
- >1GB RAM usage
- Memory growth during build
- GC pauses

---

## Quick Test: Disable Related Posts

Related posts is a known O(n²) operation. Let me check if it's disabled by default or always runs.
