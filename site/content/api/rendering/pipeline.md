
---
title: "rendering.pipeline"
type: python-module
source_file: "bengal/rendering/pipeline.py"
css_class: api-content
description: "Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering."
---

# rendering.pipeline

Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.

---

## Classes

### `RenderingPipeline`


Coordinates the entire rendering process for content.

Pipeline stages:
1. Parse source content (Markdown, etc.)
2. Build Abstract Syntax Tree (AST)
3. Apply templates
4. Render output (HTML)
5. Write to output directory




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any, dependency_tracker: Any = None, quiet: bool = False, build_stats: Any = None, build_context: Any | None = None) -> None
```

Initialize the rendering pipeline.

Parser Selection:
    Reads from config in this order:
    1. config['markdown_engine'] (legacy)
    2. config['markdown']['parser'] (preferred)
    3. Default: 'mistune' (recommended for speed)

    Common values:
    - 'mistune': Fast parser, recommended for most sites (default)
    - 'python-markdown': Full-featured, slightly slower

Parser Caching:
    Uses thread-local caching via _get_thread_parser().
    Creates ONE parser per worker thread, cached for reuse.

    With max_workers=N:
    - First page in thread: creates parser (~10ms)
    - Subsequent pages: reuses cached parser (~0ms)
    - Total parsers = N (optimal)

Cross-Reference Support:
    If site has xref_index (built during discovery):
    - Enables [[link]] syntax in markdown
    - Enables automatic .md link resolution (future)
    - O(1) lookup performance



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 6 parameters (click to expand)
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
  - `Any`
  - -
  - Site instance with config and xref_index
* - `dependency_tracker`
  - `Any`
  - `None`
  - Optional tracker for incremental builds
* - `quiet`
  - `bool`
  - `False`
  - If True, suppress per-page output
* - `build_stats`
  - `Any`
  - `None`
  - Optional BuildStats object to collect warnings
* - `build_context`
  - `Any | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`


```{note}
Each worker thread creates its own RenderingPipeline instance. The parser is cached at thread level, not pipeline level.
```




---
#### `process_page`
```python
def process_page(self, page: Page) -> None
```

Process a single page through the entire pipeline.



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
  - Page to process
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


## Functions

### `extract_toc_structure`
```python
def extract_toc_structure(toc_html: str) -> list
```

Parse TOC HTML into structured data for custom rendering.

Handles both nested <ul> structures (python-markdown style) and flat lists (mistune style).
For flat lists from mistune, parses indentation to infer heading levels.

This is a standalone function so it can be called from Page.toc_items
property for lazy evaluation.



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
* - `toc_html`
  - `str`
  - -
  - HTML table of contents
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list` - List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)




---
