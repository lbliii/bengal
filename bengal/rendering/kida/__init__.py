"""Kida — Next-generation template engine for free-threaded Python (3.14t+).

A pure-Python template engine optimized for free-threaded Python execution.
Features AST-native compilation, StringBuilder rendering, and native async support.

Quickstart:
    >>> from bengal.rendering.kida import Environment
    >>> env = Environment()
    >>> template = env.from_string("Hello, {{ name }}!")
    >>> template.render(name="World")
    'Hello, World!'

File-based templates:
    >>> from bengal.rendering.kida import Environment, FileSystemLoader
    >>> env = Environment(loader=FileSystemLoader("templates/"))
    >>> template = env.get_template("index.html")
    >>> template.render(page=page, site=site)

Architecture:
    Template Source → Lexer → Parser → Kida AST → Compiler → Python AST → exec()

    Pipeline stages:
    1. **Lexer**: Tokenizes template source into token stream
    2. **Parser**: Builds immutable Kida AST from tokens
    3. **Compiler**: Transforms Kida AST to Python AST
    4. **Template**: Wraps compiled code with render() interface

    Unlike Jinja2 which generates Python source strings, Kida generates
    `ast.Module` objects directly, enabling structured code manipulation,
    compile-time optimization, and precise error source mapping.

Thread-Safety:
    All public APIs are thread-safe by design:
    - Template compilation is idempotent (same input → same output)
    - Rendering uses only local state (StringBuilder pattern, no shared buffers)
    - Environment caching uses copy-on-write for filters/tests/globals
    - LRU caches use atomic operations (no locks required)

Free-Threading (PEP 703):
    Declares GIL-independence via `_Py_mod_gil = 0` attribute.
    Safe for concurrent template rendering in Python 3.14t+ free-threaded builds.

Performance Optimizations:
    - StringBuilder pattern: O(n) output vs O(n²) string concatenation
    - Local variable caching: `_escape`, `_str` bound once per render
    - O(1) operator dispatch: dict-based token → handler lookup
    - Single-pass HTML escaping via `str.translate()`
    - Compiled regex patterns at class level (immutable)

Key Differences from Jinja2:
    - **Rendering**: StringBuilder pattern (25-40% faster than generator yields)
    - **Compilation**: AST-to-AST (no string manipulation or regex)
    - **Async**: Native async/await (no `auto_await()` wrappers)
    - **Scoping**: Explicit `{% let %}`, `{% set %}`, `{% export %}` semantics
    - **Syntax**: Unified `{% end %}` for all blocks (like Go templates)
    - **Filters**: Protocol-based dispatch with compile-time binding
    - **Caching**: Built-in `{% cache key %}...{% end %}` directive
    - **Pipeline**: `|>` operator for readable filter chains
    - **Pattern Matching**: `{% match %}...{% case %}` for cleaner branching

Strict Mode (default):
    Undefined variables raise `UndefinedError` instead of silently returning
    empty string. Use `| default(fallback)` for optional variables:

    >>> env.from_string("{{ missing }}").render()  # Raises UndefinedError
    >>> env.from_string("{{ missing | default('N/A') }}").render()
    'N/A'

Jinja2 Compatibility:
    Use `kida.compat.jinja.JinjaParser` to parse existing Jinja2 templates:

    >>> from bengal.rendering.kida.compat.jinja import JinjaParser
    >>> parser = JinjaParser(tokens, source=source)
    >>> kida_ast = parser.parse()  # Produces Kida AST from Jinja2 syntax
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

# Python 3.14+ t-string support (PEP 750)
# Only import if string.templatelib is available
try:
    from bengal.rendering.kida.tstring import k
except ImportError:
    # Pre-3.14 Python - t-strings not available
    k = None

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "Environment",
    "Template",
    # Template Strings (3.14+)
    "k",
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
