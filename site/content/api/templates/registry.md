
---
title: "templates.registry"
type: python-module
source_file: "bengal/cli/templates/registry.py"
css_class: api-content
description: "Template registry and discovery."
---

# templates.registry

Template registry and discovery.

---

## Classes

### `TemplateRegistry`


Registry for discovering and managing site templates.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

*No description provided.*



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




---
#### `get`
```python
def get(self, template_id: str) -> SiteTemplate | None
```

Get a template by ID.



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
* - `template_id`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`SiteTemplate | None`




---
#### `list`
```python
def list(self) -> list[tuple[str, str]]
```

List all templates (id, description).



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

`list[tuple[str, str]]`




---
#### `exists`
```python
def exists(self, template_id: str) -> bool
```

Check if a template exists.



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
* - `template_id`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---


## Functions

### `get_template`
```python
def get_template(template_id: str) -> SiteTemplate | None
```

Get a template by ID.



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
* - `template_id`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`SiteTemplate | None`




---
### `list_templates`
```python
def list_templates() -> list[tuple[str, str]]
```

List all available templates.



:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple[str, str]]`




---
### `register_template`
```python
def register_template(template: SiteTemplate) -> None
```

Register a custom template.



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
* - `template`
  - `SiteTemplate`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
