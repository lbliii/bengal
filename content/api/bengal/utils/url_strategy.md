
---
title: "url_strategy"
type: "python-module"
source_file: "bengal/bengal/utils/url_strategy.py"
line_number: 1
description: "URL Strategy - Centralized URL and path computation. Provides pure utility functions for computing output paths and URLs. Used by orchestrators to ensure consistent path generation across the system."
---

# url_strategy
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/utils/url_strategy.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›url_strategy

URL Strategy - Centralized URL and path computation.

Provides pure utility functions for computing output paths and URLs.
Used by orchestrators to ensure consistent path generation across the system.

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









## Methods



#### `compute_regular_page_output_path` @staticmethod
```python
def compute_regular_page_output_path(page: Page, site: Site, pre_cascade: bool = False) -> Path
```


Compute output path for a regular content page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page object (must have source_path set) |
| `site` | `Site` | - | Site object (for output_dir and config) |
| `pre_cascade` | `bool` | `False` | *No description provided.* |







**Returns**


`Path` - Absolute path where the page HTML should be written
:::{rubric} Examples
:class: rubric-examples
:::


```python
content/about.md → public/about/index.html (pretty URLs)
    content/blog/post.md → public/blog/post/index.html
    content/docs/_index.md → public/docs/index.html
```




#### `compute_archive_output_path` @staticmethod
```python
def compute_archive_output_path(section: Section, page_num: int, site: Site) -> Path
```


Compute output path for a section archive page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | Section to create archive for |
| `page_num` | `int` | - | Page number (1 for first page, 2+ for pagination) |
| `site` | `Site` | - | Site object (for output_dir) |







**Returns**


`Path` - Absolute path where the archive HTML should be written
:::{rubric} Examples
:class: rubric-examples
:::


```python
section='docs', page=1 → public/docs/index.html
    section='docs', page=2 → public/docs/page/2/index.html
    section='docs/markdown', page=1 → public/docs/markdown/index.html
```




#### `compute_tag_output_path` @staticmethod
```python
def compute_tag_output_path(tag_slug: str, page_num: int, site: Site) -> Path
```


Compute output path for a tag listing page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | URL-safe tag identifier |
| `page_num` | `int` | - | Page number (1 for first page, 2+ for pagination) |
| `site` | `Site` | - | Site object (for output_dir) |







**Returns**


`Path` - Absolute path where the tag page HTML should be written
:::{rubric} Examples
:class: rubric-examples
:::


```python
tag='python', page=1 → public/tags/python/index.html
    tag='python', page=2 → public/tags/python/page/2/index.html
```




#### `compute_tag_index_output_path` @staticmethod
```python
def compute_tag_index_output_path(site: Site) -> Path
```


Compute output path for the main tags index page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | Site object (for output_dir) |







**Returns**


`Path` - Absolute path where the tags index HTML should be written
:::{rubric} Examples
:class: rubric-examples
:::


```python
public/tags/index.html
```




#### `url_from_output_path` @staticmethod
```python
def url_from_output_path(output_path: Path, site: Site) -> str
```


Generate clean URL from output path.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_path` | `Path` | - | Absolute path to output file |
| `site` | `Site` | - | Site object (for output_dir) |







**Returns**


`str` - Clean URL with leading/trailing slashes
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If output_path is not under site.output_dir

:::{rubric} Examples
:class: rubric-examples
:::


```python
public/about/index.html → /about/
    public/docs/guide.html → /docs/guide/
    public/index.html → /
```




#### `make_virtual_path` @staticmethod
```python
def make_virtual_path(site: Site, *parts: str) -> Path
```


Create virtual source path for generated pages.

Generated pages (archives, tags, etc.) don't have real source files.
This creates a virtual path under .bengal/generated/ for tracking.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | Site object (for root_path) *parts: Path components |







**Returns**


`Path` - Virtual path under .bengal/generated/
:::{rubric} Examples
:class: rubric-examples
:::


```python
make_virtual_path(site, 'archives', 'docs')
    → /path/to/site/.bengal/generated/archives/docs/index.md

    make_virtual_path(site, 'tags', 'python')
    → /path/to/site/.bengal/generated/tags/python/index.md
```



---
*Generated by Bengal autodoc from `bengal/bengal/utils/url_strategy.py`*

