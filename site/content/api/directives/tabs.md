
---
title: "directives.tabs"
type: python-module
source_file: "bengal/rendering/plugins/directives/tabs.py"
css_class: api-content
description: "Tabs directive for Mistune.  Provides tabbed content sections with full markdown support including nested directives, code blocks, and admonitions.  Modern MyST syntax:     :::{tab-set}     :::{tab..."
---

# directives.tabs

Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

Modern MyST syntax:
    :::{tab-set}
    :::{tab-item} Python
    Content here
    :::
    :::{tab-item} JavaScript
    Content here
    :::
    ::::

---

## Classes

### `TabsDirective`

**Inherits from:** `DirectivePlugin`
Legacy tabs directive for backward compatibility.

Syntax:
    ```{tabs}
    :id: my-tabs

    ### Tab: First

    Content in first tab.

    ### Tab: Second

    Content in second tab.
    ```

This uses ### Tab: markers to split content into tabs.
For new code, prefer the modern {tab-set}/{tab-item} syntax.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse legacy tabs directive.



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
  - `Any`
  - -
  - -
* - `m`
  - `Match`
  - -
  - -
* - `state`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive with mistune.



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

### `TabSetDirective`

**Inherits from:** `DirectivePlugin`
Modern MyST-style tab container directive.

Syntax:
    :::{tab-set}
    :sync: my-key  # Optional: sync tabs across multiple tab-sets

    :::{tab-item} Python
    Python content with **markdown** support.
    :::

    :::{tab-item} JavaScript
    JavaScript content here.
    :::
    ::::

Each tab-item is a nested directive inside the tab-set.
This is cleaner and more consistent with MyST Markdown.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse tab-set directive.



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
  - `Any`
  - -
  - -
* - `m`
  - `Match`
  - -
  - -
* - `state`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive with mistune.



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

### `TabItemDirective`

**Inherits from:** `DirectivePlugin`
Individual tab directive (nested in tab-set).

Syntax:
    :::{tab-item} Tab Title
    :selected:  # Optional: mark this tab as initially selected

    Tab content with full **markdown** support.
    :::

Supports all markdown features including nested directives.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse tab-item directive.



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
  - `Any`
  - -
  - -
* - `m`
  - `Match`
  - -
  - -
* - `state`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive with mistune.



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

### `render_tab_set`
```python
def render_tab_set(renderer, text: str, **attrs) -> str
```

Render tab-set container to HTML.

The text contains rendered tab-item children. We need to extract
titles and contents to build the tab navigation and panels.



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
  - Mistune renderer
* - `text`
  - `str`
  - -
  - Rendered children (tab items)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for tab set




---
### `render_tab_item`
```python
def render_tab_item(renderer, text: str, **attrs) -> str
```

Render individual tab item to HTML.

This creates a wrapper div with metadata that the parent tab-set
will parse to build the navigation and panels.



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
  - Mistune renderer
* - `text`
  - `str`
  - -
  - Rendered tab content
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for tab item (wrapper for tab-set to parse)




---
### `render_legacy_tab_item`
```python
def render_legacy_tab_item(renderer, text: str, **attrs) -> str
```

Render legacy tab item to HTML.

Similar to render_tab_item, creates a wrapper div with metadata
that the parent legacy_tabs will parse.



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
  - Mistune renderer
* - `text`
  - `str`
  - -
  - Rendered tab content
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for tab item (wrapper for legacy_tabs to parse)




---
### `render_tabs`
```python
def render_tabs(renderer, text: str, **attrs) -> str
```

Render legacy tabs directive to HTML.



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
  - Mistune renderer
* - `text`
  - `str`
  - -
  - Rendered children (tab items as wrapper divs)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for tabs




---
