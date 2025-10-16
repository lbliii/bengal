
---
title: "directives.code_tabs"
type: python-module
source_file: "bengal/rendering/plugins/directives/code_tabs.py"
css_class: api-content
description: "Code tabs directive for Mistune.  Provides multi-language code examples with tabbed interface for easy comparison across programming languages."
---

# directives.code_tabs

Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.

---

## Classes

### `CodeTabsDirective`

**Inherits from:** `DirectivePlugin`
Code tabs for multi-language examples.

Syntax:
    ````{code-tabs}

    ### Tab: Python
    ```python
    # Example code here
    ```

    ### Tab: JavaScript
    ```javascript
    console.log("hello")
    ```
    ````




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block, m, state)
```

Parse code tabs directive.



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

Register the directive and renderers.



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

### `render_code_tabs`
```python
def render_code_tabs(renderer, text, **attrs)
```

Render code tabs to HTML.



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
### `render_code_tab_item`
```python
def render_code_tab_item(renderer, **attrs)
```

Render code tab item marker (used internally).



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
* - `renderer`
  - -
  - -
  - -
:::

::::




---
