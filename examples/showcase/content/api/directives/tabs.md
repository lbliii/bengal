---
title: "directives.tabs"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/tabs.py"
---

# directives.tabs

Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

**Source:** `../../bengal/rendering/plugins/directives/tabs.py`

---

## Classes

### TabsDirective

**Inherits from:** `DirectivePlugin`
Tabbed content directive with full markdown support.

Syntax:
    ```{tabs}
    :id: my-tabs
    
    ### Tab: Python
    
    Content with **markdown**, code blocks, admonitions, etc.
    
    ### Tab: JavaScript
    
    More content here.
    ```

Supports nested directives, code blocks, admonitions, etc.




**Methods:**

#### parse

```python
def parse(self, block, m, state)
```

Parse tabs directive with nested content support.

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

### render_tabs

```python
def render_tabs(renderer, text, **attrs)
```

Render tabs container to HTML.

The text contains alternating tab titles and contents.
We need to restructure this into navigation + content panes.

**Parameters:**

- **renderer**
- **text**






---
### render_tab_title

```python
def render_tab_title(renderer, text)
```

Render tab title marker.

**Parameters:**

- **renderer**
- **text**






---
### render_tab_content

```python
def render_tab_content(renderer, text)
```

Render tab content.

**Parameters:**

- **renderer**
- **text**






---
