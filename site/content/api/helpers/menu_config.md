
---
title: "helpers.menu_config"
type: python-module
source_file: "bengal/cli/helpers/menu_config.py"
css_class: api-content
description: "Menu configuration generation helpers.  This module provides utilities for automatically generating menu configuration entries from site sections, similar to how sidebars and TOC are automatically ..."
---

# helpers.menu_config

Menu configuration generation helpers.

This module provides utilities for automatically generating menu
configuration entries from site sections, similar to how sidebars
and TOC are automatically generated.

---


## Functions

### `generate_menu_config`
```python
def generate_menu_config(sections: list[str], menu_name: str = 'main') -> str
```

Generate menu configuration entries for given sections.

Creates [[menu.main]] entries with appropriate weights based on
common conventions (Home first, then other sections in order).



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
* - `sections`
  - `list[str]`
  - -
  - List of section slugs (e.g., ['blog', 'about', 'projects'])
* - `menu_name`
  - `str`
  - `'main'`
  - Menu identifier (default: 'main')
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - TOML-formatted menu configuration string




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> generate_menu_config(['blog', 'about'])
    '''
    # Navigation Menu
    [[menu.main]]
    name = "Home"
    url = "/"
    weight = 1

    [[menu.main]]
    name = "Blog"
    url = "/blog/"
    weight = 10

    [[menu.main]]
    name = "About"
    url = "/about/"
    weight = 20
    '''
```


---
### `append_menu_to_config`
```python
def append_menu_to_config(config_path: Path, sections: list[str], menu_name: str = 'main') -> bool
```

Append menu configuration to existing bengal.toml file.

Safely appends menu entries to the config file, checking if
menu configuration already exists to avoid duplicates.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `config_path`
  - `Path`
  - -
  - Path to bengal.toml
* - `sections`
  - `list[str]`
  - -
  - List of section slugs to add
* - `menu_name`
  - `str`
  - `'main'`
  - Menu identifier (default: 'main')
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if menu was added, False if menu already exists

:::{rubric} Raises
:class: rubric-raises
:::
- **`FileNotFoundError`**: If config file doesn't exist



---
### `get_menu_suggestions`
```python
def get_menu_suggestions(sections: list[str], menu_name: str = 'main') -> dict[str, Any]
```

Get menu configuration suggestions for display to user.

Returns structured menu data that can be used for:
- CLI display/preview
- Interactive prompts
- Configuration generation



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
* - `sections`
  - `list[str]`
  - -
  - List of section slugs
* - `menu_name`
  - `str`
  - `'main'`
  - Menu identifier (default: 'main')
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Dictionary with menu items and TOML representation




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> get_menu_suggestions(['blog', 'about'])
    {
        'menu_name': 'main',
        'items': [
            {'name': 'Home', 'url': '/', 'weight': 1},
            {'name': 'Blog', 'url': '/blog/', 'weight': 10},
            {'name': 'About', 'url': '/about/', 'weight': 20}
        ],
        'toml': '[[menu.main]]\nname = "Home"...'
    }
```


---
