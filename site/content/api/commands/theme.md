
---
title: "commands.theme"
type: python-module
source_file: "bengal/cli/commands/theme.py"
css_class: api-content
description: "Theme-related CLI commands (themes, swizzle)."
---

# commands.theme

Theme-related CLI commands (themes, swizzle).

---


## Functions

### `theme`
```python
def theme() -> None
```

Theme utilities (list/info/discover/install, swizzle).



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `swizzle`
```python
def swizzle(template_path: str, source: str) -> None
```

Copy a theme template/partial to project templates/ and track provenance.



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
* - `template_path`
  - `str`
  - -
  - -
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `swizzle_list`
```python
def swizzle_list(source: str) -> None
```

List swizzled templates.



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
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `swizzle_update`
```python
def swizzle_update(source: str) -> None
```

Update swizzled templates if unchanged locally.



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
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `list_themes`
```python
def list_themes(source: str) -> None
```

List available themes (project, installed, bundled).



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
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `info`
```python
def info(slug: str, source: str) -> None
```

Show theme info for a slug (source, version, paths).



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
* - `slug`
  - `str`
  - -
  - -
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `discover`
```python
def discover(source: str) -> None
```

List swizzlable templates from the active theme chain.



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
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `install`
```python
def install(name: str, force: bool) -> None
```

Install a theme via uv pip.

NAME may be a package or a slug. If a slug without prefix is provided,
suggest canonical 'bengal-theme-<slug>'.



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
* - `name`
  - `str`
  - -
  - -
* - `force`
  - `bool`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `new`
```python
def new(slug: str, mode: str, output: str, extends: str, force: bool) -> None
```

Create a new theme scaffold.

SLUG is the theme identifier used in config (e.g., [site].theme = SLUG).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 5 parameters (click to expand)
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
* - `mode`
  - `str`
  - -
  - -
* - `output`
  - `str`
  - -
  - -
* - `extends`
  - `str`
  - -
  - -
* - `force`
  - `bool`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
