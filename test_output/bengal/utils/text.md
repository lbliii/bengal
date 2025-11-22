# text

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/text.py

Text processing utilities.

Provides canonical implementations for common text operations like slugification,
HTML stripping, truncation, and excerpt generation. These utilities consolidate
duplicate implementations found throughout the codebase.

Example:
    from bengal.utils.text import slugify, strip_html, truncate_words

    slug = slugify("Hello World!")  # "hello-world"
    text = strip_html("<p>Hello</p>")  # "Hello"
    excerpt = truncate_words("Long text here...", 10)

*Note: Template has undefined variables. This is fallback content.*
