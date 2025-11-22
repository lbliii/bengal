# template

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cli/templates/default/template.py

Default site template.

This module defines the minimal starter template shipped with Bengal. It
creates a single ``content/index.md`` file so users can bootstrap a site with
one command, and serves as a reference implementation for custom templates.

Exported objects:
- ``TEMPLATE``: the concrete  `SiteTemplate`
  instance discovered by the template registry.

*Note: Template has undefined variables. This is fallback content.*
