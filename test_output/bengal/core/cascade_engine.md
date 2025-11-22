# cascade_engine

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/core/cascade_engine.py

Isolated cascade engine for applying Hugo-style metadata cascades.

This module provides the CascadeEngine class which handles all cascade
application logic independently from Site and ContentOrchestrator.

The engine pre-computes page-section relationships for O(1) top-level
page detection, improving performance from O(n²) to O(n).

*Note: Template has undefined variables. This is fallback content.*
