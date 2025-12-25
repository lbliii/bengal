"""Lazy lexer registry for Rosettes.

Lexers are loaded on-demand to minimize import time.
The registry uses functools.cache for thread-safe caching.
"""

from dataclasses import dataclass
from functools import cache
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._protocol import Lexer

__all__ = ["get_lexer", "list_languages", "supports_language"]


@dataclass(frozen=True, slots=True)
class LexerSpec:
    """Specification for lazy-loading a lexer.

    Attributes:
        module: Full module path (e.g., 'rosettes.lexers.python').
        class_name: Name of the lexer class in the module.
        aliases: Alternative names for lookup.
    """

    module: str
    class_name: str
    aliases: tuple[str, ...] = ()


# Static registry — lexers are loaded on demand
# Mapping: canonical name -> LexerSpec
_LEXER_SPECS: dict[str, LexerSpec] = {
    "python": LexerSpec(
        "rosettes.lexers.python",
        "PythonLexer",
        aliases=("py", "python3", "py3"),
    ),
    "javascript": LexerSpec(
        "rosettes.lexers.javascript",
        "JavaScriptLexer",
        aliases=("js", "ecmascript"),
    ),
    "typescript": LexerSpec(
        "rosettes.lexers.typescript",
        "TypeScriptLexer",
        aliases=("ts",),
    ),
    "json": LexerSpec(
        "rosettes.lexers.json",
        "JsonLexer",
        aliases=("json5",),
    ),
    "yaml": LexerSpec(
        "rosettes.lexers.yaml",
        "YamlLexer",
        aliases=("yml",),
    ),
    "toml": LexerSpec(
        "rosettes.lexers.toml",
        "TomlLexer",
        aliases=(),
    ),
    "bash": LexerSpec(
        "rosettes.lexers.bash",
        "BashLexer",
        aliases=("sh", "shell", "zsh", "ksh"),
    ),
    "html": LexerSpec(
        "rosettes.lexers.html",
        "HtmlLexer",
        aliases=("htm", "xhtml"),
    ),
    "css": LexerSpec(
        "rosettes.lexers.css",
        "CssLexer",
        aliases=(),
    ),
    "diff": LexerSpec(
        "rosettes.lexers.diff",
        "DiffLexer",
        aliases=("patch", "udiff"),
    ),
}

# Build alias lookup table
_ALIAS_TO_NAME: dict[str, str] = {}
for name, spec in _LEXER_SPECS.items():
    _ALIAS_TO_NAME[name] = name
    for alias in spec.aliases:
        _ALIAS_TO_NAME[alias] = name


def _normalize_name(name: str) -> str:
    """Normalize a language name to its canonical form.

    Args:
        name: Language name or alias.

    Returns:
        Canonical language name.

    Raises:
        LookupError: If the language is not supported.
    """
    normalized = name.lower().strip()
    if normalized not in _ALIAS_TO_NAME:
        raise LookupError(f"Unknown language: {name!r}. Supported: {sorted(_LEXER_SPECS.keys())}")
    return _ALIAS_TO_NAME[normalized]


def get_lexer(name: str) -> "Lexer":
    """Get a lexer instance by name or alias.

    Uses functools.cache for thread-safe memoization.
    Lexers are loaded lazily on first access.

    Args:
        name: Language name or alias (e.g., 'python', 'py', 'js').

    Returns:
        Lexer instance.

    Raises:
        LookupError: If the language is not supported.

    Example:
        >>> lexer = get_lexer("python")
        >>> lexer.name
        'python'
        >>> get_lexer("py") is lexer  # Same instance (cached)
        True
    """
    canonical = _normalize_name(name)
    return _get_lexer_by_canonical(canonical)


@cache
def _get_lexer_by_canonical(canonical: str) -> "Lexer":
    """Internal cached loader - keyed by canonical name."""
    spec = _LEXER_SPECS[canonical]
    module = import_module(spec.module)
    lexer_class = getattr(module, spec.class_name)
    return lexer_class()


def list_languages() -> list[str]:
    """List all supported language names.

    Returns:
        Sorted list of canonical language names.
    """
    return sorted(_LEXER_SPECS.keys())


def supports_language(name: str) -> bool:
    """Check if a language is supported.

    Args:
        name: Language name or alias.

    Returns:
        True if the language is supported.
    """
    try:
        _normalize_name(name)
        return True
    except LookupError:
        return False
