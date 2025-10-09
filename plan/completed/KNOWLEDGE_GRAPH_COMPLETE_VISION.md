# Knowledge Graph - Complete Vision & Strategy

**Date:** 2025-10-09  
**Status:** Ready for Implementation  
**Inspired By:** Obsidian's graph view + performance optimization needs  

---

## 🎯 Executive Summary

**What:** Knowledge graph analysis and visualization for Bengal SSG

**Why:** 
- Solves memory bottleneck at scale (80-90% reduction)
- Provides reader-facing navigation feature (Obsidian-style)
- Differentiates Bengal from all other SSGs
- Serves all three user personas (writers, theme devs, developers)

**When:** 5 phases, first 4 phases = 3-4 weeks, phase 5 = 1-2 weeks later

**Impact:** 
- Performance: Enables 10K-50K page sites
- UX: Better content discovery for readers
- Marketing: Unique, visual, shareable feature
- SEO: Improved site structure signals

---

## 🌟 The Four Audiences

### 1. **Developers** (Build-time optimization)
```bash
$ bengal build --optimize-memory
📊 Hub-first build: 89% memory reduction
⚡ 16K pages: 160MB → 17MB peak memory
```

**Value:** Enables massive sites, faster builds

### 2. **Writers** (Content health)
```bash
$ bengal graph --stats
📊 Found 12 orphaned pages (no incoming links)
💡 Consider adding navigation or cross-references
```

**Value:** Improve SEO, content discoverability

### 3. **Theme Developers** (Structure visualization)
```bash
$ bengal graph --output public/graph.html
🎨 Interactive graph shows navigation patterns
💡 Helps design better UX
```

**Value:** Understand site structure, test themes

### 4. **Readers** (Site exploration) ⭐ NEW
```
Visit: yoursite.com/explore/
🗺️ Interactive map of all content
🔍 Search, filter, navigate visually
📍 See where you are in the knowledge structure
```

**Value:** Better discovery, non-linear navigation

---

## 📦 The Five Phases

### **Phase 0: Foundation** ✅ COMPLETE

Already have:
- BuildProfile system
- Cross-reference index
- Related posts computation
- Health check validators
- Structured logging

**No work needed!** We can build on this.

---

### **Phase 1: Graph Analysis & Stats** (2-3 days)

**Deliverable:** `bengal graph --stats`

**What it does:**
```bash
$ bengal graph --stats

📊 Knowledge Graph Statistics
════════════════════════════════════════
Total pages:        198
Total links:        847
Average links:      4.3 per page

Connectivity Distribution:
  Hubs (>10 refs):  12 pages (6%)
  Mid-tier (3-10):  54 pages (27%)
  Leaves (0-2):     132 pages (67%)

Top Hubs:
  1. Getting Started     34 refs
  2. API Reference       28 refs
  3. Core Concepts       22 refs

Orphaned Pages (0 incoming refs):
  • changelog/v0.1.0.md
  • drafts/old-post.md
  • about/team/old-member.md

💡 Insights:
  • 67% of pages are leaves (could stream for memory savings)
  • 3 pages have no incoming links (consider adding navigation)
```

**Implementation:**
- `bengal/analysis/knowledge_graph.py` (new module)
- `KnowledgeGraph` class with connectivity analysis
- CLI command in `bengal/cli.py`
- Tests in `tests/unit/analysis/`

**Value:** Immediate actionable insights for writers

---

### **Phase 2: Interactive Visualization** (3-4 days)

**Deliverable:** `bengal graph --output public/graph.html`

**What it generates:**
- Full-page interactive D3.js graph
- Nodes = pages (sized by connectivity)
- Edges = links between pages
- Clickable navigation
- Search and filter

**Visual:**
```
[Homepage]──────[About]
    │              │
    ├──[Docs]──────┤
    │    │         │
    │  [API]─────[CLI]
    │    │         │
    └──[Blog]──────┘
         │
    [Orphan] ← highlighted in red
```

**Implementation:**
- `bengal/analysis/graph_visualizer.py`
- D3.js force-directed graph template
- JSON export of graph data
- CSS styling (theme-aware)

**Value:** Visual understanding of site structure

---

### **Phase 3: Memory Optimization** (3-5 days)

**Deliverable:** `bengal build --optimize-memory`

**What it does:**
1. Analyze connectivity graph
2. Process hubs first (keep in memory)
3. Stream leaves (release immediately)
4. Result: 80-90% memory reduction

**Algorithm:**
```python
# Phase 1: Render hubs (10% of pages, stay in memory)
for page in hubs:
    render(page)
    write(page)
# Hubs stay: 16MB

# Phase 2: Stream leaves (90% of pages, batch release)
for batch in chunk(leaves, 100):
    render(batch)
    write(batch)
    del batch  # Release immediately
# Peak memory: 17MB vs 160MB!
```

**Implementation:**
- Refactor `bengal/orchestration/build.py`
- Add `StreamingBuildOrchestrator`
- Memory profiling and benchmarks

**Value:** Enables 10K-50K page sites

---

### **Phase 4: Health Check Integration** (2 days)

**Deliverable:** `ConnectivityValidator` in `--profile=dev`

**What it checks:**
- Orphaned pages (0 incoming links)
- Over-connected pages (>50 refs)
- Isolated clusters
- Broken link patterns

**Output:**
```
🔍 Health Check: Connectivity
════════════════════════════════════════
⚠️  Warning: 3 orphaned pages
    • /changelog/v0.1.0/
    • /drafts/old-post/
    • /about/team/old-member/
    
ℹ️  Info: 2 pages heavily referenced
    • /docs/getting-started/ (52 refs)
    • /api/reference/ (41 refs)
    
✅ Site connectivity: Good
```

**Implementation:**
- `bengal/health/validators/connectivity.py`
- Integration with health orchestrator
- Configuration in `bengal.toml`

**Value:** Proactive quality checks

---

### **Phase 5: Reader-Facing Graph** (1-2 weeks, future)

**Deliverable:** Interactive graph for site visitors

**Three modes:**

**A) Local Graph Widget** (Obsidian-style)
```html
<!-- On every page, sidebar -->
<div class="local-graph">
  <h4>Explore Nearby</h4>
  <div id="graph">
    <!-- Shows current page + 2 hops -->
    <!-- Click to navigate -->
  </div>
</div>
```

**B) Full Explore Page**
```
yoursite.com/explore/
  - Full interactive graph
  - Search and filter
  - Current page highlighted
  - Tag-based clustering
```

**C) Mini-Graph (Related Content)**
```html
<!-- At end of articles -->
<section class="related-content">
  <h3>Related Articles</h3>
  <div class="mini-graph">
    <!-- Shows related posts visually -->
  </div>
</section>
```

**Features:**
- ✅ Filter by tag/section/type
- ✅ Search and highlight
- ✅ Reading progress tracking (localStorage)
- ✅ Mobile-optimized touch controls
- ✅ Keyboard navigation
- ✅ Accessibility (list fallback)

**Configuration:**
```toml
[features.knowledge_graph]
# Reader-facing settings
reader_mode = "local"  # "local", "full", "mini", "disabled"
reader_depth = 2       # Hops from current page
reader_max_nodes = 500
reader_show_orphans = false
reader_enable_search = true
reader_store_progress = true  # localStorage
```

**Implementation:**
- Enhanced graph visualizer
- Multiple layout modes
- Mobile-responsive controls
- Privacy-respecting (localStorage only)

**Value:** Better reader discovery and navigation

---

## 🎨 Obsidian Inspiration

**What Obsidian does well:**
- [Graph view on help.obsidian.md](https://help.obsidian.md/) embedded in top-left
- Hover to highlight connections
- Click to navigate
- Visual clustering by topic
- Node size = importance

**How Bengal improves on it:**
- ✅ Pre-generated at build time (faster)
- ✅ SEO-friendly (JSON-LD structure)
- ✅ Tag-based auto-clustering
- ✅ Section hierarchies (docs sites)
- ✅ Reading progress tracking
- ✅ Mobile-optimized
- ✅ Multiple layout modes per use case

---

## 📊 Expected Impact

### Performance (Phase 3)

**Before:**
- 16K pages: 837s build, 160MB peak memory
- Limited to ~20K pages max

**After:**
- 16K pages: ~655s build, 17MB peak memory
- Can handle 50K-100K pages

**Improvement:** 89% memory reduction, 22% faster

---

### User Adoption (Phase 1-2)

**Targets (3 months post-launch):**
- 40% of users run `bengal graph --stats`
- 20% generate visualizations
- 10% use `--optimize-memory`

---

### Reader Engagement (Phase 5)

**Targets:**
- 20% of visitors use graph navigation
- 2-3 pages discovered per graph session
- 30% longer time on site
- Lower bounce rate

---

### SEO Benefits (Phase 5)

**Improvements:**
- Better internal linking structure
- JSON-LD graph data for search engines
- Improved crawl depth
- Clearer site architecture signals

---

## 🎯 Strategic Value

### Competitive Differentiation

| Feature | Hugo | Jekyll | Eleventy | Gatsby | **Bengal** |
|---------|------|--------|----------|--------|-----------|
| Graph stats | ❌ | ❌ | ❌ | ❌ | ✅ |
| Graph viz | ❌ | ❌ | ❌ | ⚠️ GraphQL | ✅ |
| Memory opt | ⚠️ Go | ❌ | ❌ | ⚠️ | ✅ |
| Reader graph | ❌ | ❌ | ❌ | ❌ | ✅ |

**Result:** Bengal becomes "the SSG with knowledge graphs"

---

### Market Position

**Target audiences:**
1. **Knowledge workers** (Obsidian, Roam, Notion users)
   - "Build your digital garden with graph navigation"
   
2. **Documentation sites** (large, interconnected)
   - "Handle 10K+ pages with graph-based optimization"
   
3. **Educators** (course materials, learning paths)
   - "Show students the knowledge map with progress tracking"
   
4. **Bloggers** (content strategists)
   - "Find orphaned content, improve SEO with connectivity insights"

---

### Marketing Angles

**Taglines:**
- "See your knowledge, mapped."
- "The SSG that shows you how your content connects"
- "From Obsidian notes to published sites with graph navigation"
- "Build sites that show their structure"

**Demo scenarios:**
1. Show graph analysis finding orphaned pages
2. Show interactive exploration on live site
3. Show memory optimization for 10K pages
4. Show reader discovering content via graph

**Visuals:**
- Animated graph transitions
- Before/after memory usage charts
- Side-by-side with Obsidian (inspiration)
- Real site examples

---

## 🔧 Technical Architecture

### Module Structure
```
bengal/
├── analysis/                    [NEW]
│   ├── __init__.py
│   ├── knowledge_graph.py      [Phase 1: Core analysis]
│   └── graph_visualizer.py     [Phase 2: D3.js generation]
│
├── orchestration/
│   ├── build.py                [Phase 3: Modified for streaming]
│   └── streaming.py            [Phase 3: New streaming orchestrator]
│
├── health/
│   └── validators/
│       └── connectivity.py     [Phase 4: New validator]
│
└── cli.py                      [Phase 1-3: Add graph commands]
```

### Data Structures
```python
class KnowledgeGraph:
    """Analyze page connectivity."""
    incoming_refs: Dict[int, int]      # page_id -> ref count
    outgoing_refs: Dict[int, Set]      # page_id -> linked pages
    layers: List[List[Page]]           # Topological layers
    
    def get_hubs(threshold=10) -> List[Page]
    def get_leaves() -> List[Page]
    def get_orphans() -> List[Page]
    def compute_layers() -> List[List[Page]]

class GraphVisualizer:
    """Generate D3.js visualizations."""
    
    def generate_graph_data() -> GraphData
    def generate_html() -> str
    def generate_json_ld() -> dict
```

### Dependencies
- **Zero new dependencies!**
- Uses D3.js via CDN in generated HTML
- All graph analysis in pure Python
- Standard library only

---

## 📚 Documentation Plan

### User Docs
1. `docs/features/knowledge-graph.md` - Overview
2. `docs/cli.md` - Command reference
3. `docs/advanced/performance.md` - Optimization guide
4. `docs/themes/graph-integration.md` - Theme customization

### Developer Docs
1. `ARCHITECTURE.md` - Add graph system section
2. `docs/api/analysis.md` - API reference
3. `CONTRIBUTING.md` - How to extend

### Examples
1. Showcase site with graph enabled
2. Blog example (mini-graph sidebar)
3. Docs example (full explore page)
4. Digital garden example (graph-first nav)

---

## 🚀 Implementation Timeline

### Sprint 1: Foundation (Week 1)
- **Mon-Tue:** Implement `KnowledgeGraph` class
- **Wed-Thu:** Add CLI `bengal graph --stats`
- **Fri:** Tests and documentation

**Deliverable:** Graph analysis working on showcase site

---

### Sprint 2: Visualization (Week 2)
- **Mon-Tue:** Implement `GraphVisualizer`
- **Wed-Thu:** D3.js template and styling
- **Fri:** Polish and mobile optimization

**Deliverable:** Interactive graph at `/explore/`

---

### Sprint 3: Optimization (Week 3)
- **Mon-Tue:** Streaming build orchestrator
- **Wed-Thu:** Memory profiling and benchmarks
- **Fri:** Testing on synthetic large sites

**Deliverable:** `--optimize-memory` flag working

---

### Sprint 4: Integration (Week 4, Mon-Wed)
- **Mon:** `ConnectivityValidator` implementation
- **Tue:** Documentation and examples
- **Wed:** Final testing and PR

**Deliverable:** Complete Phases 1-4, ready to ship

---

### Sprint 5: Reader Features (Future, 1-2 weeks)
- **Week 1:** Local graph widget, explore page
- **Week 2:** Search, filters, reading progress

**Deliverable:** Reader-facing graph navigation

---

## ✅ Success Criteria

### Phase 1-2 (Analysis & Viz)
- [ ] Graph analysis completes in <500ms for 1K pages
- [ ] Accurately identifies hubs, leaves, orphans
- [ ] Interactive graph renders smoothly
- [ ] All tests pass with >90% coverage

### Phase 3 (Optimization)
- [ ] Peak memory <20% of standard build for 10K pages
- [ ] Build time improvement: 10-20%
- [ ] Zero regressions on small sites
- [ ] Fallback works if optimization fails

### Phase 4 (Health)
- [ ] ConnectivityValidator runs in <100ms
- [ ] Issues are actionable and clear
- [ ] Integrates cleanly with existing health system
- [ ] False positive rate <5%

### Phase 5 (Readers)
- [ ] Local graph loads in <1s on mobile
- [ ] Keyboard accessible
- [ ] Works without JS (fallback to list)
- [ ] Privacy-respecting (no tracking)

---

## 🎓 Key Insights

### 1. Order Matters (Hub-First Strategy)
Processing hubs first → small "must keep" set → stream the rest
- **Result:** 90% memory reduction vs. leaves-first approach

### 2. Dual-Purpose Architecture
Same graph analysis serves:
- Build-time optimization (streaming)
- User-facing visualization (exploration)
- Health checks (quality)
- **Result:** Feature pays for itself multiple ways

### 3. Progressive Enhancement
Each phase delivers value independently:
- Phase 1 alone helps writers find orphans
- Phase 2 alone helps theme devs
- Phase 3 alone enables large sites
- **Result:** Can ship incrementally

### 4. Obsidian Inspiration
Obsidian proved graph navigation works for knowledge:
- Readers love visual exploration
- Non-linear nav matches thought patterns
- Graph reveals structure instantly
- **Result:** Proven UX pattern to follow

---

## 🎯 Decision: GO!

**Recommendation:** Proceed with implementation

**Why:**
1. ✅ Clear value for all user personas
2. ✅ Unique competitive differentiator
3. ✅ Solves real performance problem
4. ✅ Builds on existing foundation (low risk)
5. ✅ Marketing potential (visual, shareable)
6. ✅ Reasonable timeline (3-4 weeks → ship)
7. ✅ Future-proof (reader features later)

**Next Steps:**
1. Create GitHub issue/project
2. Set up feature branch
3. Begin Phase 1 implementation
4. Ship incrementally (phase by phase)

---

## 📋 Related Documents

- `KNOWLEDGE_GRAPH_IMPLEMENTATION_PLAN.md` - Detailed implementation guide
- `KNOWLEDGE_GRAPH_OPTIMIZATION.md` - Technical deep dive on optimization
- `MEMORY_OPTIMIZATION_STRATEGY.md` - Memory management strategies
- `PERFORMANCE_OPTIMIZATION_COMPLETE.md` - URL caching + profile work

---

**Status:** 🚀 Ready to start Phase 1

**End of Vision Document**

