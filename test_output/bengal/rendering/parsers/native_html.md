# native_html

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/rendering/parsers/native_html.py

Native HTML parser for build-time validation and health checks.

This parser is used during `bengal build` for:
- Health check validation (detecting unrendered directives, Jinja templates)
- Text extraction from rendered HTML (excluding code blocks)
- Performance-optimized alternative to BeautifulSoup4

Design:
- Uses Python's stdlib html.parser (fast, zero dependencies)
- Tracks state for code/script/style blocks to exclude from text extraction
- Optimized for build-time validation, not complex DOM manipulation

Performance:
- ~5-10x faster than BeautifulSoup4 for text extraction
- Suitable for high-volume build-time validation

*Note: Template has undefined variables. This is fallback content.*
