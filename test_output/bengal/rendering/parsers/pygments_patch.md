# pygments_patch

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/rendering/parsers/pygments_patch.py

Pygments performance patch for python-markdown.

This module provides a process-wide performance optimization that replaces
Pygments' lexer lookup functions with cached versions. This avoids expensive
plugin discovery on every code block during markdown rendering.

Performance Impact (826-page site):
    - Before: 86s (73% in plugin discovery)
    - After: ~29s (3× faster)

Warning:
    This patch affects the global markdown.extensions.codehilite module state.
    It is safe for CLI tools and single-process applications, but may not be
    suitable for multi-tenant web applications.

Usage:
    # One-time application (typical usage):
    PygmentsPatch.apply()

    # Temporary patching (for testing):
    with PygmentsPatch():
        # Patch is active here
        parser.parse(content)
    # Patch is removed here

*Note: Template has undefined variables. This is fallback content.*
