"""Optional CSS nesting flatten (de-sugar nested rules for legacy targets).

Transforms nested qualified rules into flat selectors (``.parent .child``,
``.parent:hover``) while preserving the resolved cascade. Opt-in via
:func:`bengal.css.minify.minify_css` ``flatten_nesting=True``.
"""

from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_SKIP = (TokenType.WHITESPACE, TokenType.COMMENT)
_WS = Token(TokenType.WHITESPACE, " ")
_COMBINATORS = frozenset({">", "+", "~"})


def _strip(tokens: tuple[Token, ...]) -> tuple[Token, ...]:
    start = 0
    end = len(tokens)
    while start < end and tokens[start].type in _SKIP:
        start += 1
    while end > start and tokens[end - 1].type in _SKIP:
        end -= 1
    return tokens[start:end]


def _split_selectors(prelude: tuple[Token, ...]) -> list[tuple[Token, ...]]:
    parts: list[tuple[Token, ...]] = []
    current: list[Token] = []
    depth = 0
    for tok in prelude:
        if tok.type in (TokenType.LPAREN, TokenType.LBRACKET):
            depth += 1
        elif tok.type in (TokenType.RPAREN, TokenType.RBRACKET) and depth > 0:
            depth -= 1
        if depth == 0 and tok.type is TokenType.COMMA:
            part = _strip(tuple(current))
            if part:
                parts.append(part)
            current = []
            continue
        current.append(tok)
    part = _strip(tuple(current))
    if part:
        parts.append(part)
    return parts


def _first_significant(tokens: tuple[Token, ...]) -> Token | None:
    for tok in tokens:
        if tok.type not in _SKIP:
            return tok
    return None


def _has_nesting_selector(tokens: tuple[Token, ...]) -> bool:
    return any(tok.type is TokenType.DELIM and tok.value == "&" for tok in tokens)


def _starts_with_combinator(tokens: tuple[Token, ...]) -> bool:
    first = _first_significant(tokens)
    return first is not None and first.type is TokenType.DELIM and first.value in _COMBINATORS


def _substitute_nesting_selector(
    parent: tuple[Token, ...], child: tuple[Token, ...]
) -> tuple[Token, ...]:
    out: list[Token] = []
    for tok in child:
        if tok.type is TokenType.DELIM and tok.value == "&":
            if out and out[-1].type not in _SKIP:
                out.append(_WS)
            out.extend(parent)
            continue
        out.append(tok)
    return _strip(tuple(out))


def _combine_selectors(parent: tuple[Token, ...], child: tuple[Token, ...]) -> tuple[Token, ...]:
    child = _strip(child)
    if not child:
        return parent
    if _has_nesting_selector(child) or _starts_with_combinator(child):
        return _substitute_nesting_selector(parent, child)
    return (*parent, _WS, *child)


def _combine_preludes(parent: tuple[Token, ...], child: tuple[Token, ...]) -> tuple[Token, ...]:
    parent_sels = _split_selectors(parent)
    child_sels = _split_selectors(child)
    combined: list[tuple[Token, ...]] = [
        _combine_selectors(p, c) for p in parent_sels for c in child_sels
    ]
    if len(combined) == 1:
        return combined[0]
    out: list[Token] = []
    for idx, sel in enumerate(combined):
        if idx:
            out.append(Token(TokenType.COMMA, ","))
        out.extend(sel)
    return tuple(out)


def _flatten_qualified(rule: QualifiedRule) -> tuple[Node, ...]:
    decls: list[Declaration] = []
    nested_rules: list[QualifiedRule] = []
    passthrough: list[Node] = []
    for node in rule.block:
        if isinstance(node, Declaration):
            decls.append(node)
        elif isinstance(node, QualifiedRule):
            nested_rules.append(node)
        else:
            passthrough.append(node)

    out: list[Node] = []
    if decls or passthrough:
        out.append(QualifiedRule(rule.prelude, (*decls, *passthrough)))

    for nested in nested_rules:
        combined = _combine_preludes(rule.prelude, nested.prelude)
        out.extend(_flatten_qualified(QualifiedRule(combined, nested.block)))
    return tuple(out)


def _flatten_node(node: Node) -> tuple[Node, ...]:
    if isinstance(node, QualifiedRule):
        return _flatten_qualified(node)
    if isinstance(node, AtRule) and node.block is not None:
        flat_block = flatten_nesting_tree(node.block)
        if flat_block is node.block:
            return (node,)
        return (AtRule(node.name, node.prelude, flat_block),)
    return (node,)


def flatten_nesting_tree(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    """Return a tree with nested qualified rules hoisted to flat selectors."""
    if not nodes:
        return nodes
    changed = False
    out: list[Node] = []
    for node in nodes:
        flat = _flatten_node(node)
        if flat != (node,):
            changed = True
        out.extend(flat)
    return tuple(out) if changed else nodes


def has_nested_rules(nodes: tuple[Node, ...]) -> bool:
    """Return True if any qualified rule contains a nested qualified rule."""
    for node in nodes:
        if isinstance(node, QualifiedRule):
            for child in node.block:
                if isinstance(child, QualifiedRule):
                    return True
        elif isinstance(node, AtRule) and node.block is not None and has_nested_rules(node.block):
            return True
    return False
