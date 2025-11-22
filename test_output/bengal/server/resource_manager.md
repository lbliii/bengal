# resource_manager

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/server/resource_manager.py

Resource lifecycle management for Bengal dev server.

Provides centralized cleanup handling for all termination scenarios:
- Normal exit (context manager)
- Ctrl+C (KeyboardInterrupt + signal handler)
- kill/SIGTERM (signal handler)
- Parent death (atexit handler)
- Exceptions (context manager __exit__)

*Note: Template has undefined variables. This is fallback content.*
