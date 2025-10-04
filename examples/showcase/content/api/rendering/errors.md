---
title: "rendering.errors"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/errors.py"
---

# rendering.errors

Rich template error objects with line numbers, context, and suggestions.

**Source:** `../../bengal/rendering/errors.py`

---

## Classes

### TemplateErrorContext


Context around an error in a template.

::: info
This is a dataclass.
:::

**Attributes:**

- **template_name** (`str`)- **line_number** (`Optional[int]`)- **column** (`Optional[int]`)- **source_line** (`Optional[str]`)- **surrounding_lines** (`List[Tuple[int, str]]`)- **template_path** (`Optional[Path]`)


### InclusionChain


Represents the template inclusion chain.

::: info
This is a dataclass.
:::

**Attributes:**

- **entries** (`List[Tuple[str, Optional[int]]]`)

**Methods:**

#### __str__

```python
def __str__(self) -> str
```

Format as readable chain.

**Parameters:**

- **self**

**Returns:** `str`






---

### TemplateRenderError


Rich template error with all debugging information.

This replaces the simple string error messages with structured data
that can be displayed beautifully and used for IDE integration.

::: info
This is a dataclass.
:::

**Attributes:**

- **error_type** (`str`)- **message** (`str`)- **template_context** (`TemplateErrorContext`)- **inclusion_chain** (`Optional[InclusionChain]`)- **page_source** (`Optional[Path]`)- **suggestion** (`Optional[str]`)- **available_alternatives** (`List[str]`)

**Methods:**

#### from_jinja2_error

```python
def from_jinja2_error(cls, error: Exception, template_name: str, page_source: Optional[Path], template_engine: Any) -> 'TemplateRenderError'
```

Extract rich error information from Jinja2 exception.

**Parameters:**

- **cls**
- **error** (`Exception`) - Jinja2 exception
- **template_name** (`str`) - Template being rendered
- **page_source** (`Optional[Path]`) - Source content file (if applicable)
- **template_engine** (`Any`) - Template engine instance

**Returns:** `'TemplateRenderError'` - Rich error object






---


## Functions

### display_template_error

```python
def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None
```

Display a rich template error in the terminal.

**Parameters:**

- **error** (`TemplateRenderError`) - Rich error object
- **use_color** (`bool`) = `True` - Whether to use terminal colors

**Returns:** `None`





---
