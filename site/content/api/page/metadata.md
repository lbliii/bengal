
---
title: "page.metadata"
type: python-module
source_file: "bengal/core/page/metadata.py"
css_class: api-content
description: "Page Metadata Mixin - Basic properties and type checking."
---

# page.metadata

Page Metadata Mixin - Basic properties and type checking.

---

## Classes

### `PageMetadataMixin`


Mixin providing metadata properties and type checking for pages.

This mixin handles:
- Basic properties: title, date, slug, url
- Type checking: is_home, is_section, is_page, kind
- Simple metadata: description, draft, keywords
- TOC access: toc_items (lazy evaluation)



:::{rubric} Properties
:class: rubric-properties
:::
#### `title` @property

```python
@property
def title(self) -> str
```

Get page title from metadata or generate from filename.
#### `date` @property

```python
@property
def date(self) -> datetime | None
```

Get page date from metadata.

Uses bengal.utils.dates.parse_date for flexible date parsing.
#### `slug` @property

```python
@property
def slug(self) -> str
```

Get URL slug for the page.
#### `url` @property

```python
@property
def url(self) -> str
```

Get the URL path for the page (cached after first access).

Generates clean URLs from output paths, handling:
- Pretty URLs (about/index.html -> /about/)
- Index pages (docs/index.html -> /docs/)
- Root index (index.html -> /)
- Edge cases (missing site reference, invalid paths)

URLs are stable after output_path is set (during rendering phase),
so caching eliminates redundant recalculation during health checks
and template rendering.
#### `toc_items` @property

```python
@property
def toc_items(self) -> list[dict[str, Any]]
```

Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.

Important: This property does NOT cache empty results. This allows
toc_items to be accessed before parsing (during xref indexing) without
preventing extraction after parsing when page.toc is actually set.
#### `is_home` @property

```python
@property
def is_home(self) -> bool
```

Check if this page is the home page.
#### `is_section` @property

```python
@property
def is_section(self) -> bool
```

Check if this page is a section page.
#### `is_page` @property

```python
@property
def is_page(self) -> bool
```

Check if this is a regular page (not a section).
#### `kind` @property

```python
@property
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.
#### `description` @property

```python
@property
def description(self) -> str
```

Get page description from metadata.
#### `draft` @property

```python
@property
def draft(self) -> bool
```

Check if page is marked as draft.
#### `keywords` @property

```python
@property
def keywords(self) -> list[str]
```

Get page keywords from metadata.

:::{rubric} Methods
:class: rubric-methods
:::
#### `title`
```python
def title(self) -> str
```

Get page title from metadata or generate from filename.



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
#### `date`
```python
def date(self) -> datetime | None
```

Get page date from metadata.

Uses bengal.utils.dates.parse_date for flexible date parsing.



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

`datetime | None`




---
#### `slug`
```python
def slug(self) -> str
```

Get URL slug for the page.



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
#### `url`
```python
def url(self) -> str
```

Get the URL path for the page (cached after first access).

Generates clean URLs from output paths, handling:
- Pretty URLs (about/index.html -> /about/)
- Index pages (docs/index.html -> /docs/)
- Root index (index.html -> /)
- Edge cases (missing site reference, invalid paths)

URLs are stable after output_path is set (during rendering phase),
so caching eliminates redundant recalculation during health checks
and template rendering.



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

`str` - URL path with leading and trailing slashes




---
#### `toc_items`
```python
def toc_items(self) -> list[dict[str, Any]]
```

Get structured TOC data (lazy evaluation).

Only extracts TOC structure when accessed by templates, saving
HTMLParser overhead for pages that don't use toc_items.

Important: This property does NOT cache empty results. This allows
toc_items to be accessed before parsing (during xref indexing) without
preventing extraction after parsing when page.toc is actually set.



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

`list[dict[str, Any]]` - List of TOC items with id, title, and level




---
#### `is_home`
```python
def is_home(self) -> bool
```

Check if this page is the home page.



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

`bool` - True if this is the home page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.is_home %}
```


---
#### `is_section`
```python
def is_section(self) -> bool
```

Check if this page is a section page.



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

`bool` - True if this is a section (always False for Page, True for Section)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.is_section %}
```


---
#### `is_page`
```python
def is_page(self) -> bool
```

Check if this is a regular page (not a section).



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

`bool` - True if this is a regular page




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.is_page %}
```


---
#### `kind`
```python
def kind(self) -> str
```

Get the kind of page: 'home', 'section', or 'page'.



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

`str` - String indicating page kind




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page.kind == 'section' %}
```


---
#### `description`
```python
def description(self) -> str
```

Get page description from metadata.



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

`str` - Page description or empty string




---
#### `draft`
```python
def draft(self) -> bool
```

Check if page is marked as draft.



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

`bool` - True if page is a draft




---
#### `keywords`
```python
def keywords(self) -> list[str]
```

Get page keywords from metadata.



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

`list[str]` - List of keywords




---
