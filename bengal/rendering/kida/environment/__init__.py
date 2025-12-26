"""Kida Environment — central configuration and template management.

The Environment is the central hub for:
- Template configuration (delimiters, escaping, etc.)
- Template loading and caching
- Filter and test registration
- Extension management

Thread-Safety:
    The Environment uses copy-on-write for mutable state (filters, tests)
    and lock-free reads. Template caching uses atomic pointer swaps.

Example:
    >>> from kida import Environment
    >>> env = Environment()
    >>> template = env.from_string("Hello, {{ name }}!")
    >>> template.render(name="World")
    'Hello, World!'
"""

from bengal.rendering.kida.environment.core import Environment
from bengal.rendering.kida.environment.exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateSyntaxError,
)
from bengal.rendering.kida.environment.loaders import DictLoader, FileSystemLoader
from bengal.rendering.kida.environment.protocols import Filter, Loader, Test
from bengal.rendering.kida.environment.registry import FilterRegistry

__all__ = [
    "Environment",
    "FileSystemLoader",
    "DictLoader",
    "FilterRegistry",
    "Loader",
    "Filter",
    "Test",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateSyntaxError",
]
