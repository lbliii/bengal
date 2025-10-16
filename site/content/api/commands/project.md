
---
title: "commands.project"
type: python-module
source_file: "bengal/cli/commands/project.py"
css_class: api-content
description: "Python module documentation"
---

# commands.project

*No module description provided.*

---


## Functions

### `project_cli`
```python
def project_cli()
```

📦 Project management and setup commands.

Commands:
    init       Initialize project structure and content sections
    profile    Set your working profile (dev, themer, writer, ai)
    validate   Validate configuration and directory structure
    info       Display project information and statistics
    config     View and manage configuration settings







---
### `profile`
```python
def profile(profile_name: str) -> None
```

👤 Set your Bengal working profile / persona.

Profiles customize CLI behavior and output format based on your role:

    dev       👨‍💻  Full debug output, performance metrics, all commands
    themer    🎨  Focus on templates, themes, component preview
    writer    ✍️  Simple UX, focus on content, minimal tech details
    ai        🤖  Machine-readable output, JSON formats



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
* - `profile_name`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal project profile dev       # Switch to developer profile
```


---
### `validate`
```python
def validate() -> None
```

✓ Validate Bengal project configuration and structure.

Checks:
    ✓ bengal.toml exists and is valid
    ✓ Required configuration fields
    ✓ Directory structure (content/, templates/, assets/)
    ✓ Theme configuration
    ✓ Content files parseable



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `info`
```python
def info() -> None
```

ℹ️  Display project information and statistics.

Shows:
    - Site title, baseurl, theme
    - Content statistics (pages, sections)
    - Asset counts
    - Configuration paths



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `config`
```python
def config(key: str, value: str, set_value: bool, list_all: bool) -> None
```

⚙️  Manage Bengal configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `key`
  - `str`
  - -
  - -
* - `value`
  - `str`
  - -
  - -
* - `set_value`
  - `bool`
  - -
  - -
* - `list_all`
  - `bool`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal project config                    # Show current config
```


---
