
---
title: "directives.dropdown"
type: python-module
source_file: "bengal/rendering/plugins/directives/dropdown.py"
css_class: api-content
description: "Dropdown directive for Mistune.  Provides collapsible sections with markdown support including nested directives and code blocks."
---

# directives.dropdown

Dropdown directive for Mistune.

Provides collapsible sections with markdown support including
nested directives and code blocks.

---

## Classes

### `DropdownDirective`

**Inherits from:** `DirectivePlugin`
Collapsible dropdown directive with markdown support.

Syntax:
    ````{dropdown} Title
    :open: true

    Content with **markdown**, code blocks, etc.

    !!! note
        Even nested admonitions work!
    ````




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block, m, state)
```

Parse dropdown directive with nested content support.



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
* - `self`
  - -
  - -
  - -
* - `block`
  - -
  - -
  - -
* - `m`
  - -
  - -
  - -
* - `state`
  - -
  - -
  - -
:::

::::




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive and renderer.



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
* - `directive`
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


## Functions

### `render_dropdown`
```python
def render_dropdown(renderer, text, **attrs)
```

Render dropdown to HTML.



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
* - `renderer`
  - -
  - -
  - -
* - `text`
  - -
  - -
  - -
:::

::::




---
