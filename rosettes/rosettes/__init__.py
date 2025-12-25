"""Rosettes — Modern syntax highlighting for Python 3.14t.

A pure-Python syntax highlighter designed for free-threaded Python.
Zero global mutable state, immutable configuration, lazy loading.

All formatters and themes are lazy-loaded for sub-millisecond import times.

Example:
    >>> from rosettes import highlight
    >>> html = highlight("def foo(): pass", "python")
    >>> print(html)
    <div class="rosettes">...</div>

Theming:
    >>> from rosettes import highlight
    >>> from rosettes.themes import MONOKAI, generate_css
    >>>
    >>> # Highlight with semantic classes (default)
    >>> html = highlight("def foo(): pass", "python")
    >>>
    >>> # Use Pygments-compatible classes
    >>> html = highlight("def foo(): pass", "python", css_class_style="pygments")
    >>>
    >>> # Get CSS for a palette
    >>> css = generate_css(MONOKAI)

Thread-Safety:
    All public APIs are thread-safe by design:
    - Lexers use only local variables during tokenization
    - Formatter state is immutable
    - Registry uses functools.cache for thread-safe memoization

Free-Threading Declaration:
    This module declares itself safe for free-threaded Python via
    the _Py_mod_gil attribute (PEP 703).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Core types - lightweight, OK to import eagerly
from rosettes._config import FormatConfig, HighlightConfig, LexerConfig
from rosettes._protocol import Formatter, Lexer
from rosettes._registry import get_lexer, list_languages, supports_language
from rosettes._types import Token, TokenType

if TYPE_CHECKING:
    from typing import Literal

    CssClassStyle = Literal["semantic", "pygments"]

__version__ = "0.2.0"

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
    # Formatters (lazy)
    "HtmlFormatter",
    "TerminalFormatter",
    # High-level API
    "highlight",
    "highlight_terminal",
    "tokenize",
]

# Lazy-loaded formatters cache
_formatter_cache: dict[str, type] = {}


def __getattr__(name: str) -> object:
    """Lazy-load formatters and handle free-threading declaration."""
    # Free-threading declaration (PEP 703)
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0

    # Lazy-load formatters
    if name == "HtmlFormatter":
        if "HtmlFormatter" not in _formatter_cache:
            from rosettes.formatters.html import HtmlFormatter

            _formatter_cache["HtmlFormatter"] = HtmlFormatter
        return _formatter_cache["HtmlFormatter"]

    if name == "TerminalFormatter":
        if "TerminalFormatter" not in _formatter_cache:
            from rosettes.formatters.terminal import TerminalFormatter

            _formatter_cache["TerminalFormatter"] = TerminalFormatter
        return _formatter_cache["TerminalFormatter"]

    raise AttributeError(f"module 'rosettes' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for tab completion."""
    return list(__all__)


def highlight(
    code: str,
    language: str,
    *,
    hl_lines: set[int] | frozenset[int] | None = None,
    show_linenos: bool = False,
    css_class: str | None = None,
    css_class_style: CssClassStyle = "semantic",
    palette: str | None = None,
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
        palette: Optional palette name for CSS generation.

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
    # Lazy import formatter
    from rosettes.formatters.html import HtmlFormatter

    lexer = get_lexer(language)

    # Determine container class
    if css_class is None:
        css_class = "rosettes" if css_class_style == "semantic" else "highlight"

    format_config = FormatConfig(css_class=css_class)

    # Fast path: no line highlighting needed
    if not hl_lines and not show_linenos:
        formatter = HtmlFormatter(
            css_class_style=css_class_style,
            palette=palette,
        )
        return formatter.format_string_fast(lexer.tokenize_fast(code), format_config)

    # Slow path: line highlighting or line numbers
    hl_config = HighlightConfig(
        hl_lines=frozenset(hl_lines) if hl_lines else frozenset(),
        show_linenos=show_linenos,
        css_class=css_class,
    )
    formatter = HtmlFormatter(
        config=hl_config,
        css_class_style=css_class_style,
        palette=palette,
    )
    return formatter.format_string(lexer.tokenize(code), format_config)


def highlight_terminal(
    code: str,
    language: str,
    *,
    palette: str | None = None,
    color_mode: Literal["16", "256", "truecolor"] = "256",
) -> str:
    """Highlight source code for terminal output with ANSI colors.

    Thread-safe and suitable for concurrent use.

    Args:
        code: The source code to highlight.
        language: Language name or alias.
        palette: Optional terminal palette name.
        color_mode: Color mode ("16", "256", or "truecolor").

    Returns:
        String with ANSI escape codes for terminal display.

    Raises:
        LookupError: If the language is not supported.

    Example:
        >>> output = highlight_terminal("print('hello')", "python")
        >>> print(output)  # Colorized in terminal
    """
    # Lazy import formatter
    from rosettes.formatters.terminal import TerminalFormatter

    lexer = get_lexer(language)

    # Get terminal palette if specified
    terminal_palette = None
    if palette is not None:
        from rosettes.themes import get_palette
        from rosettes.themes._terminal import TerminalPalette

        base_palette = get_palette(palette)
        # Convert to terminal palette if needed
        if hasattr(base_palette, "with_defaults"):
            terminal_palette = TerminalPalette.from_syntax_palette(
                base_palette.with_defaults(),
                color_mode=color_mode,
            )

    formatter = TerminalFormatter(
        palette=terminal_palette,
        color_mode=color_mode,
    )
    return formatter.format_string_fast(lexer.tokenize_fast(code))


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
