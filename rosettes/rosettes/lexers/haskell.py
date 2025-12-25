"""Haskell lexer for Rosettes.

Thread-safe regex-based tokenizer for Haskell source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["HaskellLexer"]

_KEYWORDS = (
    "as",
    "case",
    "class",
    "data",
    "default",
    "deriving",
    "do",
    "else",
    "family",
    "forall",
    "foreign",
    "hiding",
    "if",
    "import",
    "in",
    "infix",
    "infixl",
    "infixr",
    "instance",
    "let",
    "mdo",
    "module",
    "newtype",
    "of",
    "proc",
    "qualified",
    "rec",
    "then",
    "type",
    "where",
)

_TYPES = (
    "Bool",
    "Char",
    "Double",
    "Either",
    "Float",
    "IO",
    "Int",
    "Integer",
    "Maybe",
    "Ordering",
    "String",
    "Word",
)

_BUILTINS = (
    "abs",
    "acos",
    "acosh",
    "all",
    "and",
    "any",
    "appendFile",
    "asin",
    "asinh",
    "atan",
    "atan2",
    "atanh",
    "break",
    "ceiling",
    "compare",
    "concat",
    "concatMap",
    "const",
    "cos",
    "cosh",
    "curry",
    "cycle",
    "decodeFloat",
    "div",
    "divMod",
    "drop",
    "dropWhile",
    "either",
    "elem",
    "encodeFloat",
    "enumFrom",
    "enumFromThen",
    "enumFromThenTo",
    "enumFromTo",
    "error",
    "even",
    "exp",
    "exponent",
    "fail",
    "filter",
    "flip",
    "floatDigits",
    "floatRadix",
    "floatRange",
    "floor",
    "fmap",
    "foldl",
    "foldl1",
    "foldr",
    "foldr1",
    "fromEnum",
    "fromInteger",
    "fromIntegral",
    "fromRational",
    "fst",
    "gcd",
    "getChar",
    "getContents",
    "getLine",
    "head",
    "id",
    "init",
    "interact",
    "ioError",
    "isDenormalized",
    "isIEEE",
    "isInfinite",
    "isNaN",
    "isNegativeZero",
    "iterate",
    "last",
    "lcm",
    "length",
    "lex",
    "lines",
    "log",
    "logBase",
    "lookup",
    "map",
    "mapM",
    "mapM_",
    "max",
    "maxBound",
    "maximum",
    "maybe",
    "min",
    "minBound",
    "minimum",
    "mod",
    "negate",
    "not",
    "notElem",
    "null",
    "odd",
    "or",
    "otherwise",
    "pi",
    "pred",
    "print",
    "product",
    "properFraction",
    "putChar",
    "putStr",
    "putStrLn",
    "quot",
    "quotRem",
    "read",
    "readFile",
    "readIO",
    "readList",
    "readLn",
    "readParen",
    "reads",
    "readsPrec",
    "realToFrac",
    "recip",
    "rem",
    "repeat",
    "replicate",
    "return",
    "reverse",
    "round",
    "scaleFloat",
    "scanl",
    "scanl1",
    "scanr",
    "scanr1",
    "seq",
    "sequence",
    "sequence_",
    "show",
    "showChar",
    "showList",
    "showParen",
    "showString",
    "shows",
    "showsPrec",
    "significand",
    "signum",
    "sin",
    "sinh",
    "snd",
    "span",
    "splitAt",
    "sqrt",
    "subtract",
    "succ",
    "sum",
    "tail",
    "take",
    "takeWhile",
    "tan",
    "tanh",
    "toEnum",
    "toInteger",
    "toRational",
    "truncate",
    "uncurry",
    "undefined",
    "unlines",
    "until",
    "unwords",
    "unzip",
    "unzip3",
    "userError",
    "words",
    "writeFile",
    "zip",
    "zip3",
    "zipWith",
    "zipWith3",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("True", "False"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("data", "type", "newtype", "class", "instance", "deriving"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("module", "import", "qualified", "as", "hiding"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class HaskellLexer(PatternLexer):
    """Haskell lexer. Thread-safe."""

    name = "haskell"
    aliases = ("hs",)
    filenames = ("*.hs", "*.lhs")
    mimetypes = ("text/x-haskell",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_']*\b"

    rules = (
        # Pragmas
        Rule(re.compile(r"\{-#[\s\S]*?#-\}"), TokenType.COMMENT_PREPROC),
        # Block comments
        Rule(re.compile(r"\{-[\s\S]*?-\}"), TokenType.COMMENT_MULTILINE),
        # Line comments
        Rule(re.compile(r"--.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]+'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"\d+\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Type/constructor operators
        Rule(re.compile(r":[:!#$%&*+./<=>?@\\^|~-]+"), TokenType.OPERATOR),
        # Regular operators
        Rule(re.compile(r"[!#$%&*+./<=>?@\\^|~-]+"), TokenType.OPERATOR),
        # Special operators
        Rule(re.compile(r"->|<-|=>|::|\||\\|@|~"), TokenType.OPERATOR),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Punctuation
        Rule(re.compile(r"[()[\]{},;`]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
