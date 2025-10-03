# Performance Anti-Patterns Audit 🕵️

**Date:** October 3, 2025  
**Status:** Investigation Complete  
**Trigger:** Parallel build was 2.1x SLOWER than sequential

---

## 🎯 Executive Summary

**FOUND:** 2 catastrophic anti-patterns  
**FIXED:** 1 (parallel pipelines)  
**REMAINING:** 1 (mistune parser recreation)

### Impact Table

| Issue | Location | Impact | Status |
|-------|----------|--------|--------|
| **Pipeline Per Page** | `site.py:498` | **CATASTROPHIC** | ✅ **FIXED** |
| **Parser Per Page** | `parser.py:224` | **MAJOR** | 🔴 **OPEN** |

---

## ✅ Issue #1: Pipeline Per Page (FIXED)

### Location
`bengal/core/site.py:498` - `_build_parallel()`

### Problem
```python
def process_page_with_pipeline(page):
    # Create a new pipeline instance for this thread with same settings
    thread_pipeline = RenderingPipeline(self, tracker, quiet=quiet, build_stats=build_stats)
    thread_pipeline.process_page(page)
```

**Anti-Pattern:** Created 82 separate `RenderingPipeline` instances (one per page)

### Cost Per Pipeline
Each `RenderingPipeline` creation:
1. Creates new `TemplateEngine`
2. Creates new Jinja2 `Environment`
3. Loads and parses all templates from disk
4. Registers 30+ custom template functions
5. Sets up filters, globals, autoescape, etc.

**Total:** ~82 expensive Jinja2 environment initializations

### Impact
- **Before:** 1.88s total (1.74s rendering)
- **After:** 0.89s total (700ms rendering)
- **Speedup:** 2.1x faster! 🚀

### Fix
Use thread-local storage to reuse pipelines per thread:
```python
if not hasattr(_thread_local, 'pipeline'):
    _thread_local.pipeline = RenderingPipeline(self, tracker, quiet=quiet, build_stats=build_stats)
_thread_local.pipeline.process_page(page)
```

**Result:** Only 4 pipelines created (one per worker thread)

---

## 🔴 Issue #2: Mistune Parser Per Page (OPEN)

### Location
`bengal/rendering/parser.py:224` - `MistuneParser.parse_with_context()`

### Problem
```python
def parse_with_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> str:
    # Create temporary parser with variable substitution
    md_with_vars = self._mistune.create_markdown(
        plugins=[
            'table',
            'strikethrough',
            'task_lists',
            'url',
            'footnotes',
            'def_list',
            plugin_documentation_directives,
            VariableSubstitutionPlugin(context),  # Add variable substitution
        ],
        renderer='html',
    )
    return md_with_vars(content)
```

**Anti-Pattern:** Creates a NEW mistune parser for EVERY page (82 times)

### Call Chain
1. `pipeline.process_page(page)` - Line 104
2. `parser.parse_with_toc_and_context()` - Line 293
3. `parser.parse_with_context()` - Line 224 ← **Creates new parser here**

### Why It's Done This Way
The `VariableSubstitutionPlugin(context)` needs page-specific context:
```python
context = {
    'page': page,        # Different for each page
    'site': self.site,   # Same
    'config': config     # Same
}
```

So we can't just cache one parser - the context changes per page.

### Cost Per Parser
Each `create_markdown()` call:
1. Creates new Markdown instance
2. Initializes 7+ plugins (table, strikethrough, task_lists, etc.)
3. Sets up renderer
4. Configures all plugin hooks

**Total:** 82 expensive mistune parser initializations

### Estimated Impact
- **Current:** ~100-200ms wasted on parser creation
- **Optimized:** ~10-20ms total
- **Potential Gain:** ~150ms (15-20% faster builds)

### Solution Options

#### Option 1: Cache Parser, Update Context ⭐ **RECOMMENDED**
Store the parser and just update the plugin's context:
```python
class MistuneParser(BaseMarkdownParser):
    def __init__(self):
        # ... existing init code ...
        self._var_substitution_plugin = None
        self._parser_with_vars = None
    
    def parse_with_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Lazy init parser with variable substitution on first use
        if self._parser_with_vars is None:
            self._var_substitution_plugin = VariableSubstitutionPlugin(context)
            self._parser_with_vars = self._mistune.create_markdown(
                plugins=[
                    'table', 'strikethrough', 'task_lists', 'url',
                    'footnotes', 'def_list',
                    plugin_documentation_directives,
                    self._var_substitution_plugin,
                ],
                renderer='html',
            )
        else:
            # Just update the context on existing plugin
            self._var_substitution_plugin.update_context(context)
        
        return self._parser_with_vars(content)
```

**Requires:** Adding `update_context()` method to `VariableSubstitutionPlugin`

**Complexity:** Low  
**Risk:** Low  
**Gain:** ~150ms

#### Option 2: Pool of Pre-Created Parsers
Maintain a small pool (e.g., 4-8) of pre-created parsers:
```python
class MistuneParser(BaseMarkdownParser):
    def __init__(self):
        # ... existing init code ...
        self._parser_pool = []
        self._pool_lock = threading.Lock()
        MAX_POOL_SIZE = 8
    
    def parse_with_context(self, content, metadata, context):
        # Get parser from pool or create new one
        with self._pool_lock:
            if self._parser_pool:
                parser_info = self._parser_pool.pop()
            else:
                parser_info = self._create_parser_with_vars()
        
        # Update context and parse
        parser_info['plugin'].update_context(context)
        result = parser_info['parser'](content)
        
        # Return to pool
        with self._pool_lock:
            if len(self._parser_pool) < MAX_POOL_SIZE:
                self._parser_pool.append(parser_info)
        
        return result
```

**Complexity:** Medium  
**Risk:** Low  
**Gain:** ~150ms

#### Option 3: Accept the Cost (Do Nothing)
Current implementation is clean and correct. The cost is:
- ~150ms on a ~900ms build = ~17% overhead
- Not terrible, but not great

**Complexity:** Zero  
**Risk:** Zero  
**Gain:** Zero

---

## 📊 Overall Performance Analysis

### Current State (After Fix #1)
| Component | Time | Notes |
|-----------|------|-------|
| Discovery | 27ms | ✅ Efficient |
| Taxonomies | 0.7ms | ✅ Excellent |
| Rendering | 700ms | ⚠️ Has Issue #2 (~150ms overhead) |
| Assets | 55ms | ✅ Good |
| Postprocess | 33ms | ✅ Good |
| **Total** | **890ms** | |

### Potential State (After Fix #2)
| Component | Time | Improvement |
|-----------|------|-------------|
| Rendering | ~550ms | -150ms |
| **Total** | **~740ms** | **17% faster** |

---

## 🔍 Other Areas Audited (All Clear ✅)

### Asset Processing
**Status:** ✅ Good  
- Already uses thread-local patterns
- No expensive re-initialization
- Smart parallelization threshold (5+ assets)

### Post-Processing
**Status:** ✅ Good  
- Simple function calls
- No expensive initialization
- Efficient parallel execution

### Discovery Phase
**Status:** ✅ Good  
- Single-pass directory walk
- Frontmatter parsed once per file
- No repeated work

### Config Lookups
**Status:** ✅ Good  
- No config.get() in hot rendering paths
- Config passed as parameter, not looked up repeatedly

### Thread-Local Parser Caching
**Status:** ✅ Already Optimized  
- Parser instances cached per thread
- Good use of thread-local storage

---

## 🎯 Recommendations

### Priority 1: Fix Issue #2 (Mistune Parser Recreation)
**Effort:** 1-2 hours  
**Impact:** ~150ms faster builds (17% improvement)  
**Risk:** Low

**Action:**
1. Add `update_context()` method to `VariableSubstitutionPlugin`
2. Cache parser in `MistuneParser.__init__()`
3. Update context instead of recreating parser

### Priority 2: Benchmark Large Sites
Test with 500+ page sites to see if there are other bottlenecks that emerge at scale.

### Priority 3: Profile Real Workloads
Use Python profiler to identify any other hot spots we might have missed.

---

## 📈 Performance Gains Summary

| Fix | Status | Improvement | Cumulative |
|-----|--------|-------------|------------|
| Baseline (broken parallel) | - | - | 1.88s |
| **Fix #1: Thread-local pipelines** | ✅ Done | -990ms | **0.89s** |
| **Fix #2: Cache mistune parser** | 🔴 Open | -150ms | **~0.74s** |
| **Total Potential** | | **-1.14s** | **2.5x faster!** |

---

## 🎉 Conclusion

We found and fixed one **catastrophic** anti-pattern (82 pipelines → 4 pipelines), resulting in a **2.1x speedup**.

One more **major** anti-pattern remains (82 parsers → 1 cached parser), which could give us another **17% speedup**.

Overall system design is solid - no other major issues found. The codebase uses good patterns like:
- Thread-local storage for parser caching
- Smart parallelization thresholds
- Efficient single-pass algorithms
- Minimal repeated work

Great job on the overall architecture! Just these two initialization patterns needed fixing.

