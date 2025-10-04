---
title: "rendering.renderer"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/renderer.py"
---

# rendering.renderer

Renderer for converting pages to final HTML output.

**Source:** `../../bengal/rendering/renderer.py`

---

## Classes

### Renderer


Renders pages using templates.




**Methods:**

#### __init__

```python
def __init__(self, template_engine: Any, build_stats: Any = None) -> None
```

Initialize the renderer.

**Parameters:**

- **self**
- **template_engine** (`Any`) - Template engine instance
- **build_stats** (`Any`) = `None` - Optional BuildStats object for error collection

**Returns:** `None`






---
#### render_content

```python
def render_content(self, content: str) -> str
```

Render raw content (already parsed HTML).

Automatically strips the first H1 tag to avoid duplication with
the template-rendered title.

**Parameters:**

- **self**
- **content** (`str`) - Parsed HTML content

**Returns:** `str` - Content with first H1 removed






---
#### render_page

```python
def render_page(self, page: Page, content: Optional[str] = None) -> str
```

Render a complete page with template.

**Parameters:**

- **self**
- **page** (`Page`) - Page to render
- **content** (`Optional[str]`) = `None` - Optional pre-rendered content (uses page.parsed_ast if not provided)

**Returns:** `str` - Fully rendered HTML page






---


