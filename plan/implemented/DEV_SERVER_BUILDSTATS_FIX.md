# Dev Server BuildStats Fix

**Status:** ✅ Complete  
**Date:** October 9, 2025  
**Issue:** Dev server and live reload not working due to AttributeError

## Problem

The dev server was failing to start with the error:
```
❌ Server failed: 'BuildStats' object has no attribute 'get'
Aborted!
```

The server would complete the initial build successfully, but then crash before starting the HTTP server.

## Root Cause

The dev server code was treating `BuildStats` objects as dictionaries and using the `.get()` method:

```python
# ❌ Wrong - BuildStats is a dataclass, not a dict
stats.get('pages_rendered', 0)
stats.get('total_duration_ms', 0)
stats.get('cache_hits', 0)
stats.get('cache_misses', 0)
```

However, `BuildStats` is a dataclass (defined in `bengal/utils/build_stats.py`) with attributes, not a dictionary.

## Solution

Updated both files to use attribute access instead of dictionary access:

### 1. `bengal/server/dev_server.py` (lines 68-70)

**Before:**
```python
logger.debug("initial_build_complete",
            pages_built=stats.get('pages_rendered', 0),
            duration_ms=stats.get('total_duration_ms', 0))
```

**After:**
```python
logger.debug("initial_build_complete",
            pages_built=stats.total_pages,
            duration_ms=stats.build_time_ms)
```

### 2. `bengal/server/build_handler.py` (lines 121-125)

**Before:**
```python
logger.info("rebuild_complete",
           duration_seconds=round(build_duration, 2),
           pages_built=stats.get('pages_rendered', 0),
           cache_hits=stats.get('cache_hits', 0),
           cache_misses=stats.get('cache_misses', 0))
```

**After:**
```python
logger.info("rebuild_complete",
           duration_seconds=round(build_duration, 2),
           pages_built=stats.total_pages,
           incremental=stats.incremental,
           parallel=stats.parallel)
```

## Testing

After the fix, tested the following:

1. ✅ **Server Startup:** Server starts successfully
2. ✅ **HTTP Serving:** Pages load correctly (`http://localhost:5173/`)
3. ✅ **Navigation:** Can navigate to different pages (`/docs/`)
4. ✅ **Live Reload Script:** Script is properly injected into HTML
5. ✅ **SSE Endpoint:** `/__bengal_reload__` endpoint is accessible
6. ✅ **File Watching:** Changes to content files trigger rebuilds

### Test Results

```bash
$ curl -I http://localhost:5173/
HTTP/1.0 200 OK
Server: Bengal/1.0
Content-type: text/html
Content-Length: 25263
```

```bash
$ curl -s http://localhost:5173/ | grep "Bengal Live Reload"
    // Bengal Live Reload
```

## BuildStats Reference

For reference, `BuildStats` has these attributes (not dict keys):

- `total_pages` (not `pages_rendered`)
- `build_time_ms` (not `total_duration_ms`)
- `regular_pages`
- `generated_pages`
- `total_assets`
- `total_sections`
- `taxonomies_count`
- `parallel`
- `incremental`
- `discovery_time_ms`
- `rendering_time_ms`
- `assets_time_ms`
- `postprocess_time_ms`
- And more...

## Additional Notes

### Other Files Using stats.get()

These files also use `stats.get()` but they might be receiving dict stats from different sources:

- `bengal/health/report.py:398`
- `bengal/health/validators/performance.py` (multiple lines)

These weren't causing issues because they're not in the critical dev server startup path, but they should be reviewed and potentially updated if they also receive `BuildStats` objects.

### Cache Clearing

Had to clear Python `__pycache__` files to ensure updated code was loaded:
```bash
find . -type d -name __pycache__ -path "*/bengal/server/*" -exec rm -rf {} +
```

## Impact

- Dev server now starts successfully ✅
- Live reload works as expected ✅
- File watching triggers rebuilds ✅
- Server logs properly ✅
- No more crashes on startup ✅

## Files Modified

1. `/Users/llane/Documents/github/python/bengal/bengal/server/dev_server.py`
2. `/Users/llane/Documents/github/python/bengal/bengal/server/build_handler.py`

