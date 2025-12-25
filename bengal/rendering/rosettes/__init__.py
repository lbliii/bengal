"""Rosettes — Modern syntax highlighting for Python 3.14t.

A pure-Python syntax highlighter designed for free-threaded Python.
Zero global mutable state, immutable configuration, lazy loading.

Example:
    >>> from rosettes import highlight
    >>> html = highlight("def foo(): pass", "python")
    >>> print(html)
    <div class="highlight">...</div>

Thread-Safety:
    All public APIs are thread-safe by design:
    - Lexers use only local variables during tokenization
    - Formatter state is immutable
    - Registry uses functools.cache for thread-safe memoization

Free-Threading Declaration:
    This module declares itself safe for free-threaded Python via
    the _Py_mod_gil attribute (PEP 703).
"""

from bengal.rendering.rosettes._config import FormatConfig, HighlightConfig, LexerConfig
from bengal.rendering.rosettes._protocol import Formatter, Lexer
from bengal.rendering.rosettes._registry import get_lexer, list_languages, supports_language
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.formatters import HtmlFormatter

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Types
    "Token",
    "TokenType",
    # Protocols
    "Lexer",
    "Formatter",
    # Configuration
    "LexerConfig",
    "FormatConfig",
    "HighlightConfig",
    # Registry
    "get_lexer",
    "list_languages",
    "supports_language",
    # Formatters
    "HtmlFormatter",
    # High-level API
    "highlight",
    "tokenize",
]


def highlight(
    code: str,
    language: str,
    *,
    hl_lines: set[int] | frozenset[int] | None = None,
    show_linenos: bool = False,
    css_class: str | None = None,
    css_class_style: str = "semantic",
) -> str:
    """Highlight source code and return HTML.

    This is the primary high-level API for syntax highlighting.
    Thread-safe and suitable for concurrent use.

    Args:
        code: The source code to highlight.
        language: Language name or alias (e.g., 'python', 'py', 'js').
        hl_lines: Optional set of 1-based line numbers to highlight.
        show_linenos: If True, include line numbers in output.
        css_class: Base CSS class for the code container.
            Defaults to "rosettes" for semantic style, "highlight" for pygments.
        css_class_style: Class naming style:
            - "semantic" (default): Uses readable classes like .syntax-function
            - "pygments": Uses Pygments-compatible classes like .nf

    Returns:
        HTML string with syntax-highlighted code.

    Raises:
        LookupError: If the language is not supported.

    Example:
        >>> html = highlight("print('hello')", "python")
        >>> "rosettes" in html
        True

        >>> # Use Pygments-compatible classes
        >>> html = highlight("def foo(): pass", "python", css_class_style="pygments")
        >>> "highlight" in html
        True
    """
    lexer = get_lexer(language)

    # Determine container class based on style
    if css_class is None:
        css_class = "rosettes" if css_class_style == "semantic" else "highlight"

    format_config = FormatConfig(css_class=css_class)

    # Fast path: no line highlighting needed
    if not hl_lines and not show_linenos:
        formatter = HtmlFormatter(css_class_style=css_class_style)
        return formatter.format_string_fast(lexer.tokenize_fast(code), format_config)

    # Slow path: line highlighting or line numbers
    hl_config = HighlightConfig(
        hl_lines=frozenset(hl_lines) if hl_lines else frozenset(),
        show_linenos=show_linenos,
        css_class=css_class,
    )
    formatter = HtmlFormatter(config=hl_config, css_class_style=css_class_style)
    return formatter.format_string(lexer.tokenize(code), format_config)


def tokenize(code: str, language: str) -> list[Token]:
    """Tokenize source code without formatting.

    Useful for analysis, custom formatting, or testing.
    Thread-safe.

    Args:
        code: The source code to tokenize.
        language: Language name or alias.

    Returns:
        List of Token objects.

    Raises:
        LookupError: If the language is not supported.

    Example:
        >>> tokens = tokenize("x = 1", "python")
        >>> tokens[0].type
        <TokenType.NAME: 'n'>
    """
    lexer = get_lexer(language)
    return list(lexer.tokenize(code))


# Free-threading declaration (PEP 703)
def __getattr__(name: str) -> object:
    """Module-level getattr for free-threading declaration.

    This allows Python to query whether this module is safe for
    free-threaded execution without enabling the GIL.
    """
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0
    raise AttributeError(f"module 'rosettes' has no attribute {name!r}")
