---
title: "rendering.validator"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/validator.py"
---

# rendering.validator

Template validation before rendering.

**Source:** `../../bengal/rendering/validator.py`

---

## Classes

### TemplateValidator


Validates templates for syntax errors and missing dependencies.




**Methods:**

#### __init__

```python
def __init__(self, template_engine: Any)
```

Initialize validator.

**Parameters:**

- **self**
- **template_engine** (`Any`) - TemplateEngine instance







---
#### validate_all

```python
def validate_all(self) -> List[Any]
```

Validate all templates in the theme.

**Parameters:**

- **self**

**Returns:** `List[Any]` - List of errors found






---


## Functions

### validate_templates

```python
def validate_templates(template_engine: Any) -> int
```

Validate all templates and display results.

**Parameters:**

- **template_engine** (`Any`) - TemplateEngine instance

**Returns:** `int` - Number of errors found





---
