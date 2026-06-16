"""Token model for the Bengal CSS engine.

Implements the token kinds from CSS Syntax Module Level 3 (§4 Tokenization)
closely enough for correct, lossless minification. The key property a minifier
needs is the distinction between an ``<ident-token>`` and a ``<function-token>``
(an identifier *immediately* followed by ``(``): collapsing whitespace can never
merge ``to (`` into ``to(`` because they are different token kinds by
construction.

Thread safety: ``Token`` is a frozen, slotted dataclass and safe to share across
threads. The module-level frozensets are immutable.

See also:
- ``bengal/css/tokenizer.py``: produces these tokens.
- W3C CSS Syntax §9 "Serialization": the ``needs_separator`` adjacency rules.
"""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """CSS token kinds (CSS Syntax Level 3)."""

    WHITESPACE = auto()
    COMMENT = auto()

    IDENT = auto()
    FUNCTION = auto()  # name of an identifier immediately followed by "("
    AT_KEYWORD = auto()  # includes the leading "@"
    HASH = auto()  # includes the leading "#"

    STRING = auto()
    BAD_STRING = auto()
    URL = auto()  # url( ... ) with an unquoted body
    BAD_URL = auto()

    NUMBER = auto()
    PERCENTAGE = auto()
    DIMENSION = auto()

    CDO = auto()  # <!--
    CDC = auto()  # -->

    COLON = auto()
    SEMICOLON = auto()
    COMMA = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()

    DELIM = auto()  # a single code point not otherwise classified
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """A single CSS token.

    Attributes:
        type: The token kind.
        value: The exact source text of the token. For ``FUNCTION`` this is the
            function name *without* the trailing ``(``. For ``HASH`` and
            ``AT_KEYWORD`` it includes the leading sigil. For ``DIMENSION`` it is
            the full ``<number><unit>`` text.
        unit: The unit of a ``DIMENSION`` token (lowercased view kept separate so
            normalizers can reason about it), otherwise ``""``.
    """

    type: TokenType
    value: str
    unit: str = ""


# --- Serialization adjacency (CSS Syntax §9) -------------------------------
#
# When whitespace/comments are removed between two tokens A then B, a separator
# must be re-inserted iff joining A and B would re-tokenize differently. This is
# the single rule that replaces the old minifier's pile of property heuristics.
# The categories and matrix mirror Servo's `cssparser` TokenSerializationType.


class _SerType(Enum):
    NOTHING = auto()
    IDENT = auto()
    FUNCTION = auto()
    AT_HASH = auto()  # at-keyword or hash token
    URL = auto()
    NUMBER = auto()
    PERCENTAGE = auto()
    DIMENSION = auto()
    CDC = auto()
    OPEN_PAREN = auto()
    DELIM_HASH = auto()  # delim "#"
    DELIM_AT = auto()  # delim "@"
    DELIM_MINUS = auto()  # delim "-"
    DELIM_DOT_PLUS = auto()  # delim "." or "+"
    DELIM_SLASH = auto()  # delim "/"
    DELIM_ASTERISK = auto()  # delim "*"
    OTHER = auto()


def _ser_type(tok: Token) -> _SerType:
    t = tok.type
    if t is TokenType.IDENT:
        return _SerType.IDENT
    if t is TokenType.FUNCTION:
        return _SerType.FUNCTION
    if t in (TokenType.AT_KEYWORD, TokenType.HASH):
        return _SerType.AT_HASH
    if t in (TokenType.URL, TokenType.BAD_URL):
        return _SerType.URL
    if t is TokenType.NUMBER:
        return _SerType.NUMBER
    if t is TokenType.PERCENTAGE:
        return _SerType.PERCENTAGE
    if t is TokenType.DIMENSION:
        return _SerType.DIMENSION
    if t is TokenType.CDC:
        return _SerType.CDC
    if t is TokenType.LPAREN:
        return _SerType.OPEN_PAREN
    if t is TokenType.DELIM:
        v = tok.value
        if v == "#":
            return _SerType.DELIM_HASH
        if v == "@":
            return _SerType.DELIM_AT
        if v == "-":
            return _SerType.DELIM_MINUS
        if v in (".", "+"):
            return _SerType.DELIM_DOT_PLUS
        if v == "/":
            return _SerType.DELIM_SLASH
        if v == "*":
            return _SerType.DELIM_ASTERISK
        return _SerType.OTHER
    return _SerType.OTHER


# Second-token category sets for each first-token category.
_IDENT_LIKE = frozenset(
    {
        _SerType.IDENT,
        _SerType.FUNCTION,
        _SerType.URL,
        _SerType.DELIM_MINUS,
        _SerType.NUMBER,
        _SerType.PERCENTAGE,
        _SerType.DIMENSION,
        _SerType.CDC,
    }
)
_IDENT_FOLLOW = _IDENT_LIKE | {_SerType.OPEN_PAREN}
_HASH_DIM_FOLLOW = _IDENT_LIKE
_DELIMHASH_MINUS_FOLLOW = frozenset(
    {
        _SerType.IDENT,
        _SerType.FUNCTION,
        _SerType.URL,
        _SerType.DELIM_MINUS,
        _SerType.NUMBER,
        _SerType.PERCENTAGE,
        _SerType.DIMENSION,
    }
)
_NUMBER_FOLLOW = _DELIMHASH_MINUS_FOLLOW
_AT_FOLLOW = frozenset({_SerType.IDENT, _SerType.FUNCTION, _SerType.URL, _SerType.DELIM_MINUS})
_DOTPLUS_FOLLOW = frozenset({_SerType.NUMBER, _SerType.PERCENTAGE, _SerType.DIMENSION})
_SLASH_FOLLOW = frozenset({_SerType.DELIM_ASTERISK})


def needs_separator(a: Token, b: Token) -> bool:
    """Return whether a separator is required between adjacent tokens ``a`` ``b``.

    Implements the CSS Syntax §9 serialization adjacency rules. If this returns
    ``True``, removing the whitespace between the two tokens would change how the
    output re-tokenizes (e.g. ``to`` + ``(`` -> ``to(`` function token).
    """
    sa = _ser_type(a)
    sb = _ser_type(b)
    if sa is _SerType.IDENT:
        return sb in _IDENT_FOLLOW
    if sa in (_SerType.AT_HASH, _SerType.DIMENSION):
        return sb in _HASH_DIM_FOLLOW
    if sa in (_SerType.DELIM_HASH, _SerType.DELIM_MINUS):
        return sb in _DELIMHASH_MINUS_FOLLOW
    if sa is _SerType.NUMBER:
        return sb in _NUMBER_FOLLOW
    if sa is _SerType.DELIM_AT:
        return sb in _AT_FOLLOW
    if sa is _SerType.DELIM_DOT_PLUS:
        return sb in _DOTPLUS_FOLLOW
    if sa is _SerType.DELIM_SLASH:
        return sb in _SLASH_FOLLOW
    return False
