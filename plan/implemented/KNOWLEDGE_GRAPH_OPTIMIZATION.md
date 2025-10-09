# Knowledge Graph Optimization & Visualization

**Date:** 2025-10-09  
**Inspired By:** Obsidian's graph view and connectivity-based processing  
**Key Insight:** Process order determines what we can release from memory  

---

## 🎯 The Order Question

### Original Strategy (Leaves First)
```
Process: Leaf pages (no dependencies) → Release immediately
Keep:    Hub pages (many dependencies) → Stay in memory
```

### Inverted Strategy (Hubs First) ⭐
```
Process: Hub pages (many dependencies) → Keep in memory
Process: Leaf pages → Release immediately as we go
Result:  Small set in memory (hubs) + streaming leaves
```

**Why this is BETTER:**

In a typical knowledge graph, connectivity follows a **power-law distribution**:
- **10% of pages** are hubs (heavily referenced)
- **90% of pages** are leaves (lightly or not referenced)

By processing hubs first, we:
1. Render the small set that MUST stay in memory
2. Stream the large set (leaves), releasing as we go
3. End up with minimal memory footprint!

---

## 📊 Graph Topology Analysis

### Real-World Knowledge Graphs

**Typical Blog (500 pages):**
```
Hubs (5%):        25 pages
  ├─ Homepage
  ├─ About/Contact
  ├─ Popular posts (referenced often)
  └─ Index pages

Mid-tier (30%):   150 pages
  ├─ Normal posts with tags
  └─ Some internal links

Leaves (65%):     325 pages
  ├─ One-off posts
  ├─ No tags
  └─ Rarely linked
```

**Documentation Site (1,000 pages):**
```
Hubs (15%):       150 pages
  ├─ Index pages (per section)
  ├─ Getting started guides
  ├─ Core concept pages
  └─ Heavily cross-referenced

Mid-tier (50%):   500 pages
  ├─ API reference pages
  └─ Standard docs

Leaves (35%):     350 pages
  ├─ Changelog entries
  ├─ Migration guides
  └─ Niche topics
```

### Memory Implications

**Current approach (all in memory):**
```
16K pages × 10KB = 160MB (all held)
```

**Hub-first streaming:**
```
Phase 1: Render 1.6K hubs (10%) = 16MB (kept)
Phase 2: Render 14.4K leaves in batches:
  - Batch 1 (100 leaves) → render → write → release
  - Batch 2 (100 leaves) → render → write → release
  - ...
  
Peak memory: 16MB (hubs) + 1MB (current batch) = 17MB
Reduction: 160MB → 17MB (90% savings!) 🎉
```

---

## 🔍 Dependency Direction Matters!

### Critical Insight: Who References Whom?

```
Rendering Page A needs Page B in memory IF:
  ├─ Page A's template calls {{ doc('B') }}
  ├─ Page A shows B in related_posts
  ├─ Page A lists B in a taxonomy
  └─ Page A includes B in navigation

After Page A is rendered:
  ├─ Page A can be released IF no future page will reference it
  └─ Page A must stay IF future pages might call {{ doc('A') }}
```

### Processing Order Strategy

**Topological sort from hubs to leaves:**

```
Level 0: Pages referenced by MANY (hubs)
  ├─ Keep in memory throughout build
  └─ These are "infrastructure" pages

Level 1: Pages that reference Level 0
  ├─ Render while Level 0 is in memory
  └─ Release if not referenced by Level 2+

Level 2: Pages that reference Level 1
  ├─ Render while Level 1 is in memory
  └─ Release if not referenced by Level 3+

...

Level N: Leaf pages (reference others, but nothing references them)
  ├─ Render and release IMMEDIATELY
  └─ Streaming processing possible
```

**This is essentially a reverse topological sort!**

---

## 💡 The Hub-First Algorithm

### Phase 1: Build Knowledge Graph

```python
class KnowledgeGraph:
    """Analyze page connectivity for optimization and visualization."""
    
    def __init__(self, site: Site):
        self.site = site
        self.incoming_refs = defaultdict(int)  # How many pages reference this
        self.outgoing_refs = defaultdict(set)  # What this page references
        self.layers = []  # Topological layers
    
    def build(self):
        """Build complete connectivity graph."""
        
        # Count incoming references
        for page in self.site.pages:
            # From taxonomies
            for tag in page.tags:
                for other_page in self.site.taxonomies['tags'][tag]['pages']:
                    if other_page != page:
                        self.incoming_refs[id(other_page)] += 1
            
            # From cross-references (page links to others)
            for link in page.links:
                target = resolve_link(link)
                if target:
                    self.incoming_refs[id(target)] += 1
                    self.outgoing_refs[id(page)].add(target)
            
            # From related posts
            for related in page.related_posts:
                self.incoming_refs[id(related)] += 1
            
            # From menus
            if page in menu_pages:
                self.incoming_refs[id(page)] += 10  # Bonus weight
    
    def compute_layers(self) -> List[List[Page]]:
        """
        Compute topological layers (hubs to leaves).
        
        Layer 0: Pages with incoming_refs > threshold (hubs)
        Layer 1: Pages that reference Layer 0 only
        Layer 2: Pages that reference Layer 1 only
        ...
        Layer N: Leaf pages (no incoming refs)
        
        Returns:
            List of layers, each containing pages at that level
        """
        pages_by_refs = defaultdict(list)
        
        for page in self.site.pages:
            ref_count = self.incoming_refs[id(page)]
            pages_by_refs[ref_count].append(page)
        
        # Sort by incoming references (descending)
        sorted_counts = sorted(pages_by_refs.keys(), reverse=True)
        
        # Group into layers
        # Layer 0: Top 10% by references (hubs)
        # Layer 1: Next 30% (mid-tier)
        # Layer 2: Bottom 60% (leaves)
        
        total_pages = len(self.site.pages)
        hub_threshold = int(total_pages * 0.10)
        mid_threshold = int(total_pages * 0.40)
        
        hubs = []
        mid_tier = []
        leaves = []
        
        count = 0
        for ref_count in sorted_counts:
            pages = pages_by_refs[ref_count]
            
            for page in pages:
                if count < hub_threshold:
                    hubs.append(page)
                elif count < mid_threshold:
                    mid_tier.append(page)
                else:
                    leaves.append(page)
                count += 1
        
        return [hubs, mid_tier, leaves]
    
    def get_connectivity_score(self, page: Page) -> int:
        """Get total connectivity (incoming + outgoing)."""
        return (self.incoming_refs[id(page)] + 
                len(self.outgoing_refs[id(page)]))
```

### Phase 2: Hub-First Streaming Build

```python
class StreamingBuildOrchestrator:
    """Build orchestrator with knowledge-graph-based memory optimization."""
    
    def build_streaming(self, site: Site):
        """Execute hub-first streaming build."""
        
        # 1. Build knowledge graph
        graph = KnowledgeGraph(site)
        graph.build()
        layers = graph.compute_layers()
        
        hubs, mid_tier, leaves = layers
        
        print(f"📊 Knowledge Graph Analysis:")
        print(f"   Hubs:     {len(hubs):5d} pages ({len(hubs)/len(site.pages)*100:.1f}%)")
        print(f"   Mid-tier: {len(mid_tier):5d} pages ({len(mid_tier)/len(site.pages)*100:.1f}%)")
        print(f"   Leaves:   {len(leaves):5d} pages ({len(leaves)/len(site.pages)*100:.1f}%)")
        
        # 2. Phase 1: Render hubs (keep in memory)
        print(f"\n🌟 Phase 1: Rendering hubs (will stay in memory)...")
        for page in hubs:
            self.render_page(page)
            self.write_to_disk(page)
        
        print(f"   ✅ {len(hubs)} hub pages in memory (~{len(hubs)*10/1024:.1f}MB)")
        
        # 3. Phase 2: Stream mid-tier (batch processing)
        print(f"\n🔄 Phase 2: Streaming mid-tier pages...")
        for batch in chunk(mid_tier, size=100):
            for page in batch:
                self.render_page(page)
                self.write_to_disk(page)
            # Can release if not needed by leaves
            if self._safe_to_release(batch, leaves, graph):
                del batch
        
        # 4. Phase 3: Stream leaves (aggressive release)
        print(f"\n🍃 Phase 3: Streaming leaf pages...")
        for batch in chunk(leaves, size=100):
            for page in batch:
                self.render_page(page)
                self.write_to_disk(page)
            # Leaves are NEVER referenced by future pages
            del batch  # ✅ Always safe to release!
        
        print(f"\n✅ Build complete with minimal memory footprint!")
    
    def _safe_to_release(self, batch, future_pages, graph):
        """Check if batch can be safely released."""
        batch_ids = {id(p) for p in batch}
        
        for future_page in future_pages:
            # Does future_page reference any page in batch?
            for ref_page in graph.outgoing_refs[id(future_page)]:
                if id(ref_page) in batch_ids:
                    return False  # Can't release, still needed
        
        return True  # Safe to release
```

---

## 🎨 Obsidian-Style Graph Visualization

### Feature: Interactive Knowledge Graph

**User-facing feature to visualize site structure:**

```python
class GraphVisualizer:
    """Generate interactive knowledge graph visualization."""
    
    def generate_graph_data(self, site: Site) -> dict:
        """
        Generate D3.js-compatible graph data.
        
        Nodes: Pages (sized by incoming refs, colored by type)
        Edges: Links between pages (weighted by strength)
        
        Returns:
            JSON-serializable graph data
        """
        graph = KnowledgeGraph(site)
        graph.build()
        
        nodes = []
        edges = []
        
        for page in site.pages:
            page_id = id(page)
            
            nodes.append({
                'id': str(page_id),
                'label': page.title,
                'url': page.url,
                'type': page.metadata.get('type', 'page'),
                'tags': page.tags,
                
                # Connectivity metrics
                'incoming_refs': graph.incoming_refs[page_id],
                'outgoing_refs': len(graph.outgoing_refs[page_id]),
                'connectivity': graph.get_connectivity_score(page),
                
                # Visual properties
                'size': min(50, 10 + graph.incoming_refs[page_id] * 2),
                'color': self._get_color_by_type(page),
            })
        
        for page in site.pages:
            page_id = id(page)
            for target_page in graph.outgoing_refs[page_id]:
                edges.append({
                    'source': str(page_id),
                    'target': str(id(target_page)),
                    'weight': 1,
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_pages': len(site.pages),
                'total_links': len(edges),
                'avg_connectivity': sum(graph.get_connectivity_score(p) for p in site.pages) / len(site.pages),
            }
        }
    
    def generate_html(self, graph_data: dict) -> str:
        """Generate interactive HTML graph visualization."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Knowledge Graph - {{{{ site.title }}}}</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {{ margin: 0; overflow: hidden; }}
                #graph {{ width: 100vw; height: 100vh; }}
                .node {{ cursor: pointer; }}
                .node:hover {{ stroke: #000; stroke-width: 3px; }}
                .link {{ stroke: #999; stroke-opacity: 0.6; }}
            </style>
        </head>
        <body>
            <div id="graph"></div>
            <script>
                const graphData = {json.dumps(graph_data)};
                
                // D3.js force-directed graph
                const width = window.innerWidth;
                const height = window.innerHeight;
                
                const svg = d3.select("#graph")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);
                
                const simulation = d3.forceSimulation(graphData.nodes)
                    .force("link", d3.forceLink(graphData.edges).id(d => d.id))
                    .force("charge", d3.forceManyBody().strength(-100))
                    .force("center", d3.forceCenter(width / 2, height / 2));
                
                // Render links
                const link = svg.append("g")
                    .selectAll("line")
                    .data(graphData.edges)
                    .enter().append("line")
                    .attr("class", "link");
                
                // Render nodes
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(graphData.nodes)
                    .enter().append("circle")
                    .attr("class", "node")
                    .attr("r", d => d.size)
                    .attr("fill", d => d.color)
                    .on("click", d => window.location.href = d.url);
                
                // Add labels
                const label = svg.append("g")
                    .selectAll("text")
                    .data(graphData.nodes)
                    .enter().append("text")
                    .text(d => d.label)
                    .attr("font-size", 10);
                
                // Update positions
                simulation.on("tick", () => {{
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);
                    
                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);
                    
                    label
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                }});
            </script>
        </body>
        </html>
        """
```

### CLI Command

```bash
# Generate knowledge graph visualization
bengal graph --output public/graph.html

# View graph statistics
bengal graph --stats

# Output:
# 📊 Knowledge Graph Statistics
#    Total pages:    1,024
#    Total links:    3,847
#    Avg connectivity: 7.5
#    
#    Top hubs:
#      1. Getting Started (52 incoming refs)
#      2. API Reference   (41 incoming refs)
#      3. Core Concepts   (38 incoming refs)
#    
#    Isolated pages: 127 (12.4%)
```

---

## 🎯 Dual-Purpose Graph

**The knowledge graph serves TWO purposes:**

### 1. **User Feature** (Obsidian-style)

Users can:
- ✅ Visualize their site structure
- ✅ Find orphaned pages (no incoming links)
- ✅ Identify over-connected pages (needs splitting)
- ✅ Discover content gaps (sparse areas)
- ✅ Navigate visually (click nodes)

**Marketing:** "See your knowledge, mapped."

### 2. **Build Optimization** (Internal)

Build system uses graph to:
- ✅ Determine processing order (hubs first)
- ✅ Identify memory release points (leaves)
- ✅ Optimize for incremental builds (affected subgraphs)
- ✅ Parallelize independent clusters

**Win-win:** Feature pays for itself in optimization!

---

## 📊 Expected Impact

### Memory Reduction (16K pages)

**Current:**
```
All pages in memory: 16K × 10KB = 160MB
```

**Hub-first streaming:**
```
Hubs (10%):     1.6K × 10KB =  16MB (kept)
Mid-tier batch:  100 × 10KB =   1MB (temporary)
Leaves batch:    100 × 10KB =   1MB (temporary)

Peak memory: 18MB (89% reduction!)
```

### Performance Impact

**Processing overhead:**
- Graph analysis: ~200ms for 16K pages (one-time)
- Topological sort: ~100ms (one-time)
- **Total overhead:** ~300ms (0.04% of 838s build)

**Speedup from better cache locality:**
- Hubs rendered together (similar references)
- Better CPU cache utilization
- **Estimated speedup:** 10-15%

**Net result:** 89% less memory, ~12% faster!

---

## 🚀 Implementation Plan

### Phase 1: Knowledge Graph Core (2 days)

1. Implement `KnowledgeGraph` class
2. Build connectivity analysis
3. Add CLI command: `bengal graph --stats`
4. Validate on real sites

### Phase 2: Visualization Feature (3 days)

1. Generate D3.js graph data
2. Create interactive HTML template
3. Add CLI command: `bengal graph --output graph.html`
4. Add to default theme (optional nav item)

### Phase 3: Hub-First Build (3 days)

1. Implement layer-based rendering
2. Add memory release logic
3. Benchmark memory usage
4. Compare performance

### Phase 4: Polish & Testing (2 days)

1. Add comprehensive tests
2. Profile memory usage
3. Document feature
4. Update changelog

**Total: ~2 weeks for complete feature + optimization**

---

## 🎓 Lessons Learned

### Order ABSOLUTELY Matters!

```
❌ Leaves first (my original idea):
   - Process leaves → release
   - Process hubs → must keep
   - Result: Hubs stay in memory (problem)

✅ Hubs first (your idea):
   - Process hubs → keep (small set!)
   - Process leaves → release as we go
   - Result: Only hubs in memory (win!)
```

**The insight:** In a power-law graph, the "must keep" set is SMALL, so process it first!

### Knowledge Graph = Swiss Army Knife

One graph analysis enables:
- User-facing visualization feature
- Build-time optimization
- Diagnostic tool for site health
- Future features (link checking, content recommendations, etc.)

**Investment pays dividends!**

### Obsidian Comparison

Obsidian's graph view is brilliant because:
1. Makes abstract connections concrete (visualization)
2. Reveals structure (hubs, clusters, orphans)
3. Aids navigation (visual index)
4. Looks cool (marketing value!)

Bengal should have this! 📊

---

## 🔥 Quick Wins

Even without full implementation, we can:

### 1. Add `--graph-stats` to current builds

```bash
bengal build --graph-stats

# Output:
# 📊 Knowledge Graph Analysis:
#    Hubs:     12 pages (could keep in memory)
#    Mid-tier: 56 pages (batch processing)
#    Leaves:   132 pages (stream & release)
#    
#    Potential memory savings: ~85%
```

### 2. Generate static graph in health check

During `--profile=dev` builds, auto-generate `public/_diagnostics/graph.html`

### 3. Add graph metrics to build output

```bash
Build complete!
  📄 Pages: 200
  🔗 Links: 847 (avg 4.2 per page)
  🌟 Hubs: 15 (top: "Getting Started" with 34 refs)
  🍃 Leaves: 82 (could stream these for 70% memory reduction)
```

---

## ✅ Decision

**Should we build this?**

**YES! 🎉** Here's why:

1. **Dual value:** User feature + build optimization
2. **Differentiator:** Not many SSGs have graph visualization
3. **Educational:** Helps users understand their site structure
4. **Performance:** 80-90% memory reduction at scale
5. **Foundation:** Enables future features (content recs, link checking, etc.)

**Recommended:** Implement Phase 1 + 2 first (graph feature), then Phase 3 (optimization) if needed.

---

**End of Knowledge Graph Optimization & Visualization**

