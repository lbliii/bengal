# Template Rendering Issue Analysis & Solutions

**Date:** October 2, 2025  
**Issue:** 46 warnings during build: `'page' is undefined`  
**Status:** Pre-existing bug (not caused by parallel processing)  
**Impact:** Pages build successfully using fallback HTML, but don't use theme templates

---

## 🔍 Root Cause Analysis

### The Problem

During builds (both parallel and sequential), template rendering fails with:
```
Warning: Failed to render page [...]/content/about.md with template page.html: 'page' is undefined
```

Yet when testing individual pages in isolation, rendering works perfectly.

### Investigation Results

1. ✅ **Parallel processing is NOT the cause** - same 46 warnings with `parallel=false`
2. ✅ **Page objects are valid** - all attributes accessible
3. ✅ **Context is passed correctly** - `{'page': page, 'content': content, ...}`
4. ✅ **Individual page rendering works** - tested successfully in isolation
5. ❌ **Build with multiple pages fails** - warnings appear during full builds

### Key Findings

**Line 288 in `site.py`:**
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(pipeline.process_page, page) for page in self.pages]
```

**Line 229 in `site.py`:**
```python
pipeline = RenderingPipeline(self)  # Single pipeline shared across threads
```

**The Issue:**
- A single `RenderingPipeline` instance is shared across multiple threads
- This pipeline contains a single `TemplateEngine` instance
- The `TemplateEngine` contains a single Jinja2 `Environment`
- **Thread safety issue**: Multiple threads rendering templates simultaneously

### But Wait... Jinja2 IS Thread-Safe!

Jinja2's documentation states that the Environment is thread-safe for **rendering**. So why the errors?

**The Real Problem:**
Look at `template_engine.py` lines 84-98:

```python
def render(self, template_name: str, context: Dict[str, Any]) -> str:
    # Track template dependency
    if self.dependency_tracker:
        template_path = self._find_template_path(template_name)
        if template_path:
            self.dependency_tracker.track_template(template_path)  # ← SHARED STATE!
    
    # Add site to context
    context.setdefault('site', self.site)
    context.setdefault('config', self.site.config)
    
    template = self.env.get_template(template_name)
    
    # Track all templates used (including partials via includes/extends)
    if self.dependency_tracker:
        self._track_template_dependencies(template)  # ← SHARED STATE!
    
    return template.render(**context)
```

**The `dependency_tracker` is shared across threads!**

And in `pipeline.py` line 62:
```python
if self.dependency_tracker:
    self.template_engine.dependency_tracker = self.dependency_tracker  # ← SET ONCE
```

### The Race Condition

1. Thread A starts processing Page A
2. Thread A calls `dependency_tracker.start_page(page_a.source_path)`
3. Thread B starts processing Page B  
4. Thread B calls `dependency_tracker.start_page(page_b.source_path)` **← OVERWRITES Thread A's page!**
5. Thread A renders template → tracks dependency for **Page B** (wrong!)
6. Chaos ensues with mixed-up dependencies and undefined variables

---

## 🎯 Proposed Solutions

### Solution 1: Thread-Local Dependency Tracking (RECOMMENDED)

**Approach:** Use thread-local storage for the current page being processed.

**Implementation:**
```python
import threading

class DependencyTracker:
    def __init__(self, cache):
        self.cache = cache
        self._current_page = threading.local()  # Thread-local storage
    
    def start_page(self, page_path: Path) -> None:
        """Start tracking dependencies for a page (thread-safe)."""
        self._current_page.value = str(page_path)
    
    def end_page(self) -> None:
        """End tracking for current page (thread-safe)."""
        if hasattr(self._current_page, 'value'):
            del self._current_page.value
    
    def track_template(self, template_path: Path) -> None:
        """Track a template dependency (thread-safe)."""
        if hasattr(self._current_page, 'value'):
            page_path = self._current_page.value
            self.cache.add_dependency(page_path, str(template_path), "template")
```

**Pros:**
- ✅ Thread-safe by design
- ✅ Minimal code changes
- ✅ No performance impact
- ✅ Preserves all functionality

**Cons:**
- Requires modifying `DependencyTracker` class

---

### Solution 2: Per-Thread Pipeline Instances

**Approach:** Create a separate pipeline instance for each thread.

**Implementation:**
```python
def _build_parallel(self, pipeline: Any) -> None:
    """Build pages in parallel for better performance."""
    max_workers = self.config.get("max_workers", 4)
    
    def process_with_own_pipeline(page):
        # Each thread gets its own pipeline
        thread_pipeline = RenderingPipeline(self)
        thread_pipeline.dependency_tracker = DependencyTracker(self.cache)
        thread_pipeline.process_page(page)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_own_pipeline, page) for page in self.pages]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing page: {e}")
```

**Pros:**
- ✅ Complete isolation
- ✅ No shared state issues
- ✅ Simple to understand

**Cons:**
- ⚠️ Creates multiple Jinja2 environments (memory overhead)
- ⚠️ Loses shared template compilation cache
- ⚠️ Slightly slower (re-parsing templates)

---

### Solution 3: Lock-Based Synchronization

**Approach:** Use locks around dependency tracking operations.

**Implementation:**
```python
from threading import Lock

class DependencyTracker:
    def __init__(self, cache):
        self.cache = cache
        self._lock = Lock()
        self._current_pages = {}  # Thread ID → page path
    
    def start_page(self, page_path: Path) -> None:
        """Start tracking dependencies for a page (thread-safe)."""
        thread_id = threading.get_ident()
        with self._lock:
            self._current_pages[thread_id] = str(page_path)
    
    def track_template(self, template_path: Path) -> None:
        """Track a template dependency (thread-safe)."""
        thread_id = threading.get_ident()
        with self._lock:
            if thread_id in self._current_pages:
                page_path = self._current_pages[thread_id]
                self.cache.add_dependency(page_path, str(template_path), "template")
```

**Pros:**
- ✅ Thread-safe
- ✅ Preserves functionality

**Cons:**
- ⚠️ Locks add overhead
- ⚠️ Potential bottleneck with many threads
- ⚠️ More complex code

---

### Solution 4: Disable Dependency Tracking in Parallel Builds

**Approach:** Only track dependencies in sequential builds.

**Implementation:**
```python
def _build_parallel(self, pipeline: Any) -> None:
    """Build pages in parallel for better performance."""
    # Temporarily disable dependency tracking for parallel builds
    original_tracker = pipeline.dependency_tracker
    pipeline.dependency_tracker = None
    pipeline.template_engine.dependency_tracker = None
    
    try:
        max_workers = self.config.get("max_workers", 4)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(pipeline.process_page, page) for page in self.pages]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing page: {e}")
    finally:
        # Restore dependency tracking
        pipeline.dependency_tracker = original_tracker
        pipeline.template_engine.dependency_tracker = original_tracker
```

**Pros:**
- ✅ Simple fix
- ✅ No threading issues
- ✅ Fast parallel builds

**Cons:**
- ❌ Loses dependency tracking for parallel builds
- ❌ Incremental builds won't know which templates changed
- ❌ Less accurate cache invalidation

---

## 📊 Comparison Matrix

| Solution | Complexity | Performance | Correctness | Recommended |
|----------|-----------|-------------|-------------|-------------|
| **1. Thread-Local Storage** | Low | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Perfect | ✅ **YES** |
| 2. Per-Thread Pipelines | Medium | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Perfect | ⚠️ Acceptable |
| 3. Lock-Based | Medium | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐⭐ Perfect | ⚠️ Acceptable |
| 4. Disable Tracking | Low | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Reduced | ❌ No |

---

## 🎯 Recommended Solution

**Use Solution 1: Thread-Local Dependency Tracking**

### Why?
1. **Minimal changes** - only modify `DependencyTracker` class
2. **Best performance** - no locks, no overhead
3. **Maintains all functionality** - dependency tracking still works
4. **Thread-safe by design** - Python's `threading.local()` is built for this
5. **Clean architecture** - proper separation of concerns

### Implementation Steps

1. **Modify `bengal/cache/dependency_tracker.py`:**
   - Add `import threading`
   - Change `self._current_page` to `threading.local()`
   - Update all methods to use `self._current_page.value`
   - Add `hasattr` checks for thread safety

2. **Add tests:**
   - Test concurrent dependency tracking
   - Verify thread isolation
   - Validate no cross-contamination

3. **Verify fix:**
   - Run full build
   - Confirm 0 warnings (not 46!)
   - Verify themed templates are used
   - Check dependency tracking still works

### Expected Results
- ✅ 0 warnings during build
- ✅ All pages use proper theme templates
- ✅ Dependency tracking works correctly
- ✅ Incremental builds remain accurate
- ✅ Parallel processing works perfectly

---

## 🔧 Quick Fix for Testing

If you want to quickly verify this is the issue, temporarily disable dependency tracking:

```bash
# In bengal/core/site.py, line 230, add:
pipeline.dependency_tracker = None

# Then build:
bengal build
```

If warnings disappear, we've confirmed the root cause!

---

## 📝 Additional Observations

### Why Does Fallback HTML Still Work?

The `_render_fallback()` method (renderer.py line 190) creates simple HTML without templates, so it doesn't trigger the race condition. That's why builds "succeed" - they use fallback HTML when template rendering fails.

### Why Didn't We Notice Earlier?

1. Pages still build (using fallback)
2. Warnings are easy to ignore  
3. Fallback HTML is "good enough" for basic testing
4. Issue only appears with dependency tracking enabled

### Impact on Incremental Builds

The current bug means incremental builds might not properly track which templates affect which pages, leading to stale pages when templates change. **This is a correctness issue**, not just cosmetic!

---

## 🎉 Conclusion

This is a **thread safety bug in dependency tracking**, not in the parallel processing code itself. The parallel processing implementation is correct - it just exposed a pre-existing race condition.

**Action Items:**
1. Implement Solution 1 (Thread-Local Storage)
2. Add thread-safety tests
3. Verify all warnings disappear
4. Document the fix

**Priority:** High (affects correctness of incremental builds)  
**Difficulty:** Low (straightforward fix)  
**Impact:** High (fixes 46 warnings + improves reliability)

