# Bengal SSG - Observability Gaps Analysis

**Date:** October 8, 2025  
**Status:** Analysis Complete  
**Priority:** Medium - Good foundation, incremental improvements needed

---

## Executive Summary

Bengal has **excellent observability infrastructure** in place, with structured logging, performance metrics collection, health checks, and build profiles. However, there are **inconsistent adoption patterns** across the codebase where some modules still use basic `print()` statements instead of the structured logging system.

**Overall Grade:** B+ (Good foundation, needs consistency)

---

## ✅ What's Working Well

### 1. **Structured Logging System** (`bengal/utils/logger.py`)
- ✨ **Excellent design** with phase-aware logging
- Context propagation and timing built-in
- Memory tracking integration with `tracemalloc`
- JSON and console output formats
- LogLevel hierarchy (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Global logger registry with `get_logger(__name__)`

### 2. **Performance Metrics** 
- **PerformanceCollector** (`bengal/utils/performance_collector.py`)
  - Build time tracking
  - Memory profiling (RSS and heap)
  - Persistent metrics storage (`.bengal-metrics/`)
- **PerformanceReport** (`bengal/utils/performance_report.py`)
  - Historical metrics analysis
  - Trend detection
  - Multiple output formats (table, JSON, summary)

### 3. **Build Statistics** (`bengal/utils/build_stats.py`)
- Comprehensive build metrics
- Template error collection
- Warning categorization (jinja2, preprocessing, link, other)
- Directive usage tracking
- Phase timing breakdown

### 4. **Health Check System** (`bengal/health/`)
- 10+ validators for different aspects
- Extensible validator architecture
- Profile-based validator filtering
- Rich reporting with recommendations

### 5. **Build Profile System** (`bengal/utils/profile.py`)
- Persona-based observability (Writer, Theme-Dev, Developer)
- Smart feature toggling per profile
- Clean separation of concerns

### 6. **Error Handling**
- Rich template error system (`bengal/rendering/errors.py`)
- Structured error context with suggestions
- Nice visual error display

---

## ⚠️ Observability Gaps Identified

### **Priority 1: Critical Gaps**

#### 1.1 Cache System - No Structured Logging
**Files:** 
- `bengal/cache/build_cache.py`
- `bengal/cache/dependency_tracker.py`

**Current State:**
```python
# build_cache.py line 109
print(f"Warning: Failed to load cache from {cache_path}: {e}")
print("Starting with fresh cache")

# build_cache.py line 140
print(f"Warning: Failed to save cache to {cache_path}: {e}")

# build_cache.py line 160
print(f"Warning: Failed to hash file {file_path}: {e}")
```

**Impact:** 
- Cache failures are silent in production
- No visibility into cache performance (hit/miss rates)
- Can't debug incremental build issues effectively

**Recommendation:**
```python
from bengal.utils.logger import get_logger

class BuildCache:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def load(cls, cache_path: Path) -> 'BuildCache':
        # ...
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning("cache_load_failed", 
                          cache_path=str(cache_path), 
                          error=str(e),
                          fallback="fresh_cache")
```

#### 1.2 Discovery System - Basic Print Statements
**Files:**
- `bengal/discovery/content_discovery.py`
- `bengal/discovery/asset_discovery.py`

**Current State:**
- No logging of discovery metrics (files found, skipped, errors)
- Silent failures on malformed frontmatter
- No visibility into discovery performance

**Impact:**
- Users don't know why content isn't discovered
- Hard to debug missing pages
- No metrics on content growth over time

**Recommendation:**
Add structured logging for:
- Files discovered vs skipped
- Frontmatter parsing errors
- Discovery duration per section
- Content type distribution

#### 1.3 Config Loading - Minimal Observability
**Files:**
- `bengal/config/loader.py`

**Current State:**
```python
# line 60
print("Warning: No configuration file found, using defaults")

# line 99
print(f"❌ Error loading config from {config_path}: {e}")
```

**Impact:**
- Config errors may be overlooked
- No visibility into which config values are actually used
- Missing config validation events

**Recommendation:**
- Log config file discovery
- Log all config overrides
- Log validation warnings with suggestions


### **Priority 2: Medium Gaps**

#### 2.1 Asset Processing - Inconsistent Logging
**Files:**
- `bengal/orchestration/asset.py`

**Current State:**
```python
# line 157
print(f"Warning: Failed to process asset {asset.source_path}: {e}")

# Parallel processing errors collected but just printed (lines 196-202)
```

**Impact:**
- Asset processing failures are hard to track
- No metrics on asset optimization success rates
- Parallel asset failures may be missed

**Recommendation:**
```python
self.logger.error("asset_processing_failed",
                 asset_path=str(asset.source_path),
                 asset_type=asset.asset_type,
                 operation="minify/optimize",
                 error=str(e))
```

#### 2.2 Postprocess System - Basic Print Statements
**Files:**
- `bengal/postprocess/sitemap.py`
- `bengal/postprocess/rss.py`
- `bengal/postprocess/special_pages.py`

**Current State:**
```python
# sitemap.py line 74
print(f"   └─ Sitemap ✓")
```

**Impact:**
- No visibility into sitemap/RSS generation issues
- Can't track which pages are included/excluded
- No error handling for XML generation

**Recommendation:**
Add structured logging with:
- Pages included in sitemap
- RSS feed generation metrics
- XML generation errors

#### 2.3 Template Functions - Error Handling
**Files:**
- `bengal/rendering/template_functions/*.py` (multiple files)

**Current State:**
Many template functions have try/except but don't log errors properly.

**Impact:**
- Template function errors are silent
- Hard to debug template issues
- No metrics on which functions fail most

**Recommendation:**
```python
def my_template_function():
    try:
        # ...
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning("template_function_error",
                      function="my_template_function",
                      error=str(e),
                      fallback="default_value")
```

#### 2.4 Dev Server - Minimal File Watch Logging
**Files:**
- `bengal/server/dev_server.py`

**Current State:**
File changes trigger rebuilds but limited observability:
```python
# line 209
print(f"  {timestamp} │ \033[33m📝 File changed:\033[0m {file_name}")
```

**Impact:**
- Can't see which files triggered rebuilds
- No metrics on rebuild frequency
- Hard to debug watch issues

**Recommendation:**
- Log file watch events with full paths
- Log ignored files/patterns
- Track rebuild frequency and duration


### **Priority 3: Nice-to-Have Improvements**

#### 3.1 Missing Metrics

**Cache Hit Rate Tracking:**
```python
# Should track:
- cache_hits: int
- cache_misses: int
- cache_invalidations: int
```

**Build Phase Correlation:**
```python
# Add correlation IDs to link related log events
with logger.phase("rendering", build_id="abc123") as phase:
    # All logs in this phase get build_id
```

**Exception Context:**
Some exception handlers lose context:
```python
# Better context:
try:
    process_asset(asset)
except Exception as e:
    logger.error("asset_failed",
                asset=asset.path,
                asset_type=asset.type,
                stage="processing",
                error=str(e),
                traceback=traceback.format_exc())
```

#### 3.2 Log Aggregation Documentation

**Current State:** No documentation on:
- How to export logs to external systems
- Log format specifications
- Integration with logging platforms (ELK, Grafana Loki, etc.)

**Recommendation:** Add documentation for:
- Parsing JSONL log files
- Setting up log rotation
- Integrating with log aggregation platforms

#### 3.3 Metrics Export

**Current State:** Metrics stored locally in `.bengal-metrics/`

**Enhancement Ideas:**
- Prometheus exporter for CI/CD metrics
- StatsD integration for real-time metrics
- GitHub Actions integration for build time tracking

#### 3.4 Distributed Tracing

**Current State:** Not needed for single-process SSG

**Future Consideration:** If Bengal adds distributed builds (multiple machines), consider:
- OpenTelemetry integration
- Span tracking across workers
- Distributed build coordination


---

## 📊 Gap Summary by Module

| Module | Current State | Logger Usage | Print Usage | Exception Handling | Grade |
|--------|--------------|--------------|-------------|-------------------|-------|
| `orchestration/build.py` | ✅ Good | ✅ Yes | ⚠️ Some | ✅ Good | A |
| `rendering/pipeline.py` | ✅ Good | ❌ No | ✅ Structured | ✅ Excellent | A- |
| `rendering/errors.py` | ✅ Excellent | N/A | ✅ Structured | ✅ Excellent | A+ |
| `cache/` | ⚠️ Basic | ❌ No | ⚠️ Many | ⚠️ Warnings only | C |
| `discovery/` | ⚠️ Basic | ❌ No | ⚠️ Some | ⚠️ Basic | C+ |
| `config/` | ⚠️ Basic | ❌ No | ⚠️ Some | ⚠️ Basic | C+ |
| `orchestration/asset.py` | ⚠️ Mixed | ❌ No | ⚠️ Many | ⚠️ Basic | C+ |
| `postprocess/` | ⚠️ Basic | ❌ No | ⚠️ Many | ❌ Minimal | C |
| `server/` | ⚠️ Mixed | ❌ No | ✅ Structured | ✅ Good | B- |
| `health/` | ✅ Good | ✅ Yes | ⚠️ Some | ✅ Good | A- |
| `autodoc/` | ✅ Good | ❌ No | ✅ Structured | ✅ Good | B+ |
| `utils/` | ✅ Excellent | ✅ Yes | ✅ Structured | ✅ Excellent | A+ |

**Overall Average Grade: B+**


---

## 🎯 Recommended Action Plan

### **Phase 1: Foundation (1-2 days)**
1. ✅ Add logger to `BuildCache` and `DependencyTracker`
2. ✅ Add logger to `ContentDiscovery` and `AssetDiscovery`
3. ✅ Add logger to `ConfigLoader`

### **Phase 2: Consistency (2-3 days)**
4. Replace print statements with structured logging in:
   - Asset orchestration
   - Postprocess modules
   - Template functions
5. Add cache hit/miss metrics

### **Phase 3: Enhancement (1-2 days)**
6. Add correlation IDs for build tracking
7. Enhance exception context
8. Add metrics aggregation helpers

### **Phase 4: Documentation (1 day)**
9. Document log formats and fields
10. Add log aggregation integration guide
11. Document observability best practices


---

## 💡 Best Practices Going Forward

### **For New Code:**
1. ✅ Always use `get_logger(__name__)` instead of `print()`
2. ✅ Use structured logging with context:
   ```python
   logger.error("operation_failed", 
               file=str(path), 
               reason="permission_denied",
               user_action="check_file_permissions")
   ```
3. ✅ Log exceptions with context:
   ```python
   except Exception as e:
       logger.error("unexpected_error", 
                   operation="render_page",
                   page=page.path,
                   error=str(e),
                   error_type=type(e).__name__)
   ```

### **For Existing Code:**
1. When touching a file, migrate `print()` to `logger.*`
2. Add try/except with structured error logging
3. Add metrics for performance-critical operations

### **Log Level Guidelines:**
- **DEBUG:** Detailed info for developers (disabled in writer mode)
- **INFO:** Important events users should know about
- **WARNING:** Problems that don't stop the build
- **ERROR:** Failures that impact output quality
- **CRITICAL:** Build-stopping errors


---

## 🔍 Testing Observability

### **Manual Testing:**
```bash
# Test all log levels
bengal build --dev --log-file build.log

# Check JSON logs
cat build.log | jq '.level' | sort | uniq -c

# Test profile differences
bengal build                    # Writer profile (minimal)
bengal build --theme-dev        # Theme dev (moderate)
bengal build --dev             # Developer (full)
```

### **Automated Testing:**
Create tests for:
- Logger output format
- Log level filtering
- Phase timing accuracy
- Exception logging completeness


---

## 📚 Related Documentation

- Architecture: See `ARCHITECTURE.md` for system design
- Logging API: See `bengal/utils/logger.py` docstrings
- Health Checks: See `bengal/health/README.md` (if exists)
- Performance: See `bengal/utils/performance_*.py` for metrics


---

## 🎉 Conclusion

Bengal has a **solid observability foundation** that's ahead of most SSGs. The main issue is **inconsistent adoption** - some modules use the excellent structured logging system while others still use basic print statements.

**Key Strengths:**
- ✅ Structured logging with phase tracking
- ✅ Performance metrics collection
- ✅ Build profile system for different personas
- ✅ Health check system
- ✅ Rich error handling for templates

**Key Improvements Needed:**
- ⚠️ Migrate cache system to structured logging
- ⚠️ Add logging to discovery and config modules
- ⚠️ Consistent logging across all orchestrators
- ⚠️ Add cache metrics (hit/miss rates)

**Time Investment:** ~1 week for comprehensive improvements
**Maintenance Impact:** Low - mostly additive changes
**User Impact:** High - better debugging and troubleshooting experience

