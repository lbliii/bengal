
---
title: "graph.pagerank"
type: python-module
source_file: "bengal/cli/commands/graph/pagerank.py"
css_class: api-content
description: "PageRank analysis command for identifying important pages."
---

# graph.pagerank

PageRank analysis command for identifying important pages.

---


## Functions

### `pagerank`
```python
def pagerank(top_n: int, damping: float, format: str, config: str, source: str) -> None
```

🏆 Analyze page importance using PageRank algorithm.

Computes PageRank scores for all pages based on their link structure.
Pages that are linked to by many important pages receive high scores.

Use PageRank to:
- Identify your most important content
- Prioritize content updates
- Guide navigation and sitemap design
- Find underlinked valuable content



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
* - `damping`
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
# Show top 20 most important pages
```


---
