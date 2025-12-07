
---
title: "graph_analysis"
type: "python-module"
source_file: "bengal/analysis/graph_analysis.py"
line_number: 1
description: "Graph analysis module for Bengal SSG. Provides structural analysis of knowledge graphs including connectivity scoring, hub/leaf detection, and page layering."
---

# graph_analysis
**Type:** Module
**Source:** [View source](bengal/analysis/graph_analysis.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[analysis](/api/bengal/analysis/) ›graph_analysis

Graph analysis module for Bengal SSG.

Provides structural analysis of knowledge graphs including
connectivity scoring, hub/leaf detection, and page layering.

## Classes




### `GraphAnalyzer`


Analyzes knowledge graph structure for page connectivity insights.

Provides methods for:
- Connectivity scoring (incoming + outgoing refs)
- Hub detection (highly connected pages)
- Leaf detection (low connectivity pages)
- Orphan detection (no connections)
- Layer partitioning (for hub-first streaming builds)









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, graph: KnowledgeGraph) -> None
```


Initialize the graph analyzer.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `graph` | `KnowledgeGraph` | - | Knowledge graph to analyze (must be built) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`




#### `get_connectivity`

:::{div} api-badge-group
:::

```python
def get_connectivity(self, page: Page) -> PageConnectivity
```


Get connectivity information for a specific page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to analyze |







:::{rubric} Returns
:class: rubric-returns
:::


`PageConnectivity` - PageConnectivity with detailed metrics
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet




#### `get_connectivity_score`

:::{div} api-badge-group
:::

```python
def get_connectivity_score(self, page: Page) -> int
```


Get total connectivity score for a page.

Connectivity = incoming_refs + outgoing_refs


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to analyze |







:::{rubric} Returns
:class: rubric-returns
:::


`int` - Connectivity score (higher = more connected)
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet




#### `get_hubs`

:::{div} api-badge-group
:::

```python
def get_hubs(self, threshold: int | None = None) -> list[Page]
```


Get hub pages (highly connected pages).

Hubs are pages with many incoming references. These are typically:
- Index pages
- Popular articles
- Core documentation


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `threshold` | `int \| None` | - | Minimum incoming refs (defaults to graph.hub_threshold) |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]` - List of hub pages sorted by incoming references (descending)
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet




#### `get_leaves`

:::{div} api-badge-group
:::

```python
def get_leaves(self, threshold: int | None = None) -> list[Page]
```


Get leaf pages (low connectivity pages).

Leaves are pages with few connections. These are typically:
- One-off blog posts
- Changelog entries
- Niche content


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `threshold` | `int \| None` | - | Maximum connectivity (defaults to graph.leaf_threshold) |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]` - List of leaf pages sorted by connectivity (ascending)
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet




#### `get_orphans`

:::{div} api-badge-group
:::

```python
def get_orphans(self) -> list[Page]
```


Get orphaned pages (no connections at all).

Orphans are pages with no incoming or outgoing references. These might be:
- Forgotten content
- Draft pages
- Pages that should be linked from navigation



:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]` - List of orphaned pages sorted by slug
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet




#### `get_layers`

:::{div} api-badge-group
:::

```python
def get_layers(self) -> tuple[list[Page], list[Page], list[Page]]
```


Partition pages into three layers by connectivity.

Layers enable hub-first streaming builds:
- Layer 0 (Hubs): High connectivity, process first, keep in memory
- Layer 1 (Mid-tier): Medium connectivity, batch processing
- Layer 2 (Leaves): Low connectivity, stream and release



:::{rubric} Returns
:class: rubric-returns
:::


`tuple[list[Page], list[Page], list[Page]]` - Tuple of (hubs, mid_tier, leaves)
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If graph hasn't been built yet



---
*Generated by Bengal autodoc from `bengal/analysis/graph_analysis.py`*

