
---
title: "postprocess.rss"
type: python-module
source_file: "bengal/postprocess/rss.py"
css_class: api-content
description: "RSS feed generation."
---

# postprocess.rss

RSS feed generation.

---

## Classes

### `RSSGenerator`


Generates RSS feed for the site.

Creates an rss.xml file with the 20 most recent pages that have dates,
enabling readers to subscribe to site updates via RSS readers.

Features:
- Includes title, link, description for each item
- Sorted by date (newest first)
- Limited to 20 most recent items
- RFC 822 date formatting




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any) -> None
```

Initialize RSS generator.



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
* - `site`
  - `Any`
  - -
  - Site instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate`
```python
def generate(self) -> None
```

Generate and write rss.xml to output directory.

Filters pages with dates, sorts by date (newest first), limits to 20 items,
and writes RSS feed atomically to prevent corruption.



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

`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`Exception`**: If RSS generation or file writing fails



---
