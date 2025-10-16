
---
title: "utils.theme_registry"
type: python-module
source_file: "bengal/utils/theme_registry.py"
css_class: api-content
description: "Installed theme discovery and utilities.  Discovers uv/pip-installed themes via entry points (group: "bengal.themes").  Conventions: - Package name: prefer "bengal-theme-<slug>"; accept "<slug>-ben..."
---

# utils.theme_registry

Installed theme discovery and utilities.

Discovers uv/pip-installed themes via entry points (group: "bengal.themes").

Conventions:
- Package name: prefer "bengal-theme-<slug>"; accept "<slug>-bengal-theme".
- Entry point name: slug (e.g., "acme") → value: import path (e.g., "bengal_themes.acme").

---

## Classes

### `ThemePackage`


*No class description provided.*


:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 4 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `slug`
  - `str`
  - -
* - `package`
  - `str`
  - -
* - `distribution`
  - `str | None`
  - -
* - `version`
  - `str | None`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `templates_exists`
```python
def templates_exists(self) -> bool
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

`bool`




---
#### `assets_exists`
```python
def assets_exists(self) -> bool
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

`bool`




---
#### `manifest_exists`
```python
def manifest_exists(self) -> bool
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

`bool`




---
#### `jinja_loader`
```python
def jinja_loader(self) -> PackageLoader
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

`PackageLoader`




---
#### `resolve_resource_path`
```python
def resolve_resource_path(self, relative: str) -> Path | None
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
* - `relative`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path | None`




---


## Functions

### `get_installed_themes`
```python
def get_installed_themes() -> dict[str, ThemePackage]
```

Discover installed themes via entry points.



:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, ThemePackage]` - Mapping of slug -> ThemePackage




---
### `get_theme_package`
```python
def get_theme_package(slug: str) -> ThemePackage | None
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
* - `slug`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`ThemePackage | None`




---
### `clear_theme_cache`
```python
def clear_theme_cache() -> None
```

*No description provided.*



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
