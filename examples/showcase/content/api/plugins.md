
---
title: "plugins"
type: python-module
source_file: "bengal/rendering/plugins/__init__.py"
css_class: api-content
description: "Mistune plugins package for Bengal SSG.  Provides custom Mistune plugins for enhanced markdown processing:  Core Plugins:     - VariableSubstitutionPlugin: {{ variable }} substitution in content   ..."
---

# plugins

Mistune plugins package for Bengal SSG.

Provides custom Mistune plugins for enhanced markdown processing:

Core Plugins:
    - VariableSubstitutionPlugin: {{ variable }} substitution in content
    - CrossReferencePlugin: [[link]] syntax for internal references

Documentation Directives:
    - Admonitions: note, warning, tip, danger, etc.
    - Tabs: Tabbed content sections
    - Dropdown: Collapsible sections
    - Code Tabs: Multi-language code examples

Usage:
    # Import plugins
    from bengal.rendering.plugins import (
        VariableSubstitutionPlugin,
        CrossReferencePlugin,
        create_documentation_directives
    )

    # Use in mistune parser
    md = mistune.create_markdown(
        plugins=[
            create_documentation_directives(),
            VariableSubstitutionPlugin(context),
        ]
    )

For detailed documentation on each plugin, see:
    - variable_substitution.py
    - cross_references.py
    - directives/ package

---


## Functions

### `plugin_documentation_directives`
```python
def plugin_documentation_directives(md)
```

DEPRECATED: Use create_documentation_directives() instead.

This function will be removed in Bengal 2.0.

Usage:
    # Old (deprecated):
    md = mistune.create_markdown(
        plugins=[plugin_documentation_directives]
    )

    # New (recommended):
    md = mistune.create_markdown(
        plugins=[create_documentation_directives()]
    )



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`md`**





---
