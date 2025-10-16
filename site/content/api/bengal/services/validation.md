
---
title: "bengal.services.validation"
type: python-module
source_file: "bengal/services/validation.py"
css_class: api-content
description: "Python module documentation"
---

# bengal.services.validation

*No module description provided.*

---

## Classes

### `TemplateValidationService`

**Inherits from:** `Protocol`
*No class description provided.*




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: Any) -> int
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
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int`




---

### `DefaultTemplateValidationService`


Adapter around bengal.rendering.validator with current TemplateEngine.

Keeps CLI decoupled from concrete rendering internals while preserving behavior.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 1 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `strict`
  - `bool`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: Any) -> int
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
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int`




---
