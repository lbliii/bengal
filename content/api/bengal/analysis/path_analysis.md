
---
title: "path_analysis"
type: "python-module"
source_file: "bengal/bengal/analysis/path_analysis.py"
line_number: 1
description: "Path Analysis for Bengal SSG. Implements algorithms for understanding navigation patterns and page accessibility: - Shortest paths between pages (BFS-based) - Betweenness centrality (identifies bridge..."
---

# path_analysis
**Type:** Module
**Source:** [View source](bengal/bengal/analysis/path_analysis.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[analysis](/api/bengal/analysis/) ›path_analysis

Path Analysis for Bengal SSG.

Implements algorithms for understanding navigation patterns and page accessibility:
- Shortest paths between pages (BFS-based)
- Betweenness centrality (identifies bridge pages)
- Closeness centrality (measures accessibility)

These metrics help optimize navigation structure and identify critical pages.

References:
    - Brandes, U. (2001). A faster algorithm for betweenness centrality.
      Journal of Mathematical Sociology.

## Classes




### `PathAnalysisResults`


Results from path analysis and centrality computations.

Contains centrality metrics that identify important pages in the
site's link structure. High betweenness indicates bridge pages,
high closeness indicates easily accessible pages.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `betweenness_centrality` | - | Map of pages to betweenness scores (0.0-1.0) |
| `closeness_centrality` | - | Map of pages to closeness scores (0.0-1.0) |
| `avg_path_length` | - | Average shortest path length between all page pairs |
| `diameter` | - | Network diameter (longest shortest path) |







## Methods



#### `get_top_bridges`
```python
def get_top_bridges(self, limit: int = 20) -> list[tuple[Page, float]]
```


Get pages with highest betweenness centrality (bridge pages).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `limit` | `int` | `20` | Number of pages to return |







**Returns**


`list[tuple[Page, float]]` - List of (page, centrality) tuples sorted by centrality descending



#### `get_most_accessible`
```python
def get_most_accessible(self, limit: int = 20) -> list[tuple[Page, float]]
```


Get most accessible pages (highest closeness centrality).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `limit` | `int` | `20` | Number of pages to return |







**Returns**


`list[tuple[Page, float]]` - List of (page, centrality) tuples sorted by centrality descending



#### `get_betweenness`
```python
def get_betweenness(self, page: Page) -> float
```


Get betweenness centrality for specific page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | *No description provided.* |







**Returns**


`float`



#### `get_closeness`
```python
def get_closeness(self, page: Page) -> float
```


Get closeness centrality for specific page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | *No description provided.* |







**Returns**


`float`




### `PathAnalyzer`


Analyze navigation paths and page accessibility.

Computes centrality metrics to identify:
- Bridge pages (high betweenness): Pages that connect different parts of the site
- Accessible pages (high closeness): Pages that are easy to reach from anywhere
- Navigation bottlenecks: Critical pages for site navigation

Uses Brandes' algorithm for efficient betweenness centrality computation.









## Methods



#### `__init__`
```python
def __init__(self, graph: KnowledgeGraph)
```


Initialize path analyzer.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `graph` | `KnowledgeGraph` | - | KnowledgeGraph with page connections |








#### `find_shortest_path`
```python
def find_shortest_path(self, source: Page, target: Page) -> list[Page] | None
```


Find shortest path between two pages using BFS.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `Page` | - | Starting page |
| `target` | `Page` | - | Destination page |







**Returns**


`list[Page] | None` - List of pages representing the path, or None if no path exists
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> path = analyzer.find_shortest_path(page_a, page_b)
    >>> if path:
    ...     print(f"Path length: {len(path) - 1}")
```




#### `analyze`
```python
def analyze(self) -> PathAnalysisResults
```


Compute path-based centrality metrics.

Computes:
- Betweenness centrality: How often a page appears on shortest paths
- Closeness centrality: How close a page is to all other pages
- Network diameter: Longest shortest path
- Average path length



**Returns**


`PathAnalysisResults` - PathAnalysisResults with all metrics






#### `find_all_paths`
```python
def find_all_paths(self, source: Page, target: Page, max_length: int = 10) -> list[list[Page]]
```


Find all simple paths between two pages (up to max_length).

Warning: Can be expensive for highly connected graphs.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `Page` | - | Starting page |
| `target` | `Page` | - | Destination page |
| `max_length` | `int` | `10` | Maximum path length to search |







**Returns**


`list[list[Page]]` - List of paths (each path is a list of pages)

## Functions



### `analyze_paths`


```python
def analyze_paths(graph: KnowledgeGraph) -> PathAnalysisResults
```



Convenience function for path analysis.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `graph` | `KnowledgeGraph` | - | KnowledgeGraph with page connections |







**Returns**


`PathAnalysisResults` - PathAnalysisResults with centrality metrics
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = analyze_paths(graph)
    >>> bridges = results.get_top_bridges(10)
```



---
*Generated by Bengal autodoc from `bengal/bengal/analysis/path_analysis.py`*
