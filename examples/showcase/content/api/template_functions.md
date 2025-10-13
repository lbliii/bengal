
---
title: "template_functions"
type: python-module
source_file: "bengal/rendering/template_functions/__init__.py"
css_class: api-content
description: "Template function registry for Bengal SSG.  This module provides 30+ template functions for use in Jinja2 templates, organized into focused modules by responsibility.  Each module self-registers it..."
---

# template_functions

Template function registry for Bengal SSG.

This module provides 30+ template functions for use in Jinja2 templates,
organized into focused modules by responsibility.

Each module self-registers its functions to avoid god objects and maintain
clean separation of concerns.

---


## Functions

### `register_all`
```python
def register_all(env: 'Environment', site: 'Site') -> None
```

Register all template functions with Jinja2 environment.

This is a thin coordinator - each module handles its own registration
following the Single Responsibility Principle.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment to register functions with
- **`site`** (`'Site'`) - Site instance for context-aware functions

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
