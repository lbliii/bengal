---
title: "template_functions"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/__init__.py"
---

# template_functions

Template function registry for Bengal SSG.

This module provides 30+ template functions for use in Jinja2 templates,
organized into focused modules by responsibility.

Each module self-registers its functions to avoid god objects and maintain
clean separation of concerns.

**Source:** `../../bengal/rendering/template_functions/__init__.py`

---


## Functions

### register_all

```python
def register_all(env: 'Environment', site: 'Site') -> None
```

Register all template functions with Jinja2 environment.

This is a thin coordinator - each module handles its own registration
following the Single Responsibility Principle.

**Parameters:**

- **env** (`'Environment'`) - Jinja2 environment to register functions with
- **site** (`'Site'`) - Site instance for context-aware functions

**Returns:** `None`





---
