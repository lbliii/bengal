---
title: "utils.url_strategy"
layout: api-reference
type: python-module
source_file: "../../bengal/utils/url_strategy.py"
---

# utils.url_strategy

URL Strategy - Centralized URL and path computation.

Provides pure utility functions for computing output paths and URLs.
Used by orchestrators to ensure consistent path generation across the system.

**Source:** `../../bengal/utils/url_strategy.py`

---

## Classes

### URLStrategy


Pure utility for URL and output path computation.

Centralizes all path/URL logic to ensure consistency and prevent bugs.
All methods are static - no state, pure logic.

Design principles:
- Pure functions (no side effects)
- No dependencies on global state
- Easy to test in isolation
- Reusable across orchestrators




**Methods:**

#### compute_regular_page_output_path

```python
def compute_regular_page_output_path(page: 'Page', site: 'Site') -> Path
```

Compute output path for a regular content page.

**Parameters:**

- **page** (`'Page'`) - Page object (must have source_path set)
- **site** (`'Site'`) - Site object (for output_dir and config)

**Returns:** `Path` - Absolute path where the page HTML should be written


**Examples:**

content/about.md → public/about/index.html (pretty URLs)





---
#### compute_archive_output_path

```python
def compute_archive_output_path(section: 'Section', page_num: int, site: 'Site') -> Path
```

Compute output path for a section archive page.

**Parameters:**

- **section** (`'Section'`) - Section to create archive for
- **page_num** (`int`) - Page number (1 for first page, 2+ for pagination)
- **site** (`'Site'`) - Site object (for output_dir)

**Returns:** `Path` - Absolute path where the archive HTML should be written


**Examples:**

section='docs', page=1 → public/docs/index.html





---
#### compute_tag_output_path

```python
def compute_tag_output_path(tag_slug: str, page_num: int, site: 'Site') -> Path
```

Compute output path for a tag listing page.

**Parameters:**

- **tag_slug** (`str`) - URL-safe tag identifier
- **page_num** (`int`) - Page number (1 for first page, 2+ for pagination)
- **site** (`'Site'`) - Site object (for output_dir)

**Returns:** `Path` - Absolute path where the tag page HTML should be written


**Examples:**

tag='python', page=1 → public/tags/python/index.html





---
#### compute_tag_index_output_path

```python
def compute_tag_index_output_path(site: 'Site') -> Path
```

Compute output path for the main tags index page.

**Parameters:**

- **site** (`'Site'`) - Site object (for output_dir)

**Returns:** `Path` - Absolute path where the tags index HTML should be written


**Examples:**

public/tags/index.html





---
#### url_from_output_path

```python
def url_from_output_path(output_path: Path, site: 'Site') -> str
```

Generate clean URL from output path.

**Parameters:**

- **output_path** (`Path`) - Absolute path to output file
- **site** (`'Site'`) - Site object (for output_dir)

**Returns:** `str` - Clean URL with leading/trailing slashes

**Raises:**

- **ValueError**: If output_path is not under site.output_dir

**Examples:**

public/about/index.html → /about/





---
#### make_virtual_path

```python
def make_virtual_path(site: 'Site', *parts: str) -> Path
```

Create virtual source path for generated pages.

Generated pages (archives, tags, etc.) don't have real source files.
This creates a virtual path under .bengal/generated/ for tracking.

**Parameters:**

- **site** (`'Site'`) - Site object (for root_path) *parts: Path components

**Returns:** `Path` - Virtual path under .bengal/generated/


**Examples:**

make_virtual_path(site, 'archives', 'docs')





---


