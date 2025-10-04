---
title: "directives.dropdown"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/dropdown.py"
---

# directives.dropdown

Dropdown directive for Mistune.

Provides collapsible sections with markdown support including
nested directives and code blocks.

**Source:** `../../bengal/rendering/plugins/directives/dropdown.py`

---

## Classes

### DropdownDirective

**Inherits from:** `DirectivePlugin`
Collapsible dropdown directive with markdown support.

Syntax:
    ```{dropdown} Title
    :open: true
    
    Content with **markdown**, code blocks, etc.
    
    !!! note
        Even nested admonitions work!
    ```




**Methods:**

#### parse

```python
def parse(self, block, m, state)
```

Parse dropdown directive with nested content support.

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

Register the directive and renderer.

**Parameters:**

- **self**
- **directive**
- **md**







---


## Functions

### render_dropdown

```python
def render_dropdown(renderer, text, **attrs)
```

Render dropdown to HTML.

**Parameters:**

- **renderer**
- **text**






---
