
---
title: "graph.communities"
type: python-module
source_file: "bengal/cli/commands/graph/communities.py"
css_class: api-content
description: "Community detection command for discovering topical clusters."
---

# graph.communities

Community detection command for discovering topical clusters.

---


## Functions

### `communities`
```python
def communities(min_size: int, resolution: float, top_n: int, format: str, seed: int, config: str, source: str) -> None
```

🔍 Discover topical communities in your content.

Uses the Louvain algorithm to find natural clusters of related pages.
Communities represent topic areas or content groups based on link structure.

Use community detection to:
- Discover hidden content structure
- Organize content into logical groups
- Identify topic clusters
- Guide taxonomy creation



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 7 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `min_size`
  - `int`
  - -
  - -
* - `resolution`
  - `float`
  - -
  - -
* - `top_n`
  - `int`
  - -
  - -
* - `format`
  - `str`
  - -
  - -
* - `seed`
  - `int`
  - -
  - -
* - `config`
  - `str`
  - -
  - -
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Show top 10 communities
```


---
