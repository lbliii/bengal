
---
title: "rendering.api_doc_enhancer"
type: python-module
source_file: "bengal/rendering/api_doc_enhancer.py"
css_class: api-content
description: "API Documentation Enhancer - Post-processes API docs to inject badges and visual indicators.  This module operates on parsed HTML after Markdown rendering but before template application. It's desi..."
---

# rendering.api_doc_enhancer

API Documentation Enhancer - Post-processes API docs to inject badges and visual indicators.

This module operates on parsed HTML after Markdown rendering but before template application.
It's designed to work around Mistune's HTML escaping while maintaining clean, maintainable code.

Architecture:
    - Operates at the rendering pipeline stage (after Markdown → HTML)
    - Uses marker syntax in templates (@async, @property, etc.)
    - Injects HTML badges via regex replacement
    - Opt-in via page type (python-module, api-reference)

Usage:
    from bengal.rendering.api_doc_enhancer import APIDocEnhancer

    enhancer = APIDocEnhancer()
    enhanced_html = enhancer.enhance(html, page_type='python-module')

---

## Classes

### `APIDocEnhancer`


Post-processes API documentation HTML to inject badges and visual enhancements.

This enhancer transforms marker syntax (e.g., @async, @property) into styled
HTML badges. It operates on already-parsed HTML, avoiding Mistune's escaping issues.

Markers are placed in templates after method names and get replaced with proper
HTML during post-processing.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

Initialize the enhancer.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `should_enhance`
```python
def should_enhance(self, page_type: str | None) -> bool
```

Check if a page should be enhanced based on its type.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_type`** (`str | None`) - The page type from frontmatter

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if the page should be enhanced




---
#### `enhance`
```python
def enhance(self, html: str, page_type: str | None = None) -> str
```

Enhance HTML with API documentation badges.

This method applies all badge transformations to the HTML if the page
type indicates it's an API documentation page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`html`** (`str`) - Parsed HTML from markdown rendering
- **`page_type`** (`str | None`) = `None` - Page type from frontmatter (optional)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Enhanced HTML with badges injected (or unchanged HTML if not applicable)




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> enhancer = APIDocEnhancer()
    >>> html = '<h4>render @async</h4>'
    >>> enhancer.enhance(html, 'python-module')
    '<h4>render <span class="api-badge api-badge-async">async</span></h4>'
```


---
#### `strip_markers`
```python
def strip_markers(self, html: str) -> str
```

Remove all marker syntax from HTML without adding badges.

Useful for pages that want to show API documentation without badges,
or for debugging purposes.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`html`** (`str`) - HTML with marker syntax

:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML with markers removed




---


## Functions

### `get_enhancer`
```python
def get_enhancer() -> APIDocEnhancer
```

Get or create the singleton APIDocEnhancer instance.



:::{rubric} Returns
:class: rubric-returns
:::
`APIDocEnhancer` - Shared APIDocEnhancer instance




---
