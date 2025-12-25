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
    # Phase 2: Additional languages (10 more)
    "rust": LexerSpec(
        "rosettes.lexers.rust",
        "RustLexer",
        aliases=("rs",),
    ),
    "go": LexerSpec(
        "rosettes.lexers.go",
        "GoLexer",
        aliases=("golang",),
    ),
    "sql": LexerSpec(
        "rosettes.lexers.sql",
        "SqlLexer",
        aliases=("mysql", "postgresql", "sqlite"),
    ),
    "markdown": LexerSpec(
        "rosettes.lexers.markdown",
        "MarkdownLexer",
        aliases=("md", "mdown"),
    ),
    "xml": LexerSpec(
        "rosettes.lexers.xml",
        "XmlLexer",
        aliases=("xsl", "xslt", "rss", "svg"),
    ),
    "c": LexerSpec(
        "rosettes.lexers.c",
        "CLexer",
        aliases=("h",),
    ),
    "cpp": LexerSpec(
        "rosettes.lexers.cpp",
        "CppLexer",
        aliases=("c++", "cxx", "hpp"),
    ),
    "java": LexerSpec(
        "rosettes.lexers.java",
        "JavaLexer",
        aliases=(),
    ),
    "ruby": LexerSpec(
        "rosettes.lexers.ruby",
        "RubyLexer",
        aliases=("rb",),
    ),
    "php": LexerSpec(
        "rosettes.lexers.php",
        "PhpLexer",
        aliases=("php3", "php4", "php5", "php7", "php8"),
    ),
    # Phase 3: Additional languages (10 more)
    "kotlin": LexerSpec(
        "rosettes.lexers.kotlin",
        "KotlinLexer",
        aliases=("kt", "kts"),
    ),
    "swift": LexerSpec(
        "rosettes.lexers.swift",
        "SwiftLexer",
        aliases=(),
    ),
    "scala": LexerSpec(
        "rosettes.lexers.scala",
        "ScalaLexer",
        aliases=("sc",),
    ),
    "dockerfile": LexerSpec(
        "rosettes.lexers.dockerfile",
        "DockerfileLexer",
        aliases=("docker",),
    ),
    "graphql": LexerSpec(
        "rosettes.lexers.graphql",
        "GraphQLLexer",
        aliases=("gql",),
    ),
    "makefile": LexerSpec(
        "rosettes.lexers.makefile",
        "MakefileLexer",
        aliases=("make", "mf", "bsdmake"),
    ),
    "lua": LexerSpec(
        "rosettes.lexers.lua",
        "LuaLexer",
        aliases=(),
    ),
    "powershell": LexerSpec(
        "rosettes.lexers.powershell",
        "PowerShellLexer",
        aliases=("posh", "ps1", "psm1", "pwsh"),
    ),
    "elixir": LexerSpec(
        "rosettes.lexers.elixir",
        "ElixirLexer",
        aliases=("ex", "exs"),
    ),
    "hcl": LexerSpec(
        "rosettes.lexers.hcl",
        "HclLexer",
        aliases=("terraform", "tf"),
    ),
    # Phase 4: Additional languages (10 more)
    "haskell": LexerSpec(
        "rosettes.lexers.haskell",
        "HaskellLexer",
        aliases=("hs",),
    ),
    "r": LexerSpec(
        "rosettes.lexers.r",
        "RLexer",
        aliases=("rlang", "splus"),
    ),
    "perl": LexerSpec(
        "rosettes.lexers.perl",
        "PerlLexer",
        aliases=("pl", "pm"),
    ),
    "clojure": LexerSpec(
        "rosettes.lexers.clojure",
        "ClojureLexer",
        aliases=("clj", "edn"),
    ),
    "dart": LexerSpec(
        "rosettes.lexers.dart",
        "DartLexer",
        aliases=(),
    ),
    "groovy": LexerSpec(
        "rosettes.lexers.groovy",
        "GroovyLexer",
        aliases=("gradle",),
    ),
    "julia": LexerSpec(
        "rosettes.lexers.julia",
        "JuliaLexer",
        aliases=("jl",),
    ),
    "protobuf": LexerSpec(
        "rosettes.lexers.protobuf",
        "ProtobufLexer",
        aliases=("proto", "proto3"),
    ),
    "ini": LexerSpec(
        "rosettes.lexers.ini",
        "IniLexer",
        aliases=("cfg", "dosini", "properties", "conf"),
    ),
    "nginx": LexerSpec(
        "rosettes.lexers.nginx",
        "NginxLexer",
        aliases=("nginxconf",),
    ),
    # Phase 5: AI/ML and emerging languages (10 more)
    "mojo": LexerSpec(
        "rosettes.lexers.mojo",
        "MojoLexer",
        aliases=("🔥",),
    ),
    "zig": LexerSpec(
        "rosettes.lexers.zig",
        "ZigLexer",
        aliases=(),
    ),
    "cuda": LexerSpec(
        "rosettes.lexers.cuda",
        "CudaLexer",
        aliases=("cu",),
    ),
    "gleam": LexerSpec(
        "rosettes.lexers.gleam",
        "GleamLexer",
        aliases=(),
    ),
    "nim": LexerSpec(
        "rosettes.lexers.nim",
        "NimLexer",
        aliases=("nimrod",),
    ),
    "stan": LexerSpec(
        "rosettes.lexers.stan",
        "StanLexer",
        aliases=(),
    ),
    "pkl": LexerSpec(
        "rosettes.lexers.pkl",
        "PklLexer",
        aliases=(),
    ),
    "cue": LexerSpec(
        "rosettes.lexers.cue",
        "CueLexer",
        aliases=(),
    ),
    "v": LexerSpec(
        "rosettes.lexers.v",
        "VLexer",
        aliases=("vlang",),
    ),
    "triton": LexerSpec(
        "rosettes.lexers.triton",
        "TritonLexer",
        aliases=(),
    ),
    # Documentation markup
    "myst": LexerSpec(
        "rosettes.lexers.myst",
        "MystLexer",
        aliases=("myst-markdown", "mystmd"),
    ),
    # Template languages
    "jinja2": LexerSpec(
        "rosettes.lexers.jinja2",
        "Jinja2Lexer",
        aliases=("jinja", "j2", "jinja2-html", "html+jinja", "htmldjango"),
    ),
    "liquid": LexerSpec(
        "rosettes.lexers.liquid",
        "LiquidLexer",
        aliases=("jekyll", "shopify-liquid"),
    ),
    "svelte": LexerSpec(
        "rosettes.lexers.svelte",
        "SvelteLexer",
        aliases=("svelte-html",),
    ),
    # CSS preprocessors
    "scss": LexerSpec(
        "rosettes.lexers.scss",
        "ScssLexer",
        aliases=("sass", "css-sass", "css-scss"),
    ),
    # Markup languages
    "rst": LexerSpec(
        "rosettes.lexers.rst",
        "RstLexer",
        aliases=("restructuredtext", "rest", "restx"),
    ),
    "asciidoc": LexerSpec(
        "rosettes.lexers.asciidoc",
        "AsciidocLexer",
        aliases=("adoc", "asc"),
    ),
    "latex": LexerSpec(
        "rosettes.lexers.latex",
        "LatexLexer",
        aliases=("tex", "context"),
    ),
    # Protocol/data formats
    "http": LexerSpec(
        "rosettes.lexers.http",
        "HttpLexer",
        aliases=("https",),
    ),
    "regex": LexerSpec(
        "rosettes.lexers.regex",
        "RegexLexer",
        aliases=("regexp", "re"),
    ),
    # Functional/scripting
    "ocaml": LexerSpec(
        "rosettes.lexers.ocaml",
        "OcamlLexer",
        aliases=("ml", "reasonml", "reason", "rescript"),
    ),
    "awk": LexerSpec(
        "rosettes.lexers.awk",
        "AwkLexer",
        aliases=("gawk", "mawk", "nawk"),
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
