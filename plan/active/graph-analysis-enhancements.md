# Graph Analysis Enhancements

**Date**: 2025-01-27  
**Status**: Planning  
**Priority**: High

## Current State

✅ **Working Well**:
- Link detection fixed (extracts links before graph build)
- Autodoc filtering implemented (excludes API reference pages)
- All 5 commands functional (analyze, pagerank, communities, bridges, suggest)
- Visualization generates HTML (but has a bug)
- Basic insights provided

## Critical Fixes Needed

### 1. Fix Graph Visualization Bug 🔴

**Issue**: Visualization uses `id(page)` for node IDs but `outgoing_refs` uses pages directly as keys.

**Location**: `bengal/bengal/analysis/graph_visualizer.py:140-146`

**Current Code**:
```python
# Generate edges
for page in self.site.pages:
    source_id = str(id(page))
    # Get outgoing references
    target_ids = self.graph.outgoing_refs.get(id(page), set())  # ❌ Wrong!
```

**Fix**: Use pages directly as keys (they're hashable):
```python
# Generate edges
for page in self.graph.get_analysis_pages():  # Use filtered pages
    source_id = self._get_page_id(page)
    # Get outgoing references
    targets = self.graph.outgoing_refs.get(page, set())  # ✅ Correct
    for target in targets:
        target_id = self._get_page_id(target)
        edges.append(...)
```

**Impact**: Visualization edges won't render correctly without this fix.

## High-Value Enhancements

### 2. Actionable Insights & Recommendations 🟡

**Current**: Basic statistics (hub count, orphan count, etc.)

**Enhancement**: Add actionable recommendations:

```python
def get_actionable_insights(self) -> list[str]:
    """Generate actionable recommendations for improving site structure."""
    insights = []

    # Orphaned pages
    orphans = self.get_orphans()
    if len(orphans) > 10:
        top_orphans = orphans[:5]
        insights.append(
            f"🔗 Link {len(orphans)} orphaned pages. Start with: "
            f"{', '.join(p.title for p in top_orphans)}"
        )

    # Underlinked valuable content
    high_pagerank_orphans = [
        p for p in orphans
        if self.get_pagerank_score(p) > 0.001
    ]
    if high_pagerank_orphans:
        insights.append(
            f"⭐ {len(high_pagerank_orphans)} high-value pages are underlinked. "
            f"Consider adding navigation or cross-links."
        )

    # Link density
    if self.metrics.avg_connectivity < 2:
        insights.append(
            f"📊 Low link density ({self.metrics.avg_connectivity:.1f} links/page). "
            f"Consider adding more internal links for better SEO."
        )

    # Bridge pages
    bridges = self.analyze_paths().get_top_bridges(5)
    if bridges:
        insights.append(
            f"🌉 Top bridge pages: {', '.join(p.title for p, _ in bridges)}. "
            f"These are critical for navigation - ensure they're prominent."
        )

    return insights
```

**Integration**: Add to `graph analyze` output and `format_stats()`.

### 3. SEO-Focused Analysis 🟡

**Enhancement**: Add SEO-specific insights:

- **Internal linking structure**: Analyze anchor text distribution
- **Link equity flow**: Identify pages that should pass more link equity
- **Orphan page detection**: Pages with no internal links (SEO risk)
- **Hub optimization**: Ensure important pages are hubs
- **Link depth**: Average clicks from homepage to content

**New Command**: `bengal utils graph seo` or add `--seo` flag to `analyze`

### 4. Content Gap Detection 🟡

**Enhancement**: Identify content gaps based on link structure:

- **Missing bridge pages**: Topics that should connect but don't
- **Underlinked topics**: Tags/categories with few cross-links
- **Isolated content**: Pages that should link to related content but don't
- **Navigation gaps**: Sections that should have index pages

**Implementation**: Analyze tag/category overlap vs. link structure.

### 5. Enhanced Export Formats 🟢

**Current**: JSON export for some commands

**Enhancement**: Add more formats:

- **CSV**: For spreadsheet analysis
  ```bash
  bengal utils graph pagerank --format csv > pagerank.csv
  ```
- **GraphML**: For external graph tools (Gephi, Cytoscape)
- **Markdown reports**: Formatted analysis reports
- **JSON-LD**: For structured data

### 6. Performance Recommendations 🟢

**Enhancement**: Add performance-focused insights:

- **Hub-first streaming**: Identify pages to keep in memory
- **Lazy loading opportunities**: Pages that can be loaded on-demand
- **Cache priorities**: Pages that should be cached aggressively

**Integration**: Connect with `performance_advisor.py`

### 7. Interactive Visualization Improvements 🟢

**Current**: Basic D3.js force-directed graph

**Enhancements**:
- **Filtering**: Filter by tags, sections, connectivity level
- **Search**: Find specific pages quickly
- **Path highlighting**: Show paths between selected pages
- **Community highlighting**: Color-code communities
- **Export**: Export filtered views as images/PDFs

### 8. Integration with Health Checks 🟢

**Enhancement**: Add graph analysis to health checks:

```bash
bengal health check --include graph
```

**Checks**:
- Orphaned pages (warn if >10%)
- Low link density (warn if <2 links/page)
- Missing navigation (warn if important pages aren't in menus)
- Broken link structure (pages that should link but don't)

### 9. Batch Link Suggestions 🟢

**Enhancement**: Generate actionable link suggestions:

```bash
bengal utils graph suggest --apply
```

**Features**:
- Generate markdown with suggested links
- Create TODO list for content team
- Auto-apply low-risk suggestions (with confirmation)
- Track applied suggestions

### 10. Historical Tracking 🟢

**Enhancement**: Track graph metrics over time:

- Store metrics in build cache
- Compare current vs. previous build
- Show trends (improving/declining connectivity)
- Alert on regressions

## Implementation Priority

### Phase 1: Critical Fixes (Do First)
1. ✅ Fix visualization bug (edges not rendering)
2. ✅ Use filtered pages in visualization

### Phase 2: High-Value Quick Wins (This Sprint)
3. ✅ Add actionable insights to `analyze` command
4. ✅ Enhance `format_stats()` with recommendations
5. ✅ Add CSV export format

### Phase 3: Feature Enhancements (Next Sprint)
6. ✅ SEO-focused analysis (link depth, link equity flow, orphan risk)
7. ✅ Content gap detection (missing cross-links, section index pages)
8. ✅ Enhanced visualization (filtering by type, improved search)

### Phase 4: Integration & Polish (Future)
9. ✅ Health check integration
10. ✅ Historical tracking
11. ✅ Batch link suggestions

## Example Enhanced Output

### Before:
```
📊 Knowledge Graph Statistics
Total pages:        82
Total links:        79
Average links:      2.0 per page
```

### After:
```
📊 Knowledge Graph Statistics
Total pages:        82
Total links:        79
Average links:      2.0 per page

💡 Actionable Recommendations:
  🔗 Link 48 orphaned pages. Start with: Release 0.1.1, Release 0.1.2, About
  ⭐ 5 high-value pages are underlinked. Consider adding navigation.
  📊 Low link density (2.0 links/page). Consider adding more internal links.
  🌉 Top bridge pages: Start Writing, Documentation, Guides. Ensure prominent.

🎯 SEO Insights:
  • 58% of pages are leaves (good for performance)
  • Average link depth: 2.9 clicks from homepage
  • 3 pages should pass more link equity (high PageRank, few outgoing links)

📈 Performance Opportunities:
  • 1 hub page identified (keep in memory)
  • 58 leaf pages can be lazy-loaded
  • Consider caching top 10 pages by PageRank
```

## Testing Strategy

1. **Unit Tests**: Test new insight generation logic
2. **Integration Tests**: Test with `site/` content
3. **Visual Tests**: Verify visualization renders correctly
4. **Performance Tests**: Ensure analysis completes in reasonable time

## Success Metrics

- ✅ Visualization renders correctly with all edges
- ✅ Actionable insights provided for 80%+ of sites
- ✅ CSV export works for all commands
- ✅ SEO analysis identifies real issues
- ✅ Health check integration flags graph issues

## Related Files

- `bengal/bengal/analysis/knowledge_graph.py` - Core graph logic
- `bengal/bengal/analysis/graph_visualizer.py` - Visualization (needs bug fix)
- `bengal/bengal/cli/commands/graph/__main__.py` - CLI commands
- `bengal/bengal/health/` - Health check integration point
