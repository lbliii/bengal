---
title: "directives"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/__init__.py"
---

# directives

Mistune directives package.

Provides all documentation directives (admonitions, tabs, dropdown, code-tabs)
as a single factory function for easy registration with Mistune.

Also provides:
- Directive caching for performance
- Error handling and validation

**Source:** `../../bengal/rendering/plugins/directives/__init__.py`

---


## Functions

### create_documentation_directives

```python
def create_documentation_directives()
```

Create documentation directives plugin for Mistune.

Returns a function that can be passed to mistune.create_markdown(plugins=[...]).

Provides:
- admonitions: note, tip, warning, danger, error, info, example, success
- tabs: Tabbed content with full markdown support
- dropdown: Collapsible sections with markdown
- code-tabs: Code examples in multiple languages

Usage:
    from bengal.rendering.plugins.directives import create_documentation_directives
    
    md = mistune.create_markdown(
        plugins=[create_documentation_directives()]
    )



**Raises:**

- **RuntimeError**: If directive registration fails
- **ImportError**: If FencedDirective is not available




---
