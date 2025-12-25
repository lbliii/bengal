"""Python lexer for Rosettes.

Thread-safe regex-based tokenizer for Python 3.x source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PythonLexer"]

# Python keywords
_KEYWORDS = (
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
)

# Python builtins
_BUILTINS = (
    "abs",
    "aiter",
    "all",
    "anext",
    "any",
    "ascii",
    "bin",
    "bool",
    "breakpoint",
    "bytearray",
    "bytes",
    "callable",
    "chr",
    "classmethod",
    "compile",
    "complex",
    "delattr",
    "dict",
    "dir",
    "divmod",
    "enumerate",
    "eval",
    "exec",
    "filter",
    "float",
    "format",
    "frozenset",
    "getattr",
    "globals",
    "hasattr",
    "hash",
    "help",
    "hex",
    "id",
    "input",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "locals",
    "map",
    "max",
    "memoryview",
    "min",
    "next",
    "object",
    "oct",
    "open",
    "ord",
    "pow",
    "print",
    "property",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "setattr",
    "slice",
    "sorted",
    "staticmethod",
    "str",
    "sum",
    "super",
    "tuple",
    "type",
    "vars",
    "zip",
    "__import__",
)

# Pseudo builtins
_PSEUDO_BUILTINS = (
    "self",
    "cls",
    "__name__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__path__",
    "__file__",
    "__cached__",
    "__builtins__",
)

# Exception names
_EXCEPTIONS = (
    "ArithmeticError",
    "AssertionError",
    "AttributeError",
    "BaseException",
    "BlockingIOError",
    "BrokenPipeError",
    "BufferError",
    "BytesWarning",
    "ChildProcessError",
    "ConnectionAbortedError",
    "ConnectionError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "DeprecationWarning",
    "EOFError",
    "EnvironmentError",
    "Exception",
    "FileExistsError",
    "FileNotFoundError",
    "FloatingPointError",
    "FutureWarning",
    "GeneratorExit",
    "IOError",
    "ImportError",
    "ImportWarning",
    "IndentationError",
    "IndexError",
    "InterruptedError",
    "IsADirectoryError",
    "KeyError",
    "KeyboardInterrupt",
    "LookupError",
    "MemoryError",
    "ModuleNotFoundError",
    "NameError",
    "NotADirectoryError",
    "NotImplemented",
    "NotImplementedError",
    "OSError",
    "OverflowError",
    "PendingDeprecationWarning",
    "PermissionError",
    "ProcessLookupError",
    "RecursionError",
    "ReferenceError",
    "ResourceWarning",
    "RuntimeError",
    "RuntimeWarning",
    "StopAsyncIteration",
    "StopIteration",
    "SyntaxError",
    "SyntaxWarning",
    "SystemError",
    "SystemExit",
    "TabError",
    "TimeoutError",
    "TypeError",
    "UnboundLocalError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "UnicodeError",
    "UnicodeTranslateError",
    "UnicodeWarning",
    "UserWarning",
    "ValueError",
    "Warning",
    "ZeroDivisionError",
)


def _classify_keyword(match: re.Match[str]) -> TokenType:
    """Classify a keyword match into the appropriate token type."""
    word = match.group(0)
    if word in ("True", "False", "None"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("def", "class", "lambda"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "from"):
        return TokenType.KEYWORD_NAMESPACE
    return TokenType.KEYWORD


def _classify_name(match: re.Match[str]) -> TokenType:
    """Classify a name match into the appropriate token type."""
    word = match.group(0)
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word in _PSEUDO_BUILTINS:
        return TokenType.NAME_BUILTIN_PSEUDO
    if word in _EXCEPTIONS:
        return TokenType.NAME_EXCEPTION
    return TokenType.NAME


class PythonLexer(PatternLexer):
    """Python 3 lexer.

    Handles Python 3.x syntax including f-strings, type hints, and walrus operator.
    Thread-safe: all state is immutable.
    """

    name = "python"
    aliases = ("py", "python3", "py3")
    filenames = ("*.py", "*.pyw", "*.pyi")
    mimetypes = ("text/x-python", "application/x-python")

    # Pattern for keywords (must be matched as whole words)
    _KEYWORD_PATTERN = r"\b(?:" + "|".join(_KEYWORDS) + r")\b"

    # Pattern for names that might be builtins
    _NAME_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments (must come before operators to match #)
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Triple-quoted strings (docstrings and multi-line)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING_DOC),
        # F-strings (simplified — captures whole f-string, no interpolation highlighting)
        Rule(re.compile(r'[fF]"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"[fF]'''[\s\S]*?'''"), TokenType.STRING_DOC),
        Rule(re.compile(r'[fF]"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"[fF]'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Raw strings
        Rule(re.compile(r'[rR]"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"[rR]'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Byte strings
        Rule(re.compile(r'[bB]"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"[bB]'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Regular strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Decorators
        Rule(
            re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*"),
            TokenType.NAME_DECORATOR,
        ),
        # Numbers (must come before operators to match signs)
        # Hex, octal, binary
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        # Float with exponent or decimal point
        Rule(re.compile(r"\d[\d_]*\.[\d_]*(?:[eE][+-]?[\d_]+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.[\d_]+(?:[eE][+-]?[\d_]+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?[\d_]+"), TokenType.NUMBER_FLOAT),
        # Integer
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords (before names)
        Rule(re.compile(_KEYWORD_PATTERN), _classify_keyword),
        # Names (builtins detected by callback)
        Rule(re.compile(_NAME_PATTERN), _classify_name),
        # Operators
        Rule(re.compile(r":="), TokenType.OPERATOR),  # Walrus
        Rule(re.compile(r"->"), TokenType.OPERATOR),  # Return type hint
        Rule(re.compile(r"==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\*\*=?|\+=|-=|\*=|//=?|/=|%=|@=|&=|\|=|\^=|>>=|<<="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%@&|^~]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;.,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
