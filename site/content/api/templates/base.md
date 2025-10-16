
---
title: "templates.base"
type: python-module
source_file: "bengal/cli/templates/base.py"
css_class: api-content
description: "Base classes for site templates."
---

# templates.base

Base classes for site templates.

---

## Classes

### `TemplateFile`


Represents a file to be created from a template.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `relative_path`
  - `str`
  - -
* - `content`
  - `str`
  - -
* - `target_dir`
  - `str`
  - -
:::

::::



### `SiteTemplate`


Base class for site templates.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 6 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `id`
  - `str`
  - -
* - `name`
  - `str`
  - -
* - `description`
  - `str`
  - -
* - `files`
  - `list[TemplateFile]`
  - -
* - `additional_dirs`
  - `list[str]`
  - -
* - `menu_sections`
  - `list[str]`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `get_files`
```python
def get_files(self) -> list[TemplateFile]
```

Get all files for this template.



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

`list[TemplateFile]`




---
#### `get_additional_dirs`
```python
def get_additional_dirs(self) -> list[str]
```

Get additional directories to create.



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

`list[str]`




---
#### `get_menu_sections`
```python
def get_menu_sections(self) -> list[str]
```

Get sections for menu auto-generation.



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

`list[str]`




---

### `TemplateProvider`

**Inherits from:** `Protocol`
Protocol for template providers.




:::{rubric} Methods
:class: rubric-methods
:::
#### `get_template` @classmethod
```python
def get_template(cls) -> SiteTemplate
```

Return the site template.



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
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`SiteTemplate`




---
