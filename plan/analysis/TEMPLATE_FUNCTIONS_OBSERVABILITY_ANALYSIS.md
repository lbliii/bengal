# Template Functions Observability Analysis

**Date:** 2025-10-09  
**Status:** Analysis Complete  
**Priority:** Medium-High  

## Executive Summary

Template functions (30+ functions across 17 modules) currently have **zero structured logging or observability**. This is a significant gap compared to other parts of the codebase (orchestration, postprocess, cache, discovery all use Bengal's structured logger).

## Current State

### What We Have
- ✅ Robust `bengal.utils.logger` with phase tracking, timing, and memory profiling
- ✅ Structured logging in: orchestration, postprocess, config, cache, discovery
- ✅ Template rendering error tracking (via `TemplateRenderError`)
- ❌ **ZERO logging in template functions**

### Template Function Modules (17 total)
```
bengal/rendering/template_functions/
├── __init__.py          (coordinator)
├── advanced_collections.py
├── advanced_strings.py
├── collections.py
├── content.py
├── crossref.py          ⚠️ O(1) lookups - should track cache hits/misses
├── data.py              ⚠️ File I/O - silently fails
├── dates.py
├── debug.py
├── files.py
├── images.py            ⚠️ Pillow dependency - silently fails
├── math_functions.py
├── pagination_helpers.py
├── seo.py
├── strings.py
├── taxonomies.py        🐛 Has debug prints, not structured logging
└── urls.py
```

## Critical Observability Gaps

### 1. Silent Failures (High Priority)

**`data.py:get_data()`** - Lines 37-84
```python
def get_data(path: str, root_path: Any) -> Any:
    # ...
    if not file_path.exists():
        return {}  # ❌ Silent failure - user has no idea file is missing
    
    try:
        # ... parse JSON/YAML ...
    except (json.JSONDecodeError, Exception):
        return {}  # ❌ Silent failure - no error context
```

**Issues:**
- User types wrong path → gets empty dict, no warning
- YAML parse error → gets empty dict, no error message
- No way to debug which data files are being loaded

**Impact:** Template bugs are hard to debug

---

**`images.py:image_dimensions()`** - Lines 88-120
```python
def image_dimensions(path: str, root_path: Path) -> Optional[Tuple[int, int]]:
    if not file_path.exists():
        return None  # ❌ Silent failure
    
    try:
        from PIL import Image
        # ...
    except (ImportError, Exception):
        return None  # ❌ Doesn't distinguish between "Pillow not installed" vs "corrupt image"
```

**Issues:**
- Pillow not installed → None (should warn once)
- Image file corrupt → None (should error with context)
- File not found → None (should warn with attempted paths)

---

**`crossref.py:doc()`** - Lines 100-136
```python
def doc(path: str, index: dict) -> Optional['Page']:
    if not path:
        return None  # ❌ No logging of failed lookups
    
    # Try different strategies...
    return None  # ❌ User has no idea why reference failed
```

**Issues:**
- Typo in path → None (should suggest alternatives)
- No tracking of cross-reference usage patterns
- Can't identify broken references at build time

### 2. Performance Blind Spots (Medium Priority)

**`taxonomies.py:related_posts()`** - Lines 55-118
```python
def related_posts(page: Any, all_pages: List[Any] = None, limit: int = 5):
    # FAST PATH: O(1) pre-computed
    if hasattr(page, 'related_posts'):
        return page.related_posts[:limit]  # ❌ No logging of fast path usage
    
    # SLOW PATH: O(n²) runtime computation
    for other_page in all_pages:  # ❌ No warning that slow path is being used
        # ...
```

**Issues:**
- No visibility into which path is being used
- Can't detect if pre-computation is failing
- No timing data to prove performance improvements

---

**`data.py:merge()`** - Lines 108-143
```python
def merge(dict1: Dict, dict2: Dict, deep: bool = True) -> Dict:
    # Deep merge can be expensive on large nested dicts
    # ❌ No timing for deep merges
    # ❌ No logging of data structure depth
```

### 3. Debug Prints vs Structured Logging (Low Priority)

**`taxonomies.py:popular_tags_with_site()`** - Lines 21-39
```python
def popular_tags_with_site(limit: int = 10) -> List[tuple]:
    import traceback
    raw_tags = site.taxonomies.get('tags', {})
    print(f"\n🐛 DEBUG popular_tags_with_site (limit={limit}):")  # ❌ Print instead of logger
    print(f"   Stack: {' -> '.join([f.name for f in traceback.extract_stack()[-5:-1]])}")
    print(f"   Raw tags count: {len(raw_tags)}")
    # ...
```

**Issues:**
- Prints to stdout (not captured in build logs)
- No log levels (always shown)
- Not structured (can't be parsed)
- Stack trace is overkill for normal debugging

### 4. Missing Context for Template Errors (Medium Priority)

When a template function is called with invalid inputs, the resulting Jinja2 error doesn't include information about **why** the function failed internally.

**Example:** Template uses `{{ image_dimensions('missing.jpg') }}`
- Returns: `None`
- Template tries: `{{ width, height = ... }}` → UnpackError
- User sees: "cannot unpack non-iterable NoneType object"
- User **doesn't** see: "Image file 'missing.jpg' not found (tried: /assets/missing.jpg, /missing.jpg)"

## What Good Observability Would Look Like

### Example 1: Data Loading with Logging

```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

def get_data(path: str, root_path: Any) -> Any:
    """Load data from JSON or YAML file."""
    if not path:
        logger.debug("get_data_empty_path", caller="template")
        return {}
    
    file_path = Path(root_path) / path
    
    if not file_path.exists():
        logger.warning(
            "data_file_not_found",
            path=path,
            attempted=str(file_path),
            caller="template"
        )
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if path.endswith('.json'):
            data = json.loads(content)
            logger.debug("data_loaded", path=path, type="json", keys=len(data) if isinstance(data, dict) else None)
            return data
        
        # ... similar for YAML ...
        
    except json.JSONDecodeError as e:
        logger.error(
            "data_parse_error",
            path=path,
            format="json",
            error=str(e),
            line=e.lineno,
            caller="template"
        )
        return {}
    except Exception as e:
        logger.error("data_load_error", path=path, error=str(e))
        return {}
```

**Benefits:**
- Users see warnings about missing files in build output
- Build logs show which data files are being loaded (useful for debugging)
- Parse errors include line numbers and context
- Can track data file usage patterns

### Example 2: Cross-Reference Tracking

```python
def doc(path: str, index: dict) -> Optional['Page']:
    """Get page by path with logging."""
    if not path:
        return None
    
    # Try different strategies...
    page = # ... lookup logic ...
    
    if page:
        logger.debug("xref_resolved", path=path, url=page.url)
    else:
        # Suggest alternatives
        all_paths = list(index.get('by_path', {}).keys())
        from difflib import get_close_matches
        suggestions = get_close_matches(path, all_paths, n=3, cutoff=0.6)
        
        logger.warning(
            "xref_not_found",
            path=path,
            suggestions=suggestions,
            caller="template"
        )
    
    return page
```

### Example 3: Performance Tracking

```python
def related_posts(page: Any, all_pages: List[Any] = None, limit: int = 5):
    """Find related posts with path tracking."""
    if hasattr(page, 'related_posts') and page.related_posts:
        logger.debug("related_posts_fast_path", page=page.slug, count=len(page.related_posts))
        return page.related_posts[:limit]
    
    # Slow path warning
    logger.warning(
        "related_posts_slow_path",
        page=page.slug,
        all_pages=len(all_pages) if all_pages else 0,
        message="Pre-computed related posts not available, falling back to O(n²) algorithm"
    )
    
    import time
    start = time.time()
    
    # ... slow algorithm ...
    
    duration_ms = (time.time() - start) * 1000
    logger.debug("related_posts_computed", page=page.slug, duration_ms=duration_ms, count=len(scored_pages))
    
    return results
```

## Recommendations

### Priority 1: High-Impact Functions (Do First)

Add logging to functions that involve I/O or can fail silently:

1. **`data.py:get_data()`** - File loading errors
2. **`images.py:image_dimensions()`** - Pillow dependency + file errors
3. **`images.py:image_data_uri()`** - File loading + encoding errors
4. **`crossref.py:doc()`** - Failed lookups with suggestions
5. **`crossref.py:ref()`** - Broken references
6. **`taxonomies.py:popular_tags_with_site()`** - Replace debug prints with logger

**Estimated effort:** 2-3 hours  
**Impact:** Immediate improvement in template debugging

### Priority 2: Performance Tracking (Do Second)

Add timing and path detection for performance-sensitive functions:

1. **`taxonomies.py:related_posts()`** - Track fast vs slow path usage
2. **`data.py:merge()`** - Time deep merges on large data structures
3. **`crossref.py` lookups** - Track index hit rates

**Estimated effort:** 1-2 hours  
**Impact:** Validate performance optimizations, detect regressions

### Priority 3: Enhanced Context (Do Last)

Add debug-level logging for function usage patterns:

1. **`pagination_helpers.py`** - Track pagination patterns
2. **`seo.py`** - Track SEO function usage
3. **`urls.py`** - Track URL generation patterns

**Estimated effort:** 1-2 hours  
**Impact:** Better understanding of feature usage

### Non-Goals

**Don't add logging to:**
- Pure string/math functions (too noisy, not useful)
- Simple getters/setters
- Functions that already raise exceptions appropriately

## Implementation Strategy

### Phase 1: Add Logger Infrastructure (15 min)

Add to `bengal/rendering/template_functions/__init__.py`:

```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

def register_all(env: 'Environment', site: 'Site') -> None:
    """Register all template functions with logging."""
    logger.debug("registering_template_functions", count=17)
    
    # ... existing registration ...
    
    logger.debug("template_functions_registered")
```

### Phase 2: Update High-Impact Functions (2-3 hours)

Work through Priority 1 list, adding:
- `logger.warning()` for missing files, failed lookups
- `logger.error()` for parse errors, exceptions
- `logger.debug()` for successful operations (when verbose mode enabled)

### Phase 3: Add Performance Tracking (1-2 hours)

Add timing to expensive operations using:

```python
import time
start = time.time()
# ... work ...
duration_ms = (time.time() - start) * 1000
logger.debug("operation_complete", duration_ms=duration_ms)
```

Or use logger's phase context manager for complex operations:

```python
with logger.phase("deep_merge", keys=len(dict1)):
    result = merge(dict1, dict2, deep=True)
```

### Phase 4: Replace Debug Prints (30 min)

Replace all `print()` statements in `taxonomies.py` with appropriate logger calls.

## Testing Strategy

1. **Unit tests:** Verify logger is called with expected events (use mock)
2. **Integration tests:** Build example site, verify log output contains expected events
3. **Manual testing:** Enable verbose logging, verify useful information is shown

## Success Metrics

After implementation, we should be able to:

1. ✅ See warnings when data files are missing
2. ✅ Identify broken cross-references with suggestions
3. ✅ Track fast vs slow path usage for `related_posts()`
4. ✅ Debug image loading issues (Pillow availability, file paths)
5. ✅ Generate build reports showing template function usage patterns
6. ✅ Correlate template errors with underlying function failures

## Related Work

- **Current:** `bengal.rendering.errors.TemplateRenderError` - Good Jinja2 error tracking
- **Current:** `bengal.utils.logger` - Excellent structured logging framework
- **Gap:** Template functions don't use the logger
- **Opportunity:** Low-hanging fruit for immediate observability improvement

## Appendix: Logger Usage Examples from Other Modules

### Example from `orchestration/content.py`:
```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

def process_content(files: List[Path]) -> List[Page]:
    with logger.phase("content_processing", file_count=len(files)):
        for file in files:
            logger.debug("processing_file", path=str(file))
            # ...
        logger.info("content_processed", pages=len(pages))
```

### Example from `cache/build_cache.py`:
```python
def load_cache(self) -> Dict[str, Any]:
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        logger.debug("cache_loaded", entries=len(cache))
        return cache
    except FileNotFoundError:
        logger.debug("cache_not_found", creating_new=True)
        return {}
    except json.JSONDecodeError as e:
        logger.warning("cache_corrupted", error=str(e), resetting=True)
        return {}
```

These are the patterns we should follow in template functions.

---

**Next Steps:**
1. Review this analysis
2. Prioritize which functions to add logging to first
3. Implement in phases (can be done incrementally)
4. Update tests to verify logger usage

