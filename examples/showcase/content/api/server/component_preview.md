
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
- **`self`**
- **`site`** (`Site`)

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
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[dict[str, Any]]`




---
#### `render_component`
```python
def render_component(self, template_rel: str | None, context: dict[str, Any], macro_ref: str | None = None) -> str
```

Render a component (either include-based template or macro).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_rel`** (`str | None`) - Template path for include-based components (legacy)
- **`context`** (`dict[str, Any]`) - Context variables or macro parameters
- **`macro_ref`** (`str | None`) = `None` - Macro reference like "navigation-components.breadcrumbs" (new)

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
- **`self`**
- **`base_path`** (`str`) = `'/__bengal_components__/'`

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
- **`self`**
- **`comp_id`** (`str`)
- **`variant_id`** (`str | None`)

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
