"""
Site templates module - Re-exports from modular template system.

This module provides backward-compatible imports for the site templates system.
The actual templates are now organized in `bengal/cli/templates/` as separate
modules with their own template files and configuration.

Note:
    New code should import directly from `bengal.cli.templates`.
    This module exists for backward compatibility only.

Exports:
    SiteTemplate: Base class for site templates
    TemplateFile: Dataclass for template file definitions
    get_template: Get a registered template by name
    list_templates: List all registered templates
    register_template: Register a new site template

Related:
    - bengal/cli/templates/: Primary template module location
    - bengal/cli/templates/registry.py: Template registry implementation
"""

from __future__ import annotations

from bengal.cli.templates import (
    SiteTemplate,
    TemplateFile,
    get_template,
    list_templates,
    register_template,
)

# Compatibility exports
__all__ = [
    "SiteTemplate",
    "TemplateFile",
    "get_template",
    "list_templates",
    "register_template",
]
