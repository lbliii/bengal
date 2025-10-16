
---
title: "page.relationships"
type: python-module
source_file: "bengal/core/page/relationships.py"
css_class: api-content
description: "Page Relationships Mixin - Relationship checking and comparisons."
---

# page.relationships

Page Relationships Mixin - Relationship checking and comparisons.

---

## Classes

### `PageRelationshipsMixin`


Mixin providing relationship checking for pages.

This mixin handles:
- Page equality checking
- Section membership
- Ancestor/descendant relationships




:::{rubric} Methods
:class: rubric-methods
:::
#### `eq`
```python
def eq(self, other: 'Page') -> bool
```

Check if two pages are equal.



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
* - `self`
  - -
  - -
  - -
* - `other`
  - `'Page'`
  - -
  - Page to compare with
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if pages are the same




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.eq(other_page) %}
```


---
#### `in_section`
```python
def in_section(self, section: Any) -> bool
```

Check if this page is in the given section.



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
* - `self`
  - -
  - -
  - -
* - `section`
  - `Any`
  - -
  - Section to check
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if page is in the section




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.in_section(blog_section) %}
```


---
#### `is_ancestor`
```python
def is_ancestor(self, other: 'Page') -> bool
```

Check if this page is an ancestor of another page.



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
* - `self`
  - -
  - -
  - -
* - `other`
  - `'Page'`
  - -
  - Page to check
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if this page is an ancestor




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if section.is_ancestor(page) %}
```


---
#### `is_descendant`
```python
def is_descendant(self, other: 'Page') -> bool
```

Check if this page is a descendant of another page.



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
* - `self`
  - -
  - -
  - -
* - `other`
  - `'Page'`
  - -
  - Page to check
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if this page is a descendant




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.is_descendant(section) %}
```


---


