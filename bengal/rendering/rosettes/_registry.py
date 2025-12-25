"""Lazy lexer registry for Rosettes.

Lexers are loaded on-demand to minimize import time.
The registry uses functools.cache for thread-safe caching.
"""

from __future__ import annotations

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
        "bengal.rendering.rosettes.lexers.python",
        "PythonLexer",
        aliases=("py", "python3", "py3"),
    ),
    "javascript": LexerSpec(
        "bengal.rendering.rosettes.lexers.javascript",
        "JavaScriptLexer",
        aliases=("js", "ecmascript"),
    ),
    "typescript": LexerSpec(
        "bengal.rendering.rosettes.lexers.typescript",
        "TypeScriptLexer",
        aliases=("ts",),
    ),
    "json": LexerSpec(
        "bengal.rendering.rosettes.lexers.json",
        "JsonLexer",
        aliases=("json5",),
    ),
    "yaml": LexerSpec(
        "bengal.rendering.rosettes.lexers.yaml",
        "YamlLexer",
        aliases=("yml",),
    ),
    "toml": LexerSpec(
        "bengal.rendering.rosettes.lexers.toml",
        "TomlLexer",
        aliases=(),
    ),
    "bash": LexerSpec(
        "bengal.rendering.rosettes.lexers.bash",
        "BashLexer",
        aliases=("sh", "shell", "zsh", "ksh"),
    ),
    "html": LexerSpec(
        "bengal.rendering.rosettes.lexers.html",
        "HtmlLexer",
        aliases=("htm", "xhtml"),
    ),
    "css": LexerSpec(
        "bengal.rendering.rosettes.lexers.css",
        "CssLexer",
        aliases=(),
    ),
    "diff": LexerSpec(
        "bengal.rendering.rosettes.lexers.diff",
        "DiffLexer",
        aliases=("patch", "udiff"),
    ),
    # Phase 2: Additional languages (10 more)
    "rust": LexerSpec(
        "bengal.rendering.rosettes.lexers.rust",
        "RustLexer",
        aliases=("rs",),
    ),
    "go": LexerSpec(
        "bengal.rendering.rosettes.lexers.go",
        "GoLexer",
        aliases=("golang",),
    ),
    "sql": LexerSpec(
        "bengal.rendering.rosettes.lexers.sql",
        "SqlLexer",
        aliases=("mysql", "postgresql", "sqlite"),
    ),
    "markdown": LexerSpec(
        "bengal.rendering.rosettes.lexers.markdown",
        "MarkdownLexer",
        aliases=("md", "mdown"),
    ),
    "xml": LexerSpec(
        "bengal.rendering.rosettes.lexers.xml",
        "XmlLexer",
        aliases=("xsl", "xslt", "rss", "svg"),
    ),
    "c": LexerSpec(
        "bengal.rendering.rosettes.lexers.c",
        "CLexer",
        aliases=("h",),
    ),
    "cpp": LexerSpec(
        "bengal.rendering.rosettes.lexers.cpp",
        "CppLexer",
        aliases=("c++", "cxx", "hpp"),
    ),
    "java": LexerSpec(
        "bengal.rendering.rosettes.lexers.java",
        "JavaLexer",
        aliases=(),
    ),
    "ruby": LexerSpec(
        "bengal.rendering.rosettes.lexers.ruby",
        "RubyLexer",
        aliases=("rb",),
    ),
    "php": LexerSpec(
        "bengal.rendering.rosettes.lexers.php",
        "PhpLexer",
        aliases=("php3", "php4", "php5", "php7", "php8"),
    ),
    # Phase 3: Additional languages (10 more)
    "kotlin": LexerSpec(
        "bengal.rendering.rosettes.lexers.kotlin",
        "KotlinLexer",
        aliases=("kt", "kts"),
    ),
    "swift": LexerSpec(
        "bengal.rendering.rosettes.lexers.swift",
        "SwiftLexer",
        aliases=(),
    ),
    "scala": LexerSpec(
        "bengal.rendering.rosettes.lexers.scala",
        "ScalaLexer",
        aliases=("sc",),
    ),
    "dockerfile": LexerSpec(
        "bengal.rendering.rosettes.lexers.dockerfile",
        "DockerfileLexer",
        aliases=("docker",),
    ),
    "graphql": LexerSpec(
        "bengal.rendering.rosettes.lexers.graphql",
        "GraphQLLexer",
        aliases=("gql",),
    ),
    "makefile": LexerSpec(
        "bengal.rendering.rosettes.lexers.makefile",
        "MakefileLexer",
        aliases=("make", "mf", "bsdmake"),
    ),
    "lua": LexerSpec(
        "bengal.rendering.rosettes.lexers.lua",
        "LuaLexer",
        aliases=(),
    ),
    "powershell": LexerSpec(
        "bengal.rendering.rosettes.lexers.powershell",
        "PowerShellLexer",
        aliases=("posh", "ps1", "psm1", "pwsh"),
    ),
    "elixir": LexerSpec(
        "bengal.rendering.rosettes.lexers.elixir",
        "ElixirLexer",
        aliases=("ex", "exs"),
    ),
    "hcl": LexerSpec(
        "bengal.rendering.rosettes.lexers.hcl",
        "HclLexer",
        aliases=("terraform", "tf"),
    ),
    # Phase 4: Additional languages (10 more)
    "haskell": LexerSpec(
        "bengal.rendering.rosettes.lexers.haskell",
        "HaskellLexer",
        aliases=("hs",),
    ),
    "r": LexerSpec(
        "bengal.rendering.rosettes.lexers.r",
        "RLexer",
        aliases=("rlang", "splus"),
    ),
    "perl": LexerSpec(
        "bengal.rendering.rosettes.lexers.perl",
        "PerlLexer",
        aliases=("pl", "pm"),
    ),
    "clojure": LexerSpec(
        "bengal.rendering.rosettes.lexers.clojure",
        "ClojureLexer",
        aliases=("clj", "edn"),
    ),
    "dart": LexerSpec(
        "bengal.rendering.rosettes.lexers.dart",
        "DartLexer",
        aliases=(),
    ),
    "groovy": LexerSpec(
        "bengal.rendering.rosettes.lexers.groovy",
        "GroovyLexer",
        aliases=("gradle",),
    ),
    "julia": LexerSpec(
        "bengal.rendering.rosettes.lexers.julia",
        "JuliaLexer",
        aliases=("jl",),
    ),
    "protobuf": LexerSpec(
        "bengal.rendering.rosettes.lexers.protobuf",
        "ProtobufLexer",
        aliases=("proto", "proto3"),
    ),
    "ini": LexerSpec(
        "bengal.rendering.rosettes.lexers.ini",
        "IniLexer",
        aliases=("cfg", "dosini", "properties", "conf"),
    ),
    "nginx": LexerSpec(
        "bengal.rendering.rosettes.lexers.nginx",
        "NginxLexer",
        aliases=("nginxconf",),
    ),
    # Phase 5: AI/ML and emerging languages (10 more)
    "mojo": LexerSpec(
        "bengal.rendering.rosettes.lexers.mojo",
        "MojoLexer",
        aliases=("🔥",),
    ),
    "zig": LexerSpec(
        "bengal.rendering.rosettes.lexers.zig",
        "ZigLexer",
        aliases=(),
    ),
    "cuda": LexerSpec(
        "bengal.rendering.rosettes.lexers.cuda",
        "CudaLexer",
        aliases=("cu",),
    ),
    "gleam": LexerSpec(
        "bengal.rendering.rosettes.lexers.gleam",
        "GleamLexer",
        aliases=(),
    ),
    "nim": LexerSpec(
        "bengal.rendering.rosettes.lexers.nim",
        "NimLexer",
        aliases=("nimrod",),
    ),
    "stan": LexerSpec(
        "bengal.rendering.rosettes.lexers.stan",
        "StanLexer",
        aliases=(),
    ),
    "pkl": LexerSpec(
        "bengal.rendering.rosettes.lexers.pkl",
        "PklLexer",
        aliases=(),
    ),
    "cue": LexerSpec(
        "bengal.rendering.rosettes.lexers.cue",
        "CueLexer",
        aliases=(),
    ),
    "v": LexerSpec(
        "bengal.rendering.rosettes.lexers.v",
        "VLexer",
        aliases=("vlang",),
    ),
    "triton": LexerSpec(
        "bengal.rendering.rosettes.lexers.triton",
        "TritonLexer",
        aliases=(),
    ),
    # Directory/file trees
    "tree": LexerSpec(
        "bengal.rendering.rosettes.lexers.tree",
        "TreeLexer",
        aliases=("directory", "filetree", "dirtree", "files"),
    ),
}

# Build alias lookup table (case-insensitive)
_ALIAS_TO_NAME: dict[str, str] = {}
for _name, _spec in _LEXER_SPECS.items():
    _ALIAS_TO_NAME[_name] = _name
    _ALIAS_TO_NAME[_name.upper()] = _name  # Pre-compute uppercase
    for _alias in _spec.aliases:
        _ALIAS_TO_NAME[_alias] = _name
        _ALIAS_TO_NAME[_alias.upper()] = _name

# Pre-compute sorted language list (avoid sorting on each call)
_SORTED_LANGUAGES: list[str] = sorted(_LEXER_SPECS.keys())


def _normalize_name(name: str) -> str:
    """Normalize a language name to its canonical form. O(1) lookup.

    Args:
        name: Language name or alias.

    Returns:
        Canonical language name.

    Raises:
        LookupError: If the language is not supported.
    """
    # Try direct lookup first (common case: already lowercase)
    if name in _ALIAS_TO_NAME:
        return _ALIAS_TO_NAME[name]
    # Try lowercase (avoid strip - rarely needed)
    lower = name.lower()
    if lower in _ALIAS_TO_NAME:
        return _ALIAS_TO_NAME[lower]
    raise LookupError(f"Unknown language: {name!r}. Supported: {_SORTED_LANGUAGES}")


def get_lexer(name: str) -> Lexer:
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
def _get_lexer_by_canonical(canonical: str) -> Lexer:
    """Internal cached loader - keyed by canonical name."""
    spec = _LEXER_SPECS[canonical]
    module = import_module(spec.module)
    lexer_class = getattr(module, spec.class_name)
    return lexer_class()


def list_languages() -> list[str]:
    """List all supported language names. O(1).

    Returns:
        Sorted list of canonical language names.
    """
    return _SORTED_LANGUAGES.copy()  # Return copy to prevent mutation


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
