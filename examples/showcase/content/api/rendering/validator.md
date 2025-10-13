
---
title: "rendering.validator"
type: python-module
source_file: "bengal/rendering/validator.py"
css_class: api-content
description: "Template validation before rendering."
---

# rendering.validator

Template validation before rendering.

---

## Classes

### `TemplateValidator`


Validates templates for syntax errors and missing dependencies.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, template_engine: Any)
```

Initialize validator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_engine`** (`Any`) - TemplateEngine instance





---
#### `validate_all`
```python
def validate_all(self) -> list[Any]
```

Validate all templates in the theme.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - List of errors found




---


## Functions

### `validate_templates`
```python
def validate_templates(template_engine: Any) -> int
```

Validate all templates and display results.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`template_engine`** (`Any`) - TemplateEngine instance

:::{rubric} Returns
:class: rubric-returns
:::
`int` - Number of errors found




---
