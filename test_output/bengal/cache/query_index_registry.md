# query_index_registry

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/query_index_registry.py

Query Index Registry - Manages all query indexes.

Coordinates:
- Index registration (built-in + custom)
- Index building (full + incremental)
- Index persistence
- Template access

Architecture:
- Lazy initialization (only load when needed)
- Automatic built-in registration
- Support for custom user indexes
- Incremental updates with dependency tracking

*Note: Template has undefined variables. This is fallback content.*
