# Memory Optimization Strategy for Large-Scale Builds

**Date:** 2025-10-09  
**Context:** Performance analysis revealed memory pressure at 4K-16K pages  
**Question:** Can we release pages from memory when they're no longer needed?  

---

## 🎯 Executive Summary

**Short Answer:** Yes! Pages can be strategically released, but we need to understand the **dependency graph** first.

**Key Insight:** Current architecture keeps **all 16K pages in memory** throughout the build because templates can reference **any page at any time** via:
- `site.pages` (direct access)
- `site.taxonomies` (tag/category pages)
- `doc('path/to/page')` (cross-references)
- `related_posts(page)` (pre-computed relationships)

**Opportunity:** Most pages are **not actually referenced** by templates. We can identify "islands" of pages with no incoming references and apply different strategies:

1. **Stream processing** (no dependencies)
2. **Lazy loading** (infrequent access)
3. **Serialization** (can be rehydrated)
4. **Graph-based pruning** (smart release)

---

## 📊 Current Memory Lifecycle

### Build Phase Timeline

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Discovery (all pages created)                   │
│   └─> 16K Page objects in memory                         │
├─────────────────────────────────────────────────────────┤
│ Phase 2: Taxonomies (grouping by tags)                   │
│   └─> site.taxonomies references Page objects            │
├─────────────────────────────────────────────────────────┤
│ Phase 3: Related Posts (pre-compute relationships)       │
│   └─> page.related_posts references other Page objects   │
├─────────────────────────────────────────────────────────┤
│ Phase 4: Rendering (templates access pages)              │
│   └─> Templates can reference ANY page via:              │
│       - site.pages (all pages)                            │
│       - site.taxonomies (grouped by tags)                 │
│       - doc('path') (xref index)                          │
│       - page.related_posts (pre-computed)                 │
├─────────────────────────────────────────────────────────┤
│ Phase 5: Health Checks (validation)                      │
│   └─> Validators iterate through site.pages              │
├─────────────────────────────────────────────────────────┤
│ Phase 6: Build Complete                                  │
│   └─> ALL 16K pages still in memory! ❌                  │
└─────────────────────────────────────────────────────────┘
```

**Problem:** Pages are never released until build completes.

---

## 🔍 Dependency Analysis

### When Are Pages Accessed?

**1. During Their Own Rendering** (always)
```python
# Template for page X needs page X's data
{{ page.title }}
{{ page.content }}
{{ page.tags }}
```

**2. Via Taxonomies** (if they have tags)
```python
# Templates might iterate over tag pages
{% for post in site.taxonomies['tags']['python']['pages'] %}
  {{ post.title }}
{% endfor %}
```

**3. Via Cross-References** (if linked from other pages)
```python
# Another page links to this page
{{ doc('docs/installation').title }}
```

**4. Via Related Posts** (if they share tags)
```python
# Page Y has related posts, one of which is page X
{% for related in page.related_posts %}
  {{ related.title }}
{% endfor %}
```

**5. Via Menus** (if in navigation)
```python
# Page appears in menu
{% for item in site.menu['main'] %}
  {{ item.page.title }}
{% endfor %}
```

**6. Via site.pages** (if template iterates all pages)
```python
# Template explicitly lists all pages
{% for p in site.pages %}
  {{ p.title }}
{% endfor %}
```

### Dependency Graph

```
High Connectivity (MUST stay in memory):
  ├─ Pages in menus (referenced during every page render)
  ├─ Pages with many incoming links (high ref count)
  ├─ Pages with many tags (in many taxonomy groups)
  └─ Index pages (often referenced)

Medium Connectivity (could serialize):
  ├─ Pages with 1-3 tags (in some taxonomy groups)
  ├─ Pages with 1-5 incoming links
  └─ Pages in related_posts of others

Low Connectivity (PRIME for optimization):
  ├─ Pages with 0 tags ⭐
  ├─ Pages with 0 incoming links ⭐
  ├─ Pages NOT in menus ⭐
  └─ Pages NOT in related_posts ⭐
```

**Key Insight:** A page with **no tags, no menu entry, no incoming links** can be released immediately after its own rendering!

---

## 💡 Optimization Strategies

### Strategy 1: Streaming Architecture (Low-Hanging Fruit)

**Concept:** Process "island" pages in isolation, release immediately after rendering.

**Algorithm:**
```python
def identify_island_pages(site):
    """Pages with zero dependencies."""
    islands = []
    
    for page in site.pages:
        is_island = (
            not page.tags and              # No taxonomy references
            page not in menu_pages and     # Not in navigation
            page not in xref_targets and   # No incoming links
            page not in related_posts_refs # Not in anyone's related
        )
        
        if is_island:
            islands.append(page)
    
    return islands

# Build process:
islands, connected = partition_pages(site)

# Process islands first, release immediately
for page in islands:
    render_page(page)
    write_to_disk(page)
    del page  # ✅ Release from memory

# Process connected pages normally
render_connected_pages(connected)
```

**Expected Impact:**
- For typical blogs: **30-50% of pages** are islands (posts with no tags, no links)
- For docs: **10-20%** (most docs are interlinked)
- **Memory reduction:** Proportional to island percentage

**Implementation Cost:** ~1-2 days (dependency graph analysis + streaming render)

---

### Strategy 2: Lazy Page Loading (Memory-Mapped Pages)

**Concept:** Serialize pages to disk, load on-demand during template rendering.

**Architecture:**
```python
class LazyPage:
    """Proxy object that loads page data on access."""
    
    def __init__(self, page_id: str, cache_path: Path):
        self._id = page_id
        self._cache = cache_path
        self._loaded = None
    
    def __getattr__(self, name):
        """Load page data on first access."""
        if self._loaded is None:
            self._loaded = self._load_from_disk()
        return getattr(self._loaded, name)
    
    def _load_from_disk(self):
        """Deserialize page from cache."""
        with open(self._cache / f"{self._id}.pkl", 'rb') as f:
            return pickle.load(f)

# During build:
for page in site.pages:
    # Render page (in memory)
    rendered = render_page(page)
    write_to_disk(rendered)
    
    # Serialize page for future access
    serialize_page(page, cache_dir)
    
    # Replace with lazy proxy
    site.pages[i] = LazyPage(page.id, cache_dir)
```

**Expected Impact:**
- **Peak memory:** Only actively rendering pages (~100-200 in parallel)
- **Trade-off:** Disk I/O for pages that ARE referenced
- **Best for:** Sites with sparse reference patterns

**Implementation Cost:** ~3-4 days (serialization + proxy + testing)

---

### Strategy 3: Flattened Indices (Graph Compaction)

**Concept:** Replace `site.pages` list with lightweight index, reconstruct on demand.

**Current State:**
```python
# Each Page object is ~5-10KB (content, metadata, rendered_html, etc.)
# 16K pages × 10KB = ~160MB minimum

site.pages = [Page(...), Page(...), ...]  # Full objects
site.taxonomies = {'tags': {'python': {'pages': [Page(...), ...]}}}
```

**Optimized State:**
```python
# Each PageRef is ~500 bytes (just metadata)
# 16K pages × 500B = ~8MB (20× reduction!)

class PageRef:
    """Lightweight page reference."""
    slug: str
    url: str
    title: str
    tags: List[str]
    date: datetime
    # NO content, NO rendered_html, NO large data

site.pages = [PageRef(...), PageRef(...), ...]
site.page_store = PageStore()  # Separate storage for full data

# Templates get lazy loading:
{{ doc('path').title }}         # Fast (from PageRef)
{{ doc('path').content }}        # Slow (loads from store)
{{ doc('path').rendered_html }}  # Slow (loads from disk)
```

**Expected Impact:**
- **Memory:** 20× reduction in base memory (160MB → 8MB)
- **Speed:** Same for metadata access, slower for full content access
- **Trade-off:** Complexity in template engine (transparent lazy loading)

**Implementation Cost:** ~1 week (major refactor of rendering pipeline)

---

### Strategy 4: Weak References (Python GC-Based)

**Concept:** Use `weakref` for secondary references, let GC collect.

**Implementation:**
```python
import weakref

# Primary reference (keep alive)
site.pages = [page1, page2, ...]

# Secondary references (can be collected)
site.taxonomies = {
    'tags': {
        'python': {
            'pages': [weakref.ref(p) for p in python_pages]
        }
    }
}

# Access pattern:
for page_ref in site.taxonomies['tags']['python']['pages']:
    page = page_ref()  # Dereference
    if page is not None:  # Still alive
        render(page)
```

**Problem:** This doesn't actually help! We NEED pages to stay alive for template rendering.

**Verdict:** ❌ Not suitable for our use case.

---

## 🎯 Recommended Approach

### Phase 1: Quick Win (1-2 days) ⭐

**Implement streaming architecture for island pages.**

```python
class StreamingBuildOrchestrator:
    """Build orchestrator with memory optimization."""
    
    def build(self):
        # 1. Discover all pages (in memory)
        pages = discover_content()
        
        # 2. Build dependency graph
        graph = DependencyGraph(pages)
        islands = graph.find_islands()
        
        print(f"📊 Pages: {len(pages)}, Islands: {len(islands)} ({len(islands)/len(pages)*100:.1f}%)")
        
        # 3. Render islands in batches, release immediately
        for batch in chunk(islands, size=100):
            for page in batch:
                render_page(page)
                write_to_disk(page)
            # Batch processed, all references released
            del batch
        
        # 4. Process connected pages (standard flow)
        connected_pages = [p for p in pages if p not in islands]
        build_taxonomies(connected_pages)
        build_related_posts(connected_pages)
        render_connected(connected_pages)
```

**Expected Results:**
- **Small reduction** (10-30%) for typical sites
- **Validates the approach** for more aggressive optimization
- **Low risk** (fallback to standard flow)

---

### Phase 2: Lazy Loading (1 week)

**Implement LazyPage proxies for low-access pages.**

Pages that are referenced < 5 times get serialized and replaced with proxies.

```python
# After rendering, analyze access patterns
access_counts = count_page_accesses(render_phase)

for page in site.pages:
    if access_counts[page.slug] < 5:  # Low-access threshold
        serialize_page(page)
        replace_with_lazy_proxy(page)
```

**Expected Results:**
- **50-70% memory reduction** for large sites
- **Small performance penalty** for low-access pages (disk I/O)
- **Transparent to templates** (proxy handles all access)

---

### Phase 3: Flattened Indices (2 weeks, if needed)

**Major refactor to use PageRef + PageStore architecture.**

Only implement if Phase 1+2 aren't sufficient (unlikely for sites < 50K pages).

**Expected Results:**
- **80-90% memory reduction** (only refs in memory)
- **Enables 100K+ page sites**
- **Complex implementation** (major refactor)

---

## 📊 Memory Projections

### Current (Baseline)

| Pages | Memory | Pages/sec | Build Time |
|-------|--------|-----------|------------|
| 500 | ~5MB | 219 | 2.3s |
| 4,096 | ~40MB | 79.7 | 51s |
| 16,384 | ~160MB | 19.6 | 838s |

### After Phase 1 (Streaming)

| Pages | Memory | Pages/sec | Build Time | Islands |
|-------|--------|-----------|------------|---------|
| 500 | ~4MB | 219 | 2.3s | ~150 (30%) |
| 4,096 | ~30MB | 85 | 48s | ~1,200 (30%) |
| 16,384 | ~115MB | 25 | 655s | ~5,000 (30%) |

**Improvement:** 25-30% memory reduction, 20-25% speed increase

### After Phase 2 (Lazy Loading)

| Pages | Memory | Pages/sec | Build Time |
|-------|--------|-----------|------------|
| 500 | ~2MB | 219 | 2.3s |
| 4,096 | ~15MB | 90 | 45s |
| 16,384 | ~50MB | 30 | 545s |

**Improvement:** 70% memory reduction, 35% speed increase

---

## 🔧 Implementation Details

### Dependency Graph Builder

```python
class DependencyGraph:
    """Analyzes page connectivity for memory optimization."""
    
    def __init__(self, site: Site):
        self.site = site
        self.incoming_refs = defaultdict(set)
        self.outgoing_refs = defaultdict(set)
    
    def build(self):
        """Build complete dependency graph."""
        # Track taxonomy references
        for taxonomy in self.site.taxonomies.values():
            for group in taxonomy.values():
                for page in group['pages']:
                    self.incoming_refs[page].add('taxonomy')
        
        # Track menu references
        for menu_items in self.site.menu.values():
            for item in menu_items:
                if hasattr(item, 'page'):
                    self.incoming_refs[item.page].add('menu')
        
        # Track cross-references
        for page in self.site.pages:
            for link in page.links:
                target = self.site.xref_index.get(link)
                if target:
                    self.incoming_refs[target].add(page)
                    self.outgoing_refs[page].add(target)
        
        # Track related posts
        for page in self.site.pages:
            for related in page.related_posts:
                self.incoming_refs[related].add(page)
    
    def find_islands(self) -> List[Page]:
        """Find pages with zero dependencies."""
        islands = []
        for page in self.site.pages:
            if (not self.incoming_refs[page] and 
                not self.outgoing_refs[page] and
                not page.tags and
                not page.metadata.get('_generated')):
                islands.append(page)
        return islands
    
    def get_connectivity(self, page: Page) -> int:
        """Get connectivity score (incoming + outgoing refs)."""
        return (len(self.incoming_refs[page]) + 
                len(self.outgoing_refs[page]) + 
                len(page.tags))
    
    def sort_by_connectivity(self) -> List[Page]:
        """Sort pages by connectivity (least connected first)."""
        return sorted(self.site.pages, 
                     key=lambda p: self.get_connectivity(p))
```

### Streaming Renderer

```python
class StreamingRenderer:
    """Renders pages in connectivity order with memory release."""
    
    def render_streaming(self, site: Site, batch_size: int = 100):
        """Render pages with memory optimization."""
        graph = DependencyGraph(site)
        graph.build()
        
        # Get pages sorted by connectivity (islands first)
        sorted_pages = graph.sort_by_connectivity()
        
        # Process in batches
        for i in range(0, len(sorted_pages), batch_size):
            batch = sorted_pages[i:i+batch_size]
            
            # Check if batch can be released
            can_release = all(
                graph.get_connectivity(p) == 0 
                for p in batch
            )
            
            # Render batch
            for page in batch:
                self.render_page(page)
                self.write_to_disk(page)
            
            # Release if safe
            if can_release:
                logger.debug(f"releasing_batch", 
                           batch_size=len(batch),
                           memory_saved=sys.getsizeof(batch))
                del batch
```

---

## 🎓 Lessons & Trade-offs

### When to Optimize

**DO optimize if:**
- ✅ Sites regularly exceed 5K pages
- ✅ Memory is constrained (CI/CD with 2GB limit)
- ✅ Build times exceed user patience

**DON'T optimize if:**
- ❌ Sites are typically < 1K pages (current perf is fine)
- ❌ Memory is abundant (64GB dev machines)
- ❌ Complexity exceeds benefit

### Trade-offs

| Strategy | Memory Saved | Complexity | Performance Impact |
|----------|--------------|------------|-------------------|
| Streaming | 25-30% | Low ⭐ | +20% faster |
| Lazy Loading | 60-70% | Medium | ±0% (I/O overhead) |
| Flattened Indices | 80-90% | High | -10% slower |
| Weak Refs | 0% | Medium | N/A (doesn't help) |

**Recommendation:** Start with **streaming** (low complexity, good gains), add **lazy loading** only if needed.

---

## 🚀 Next Steps

### Immediate (if pursuing this)

1. **Profile memory usage** at different scales:
   ```bash
   python -m memory_profiler tests/performance/benchmark_full_build.py
   ```

2. **Implement DependencyGraph** analyzer:
   - Count islands in real sites
   - Measure connectivity distribution
   - Validate assumptions

3. **Prototype streaming** for islands:
   - Implement safe release logic
   - Measure memory savings
   - Benchmark performance impact

### Questions to Answer

- **How many pages are islands?** (need real site data)
- **What's the memory breakdown?** (content vs. metadata vs. rendered_html)
- **Where's the actual bottleneck?** (might be file I/O, not memory)

---

## 📚 References

- **Python Memory Management:** https://docs.python.org/3/c-api/memory.html
- **Weak References:** https://docs.python.org/3/library/weakref.html
- **Memory Profiling:** https://pypi.org/project/memory-profiler/
- **Graph Algorithms:** Tarjan's strongly connected components

---

## ✅ Decision Checklist

**Before implementing:**

- [ ] Profile actual memory usage (not estimates)
- [ ] Measure island percentage on real sites
- [ ] Confirm memory is the bottleneck (vs. rendering time)
- [ ] Estimate implementation cost vs. benefit
- [ ] Consider alternative: "Don't build 16K pages at once" (incremental only)

**The simplest optimization might be:** *"For sites > 5K pages, incremental builds are mandatory."*

---

**End of Memory Optimization Strategy**

