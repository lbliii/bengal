# theme_registry

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/theme_registry.py

Installed theme discovery and utilities.

Discovers uv/pip-installed themes via entry points (group: "bengal.themes").

Conventions:
- Package name: prefer "bengal-theme-<slug>"; accept "<slug>-bengal-theme".
- Entry point name: slug (e.g., "acme") → value: import path (e.g., "bengal_themes.acme").

*Note: Template has undefined variables. This is fallback content.*
