# directory_loader

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/config/directory_loader.py

Directory-based configuration loader.

Loads config from directory structure:
    config/
    ├── _default/       # Base config
    ├── environments/   # Environment overrides
    └── profiles/       # Profile settings

Merge order: defaults → environment → profile

*Note: Template has undefined variables. This is fallback content.*
