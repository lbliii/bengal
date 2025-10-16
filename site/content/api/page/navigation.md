
---
title: "page.navigation"
type: python-module
source_file: "bengal/core/page/navigation.py"
css_class: api-content
description: "Page Navigation Mixin - Navigation and hierarchy relationships."
---

# page.navigation

Page Navigation Mixin - Navigation and hierarchy relationships.

---

## Classes

### `PageNavigationMixin`


Mixin providing navigation capabilities for pages.

This mixin handles:
- Site-level navigation: next, prev
- Section-level navigation: next_in_section, prev_in_section
- Hierarchy: parent, ancestors



:::{rubric} Properties
:class: rubric-properties
:::
#### `next` @property

```python
@property
def next(self) -> Page | None
```

Get the next page in the site's collection of pages.
#### `prev` @property

```python
@property
def prev(self) -> Page | None
```

Get the previous page in the site's collection of pages.
#### `next_in_section` @property

```python
@property
def next_in_section(self) -> Page | None
```

Get the next page within the same section, respecting weight order.

Pages are ordered by weight (ascending), then alphabetically by title.
Pages without weight are treated as weight=999999 (appear at end).
Index pages (_index.md, index.md) are skipped in navigation.
#### `prev_in_section` @property

```python
@property
def prev_in_section(self) -> Page | None
```

Get the previous page within the same section, respecting weight order.

Pages are ordered by weight (ascending), then alphabetically by title.
Pages without weight are treated as weight=999999 (appear at end).
Index pages (_index.md, index.md) are skipped in navigation.
#### `parent` @property

```python
@property
def parent(self) -> Any | None
```

Get the parent section of this page.
#### `ancestors` @property

```python
@property
def ancestors(self) -> list[Any]
```

Get all ancestor sections of this page.

:::{rubric} Methods
:class: rubric-methods
:::
#### `next`
```python
def next(self) -> Page | None
```

Get the next page in the site's collection of pages.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None` - Next page or None if this is the last page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.next %}
```


---
#### `prev`
```python
def prev(self) -> Page | None
```

Get the previous page in the site's collection of pages.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None` - Previous page or None if this is the first page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.prev %}
```


---
#### `next_in_section`
```python
def next_in_section(self) -> Page | None
```

Get the next page within the same section, respecting weight order.

Pages are ordered by weight (ascending), then alphabetically by title.
Pages without weight are treated as weight=999999 (appear at end).
Index pages (_index.md, index.md) are skipped in navigation.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None` - Next page in section or None if this is the last page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.next_in_section %}
```


---
#### `prev_in_section`
```python
def prev_in_section(self) -> Page | None
```

Get the previous page within the same section, respecting weight order.

Pages are ordered by weight (ascending), then alphabetically by title.
Pages without weight are treated as weight=999999 (appear at end).
Index pages (_index.md, index.md) are skipped in navigation.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Page | None` - Previous page in section or None if this is the first page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.prev_in_section %}
```


---
#### `parent`
```python
def parent(self) -> Any | None
```

Get the parent section of this page.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any | None` - Parent section or None




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.parent %}
```


---
#### `ancestors`
```python
def ancestors(self) -> list[Any]
```

Get all ancestor sections of this page.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Any]` - List of ancestor sections from immediate parent to root




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for ancestor in page.ancestors | reverse %}
```


---
