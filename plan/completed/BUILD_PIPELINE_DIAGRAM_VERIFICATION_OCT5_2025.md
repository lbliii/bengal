# Build Pipeline Flow Diagram Verification
**Date:** October 5, 2025  
**Diagram Location:** ARCHITECTURE.md lines 417-468  
**Status:** ❌ INACCURATE - Multiple significant errors found

## Executive Summary

The Build Pipeline Flow diagram contains **several significant inaccuracies** that misrepresent the actual build process. The most critical error is showing `Site.build()` directly calling discovery methods, when in reality it immediately delegates to `BuildOrchestrator` which then handles discovery through specialized orchestrators.

## Verification Methodology

Examined the following source files:
- `bengal/core/site.py` - Site class and build() method
- `bengal/orchestration/build.py` - BuildOrchestrator (main coordinator)
- `bengal/orchestration/content.py` - ContentOrchestrator (discovery)
- `bengal/orchestration/taxonomy.py` - TaxonomyOrchestrator
- `bengal/orchestration/menu.py` - MenuOrchestrator
- `bengal/orchestration/render.py` - RenderOrchestrator
- `bengal/orchestration/postprocess.py` - PostprocessOrchestrator
- `bengal/orchestration/incremental.py` - IncrementalOrchestrator
- `bengal/discovery/content_discovery.py` - ContentDiscovery class
- `bengal/discovery/asset_discovery.py` - AssetDiscovery class
- `bengal/cache/build_cache.py` - BuildCache class
- `bengal/rendering/pipeline.py` - RenderingPipeline
- `bengal/rendering/template_engine.py` - TemplateEngine

## Detailed Findings

### ❌ CRITICAL ERROR #1: Discovery Flow is Wrong

**Diagram Shows:**
```
CLI->>Site: build()
Site->>Discovery: discover_content()
Discovery->>Site: pages, sections
Site->>Discovery: discover_assets()
Discovery->>Site: assets
Site->>Site: _setup_page_references()
Site->>Site: _apply_cascades()
Site->>Orchestration: BuildOrchestrator.build()
```

**Actual Code:**
```python
# bengal/core/site.py (lines 310-327)
def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False) -> BuildStats:
    """Build the entire site."""
    from bengal.orchestration import BuildOrchestrator
    
    orchestrator = BuildOrchestrator(self)
    return orchestrator.build(parallel=parallel, incremental=incremental, verbose=verbose)
```

**Reality:**
1. `Site.build()` **immediately** delegates to `BuildOrchestrator.build()`
2. There are NO discovery calls in `Site.build()`
3. Discovery happens **inside** `BuildOrchestrator.build()` via `ContentOrchestrator.discover()`

**Impact:** This is a fundamental misrepresentation of the architecture. The delegation pattern is completely lost.

---

### ❌ CRITICAL ERROR #2: Missing ContentOrchestrator

**What's Missing:**
- The diagram shows `Site` directly calling `Discovery` classes
- In reality, `BuildOrchestrator` uses `ContentOrchestrator` as an intermediary

**Actual Flow:**
```python
# bengal/orchestration/build.py (lines 90-98)
with self.logger.phase("discovery", content_dir=str(content_dir)):
    discovery_start = time.time()
    self.content.discover()  # ContentOrchestrator.discover()
    self.stats.discovery_time_ms = (time.time() - discovery_start) * 1000
```

```python
# bengal/orchestration/content.py (lines 39-45)
def discover(self) -> None:
    """Discover all content and assets."""
    self.discover_content()  # Creates ContentDiscovery internally
    self.discover_assets()   # Creates AssetDiscovery internally
```

**Why This Matters:**
- Shows the orchestration layer properly
- Demonstrates separation of concerns
- ContentOrchestrator also handles setup tasks (_setup_page_references, _apply_cascades, _build_xref_index)

---

### ⚠️ ERROR #3: Incremental Build Logic Oversimplified

**Diagram Shows:**
```
loop For each page
    Orchestration->>Cache: needs_rebuild(page)?
    alt Changed or new
        Cache-->>Orchestration: yes
        Orchestration->>Rendering: render_page(page)
    else Unchanged
        Cache-->>Orchestration: no (skip)
    end
end
```

**Actual Code:**
```python
# bengal/orchestration/build.py (lines 145-178)
# Phase 5: Determine what to build (incremental)
with self.logger.phase("incremental_filtering", enabled=incremental):
    pages_to_build = self.site.pages
    assets_to_process = self.site.assets
    
    if incremental:
        pages_to_build, assets_to_process, change_summary = self.incremental.find_work(
            verbose=verbose
        )
        # ...filtering happens here...

# Phase 6: Render Pages
with self.logger.phase("rendering", page_count=len(pages_to_build), parallel=parallel):
    # ...render filtered list...
```

**Reality:**
1. Incremental filtering happens **before** rendering phase (Phase 5 vs Phase 6)
2. It's a **bulk filter** operation, not per-page checks in a loop
3. The filtering is done by `IncrementalOrchestrator.find_work()` which returns lists
4. Rendering then processes the filtered list (either in parallel or sequentially)

**Why This Matters:**
- Performance implications (bulk filtering vs per-page)
- Architecture clarity (phases are separate)
- Parallel rendering would be impossible with per-page incremental checks

---

### ⚠️ ERROR #4: Missing Critical Phases

**Missing from Diagram:**
1. **Section Finalization** (Phase 2) - Ensures all sections have index pages
2. **Section Validation** (Phase 2) - Validates section structure
3. **Cross-reference Index Building** - ContentOrchestrator builds xref_index after discovery
4. **Health Check** (Phase 10) - Validates build output, links, performance, etc.
5. **Initialization** (Phase 0) - Cache and tracker initialization

**Actual Phase Sequence (from code):**
```
Phase 0: Initialization (cache, tracker)
Phase 1: Content Discovery (pages, sections, assets)
Phase 2: Section Finalization & Validation
Phase 3: Taxonomies & Dynamic Pages
Phase 4: Menus
Phase 5: Incremental Filtering (determine what to build)
Phase 6: Render Pages
Phase 7: Process Assets
Phase 8: Post-processing (sitemap, RSS, etc.)
Phase 9: Update Cache
Phase 10: Health Check
```

---

### ⚠️ ERROR #5: Taxonomy Phase Naming

**Diagram Shows:**
```
Orchestration->>Orchestration: collect_taxonomies()
Orchestration->>Orchestration: generate_dynamic_pages()
```

**Actual Code:**
```python
# bengal/orchestration/build.py (lines 131-137)
with self.logger.phase("taxonomies"):
    taxonomy_start = time.time()
    self.taxonomy.collect_and_generate()  # Single method!
    self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
```

```python
# bengal/orchestration/taxonomy.py (lines 44-50)
def collect_and_generate(self) -> None:
    """Collect taxonomies and generate dynamic pages."""
    self.collect_taxonomies()
    self.generate_dynamic_pages()
```

**Issue:** The diagram shows two separate orchestrator calls, but there's actually one (`collect_and_generate()`) which internally calls both methods.

---

### ⚠️ ERROR #6: Post-processing Details

**Diagram Shows:**
```
Orchestration->>PostProcess: generate_sitemap()
Orchestration->>PostProcess: generate_rss()
Orchestration->>PostProcess: generate_search_index()
```

**Actual Code:**
```python
# bengal/orchestration/build.py (lines 215-219)
with self.logger.phase("postprocessing", parallel=parallel):
    postprocess_start = time.time()
    self.postprocess.run(parallel=parallel)  # Single call!
    self.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000
```

```python
# bengal/orchestration/postprocess.py (lines 39-76)
def run(self, parallel: bool = True) -> None:
    """Perform post-processing tasks."""
    tasks = []
    tasks.append(('special pages', self._generate_special_pages))
    if self.site.config.get("generate_sitemap", True):
        tasks.append(('sitemap', self._generate_sitemap))
    if self.site.config.get("generate_rss", True):
        tasks.append(('rss', self._generate_rss))
    output_formats_config = self.site.config.get("output_formats", {})
    if output_formats_config.get("enabled", True):
        tasks.append(('output formats', self._generate_output_formats))
    if self.site.config.get("validate_links", True):
        tasks.append(('link validation', self._validate_links))
    # ...run tasks...
```

**Issues:**
1. Single `run()` call, not individual method calls
2. "generate_search_index()" should be "generate_output_formats()"
3. Missing "special pages" generation (404, etc.)
4. Missing "link validation"
5. Post-processing tasks can run in parallel

---

### ✅ ACCURATE: Menu Data Flow

**Diagram Shows:**
```
Orchestration->>Menus: build_menus()
Menus-->>Orchestration: menu data
...
Rendering->>Menus: get menu data
```

**Actual Code:**
```python
# bengal/orchestration/build.py (lines 140-142)
with self.logger.phase("menus"):
    self.menu.build()
    self.logger.info("menus_built", menu_count=len(self.site.menu))
```

```python
# bengal/orchestration/menu.py (lines 33-66)
def build(self) -> None:
    """Build all menus from config and page frontmatter."""
    # ...builds menus...
    self.site.menu[menu_name] = builder.build_hierarchy()
```

```python
# bengal/rendering/template_engine.py (lines 168-179)
def _get_menu(self, menu_name: str = 'main') -> list:
    """Get menu items as dicts for template access."""
    menu = self.site.menu.get(menu_name, [])
    return [item.to_dict() for item in menu]
```

**Status:** ✅ This is correct! Menus are built once, stored in `site.menu`, and accessed during rendering.

---

### ✅ ACCURATE: Rendering Steps

**Diagram Shows:**
```
Rendering->>Rendering: parse markdown
Rendering->>Rendering: apply plugins
Rendering->>Rendering: render template (with menus)
```

**Actual Code:**
```python
# bengal/rendering/pipeline.py (lines 113-153)
def process_page(self, page: Page) -> None:
    # Stage 1 & 2: Parse content
    if hasattr(self.parser, 'parse_with_toc_and_context'):
        parsed_content, toc = self.parser.parse_with_toc_and_context(...)
    
    page.parsed_ast = parsed_content
    
    # Stage 3: Apply plugins (during parsing)
    # (plugins are part of markdown parser pipeline)
    
    # Stage 4: Render with template
    html = self.renderer.render_page(page, parsed_content)
    
    # Stage 5: Write output
    self._write_output(page, html)
```

**Status:** ✅ Mostly accurate representation.

---

### ✅ ACCURATE: Cache Operations

**Diagram Shows:**
```
Site->>Cache: save_cache()
```

**Actual Code:**
```python
# bengal/orchestration/build.py (lines 222-225)
if incremental or self.site.config.get("cache_enabled", True):
    with self.logger.phase("cache_save"):
        self.incremental.save_cache(pages_to_build, assets_to_process)
```

**Status:** ✅ Correct, though it's actually `IncrementalOrchestrator.save_cache()`, not a direct `Cache` class call.

---

## Recommended Corrections

### Critical Priority

1. **Fix Discovery Flow:**
   ```mermaid
   CLI->>Site: build()
   Site->>BuildOrch: BuildOrchestrator.build()
   BuildOrch->>ContentOrch: discover()
   ContentOrch->>ContentDiscovery: discover content/assets
   ContentOrch->>ContentOrch: setup_references & cascades
   ```

2. **Fix Incremental Build:**
   ```mermaid
   # Phase 5: Filter what needs building
   BuildOrch->>IncrementalOrch: find_work()
   IncrementalOrch->>Cache: check changes
   IncrementalOrch-->>BuildOrch: pages_to_build, assets_to_process
   
   # Phase 6: Render filtered list
   loop For each page in pages_to_build
       BuildOrch->>RenderOrch: render(page)
   end
   ```

3. **Add Missing Phases:**
   - Section Finalization (Phase 2)
   - Health Check (Phase 10)
   - Initialization (Phase 0)

### Medium Priority

4. **Fix Post-processing:**
   ```mermaid
   BuildOrch->>PostprocessOrch: run(parallel)
   PostprocessOrch->>PostprocessOrch: special_pages, sitemap, rss, output_formats, link_validation
   ```

5. **Show Orchestrator Layer:**
   - Add ContentOrchestrator, TaxonomyOrchestrator, MenuOrchestrator, RenderOrchestrator, etc.
   - Show proper delegation pattern

---

## Conclusion

The current diagram is **fundamentally inaccurate** in its representation of:
1. **Discovery flow** - Shows Site calling discovery directly (wrong)
2. **Orchestration architecture** - Misses the orchestrator layer
3. **Incremental builds** - Oversimplifies to per-page checks
4. **Build phases** - Missing several critical phases

**Impact:** Someone using this diagram to understand the codebase would have significant misconceptions about:
- The delegation/orchestration pattern
- The role of specialized orchestrators
- How incremental builds work
- The actual build phase sequence

**Recommendation:** **Rewrite this diagram** with the correct flow, or add a note that it's a simplified view and doesn't match implementation details.

---

## Accurate Elements (Keep These)

✅ Menu building and access pattern  
✅ Basic rendering steps (parse → plugins → template)  
✅ Cache save operation  
✅ Asset processing concept  
✅ Taxonomy collection and dynamic page generation (though naming needs fixing)

---

## File References for Updates

- **Diagram location:** `ARCHITECTURE.md` lines 417-468
- **Recommended approach:** Create a new "Detailed Build Flow" diagram showing all 10 phases
- **Consider:** Adding both "simplified" and "detailed" versions for different audiences

