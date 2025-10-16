
---
title: "core.section"
type: python-module
source_file: "bengal/core/section.py"
css_class: api-content
description: "Section Object - Represents a folder or logical grouping of pages."
---

# core.section

Section Object - Represents a folder or logical grouping of pages.

---

## Classes

### `WeightedPage`


*No class description provided.*

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `page`
  - `Page`
  - -
* - `weight`
  - `float`
  - -
* - `title_lower`
  - `str`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `__lt__`
```python
def __lt__(self, other)
```

*No description provided.*



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
  - -
  - -
  - -
:::

::::




---

### `Section`


Represents a folder or logical grouping of pages.

HASHABILITY:
============
Sections are hashable based on their path, allowing them to be stored
in sets and used as dictionary keys. This enables:
- Fast membership tests and lookups
- Type-safe Set[Section] collections
- Set operations for section analysis

Two sections with the same path are considered equal. The hash is stable
throughout the section lifecycle because path is immutable.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 8 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `name`
  - `str`
  - Section name
* - `path`
  - `Path`
  - Path to the section directory
* - `pages`
  - `list[Page]`
  - List of pages in this section
* - `subsections`
  - `list['Section']`
  - Child sections
* - `metadata`
  - `dict[str, Any]`
  - Section-level metadata
* - `index_page`
  - `Page | None`
  - Optional index page for the section
* - `parent`
  - `'Section | None'`
  - Parent section (if nested)
* - `_site`
  - `Any | None`
  - -
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `title` @property

```python
@property
def title(self) -> str
```

Get section title from metadata or generate from name.
#### `hierarchy` @property

```python
@property
def hierarchy(self) -> list[str]
```

Get the full hierarchy path of this section.
#### `depth` @property

```python
@property
def depth(self) -> int
```

Get the depth of this section in the hierarchy.
#### `root` @property

```python
@property
def root(self) -> 'Section'
```

Get the root section of this section's hierarchy.
#### `regular_pages` @property

```python
@property
def regular_pages(self) -> list[Page]
```

Get only regular pages (non-sections) in this section.
#### `sections` @property

```python
@property
def sections(self) -> list['Section']
```

Get immediate child sections.
#### `sorted_pages` @property

```python
@property
def sorted_pages(self) -> list[Page]
```

Get pages sorted by weight (ascending), then by title.

Pages without a weight field are treated as having weight=float('inf')
and appear at the end of the sorted list, after all weighted pages.
Lower weights appear first in the list. Pages with equal weight are sorted
alphabetically by title.
#### `sorted_subsections` @property

```python
@property
def sorted_subsections(self) -> list['Section']
```

Get subsections sorted by weight (ascending), then by title.

Subsections without a weight field in their index page metadata
are treated as having weight=999999 (appear at end). Lower weights appear first.
#### `regular_pages_recursive` @property

```python
@property
def regular_pages_recursive(self) -> list[Page]
```

Get all regular pages recursively (including from subsections).
#### `url` @property

```python
@property
def url(self) -> str
```

Get the URL for this section (cached after first access).

Section URLs are stable after index pages have output_path set.
Caching eliminates redundant recalculation - previously this was
computed ~5× per page during health checks.

:::{rubric} Methods
:class: rubric-methods
:::
#### `title`
```python
def title(self) -> str
```

Get section title from metadata or generate from name.



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

`str`




---
#### `hierarchy`
```python
def hierarchy(self) -> list[str]
```

Get the full hierarchy path of this section.



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

`list[str]` - List of section names from root to this section




---
#### `depth`
```python
def depth(self) -> int
```

Get the depth of this section in the hierarchy.



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

`int`




---
#### `root`
```python
def root(self) -> 'Section'
```

Get the root section of this section's hierarchy.



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

`'Section'` - The topmost ancestor section




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set root_section = page._section.root %}
```


---
#### `regular_pages`
```python
def regular_pages(self) -> list[Page]
```

Get only regular pages (non-sections) in this section.



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

`list[Page]` - List of regular Page objects (excludes subsections)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for page in section.regular_pages %}
```


---
#### `sections`
```python
def sections(self) -> list['Section']
```

Get immediate child sections.



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

`list['Section']` - List of child Section objects




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for subsection in section.sections %}
```


---
#### `sorted_pages`
```python
def sorted_pages(self) -> list[Page]
```

Get pages sorted by weight (ascending), then by title.

Pages without a weight field are treated as having weight=float('inf')
and appear at the end of the sorted list, after all weighted pages.
Lower weights appear first in the list. Pages with equal weight are sorted
alphabetically by title.



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

`list[Page]` - List of pages sorted by weight, then title




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for page in section.sorted_pages %}
```


---
#### `sorted_subsections`
```python
def sorted_subsections(self) -> list['Section']
```

Get subsections sorted by weight (ascending), then by title.

Subsections without a weight field in their index page metadata
are treated as having weight=999999 (appear at end). Lower weights appear first.



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

`list['Section']` - List of subsections sorted by weight, then title




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for subsection in section.sorted_subsections %}
```


---
#### `regular_pages_recursive`
```python
def regular_pages_recursive(self) -> list[Page]
```

Get all regular pages recursively (including from subsections).



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

`list[Page]` - List of all descendant regular pages




:::{rubric} Examples
:class: rubric-examples
:::
```python
<p>Total pages: {{ section.regular_pages_recursive | length }}</p>
```


---
#### `url`
```python
def url(self) -> str
```

Get the URL for this section (cached after first access).

Section URLs are stable after index pages have output_path set.
Caching eliminates redundant recalculation - previously this was
computed ~5× per page during health checks.



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

`str` - URL path for the section




---
#### `add_page`
```python
def add_page(self, page: Page) -> None
```

Add a page to this section.



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
* - `page`
  - `Page`
  - -
  - Page to add
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `add_subsection`
```python
def add_subsection(self, section: 'Section') -> None
```

Add a subsection to this section.



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
  - `'Section'`
  - -
  - Child section to add
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `sort_children_by_weight`
```python
def sort_children_by_weight(self) -> None
```

Sort pages and subsections in this section by weight, then by title.

This modifies the pages and subsections lists in place.
Pages/sections without a weight field are treated as having weight=float('inf'),
so they appear at the end (after all weighted items).
Lower weights appear first in the sorted lists.

This is typically called after content discovery is complete.



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

`None`




---
#### `needs_auto_index`
```python
def needs_auto_index(self) -> bool
```

Check if this section needs an auto-generated index page.



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

`bool` - True if section needs auto-generated index (no explicit _index.md)




---
#### `has_index`
```python
def has_index(self) -> bool
```

Check if section has a valid index page.



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

`bool` - True if section has an index page (explicit or auto-generated)




---
#### `get_all_pages`
```python
def get_all_pages(self, recursive: bool = True) -> list[Page]
```

Get all pages in this section.



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
* - `recursive`
  - `bool`
  - `True`
  - If True, include pages from subsections
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Page]` - List of all pages




---
#### `aggregate_content`
```python
def aggregate_content(self) -> dict[str, Any]
```

Aggregate content from all pages in this section.



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

`dict[str, Any]` - Dictionary with aggregated content information




---
#### `apply_section_template`
```python
def apply_section_template(self, template_engine: Any) -> str
```

Apply a section template to generate a section index page.



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
* - `template_engine`
  - `Any`
  - -
  - Template engine instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Rendered HTML for the section index




---
#### `walk`
```python
def walk(self) -> list['Section']
```

Iteratively walk through all sections in the hierarchy.



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

`list['Section']` - List of all sections (self and descendants)




---
#### `__hash__`
```python
def __hash__(self) -> int
```

Hash based on section path for stable identity.

The hash is computed from the section's path, which is immutable
throughout the section lifecycle. This allows sections to be stored
in sets and used as dictionary keys.



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

`int` - Integer hash of the section path




---
#### `__eq__`
```python
def __eq__(self, other: Any) -> bool
```

Sections are equal if they have the same path.

Equality is based on path only, not on pages or other mutable fields.
This means two Section objects representing the same directory are
considered equal, even if their contents differ.



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
  - `Any`
  - -
  - Object to compare with
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if other is a Section with the same path




---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



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

`str`




---


