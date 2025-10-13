
---
title: "directives.admonitions"
type: python-module
source_file: "bengal/rendering/plugins/directives/admonitions.py"
css_class: api-content
description: "Admonition directive for Mistune.  Provides note, warning, tip, danger, and other callout boxes with full markdown support."
---

# directives.admonitions

Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes with
full markdown support.

---

## Classes

### `AdmonitionDirective`

**Inherits from:** `DirectivePlugin`
Admonition directive using Mistune's fenced syntax.

Syntax:
    ```{note} Optional Title
    Content with **markdown** support.
    ```

Supported types: note, tip, warning, danger, error, info, example, success, caution




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block, m, state)
```

Parse admonition directive.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`block`**
- **`m`**
- **`state`**





---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register all admonition types as directives.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`directive`**
- **`md`**





---


## Functions

### `render_admonition`
```python
def render_admonition(renderer, text: str, admon_type: str, title: str) -> str
```

Render admonition to HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`renderer`**
- **`text`** (`str`)
- **`admon_type`** (`str`)
- **`title`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
