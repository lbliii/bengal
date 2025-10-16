
---
title: "utils.page_initializer"
type: python-module
source_file: "bengal/utils/page_initializer.py"
css_class: api-content
description: "Page Initializer - Ensures pages are correctly initialized.  Validates that pages have all required references set before use. Helps prevent bugs like missing _site references or output_paths."
---

# utils.page_initializer

Page Initializer - Ensures pages are correctly initialized.

Validates that pages have all required references set before use.
Helps prevent bugs like missing _site references or output_paths.

---

## Classes

### `PageInitializer`


Ensures pages are correctly initialized with all required references.

Used by orchestrators after creating pages to validate they're ready for use.

Design principles:
- Fail fast (errors at initialization, not at URL generation)
- Clear error messages (tell developer exactly what's wrong)
- Single responsibility (just validation, not creation)
- Lightweight (minimal logic, mostly checks)

Usage:
    # In an orchestrator
    def __init__(self, site):
        self.initializer = PageInitializer(site)

    def create_my_page(self):
        page = Page(...)
        page.output_path = compute_path(...)
        self.initializer.ensure_initialized(page)  # Validate!
        return page




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Site)
```

Initialize the page initializer.



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
* - `site`
  - `Site`
  - -
  - Site object to associate with pages
:::

::::




---
#### `ensure_initialized`
```python
def ensure_initialized(self, page: Page) -> None
```

Ensure a page is correctly initialized.

Checks:
1. Page has _site reference (or sets it)
2. Page has output_path set
3. Page URL generation works



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
  - Page to validate and initialize
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If page is missing required attributes or URL generation fails



---
#### `ensure_initialized_for_section`
```python
def ensure_initialized_for_section(self, page: Page, section: Section) -> None
```

Ensure a page is initialized with section reference.

Like ensure_initialized() but also sets and validates the section reference.
Used for archive pages and section index pages.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
  - Page to validate and initialize
* - `section`
  - `Section`
  - -
  - Section this page belongs to
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If page is missing required attributes or validation fails



---


