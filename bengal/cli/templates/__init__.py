"""Site templates module."""


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
