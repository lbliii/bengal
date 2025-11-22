# registry

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cli/templates/registry.py

Template registry and discovery.

This module discovers built‑in templates (and optionally custom ones on
``PYTHONPATH``) by importing ``bengal.cli.templates.<name>.template`` and
looking for a module‑level ``TEMPLATE`` variable. The registry provides a small
API to list, retrieve, and register templates programmatically.

*Note: Template has undefined variables. This is fallback content.*
