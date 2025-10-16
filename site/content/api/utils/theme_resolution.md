
---
title: "utils.theme_resolution"
type: python-module
source_file: "bengal/utils/theme_resolution.py"
css_class: api-content
description: "Python module documentation"
---

# utils.theme_resolution

*No module description provided.*

---


## Functions

### `resolve_theme_chain`
```python
def resolve_theme_chain(site_root: Path, active_theme: str | None) -> list[str]
```

Resolve theme inheritance chain starting from the active theme.

Order: child first → parent → ... (does not duplicate 'default').



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
* - `site_root`
  - `Path`
  - -
  - -
* - `active_theme`
  - `str | None`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[str]`




---
### `iter_theme_asset_dirs`
```python
def iter_theme_asset_dirs(site_root: Path, theme_chain: Iterable[str]) -> list[Path]
```

Return list of theme asset directories from parents to child (low → high priority).
Site assets can still override these.



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
* - `site_root`
  - `Path`
  - -
  - -
* - `theme_chain`
  - `Iterable[str]`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[Path]`




---
