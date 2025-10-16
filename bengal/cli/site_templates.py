"""
Site templates module - Re-exports from modular template system.

This module provides backward-compatible imports for the site templates system.
The actual templates are now organized in bengal/cli/templates/ as separate modules.
"""

from bengal.cli.templates import (
    SiteTemplate,
    TemplateFile,
    get_template,
    list_templates,
    register_template,
)

# Legacy compatibility exports
__all__ = [
    "SiteTemplate",
    "TemplateFile",
    "get_template",
    "list_templates",
    "register_template",
]
