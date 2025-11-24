# Performance Opportunities Analysis

**Date**: 2025-01-23  
**Build Stats**: 11.23s total (344 pages, 85 assets)  
**Priority**: High

## Current Performance Breakdown

```
Total:       11.23s
├─ Rendering:   4.95s (44%) ⚠️  Largest bottleneck
├─ Assets:      3.29s (29%) ⚠️  Second largest bottleneck  
├─ Postprocess: 874ms (7.8%)
├─ Discovery:   121ms (1.1%)
└─ Taxonomies:   1ms (0.01%)
```

**Throughput**: 30.6 pages/second

## Critical Opportunities

### 1. 🔴 CSS Entry Point Sequential Processing (HIGH IMPACT)

**Location**: `bengal/orchestration/asset.py:193-202`

**Problem**:
- CSS entry points (style.css files) are processed **sequentially** in a loop
- Each CSS entry bundles multiple CSS modules, which can be slow
- With multiple CSS entry points, this creates a bottleneck

**Current Code**:
```python
# Process CSS entry points first (bundle + minify)
for i, css_entry in enumerate(css_entries):
    self._process_css_entry(css_entry, minify, optimize, fingerprint)
    # ... progress updates
```

**Impact**:
- If you have 3 CSS entry points, each taking ~500ms:
  - Sequential: 1.5s total
  - Parallel: ~500ms total (3x faster)
- Estimated improvement: **30-50% faster asset processing** for sites with multiple CSS entry points

**Recommendation**:
```python
# Process CSS entry points in parallel
if parallel and len(css_entries) > 1:
    with ThreadPoolExecutor(max_workers=min(len(css_entries), max_workers)) as executor:
        futures = [executor.submit(self._process_css_entry, entry, minify, optimize, fingerprint)
                   for entry in css_entries]
        for i, future in enumerate(futures):
            future.result()  # Wait for completion
            if progress_manager:
                progress_manager.update_phase("assets", current=i+1, ...)
else:
    # Sequential fallback for single entry or non-parallel mode
    for i, css_entry in enumerate(css_entries):
        self._process_css_entry(css_entry, minify, optimize, fingerprint)
```

**Priority**: 🔴 **HIGH** - Easy win, significant impact

---

### 2. 🟡 Asset Processing Lock Contention (MEDIUM IMPACT)

**Location**: `bengal/orchestration/asset.py:374-381`

**Problem**:
- Progress updates happen inside a lock for every asset
- String operations (`asset.source_path.name`) happen inside lock
- Similar to the rendering progress issue we already fixed

**Current Code**:
```python
with lock:
    completed_count += 1
    progress_manager.update_phase(
        "assets",
        current=completed_count,
        current_item=asset.source_path.name,  # String op in lock!
    )
```

**Impact**:
- With 85 assets and parallel processing: 85 lock acquisitions
- Estimated overhead: **2-5% of asset processing time**

**Recommendation**:
```python
# Pre-compute outside lock
item_name = asset.source_path.name
with lock:
    completed_count += 1
    progress_manager.update_phase("assets", current=completed_count, current_item=item_name)
```

**Priority**: 🟡 **MEDIUM** - Small improvement, easy to implement

---

### 3. 🟡 Batch Progress Updates for Assets (MEDIUM IMPACT)

**Location**: `bengal/orchestration/asset.py:374-381`

**Problem**:
- Progress updates happen for every single asset
- With 85 assets, that's 85 progress updates
- Similar batching strategy as rendering would help

**Recommendation**:
```python
# Batch progress updates (every 10 assets or 100ms)
last_update_time = time.time()
update_interval = 0.1  # 100ms

for future, asset in futures:
    future.result()
    if progress_manager:
        now = time.time()
        if (completed_count + 1) % 10 == 0 or (now - last_update_time) >= update_interval:
            with lock:
                completed_count += 1
                progress_manager.update_phase("assets", current=completed_count)
            last_update_time = now
        else:
            completed_count += 1  # Track but don't update
```

**Priority**: 🟡 **MEDIUM** - Reduces overhead, consistent with rendering optimization

---

### 4. 🟢 Postprocess Parallelization (LOW-MEDIUM IMPACT)

**Location**: `bengal/orchestration/postprocess.py`

**Current State**:
- Postprocess already supports parallel execution
- But some tasks might be sequential when they could be parallel

**Opportunities**:
- Sitemap generation and RSS generation are independent
- Link validation could potentially be parallelized further
- Estimated improvement: **10-20% faster postprocess** (saves ~100-175ms)

**Priority**: 🟢 **LOW-MEDIUM** - Already mostly optimized

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)

1. **Parallelize CSS Entry Point Processing** (🔴 HIGH)
   - Estimated improvement: **30-50% faster asset processing**
   - For your build: 3.29s → **1.6-2.3s** (saves ~1-1.7s)
   - Total build time: 11.23s → **9.5-10.2s** (9-15% faster)

2. **Optimize Asset Progress Updates** (🟡 MEDIUM)
   - Move string operations outside lock
   - Batch progress updates
   - Estimated improvement: **2-5% faster asset processing**
   - For your build: saves ~65-165ms

**Total Phase 1 Impact**: **10-17% faster builds** (1.1-1.9s saved)

### Phase 2: Additional Optimizations ✅ **COMPLETED**

3. **Postprocess Progress Update Optimization** (🟢 LOW-MEDIUM)
   - Optimized error handling to occur outside lock
   - Ensured minimal lock hold time for progress updates
   - Tasks already running in parallel (no further parallelization needed)
   - Estimated improvement: **2-5% faster postprocess** (marginal, but good practice)
   - For your build: saves ~20-45ms

**Total Phase 2 Impact**: **<1% faster builds** (additional ~20-45ms saved)

**Note**: Postprocess tasks were already well-optimized with parallel execution. The main optimization was ensuring error handling and string operations happen outside locks, following best practices.

---

## Expected Overall Impact

**Conservative Estimate**:
- Phase 1: **10-15% faster builds** (1.1-1.7s saved)
- Phase 2: **1-2% faster builds** (additional ~100-175ms saved)
- **Total: 11-17% faster builds**

**Best Case** (if CSS bundling is major bottleneck):
- Phase 1: **15-20% faster builds** (1.7-2.2s saved)
- **Total: 15-20% faster builds**

**Your Build**:
- Current: 11.23s
- After Phase 1: **9.5-10.1s** (estimated)
- After Phase 2: **9.5-10.0s** (estimated, minimal additional gain)

**Implementation Status**:
- ✅ Phase 1: CSS parallelization + Asset progress optimization (COMPLETED)
- ✅ Phase 2: Postprocess progress optimization (COMPLETED)

---

## Code Changes Required

### 1. Parallelize CSS Entry Points

**File**: `bengal/orchestration/asset.py`

```python
# Replace lines 193-202 with:
if parallel and len(css_entries) > 1:
    # Process CSS entry points in parallel
    max_workers = self.site.config.get("max_workers", min(8, len(css_entries)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(self._process_css_entry, entry, minify, optimize, fingerprint)
            for entry in css_entries
        ]
        for i, future in enumerate(futures):
            try:
                future.result()
                if progress_manager:
                    progress_manager.update_phase(
                        "assets",
                        current=i + 1,
                        current_item=f"{css_entries[i].source_path.name} (bundled)",
                        minified=minify,
                        bundled_modules=len(css_modules),
                    )
            except Exception as e:
                self.logger.error("css_entry_processing_failed", ...)
else:
    # Sequential fallback
    for i, css_entry in enumerate(css_entries):
        self._process_css_entry(css_entry, minify, optimize, fingerprint)
        if progress_manager:
            progress_manager.update_phase(...)
```

### 2. Optimize Asset Progress Updates

**File**: `bengal/orchestration/asset.py`

```python
# In _process_parallel, replace lines 371-381 with:
import time
last_update_time = time.time()
update_interval = 0.1  # 100ms
pending_updates = 0

for future, asset in futures:
    try:
        future.result()
        # Pre-compute outside lock
        item_name = asset.source_path.name
        pending_updates += 1

        now = time.time()
        should_update = (
            pending_updates >= 10 or
            (now - last_update_time) >= update_interval
        )

        if progress_manager and should_update:
            with lock:
                completed_count += pending_updates
                progress_manager.update_phase(
                    "assets",
                    current=completed_count,
                    current_item=item_name,
                )
                pending_updates = 0
                last_update_time = now
    except Exception as e:
        errors.append(str(e))

# Final update
if progress_manager and pending_updates > 0:
    with lock:
        completed_count += pending_updates
        progress_manager.update_phase("assets", current=completed_count)
```

---

## Testing Plan

1. **Benchmark current performance**:
   ```bash
   time bengal site build
   ```

2. **Apply Phase 1 changes**

3. **Benchmark again**:
   ```bash
   time bengal site build
   ```

4. **Compare results**:
   - Asset processing time should decrease significantly
   - Total build time should decrease by 10-17%

---

## Notes

- CSS bundling is CPU-bound, perfect for parallelization
- ThreadPoolExecutor overhead is minimal compared to CSS processing time
- Changes maintain backward compatibility (sequential fallback for single entry)
- Progress updates still work, just batched more efficiently

---

## Related Files

- `bengal/orchestration/asset.py:193-202` - CSS entry point processing (sequential)
- `bengal/orchestration/asset.py:329-394` - Parallel asset processing (already optimized)
- `bengal/orchestration/render.py` - Rendering parallelization (reference implementation)
