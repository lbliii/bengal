---
title: "core.page"
layout: api-reference
type: python-module
source_file: "../../bengal/core/page.py"
---

# core.page

Page Object - Represents a single content page.

**Source:** `../../bengal/core/page.py`

---

## Classes

### Page


Represents a single content page.

Attributes:
    source_path: Path to the source content file
    content: Raw content (Markdown, etc.)
    metadata: Frontmatter metadata (title, date, tags, etc.)
    parsed_ast: Abstract Syntax Tree from parsed content
    rendered_html: Rendered HTML output
    output_path: Path where the rendered page will be written
    links: List of links found in the page
    tags: Tags associated with the page
    version: Version information for versioned content
    toc: Table of contents HTML (auto-generated from headings)
    toc_items: Structured TOC data for custom rendering

::: info
This is a dataclass.
:::

**Attributes:**

- **source_path** (`Path`)- **content** (`str`)- **metadata** (`Dict[str, Any]`)- **parsed_ast** (`Optional[Any]`)- **rendered_html** (`str`)- **output_path** (`Optional[Path]`)- **links** (`List[str]`)- **tags** (`List[str]`)- **version** (`Optional[str]`)- **toc** (`Optional[str]`)- **_site** (`Optional[Any]`)- **_section** (`Optional[Any]`)- **_toc_items_cache** (`Optional[List[Dict[str, Any]]]`)
**Properties:**

#### title

```python
@property
def title(self) -> str
```

Get page title from metadata or generate from filename.
#### date

```python
@property
def date(self) -> Optional[datetime]
```

Get page date from metadata.
#### slug

```python
@property
def slug(self) -> str
```

Get URL slug for the page.
#### url

```python
@property
def url(self) -> str
```

Get the URL path for the page.

Generates clean URLs from output paths, handling:
- Pretty URLs (about/index.html -> /about/)
- Index pages (docs/index.html -> /docs/)
- Root index (index.html -> /)
- Edge cases (missing site reference, invalid paths)
#### toc_items

```python
@property
def toc_items(self) -> List[Dict[str, Any]]
```

Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.
#### next

```python
@property
def next(self) -> Optional['Page']
```

Get the next page in the site's collection of pages.
#### prev

```python
@property
def prev(self) -> Optional['Page']
```

Get the previous page in the site's collection of pages.
#### next_in_section

```python
@property
def next_in_section(self) -> Optional['Page']
```

Get the next page within the same section.
#### prev_in_section

```python
@property
def prev_in_section(self) -> Optional['Page']
```

Get the previous page within the same section.
#### parent

```python
@property
def parent(self) -> Optional[Any]
```

Get the parent section of this page.
#### ancestors

```python
@property
def ancestors(self) -> List[Any]
```

Get all ancestor sections of this page.
#### is_home

```python
@property
def is_home(self) -> bool
```

Check if this page is the home page.
#### is_section

```python
@property
def is_section(self) -> bool
```

Check if this page is a section page.
#### is_page

```python
@property
def is_page(self) -> bool
```

Check if this is a regular page (not a section).
#### kind

```python
@property
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.
#### description

```python
@property
def description(self) -> str
```

Get page description from metadata.
#### draft

```python
@property
def draft(self) -> bool
```

Check if page is marked as draft.
#### keywords

```python
@property
def keywords(self) -> List[str]
```

Get page keywords from metadata.

**Methods:**

#### title

```python
def title(self) -> str
```

Get page title from metadata or generate from filename.

**Parameters:**

- **self**

**Returns:** `str`






---
#### date

```python
def date(self) -> Optional[datetime]
```

Get page date from metadata.

**Parameters:**

- **self**

**Returns:** `Optional[datetime]`






---
#### slug

```python
def slug(self) -> str
```

Get URL slug for the page.

**Parameters:**

- **self**

**Returns:** `str`






---
#### url

```python
def url(self) -> str
```

Get the URL path for the page.

Generates clean URLs from output paths, handling:
- Pretty URLs (about/index.html -> /about/)
- Index pages (docs/index.html -> /docs/)
- Root index (index.html -> /)
- Edge cases (missing site reference, invalid paths)

**Parameters:**

- **self**

**Returns:** `str` - URL path with leading and trailing slashes






---
#### toc_items

```python
def toc_items(self) -> List[Dict[str, Any]]
```

Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.

**Parameters:**

- **self**

**Returns:** `List[Dict[str, Any]]` - List of TOC items with id, title, and level






---
#### next

```python
def next(self) -> Optional['Page']
```

Get the next page in the site's collection of pages.

**Parameters:**

- **self**

**Returns:** `Optional['Page']` - Next page or None if this is the last page


**Examples:**

{% if page.next %}





---
#### prev

```python
def prev(self) -> Optional['Page']
```

Get the previous page in the site's collection of pages.

**Parameters:**

- **self**

**Returns:** `Optional['Page']` - Previous page or None if this is the first page


**Examples:**

{% if page.prev %}





---
#### next_in_section

```python
def next_in_section(self) -> Optional['Page']
```

Get the next page within the same section.

**Parameters:**

- **self**

**Returns:** `Optional['Page']` - Next page in section or None


**Examples:**

{% if page.next_in_section %}





---
#### prev_in_section

```python
def prev_in_section(self) -> Optional['Page']
```

Get the previous page within the same section.

**Parameters:**

- **self**

**Returns:** `Optional['Page']` - Previous page in section or None


**Examples:**

{% if page.prev_in_section %}





---
#### parent

```python
def parent(self) -> Optional[Any]
```

Get the parent section of this page.

**Parameters:**

- **self**

**Returns:** `Optional[Any]` - Parent section or None


**Examples:**

{% if page.parent %}





---
#### ancestors

```python
def ancestors(self) -> List[Any]
```

Get all ancestor sections of this page.

**Parameters:**

- **self**

**Returns:** `List[Any]` - List of ancestor sections from immediate parent to root


**Examples:**

{% for ancestor in page.ancestors | reverse %}





---
#### is_home

```python
def is_home(self) -> bool
```

Check if this page is the home page.

**Parameters:**

- **self**

**Returns:** `bool` - True if this is the home page


**Examples:**

{% if page.is_home %}





---
#### is_section

```python
def is_section(self) -> bool
```

Check if this page is a section page.

**Parameters:**

- **self**

**Returns:** `bool` - True if this is a section (always False for Page, True for Section)


**Examples:**

{% if page.is_section %}





---
#### is_page

```python
def is_page(self) -> bool
```

Check if this is a regular page (not a section).

**Parameters:**

- **self**

**Returns:** `bool` - True if this is a regular page


**Examples:**

{% if page.is_page %}





---
#### kind

```python
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.

**Parameters:**

- **self**

**Returns:** `str` - String indicating page kind


**Examples:**

{% if page.kind == 'section' %}





---
#### description

```python
def description(self) -> str
```

Get page description from metadata.

**Parameters:**

- **self**

**Returns:** `str` - Page description or empty string






---
#### draft

```python
def draft(self) -> bool
```

Check if page is marked as draft.

**Parameters:**

- **self**

**Returns:** `bool` - True if page is a draft






---
#### keywords

```python
def keywords(self) -> List[str]
```

Get page keywords from metadata.

**Parameters:**

- **self**

**Returns:** `List[str]` - List of keywords






---
#### __post_init__

```python
def __post_init__(self) -> None
```

Initialize computed fields.

**Parameters:**

- **self**

**Returns:** `None`






---
#### eq

```python
def eq(self, other: 'Page') -> bool
```

Check if two pages are equal.

**Parameters:**

- **self**
- **other** (`'Page'`) - Page to compare with

**Returns:** `bool` - True if pages are the same


**Examples:**

{% if page.eq(other_page) %}





---
#### in_section

```python
def in_section(self, section: Any) -> bool
```

Check if this page is in the given section.

**Parameters:**

- **self**
- **section** (`Any`) - Section to check

**Returns:** `bool` - True if page is in the section


**Examples:**

{% if page.in_section(blog_section) %}





---
#### is_ancestor

```python
def is_ancestor(self, other: 'Page') -> bool
```

Check if this page is an ancestor of another page.

**Parameters:**

- **self**
- **other** (`'Page'`) - Page to check

**Returns:** `bool` - True if this page is an ancestor


**Examples:**

{% if section.is_ancestor(page) %}





---
#### is_descendant

```python
def is_descendant(self, other: 'Page') -> bool
```

Check if this page is a descendant of another page.

**Parameters:**

- **self**
- **other** (`'Page'`) - Page to check

**Returns:** `bool` - True if this page is a descendant


**Examples:**

{% if page.is_descendant(section) %}





---
#### render

```python
def render(self, template_engine: Any) -> str
```

Render the page using the provided template engine.

**Parameters:**

- **self**
- **template_engine** (`Any`) - Template engine instance

**Returns:** `str` - Rendered HTML content






---
#### validate_links

```python
def validate_links(self) -> List[str]
```

Validate all links in the page.

**Parameters:**

- **self**

**Returns:** `List[str]` - List of broken link URLs






---
#### apply_template

```python
def apply_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str
```

Apply a specific template to this page.

**Parameters:**

- **self**
- **template_name** (`str`) - Name of the template to apply
- **context** (`Optional[Dict[str, Any]]`) = `None` - Additional context variables

**Returns:** `str` - Rendered content with template applied






---
#### extract_links

```python
def extract_links(self) -> List[str]
```

Extract all links from the page content.

**Parameters:**

- **self**

**Returns:** `List[str]` - List of link URLs found in the page






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


