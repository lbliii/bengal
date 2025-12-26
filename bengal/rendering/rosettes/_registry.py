"""Lazy lexer registry for Rosettes.

All lexers are hand-written state machines with O(n) guaranteed performance
and zero ReDoS vulnerability. Lexers are loaded on-demand using functools.cache
for thread-safe memoization.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lexers._state_machine import StateMachineLexer

__all__ = ["get_lexer", "list_languages", "supports_language"]


@dataclass(frozen=True, slots=True)
class LexerSpec:
    """Specification for lazy-loading a lexer.

    Attributes:
        module: Full module path (e.g., 'rosettes.lexers.python_sm').
        class_name: Name of the lexer class in the module.
        aliases: Alternative names for lookup.
    """

    module: str
    class_name: str
    aliases: tuple[str, ...] = ()


# Static registry — all state machine lexers (O(n) guaranteed, zero ReDoS)
_LEXER_SPECS: dict[str, LexerSpec] = {
    # Core languages
    "python": LexerSpec(
        "bengal.rendering.rosettes.lexers.python_sm",
        "PythonStateMachineLexer",
        aliases=("py", "python3", "py3"),
    ),
    "javascript": LexerSpec(
        "bengal.rendering.rosettes.lexers.javascript_sm",
        "JavaScriptStateMachineLexer",
        aliases=("js", "ecmascript"),
    ),
    "typescript": LexerSpec(
        "bengal.rendering.rosettes.lexers.typescript_sm",
        "TypeScriptStateMachineLexer",
        aliases=("ts",),
    ),
    "json": LexerSpec(
        "bengal.rendering.rosettes.lexers.json_sm",
        "JsonStateMachineLexer",
        aliases=("json5",),
    ),
    "yaml": LexerSpec(
        "bengal.rendering.rosettes.lexers.yaml_sm",
        "YamlStateMachineLexer",
        aliases=("yml",),
    ),
    "toml": LexerSpec(
        "bengal.rendering.rosettes.lexers.toml_sm",
        "TomlStateMachineLexer",
        aliases=(),
    ),
    "bash": LexerSpec(
        "bengal.rendering.rosettes.lexers.bash_sm",
        "BashStateMachineLexer",
        aliases=("sh", "shell", "zsh", "ksh"),
    ),
    "html": LexerSpec(
        "bengal.rendering.rosettes.lexers.html_sm",
        "HtmlStateMachineLexer",
        aliases=("htm", "xhtml"),
    ),
    "css": LexerSpec(
        "bengal.rendering.rosettes.lexers.css_sm",
        "CssStateMachineLexer",
        aliases=(),
    ),
    "diff": LexerSpec(
        "bengal.rendering.rosettes.lexers.diff_sm",
        "DiffStateMachineLexer",
        aliases=("patch", "udiff"),
    ),
    # Systems languages
    "c": LexerSpec(
        "bengal.rendering.rosettes.lexers.c_sm",
        "CStateMachineLexer",
        aliases=("h",),
    ),
    "cpp": LexerSpec(
        "bengal.rendering.rosettes.lexers.cpp_sm",
        "CppStateMachineLexer",
        aliases=("c++", "cxx", "hpp"),
    ),
    "rust": LexerSpec(
        "bengal.rendering.rosettes.lexers.rust_sm",
        "RustStateMachineLexer",
        aliases=("rs",),
    ),
    "go": LexerSpec(
        "bengal.rendering.rosettes.lexers.go_sm",
        "GoStateMachineLexer",
        aliases=("golang",),
    ),
    "zig": LexerSpec(
        "bengal.rendering.rosettes.lexers.zig_sm",
        "ZigStateMachineLexer",
        aliases=(),
    ),
    # JVM languages
    "java": LexerSpec(
        "bengal.rendering.rosettes.lexers.java_sm",
        "JavaStateMachineLexer",
        aliases=(),
    ),
    "kotlin": LexerSpec(
        "bengal.rendering.rosettes.lexers.kotlin_sm",
        "KotlinStateMachineLexer",
        aliases=("kt", "kts"),
    ),
    "scala": LexerSpec(
        "bengal.rendering.rosettes.lexers.scala_sm",
        "ScalaStateMachineLexer",
        aliases=("sc",),
    ),
    "groovy": LexerSpec(
        "bengal.rendering.rosettes.lexers.groovy_sm",
        "GroovyStateMachineLexer",
        aliases=("gradle", "gvy"),
    ),
    "clojure": LexerSpec(
        "bengal.rendering.rosettes.lexers.clojure_sm",
        "ClojureStateMachineLexer",
        aliases=("clj", "edn"),
    ),
    # Apple ecosystem
    "swift": LexerSpec(
        "bengal.rendering.rosettes.lexers.swift_sm",
        "SwiftStateMachineLexer",
        aliases=(),
    ),
    # Scripting languages
    "ruby": LexerSpec(
        "bengal.rendering.rosettes.lexers.ruby_sm",
        "RubyStateMachineLexer",
        aliases=("rb",),
    ),
    "perl": LexerSpec(
        "bengal.rendering.rosettes.lexers.perl_sm",
        "PerlStateMachineLexer",
        aliases=("pl", "pm"),
    ),
    "php": LexerSpec(
        "bengal.rendering.rosettes.lexers.php_sm",
        "PhpStateMachineLexer",
        aliases=("php3", "php4", "php5", "php7", "php8"),
    ),
    "lua": LexerSpec(
        "bengal.rendering.rosettes.lexers.lua_sm",
        "LuaStateMachineLexer",
        aliases=(),
    ),
    "r": LexerSpec(
        "bengal.rendering.rosettes.lexers.r_sm",
        "RStateMachineLexer",
        aliases=("rlang", "splus"),
    ),
    "powershell": LexerSpec(
        "bengal.rendering.rosettes.lexers.powershell_sm",
        "PowershellStateMachineLexer",
        aliases=("posh", "ps1", "psm1", "pwsh"),
    ),
    # Functional languages
    "haskell": LexerSpec(
        "bengal.rendering.rosettes.lexers.haskell_sm",
        "HaskellStateMachineLexer",
        aliases=("hs",),
    ),
    "elixir": LexerSpec(
        "bengal.rendering.rosettes.lexers.elixir_sm",
        "ElixirStateMachineLexer",
        aliases=("ex", "exs"),
    ),
    # Data/query languages
    "sql": LexerSpec(
        "bengal.rendering.rosettes.lexers.sql_sm",
        "SqlStateMachineLexer",
        aliases=("mysql", "postgresql", "sqlite"),
    ),
    "graphql": LexerSpec(
        "bengal.rendering.rosettes.lexers.graphql_sm",
        "GraphqlStateMachineLexer",
        aliases=("gql",),
    ),
    # Markup
    "markdown": LexerSpec(
        "bengal.rendering.rosettes.lexers.markdown_sm",
        "MarkdownStateMachineLexer",
        aliases=("md", "mdown"),
    ),
    "xml": LexerSpec(
        "bengal.rendering.rosettes.lexers.xml_sm",
        "XmlStateMachineLexer",
        aliases=("xsl", "xslt", "rss", "svg"),
    ),
    # Config formats
    "ini": LexerSpec(
        "bengal.rendering.rosettes.lexers.ini_sm",
        "IniStateMachineLexer",
        aliases=("cfg", "dosini", "properties", "conf"),
    ),
    "nginx": LexerSpec(
        "bengal.rendering.rosettes.lexers.nginx_sm",
        "NginxStateMachineLexer",
        aliases=("nginxconf",),
    ),
    "dockerfile": LexerSpec(
        "bengal.rendering.rosettes.lexers.dockerfile_sm",
        "DockerfileStateMachineLexer",
        aliases=("docker",),
    ),
    "makefile": LexerSpec(
        "bengal.rendering.rosettes.lexers.makefile_sm",
        "MakefileStateMachineLexer",
        aliases=("make", "mf", "bsdmake"),
    ),
    "hcl": LexerSpec(
        "bengal.rendering.rosettes.lexers.hcl_sm",
        "HclStateMachineLexer",
        aliases=("terraform", "tf"),
    ),
    # Schema/IDL
    "protobuf": LexerSpec(
        "bengal.rendering.rosettes.lexers.protobuf_sm",
        "ProtobufStateMachineLexer",
        aliases=("proto", "proto3"),
    ),
    # Modern/emerging languages
    "dart": LexerSpec(
        "bengal.rendering.rosettes.lexers.dart_sm",
        "DartStateMachineLexer",
        aliases=(),
    ),
    "julia": LexerSpec(
        "bengal.rendering.rosettes.lexers.julia_sm",
        "JuliaStateMachineLexer",
        aliases=("jl",),
    ),
    "nim": LexerSpec(
        "bengal.rendering.rosettes.lexers.nim_sm",
        "NimStateMachineLexer",
        aliases=("nimrod",),
    ),
    "gleam": LexerSpec(
        "bengal.rendering.rosettes.lexers.gleam_sm",
        "GleamStateMachineLexer",
        aliases=(),
    ),
    "v": LexerSpec(
        "bengal.rendering.rosettes.lexers.v_sm",
        "VStateMachineLexer",
        aliases=("vlang",),
    ),
    # AI/ML specialized
    "mojo": LexerSpec(
        "bengal.rendering.rosettes.lexers.mojo_sm",
        "MojoStateMachineLexer",
        aliases=("🔥",),
    ),
    "triton": LexerSpec(
        "bengal.rendering.rosettes.lexers.triton_sm",
        "TritonStateMachineLexer",
        aliases=(),
    ),
    "cuda": LexerSpec(
        "bengal.rendering.rosettes.lexers.cuda_sm",
        "CudaStateMachineLexer",
        aliases=("cu",),
    ),
    "stan": LexerSpec(
        "bengal.rendering.rosettes.lexers.stan_sm",
        "StanStateMachineLexer",
        aliases=(),
    ),
    # Configuration languages
    "pkl": LexerSpec(
        "bengal.rendering.rosettes.lexers.pkl_sm",
        "PklStateMachineLexer",
        aliases=(),
    ),
    "cue": LexerSpec(
        "bengal.rendering.rosettes.lexers.cue_sm",
        "CueStateMachineLexer",
        aliases=(),
    ),
    # Tree/directory
    "tree": LexerSpec(
        "bengal.rendering.rosettes.lexers.tree_sm",
        "TreeStateMachineLexer",
        aliases=("directory", "filetree", "dirtree", "files", "scm", "treesitter"),
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


def get_lexer(name: str) -> StateMachineLexer:
    """Get a lexer instance by name or alias.

    All lexers are hand-written state machines with O(n) guaranteed
    performance and zero ReDoS vulnerability.

    Uses functools.cache for thread-safe memoization.
    Lexers are loaded lazily on first access.

    Args:
        name: Language name or alias (e.g., 'python', 'py', 'js').

    Returns:
        StateMachineLexer instance.

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
def _get_lexer_by_canonical(canonical: str) -> StateMachineLexer:
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
