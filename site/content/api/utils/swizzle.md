
---
title: "utils.swizzle"
type: python-module
source_file: "bengal/utils/swizzle.py"
css_class: api-content
description: "SwizzleManager - Safe template override management for themes.  Features: - Copy ("swizzle") a theme template/partial into project `templates/` preserving relative path - Track provenance in `.beng..."
---

# utils.swizzle

SwizzleManager - Safe template override management for themes.

Features:
- Copy ("swizzle") a theme template/partial into project `templates/` preserving relative path
- Track provenance in `.bengal/themes/sources.json`
- List swizzled files
- Naive update: if local file is unchanged from its original swizzle, replace with upstream

Note: Three-way merge can be added later; for now we only auto-update when no local edits.

---

## Classes

### `SwizzleRecord`


*No class description provided.*


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
* - `target`
  - `str`
  - -
* - `source`
  - `str`
  - -
* - `theme`
  - `str`
  - -
* - `upstream_checksum`
  - `str`
  - -
* - `local_checksum`
  - `str`
  - -
* - `timestamp`
  - `float`
  - -
:::

::::



### `SwizzleManager`


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
#### `swizzle`
```python
def swizzle(self, template_rel_path: str) -> Path
```

Copy a theme template into project templates/ and record provenance.



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
* - `template_rel_path`
  - `str`
  - -
  - Relative path inside theme templates/ (e.g., 'partials/toc.html')
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to copied file under project templates/




---
#### `list`
```python
def list(self) -> builtins.list[SwizzleRecord]
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

`builtins.list[SwizzleRecord]`




---
#### `list_swizzled`
```python
def list_swizzled(self) -> builtins.list[SwizzleRecord]
```

Alias for list() for backward compatibility.



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

`builtins.list[SwizzleRecord]`




---
#### `update`
```python
def update(self) -> dict[str, int]
```

Attempt to update swizzled files from upstream if local is unchanged.

Returns a summary dict with counts: {updated, skipped_changed, missing_upstream}



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

`dict[str, int]`




---


