---
title: "core.section"
layout: api-reference
type: python-module
source_file: "../../bengal/core/section.py"
---

# core.section

Section Object - Represents a folder or logical grouping of pages.

**Source:** `../../bengal/core/section.py`

---

## Classes

### Section


Represents a folder or logical grouping of pages.

Attributes:
    name: Section name
    path: Path to the section directory
    pages: List of pages in this section
    subsections: Child sections
    metadata: Section-level metadata
    index_page: Optional index page for the section
    parent: Parent section (if nested)

::: info
This is a dataclass.
:::

**Attributes:**

- **name** (`str`)- **path** (`Path`)- **pages** (`List[Page]`)- **subsections** (`List['Section']`)- **metadata** (`Dict[str, Any]`)- **index_page** (`Optional[Page]`)- **parent** (`Optional['Section']`)- **_site** (`Optional[Any]`)
**Properties:**

#### title

```python
@property
def title(self) -> str
```

Get section title from metadata or generate from name.
#### hierarchy

```python
@property
def hierarchy(self) -> List[str]
```

Get the full hierarchy path of this section.
#### depth

```python
@property
def depth(self) -> int
```

Get the depth of this section in the hierarchy.
#### regular_pages

```python
@property
def regular_pages(self) -> List[Page]
```

Get only regular pages (non-sections) in this section.
#### sections

```python
@property
def sections(self) -> List['Section']
```

Get immediate child sections.
#### regular_pages_recursive

```python
@property
def regular_pages_recursive(self) -> List[Page]
```

Get all regular pages recursively (including from subsections).
#### url

```python
@property
def url(self) -> str
```

Get the URL for this section.

**Methods:**

#### title

```python
def title(self) -> str
```

Get section title from metadata or generate from name.

**Parameters:**

- **self**

**Returns:** `str`






---
#### hierarchy

```python
def hierarchy(self) -> List[str]
```

Get the full hierarchy path of this section.

**Parameters:**

- **self**

**Returns:** `List[str]` - List of section names from root to this section






---
#### depth

```python
def depth(self) -> int
```

Get the depth of this section in the hierarchy.

**Parameters:**

- **self**

**Returns:** `int`






---
#### regular_pages

```python
def regular_pages(self) -> List[Page]
```

Get only regular pages (non-sections) in this section.

**Parameters:**

- **self**

**Returns:** `List[Page]` - List of regular Page objects (excludes subsections)


**Examples:**

{% for page in section.regular_pages %}





---
#### sections

```python
def sections(self) -> List['Section']
```

Get immediate child sections.

**Parameters:**

- **self**

**Returns:** `List['Section']` - List of child Section objects


**Examples:**

{% for subsection in section.sections %}





---
#### regular_pages_recursive

```python
def regular_pages_recursive(self) -> List[Page]
```

Get all regular pages recursively (including from subsections).

**Parameters:**

- **self**

**Returns:** `List[Page]` - List of all descendant regular pages


**Examples:**

<p>Total pages: {{ section.regular_pages_recursive | length }}</p>





---
#### url

```python
def url(self) -> str
```

Get the URL for this section.

**Parameters:**

- **self**

**Returns:** `str` - URL path for the section






---
#### add_page

```python
def add_page(self, page: Page) -> None
```

Add a page to this section.

**Parameters:**

- **self**
- **page** (`Page`) - Page to add

**Returns:** `None`






---
#### add_subsection

```python
def add_subsection(self, section: 'Section') -> None
```

Add a subsection to this section.

**Parameters:**

- **self**
- **section** (`'Section'`) - Child section to add

**Returns:** `None`






---
#### needs_auto_index

```python
def needs_auto_index(self) -> bool
```

Check if this section needs an auto-generated index page.

**Parameters:**

- **self**

**Returns:** `bool` - True if section needs auto-generated index (no explicit _index.md)






---
#### has_index

```python
def has_index(self) -> bool
```

Check if section has a valid index page.

**Parameters:**

- **self**

**Returns:** `bool` - True if section has an index page (explicit or auto-generated)






---
#### get_all_pages

```python
def get_all_pages(self, recursive: bool = True) -> List[Page]
```

Get all pages in this section.

**Parameters:**

- **self**
- **recursive** (`bool`) = `True` - If True, include pages from subsections

**Returns:** `List[Page]` - List of all pages






---
#### aggregate_content

```python
def aggregate_content(self) -> Dict[str, Any]
```

Aggregate content from all pages in this section.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]` - Dictionary with aggregated content information






---
#### apply_section_template

```python
def apply_section_template(self, template_engine: Any) -> str
```

Apply a section template to generate a section index page.

**Parameters:**

- **self**
- **template_engine** (`Any`) - Template engine instance

**Returns:** `str` - Rendered HTML for the section index






---
#### walk

```python
def walk(self) -> List['Section']
```

Iteratively walk through all sections in the hierarchy.

**Parameters:**

- **self**

**Returns:** `List['Section']` - List of all sections (self and descendants)






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


