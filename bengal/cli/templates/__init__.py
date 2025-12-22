"""
Site templates for Bengal project scaffolding.

This package contains site templates used by `bengal new site` to create
new Bengal sites with pre-configured content, structure, and styling.

Available Templates:
    default: Minimal single-page site
    blog: Blog with posts and about page
    docs: Documentation site with sections
    landing: Marketing landing page
    portfolio: Personal portfolio site
    product: Product showcase site
    resume: Single-page resume/CV
    changelog: Project changelog site

Classes:
    SiteTemplate: Base class for defining templates
    TemplateFile: Dataclass for template file specifications

Functions:
    get_template: Retrieve a template by name
    list_templates: Get list of all available templates
    register_template: Register a custom template

Example:
    >>> from bengal.cli.templates import get_template, list_templates
    >>> template = get_template('blog')
    >>> all_templates = list_templates()
"""

from __future__ import annotations

from .base import SiteTemplate, TemplateFile
from .registry import get_template, list_templates, register_template

__all__ = [
    "SiteTemplate",
    "TemplateFile",
    "get_template",
    "list_templates",
    "register_template",
]
