"""Parse a CSS token stream into the rule tree.

Implements a pragmatic subset of the CSS Syntax Level 3 parsing algorithms
("consume a list of rules / declarations / a qualified rule / an at-rule") that
is sufficient for minification, including native nesting (a block may contain
both declarations and nested rules).

Robustness over strictness: anything that does not parse cleanly is preserved as
a verbatim declaration so the serializer can emit it unchanged. The runtime
round-trip guard in :mod:`bengal.css.minify` is the backstop that guarantees
malformed or unanticipated input is never corrupted.
"""

from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_SKIP = (TokenType.WHITESPACE, TokenType.COMMENT)
_OPEN_NESTING = (TokenType.LPAREN, TokenType.LBRACKET)
_CLOSE_NESTING = (TokenType.RPAREN, TokenType.RBRACKET)


def parse_stylesheet(tokens: list[Token]) -> tuple[Node, ...]:
    """Parse a full stylesheet into a tuple of top-level nodes."""
    nodes, _ = _consume_contents(tokens, 0, len(tokens), top_level=True)
    return nodes


def _strip(tokens: list[Token], start: int, end: int) -> tuple[Token, ...]:
    while start < end and tokens[start].type in _SKIP:
        start += 1
    while end > start and tokens[end - 1].type in _SKIP:
        end -= 1
    return tuple(tokens[start:end])


def _consume_contents(
    tokens: list[Token], i: int, length: int, *, top_level: bool
) -> tuple[tuple[Node, ...], int]:
    nodes: list[Node] = []
    while i < length:
        t = tokens[i].type
        if t in _SKIP:
            i += 1
            continue
        if t in (TokenType.CDO, TokenType.CDC):
            i += 1
            continue
        if t is TokenType.RBRACE:
            if top_level:
                i += 1  # stray close brace; ignore
                continue
            return tuple(nodes), i  # caller consumes the brace
        if t is TokenType.AT_KEYWORD:
            node, i = _consume_at_rule(tokens, i, length)
            nodes.append(node)
            continue
        node, i = _consume_decl_or_qualified(tokens, i, length)
        if node is not None:
            nodes.append(node)
    return tuple(nodes), i


def _scan_top_level(tokens: list[Token], i: int, length: int) -> tuple[str, int]:
    """Find the next structural boundary at paren/bracket depth 0.

    Returns ``(kind, index)`` where kind is ``"brace"`` (a ``{`` block starts),
    ``"semi"`` (declaration ends at ``;``), or ``"close"`` (ends at ``}``/EOF).
    """
    depth = 0
    j = i
    while j < length:
        t = tokens[j].type
        if t in _OPEN_NESTING:
            depth += 1
        elif t in _CLOSE_NESTING:
            if depth > 0:
                depth -= 1
        elif depth == 0:
            if t is TokenType.LBRACE:
                return "brace", j
            if t is TokenType.SEMICOLON:
                return "semi", j
            if t is TokenType.RBRACE:
                return "close", j
        j += 1
    return "close", j


def _consume_block(tokens: list[Token], brace: int, length: int) -> tuple[tuple[Node, ...], int]:
    contents, k = _consume_contents(tokens, brace + 1, length, top_level=False)
    if k < length and tokens[k].type is TokenType.RBRACE:
        k += 1
    return contents, k


def _consume_at_rule(tokens: list[Token], i: int, length: int) -> tuple[Node, int]:
    name = tokens[i].value
    kind, j = _scan_top_level(tokens, i + 1, length)
    prelude = _strip(tokens, i + 1, j)
    if kind == "brace":
        block, k = _consume_block(tokens, j, length)
        return AtRule(name, prelude, block), k
    # statement at-rule (e.g. @import ...;)
    end = j + 1 if kind == "semi" else j
    return AtRule(name, prelude, None), end


def _consume_decl_or_qualified(tokens: list[Token], i: int, length: int) -> tuple[Node | None, int]:
    kind, j = _scan_top_level(tokens, i, length)
    if kind == "brace":
        prelude = _strip(tokens, i, j)
        block, k = _consume_block(tokens, j, length)
        return QualifiedRule(prelude, block), k
    decl_tokens = _strip(tokens, i, j)
    end = j + 1 if kind == "semi" else j
    if not decl_tokens:
        return None, end
    return _parse_declaration(decl_tokens), end


def _parse_declaration(toks: tuple[Token, ...]) -> Declaration:
    colon = -1
    for idx, tok in enumerate(toks):
        if tok.type is TokenType.COLON:
            colon = idx
            break
        if tok.type not in _SKIP and idx > 0:
            # name is expected to be a single ident before the colon
            pass
    if colon <= 0 or toks[0].type is not TokenType.IDENT:
        # Unparseable declaration; preserve verbatim.
        return Declaration("", toks, important=False)
    name = toks[0].value
    value = list(toks[colon + 1 :])
    important = False
    # Detect trailing "! important" (whitespace/comments already trimmed at ends).
    trimmed = _trim_seq(value)
    n = len(trimmed)
    if n >= 2:
        last = trimmed[-1]
        prev = trimmed[-2]
        if (
            last.type is TokenType.IDENT
            and last.value.lower() == "important"
            and prev.type is TokenType.DELIM
            and prev.value == "!"
        ):
            important = True
            trimmed = _trim_seq(trimmed[:-2])
    return Declaration(name, tuple(trimmed), important)


def _trim_seq(seq: list[Token] | tuple[Token, ...]) -> list[Token]:
    items = list(seq)
    start = 0
    end = len(items)
    while start < end and items[start].type in _SKIP:
        start += 1
    while end > start and items[end - 1].type in _SKIP:
        end -= 1
    return items[start:end]
