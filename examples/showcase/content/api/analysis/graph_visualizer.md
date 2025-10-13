
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

Attributes:
    id: Unique identifier for the node
    label: Display label (page title)
    url: URL to the page
    type: Page type (page, index, generated, etc.)
    tags: List of tags
    incoming_refs: Number of incoming references
    outgoing_refs: Number of outgoing references
    connectivity: Total connectivity score
    size: Visual size (based on connectivity)
    color: Node color (based on type or connectivity)

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`id`** (`str`)- **`label`** (`str`)- **`url`** (`str`)- **`type`** (`str`)- **`tags`** (`list[str]`)- **`incoming_refs`** (`int`)- **`outgoing_refs`** (`int`)- **`connectivity`** (`int`)- **`size`** (`int`)- **`color`** (`str`)



### `GraphEdge`


Edge in the graph visualization.

Attributes:
    source: Source node ID
    target: Target node ID
    weight: Edge weight (link strength)

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`source`** (`str`)- **`target`** (`str`)- **`weight`** (`int`)



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
- **`self`**
- **`site`** (`'Site'`) - Site instance
- **`graph`** (`'KnowledgeGraph'`) - Built KnowledgeGraph instance





---
#### `generate_graph_data`
```python
def generate_graph_data(self) -> dict[str, Any]
```

Generate D3.js-compatible graph data.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

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
- **`self`**
- **`title`** (`str | None`) = `None` - Page title (defaults to site title)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Complete HTML document as string




---
