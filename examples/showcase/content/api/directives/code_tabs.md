---
title: "directives.code_tabs"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/code_tabs.py"
---

# directives.code_tabs

Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.

**Source:** `../../bengal/rendering/plugins/directives/code_tabs.py`

---

## Classes

### CodeTabsDirective

**Inherits from:** `DirectivePlugin`
Code tabs for multi-language examples.

Syntax:
    ```{code-tabs}
    
    ### Tab: Python
    ```python
    print("hello")
    ```
    
    ### Tab: JavaScript
    ```javascript
    console.log("hello")
    ```
    ```




**Methods:**

#### parse

```python
def parse(self, block, m, state)
```

Parse code tabs directive.

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

Register the directive and renderers.

**Parameters:**

- **self**
- **directive**
- **md**







---


## Functions

### render_code_tabs

```python
def render_code_tabs(renderer, text, **attrs)
```

Render code tabs to HTML.

**Parameters:**

- **renderer**
- **text**






---
### render_code_tab_item

```python
def render_code_tab_item(renderer, **attrs)
```

Render code tab item marker (used internally).

**Parameters:**

- **renderer**






---
