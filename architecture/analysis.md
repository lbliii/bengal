# Analysis System (`bengal/analysis/`)

Bengal includes a comprehensive analysis system that helps understand and optimize site structure, connectivity, and content relationships.

## Overview

The analysis module provides tools for:
- **Knowledge Graph Analysis**: Build and analyze page connectivity through links, taxonomies, and menus
- **PageRank**: Compute page importance scores using Google's PageRank algorithm
- **Community Detection**: Discover topical clusters using the Louvain method
- **Path Analysis**: Identify navigation bridges and bottlenecks using centrality metrics
- **Link Suggestions**: Get smart recommendations for internal linking
- **Graph Visualization**: Generate interactive visualizations of site structure
- **Performance Advisor**: Analyze and recommend performance optimizations

## Knowledge Graph (`bengal/analysis/knowledge_graph.py`)

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

graph = KnowledgeGraph(site)
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
```

**Provides insights for**:
- Content strategy (find orphaned pages)
- Performance optimization (hub-first streaming)
- Navigation design (understand structure)
- SEO improvements (link structure)

## PageRank (`bengal/analysis/page_rank.py`)

**Purpose**: Computes page importance scores using Google's PageRank algorithm with the iterative power method.

**Algorithm considers**:
- Number of incoming links (popularity)
- Importance of pages linking to it (authority)
- Damping factor for random navigation (user behavior)

**Key Classes**:

| Class | Description |
|-------|-------------|
| `PageRankComputer` | Computes PageRank scores iteratively |
| `PageRankResults` | Results with scores, convergence info, and ranking methods |

**Usage**:
```python
from bengal.analysis.page_rank import PageRankComputer

computer = PageRankComputer(knowledge_graph, damping_factor=0.85)
results = computer.compute(max_iterations=100)

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

## Community Detection (`bengal/analysis/community_detection.py`)

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
from bengal.analysis.community_detection import LouvainCommunityDetector

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

## Path Analysis (`bengal/analysis/path_analysis.py`)

**Purpose**: Analyze navigation paths and page accessibility using centrality metrics.

**Computes**:
- **Betweenness centrality**: Pages that connect different parts of the site (bridges)
- **Closeness centrality**: Pages that are easy to reach from anywhere (accessible)
- **Shortest paths**: Navigation paths between pages

**Key Classes**:

| Class | Description |
|-------|-------------|
| `PathAnalyzer` | Computes centrality metrics using Brandes' algorithm |
| `PathAnalysisResults` | Results with centrality scores and path queries |

**Usage**:
```python
from bengal.analysis.path_analysis import PathAnalyzer

analyzer = PathAnalyzer(knowledge_graph)
results = analyzer.analyze()

# Find bridge pages (navigation bottlenecks)
bridges = results.get_top_bridges(10)
for page, score in bridges:
    print(f"Bridge: {page.title} (score: {score:.4f})")

# Find shortest path between pages
path = analyzer.find_shortest_path(source_page, target_page)
if path:
    print(" → ".join([p.title for p in path]))
```

**Applications**:
- Identify navigation bottlenecks
- Optimize site structure
- Find critical pages for user flows
- Improve site accessibility

## Link Suggestions (`bengal/analysis/link_suggestions.py`)

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
from bengal.analysis.link_suggestions import LinkSuggestionEngine

engine = LinkSuggestionEngine(knowledge_graph)
results = engine.generate_suggestions(min_score=0.5, max_per_page=5)

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

## Graph Visualization (`bengal/analysis/graph_visualizer.py`)

**Purpose**: Generate interactive visualizations of site structure using D3.js force-directed graphs.

**Features**:
- Node sizing by PageRank
- Node coloring by community
- Edge thickness by connection strength
- Interactive zoom and pan
- Node hover information
- Responsive design

**Usage**:
```python
from bengal.analysis import GraphVisualizer

visualizer = GraphVisualizer(knowledge_graph)
visualizer.generate(
    output_path="public/graph.html",
    include_pagerank=True,
    include_communities=True
)
```

## Performance Advisor (`bengal/analysis/performance_advisor.py`)

**Purpose**: Analyzes site structure and provides performance optimization recommendations.

**Analyzes**:
- Hub-first streaming opportunities
- Parallel rendering candidates
- Cache hit potential
- Link structure efficiency

**Usage**:
```python
from bengal.analysis.performance_advisor import PerformanceAdvisor

advisor = PerformanceAdvisor(site, knowledge_graph)
recommendations = advisor.analyze()

for rec in recommendations:
    print(f"{rec.category}: {rec.message}")
    print(f"  Impact: {rec.impact}")
    print(f"  Effort: {rec.effort}")
```

## CLI Integration

The analysis system is integrated into the CLI with dedicated commands:

```bash
# Analyze site structure
bengal graph

# Show site structure as tree
bengal graph --tree

# Generate interactive visualization
bengal graph --output public/graph.html

# Compute PageRank scores
bengal pagerank --top 20

# Detect communities
bengal communities --min-size 3

# Find bridge pages
bengal bridges --top 10

# Get link suggestions
bengal suggest --min-score 0.5
```

See "CLI Commands" section for detailed command documentation.
