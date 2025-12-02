
---
title: "cards"
type: "python-module"
source_file: "bengal/bengal/rendering/plugins/directives/cards.py"
line_number: 1
description: "Cards directive for Bengal SSG. Provides a modern, simple card grid system with auto-layout and responsive columns. Syntax: :::{cards} :columns: 3  # or \"auto\" or \"1-2-3-4\" for responsive :gap: medium..."
---

# cards
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/rendering/plugins/directives/cards.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[plugins](/api/bengal/rendering/plugins/) ›[directives](/api/bengal/rendering/plugins/directives/) ›cards

Cards directive for Bengal SSG.

Provides a modern, simple card grid system with auto-layout and responsive columns.

Syntax:
    :::{cards}
    :columns: 3  # or "auto" or "1-2-3-4" for responsive
    :gap: medium
    :style: default
    :variant: navigation  # or "info", "concept" for non-interactive use

    :::{card} Card Title
    :icon: book
    :link: /docs/
    :color: blue
    :image: /hero.jpg
    :footer: Updated 2025

    Card content with **full markdown** support.
    :::
    ::::

Examples:
    # Auto-layout (default)
    :::{cards}
    :::{card} One
    :::
    :::{card} Two
    :::
    ::::

    # Responsive columns
    :::{cards}
    :columns: 1-2-3  # 1 col mobile, 2 tablet, 3 desktop
    :::{card} Card 1
    :::
    :::{card} Card 2
    :::
    ::::

## Classes




### `CardsDirective`


**Inherits from:**`DirectivePlugin`Cards grid container directive.

Creates a responsive grid of cards with sensible defaults and powerful options.
Uses modern CSS Grid for layout.









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse cards directive.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | Block parser |
| `m` | `Match` | - | Regex match object |
| `state` | `Any` | - | Parser state |







**Returns**


`dict[str, Any]` - Token dict with type 'cards_grid'




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




### `CardDirective`


**Inherits from:**`DirectivePlugin`Individual card directive (nested in cards).

Creates a single card with optional icon, link, color, image, and footer.
Supports full markdown in content.

Supports footer separator (Sphinx-Design convention):
    :::{card} Title
    Body content
    +++
    Footer content
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse card directive.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | Block parser |
| `m` | `Match` | - | Regex match object |
| `state` | `Any` | - | Parser state |







**Returns**


`dict[str, Any]` - Token dict with type 'card'



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




### `GridDirective`


**Inherits from:**`DirectivePlugin`Sphinx-Design grid compatibility layer.

Accepts old Sphinx-Design syntax and converts to modern cards syntax.

Old syntax:
    ::::{grid} 1 2 2 2
    :gutter: 1
    ::::

Converts to:
    :::{cards}
    :columns: 1-2-2-2
    :gap: medium
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse grid directive (compatibility mode).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | Block parser |
| `m` | `Match` | - | Regex match object |
| `state` | `Any` | - | Parser state |







**Returns**


`dict[str, Any]` - Token dict with type 'cards_grid' (same as CardsDirective)





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




### `GridItemCardDirective`


**Inherits from:**`DirectivePlugin`Sphinx-Design grid-item-card compatibility layer.

Converts old syntax to modern card syntax.

Old syntax:
    :::{grid-item-card} {octicon}`book;1.5em` Title
    :link: docs/page
    :link-type: doc
    Content
    :::

Converts to:
    :::{card} Title
    :icon: book
    :link: docs/page
    Content
    :::









## Methods



#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```


Parse grid-item-card directive (compatibility mode).

Supports Sphinx-Design footer separator:
    :::{grid-item-card} Title
    Body content
    +++
    Footer content
    :::


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `block` | `Any` | - | Block parser |
| `m` | `Match` | - | Regex match object |
| `state` | `Any` | - | Parser state |







**Returns**


`dict[str, Any]` - Token dict with type 'card' (same as CardDirective)




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



### `render_cards_grid`


```python
def render_cards_grid(renderer, text: str, **attrs) -> str
```



Render cards grid container to HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered children (cards) |







**Returns**


`str` - HTML string for card grid




### `render_card`


```python
def render_card(renderer, text: str, **attrs) -> str
```



Render individual card to HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | - | - | Mistune renderer |
| `text` | `str` | - | Rendered card content |







**Returns**


`str` - HTML string for card



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/plugins/directives/cards.py`*

