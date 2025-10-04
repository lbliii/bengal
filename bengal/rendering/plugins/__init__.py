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
"""

from bengal.rendering.plugins.variable_substitution import VariableSubstitutionPlugin
from bengal.rendering.plugins.cross_references import CrossReferencePlugin
from bengal.rendering.plugins.directives import create_documentation_directives

# For backward compatibility, provide the old function name
def plugin_documentation_directives(md):
    """
    DEPRECATED: Use create_documentation_directives() instead.
    
    This function is maintained for backward compatibility but will be
    removed in a future version.
    """
    return create_documentation_directives()(md)


__all__ = [
    # Core plugins
    'VariableSubstitutionPlugin',
    'CrossReferencePlugin',
    
    # Directive factory
    'create_documentation_directives',
    
    # Backward compatibility (deprecated)
    'plugin_documentation_directives',
]

__version__ = '1.0.0'

