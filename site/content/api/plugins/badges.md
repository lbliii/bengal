
---
title: "plugins.badges"
type: python-module
source_file: "bengal/rendering/plugins/badges.py"
css_class: api-content
description: "Badge plugin for Mistune.  Provides Sphinx-Design badge syntax: {bdg-color}`text`  Supports badge colors that map to Bengal's design system."
---

# plugins.badges

Badge plugin for Mistune.

Provides Sphinx-Design badge syntax: {bdg-color}`text`

Supports badge colors that map to Bengal's design system.

---

## Classes

### `BadgePlugin`


Mistune plugin for inline badge syntax.

Syntax:
    {bdg-primary}`text`      -> Primary color badge
    {bdg-secondary}`text`    -> Secondary/muted badge
    {bdg-success}`text`      -> Success/green badge
    {bdg-danger}`text`       -> Danger/red badge
    {bdg-warning}`text`      -> Warning/yellow badge
    {bdg-info}`text`         -> Info/blue badge
    {bdg-light}`text`        -> Light badge
    {bdg-dark}`text`         -> Dark badge

Maps to Bengal's CSS color system:
    bdg-primary   -> badge-primary (blue)
    bdg-secondary -> badge-secondary (gray)
    bdg-success   -> badge-success (green)
    bdg-danger    -> badge-danger (red)
    bdg-warning   -> badge-warning (yellow)
    bdg-info      -> badge-info (blue)
    bdg-light     -> badge-light (light gray)
    bdg-dark      -> badge-dark (dark gray)

Sphinx-Design compatibility: Full support for bdg-* roles.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

Initialize badge plugin.



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




---
#### `__call__`
```python
def __call__(self, md)
```

Register the plugin with Mistune.

Badge substitution happens in parser.py after HTML is generated.
This method is required for Mistune plugin interface but does nothing.



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
* - `md`
  - -
  - -
  - -
:::

::::




---
