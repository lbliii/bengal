
---
title: "parsers"
type: python-module
source_file: "bengal/rendering/parsers/__init__.py"
css_class: api-content
description: "Content parser for Markdown and other formats.  Supports multiple parser engines: - python-markdown: Full-featured, slower (default) - mistune: Fast, subset of features"
---

# parsers

Content parser for Markdown and other formats.

Supports multiple parser engines:
- python-markdown: Full-featured, slower (default)
- mistune: Fast, subset of features

---


## Functions

### `create_markdown_parser`
```python
def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser
```

Factory function to create a markdown parser instance.



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
* - `engine`
  - `str | None`
  - `None`
  - Parser engine to use ('python-markdown', 'mistune', or None for default)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`BaseMarkdownParser` - Markdown parser instance

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If engine is not supported



---
