# Graph Analysis Commands Investigation

**Date**: 2025-01-27  
**Status**: Investigation Complete → Fixing

## Problem Summary

All graph analysis commands report **0 links detected** when analyzing `site/` content, even though pages contain internal links. This breaks:
- Link-based analysis (PageRank, communities, bridges)
- Connectivity statistics
- Hub/leaf/orphan detection

The `suggest` command works because it uses semantic similarity (tags) rather than existing links.

## Root Cause

**Issue**: `page.links` is empty when the knowledge graph is built.

**Why**:
1. `extract_links()` is called during **rendering** (`pipeline.py:209`)
2. Knowledge graph is built right after **discovery** (`graph/__main__.py:87-92`)
3. Discovery happens **before** rendering, so `page.links` is never populated

**Code Flow**:
```
ContentOrchestrator.discover()
  → Creates Page objects (no links extracted)
  → KnowledgeGraph.build()
    → _analyze_cross_references()
      → for link in getattr(page, "links", []):  # ← Empty!
```

**Evidence**:
- `bengal/bengal/rendering/pipeline.py:209` - `extract_links()` called during rendering
- `bengal/bengal/analysis/knowledge_graph.py:180` - Expects `page.links` to exist
- `bengal/bengal/core/page/operations.py:66-80` - `extract_links()` method exists but not called early

## Original Intent of Each Command

### 1. `graph analyze` - Site Structure Analysis
**Purpose**: Provide overview of site connectivity and structure

**Intended Output**:
- Total pages and links
- Connectivity distribution (hubs, mid-tier, leaves)
- Top hub pages
- Orphaned pages list
- Insights for optimization

**Current State**: ✅ Works but shows 0 links (all pages appear as orphans)

**Use Cases**:
- Content strategy (find orphaned pages)
- Performance optimization (hub-first streaming)
- Navigation design (understand structure)
- SEO improvements (link structure)

### 2. `graph pagerank` - Page Importance Ranking
**Purpose**: Identify most important pages using PageRank algorithm

**Intended Output**:
- Top N pages by PageRank score
- Incoming/outgoing link counts
- Score distribution statistics
- Convergence metrics

**Current State**: ❌ Broken - all pages have identical scores (0.00036408) because no links detected

**Use Cases**:
- Identify most important content
- Prioritize content updates
- Guide navigation and sitemap design
- Find underlinked valuable content

**Algorithm**: Standard PageRank with damping factor (default 0.85)

### 3. `graph communities` - Topical Clustering
**Purpose**: Discover natural clusters of related pages using Louvain algorithm

**Intended Output**:
- List of communities with sizes
- Top pages per community
- Modularity score
- Community statistics

**Current State**: ❌ Broken - finds 412 communities (one per page) because no connections

**Use Cases**:
- Discover hidden content structure
- Organize content into logical groups
- Identify topic clusters
- Guide taxonomy creation

**Algorithm**: Louvain community detection with configurable resolution

### 4. `graph bridges` - Navigation Analysis
**Purpose**: Identify bridge pages and navigation bottlenecks

**Intended Output**:
- Top bridge pages (betweenness centrality)
- Most accessible pages (closeness centrality)
- Network diameter and average path length
- Navigation insights

**Current State**: ❌ Broken - all centrality scores are 0.0 because no paths exist

**Use Cases**:
- Optimize navigation structure
- Identify critical pages
- Improve content discoverability
- Find navigation gaps

**Metrics**:
- **Betweenness**: Pages that connect different parts of site
- **Closeness**: Pages easy to reach from anywhere

### 5. `graph suggest` - Link Suggestions
**Purpose**: Generate smart link suggestions to improve internal linking

**Intended Output**:
- Top N link suggestions with scores
- Reasons for each suggestion (shared tags, PageRank, etc.)
- Summary statistics

**Current State**: ✅ Works! Uses semantic similarity (tags/categories) rather than existing links

**Use Cases**:
- Improve internal linking structure
- Boost SEO through better connectivity
- Increase content discoverability
- Fill navigation gaps

**Signals Used**:
- Topic similarity (shared tags/categories)
- PageRank importance
- Betweenness centrality (bridge pages)
- Link gaps (underlinked content)

## Fix Strategy

### Option 1: Extract Links Before Graph Build (Recommended)
**Approach**: Call `extract_links()` on all pages after discovery, before building graph

**Pros**:
- Simple, minimal changes
- Works with existing code
- No performance impact (links extracted anyway during rendering)

**Cons**:
- Requires parsing markdown content (but we have content already)

**Implementation**:
```python
# In graph commands, after discovery:
for page in site.pages:
    if not hasattr(page, 'links') or not page.links:
        page.extract_links()

# Then build graph
graph_obj = KnowledgeGraph(site)
graph_obj.build()
```

### Option 2: Extract Links On-Demand in KnowledgeGraph
**Approach**: Extract links in `_analyze_cross_references()` if not already extracted

**Pros**:
- More defensive (works even if links not extracted)
- Centralized logic

**Cons**:
- Graph analysis shouldn't mutate pages
- Less clear when links are extracted

**Implementation**:
```python
def _analyze_cross_references(self) -> None:
    for page in self.site.pages:
        # Extract links if not already done
        if not hasattr(page, 'links') or not page.links:
            page.extract_links()

        for link in page.links:
            # ... rest of logic
```

### Option 3: Extract Links During Discovery
**Approach**: Extract links when pages are created during discovery

**Pros**:
- Links always available
- No need to remember to extract

**Cons**:
- Discovery phase shouldn't parse content (separation of concerns)
- Performance impact (parsing all pages during discovery)

**Recommendation**: ❌ Not recommended - breaks separation of concerns

## Recommended Fix

**Use Option 1**: Extract links before graph build in each graph command.

**Why**:
- Graph analysis is a separate concern from rendering
- Links are needed for analysis, so extract them when needed
- Minimal code changes
- Clear intent

**Files to Modify**:
1. `bengal/bengal/cli/commands/graph/__main__.py` - `analyze` command
2. `bengal/bengal/cli/commands/graph/pagerank.py` - `pagerank` command
3. `bengal/bengal/cli/commands/graph/communities.py` - `communities` command
4. `bengal/bengal/cli/commands/graph/bridges.py` - `bridges` command
5. `bengal/bengal/cli/commands/graph/suggest.py` - Already works, but should extract for consistency

**Helper Function** (optional):
Create a helper in `knowledge_graph.py`:
```python
def _ensure_links_extracted(self) -> None:
    """Extract links from all pages if not already extracted."""
    for page in self.site.pages:
        if not hasattr(page, 'links') or not page.links:
            page.extract_links()
```

Then call in `build()` before `_analyze_cross_references()`.

## Testing Plan

1. **Before Fix**: Run all commands, verify 0 links detected
2. **After Fix**:
   - Run `graph analyze` - should show links and connectivity
   - Run `graph pagerank` - should show varied scores
   - Run `graph communities` - should find real communities
   - Run `graph bridges` - should show non-zero centrality
   - Run `graph suggest` - should still work (already does)
3. **Verify**: Check that pages with links show up correctly

## Expected Results After Fix

### `graph analyze`
- Should show actual link counts
- Identify real hubs (pages with many incoming links)
- Show actual orphaned pages (those truly unlinked)
- Provide meaningful insights

### `graph pagerank`
- Varied scores based on link structure
- Top pages should be those with many incoming links
- Scores should converge properly

### `graph communities`
- Find real communities (groups of connected pages)
- Modularity > 0 (indicates structure)
- Communities with multiple pages

### `graph bridges`
- Non-zero betweenness/closeness scores
- Identify actual bridge pages
- Meaningful path length and diameter

## Related Files

- `bengal/bengal/analysis/knowledge_graph.py` - Core graph building logic
- `bengal/bengal/core/page/operations.py` - Link extraction method
- `bengal/bengal/rendering/pipeline.py` - Where links are currently extracted
- `bengal/bengal/cli/commands/graph/*.py` - CLI commands

## Next Steps

1. ✅ Investigation complete
2. ✅ Implement fix (Option 1)
3. ✅ Test with `site/` content
4. ✅ Verify all commands work correctly
5. ✅ Fix complete and verified

## Fix Results

After implementing the fix, all commands now work correctly:

### `graph analyze`
- ✅ **504 total links** detected (was 0)
- ✅ **2.5 average links** per page
- ✅ **17 hub pages** identified (was 0)
- ✅ **92 orphaned pages** (down from 412)
- ✅ Proper connectivity distribution

### `graph pagerank`
- ✅ **Varied scores** (0.000632 avg, 0.017540 max)
- ✅ **Converged in 12 iterations**
- ✅ Top pages: rendering API (0.0175), cli API (0.0149), utils API (0.0096)
- ✅ **High score concentration** (proper distribution)

### `graph communities`
- ✅ **112 communities** found (was 412 - one per page)
- ✅ **Modularity: 0.6594** (high - good clustering!)
- ✅ Largest community: 42 pages
- ✅ **5 communities >= 3 pages** (meaningful clusters)

### `graph bridges`
- ✅ **Non-zero centrality scores**
- ✅ **Network diameter: 7 hops**
- ✅ **Average path length: 2.00**
- ✅ Top bridge: "Start Writing" (betweenness: 0.00125)

### `graph suggest`
- ✅ Already worked (uses semantic similarity)
- ✅ Still generates 4120 suggestions

## Implementation Details

**Change Made**: Added `_ensure_links_extracted()` method to `KnowledgeGraph` that extracts links from all pages before building the graph.

**Files Modified**:
- `bengal/bengal/analysis/knowledge_graph.py`:
  - Added `_ensure_links_extracted()` method
  - Call it at start of `build()` method
  - Fixed bug in `format_stats()` (was using `id(page)` instead of `page`)

**Impact**:
- All graph analysis commands now work correctly
- No breaking changes
- Minimal performance impact (links extracted once, cached on page)
