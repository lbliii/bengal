
---
title: "parsers.base"
type: python-module
source_file: "bengal/rendering/parsers/base.py"
css_class: api-content
description: "Base class for Markdown parsers."
---

# parsers.base

Base class for Markdown parsers.

---

## Classes

### `BaseMarkdownParser`

**Inherits from:** `ABC`
Abstract base class for Markdown parsers.
All parser implementations must implement this interface.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, content: str, metadata: dict[str, Any]) -> str
```

Parse Markdown content into HTML.



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
* - `content`
  - `str`
  - -
  - Raw Markdown content
* - `metadata`
  - `dict[str, Any]`
  - -
  - Page metadata
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Parsed HTML content




---
#### `parse_with_toc`
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.



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
* - `content`
  - `str`
  - -
  - Raw Markdown content
* - `metadata`
  - `dict[str, Any]`
  - -
  - Page metadata
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[str, str]` - Tuple of (parsed HTML, table of contents HTML)




---


