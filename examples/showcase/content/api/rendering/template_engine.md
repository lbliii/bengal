
---
title: "rendering.template_engine"
type: python-module
source_file: "bengal/rendering/template_engine.py"
css_class: api-content
description: "Template engine using Jinja2."
---

# rendering.template_engine

Template engine using Jinja2.

---

## Classes

### `TemplateEngine`


Template engine for rendering pages with Jinja2 templates.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any) -> None
```

Initialize the template engine.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`Any`) - Site instance

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `render`
```python
def render(self, template_name: str, context: dict[str, Any]) -> str
```

Render a template with the given context.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_name`** (`str`) - Name of the template file
- **`context`** (`dict[str, Any]`) - Template context variables

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Rendered HTML




---
#### `render_string`
```python
def render_string(self, template_string: str, context: dict[str, Any]) -> str
```

Render a template string with the given context.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_string`** (`str`) - Template content as string
- **`context`** (`dict[str, Any]`) - Template context variables

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Rendered HTML




---
