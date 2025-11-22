# reload_controller

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/server/reload_controller.py

ReloadController: Decide when and how to reload based on output diffs.

Scans the built output directory (e.g., public/) after each build and
compares against the prior snapshot to determine whether:
 - no reload is needed
 - CSS-only hot reload is sufficient
 - a full page reload is required

Uses file size and modification time for fast diffing. This is sufficient
for dev; a hashing option can be added later if needed.

*Note: Template has undefined variables. This is fallback content.*
