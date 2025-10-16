
---
title: "commands.new"
type: python-module
source_file: "bengal/cli/commands/new.py"
css_class: api-content
description: "Commands for creating new sites and pages."
---

# commands.new

Commands for creating new sites and pages.

---


## Functions

### `new`
```python
def new() -> None
```

✨ Create new site, page, layout, partial, or theme.

Subcommands:
    site      Create a new Bengal site with optional presets
    page      Create a new page in content directory
    layout    Create a new layout template in templates/layouts/
    partial   Create a new partial template in templates/partials/
    theme     Create a new theme scaffold with templates and assets



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `site`
```python
def site(name: str, theme: str, template: str, no_init: bool, init_preset: str) -> None
```

🏗️  Create a new Bengal site with optional structure initialization.



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
* - `name`
  - `str`
  - -
  - -
* - `theme`
  - `str`
  - -
  - -
* - `template`
  - `str`
  - -
  - -
* - `no_init`
  - `bool`
  - -
  - -
* - `init_preset`
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
### `page`
```python
def page(name: str, section: str) -> None
```

📄 Create a new page.

The page name will be automatically slugified for the filename.
Example: "My Awesome Page" → my-awesome-page.md



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
* - `section`
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
### `layout`
```python
def layout(name: str) -> None
```

📋 Create a new layout template.

Layouts are reusable HTML templates used by pages.
Example: "article" → templates/layouts/article.html



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
* - `name`
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
### `partial`
```python
def partial(name: str) -> None
```

🧩 Create a new partial template.

Partials are reusable template fragments included in other templates.
Example: "sidebar" → templates/partials/sidebar.html



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
* - `name`
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
### `theme`
```python
def theme(name: str) -> None
```

🎨 Create a new theme scaffold.

Themes are self-contained template and asset packages.
Example: "my-theme" → themes/my-theme/ with templates, partials, and assets



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
* - `name`
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
