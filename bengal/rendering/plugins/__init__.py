"""
Rendering plugins package for Bengal SSG.

Provides custom Mistune plugins for enhanced markdown processing:

Core Plugins:
- VariableSubstitutionPlugin: {{ variable }} substitution in content
- CrossReferencePlugin: [[link]] syntax for internal references

Usage:

```python
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    CrossReferencePlugin,
)
```

"""

from __future__ import annotations

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
]

__version__ = "1.0.0"
