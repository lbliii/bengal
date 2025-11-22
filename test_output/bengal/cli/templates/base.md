# base

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cli/templates/base.py

Template system primitives used by all built‑in site templates.

This module defines two dataclasses that describe what a site template is and
the files it contributes when instantiated via CLI commands (e.g.
`bengal new site --template blog`). These classes are intentionally small and
framework‑agnostic so they can be reused by both built‑in and custom templates.

Key concepts:
- ``TemplateFile``: a single file that will be written to a target area of the
  project (``content/``, ``data/``, ``templates/``, etc.).
- ``SiteTemplate``: a collection of ``TemplateFile`` items plus optional
  directory scaffolding and menu hints that describe a complete starter layout.

*Note: Template has undefined variables. This is fallback content.*
