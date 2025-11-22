# error_handlers

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/error_handlers.py

Context-aware error handlers to enrich exception displays.

Handlers provide concise, helpful suggestions for common Python errors:
- ImportError: Show available exports in the target module and close matches
- AttributeError: Show available attributes on a target module and close matches
- TypeError: Generic guidance for common patterns

These handlers are best-effort and must never raise; they return lightweight
strings suitable for inclusion in compact/minimal traceback renderers.

*Note: Template has undefined variables. This is fallback content.*
