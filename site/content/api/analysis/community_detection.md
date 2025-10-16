
---
title: "analysis.community_detection"
type: python-module
source_file: "bengal/analysis/community_detection.py"
css_class: api-content
description: "Community Detection for Bengal SSG.  Implements the Louvain method for discovering topical clusters in content. The algorithm optimizes modularity to find natural groupings of pages.  The Louvain m..."
---

# analysis.community_detection

Community Detection for Bengal SSG.

Implements the Louvain method for discovering topical clusters in content.
The algorithm optimizes modularity to find natural groupings of pages.

The Louvain method works in two phases:
1. Local optimization: Move nodes to communities that maximize modularity gain
2. Aggregation: Treat each community as a single node and repeat

References:
    - Blondel, V. D., et al. (2008). Fast unfolding of communities in large networks.
      Journal of Statistical Mechanics: Theory and Experiment.

---

## Classes

### `Community`


A community of related pages discovered through link structure.

Represents a group of pages that are densely connected to each other
and share similar topics or themes. Useful for understanding content
organization and identifying topic clusters.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 4 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `id`
  - `int`
  - Unique community identifier
* - `pages`
  - `set['Page']`
  - Set of pages belonging to this community
* - `size`
  - -
  - Number of pages in the community
* - `density`
  - -
  - Internal connection density (0.0-1.0)
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `size` @property

```python
@property
def size(self) -> int
```

Number of pages in this community.

:::{rubric} Methods
:class: rubric-methods
:::
#### `size`
```python
def size(self) -> int
```

Number of pages in this community.



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

`int`




---
#### `get_top_pages_by_degree`
```python
def get_top_pages_by_degree(self, limit: int = 5) -> list['Page']
```

Get most connected pages in this community.



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
  - `5`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---

### `CommunityDetectionResults`


Results from community detection analysis.

Contains discovered communities and quality metrics. Communities
represent natural groupings of related pages based on link structure.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 4 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `communities`
  - `list[Community]`
  - List of detected communities
* - `modularity`
  - `float`
  - Modularity score (quality metric, -1.0 to 1.0, higher is better)
* - `iterations`
  - `int`
  - -
* - `num_communities`
  - -
  - Total number of communities detected
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `get_community_for_page`
```python
def get_community_for_page(self, page: 'Page') -> Community | None
```

Find which community a page belongs to.



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
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Community | None`




---
#### `get_largest_communities`
```python
def get_largest_communities(self, limit: int = 10) -> list[Community]
```

Get largest communities by page count.



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
  - `10`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Community]`




---
#### `get_communities_above_size`
```python
def get_communities_above_size(self, min_size: int) -> list[Community]
```

Get communities with at least min_size pages.



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
* - `min_size`
  - `int`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Community]`




---

### `LouvainCommunityDetector`


Detect communities using the Louvain method.

The Louvain algorithm is a greedy optimization method that attempts to
optimize the modularity of a partition of the network. It runs in two phases:

1. Modularity Optimization: Each node is moved to the community that yields
   the largest increase in modularity.

2. Community Aggregation: A new network is built where nodes are communities
   and edges represent connections between communities.

These phases are repeated until no further improvement is possible.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, graph: 'KnowledgeGraph', resolution: float = 1.0, random_seed: int | None = None)
```

Initialize Louvain community detector.



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
* - `graph`
  - `'KnowledgeGraph'`
  - -
  - KnowledgeGraph with page connections
* - `resolution`
  - `float`
  - `1.0`
  - Resolution parameter (higher = more communities)
* - `random_seed`
  - `int | None`
  - `None`
  - Random seed for reproducibility
:::

::::




---
#### `detect`
```python
def detect(self) -> CommunityDetectionResults
```

Detect communities using Louvain method.



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

`CommunityDetectionResults` - CommunityDetectionResults with discovered communities




---


## Functions

### `detect_communities`
```python
def detect_communities(graph: 'KnowledgeGraph', resolution: float = 1.0, random_seed: int | None = None) -> CommunityDetectionResults
```

Convenience function to detect communities.



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
* - `graph`
  - `'KnowledgeGraph'`
  - -
  - KnowledgeGraph with page connections
* - `resolution`
  - `float`
  - `1.0`
  - Resolution parameter (higher = more communities)
* - `random_seed`
  - `int | None`
  - `None`
  - Random seed for reproducibility
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`CommunityDetectionResults` - CommunityDetectionResults with discovered communities




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> results = detect_communities(graph)
    >>> print(f"Found {len(results.communities)} communities")
```


---
