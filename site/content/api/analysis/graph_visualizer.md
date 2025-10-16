
---
title: "analysis.graph_visualizer"
type: python-module
source_file: "bengal/analysis/graph_visualizer.py"
css_class: api-content
description: "Graph Visualization Generator for Bengal SSG.  Generates interactive D3.js visualizations of the site's knowledge graph. Inspired by Obsidian's graph view."
---

# analysis.graph_visualizer

Graph Visualization Generator for Bengal SSG.

Generates interactive D3.js visualizations of the site's knowledge graph.
Inspired by Obsidian's graph view.

---

## Classes

### `GraphNode`


Node in the graph visualization.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 10 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `id`
  - `str`
  - Unique identifier for the node
* - `label`
  - `str`
  - Display label (page title)
* - `url`
  - `str`
  - URL to the page
* - `type`
  - `str`
  - Page type (page, index, generated, etc.)
* - `tags`
  - `list[str]`
  - List of tags
* - `incoming_refs`
  - `int`
  - Number of incoming references
* - `outgoing_refs`
  - `int`
  - Number of outgoing references
* - `connectivity`
  - `int`
  - Total connectivity score
* - `size`
  - `int`
  - Visual size (based on connectivity)
* - `color`
  - `str`
  - Node color (based on type or connectivity)
:::

::::



### `GraphEdge`


Edge in the graph visualization.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `source`
  - `str`
  - Source node ID
* - `target`
  - `str`
  - Target node ID
* - `weight`
  - `int`
  - Edge weight (link strength)
:::

::::



### `GraphVisualizer`


Generate interactive D3.js visualizations of knowledge graphs.

Creates standalone HTML files with:
- Force-directed graph layout
- Interactive node exploration
- Search and filtering
- Responsive design
- Customizable styling




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site', graph: 'KnowledgeGraph')
```

Initialize graph visualizer.



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
* - `site`
  - `'Site'`
  - -
  - Site instance
* - `graph`
  - `'KnowledgeGraph'`
  - -
  - Built KnowledgeGraph instance
:::

::::




---
#### `generate_graph_data`
```python
def generate_graph_data(self) -> dict[str, Any]
```

Generate D3.js-compatible graph data.



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

`dict[str, Any]` - Dictionary with 'nodes' and 'edges' arrays




---
#### `generate_html`
```python
def generate_html(self, title: str | None = None) -> str
```

Generate complete standalone HTML visualization.



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
* - `title`
  - `str | None`
  - `None`
  - Page title (defaults to site title)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Complete HTML document as string




---


