
---
title: "autodoc.base"
type: python-module
source_file: "bengal/autodoc/base.py"
css_class: api-content
description: "Base classes for autodoc system.  Provides common interfaces for all documentation extractors."
---

# autodoc.base

Base classes for autodoc system.

Provides common interfaces for all documentation extractors.

---

## Classes

### `DocElement`


Represents a documented element (function, class, endpoint, command, etc.).

This is the unified data model used by all extractors.
Each extractor converts its specific domain into this common format.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 11 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `name`
  - `str`
  - Element name (e.g., 'build', 'Site', 'GET /users')
* - `qualified_name`
  - `str`
  - Full path (e.g., 'bengal.core.site.Site.build')
* - `description`
  - `str`
  - Main description/docstring
* - `element_type`
  - `str`
  - Type of element ('function', 'class', 'endpoint', 'command', etc.)
* - `source_file`
  - `Path | None`
  - Source file path (if applicable)
* - `line_number`
  - `int | None`
  - Line number in source (if applicable)
* - `metadata`
  - `dict[str, Any]`
  - Type-specific data (signatures, parameters, etc.)
* - `children`
  - `list['DocElement']`
  - Nested elements (methods, subcommands, etc.)
* - `examples`
  - `list[str]`
  - Usage examples
* - `see_also`
  - `list[str]`
  - Cross-references to related elements
* - `deprecated`
  - `str | None`
  - Deprecation notice (if any)
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

Convert to dictionary for caching/serialization.



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

`dict[str, Any]`




---
#### `from_dict` @classmethod
```python
def from_dict(cls, data: dict[str, Any]) -> 'DocElement'
```

Create from dictionary (for cache loading).



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
* - `cls`
  - -
  - -
  - -
* - `data`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'DocElement'`




---

### `Extractor`

**Inherits from:** `ABC`
Base class for all documentation extractors.

Each documentation type (Python, OpenAPI, CLI) implements this interface.
This enables a unified API for generating documentation from different sources.




:::{rubric} Methods
:class: rubric-methods
:::
#### `extract`
```python
def extract(self, source: Any) -> list[DocElement]
```

Extract documentation elements from source.



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
  - `Any`
  - -
  - Source to extract from (Path for files, dict for specs, etc.)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[DocElement]` - List of DocElement objects representing the documentation structure


```{note}
This should be fast and not have side effects (no imports, no network calls)
```




---
#### `get_template_dir`
```python
def get_template_dir(self) -> str
```

Get template directory name for this extractor.



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

`str` - Directory name (e.g., 'python', 'openapi', 'cli')




:::{rubric} Examples
:class: rubric-examples
:::
```python
Templates will be loaded from:
```


---
#### `get_output_path`
```python
def get_output_path(self, element: DocElement) -> Path
```

Determine output path for an element.



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
  - Element to generate path for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Relative path for the generated markdown file




:::{rubric} Examples
:class: rubric-examples
:::
```python
For Python: bengal.core.site.Site → bengal/core/site.md
```


---


