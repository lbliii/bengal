"""
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

```python
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
```

For detailed documentation on each plugin, see:
    - variable_substitution.py
    - cross_references.py
    - directives/ package
"""

from __future__ import annotations

# Import from new bengal.directives package (directive system extraction)
from bengal.directives import create_documentation_directives
from bengal.rendering.plugins.badges import BadgePlugin
from bengal.rendering.plugins.cross_references import CrossReferencePlugin
from bengal.rendering.plugins.inline_icon import InlineIconPlugin
from bengal.rendering.plugins.term import TermPlugin
from bengal.rendering.plugins.variable_substitution import VariableSubstitutionPlugin

__all__ = [
    "BadgePlugin",
    "CrossReferencePlugin",
    "InlineIconPlugin",
    "TermPlugin",
    # Core plugins
    "VariableSubstitutionPlugin",
    # Directive factory
    "create_documentation_directives",
]

__version__ = "1.0.0"
