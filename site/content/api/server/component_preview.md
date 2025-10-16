
---
title: "server.component_preview"
type: python-module
source_file: "bengal/server/component_preview.py"
css_class: api-content
description: "Component preview server utilities.  Discovers component manifests and renders template partials with demo contexts.  Manifest format (YAML):  name: "Card" template: "partials/card.html" variants: ..."
---

# server.component_preview

Component preview server utilities.

Discovers component manifests and renders template partials with demo contexts.

Manifest format (YAML):

name: "Card"
template: "partials/card.html"
variants:
  - id: "default"
    name: "Default"
    context:
      title: "Hello"

---

## Classes

### `ComponentPreviewServer`


*No class description provided.*




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Site) -> None
```

*No description provided.*



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
  - `Site`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `discover_components`
```python
def discover_components(self) -> list[dict[str, Any]]
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

:::{rubric} Returns
:class: rubric-returns
:::

`list[dict[str, Any]]`




---
#### `render_component`
```python
def render_component(self, template_rel: str, context: dict[str, Any]) -> str
```

*No description provided.*



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
* - `template_rel`
  - `str`
  - -
  - -
* - `context`
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
#### `list_page`
```python
def list_page(self, base_path: str = '/__bengal_components__/') -> str
```

*No description provided.*



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
* - `base_path`
  - `str`
  - `'/__bengal_components__/'`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `view_page`
```python
def view_page(self, comp_id: str, variant_id: str | None) -> str
```

*No description provided.*



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
* - `comp_id`
  - `str`
  - -
  - -
* - `variant_id`
  - `str | None`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---


## Functions

### `discover_components`
```python
def discover_components(site: Site) -> list[dict[str, Any]]
```

Discover components using a temporary server instance (compat shim).



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
  - `Site`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[dict[str, Any]]`




---
