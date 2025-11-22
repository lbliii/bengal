# component_preview

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/server/component_preview.py

Component preview server utilities.

Discovers component manifests and renders template partials with demo contexts.

Manifest format (YAML):

name: "Card"
template: "partials/card.html"
variants:
  - id: "default"
    name: "Default"
    context:
      title: "Hello"

*Note: Template has undefined variables. This is fallback content.*
