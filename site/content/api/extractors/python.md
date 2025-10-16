
---
title: "extractors.python"
type: python-module
source_file: "bengal/autodoc/extractors/python.py"
css_class: api-content
description: "Python API documentation extractor.  Extracts documentation from Python source files via AST parsing. No imports required - fast and reliable."
---

# extractors.python

Python API documentation extractor.

Extracts documentation from Python source files via AST parsing.
No imports required - fast and reliable.

---

## Classes

### `PythonExtractor`

**Inherits from:** `Extractor`
Extract Python API documentation via AST parsing.

Features:
- No imports (AST-only) - fast and reliable
- Extracts modules, classes, functions, methods
- Type hint support
- Docstring extraction
- Signature building

Performance:
- ~0.1-0.5s per file
- No dependencies loaded
- No side effects




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, exclude_patterns: list[str] | None = None)
```

Initialize extractor.



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
* - `exclude_patterns`
  - `list[str] | None`
  - `None`
  - Glob patterns to exclude (e.g., "*/tests/*")
:::

::::




---
#### `extract`
```python
def extract(self, source: Path) -> list[DocElement]
```

Extract documentation from Python source.



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
* - `source`
  - `Path`
  - -
  - Directory or file path
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[DocElement]` - List of DocElement objects




---
#### `get_template_dir`
```python
def get_template_dir(self) -> str
```

Get template directory name.



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

`str`




---
#### `get_output_path`
```python
def get_output_path(self, element: DocElement) -> Path
```

Get output path for element.



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
* - `element`
  - `DocElement`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal.core.site (module) → bengal/core/site.md
```


---
