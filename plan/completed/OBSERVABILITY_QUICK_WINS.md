# Observability Quick Wins - Priority Fixes

**Goal:** Get the biggest observability improvements with minimal effort.

---

## 🎯 Top 3 Priority Fixes (2-3 hours total)

### 1. **Cache System Logging** (~45 min)
**File:** `bengal/cache/build_cache.py`

**Add at top:**
```python
from bengal.utils.logger import get_logger
logger = get_logger(__name__)
```

**Replace print statements:**
```python
# Line 109: Cache load failure
logger.warning("cache_load_failed", 
              cache_path=str(cache_path), 
              error=str(e),
              action="using_fresh_cache")

# Line 140: Cache save failure  
logger.warning("cache_save_failed",
              cache_path=str(cache_path),
              error=str(e),
              impact="incremental_builds_disabled")

# Line 160: File hash failure
logger.warning("file_hash_failed",
              file_path=str(file_path),
              error=str(e),
              fallback="empty_hash")
```

**Add cache metrics:**
```python
def get_cache_stats(self) -> Dict[str, Any]:
    """Get cache statistics with logging."""
    stats = {
        'tracked_files': len(self.file_hashes),
        'dependencies': sum(len(deps) for deps in self.dependencies.values()),
        'taxonomy_terms': len(self.taxonomy_deps),
        'parsed_content_cached': len(self.parsed_content)
    }
    
    logger.info("cache_stats", **stats)
    return stats
```

**Impact:** Better incremental build debugging, visibility into cache failures.

---

### 2. **Discovery System Logging** (~45 min)  
**File:** `bengal/discovery/content_discovery.py`

**Add at top:**
```python
from bengal.utils.logger import get_logger
logger = get_logger(__name__)
```

**Add to `discover()` method:**
```python
def discover(self) -> Tuple[List[Section], List[Page]]:
    """Discover all content in the content directory."""
    logger.info("content_discovery_start", content_dir=str(self.content_dir))
    
    if not self.content_dir.exists():
        logger.warning("content_dir_missing", 
                      content_dir=str(self.content_dir),
                      action="returning_empty")
        return self.sections, self.pages
    
    # ... existing discovery logic ...
    
    logger.info("content_discovery_complete",
               sections_found=len(self.sections),
               pages_found=len(self.pages),
               top_level_sections=len([s for s in self.sections if not s.parent]))
    
    return self.sections, self.pages
```

**Add to `_create_page()` method:**
```python
def _create_page(self, file_path: Path) -> Page:
    try:
        # ... existing logic ...
        logger.debug("page_created", 
                    page_path=str(file_path),
                    slug=page.slug)
        return page
    except Exception as e:
        logger.error("page_creation_failed",
                    file_path=str(file_path),
                    error=str(e),
                    error_type=type(e).__name__)
        raise
```

**Impact:** Understand why content isn't being discovered, debug missing pages.

---

### 3. **Asset Processing Logging** (~30 min)
**File:** `bengal/orchestration/asset.py`

**Add at top:**
```python
from bengal.utils.logger import get_logger
```

**Add to `__init__`:**
```python
def __init__(self, site: 'Site'):
    self.site = site
    self.logger = get_logger(__name__)
```

**Replace print statements:**
```python
# Line 157 - Sequential processing error
self.logger.error("asset_processing_failed",
                 asset_path=str(asset.source_path),
                 asset_type=asset.asset_type,
                 error=str(e))

# Lines 196-202 - Parallel processing errors
if errors:
    self.logger.error("asset_batch_processing_failed",
                     total_errors=len(errors),
                     total_assets=len(assets),
                     first_errors=errors[:5])
    # Keep the print for user visibility
```

**Add metrics:**
```python
def process(self, assets: List['Asset'], parallel: bool = True) -> None:
    """Process all assets (copy, minify, optimize, fingerprint)."""
    if not assets:
        self.logger.info("asset_processing_skipped", reason="no_assets")
        return
    
    self.logger.info("asset_processing_start",
                    total_assets=len(assets),
                    mode="parallel" if parallel else "sequential",
                    minify=minify,
                    optimize=optimize)
    
    start_time = time.time()
    
    # ... existing processing logic ...
    
    duration_ms = (time.time() - start_time) * 1000
    self.logger.info("asset_processing_complete",
                    assets_processed=len(assets),
                    duration_ms=duration_ms,
                    throughput=len(assets) / (duration_ms / 1000))
```

**Impact:** Track asset processing failures, measure performance.

---

## 📊 Expected Results After Quick Wins

### **Before:**
```
Warning: Failed to load cache from /path/to/cache: [Errno 2] No such file or directory
Starting with fresh cache
```

### **After (in build.log):**
```json
{
  "timestamp": "2025-10-08T10:30:45.123456",
  "level": "WARNING",
  "logger_name": "bengal.cache.build_cache",
  "event_type": "cache_load_failed",
  "message": "cache_load_failed",
  "phase": "initialization",
  "context": {
    "cache_path": "/path/to/cache",
    "error": "[Errno 2] No such file or directory",
    "action": "using_fresh_cache"
  }
}
```

### **Benefits:**
✅ Searchable structured logs  
✅ Filterable by log level  
✅ Better error context  
✅ Phase correlation  
✅ Historical log analysis  

---

## 🚀 Testing Quick Wins

```bash
# Build with dev profile to see all logs
bengal build --dev --log-file quick-wins.log

# Check structured logs
cat quick-wins.log | jq '.event_type' | sort | uniq -c

# Check cache logs specifically
cat quick-wins.log | jq 'select(.logger_name | contains("cache"))'

# Check discovery logs
cat quick-wins.log | jq 'select(.event_type | contains("discovery"))'

# Check asset logs  
cat quick-wins.log | jq 'select(.event_type | contains("asset"))'
```

---

## 📋 Validation Checklist

After implementing quick wins, verify:

- [ ] Cache operations logged with structured events
- [ ] Discovery phase shows page/section counts
- [ ] Asset processing shows success/failure counts
- [ ] All errors include `error` and `error_type` fields
- [ ] Phase correlation works (events tagged with current phase)
- [ ] Log file is valid JSONL format
- [ ] No more bare `print()` statements for errors
- [ ] Existing functionality unchanged (no regressions)

---

## 🎓 Pattern to Follow

For any new module, follow this pattern:

```python
from bengal.utils.logger import get_logger

class MyModule:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def my_operation(self):
        """Do something important."""
        self.logger.info("operation_start", param1=value1)
        
        try:
            # ... do work ...
            
            self.logger.info("operation_complete",
                           duration_ms=duration,
                           items_processed=count)
        except Exception as e:
            self.logger.error("operation_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                            context="additional info")
            raise
```

---

## 🔗 Next Steps

After quick wins are complete:

1. Run full build and check logs: `bengal build --dev`
2. Review log output quality
3. Move on to **Priority 2** items from main analysis
4. Consider adding cache hit/miss metrics
5. Add correlation IDs for build tracking

---

**Time to complete: 2-3 hours**  
**Value delivered: High - fixes most visible gaps**  
**Risk: Low - additive changes only**

