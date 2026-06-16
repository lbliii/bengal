"""Level ``OPTIMIZE`` value normalizations (token-level, idempotent).

Only universally-safe spellings are changed; values never change *identity*:

- hex colors: lowercased and shortened (``#AABBCC`` -> ``#abc``,
  ``#AABBCCDD`` -> ``#abcd``).
- numeric tokens: strip a redundant leading ``+``, strip leading zeros
  (``0.5`` -> ``.5``), and strip trailing fractional zeros (``1.50`` -> ``1.5``,
  ``1.0`` -> ``1``). Units are lowercased.

Custom-property declarations (``--x``) are left untouched, since their value is an
arbitrary token stream that may be substituted into any context.
"""

from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_HEX = frozenset("0123456789abcdefABCDEF")


def _shorten_hex(value: str) -> str:
    # value includes leading "#".
    body = value[1:]
    if any(c not in _HEX for c in body):
        return value
    lower = body.lower()
    if len(lower) == 6 and lower[0] == lower[1] and lower[2] == lower[3] and lower[4] == lower[5]:
        return "#" + lower[0] + lower[2] + lower[4]
    if (
        len(lower) == 8
        and lower[0] == lower[1]
        and lower[2] == lower[3]
        and lower[4] == lower[5]
        and lower[6] == lower[7]
    ):
        return "#" + lower[0] + lower[2] + lower[4] + lower[6]
    return "#" + lower


def _normalize_number_text(text: str) -> str:
    sign = ""
    if text and text[0] in "+-":
        if text[0] == "-":
            sign = "-"
        text = text[1:]
    # Split exponent.
    exp = ""
    for marker in ("e", "E"):
        if marker in text:
            idx = text.index(marker)
            exp = "e" + text[idx + 1 :]
            text = text[:idx]
            break
    if "." in text:
        int_part, frac_part = text.split(".", 1)
        frac_part = frac_part.rstrip("0")
        int_part = int_part.lstrip("0")
        if frac_part:
            text = (int_part + "." + frac_part) if int_part else ("." + frac_part)
        else:
            text = int_part or "0"
    else:
        stripped = text.lstrip("0")
        text = stripped or "0"
    if not text or text == ".":
        text = "0"
    return sign + text + exp


def _normalize_token(tok: Token) -> Token:
    t = tok.type
    if t is TokenType.HASH:
        new = _shorten_hex(tok.value)
        return tok if new == tok.value else Token(TokenType.HASH, new)
    if t is TokenType.NUMBER:
        new = _normalize_number_text(tok.value)
        return tok if new == tok.value else Token(TokenType.NUMBER, new)
    if t is TokenType.PERCENTAGE:
        new = _normalize_number_text(tok.value[:-1]) + "%"
        return tok if new == tok.value else Token(TokenType.PERCENTAGE, new)
    if t is TokenType.DIMENSION:
        num = _normalize_number_text(tok.value[: len(tok.value) - len(tok.unit)])
        unit = tok.unit.lower()
        new = num + unit
        return tok if new == tok.value else Token(TokenType.DIMENSION, new, unit=unit)
    return tok


def normalize_value(value: tuple[Token, ...]) -> tuple[Token, ...]:
    """Normalize a declaration value's tokens."""
    changed = False
    out: list[Token] = []
    for tok in value:
        nt = _normalize_token(tok)
        if nt is not tok:
            changed = True
        out.append(nt)
    return tuple(out) if changed else value


def optimize_tree(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    """Return a new tree with declaration values normalized."""
    return tuple(_optimize_node(n) for n in nodes)


def _optimize_node(node: Node) -> Node:
    if isinstance(node, Declaration):
        if node.name.startswith("--"):
            return node
        new_value = normalize_value(node.value)
        return (
            node if new_value is node.value else Declaration(node.name, new_value, node.important)
        )
    if isinstance(node, QualifiedRule):
        return QualifiedRule(node.prelude, optimize_tree(node.block))
    # AtRule
    if node.block is None:
        return node
    return AtRule(node.name, node.prelude, optimize_tree(node.block))
