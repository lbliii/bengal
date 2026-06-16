"""Serialize the CSS rule tree back to minimal, correct text.

Two whitespace policies:

- **Selector / at-rule preludes** (``selector`` mode): source whitespace between
  two simple selectors is a *descendant combinator* and is semantically
  significant, so it is preserved as a single space. Whitespace around the
  combinators ``> + ~``, around ``,``, and at ``( [`` boundaries is dropped. This
  is the policy that keeps ``@scope (.a .b) to (.c)`` correct — ``to`` + ``(``
  never collapse into a function token.
- **Declaration values** (``value`` mode): whitespace is dropped unless removing
  it would re-tokenize differently (CSS Syntax §9, via
  :func:`bengal.css.tokens.needs_separator`) or it surrounds a ``+``/``-`` math
  operator (required whitespace inside ``calc()`` and friends).

The serializer only ever *removes* source whitespace; it never invents a
separator where the source had none, so any already-tight input round-trips
byte-for-byte.
"""

from collections.abc import Callable

from bengal.css.nodes import Declaration, Node, QualifiedRule
from bengal.css.stringbuilder import StringBuilder
from bengal.css.tokens import Token, TokenType, needs_separator

_SKIP = (TokenType.WHITESPACE, TokenType.COMMENT)
_COMBINATORS = frozenset({">", "+", "~"})
_NO_SPACE_AFTER = (
    TokenType.FUNCTION,
    TokenType.LPAREN,
    TokenType.LBRACKET,
    TokenType.COMMA,
    TokenType.COLON,
)
_NO_SPACE_BEFORE = (TokenType.RPAREN, TokenType.RBRACKET, TokenType.COMMA)

ValueTransform = Callable[[tuple[Token, ...], str], tuple[Token, ...]]


def _emit(sb: StringBuilder, tok: Token) -> None:
    if tok.type is TokenType.FUNCTION:
        sb.append(tok.value)
        sb.append("(")
    else:
        sb.append(tok.value)


def _is_combinator(tok: Token) -> bool:
    return tok.type is TokenType.DELIM and tok.value in _COMBINATORS


def _is_plus_minus(tok: Token) -> bool:
    return tok.type is TokenType.DELIM and tok.value in ("+", "-")


def _serialize_selector(tokens: tuple[Token, ...], sb: StringBuilder) -> None:
    prev: Token | None = None
    prev_boundary = False
    sep = False
    bracket_depth = 0
    for tok in tokens:
        if tok.type in _SKIP:
            sep = True
            continue
        if tok.type is TokenType.LBRACKET:
            bracket_depth += 1
        cur_combinator = bracket_depth == 0 and _is_combinator(tok)
        cur_boundary = cur_combinator or tok.type in _NO_SPACE_BEFORE
        if (
            prev is not None
            and sep
            and (needs_separator(prev, tok) or (not prev_boundary and not cur_boundary))
        ):
            sb.append(" ")
        _emit(sb, tok)
        if tok.type is TokenType.RBRACKET and bracket_depth > 0:
            bracket_depth -= 1
        prev = tok
        prev_boundary = cur_combinator or tok.type in _NO_SPACE_AFTER
        sep = False


_VALUE_OPERATORS = frozenset({"/", "*"})


def _value_drop_ok(prev: Token, cur: Token) -> bool:
    """Whether the whitespace between ``prev`` and ``cur`` is safe to drop.

    Conservative on purpose: a space between two genuine value *components*
    (e.g. ``blur(5px) brightness(.5)`` or ``var(--a) solid``) is preserved, since
    browsers parse those unambiguously but the W3C validator — and some parsers —
    treat the separator as required. Only spaces adjacent to explicit separators
    and operators (``,`` ``/`` ``*``) or paren/bracket boundaries are dropped.
    """
    if prev.type in (TokenType.FUNCTION, TokenType.LPAREN, TokenType.LBRACKET):
        return True
    if cur.type in (TokenType.RPAREN, TokenType.RBRACKET):
        return True
    if prev.type is TokenType.COMMA or cur.type is TokenType.COMMA:
        return True
    if prev.type is TokenType.DELIM and prev.value in _VALUE_OPERATORS:
        return True
    return cur.type is TokenType.DELIM and cur.value in _VALUE_OPERATORS


def _serialize_value(tokens: tuple[Token, ...], sb: StringBuilder) -> None:
    prev: Token | None = None
    sep = False
    for tok in tokens:
        if tok.type in _SKIP:
            sep = True
            continue
        if (
            prev is not None
            and sep
            and (
                needs_separator(prev, tok)
                or _is_plus_minus(prev)
                or _is_plus_minus(tok)
                or not _value_drop_ok(prev, tok)
            )
        ):
            sb.append(" ")
        _emit(sb, tok)
        prev = tok
        sep = False


def _serialize_declaration(decl: Declaration, sb: StringBuilder, transform: ValueTransform) -> None:
    if not decl.name:
        _serialize_value(decl.value, sb)
        return
    sb.append(decl.name)
    sb.append(":")
    value = transform(decl.value, decl.name) if transform is not _IDENTITY else decl.value
    _serialize_value(value, sb)
    if decl.important:
        sb.append("!important")


def _serialize_block(nodes: tuple[Node, ...], sb: StringBuilder, transform: ValueTransform) -> None:
    last = len(nodes) - 1
    for idx, node in enumerate(nodes):
        _serialize_node(node, sb, transform)
        if isinstance(node, Declaration) and idx != last:
            sb.append(";")


def _serialize_node(node: Node, sb: StringBuilder, transform: ValueTransform) -> None:
    if isinstance(node, Declaration):
        _serialize_declaration(node, sb, transform)
        return
    if isinstance(node, QualifiedRule):
        _serialize_selector(node.prelude, sb)
        sb.append("{")
        _serialize_block(node.block, sb, transform)
        sb.append("}")
        return
    # AtRule. A valid at-keyword is always separated from its prelude in the
    # source (otherwise it would tokenize as one longer at-keyword), so a single
    # space before the prelude is always safe and keeps selector/pseudo preludes
    # such as "@scope (.a .b) to (.c)" correct.
    sb.append(node.name)
    if node.prelude:
        sb.append(" ")
        _serialize_selector(node.prelude, sb)
    if node.block is None:
        sb.append(";")
    else:
        sb.append("{")
        _serialize_block(node.block, sb, transform)
        sb.append("}")


def _identity(value: tuple[Token, ...], _name: str) -> tuple[Token, ...]:
    return value


_IDENTITY = _identity


def serialize(nodes: tuple[Node, ...], transform: ValueTransform = _IDENTITY) -> str:
    """Serialize a rule tree to minified CSS text."""
    sb = StringBuilder()
    for node in nodes:
        _serialize_node(node, sb, transform)
    return sb.build()
