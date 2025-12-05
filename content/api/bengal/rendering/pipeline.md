
---
title: "pipeline"
type: "python-module"
source_file: "bengal/bengal/rendering/pipeline.py"
line_number: 1
description: "Rendering pipeline for orchestrating page rendering workflow. Orchestrates the parsing, AST building, templating, and output rendering phases for individual pages. Manages thread-local parser instance..."
---

# pipeline
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/pipeline.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›pipeline

Rendering pipeline for orchestrating page rendering workflow.

Orchestrates the parsing, AST building, templating, and output rendering phases
for individual pages. Manages thread-local parser instances for performance
and provides dependency tracking for incremental builds.

Key Concepts:
    - Thread-local parsers: Parser instances reused per thread for performance
    - AST-based processing: Content represented as AST for efficient transformation
    - Template rendering: Jinja2 template rendering with page context
    - Dependency tracking: Template and asset dependency tracking

Related Modules:
    - bengal.rendering.parsers.mistune: Markdown parser implementation
    - bengal.rendering.template_engine: Template engine for Jinja2 rendering
    - bengal.rendering.renderer: Individual page rendering logic
    - bengal.cache.dependency_tracker: Dependency graph construction

See Also:
    - bengal/rendering/pipeline.py:RenderingPipeline for pipeline logic
    - plan/active/rfc-content-ast-architecture.md: AST architecture RFC

## Classes




### `RenderingPipeline`


Coordinates the entire rendering process for content pages.

Orchestrates the complete rendering pipeline from markdown parsing through
template rendering to final HTML output. Manages thread-local parser instances
for performance and integrates with dependency tracking for incremental builds.

Creation:
    Direct instantiation: RenderingPipeline(site, dependency_tracker=None, ...)
        - Created by RenderOrchestrator for page rendering
        - One instance per worker thread (thread-local)
        - Requires Site instance with config



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `site` | - | Site instance with config and xref_index |
| `parser` | - | Thread-local markdown parser (cached per thread) |
| `dependency_tracker` | - | Optional DependencyTracker for incremental builds |
| `quiet` | - | Whether to suppress per-page output |
| `build_stats` | - | Optional BuildStats for error collection Pipeline Stages: 1. Parse source content (Markdown, etc.) 2. Build Abstract Syntax Tree (AST) 3. Apply templates (Jinja2) 4. Render output (HTML) 5. Write to output directory |
| `Relationships` | - | - Uses: TemplateEngine for template rendering - Uses: Renderer for individual page rendering - Uses: DependencyTracker for dependency tracking - Used by: RenderOrchestrator for page rendering Thread Safety: Thread-safe. Uses thread-local parser instances. Each thread should have its own RenderingPipeline instance. |







## Methods



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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Any` | - | Site instance with config and xref_index |
| `dependency_tracker` | `Any` | - | Optional tracker for incremental builds |
| `quiet` | `bool` | `False` | If True, suppress per-page output |
| `build_stats` | `Any` | - | Optional BuildStats object to collect warnings |
| `build_context` | `Any \| None` | - | *No description provided.* |







**Returns**


`None`
:::{note}Each worker thread creates its own RenderingPipeline instance. The parser is cached at thread level, not pipeline level.:::





#### `process_page`
```python
def process_page(self, page: Page) -> None
```


Process a single page through the entire rendering pipeline.

Executes all rendering stages: parsing, AST building, template rendering,
and output writing. Uses cached parsed content when available (skips
markdown parsing if only template changed).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page object to process. Must have source_path set. |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
pipeline.process_page(page)
    # Page is now fully rendered with rendered_html populated
```

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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `toc_html` | `str` | - | HTML table of contents |







**Returns**


`list` - List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/pipeline.py`*

