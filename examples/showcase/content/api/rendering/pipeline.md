---
title: "rendering.pipeline"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/pipeline.py"
---

# rendering.pipeline

Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.

**Source:** `../../bengal/rendering/pipeline.py`

---

## Classes

### RenderingPipeline


Coordinates the entire rendering process for content.

Pipeline stages:
1. Parse source content (Markdown, etc.)
2. Build Abstract Syntax Tree (AST)
3. Apply templates
4. Render output (HTML)
5. Write to output directory




**Methods:**

#### __init__

```python
def __init__(self, site: Any, dependency_tracker: Any = None, quiet: bool = False, build_stats: Any = None) -> None
```

Initialize the rendering pipeline.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance
- **dependency_tracker** (`Any`) = `None` - Optional dependency tracker for incremental builds
- **quiet** (`bool`) = `False` - If True, suppress per-page output
- **build_stats** (`Any`) = `None` - Optional BuildStats object to collect warnings

**Returns:** `None`






---
#### process_page

```python
def process_page(self, page: Page) -> None
```

Process a single page through the entire pipeline.

**Parameters:**

- **self**
- **page** (`Page`) - Page to process

**Returns:** `None`






---


## Functions

### extract_toc_structure

```python
def extract_toc_structure(toc_html: str) -> list
```

Parse TOC HTML into structured data for custom rendering.

This is a standalone function so it can be called from Page.toc_items
property for lazy evaluation.

**Parameters:**

- **toc_html** (`str`) - HTML table of contents

**Returns:** `list` - List of TOC items with id, title, and level





---
