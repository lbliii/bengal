
---
title: "cli"
type: python-module
source_file: "bengal/cli/__init__.py"
css_class: api-content
description: "Command-line interface for Bengal SSG."
---

# cli

Command-line interface for Bengal SSG.

---

## Classes

### `BengalGroup`

**Inherits from:** `click.Group`
Custom Click group with typo detection and suggestions.




:::{rubric} Methods
:class: rubric-methods
:::
#### `resolve_command`
```python
def resolve_command(self, ctx, args)
```

Resolve command with fuzzy matching for typos.



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
* - `self`
  - -
  - -
  - -
* - `ctx`
  - -
  - -
  - -
* - `args`
  - -
  - -
  - -
:::

::::




---


## Functions

### `main`
```python
def main() -> None
```

ᓚᘏᗢ Bengal SSG - A high-performance static site generator.

Quick start:
    bengal site build     Build your site
    bengal site serve     Start dev server with live reload
    bengal new site       Create a new site

For more commands:
    bengal --help



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
