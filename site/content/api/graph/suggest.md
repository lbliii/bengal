
---
title: "graph.suggest"
type: python-module
source_file: "bengal/cli/commands/graph/suggest.py"
css_class: api-content
description: "Smart link suggestion command for improving internal linking."
---

# graph.suggest

Smart link suggestion command for improving internal linking.

---


## Functions

### `suggest`
```python
def suggest(top_n: int, min_score: float, format: str, config: str, source: str) -> None
```

💡 Generate smart link suggestions to improve internal linking.

Analyzes your content to recommend links based on:
- Topic similarity (shared tags/categories)
- Page importance (PageRank scores)
- Navigation value (bridge pages)
- Link gaps (underlinked content)

Use link suggestions to:
- Improve internal linking structure
- Boost SEO through better connectivity
- Increase content discoverability
- Fill navigation gaps



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
* - `top_n`
  - `int`
  - -
  - -
* - `min_score`
  - `float`
  - -
  - -
* - `format`
  - `str`
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
# Show top 50 link suggestions
```


---
