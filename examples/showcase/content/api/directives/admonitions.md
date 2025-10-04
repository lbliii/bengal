---
title: "directives.admonitions"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/admonitions.py"
---

# directives.admonitions

Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes with
full markdown support.

**Source:** `../../bengal/rendering/plugins/directives/admonitions.py`

---

## Classes

### AdmonitionDirective

**Inherits from:** `DirectivePlugin`
Admonition directive using Mistune's fenced syntax.

Syntax:
    ```{note} Optional Title
    Content with **markdown** support.
    ```

Supported types: note, tip, warning, danger, error, info, example, success, caution




**Methods:**

#### parse

```python
def parse(self, block, m, state)
```

Parse admonition directive.

**Parameters:**

- **self**
- **block**
- **m**
- **state**







---
#### __call__

```python
def __call__(self, directive, md)
```

Register all admonition types as directives.

**Parameters:**

- **self**
- **directive**
- **md**







---


## Functions

### render_admonition

```python
def render_admonition(renderer, text: str, admon_type: str, title: str) -> str
```

Render admonition to HTML.

**Parameters:**

- **renderer**
- **text** (`str`)
- **admon_type** (`str`)
- **title** (`str`)

**Returns:** `str`





---
