"""Correctness oracles for the minifier.

Two independent signatures, computed straight from a parsed string (never from
the transform code), used as runtime guards:

- :func:`tree_sig` — a structural signature with descendant-combinator markers in
  selector preludes and (optionally normalized) value token sequences. Used to
  prove ``SAFE``/``OPTIMIZE`` never change meaning. It catches the ``@scope … to
  (`` bug class: ``to (`` and ``to(`` produce different signatures.
- :func:`resolve` — a cascade signature mapping each ``(at-context, individual
  selector)`` to its canonical ordered declaration list (exact duplicates that
  are shadowed by a later identical declaration are collapsed). Used to prove the
  ``AGGRESSIVE`` structural rewrites are cascade-invariant. It catches dropped
  fallbacks (e.g. removing ``display:flex`` before ``display:grid``).
"""

from bengal.css.nodes import Declaration, Node, QualifiedRule
from bengal.css.optimize import normalize_value
from bengal.css.tokens import Token, TokenType

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
_WS_MARKER = ("\x00ws",)


def _is_combinator(tok: Token) -> bool:
    return tok.type is TokenType.DELIM and tok.value in _COMBINATORS


def selector_sig(tokens: tuple[Token, ...]) -> tuple[object, ...]:
    """Signature of a selector/at-rule prelude with descendant markers."""
    out: list[object] = []
    prev_boundary = False
    sep = False
    started = False
    bracket = 0
    for tok in tokens:
        if tok.type in _SKIP:
            sep = True
            continue
        if tok.type is TokenType.LBRACKET:
            bracket += 1
        cur_comb = bracket == 0 and _is_combinator(tok)
        cur_boundary = cur_comb or tok.type in _NO_SPACE_BEFORE
        if started and sep and not prev_boundary and not cur_boundary:
            out.append(_WS_MARKER)
        out.append((tok.type, tok.value))
        if tok.type is TokenType.RBRACKET and bracket > 0:
            bracket -= 1
        prev_boundary = cur_comb or tok.type in _NO_SPACE_AFTER
        sep = False
        started = True
    return tuple(out)


def value_sig(
    tokens: tuple[Token, ...], *, normalize: bool, property_name: str = ""
) -> tuple[object, ...]:
    """Signature of a declaration value (token sequence, optionally normalized)."""
    if normalize:
        tokens = normalize_value(tokens, property_name=property_name)
    out: list[object] = []
    for tok in tokens:
        if tok.type in _SKIP:
            continue
        out.append((tok.type, tok.value))
    return tuple(out)


def tree_sig(nodes: tuple[Node, ...], *, normalize: bool) -> tuple[object, ...]:
    """Structural signature for the SAFE/OPTIMIZE guard."""
    out: list[object] = []
    for node in nodes:
        if isinstance(node, Declaration):
            name = node.name if node.name.startswith("--") else node.name.lower()
            norm = normalize and not node.name.startswith("--")
            out.append(
                (
                    "d",
                    name,
                    node.important,
                    value_sig(node.value, normalize=norm, property_name=node.name),
                )
            )
        elif isinstance(node, QualifiedRule):
            out.append(("r", selector_sig(node.prelude), tree_sig(node.block, normalize=normalize)))
        else:  # AtRule
            block = None if node.block is None else tree_sig(node.block, normalize=normalize)
            out.append(("a", node.name.lower(), selector_sig(node.prelude), block))
    return tuple(out)


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
            parts.append(tuple(current))
            current = []
            continue
        current.append(tok)
    parts.append(tuple(current))
    return parts


def _canonical(decls: list[tuple[object, ...]]) -> tuple[object, ...]:
    # Drop any declaration that exactly equals a later declaration (shadowed
    # exact duplicate); preserve order and distinct (fallback) values.
    result: list[tuple[object, ...]] = []
    for i, decl in enumerate(decls):
        if decl in decls[i + 1 :]:
            continue
        result.append(decl)
    return tuple(result)


def resolve(nodes: tuple[Node, ...], *, normalize: bool) -> dict[object, tuple[object, ...]]:
    """Cascade signature for the AGGRESSIVE guard."""
    acc: dict[object, list[tuple[object, ...]]] = {}

    def walk(
        items: tuple[Node, ...], at_ctx: tuple[object, ...], sel_path: tuple[object, ...]
    ) -> None:
        for node in items:
            if isinstance(node, Declaration):
                name = node.name if node.name.startswith("--") else node.name.lower()
                norm = normalize and not node.name.startswith("--")
                key = (at_ctx, sel_path)
                acc.setdefault(key, []).append(
                    (
                        "d",
                        name,
                        node.important,
                        value_sig(node.value, normalize=norm, property_name=node.name),
                    )
                )
            elif isinstance(node, QualifiedRule):
                for sel in _split_selectors(node.prelude):
                    walk(node.block, at_ctx, (*sel_path, selector_sig(sel)))
            else:  # AtRule
                ctx = (*at_ctx, (node.name.lower(), selector_sig(node.prelude)))
                if node.block is None:
                    key = ("__stmt__", at_ctx, sel_path)
                    acc.setdefault(key, []).append(
                        ("at", node.name.lower(), selector_sig(node.prelude))
                    )
                else:
                    walk(node.block, ctx, sel_path)

    walk(nodes, (), ())
    return {k: _canonical(v) for k, v in acc.items()}


def surviving_resolve_ok(
    before: tuple[Node, ...],
    after: tuple[Node, ...],
    *,
    normalize: bool,
) -> bool:
    """True if ``after`` only drops declarations from ``before`` (dead-code guard)."""
    before_r = resolve(before, normalize=normalize)
    after_r = resolve(after, normalize=normalize)
    for key, after_decls in after_r.items():
        before_decls = before_r.get(key)
        if before_decls is None or not _decls_subsequence(after_decls, before_decls):
            return False
    return True


def _decls_subsequence(needle: tuple[object, ...], haystack: tuple[object, ...]) -> bool:
    i = 0
    for decl in haystack:
        if i < len(needle) and decl == needle[i]:
            i += 1
    return i == len(needle)
