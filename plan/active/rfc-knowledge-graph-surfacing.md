# RFC: Knowledge Graph Intelligence Surfacing

**Status**: Draft
**Created**: 2025-12-05
**Author**: AI-assisted analysis
**Related**: `bengal/analysis/`, `rfc-lazy-build-artifacts.md`

---

## Summary

Bengal has a sophisticated Knowledge Graph analysis engine (PageRank, Louvain communities, centrality metrics, link suggestions) that currently surfaces primarily through CLI tools and a standalone `/graph/` visualization. This RFC proposes expanding the surface area to bring graph intelligence directly into templates, dev workflows, and auto-generated pages.

**Goal**: Make the unicorn visible—transform hidden graph analysis into actionable, user-facing features.

**Impact**: Higher content quality, better SEO, improved navigation, smarter authoring experience.

---

## Problem Statement

### Current State: Intelligence Hidden in CLI

| Analysis Capability | Built | CLI | Templates | Dev Mode |
|---------------------|-------|-----|-----------|----------|
| PageRank scores | ✅ | ✅ | ❌ | ❌ |
| Community detection | ✅ | ✅ | ❌ | ❌ |
| Betweenness/closeness | ✅ | ✅ | ❌ | ❌ |
| Link suggestions | ✅ | ✅ | ❌ | ❌ |
| Graph visualization | ✅ | ✅ | ✅ (minimap) | ❌ |
| Orphan detection | ✅ | ✅ | ❌ | ❌ |

### Why This Matters

1. **Authors don't run CLI tools** - Most content authors never discover `bengal graph suggest`
2. **Insights arrive too late** - Analysis happens post-build, not during writing
3. **SEO blind spots** - Orphaned pages, weak internal linking persist unnoticed
4. **Wasted computation** - Graph is built but most intelligence discarded

### Evidence

- Knowledge Graph takes ~200-500ms to build per analysis
- `bengal graph suggest` generates actionable recommendations, but only 5% of users run it (estimated)
- Orphan pages directly impact SEO crawlability
- Community detection reveals content structure invisible in folder hierarchy

---

## Proposed Solution

### Five Surface Points for Graph Intelligence

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROPOSED SURFACING STRATEGY                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. TEMPLATE: "Related by Graph" Section                            │
│     ├─ PageRank-weighted related pages                              │
│     └─ Smarter than tag-only matching                               │
│                                                                     │
│  2. TEMPLATE: Bridge Page Badges                                    │
│     ├─ Auto-mark high-betweenness pages                             │
│     └─ Visual indicator of navigation importance                    │
│                                                                     │
│  3. TEMPLATE: Community Labels                                      │
│     ├─ "Part of the Python Tutorial cluster"                        │
│     └─ Cross-link to cluster siblings                               │
│                                                                     │
│  4. DEV MODE: Interactive Link Suggestions                          │
│     ├─ Real-time "You should link to X" in dev server               │
│     └─ One-click insertion support                                  │
│                                                                     │
│  5. AUTO PAGE: /insights/ SEO Dashboard                             │
│     ├─ Orphan alerts, link gaps, cluster health                     │
│     └─ Actionable improvement checklist                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Feature 1: Related by Graph Section

### Problem
Current related posts use tag-based similarity only. Pages with no shared tags appear unrelated even when heavily cross-linked or in the same community.

### Solution
Add graph-aware related pages using multiple signals:
- PageRank of target (prioritize important pages)
- Betweenness centrality (link to bridge pages)
- Community membership (same cluster = related)
- Existing link structure (complement, don't duplicate)

### Design

```python
# bengal/analysis/related_by_graph.py

@dataclass
class GraphRelatedResult:
    """Related page with graph-based scoring."""
    page: Page
    score: float
    reasons: list[str]  # ["Same community", "High PageRank", "Bridge page"]

class GraphRelatedEngine:
    """Compute graph-aware related pages."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def get_related(
        self,
        page: Page,
        limit: int = 5,
        exclude_existing_links: bool = True,
    ) -> list[GraphRelatedResult]:
        """
        Get related pages using graph intelligence.

        Scoring formula:
          score = (
              0.30 * community_match +      # Same cluster
              0.25 * pagerank_normalized +  # Important pages
              0.20 * tag_similarity +       # Topic overlap
              0.15 * betweenness_score +    # Bridge value
              0.10 * path_proximity         # Navigation closeness
          )
        """
        ...
```

### Template Integration

```html
<!-- templates/partials/related-by-graph.html -->
{% if page.graph_related %}
<aside class="related-by-graph">
  <h3>📊 Related Content</h3>
  <ul>
    {% for related in page.graph_related[:5] %}
    <li>
      <a href="{{ related.page.url }}">{{ related.page.title }}</a>
      <span class="reason">{{ related.reasons[0] }}</span>
    </li>
    {% endfor %}
  </ul>
</aside>
{% endif %}
```

### Configuration

```toml
[graph.related]
enabled = true
limit = 5
show_reasons = true
exclude_same_section = false
```

---

## Feature 2: Bridge Page Badges

### Problem
Pages with high betweenness centrality are critical navigation hubs, but authors and readers don't know which pages connect different content areas.

### Solution
Auto-detect and badge bridge pages based on betweenness centrality threshold.

### Design

```python
# In Page model or template context
@property
def is_bridge_page(self) -> bool:
    """Check if page is a navigation bridge (high betweenness)."""
    if not hasattr(self, '_betweenness_score'):
        return False
    # Top 10% by betweenness = bridge
    return self._betweenness_score > self._site.graph_thresholds.bridge_percentile

@property  
def bridge_badge(self) -> str | None:
    """Get bridge badge HTML if applicable."""
    if self.is_bridge_page:
        return '<span class="badge badge-bridge" title="Navigation hub">🌉 Bridge</span>'
    return None
```

### Template Integration

```html
<!-- In page header -->
<h1>
  {{ page.title }}
  {% if page.bridge_badge %}{{ page.bridge_badge | safe }}{% endif %}
</h1>
```

### Visual Design

```css
.badge-bridge {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-left: 8px;
}
```

---

## Feature 3: Community Labels

### Problem
Louvain community detection reveals topic clusters, but this information is only visible via CLI. Authors don't know which content "family" a page belongs to.

### Solution
Surface community membership in templates with links to cluster siblings.

### Design

```python
# bengal/analysis/community_integration.py

@dataclass
class CommunityInfo:
    """Community metadata for a page."""
    id: int
    name: str | None  # Auto-generated or user-defined
    size: int
    top_pages: list[Page]  # Most connected in cluster

def get_community_name(community: Community, graph: KnowledgeGraph) -> str:
    """
    Auto-generate community name from shared tags/categories.

    Heuristic:
    1. Find most common tag among community pages
    2. If >50% share a tag, use it: "Python Tutorial Cluster"
    3. Otherwise use most connected page title: "Getting Started Cluster"
    """
    ...
```

### Template Integration

```html
<!-- templates/partials/community-badge.html -->
{% if page.community %}
<div class="community-info">
  <span class="community-label">
    🔗 Part of the <strong>{{ page.community.name }}</strong> cluster
  </span>
  <details class="cluster-siblings">
    <summary>{{ page.community.size }} related pages</summary>
    <ul>
      {% for sibling in page.community.top_pages[:5] %}
      <li><a href="{{ sibling.url }}">{{ sibling.title }}</a></li>
      {% endfor %}
    </ul>
  </details>
</div>
{% endif %}
```

### Configuration

```toml
[graph.communities]
enabled = true
show_in_templates = true
auto_name = true  # Generate names from shared tags
min_size = 3      # Don't show for tiny clusters
```

---

## Feature 4: Dev Mode Link Suggestions

### Problem
Link suggestions only appear after running `bengal graph suggest`. Authors miss opportunities while actively writing content.

### Solution
Surface real-time link suggestions in dev server mode.

### Design Options

#### Option A: Console Hints (Low Effort)

```
[bengal serve] Page changed: docs/python/basics.md
              💡 Suggestion: Link to "Python Advanced Topics" (0.78 score)
                 Reason: Same community, high PageRank
```

**Pros**: Zero UI changes, immediate value
**Cons**: Easy to miss, no interactivity

#### Option B: Dev Server Overlay (Medium Effort)

Inject a floating panel in dev mode showing suggestions for current page:

```html
<!-- Injected only in dev mode -->
<div id="bengal-dev-suggestions" class="dev-overlay">
  <h4>💡 Link Suggestions</h4>
  <ul>
    <li>
      <button onclick="copyLink('python-advanced')">📋</button>
      <a href="/docs/python/advanced/">Python Advanced Topics</a>
      <span class="score">0.78</span>
    </li>
  </ul>
</div>
```

**Pros**: Visible, actionable, copy-to-clipboard
**Cons**: Requires JS injection, overlay UI

#### Option C: VS Code Extension Integration (Future)

Send suggestions via WebSocket to editor extension for inline display.

**Pros**: In-editor experience, zero context switch
**Cons**: Requires extension development

### Recommended: Option B (Dev Server Overlay)

Implementation path:
1. Add `dev_suggestions` field to page context in dev mode
2. Inject overlay HTML/CSS/JS in base template when `config.dev_server`
3. Compute suggestions lazily on page render (reuse graph from build context)

---

## Feature 5: Auto-Generated Insights Page

### Problem
Site-wide SEO and content health insights require running multiple CLI commands. There's no single dashboard view.

### Solution
Auto-generate `/insights/` page during build with actionable SEO intelligence.

### Content Structure

```markdown
# 📊 Content Insights

## Health Summary
- **Total Pages**: 773
- **Orphans**: 12 ⚠️
- **Average Connectivity**: 4.3 links/page
- **Modularity Score**: 0.42 (good structure)

## 🚨 Action Items

### Orphaned Pages (12)
These pages have no incoming links and may not be discoverable:

| Page | Section | Suggestion |
|------|---------|------------|
| Old API Reference | /docs/api/ | Add link from API Overview |
| Draft Tutorial | /tutorials/ | Link from Getting Started |

### Underlinked Hubs (5)
High-importance pages that could use more incoming links:

| Page | PageRank | Current Links | Suggested Links |
|------|----------|---------------|-----------------|
| Configuration Guide | 0.062 | 8 | +3 from tutorials |

### Community Health
| Cluster | Size | Cohesion | Top Page |
|---------|------|----------|----------|
| Python Tutorials | 24 | High | Getting Started |
| API Reference | 18 | Medium | API Overview |
| Blog Posts | 45 | Low | (dispersed) |

## 📈 Recommendations

1. **Fix orphan pages**: 12 pages are unreachable via navigation
2. **Strengthen clusters**: Blog posts lack internal linking
3. **Add bridge links**: Connect Python Tutorials → API Reference
```

### Implementation

```python
# bengal/postprocess/insights_page.py

class InsightsPageGenerator:
    """Generate /insights/ dashboard from graph analysis."""

    def __init__(self, site: Site, graph: KnowledgeGraph):
        self.site = site
        self.graph = graph

    def generate(self) -> str:
        """Generate insights markdown content."""
        sections = [
            self._health_summary(),
            self._orphan_report(),
            self._underlinked_hubs(),
            self._community_health(),
            self._recommendations(),
        ]
        return "\n\n".join(sections)
```

### Configuration

```toml
[insights]
enabled = true
path = "/insights/"
include_in_sitemap = false  # Internal page
include_in_search = false
require_auth = false  # Or true for private sites
```

---

## Architecture Impact

### BuildContext Changes

```python
# bengal/utils/build_context.py (extends rfc-lazy-build-artifacts.md)

@dataclass
class BuildContext:
    # Existing fields...

    # Add computed graph artifacts
    _pagerank_results: PageRankResults | None = None
    _community_results: CommunityDetectionResults | None = None
    _path_results: PathAnalysisResults | None = None

    @property
    def pagerank(self) -> PageRankResults | None:
        """Lazy-computed PageRank (cached for build duration)."""
        if self._pagerank_results is None and self.knowledge_graph:
            self._pagerank_results = self.knowledge_graph.compute_pagerank()
        return self._pagerank_results
```

### Template Context Enhancement

```python
# bengal/rendering/renderer.py

def _build_page_context(self, page: Page, ctx: BuildContext) -> dict:
    """Build template context with graph intelligence."""
    context = {
        "page": page,
        "site": self.site,
        # ... existing context
    }

    # Add graph intelligence if available
    if ctx.knowledge_graph and ctx.knowledge_graph._built:
        context["page_graph"] = {
            "pagerank": ctx.pagerank.get_score(page) if ctx.pagerank else None,
            "community": ctx.communities.get_community_for_page(page) if ctx.communities else None,
            "is_bridge": self._is_bridge_page(page, ctx),
            "is_orphan": self._is_orphan(page, ctx),
            "related": self._get_graph_related(page, ctx),
        }

    return context
```

### New Modules

```
bengal/analysis/
├── __init__.py
├── knowledge_graph.py      # Existing
├── page_rank.py            # Existing
├── community_detection.py  # Existing
├── link_suggestions.py     # Existing
├── path_analysis.py        # Existing
├── graph_visualizer.py     # Existing
├── related_by_graph.py     # NEW: Graph-aware related pages
└── insights_generator.py   # NEW: /insights/ page generator

bengal/postprocess/
├── special_pages.py        # Add insights page generation
└── ...
```

---

## Implementation Phases

### Phase 1: Foundation (1 week)
**Goal**: Enable graph data in templates

- [ ] Extend `BuildContext` with lazy graph artifacts (per `rfc-lazy-build-artifacts.md`)
- [ ] Add `page_graph` to template context
- [ ] Create `is_bridge_page`, `is_orphan` computed properties
- [ ] Add configuration schema for graph features

### Phase 2: Template Features (1 week)
**Goal**: Surface intelligence in rendered pages

- [ ] Implement `related_by_graph.py` engine
- [ ] Create `partials/related-by-graph.html` template
- [ ] Create `partials/community-badge.html` template
- [ ] Add bridge badge to page headers
- [ ] Add CSS for new components

### Phase 3: Insights Page (1 week)
**Goal**: Auto-generated dashboard

- [ ] Implement `InsightsPageGenerator`
- [ ] Add to `SpecialPagesGenerator`
- [ ] Create `/insights/` template
- [ ] Add configuration options

### Phase 4: Dev Mode Suggestions (1 week)
**Goal**: Real-time authoring assistance

- [ ] Implement dev-mode suggestion injection
- [ ] Create overlay HTML/CSS/JS
- [ ] Add WebSocket or polling for live updates
- [ ] Test with hot reload

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance regression | Build time increases | Lazy computation (rfc-lazy-build-artifacts.md) |
| Template bloat | Slower page loads | Conditional rendering, CSS-in-head |
| Information overload | Confusing UX | Progressive disclosure, collapsible sections |
| Graph not built | Features fail silently | Graceful degradation, null checks |
| Dev overlay intrusive | Annoying in dev | Easy dismiss, remember preference |

---

## Configuration Summary

```toml
# bengal.toml

[graph]
enabled = true  # Master switch for all graph features

[graph.related]
enabled = true
limit = 5
show_reasons = true

[graph.badges]
bridge = true
orphan = true

[graph.communities]
enabled = true
show_in_templates = true
auto_name = true
min_size = 3

[graph.dev_suggestions]
enabled = true
overlay = true
console = true

[insights]
enabled = true
path = "/insights/"
include_in_sitemap = false
```

---

## Success Criteria

1. **Adoption**: >50% of sites enable at least one graph template feature
2. **Performance**: <100ms overhead for graph context in templates
3. **Actionability**: Average 3+ link suggestions implemented per site
4. **SEO**: Measurable reduction in orphan pages after using insights

---

## Open Questions

1. **Community naming heuristic** - What's the best algorithm for auto-generating meaningful cluster names?
2. **Dev overlay UX** - Should suggestions auto-hide after N seconds or persist?
3. **Insights page access** - Should it be password-protected by default?
4. **Badge threshold** - What percentile defines "bridge page"? (Currently 90th)

---

## References

- `bengal/analysis/knowledge_graph.py` - Core graph implementation
- `bengal/analysis/page_rank.py` - PageRank algorithm
- `bengal/analysis/community_detection.py` - Louvain implementation
- `bengal/analysis/link_suggestions.py` - Suggestion engine
- `plan/active/rfc-lazy-build-artifacts.md` - Prerequisite for performance
- `plan/completed/graph-minimap-implementation.md` - Prior art for visualization

---

## Changelog

- **2025-12-05**: Initial draft
