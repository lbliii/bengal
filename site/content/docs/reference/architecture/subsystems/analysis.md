---
title: Analysis System
nav_title: Analysis
description: Graph analysis, PageRank, community detection, and link suggestions
weight: 20
category: subsystems
tags:
- subsystems
- analysis
- graph-analysis
- pagerank
- community-detection
- link-suggestions
keywords:
- analysis
- graph analysis
- PageRank
- community detection
- link suggestions
- knowledge graph
---

# Analysis System (`bengal/analysis/`)

Bengal includes a comprehensive analysis system that helps understand and optimize site structure, connectivity, and content relationships.

## Overview

The analysis module is organized into focused subpackages:

```
bengal/analysis/
├── graph/           # Graph-based page analysis
│   ├── knowledge_graph.py   # Central graph representation
│   ├── builder.py           # Graph construction
│   ├── analyzer.py          # Structure analysis (hubs, leaves, orphans)
│   ├── metrics.py           # Connectivity metrics
│   ├── reporter.py          # Human-readable insights
│   ├── visualizer.py        # D3.js visualization
│   ├── page_rank.py         # PageRank scoring
│   └── community_detection.py  # Louvain clustering
├── links/           # Link analysis
│   ├── suggestions.py       # Cross-linking recommendations
│   ├── patterns.py          # Link pattern detection
│   └── types.py             # Link classification
├── performance/     # Performance analysis
│   ├── advisor.py           # Build optimization tips
│   └── path_analysis.py     # Centrality metrics
├── content_intelligence.py  # Content analysis utilities
└── results.py               # Shared result types
```

The module provides tools for:
- **Knowledge Graph Analysis**: Build and analyze page connectivity through links, taxonomies, and menus
- **PageRank**: Compute page importance scores using Google's PageRank algorithm
- **Community Detection**: Discover topical clusters using the Louvain method
- **Path Analysis**: Identify navigation bridges and bottlenecks using centrality metrics
- **Link Suggestions**: Get smart recommendations for internal linking
- **Graph Visualization**: Generate interactive visualizations of site structure
- **Performance Advisor**: Analyze and recommend performance optimizations

## Knowledge Graph (`bengal/analysis/graph/knowledge_graph.py`)

**Purpose**: Analyzes the connectivity structure of a Bengal site by building a graph of all pages and their connections.

**Tracks connections through**:
- Internal links (cross-references)
- Taxonomies (tags, categories)
- Related posts
- Menu items

**Key Classes**:

| Class | Description |
|-------|-------------|
| `KnowledgeGraph` | Main analyzer that builds and queries the connectivity graph |
| `GraphMetrics` | Aggregated metrics (total pages, links, hubs, leaves, orphans) |
| `PageConnectivity` | Per-page connectivity information |

**Usage**:
```python
from bengal.analysis import KnowledgeGraph

graph = KnowledgeGraph(site, exclude_autodoc=True)  # Exclude API docs by default
graph.build()

# Find orphaned pages
orphans = graph.get_orphans()
print(f"Found {len(orphans)} orphaned pages")

# Find hub pages
hubs = graph.get_hubs(threshold=10)
print(f"Found {len(hubs)} hub pages")

# Get metrics
metrics = graph.metrics
print(f"Average connectivity: {metrics.avg_connectivity:.2f}")

# Get actionable recommendations
recommendations = graph.get_actionable_recommendations()
for rec in recommendations:
    print(rec)
```

**Key Features**:
- **Autodoc Filtering**: Excludes API reference pages from analysis by default (`exclude_autodoc=True`)
- **Actionable Recommendations**: Provides specific, actionable suggestions for improvement
- **Link Extraction**: Automatically extracts links from pages before analysis

**Provides insights for**:
- Content strategy (find orphaned pages)
- Performance optimization (hub-first streaming)
- Navigation design (understand structure)
- SEO improvements (link structure)

## PageRank (`bengal/analysis/graph/page_rank.py`)

**Purpose**: Computes page importance scores using Google's PageRank algorithm with the iterative power method.

**Algorithm considers**:
- Number of incoming links (popularity)
- Importance of pages linking to it (authority)
- Damping factor for random navigation (user behavior)

**Key Classes**:

| Class | Description |
|-------|-------------|
| `PageRankCalculator` | Computes PageRank scores iteratively |
| `PageRankResults` | Results with scores, convergence info, and ranking methods |

**Usage**:
```python
from bengal.analysis import KnowledgeGraph

graph = KnowledgeGraph(site)
graph.build()

# Compute PageRank (recommended: use the graph's convenience method)
results = graph.compute_pagerank(damping=0.85, max_iterations=100)

# Get top-ranked pages
top_pages = results.get_top_pages(limit=20)
for page, score in top_pages:
    print(f"{page.title}: {score:.4f}")

# Get pages above 80th percentile
important_pages = results.get_pages_above_percentile(80)
```

**Applications**:
- Prioritize important content
- Guide content promotion
- Optimize navigation structure
- Implement hub-first streaming

## Community Detection (`bengal/analysis/graph/community_detection.py`)

**Purpose**: Discovers topical clusters in content using the Louvain method for modularity optimization.

**Algorithm**: Two-phase iterative approach
1. Local optimization: Move nodes to communities that maximize modularity gain
2. Aggregation: Treat each community as a single node and repeat

**Key Classes**:

| Class | Description |
|-------|-------------|
| `LouvainCommunityDetector` | Implements Louvain method for community detection |
| `Community` | Represents a community of related pages |
| `CommunityDetectionResults` | Results with communities, modularity score, and query methods |

**Usage**:
```python
from bengal.analysis.graph.community_detection import LouvainCommunityDetector

detector = LouvainCommunityDetector(knowledge_graph)
results = detector.detect()

# Get largest communities
large_communities = results.get_largest_communities(limit=10)
for community in large_communities:
    print(f"Community {community.id}: {community.size} pages")

# Find which community a page belongs to
community = results.get_community_for_page(page)
```

**Applications**:
- Discover topical organization
- Guide content categorization
- Improve internal linking within topics
- Generate navigation menus

## Path Analysis (`bengal/analysis/performance/path_analysis.py`)

**Purpose**: Analyze navigation paths and page accessibility using centrality metrics.

**Computes**:
- **Betweenness centrality**: Pages that connect different parts of the site (bridges)
- **Closeness centrality**: Pages that are easy to reach from anywhere (accessible)
- **Shortest paths**: Navigation paths between pages

**Key Classes**:

| Class | Description |
|-------|-------------|
| `PathAnalyzer` | Computes centrality metrics with auto-scaling approximation |
| `PathAnalysisResults` | Results with centrality scores and approximation metadata |
| `PathSearchResult` | Results from path search with termination metadata |

**Scalability**: For large sites (>500 pages by default), automatically uses pivot-based approximation to achieve O(k*N) complexity instead of O(N²). This provides ~100x speedup for 10k page sites while maintaining accurate relative rankings.

**Usage**:
```python
from bengal.analysis.performance.path_analysis import PathAnalyzer

# Basic usage (auto-selects exact vs approximate)
analyzer = PathAnalyzer(knowledge_graph)
results = analyzer.analyze()

# With progress callback for long-running analysis
def on_progress(current, total, phase):
    print(f"{phase}: {current}/{total}")

results = analyzer.analyze(progress_callback=on_progress)
print(f"Approximate: {results.is_approximate}, pivots: {results.pivots_used}")

# Find bridge pages (navigation bottlenecks)
bridges = results.get_top_bridges(10)
for page, score in bridges:
    print(f"Bridge: {page.title} (score: {score:.4f})")

# Find shortest path between pages
path = analyzer.find_shortest_path(source_page, target_page)
if path:
    print(" → ".join([p.title for p in path]))

# Safe path finding with limits (prevents runaway computation)
result = analyzer.find_all_paths(
    source_page, target_page,
    max_length=10,
    max_paths=100,
    timeout_seconds=5.0
)
if not result.complete:
    print(f"Search stopped: {result.termination_reason}")
```

**Configuration**:
- `k_pivots`: Number of pivot nodes for approximation (default: 100)
- `seed`: Random seed for deterministic results (default: 42)
- `auto_approximate_threshold`: Use exact if pages ≤ this (default: 500)

**Applications**:
- Identify navigation bottlenecks
- Optimize site structure
- Find critical pages for user flows
- Improve site accessibility

## Link Suggestions (`bengal/analysis/links/suggestions.py`)

**Purpose**: Provides smart cross-linking recommendations based on multiple signals.

**Considers**:
- Topic similarity (shared tags, categories, keywords)
- PageRank importance (prioritize linking to high-value pages)
- Navigation patterns (betweenness, closeness)
- Current link structure (avoid over-linking, find gaps)

**Key Classes**:

| Class | Description |
|-------|-------------|
| `LinkSuggestionEngine` | Generates smart link suggestions |
| `LinkSuggestion` | A suggested link with score and reasons |
| `LinkSuggestionResults` | Collection of suggestions with query methods |

**Usage**:
```python
from bengal.analysis import KnowledgeGraph

graph = KnowledgeGraph(site)
graph.build()

# Generate suggestions (recommended: use the graph's convenience method)
results = graph.suggest_links(min_score=0.5, max_suggestions_per_page=5)

# Get suggestions for specific page
suggestions = results.get_suggestions_for_page(page, limit=10)
for suggestion in suggestions:
    print(f"Suggest linking to: {suggestion.target.title}")
    print(f"  Score: {suggestion.score:.3f}")
    print(f"  Reasons: {', '.join(suggestion.reasons)}")
```

**Helps improve**:
- Internal linking structure
- SEO through better site connectivity
- Content discoverability
- User navigation

## Graph Visualization (`bengal/analysis/graph/visualizer.py`)

**Purpose**: Generate interactive visualizations of site structure using D3.js force-directed graphs.

**Features**:
- Node sizing based on connectivity and content depth
- Node coloring by type (hub, orphan, regular, generated)
- Edge weight based on bidirectional links
- Interactive zoom and pan
- Search and filtering by title, tags, or type
- Theme-aware styling (light/dark mode)

**Usage**:
```python
from pathlib import Path
from bengal.analysis import KnowledgeGraph, GraphVisualizer

graph = KnowledgeGraph(site)
graph.build()

visualizer = GraphVisualizer(site, graph)
html = visualizer.generate_html(title="My Site Graph")
Path("public/graph.html").write_text(html)
```

## Performance Advisor (`bengal/analysis/performance/advisor.py`)

**Purpose**: Analyzes build statistics and provides performance optimization recommendations.

**Analyzes**:
- Parallel processing opportunities
- Incremental build potential
- Rendering bottlenecks
- Asset optimization
- Memory usage patterns
- Template complexity

**Grading System**: A (90-100), B (75-89), C (60-74), D (45-59), F (0-44)

**Usage**:
```python
from bengal.analysis.performance import analyze_build

# After a build completes, analyze its statistics
advisor = analyze_build(stats)

# Get performance grade
grade = advisor.get_grade()
print(f"Performance Grade: {grade.grade} ({grade.score}/100)")
print(f"Category: {grade.category}")

# Get top recommendations
for suggestion in advisor.get_top_suggestions(3):
    print(f"{suggestion.title}")
    print(f"  Impact: {suggestion.impact}")
    print(f"  Action: {suggestion.action}")
```

## CLI Integration

The analysis system is integrated into the CLI under `bengal graph`:

```bash
# Analyze site structure and get report
bengal graph report
bengal graph report --brief
bengal graph report --format json > report.json

# Find orphaned pages
bengal graph orphans
bengal graph orphans --level lightly
bengal graph orphans --format json > orphans.json

# Compute PageRank scores
bengal graph pagerank
bengal graph pagerank --top-n 50
bengal graph pagerank --format json > pagerank.json

# Detect communities
bengal graph communities
bengal graph communities --min-size 10
bengal graph communities --resolution 2.0

# Find bridge pages (high betweenness centrality)
bengal graph bridges
bengal graph bridges --metric closeness
bengal graph bridges --format json > bridges.json

# Get link suggestions
bengal graph suggest
bengal graph suggest --min-score 0.5
bengal graph suggest --format markdown > TODO.md
```

**Export Formats**:
All commands support multiple output formats:
- `table` (default) - Human-readable table format
- `json` - JSON for programmatic processing
- `markdown` - Markdown format (suggest command)

**Key Features**:
- **Actionable Recommendations**: The `report` command provides specific recommendations
- **Autodoc Filtering**: API reference pages are excluded by default for cleaner analysis
- **Multiple Export Formats**: Export results for further analysis or reporting

Refer to [Graph Analysis](../../../content/analysis/graph.md) for usage examples and workflows.
