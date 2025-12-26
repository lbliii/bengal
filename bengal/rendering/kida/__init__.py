"""Kida — Next-generation Python template engine for Python 3.14t.

A pure-Python template engine designed for free-threaded Python.
AST-native compilation, StringBuilder rendering, native async support.

Example:
    >>> from kida import Environment
    >>> env = Environment()
    >>> template = env.from_string("Hello, {{ name }}!")
    >>> print(template.render(name="World"))
    Hello, World!

Thread-Safety:
    All public APIs are thread-safe by design:
    - Template compilation is idempotent
    - Rendering uses only local state (StringBuilder pattern)
    - Environment caching uses copy-on-write

Free-Threading Declaration:
    This module declares itself safe for free-threaded Python via
    the _Py_mod_gil attribute (PEP 703).

Architecture:
    Template Source → Lexer → Parser → Kida AST → Compiler → Python AST → exec()

    Unlike Jinja2 which generates Python source strings, Kida generates
    ast.Module objects directly. This enables:
    - Structured code manipulation
    - Compile-time optimization
    - Better error messages with source mapping

Key Differences from Jinja2:
    - StringBuilder instead of generator yields (25-40% faster)
    - AST-to-AST compilation instead of string manipulation
    - Native async/await without wrapper adapters
    - Pythonic scoping with {% let %} and {% export %}
    - Protocol-based filter dispatch (compile-time binding)
"""

from bengal.rendering.kida._types import Token, TokenType
from bengal.rendering.kida.environment import (
    DictLoader,
    Environment,
    FileSystemLoader,
    TemplateError,
    TemplateNotFoundError,
    TemplateSyntaxError,
    UndefinedError,
)
from bengal.rendering.kida.template import LoopContext, Markup, Template

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "Environment",
    "Template",
    # Loaders
    "DictLoader",
    "FileSystemLoader",
    # Exceptions
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateSyntaxError",
    "UndefinedError",
    # Utilities
    "Markup",
    "LoopContext",
    # Types
    "Token",
    "TokenType",
]


# Free-threading declaration (PEP 703)
def __getattr__(name: str) -> object:
    """Module-level getattr for free-threading declaration."""
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0
    raise AttributeError(f"module 'kida' has no attribute {name!r}")
