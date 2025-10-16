
---
title: "utils.metadata"
type: python-module
source_file: "bengal/utils/metadata.py"
css_class: api-content
description: "Python module documentation"
---

# utils.metadata

*No module description provided.*

---


## Functions

### `build_template_metadata`
```python
def build_template_metadata(site) -> dict[str, Any]
```

Build a curated, privacy-aware metadata dictionary for templates/JS.

Exposure levels (via config['expose_metadata']):
  - minimal: engine only
  - standard: + theme, build timestamp, i18n basics
  - extended: + rendering details (markdown/highlighter versions)



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
* - `site`
  - -
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---
