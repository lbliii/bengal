
---
title: "parsers.python_markdown"
type: python-module
source_file: "bengal/rendering/parsers/python_markdown.py"
css_class: api-content
description: "Python-markdown parser implementation."
---

# parsers.python_markdown

Python-markdown parser implementation.

---

## Classes

### `PythonMarkdownParser`

**Inherits from:** `BaseMarkdownParser`
Parser using python-markdown library.
Full-featured with all extensions.

Performance Note:
    Uses cached Pygments lexers to avoid expensive plugin discovery
    on every code block. This provides 3-10× speedup on sites with
    many code blocks.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self) -> None
```

Initialize the python-markdown parser with extensions.



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




---
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
  - -
* - `metadata`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




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
  - -
* - `metadata`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[str, str]`




---


