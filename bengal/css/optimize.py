"""Level ``OPTIMIZE`` value normalizations (token-level, idempotent).

Only universally-safe spellings are changed; values never change *identity*:

- hex colors: lowercased and shortened (``#AABBCC`` -> ``#abc``,
  ``#AABBCCDD`` -> ``#abcd``); named-color spellings when strictly shorter.
- numeric tokens: strip a redundant leading ``+``, strip leading zeros
  (``0.5`` -> ``.5``), and strip trailing fractional zeros (``1.50`` -> ``1.5``,
  ``1.0`` -> ``1``). Units are lowercased.
- length-context unitless zero (``margin:0px`` -> ``margin:0``), never for
  time/angle units (``0s``, ``0deg``).
- ``url()`` quote stripping where the body is safe unquoted.
- shorthand-safe collapses (``margin:0 0 0 0`` -> ``margin:0``).

Custom-property declarations (``--x``) are left untouched, since their value is an
arbitrary token stream that may be substituted into any context.
"""

from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_HEX = frozenset("0123456789abcdefABCDEF")
_SKIP = (TokenType.WHITESPACE, TokenType.COMMENT)

# Canonical named colors mapped to their shortest hex form (after #510 shortening).
_NAMED_COLORS: dict[str, str] = {
    "aqua": "#0ff",
    "black": "#000",
    "blue": "#00f",
    "fuchsia": "#f0f",
    "gray": "#808080",
    "green": "#008000",
    "lime": "#0f0",
    "maroon": "#800000",
    "navy": "#000080",
    "olive": "#808000",
    "purple": "#800080",
    "red": "#f00",
    "silver": "#c0c0c0",
    "teal": "#008080",
    "white": "#fff",
    "yellow": "#ff0",
}

_HEX_TO_NAMED: dict[str, str] = {
    hex_value: name for name, hex_value in _NAMED_COLORS.items() if len(name) < len(hex_value)
}

_COLOR_PROPERTIES = frozenset(
    {
        "color",
        "background",
        "background-color",
        "border-color",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
        "outline-color",
        "text-decoration-color",
        "column-rule-color",
        "caret-color",
        "fill",
        "stroke",
    }
)

_LENGTH_UNITS = frozenset(
    {
        "px",
        "em",
        "rem",
        "ex",
        "ch",
        "lh",
        "rlh",
        "vw",
        "vh",
        "vmin",
        "vmax",
        "vb",
        "vi",
        "svw",
        "svh",
        "lvw",
        "lvh",
        "dvw",
        "dvh",
        "cm",
        "mm",
        "q",
        "in",
        "pt",
        "pc",
    }
)

_LENGTH_PROPERTIES = frozenset(
    {
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "top",
        "right",
        "bottom",
        "left",
        "inset",
        "inset-block",
        "inset-inline",
        "width",
        "height",
        "min-width",
        "min-height",
        "max-width",
        "max-height",
        "flex-basis",
        "gap",
        "row-gap",
        "column-gap",
        "border-width",
        "border-top-width",
        "border-right-width",
        "border-bottom-width",
        "border-left-width",
        "outline-width",
        "text-indent",
        "letter-spacing",
        "word-spacing",
        "scroll-margin",
        "scroll-margin-top",
        "scroll-margin-right",
        "scroll-margin-bottom",
        "scroll-margin-left",
        "scroll-padding",
        "scroll-padding-top",
        "scroll-padding-right",
        "scroll-padding-bottom",
        "scroll-padding-left",
    }
)

_SHORTHAND_4_PROPERTIES = frozenset(
    {"margin", "padding", "inset", "scroll-margin", "scroll-padding"}
)

_SAFE_URL_BODY = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./")


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


def _is_zero_number(text: str) -> bool:
    normalized = _normalize_number_text(text)
    return normalized in {"0", "-0"}


def _is_color_property(name: str) -> bool:
    lowered = name.lower()
    return lowered in _COLOR_PROPERTIES or lowered.endswith("-color")


def _is_length_property(name: str) -> bool:
    lowered = name.lower()
    return lowered in _LENGTH_PROPERTIES or lowered.endswith(("-width", "-offset", "-gap"))


def _pick_shorter_color_spelling(hex_value: str) -> Token:
    named = _HEX_TO_NAMED.get(hex_value)
    if named is not None:
        return Token(TokenType.IDENT, named)
    return Token(TokenType.HASH, hex_value)


def _normalize_token(tok: Token, *, property_name: str = "") -> Token:
    t = tok.type
    if t is TokenType.HASH and _is_color_property(property_name):
        shortened = _shorten_hex(tok.value)
        picked = _pick_shorter_color_spelling(shortened)
        return picked if picked.value != tok.value or picked.type is not tok.type else tok
    if t is TokenType.IDENT and _is_color_property(property_name):
        named = tok.value.lower()
        hex_value = _NAMED_COLORS.get(named)
        if hex_value is not None and len(hex_value) < len(named):
            return Token(TokenType.HASH, hex_value)
        return tok
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
        unit = tok.unit.lower()
        num_text = tok.value[: len(tok.value) - len(tok.unit)]
        num = _normalize_number_text(num_text)
        if (
            _is_length_property(property_name)
            and unit in _LENGTH_UNITS
            and _is_zero_number(num_text)
        ):
            return Token(TokenType.NUMBER, num)
        new = num + unit
        return tok if new == tok.value else Token(TokenType.DIMENSION, new, unit=unit)
    return tok


def _unquote_string_body(raw: str) -> str | None:
    if len(raw) < 2:
        return None
    quote = raw[0]
    if quote not in "\"'" or raw[-1] != quote:
        return None
    body = raw[1:-1]
    if not body or any(ch not in _SAFE_URL_BODY for ch in body):
        return None
    return body


def _strip_url_quotes(value: tuple[Token, ...]) -> tuple[Token, ...]:
    out: list[Token] = []
    changed = False
    i = 0
    while i < len(value):
        tok = value[i]
        if (
            tok.type is TokenType.FUNCTION
            and tok.value.lower() == "url"
            and i + 2 < len(value)
            and value[i + 1].type is TokenType.STRING
            and value[i + 2].type is TokenType.RPAREN
        ):
            body = _unquote_string_body(value[i + 1].value)
            if body is not None:
                out.append(Token(TokenType.URL, f"url({body})"))
                i += 3
                changed = True
                continue
        out.append(tok)
        i += 1
    return tuple(out) if changed else value


def _split_top_level_values(value: tuple[Token, ...]) -> list[tuple[Token, ...]]:
    parts: list[list[Token]] = [[]]
    depth = 0
    for tok in value:
        if tok.type is TokenType.WHITESPACE and depth == 0:
            if parts[-1]:
                parts.append([])
            continue
        if tok.type is TokenType.COMMENT:
            continue
        if tok.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE, TokenType.FUNCTION):
            depth += 1
        elif tok.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
            depth = max(0, depth - 1)
        if depth == 0 and tok.type is TokenType.DELIM and tok.value == "/":
            parts.append([])
            continue
        if depth == 0 and tok.type is TokenType.COMMA:
            parts.append([])
            continue
        parts[-1].append(tok)
    return [tuple(part) for part in parts if part]


def _collapse_shorthand(value: tuple[Token, ...], property_name: str) -> tuple[Token, ...]:
    lowered = property_name.lower()
    if lowered not in _SHORTHAND_4_PROPERTIES:
        return value
    parts = _split_top_level_values(value)
    if len(parts) != 4:
        return value
    if all(part == parts[0] for part in parts[1:]):
        return parts[0]
    return value


def normalize_value(value: tuple[Token, ...], *, property_name: str = "") -> tuple[Token, ...]:
    """Normalize a declaration value's tokens."""
    original = value
    value = _strip_url_quotes(value)
    value = _collapse_shorthand(value, property_name)
    changed = value is not original
    out: list[Token] = []
    for tok in value:
        nt = _normalize_token(tok, property_name=property_name)
        if nt is not tok:
            changed = True
        out.append(nt)
    return tuple(out) if changed else original


def optimize_tree(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    """Return a new tree with declaration values normalized."""
    return tuple(_optimize_node(n) for n in nodes)


def _optimize_node(node: Node) -> Node:
    if isinstance(node, Declaration):
        if node.name.startswith("--"):
            return node
        new_value = normalize_value(node.value, property_name=node.name)
        return (
            node if new_value is node.value else Declaration(node.name, new_value, node.important)
        )
    if isinstance(node, QualifiedRule):
        return QualifiedRule(node.prelude, optimize_tree(node.block))
    # AtRule
    if node.block is None:
        return node
    return AtRule(node.name, node.prelude, optimize_tree(node.block))
