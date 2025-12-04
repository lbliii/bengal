
---
title: "section"
type: "python-module"
source_file: "bengal/bengal/core/section.py"
line_number: 1
description: "Section representation for organizing pages into hierarchical groups. Sections represent directories in the content tree and provide navigation, sorting, and hierarchical query interfaces. Sections ca..."
---

# section
**Type:** Module
**Source:** [View source](bengal/bengal/core/section.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›section

Section representation for organizing pages into hierarchical groups.

Sections represent directories in the content tree and provide navigation,
sorting, and hierarchical query interfaces. Sections can be nested and
maintain parent-child relationships. Each section can have an index page
and contains both regular pages and subsections.

Key Concepts:
    - Hierarchy: Sections form a tree structure with parent-child relationships
    - Index pages: Special pages (_index.md or index.md) that represent the section
    - Weight-based sorting: Pages and subsections sorted by weight metadata
    - Hashability: Sections are hashable by path for set operations

Related Modules:
    - bengal.core.page: Page objects contained within sections
    - bengal.core.site: Site container that manages all sections
    - bengal.orchestration.content: Content discovery that builds section hierarchy

See Also:
    - bengal/core/section.py:Section class for section representation

## Classes




### `WeightedPage`


*No class description provided.*


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `page` | - | *No description provided.* |
| `weight` | - | *No description provided.* |
| `title_lower` | - | *No description provided.* |







## Methods



#### `__lt__`
```python
def __lt__(self, other)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `other` | - | - | *No description provided.* |




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


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | Section name |
| `path` | - | Path to the section directory |
| `pages` | - | List of pages in this section |
| `subsections` | - | Child sections |
| `metadata` | - | Section-level metadata |
| `index_page` | - | Optional index page for the section |
| `parent` | - | Parent section (if nested) |
| `_site` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `title` @property

```python
def title(self) -> str
```
Get section title from metadata or generate from name.

#### `hierarchy` @property

```python
def hierarchy(self) -> list[str]
```
Get the full hierarchy path of this section.

#### `depth` @property

```python
def depth(self) -> int
```
Get the depth of this section in the hierarchy.

#### `root` @property

```python
def root(self) -> Section
```
Get the root section of this section's hierarchy.

#### `regular_pages` @property

```python
def regular_pages(self) -> list[Page]
```
Get only regular pages (non-sections) in this section.

#### `sections` @property

```python
def sections(self) -> list[Section]
```
Get immediate child sections.

#### `sorted_pages` @property

```python
def sorted_pages(self) -> list[Page]
```
Get pages sorted by weight (ascending), then by title (CACHED).

This property is cached after first access for O(1) subsequent lookups.
The sort is computed once and reused across all template renders.

Pages without a weight field are treated as having weight=float('inf')
and appear at the end of the sorted list, after all weighted pages.
Lower weights appear first in the list. Pages with equal weight are sorted
alphabetically by title.

Performance:
    - First access: O(n log n) where n = number of pages
    - Subsequent accesses: O(1) cached lookup
    - Memory cost: O(n) to store sorted list

#### `sorted_subsections` @property

```python
def sorted_subsections(self) -> list[Section]
```
Get subsections sorted by weight (ascending), then by title (CACHED).

This property is cached after first access for O(1) subsequent lookups.
The sort is computed once and reused across all template renders.

Subsections without a weight field in their index page metadata
are treated as having weight=999999 (appear at end). Lower weights appear first.

Performance:
    - First access: O(m log m) where m = number of subsections
    - Subsequent accesses: O(1) cached lookup
    - Memory cost: O(m) to store sorted list

#### `subsection_index_urls` @property

```python
def subsection_index_urls(self) -> set[str]
```
Get set of URLs for all subsection index pages (CACHED).

This pre-computed set enables O(1) membership checks for determining
if a page is a subsection index. Used in navigation templates to avoid
showing subsection indices twice (once as page, once as subsection link).

Performance:
    - First access: O(m) where m = number of subsections
    - Subsequent lookups: O(1) set membership check
    - Memory cost: O(m) URLs

#### `has_nav_children` @property

```python
def has_nav_children(self) -> bool
```
Check if this section has navigable children (CACHED).

A section has navigable children if it contains either:
- Regular pages (excluding the index page itself)
- Subsections

This property is used by navigation templates to determine whether
to render a section as an expandable group (with toggle button) or
as a simple link. Sections without children should not show an
expand/collapse toggle since there's nothing to expand.

Performance:
    - First access: O(1) - uses cached sorted_pages/sorted_subsections
    - Subsequent accesses: O(1) cached lookup

#### `regular_pages_recursive` @property

```python
def regular_pages_recursive(self) -> list[Page]
```
Get all regular pages recursively (including from subsections).

#### `relative_url` @property

```python
def relative_url(self) -> str
```
Get relative URL without baseurl (for comparisons).

This is the identity URL - use for comparisons, menu activation, etc.
Always returns a relative path without baseurl.

#### `url` @property

```python
def url(self) -> str
```
Get URL with baseurl applied (cached after first access).

This is the primary URL property for templates - automatically includes
baseurl when available. Use .relative_url for comparisons.

#### `permalink` @property

```python
def permalink(self) -> str
```
Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
Use .relative_url for comparisons.




## Methods



#### `title`
```python
def title(self) -> str
```


Get section title from metadata or generate from name.



**Returns**


`str`



#### `hierarchy`
```python
def hierarchy(self) -> list[str]
```


Get the full hierarchy path of this section.



**Returns**


`list[str]` - List of section names from root to this section



#### `depth`
```python
def depth(self) -> int
```


Get the depth of this section in the hierarchy.



**Returns**


`int`



#### `root`
```python
def root(self) -> Section
```


Get the root section of this section's hierarchy.



**Returns**


`Section` - The topmost ancestor section
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set root_section = page._section.root %}
```




#### `regular_pages`
```python
def regular_pages(self) -> list[Page]
```


Get only regular pages (non-sections) in this section.



**Returns**


`list[Page]` - List of regular Page objects (excludes subsections)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for page in section.regular_pages %}
      <article>{{ page.title }}</article>
    {% endfor %}
```




#### `sections`
```python
def sections(self) -> list[Section]
```


Get immediate child sections.



**Returns**


`list[Section]` - List of child Section objects
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for subsection in section.sections %}
      <h3>{{ subsection.title }}</h3>
    {% endfor %}
```




#### `sorted_pages`
```python
def sorted_pages(self) -> list[Page]
```


Get pages sorted by weight (ascending), then by title (CACHED).

This property is cached after first access for O(1) subsequent lookups.
The sort is computed once and reused across all template renders.

Pages without a weight field are treated as having weight=float('inf')
and appear at the end of the sorted list, after all weighted pages.
Lower weights appear first in the list. Pages with equal weight are sorted
alphabetically by title.

Performance:
    - First access: O(n log n) where n = number of pages
    - Subsequent accesses: O(1) cached lookup
    - Memory cost: O(n) to store sorted list



**Returns**


`list[Page]` - List of pages sorted by weight, then title
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for page in section.sorted_pages %}
      <article>{{ page.title }}</article>
    {% endfor %}
```




#### `sorted_subsections`
```python
def sorted_subsections(self) -> list[Section]
```


Get subsections sorted by weight (ascending), then by title (CACHED).

This property is cached after first access for O(1) subsequent lookups.
The sort is computed once and reused across all template renders.

Subsections without a weight field in their index page metadata
are treated as having weight=999999 (appear at end). Lower weights appear first.

Performance:
    - First access: O(m log m) where m = number of subsections
    - Subsequent accesses: O(1) cached lookup
    - Memory cost: O(m) to store sorted list



**Returns**


`list[Section]` - List of subsections sorted by weight, then title
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for subsection in section.sorted_subsections %}
      <h3>{{ subsection.title }}</h3>
    {% endfor %}
```




#### `subsection_index_urls`
```python
def subsection_index_urls(self) -> set[str]
```


Get set of URLs for all subsection index pages (CACHED).

This pre-computed set enables O(1) membership checks for determining
if a page is a subsection index. Used in navigation templates to avoid
showing subsection indices twice (once as page, once as subsection link).

Performance:
    - First access: O(m) where m = number of subsections
    - Subsequent lookups: O(1) set membership check
    - Memory cost: O(m) URLs



**Returns**


`set[str]` - Set of URL strings for subsection index pages
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if page.relative_url not in section.subsection_index_urls %}
      <a href="{{ url_for(page) }}">{{ page.title }}</a>
    {% endif %}
```




#### `has_nav_children`
```python
def has_nav_children(self) -> bool
```


Check if this section has navigable children (CACHED).

A section has navigable children if it contains either:
- Regular pages (excluding the index page itself)
- Subsections

This property is used by navigation templates to determine whether
to render a section as an expandable group (with toggle button) or
as a simple link. Sections without children should not show an
expand/collapse toggle since there's nothing to expand.

Performance:
    - First access: O(1) - uses cached sorted_pages/sorted_subsections
    - Subsequent accesses: O(1) cached lookup



**Returns**


`bool` - True if section has pages or subsections to display in nav
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if section.has_nav_children %}
      {# Render as expandable group with toggle #}
    {% else %}
      {# Render as simple link #}
    {% endif %}
```




#### `regular_pages_recursive`
```python
def regular_pages_recursive(self) -> list[Page]
```


Get all regular pages recursively (including from subsections).



**Returns**


`list[Page]` - List of all descendant regular pages
:::{rubric} Examples
:class: rubric-examples
:::


```python
<p>Total pages: {{ section.regular_pages_recursive | length }}</p>
```




#### `relative_url`
```python
def relative_url(self) -> str
```


Get relative URL without baseurl (for comparisons).

This is the identity URL - use for comparisons, menu activation, etc.
Always returns a relative path without baseurl.



**Returns**


`str`



#### `url`
```python
def url(self) -> str
```


Get URL with baseurl applied (cached after first access).

This is the primary URL property for templates - automatically includes
baseurl when available. Use .relative_url for comparisons.



**Returns**


`str` - URL path with baseurl prepended (if configured)



#### `permalink`
```python
def permalink(self) -> str
```


Alias for url (for backward compatibility).

Both url and permalink now return the same value (with baseurl).
Use .relative_url for comparisons.



**Returns**


`str`



#### `add_page`
```python
def add_page(self, page: Page) -> None
```


Add a page to this section.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to add |







**Returns**


`None`



#### `add_subsection`
```python
def add_subsection(self, section: Section) -> None
```


Add a subsection to this section.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | Child section to add |







**Returns**


`None`



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



**Returns**


`None`



#### `needs_auto_index`
```python
def needs_auto_index(self) -> bool
```


Check if this section needs an auto-generated index page.



**Returns**


`bool` - True if section needs auto-generated index (no explicit _index.md)



#### `has_index`
```python
def has_index(self) -> bool
```


Check if section has a valid index page.



**Returns**


`bool` - True if section has an index page (explicit or auto-generated)



#### `get_all_pages`
```python
def get_all_pages(self, recursive: bool = True) -> list[Page]
```


Get all pages in this section.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `recursive` | `bool` | `True` | If True, include pages from subsections |







**Returns**


`list[Page]` - List of all pages



#### `aggregate_content`
```python
def aggregate_content(self) -> dict[str, Any]
```


Aggregate content from all pages in this section.



**Returns**


`dict[str, Any]` - Dictionary with aggregated content information



#### `apply_section_template`
```python
def apply_section_template(self, template_engine: Any) -> str
```


Apply a section template to generate a section index page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_engine` | `Any` | - | Template engine instance |







**Returns**


`str` - Rendered HTML for the section index



#### `walk`
```python
def walk(self) -> list[Section]
```


Iteratively walk through all sections in the hierarchy.



**Returns**


`list[Section]` - List of all sections (self and descendants)



#### `__hash__`
```python
def __hash__(self) -> int
```


Hash based on section path for stable identity.

The hash is computed from the section's path, which is immutable
throughout the section lifecycle. This allows sections to be stored
in sets and used as dictionary keys.



**Returns**


`int` - Integer hash of the section path



#### `__eq__`
```python
def __eq__(self, other: Any) -> bool
```


Sections are equal if they have the same path.

Equality is based on path only, not on pages or other mutable fields.
This means two Section objects representing the same directory are
considered equal, even if their contents differ.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `other` | `Any` | - | Object to compare with |







**Returns**


`bool` - True if other is a Section with the same path



#### `__repr__`
```python
def __repr__(self) -> str
```


*No description provided.*



**Returns**


`str`



---
*Generated by Bengal autodoc from `bengal/bengal/core/section.py`*
