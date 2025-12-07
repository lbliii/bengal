
---
title: "tabs"
type: "python-module"
source_file: "bengal/rendering/plugins/directives/tabs.py"
line_number: 1
description: "Tabs directive for Mistune. Provides tabbed content sections with full markdown support including nested directives, code blocks, and admonitions. Modern MyST syntax: :::{tab-set} :::{tab-item} Python..."
---

# tabs
**Type:** Module
**Source:** [View source](bengal/rendering/plugins/directives/tabs.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[plugins](/api/bengal/rendering/plugins/) ›[directives](/api/bengal/rendering/plugins/directives/) ›tabs

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

## Classes




### `TabsDirective`


**Inherits from:**`DirectivePlugin`Legacy tabs directive for backward compatibility.

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









## Methods



#### `parse`

:::{div} api-badge-group
:::

```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse legacy tabs directive.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `__call__`

:::{div} api-badge-group
:::

```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |




### `TabSetDirective`


**Inherits from:**`DirectivePlugin`Modern MyST-style tab container directive.

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









## Methods



#### `parse`

:::{div} api-badge-group
:::

```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse tab-set directive.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `__call__`

:::{div} api-badge-group
:::

```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |




### `TabItemDirective`


**Inherits from:**`DirectivePlugin`Individual tab directive (nested in tab-set).

Syntax:
    :::{tab-item} Tab Title
    :selected:  # Optional: mark this tab as initially selected

    Tab content with full **markdown** support.
    :::

Supports all markdown features including nested directives.









## Methods



#### `parse`

:::{div} api-badge-group
:::

```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse tab-item directive.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `__call__`

:::{div} api-badge-group
:::

```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |

## Functions



### `render_tab_set`


```python
def render_tab_set(renderer, text: str, **attrs) -> str
```



Render tab-set container to HTML.

The text contains rendered tab-item children. We need to extract
titles and contents to build the tab navigation and panels.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered children (tab items) |







**Returns**


`str` - HTML string for tab set




### `render_tab_item`


```python
def render_tab_item(renderer, text: str, **attrs) -> str
```



Render individual tab item to HTML.

This creates a wrapper div with metadata that the parent tab-set
will parse to build the navigation and panels.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered tab content |







**Returns**


`str` - HTML string for tab item (wrapper for tab-set to parse)




### `render_legacy_tab_item`


```python
def render_legacy_tab_item(renderer, text: str, **attrs) -> str
```



Render legacy tab item to HTML.

Similar to render_tab_item, creates a wrapper div with metadata
that the parent legacy_tabs will parse.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered tab content |







**Returns**


`str` - HTML string for tab item (wrapper for legacy_tabs to parse)




### `render_tabs`


```python
def render_tabs(renderer, text: str, **attrs) -> str
```



Render legacy tabs directive to HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered children (tab items as wrapper divs) |







**Returns**


`str` - HTML string for tabs



---
*Generated by Bengal autodoc from `bengal/rendering/plugins/directives/tabs.py`*

