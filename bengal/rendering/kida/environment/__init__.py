"""Kida Environment — central configuration and template management.

The Environment is the central hub for all template operations:

- **Configuration**: Delimiters, autoescape, strict mode
- **Loading**: File system, dict, or custom loaders
- **Caching**: LRU caches for templates and fragments
- **Extensibility**: Custom filters, tests, and global variables

Thread-Safety:
    Environment is designed for concurrent access:
    - Copy-on-write for `add_filter()`, `add_test()`, `add_global()`
    - Lock-free LRU cache with atomic pointer swaps
    - Immutable configuration after construction

Public API:
    - `Environment`: Central configuration class
    - `FileSystemLoader`: Load templates from directories
    - `DictLoader`: Load templates from memory (testing)
    - `FilterRegistry`: Dict-like interface for filters/tests
    - `Loader`, `Filter`, `Test`: Protocol definitions

Exceptions:
    - `TemplateError`: Base exception for all template errors
    - `TemplateNotFoundError`: Template not found by loader
    - `TemplateSyntaxError`: Parse-time syntax error
    - `UndefinedError`: Undefined variable in strict mode

Example:
    >>> from bengal.rendering.kida import Environment, FileSystemLoader
    >>> env = Environment(
    ...     loader=FileSystemLoader("templates/"),
    ...     autoescape=True,
    ...     strict=True,
    ... )
    >>> env.add_filter("upper", str.upper)
    >>> template = env.get_template("page.html")
    >>> template.render(title="Hello")
"""

from bengal.rendering.kida.environment.core import Environment
from bengal.rendering.kida.environment.exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateSyntaxError,
    UndefinedError,
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
    "UndefinedError",
]
