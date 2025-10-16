
---
title: "analysis.page_rank"
type: python-module
source_file: "bengal/analysis/page_rank.py"
css_class: api-content
description: "PageRank implementation for Bengal SSG.  Computes page importance scores using the iterative power method. Takes advantage of hashable pages for efficient graph operations.  The PageRank algorithm ..."
---

# analysis.page_rank

PageRank implementation for Bengal SSG.

Computes page importance scores using the iterative power method.
Takes advantage of hashable pages for efficient graph operations.

The PageRank algorithm assigns importance scores based on:
- Number of incoming links (popularity)
- Importance of pages linking to it (authority)
- Damping factor for random navigation (user behavior)

References:
    - Brin, S., & Page, L. (1998). The anatomy of a large-scale hypertextual
      web search engine. Computer networks and ISDN systems.

---

## Classes

### `PageRankResults`


Results from PageRank computation.

Contains importance scores for all pages based on the link structure.
Pages linked to by many important pages receive high scores.

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
* - `scores`
  - `dict['Page', float]`
  - Map of pages to PageRank scores (normalized, sum to 1.0)
* - `iterations`
  - `int`
  - Number of iterations until convergence
* - `converged`
  - `bool`
  - Whether the algorithm converged within max_iterations
* - `damping_factor`
  - `float`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `get_top_pages`
```python
def get_top_pages(self, limit: int = 20) -> list[tuple['Page', float]]
```

Get top-ranked pages.



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




---
#### `get_pages_above_percentile`
```python
def get_pages_above_percentile(self, percentile: int) -> set['Page']
```

Get pages above a certain percentile.



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
* - `percentile`
  - `int`
  - -
  - Percentile threshold (0-100)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set['Page']` - Set of pages above the threshold




---
#### `get_score`
```python
def get_score(self, page: 'Page') -> float
```

Get PageRank score for a specific page.



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

`float`




---

### `PageRankCalculator`


Compute PageRank scores for pages in a site graph.

PageRank is a link analysis algorithm that assigns numerical weights
to pages based on their link structure. Pages that are linked to by
many important pages receive high scores.

The algorithm uses an iterative approach:
1. Initialize all pages with equal probability (1/N)
2. Iteratively update scores based on incoming links
3. Continue until convergence or max iterations




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, graph: 'KnowledgeGraph', damping: float = 0.85, max_iterations: int = 100, convergence_threshold: float = 1e-06)
```

Initialize PageRank calculator.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 5 parameters (click to expand)
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
* - `damping`
  - `float`
  - `0.85`
  - Probability of following links vs random jump (0-1) Default 0.85 means 85% follow links, 15% random jump
* - `max_iterations`
  - `int`
  - `100`
  - Maximum iterations before stopping
* - `convergence_threshold`
  - `float`
  - `1e-06`
  - Stop when max score change < this value
:::

::::




---
#### `compute`
```python
def compute(self, seed_pages: set['Page'] | None = None, personalized: bool = False) -> PageRankResults
```

Compute PageRank scores for all pages.



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
* - `seed_pages`
  - `set['Page'] | None`
  - `None`
  - Optional set of pages for personalized PageRank Random jumps go only to these pages
* - `personalized`
  - `bool`
  - `False`
  - If True, use personalized PageRank
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PageRankResults` - PageRankResults with scores and metadata




---
#### `compute_personalized`
```python
def compute_personalized(self, seed_pages: set['Page']) -> PageRankResults
```

Compute personalized PageRank from seed pages.

Personalized PageRank biases random jumps toward seed pages,
useful for finding pages related to a specific topic.



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
* - `seed_pages`
  - `set['Page']`
  - -
  - Set of pages to bias toward
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PageRankResults` - PageRankResults with personalized scores




---


## Functions

### `analyze_page_importance`
```python
def analyze_page_importance(graph: 'KnowledgeGraph', damping: float = 0.85, top_n: int = 20) -> list[tuple['Page', float]]
```

Convenience function to analyze page importance.



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
* - `damping`
  - `float`
  - `0.85`
  - Damping factor (default 0.85)
* - `top_n`
  - `int`
  - `20`
  - Number of top pages to return
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple['Page', float]]` - List of (page, score) tuples for top N pages




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> top_pages = analyze_page_importance(graph, top_n=10)
    >>> for page, score in top_pages:
    ...     print(f"{page.title}: {score:.4f}")
```


---
