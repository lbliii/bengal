# traceback_config

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/traceback_config.py

Centralized configuration for traceback formatting and rendering.

Provides a simple configuration object with a style (full/compact/minimal/off),
and utilities to install Rich's global exception hook based on the active style.

MVP: Sources configuration from CLI-provided env var (BENGAL_TRACEBACK) → defaults.
Future: Extend to read from site config and config files.

*Note: Template has undefined variables. This is fallback content.*
