
---
title: "graph.bridges"
type: python-module
source_file: "bengal/cli/commands/graph/bridges.py"
css_class: api-content
description: "Bridge pages and navigation bottleneck analysis command."
---

# graph.bridges

Bridge pages and navigation bottleneck analysis command.

---


## Functions

### `bridges`
```python
def bridges(top_n: int, metric: str, format: str, config: str, source: str) -> None
```

🌉 Identify bridge pages and navigation bottlenecks.

Analyzes navigation paths to find:
- Bridge pages (high betweenness): Pages that connect different parts of the site
- Accessible pages (high closeness): Pages easy to reach from anywhere
- Navigation bottlenecks: Critical pages for site navigation

Use path analysis to:
- Optimize navigation structure
- Identify critical pages
- Improve content discoverability
- Find navigation gaps



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
* - `metric`
  - `str`
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
# Show top 20 bridge pages
```


---
