
---
title: "navigation"
type: "python-module"
source_file: "bengal/bengal/rendering/plugins/directives/navigation.py"
line_number: 1
description: "Navigation directives for Bengal SSG. Provides Hugo-style directives that leverage the pre-computed site tree: - breadcrumbs: Auto-generate breadcrumb navigation from page.ancestors - siblings: Show o..."
---

# navigation
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/plugins/directives/navigation.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[plugins](/api/bengal/rendering/plugins/) ›[directives](/api/bengal/rendering/plugins/directives/) ›navigation

Navigation directives for Bengal SSG.

Provides Hugo-style directives that leverage the pre-computed site tree:
- breadcrumbs: Auto-generate breadcrumb navigation from page.ancestors
- siblings: Show other pages in the same section
- prev-next: Section-aware previous/next navigation
- related: Show related content based on tags

All directives access renderer._current_page to walk the object tree.

## Classes




### `BreadcrumbsDirective`


**Inherits from:**`DirectivePlugin`Auto-generate breadcrumb navigation from page ancestors.

Uses page.ancestors to build a breadcrumb trail from root to current page.

Syntax:
    :::{breadcrumbs}
    :separator: /
    :show-home: true
    :home-text: Home
    :::

Example output:
    Home / Docs / Content / Authoring









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse breadcrumbs directive options.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







**Returns**


`dict[str, Any]`



#### `__call__`
```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |




### `SiblingsDirective`


**Inherits from:**`DirectivePlugin`Show other pages in the same section.

Uses page._section.sorted_pages to show sibling pages.

Syntax:
    :::{siblings}
    :limit: 10
    :exclude-current: true
    :show-description: true
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse siblings directive options.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







**Returns**


`dict[str, Any]`



#### `__call__`
```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |




### `PrevNextDirective`


**Inherits from:**`DirectivePlugin`Section-aware previous/next navigation.

Uses page.prev_in_section and page.next_in_section for navigation.

Syntax:
    :::{prev-next}
    :show-title: true
    :show-section: false
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse prev-next directive options.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







**Returns**


`dict[str, Any]`



#### `__call__`
```python
def __call__(self, directive, md)
```


Register the directive with mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive` | - | - | *No description provided.* |
| `md` | - | - | *No description provided.* |




### `RelatedDirective`


**Inherits from:**`DirectivePlugin`Show related content based on tags.

Uses page.related_posts (pre-computed during build).

Syntax:
    :::{related}
    :limit: 5
    :title: Related Articles
    :show-tags: true
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse related directive options.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | *No description provided.* |
| `m` | `Match` | - | *No description provided.* |
| `state` | `Any` | - | *No description provided.* |







**Returns**


`dict[str, Any]`



#### `__call__`
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



### `render_breadcrumbs`


```python
def render_breadcrumbs(renderer, text: str, **attrs) -> str
```



Render breadcrumb navigation from page ancestors.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer (has _current_page attribute) |
| `text` | `str` | - | Unused |







**Returns**


`str` - HTML breadcrumb navigation




### `render_siblings`


```python
def render_siblings(renderer, text: str, **attrs) -> str
```



Render sibling pages in the same section.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Unused |







**Returns**


`str` - HTML list of sibling pages




### `render_prev_next`


```python
def render_prev_next(renderer, text: str, **attrs) -> str
```



Render previous/next navigation links.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Unused |







**Returns**


`str` - HTML prev/next navigation




### `render_related`


```python
def render_related(renderer, text: str, **attrs) -> str
```



Render related content based on tags.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Unused |







**Returns**


`str` - HTML list of related content



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/plugins/directives/navigation.py`*

