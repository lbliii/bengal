"""Low-level character scanning helpers for the CSS tokenizer.

Adapted from the rosettes state-machine lexer discipline: hand-written, zero
regex (no ReDoS), O(n) single pass, and thread-safe because every function takes
explicit position arguments and returns a new position — no shared state.

Copied (rather than imported) so ``bengal/css/`` stays a self-contained,
zero-dependency subpackage that can be extracted verbatim later.
"""

DIGITS: frozenset[str] = frozenset("0123456789")
HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdefABCDEF")
WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f")
# CSS ident code points (ASCII subset; non-ASCII >= U+0080 handled in tokenizer).
IDENT_START: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
IDENT_CONT: frozenset[str] = IDENT_START | DIGITS | frozenset("-")


def scan_while(code: str, pos: int, char_set: frozenset[str], length: int) -> int:
    """Advance while ``code[pos]`` is in ``char_set``."""
    while pos < length and code[pos] in char_set:
        pos += 1
    return pos


def is_ident_start(ch: str) -> bool:
    """Return whether ``ch`` can begin a CSS identifier."""
    return ch in IDENT_START or ch >= "\u0080"


def is_ident_char(ch: str) -> bool:
    """Return whether ``ch`` can continue a CSS identifier."""
    return ch in IDENT_CONT or ch >= "\u0080"


def scan_ident(code: str, pos: int, length: int) -> int:
    """Scan an identifier (handling escapes) starting at ``pos``.

    Assumes the caller has verified an ident start. Returns the position after
    the identifier.
    """
    while pos < length:
        ch = code[pos]
        if ch == "\\" and pos + 1 < length and code[pos + 1] != "\n":
            pos += 2
            continue
        if is_ident_char(ch):
            pos += 1
            continue
        break
    return pos


def scan_string(code: str, pos: int, quote: str, length: int) -> tuple[int, bool]:
    """Scan a string body starting after the opening ``quote``.

    Returns ``(end_position, ok)`` where ``end_position`` is just past the
    closing quote (or at the newline / end of input) and ``ok`` is ``False`` for
    an unterminated string (a ``<bad-string-token>``).
    """
    while pos < length:
        ch = code[pos]
        if ch == quote:
            return pos + 1, True
        if ch == "\n":
            return pos, False
        if ch == "\\" and pos + 1 < length:
            pos += 2
            continue
        pos += 1
    return pos, False


def scan_block_comment(code: str, pos: int, length: int) -> int:
    """Scan a ``/* ... */`` comment body starting after ``/*``.

    Returns the position just past the closing ``*/`` (or end of input for an
    unterminated comment).
    """
    while pos < length:
        if code[pos] == "*" and pos + 1 < length and code[pos + 1] == "/":
            return pos + 2
        pos += 1
    return pos
