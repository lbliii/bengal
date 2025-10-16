
---
title: "analysis.knowledge_graph"
type: python-module
source_file: "bengal/analysis/knowledge_graph.py"
css_class: api-content
description: "Knowledge Graph Analysis for Bengal SSG.  Analyzes page connectivity, identifies hubs and leaves, finds orphaned pages, and provides insights for optimization and content strategy."
---

# analysis.knowledge_graph

Knowledge Graph Analysis for Bengal SSG.

Analyzes page connectivity, identifies hubs and leaves, finds orphaned pages,
and provides insights for optimization and content strategy.

---

## Classes

### `GraphMetrics`


Metrics about the knowledge graph structure.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 6 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `total_pages`
  - `int`
  - Total number of pages analyzed
* - `total_links`
  - `int`
  - Total number of links between pages
* - `avg_connectivity`
  - `float`
  - Average connectivity score per page
* - `hub_count`
  - `int`
  - Number of hub pages (highly connected)
* - `leaf_count`
  - `int`
  - Number of leaf pages (low connectivity)
* - `orphan_count`
  - `int`
  - Number of orphaned pages (no connections at all)
:::

::::



### `PageConnectivity`


Connectivity information for a single page.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 7 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `page`
  - `'Page'`
  - The page object
* - `incoming_refs`
  - `int`
  - Number of incoming references
* - `outgoing_refs`
  - `int`
  - Number of outgoing references
* - `connectivity_score`
  - `int`
  - Total connectivity (incoming + outgoing)
* - `is_hub`
  - `bool`
  - True if page has many incoming references
* - `is_leaf`
  - `bool`
  - True if page has few connections
* - `is_orphan`
  - `bool`
  - True if page has no connections at all
:::

::::



### `KnowledgeGraph`


Analyzes the connectivity structure of a Bengal site.

Builds a graph of all pages and their connections through:
- Internal links (cross-references)
- Taxonomies (tags, categories)
- Related posts
- Menu items

Provides insights for:
- Content strategy (find orphaned pages)
- Performance optimization (hub-first streaming)
- Navigation design (understand structure)
- SEO improvements (link structure)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site', hub_threshold: int = 10, leaf_threshold: int = 2)
```

Initialize knowledge graph analyzer.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - Site instance to analyze
* - `hub_threshold`
  - `int`
  - `10`
  - Minimum incoming refs to be considered a hub
* - `leaf_threshold`
  - `int`
  - `2`
  - Maximum connectivity to be considered a leaf
:::

::::




---
#### `build`
```python
def build(self) -> None
```

Build the knowledge graph by analyzing all page connections.

This analyzes:
1. Cross-references (internal links between pages)
2. Taxonomy references (pages grouped by tags/categories)
3. Related posts (pre-computed relationships)
4. Menu items (navigation references)

Call this before using any analysis methods.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `get_connectivity`
```python
def get_connectivity(self, page: 'Page') -> PageConnectivity
```

Get connectivity information for a specific page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to analyze
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PageConnectivity` - PageConnectivity with detailed metrics

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_hubs`
```python
def get_hubs(self, threshold: int | None = None) -> list['Page']
```

Get hub pages (highly connected pages).

Hubs are pages with many incoming references. These are typically:
- Index pages
- Popular articles
- Core documentation



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `threshold`
  - `int | None`
  - `None`
  - Minimum incoming refs (defaults to self.hub_threshold)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']` - List of hub pages sorted by incoming references (descending)

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_leaves`
```python
def get_leaves(self, threshold: int | None = None) -> list['Page']
```

Get leaf pages (low connectivity pages).

Leaves are pages with few connections. These are typically:
- One-off blog posts
- Changelog entries
- Niche content



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `threshold`
  - `int | None`
  - `None`
  - Maximum connectivity (defaults to self.leaf_threshold)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']` - List of leaf pages sorted by connectivity (ascending)

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_orphans`
```python
def get_orphans(self) -> list['Page']
```

Get orphaned pages (no connections at all).

Orphans are pages with no incoming or outgoing references. These might be:
- Forgotten content
- Draft pages
- Pages that should be linked from navigation



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']` - List of orphaned pages sorted by slug

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_connectivity_score`
```python
def get_connectivity_score(self, page: 'Page') -> int
```

Get total connectivity score for a page.

Connectivity = incoming_refs + outgoing_refs



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to analyze
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int` - Connectivity score (higher = more connected)

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_layers`
```python
def get_layers(self) -> tuple[list['Page'], list['Page'], list['Page']]
```

Partition pages into three layers by connectivity.

Layers enable hub-first streaming builds:
- Layer 0 (Hubs): High connectivity, process first, keep in memory
- Layer 1 (Mid-tier): Medium connectivity, batch processing
- Layer 2 (Leaves): Low connectivity, stream and release



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[list['Page'], list['Page'], list['Page']]` - Tuple of (hubs, mid_tier, leaves)

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `get_metrics`
```python
def get_metrics(self) -> GraphMetrics
```

Get overall graph metrics.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`GraphMetrics` - GraphMetrics with summary statistics

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `format_stats`
```python
def format_stats(self) -> str
```

Format graph statistics as a human-readable string.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Formatted statistics string

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If graph hasn't been built yet



---
#### `compute_pagerank`
```python
def compute_pagerank(self, damping: float = 0.85, max_iterations: int = 100, force_recompute: bool = False) -> 'PageRankResults'
```

Compute PageRank scores for all pages in the graph.

PageRank assigns importance scores based on link structure.
Pages that are linked to by many important pages get high scores.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `damping`
  - `float`
  - `0.85`
  - Probability of following links vs random jump (default 0.85)
* - `max_iterations`
  - `int`
  - `100`
  - Maximum iterations before stopping (default 100)
* - `force_recompute`
  - `bool`
  - `False`
  - If True, recompute even if cached
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'PageRankResults'` - PageRankResults with scores and metadata




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.compute_pagerank()
    >>> top_pages = results.get_top_pages(10)
```


---
#### `compute_personalized_pagerank`
```python
def compute_personalized_pagerank(self, seed_pages: set['Page'], damping: float = 0.85, max_iterations: int = 100) -> 'PageRankResults'
```

Compute personalized PageRank from seed pages.

Personalized PageRank biases random jumps toward seed pages,
useful for finding pages related to a specific topic or set of pages.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `seed_pages`
  - `set['Page']`
  - -
  - Set of pages to bias toward
* - `damping`
  - `float`
  - `0.85`
  - Probability of following links vs random jump
* - `max_iterations`
  - `int`
  - `100`
  - Maximum iterations before stopping
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'PageRankResults'` - PageRankResults with personalized scores




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> # Find pages related to Python posts
    >>> python_posts = {p for p in site.pages if 'python' in p.tags}
    >>> results = graph.compute_personalized_pagerank(python_posts)
    >>> related = results.get_top_pages(10)
```


---
#### `get_top_pages_by_pagerank`
```python
def get_top_pages_by_pagerank(self, limit: int = 20) -> list[tuple['Page', float]]
```

Get top-ranked pages by PageRank score.

Automatically computes PageRank if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `limit`
  - `int`
  - `20`
  - Number of pages to return
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[tuple['Page', float]]` - List of (page, score) tuples sorted by score descending




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> top_pages = graph.get_top_pages_by_pagerank(10)
    >>> print(f"Most important: {top_pages[0][0].title}")
```


---
#### `get_pagerank_score`
```python
def get_pagerank_score(self, page: 'Page') -> float
```

Get PageRank score for a specific page.

Automatically computes PageRank if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to get score for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`float` - PageRank score (0.0 if page not found)




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> score = graph.get_pagerank_score(some_page)
    >>> print(f"Importance score: {score:.4f}")
```


---
#### `detect_communities`
```python
def detect_communities(self, resolution: float = 1.0, random_seed: int | None = None, force_recompute: bool = False) -> 'CommunityDetectionResults'
```

Detect topical communities using Louvain method.

Discovers natural clusters of related pages based on link structure.
Communities represent topic areas or content groups.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `resolution`
  - `float`
  - `1.0`
  - Resolution parameter (higher = more communities, default 1.0)
* - `random_seed`
  - `int | None`
  - `None`
  - Random seed for reproducibility
* - `force_recompute`
  - `bool`
  - `False`
  - If True, recompute even if cached
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'CommunityDetectionResults'` - CommunityDetectionResults with discovered communities




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.detect_communities()
    >>> for community in results.get_largest_communities(5):
    ...     print(f"Community {community.id}: {community.size} pages")
```


---
#### `get_community_for_page`
```python
def get_community_for_page(self, page: 'Page') -> int | None
```

Get community ID for a specific page.

Automatically detects communities if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to get community for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int | None` - Community ID or None if page not found




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> community_id = graph.get_community_for_page(some_page)
    >>> print(f"Page belongs to community {community_id}")
```


---
#### `analyze_paths`
```python
def analyze_paths(self, force_recompute: bool = False) -> 'PathAnalysisResults'
```

Analyze navigation paths and centrality metrics.

Computes:
- Betweenness centrality: Pages that act as bridges
- Closeness centrality: Pages that are easily accessible
- Network diameter and average path length



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `force_recompute`
  - `bool`
  - `False`
  - If True, recompute even if cached
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'PathAnalysisResults'` - PathAnalysisResults with centrality metrics




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.analyze_paths()
    >>> bridges = results.get_top_bridges(10)
```


---
#### `get_betweenness_centrality`
```python
def get_betweenness_centrality(self, page: 'Page') -> float
```

Get betweenness centrality for a specific page.

Automatically analyzes paths if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to get centrality for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`float` - Betweenness centrality score




---
#### `get_closeness_centrality`
```python
def get_closeness_centrality(self, page: 'Page') -> float
```

Get closeness centrality for a specific page.

Automatically analyzes paths if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to get centrality for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`float` - Closeness centrality score




---
#### `suggest_links`
```python
def suggest_links(self, min_score: float = 0.3, max_suggestions_per_page: int = 10, force_recompute: bool = False) -> 'LinkSuggestionResults'
```

Generate smart link suggestions to improve site connectivity.

Uses multiple signals:
- Topic similarity (shared tags/categories)
- PageRank importance
- Betweenness centrality (bridge pages)
- Link gaps (underlinked content)



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `min_score`
  - `float`
  - `0.3`
  - Minimum score threshold for suggestions
* - `max_suggestions_per_page`
  - `int`
  - `10`
  - Maximum suggestions per page
* - `force_recompute`
  - `bool`
  - `False`
  - If True, recompute even if cached
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'LinkSuggestionResults'` - LinkSuggestionResults with all suggestions




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = graph.suggest_links()
    >>> for suggestion in results.get_top_suggestions(20):
    ...     print(f"{suggestion.source.title} -> {suggestion.target.title}")
```


---
#### `get_suggestions_for_page`
```python
def get_suggestions_for_page(self, page: 'Page', limit: int = 10) -> list[tuple['Page', float, list[str]]]
```

Get link suggestions for a specific page.

Automatically generates suggestions if not already computed.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `page`
  - `'Page'`
  - -
  - Page to get suggestions for
* - `limit`
  - `int`
  - `10`
  - Maximum number of suggestions
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[tuple['Page', float, list[str]]]` - List of (target_page, score, reasons) tuples




---


