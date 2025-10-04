---
title: "rendering.template_engine"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_engine.py"
---

# rendering.template_engine

Template engine using Jinja2.

**Source:** `../../bengal/rendering/template_engine.py`

---

## Classes

### TemplateEngine


Template engine for rendering pages with Jinja2 templates.




**Methods:**

#### __init__

```python
def __init__(self, site: Any) -> None
```

Initialize the template engine.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance

**Returns:** `None`






---
#### render

```python
def render(self, template_name: str, context: Dict[str, Any]) -> str
```

Render a template with the given context.

**Parameters:**

- **self**
- **template_name** (`str`) - Name of the template file
- **context** (`Dict[str, Any]`) - Template context variables

**Returns:** `str` - Rendered HTML






---
#### render_string

```python
def render_string(self, template_string: str, context: Dict[str, Any]) -> str
```

Render a template string with the given context.

**Parameters:**

- **self**
- **template_string** (`str`) - Template content as string
- **context** (`Dict[str, Any]`) - Template context variables

**Returns:** `str` - Rendered HTML






---


