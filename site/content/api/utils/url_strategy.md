
---
title: "utils.url_strategy"
type: python-module
source_file: "bengal/utils/url_strategy.py"
css_class: api-content
description: "URL Strategy - Centralized URL and path computation.  Provides pure utility functions for computing output paths and URLs. Used by orchestrators to ensure consistent path generation across the system."
---

# utils.url_strategy

URL Strategy - Centralized URL and path computation.

Provides pure utility functions for computing output paths and URLs.
Used by orchestrators to ensure consistent path generation across the system.

---

## Classes

### `URLStrategy`


Pure utility for URL and output path computation.

Centralizes all path/URL logic to ensure consistency and prevent bugs.
All methods are static - no state, pure logic.

Design principles:
- Pure functions (no side effects)
- No dependencies on global state
- Easy to test in isolation
- Reusable across orchestrators




:::{rubric} Methods
:class: rubric-methods
:::
#### `compute_regular_page_output_path` @staticmethod
```python
def compute_regular_page_output_path(page: 'Page', site: 'Site', pre_cascade: bool = False) -> Path
```

Compute output path for a regular content page.



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
* - `page`
  - `'Page'`
  - -
  - Page object (must have source_path set)
* - `site`
  - `'Site'`
  - -
  - Site object (for output_dir and config)
* - `pre_cascade`
  - `bool`
  - `False`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Absolute path where the page HTML should be written




:::{rubric} Examples
:class: rubric-examples
:::
```python
content/about.md → public/about/index.html (pretty URLs)
```


---
#### `compute_archive_output_path` @staticmethod
```python
def compute_archive_output_path(section: 'Section', page_num: int, site: 'Site') -> Path
```

Compute output path for a section archive page.



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
* - `section`
  - `'Section'`
  - -
  - Section to create archive for
* - `page_num`
  - `int`
  - -
  - Page number (1 for first page, 2+ for pagination)
* - `site`
  - `'Site'`
  - -
  - Site object (for output_dir)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Absolute path where the archive HTML should be written




:::{rubric} Examples
:class: rubric-examples
:::
```python
section='docs', page=1 → public/docs/index.html
```


---
#### `compute_tag_output_path` @staticmethod
```python
def compute_tag_output_path(tag_slug: str, page_num: int, site: 'Site') -> Path
```

Compute output path for a tag listing page.



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
* - `tag_slug`
  - `str`
  - -
  - URL-safe tag identifier
* - `page_num`
  - `int`
  - -
  - Page number (1 for first page, 2+ for pagination)
* - `site`
  - `'Site'`
  - -
  - Site object (for output_dir)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Absolute path where the tag page HTML should be written




:::{rubric} Examples
:class: rubric-examples
:::
```python
tag='python', page=1 → public/tags/python/index.html
```


---
#### `compute_tag_index_output_path` @staticmethod
```python
def compute_tag_index_output_path(site: 'Site') -> Path
```

Compute output path for the main tags index page.



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
* - `site`
  - `'Site'`
  - -
  - Site object (for output_dir)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Absolute path where the tags index HTML should be written




:::{rubric} Examples
:class: rubric-examples
:::
```python
public/tags/index.html
```


---
#### `url_from_output_path` @staticmethod
```python
def url_from_output_path(output_path: Path, site: 'Site') -> str
```

Generate clean URL from output path.



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
* - `output_path`
  - `Path`
  - -
  - Absolute path to output file
* - `site`
  - `'Site'`
  - -
  - Site object (for output_dir)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Clean URL with leading/trailing slashes

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If output_path is not under site.output_dir



:::{rubric} Examples
:class: rubric-examples
:::
```python
public/about/index.html → /about/
```


---
#### `make_virtual_path` @staticmethod
```python
def make_virtual_path(site: 'Site', *parts: str) -> Path
```

Create virtual source path for generated pages.

Generated pages (archives, tags, etc.) don't have real source files.
This creates a virtual path under .bengal/generated/ for tracking.



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
* - `site`
  - `'Site'`
  - -
  - Site object (for root_path) *parts: Path components
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Virtual path under .bengal/generated/




:::{rubric} Examples
:class: rubric-examples
:::
```python
make_virtual_path(site, 'archives', 'docs')
```


---
