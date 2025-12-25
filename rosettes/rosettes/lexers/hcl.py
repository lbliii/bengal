"""HCL/Terraform lexer for Rosettes.

Thread-safe regex-based tokenizer for HashiCorp Configuration Language.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["HclLexer"]

_BLOCK_TYPES = (
    "data",
    "locals",
    "module",
    "output",
    "provider",
    "resource",
    "terraform",
    "variable",
    "moved",
    "import",
    "check",
    "removed",
)

_KEYWORDS = (
    "for",
    "for_each",
    "if",
    "in",
    "dynamic",
    "content",
    "each",
    "self",
    "count",
    "depends_on",
    "lifecycle",
    "connection",
    "provisioner",
)

_TYPES = (
    "bool",
    "list",
    "map",
    "number",
    "object",
    "set",
    "string",
    "tuple",
    "any",
)

_FUNCTIONS = (
    "abs",
    "ceil",
    "floor",
    "log",
    "max",
    "min",
    "pow",
    "signum",
    "chomp",
    "format",
    "formatlist",
    "indent",
    "join",
    "lower",
    "regex",
    "regexall",
    "replace",
    "split",
    "strrev",
    "substr",
    "title",
    "trim",
    "trimprefix",
    "trimsuffix",
    "trimspace",
    "upper",
    "alltrue",
    "anytrue",
    "chunklist",
    "coalesce",
    "coalescelist",
    "compact",
    "concat",
    "contains",
    "distinct",
    "element",
    "flatten",
    "index",
    "keys",
    "length",
    "list",
    "lookup",
    "map",
    "matchkeys",
    "merge",
    "one",
    "range",
    "reverse",
    "setintersection",
    "setproduct",
    "setsubtract",
    "setunion",
    "slice",
    "sort",
    "sum",
    "transpose",
    "values",
    "zipmap",
    "base64decode",
    "base64encode",
    "base64gzip",
    "csvdecode",
    "jsondecode",
    "jsonencode",
    "textdecodebase64",
    "textencodebase64",
    "urlencode",
    "yamldecode",
    "yamlencode",
    "abspath",
    "dirname",
    "pathexpand",
    "basename",
    "file",
    "fileexists",
    "fileset",
    "filebase64",
    "templatefile",
    "formatdate",
    "timeadd",
    "timestamp",
    "md5",
    "sha1",
    "sha256",
    "sha512",
    "uuid",
    "uuidv5",
    "cidrhost",
    "cidrnetmask",
    "cidrsubnet",
    "cidrsubnets",
    "can",
    "nonsensitive",
    "sensitive",
    "tobool",
    "tolist",
    "tomap",
    "tonumber",
    "toset",
    "tostring",
    "try",
    "type",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in _BLOCK_TYPES:
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _FUNCTIONS:
        return TokenType.NAME_FUNCTION
    return TokenType.NAME


class HclLexer(PatternLexer):
    """HCL/Terraform lexer. Thread-safe."""

    name = "hcl"
    aliases = ("terraform", "tf")
    filenames = ("*.tf", "*.tfvars", "*.hcl")
    mimetypes = ("text/x-hcl", "application/x-terraform")

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_-]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Heredoc
        Rule(re.compile(r"<<-?(\w+)\n[\s\S]*?\n\1"), TokenType.STRING_HEREDOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Variable interpolation
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"%\{[^}]+\}"), TokenType.STRING_INTERPOL),
        # Numbers
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"=>|->|\.\.\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%!?:]"), TokenType.OPERATOR),
        # Attribute access
        Rule(re.compile(r"\."), TokenType.OPERATOR),
        # Assignment
        Rule(re.compile(r"="), TokenType.OPERATOR),
        # Splat
        Rule(re.compile(r"\[?\*\]?"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
