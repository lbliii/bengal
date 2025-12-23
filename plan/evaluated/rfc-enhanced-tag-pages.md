# RFC: Enhanced Tag Pages for Content Discovery

**Status**: Evaluated  
**Confidence**: 100% 🟢  
**Created**: 2024-12-22  
**Author**: Bengal Team

## Summary

Transform Bengal's tag pages from simple post lists into rich discovery experiences for **readers**. Leverage existing KnowledgeGraph, PageRank, and analysis infrastructure to surface the best content and enable visual exploration.

**Scope**: Reader-facing published pages only. Author-facing analytics (orphan detection, health scores) belong in the `bengal health` CLI — see separate RFC.

---

## Problem Statement

**Current State**: Tag pages are chronological post lists with a count badge. Identical to every other SSG.

**Opportunity**: Bengal already computes rich graph data that could power better discovery:
- **PageRank**: Which posts are most important/linked-to?
- **Link Structure**: How are posts within a tag connected?
- **Tag Co-occurrence**: Which tags appear together?

**None of this is exposed to readers.**

---

## Goals

1. Help readers find the **best content** on a topic (not just newest)
2. Enable **visual exploration** of content relationships
3. Surface **related topics** for lateral discovery
4. Make tag pages a **differentiator** for Bengal sites

## Non-Goals

- Author/contributor analytics on published pages (use `bengal health`)
- Health scores, orphan warnings, or "needs attention" lists
- Real-time analytics or external integrations

---

## Design

### Enhanced Tag Page Layout

```
┌────────────────────────────────────────────────────────────────┐
│  #python                                                       │
│  28 posts exploring Python development                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  🌟 ESSENTIAL READING                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Python Type Hints: A Complete Guide                      │  │
│  │ The most linked-to resource on Python typing...          │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Async/Await Deep Dive                                    │  │
│  │ Understanding Python's concurrency model...              │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Error Handling Patterns                                  │  │
│  │ Best practices for exception handling...                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  📊 CONTENT MAP                    🔗 EXPLORE RELATED          │
│  ┌─────────────────────────┐      ┌─────────────────────────┐  │
│  │    [Interactive D3      │      │ async (12 shared)       │  │
│  │     force graph of      │      │ testing (8 shared)      │  │
│  │     pages in this tag]  │      │ web-dev (6 shared)      │  │
│  │                         │      │ api (4 shared)          │  │
│  │   Node size = PageRank  │      │ typing (4 shared)       │  │
│  │   Edges = internal links│      │                         │  │
│  └─────────────────────────┘      └─────────────────────────┘  │
│                                                                │
│  📅 ALL POSTS                                                  │
│  [Existing chronological list with pagination]                 │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

### Feature 1: Essential Reading (PageRank-sorted)

Surface the **most important posts** for a tag, not just the newest.

**How it works**:
- Filter site's PageRank results to pages with this tag
- Take top 3-5 by score
- Show with excerpt for quick scanning

**Template**:
```jinja
{% if essential_posts %}
<section class="essential-reading">
  <h2>🌟 Essential Reading</h2>
  {% for post in essential_posts[:5] %}
  <article class="essential-post">
    <h3><a href="{{ post.url }}">{{ post.title }}</a></h3>
    <p>{{ post.excerpt | truncate(120) }}</p>
  </article>
  {% endfor %}
</section>
{% endif %}
```

**Data needed**: `essential_posts: list[Page]` (PageRank-sorted)

---

### Feature 2: Content Map (Mini-Graph)

Visual exploration of how posts within a tag connect.

**How it works**:
- Generate subgraph of pages with this tag
- Node size = PageRank score
- Edges = internal links between tagged pages
- Click node → navigate to page

**Implementation**:
```python
def compute_tag_graph(self, tag_slug: str, pages: list[Page]) -> dict:
    """Generate D3.js graph data for tag visualization."""
    graph = self.site._knowledge_graph
    pagerank = graph._pagerank_results

    nodes = []
    edges = []
    page_set = set(pages)

    for page in pages:
        score = pagerank.get_score(page) if pagerank else 0.5
        nodes.append({
            "id": str(hash(page.source_path)),
            "title": page.title,
            "url": page.url,
            "size": score * 10,  # Scale for visualization
        })

    for page in pages:
        for target in graph.outgoing_refs.get(page, set()):
            if target in page_set:
                edges.append({
                    "source": str(hash(page.source_path)),
                    "target": str(hash(target.source_path)),
                })

    return {"nodes": nodes, "edges": edges}
```

**Template**:
```jinja
{% if tag_graph and tag_graph.nodes | length > 2 %}
<section class="content-map">
  <h2>📊 Content Map</h2>
  <div id="tag-graph"
       data-nodes='{{ tag_graph.nodes | tojson }}'
       data-edges='{{ tag_graph.edges | tojson }}'></div>
  <p class="graph-hint">Larger nodes are more connected. Click to explore.</p>
</section>
{% endif %}
```

**JS**: Reuse existing `graph_visualizer.py` D3.js code with simplified config.

---

### Feature 3: Related Tags

Help readers discover adjacent topics.

**How it works**:
- Count pages shared between this tag and all other tags
- Sort by overlap count
- Show top 5-8 related tags

**Implementation**:
```python
def compute_related_tags(self, tag_slug: str, pages: list[Page]) -> list[tuple[str, int]]:
    """Find tags that share pages with this tag."""
    page_set = set(pages)
    tag_overlap: dict[str, int] = defaultdict(int)

    for page in pages:
        for other_tag in page.tags:
            if other_tag != tag_slug:
                tag_overlap[other_tag] += 1

    # Sort by overlap, return top results
    return sorted(tag_overlap.items(), key=lambda x: -x[1])[:8]
```

**Template**:
```jinja
{% if related_tags %}
<section class="related-tags">
  <h2>🔗 Explore Related</h2>
  <div class="tag-chips">
    {% for tag_name, count in related_tags %}
    <a href="{{ tag_url(tag_name) }}" class="tag-chip">
      {{ tag_name }} <span class="count">({{ count }})</span>
    </a>
    {% endfor %}
  </div>
</section>
{% endif %}
```

---

## Technical Architecture

### Data Flow

```
Build Pipeline:
  Phase 6 (Analysis) ──────────────────────────────────────┐
       │                                                    │
       ├── Build KnowledgeGraph (existing)                  │
       ├── Compute PageRank (existing)                      │
       │                                                    │
  Phase 7 (Taxonomies)                                      │
       │                                                    │
       ├── Collect tags (existing)                          │
       ├── NEW: Compute tag enhancements ◄──────────────────┘
       │        ├── essential_posts (PageRank filtered)
       │        ├── tag_graph (subgraph for this tag)
       │        └── related_tags (co-occurrence)
       │
       └── Generate tag pages with enhanced context
```

### New Data Structure

```python
@dataclass
class TagEnhancements:
    """Reader-facing enhancements for a tag page."""
    tag_slug: str
    tag_name: str

    # PageRank-sorted top posts
    essential_posts: list[Page]

    # Mini-graph data for D3.js visualization
    graph_data: dict | None  # {"nodes": [...], "edges": [...]}

    # Related tags by page overlap
    related_tags: list[tuple[str, int]]  # (tag_name, shared_count)
```

### Integration Point

In `TaxonomyOrchestrator._create_tag_pages()`:

```python
def _create_tag_pages(self, tag_slug: str, tag_data: dict) -> list[Page]:
    pages = tag_data["pages"]

    # NEW: Compute enhancements if graph available
    enhancements = None
    if hasattr(self.site, "_knowledge_graph") and self.site._knowledge_graph:
        enhancements = self._compute_tag_enhancements(tag_slug, pages)

    # Add to page metadata
    for tag_page in pages_to_create:
        tag_page.metadata["_tag_enhancements"] = enhancements
```

---

## Configuration

```yaml
# bengal.yaml
taxonomy:
  tags:
    enhanced_pages: true          # Enable all enhancements (default: true)
    essential_reading_count: 5    # Number of top posts to feature
    show_content_map: true        # Show D3.js graph (default: true)
    content_map_min_pages: 3      # Minimum pages to show graph
    related_tags_count: 8         # Number of related tags to show
```

---

## Mobile Considerations

| Feature | Desktop | Mobile |
|---------|---------|--------|
| Essential Reading | Full cards | Compact list |
| Content Map | Interactive D3 | Static image or hidden |
| Related Tags | Chips grid | Horizontal scroll |

```css
@media (max-width: 768px) {
  .content-map { display: none; }  /* Or show static fallback */
}
```

---

## Performance

**Build-time impact**: Minimal
- KnowledgeGraph + PageRank already computed
- Tag graph extraction: O(pages_in_tag × avg_links)
- Related tags: O(pages_in_tag × avg_tags)

**Output size impact**: Small
- Essential posts: No extra data (just different ordering)
- Graph JSON: ~2-5KB per tag
- Total for 50 tags: ~100-250KB

---

## Phased Implementation

### Phase 1: Essential Reading — 2 days
- Add PageRank-sorted `essential_posts` to tag context
- Update `tag.html` template
- No JS required

### Phase 2: Related Tags — 1 day
- Compute tag co-occurrence
- Add `related_tags` to context
- Update template

### Phase 3: Content Map — 3-4 days
- Extract subgraph per tag
- Adapt existing D3.js graph code
- Mobile fallback
- Update template

---

## Success Metrics

1. **Discoverability**: Do readers click "Essential Reading" posts?
2. **Exploration**: Do readers use Content Map and Related Tags?
3. **Engagement**: Time on tag pages (user testing)
4. **Differentiation**: Is this a selling point for Bengal?

---

## Related Work

- **Tag Health Reports**: Separate enhancement to `bengal health` CLI
  - Orphan detection, connectivity scores, recommendations
  - Not published, author-facing only

---

## Next Steps

1. [ ] Review and approve approach
2. [ ] Implement Phase 1 (Essential Reading)
3. [ ] Implement Phase 2 (Related Tags)
4. [ ] Implement Phase 3 (Content Map)
5. [ ] Update default theme templates
6. [ ] Documentation

---

## References

- `bengal/analysis/knowledge_graph.py` — Graph infrastructure
- `bengal/analysis/page_rank.py` — PageRank implementation
- `bengal/analysis/graph_visualizer.py` — D3.js visualization (reusable)
- `bengal/orchestration/taxonomy.py` — Tag page generation
- `bengal/themes/default/templates/tag.html` — Current template
