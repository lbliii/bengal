# api_doc_enhancer

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/rendering/api_doc_enhancer.py

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

*Note: Template has undefined variables. This is fallback content.*
