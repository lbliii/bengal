"""CSS Syntax Level 3 tokenizer.

Hand-written state machine, zero regex, O(n) single pass, thread-safe (only
local variables). Produces a flat list of immutable :class:`Token` objects that
the parser and serializer consume.

The crucial guarantee for minification: an identifier immediately followed by
``(`` is consumed as a single ``FUNCTION`` token. There is therefore no token
sequence in which collapsing whitespace can turn ``ident`` + ``(`` into a
function token by accident — that decision is made here, once, structurally.
"""

from bengal.css._scanners import (
    DIGITS,
    WHITESPACE,
    is_ident_char,
    is_ident_start,
    scan_block_comment,
    scan_ident,
    scan_string,
    scan_while,
)
from bengal.css.tokens import Token, TokenType

_QUOTES = frozenset("\"'")
_SINGLE_DELIMS: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ",": TokenType.COMMA,
    ":": TokenType.COLON,
    ";": TokenType.SEMICOLON,
}


def _valid_escape(code: str, pos: int, length: int) -> bool:
    return pos + 1 < length and code[pos] == "\\" and code[pos + 1] != "\n"


def _starts_number(code: str, pos: int, length: int) -> bool:
    c0 = code[pos]
    if c0 in "+-":
        if pos + 1 < length and code[pos + 1] in DIGITS:
            return True
        return pos + 2 < length and code[pos + 1] == "." and code[pos + 2] in DIGITS
    if c0 == ".":
        return pos + 1 < length and code[pos + 1] in DIGITS
    return c0 in DIGITS


def _starts_ident(code: str, pos: int, length: int) -> bool:
    c0 = code[pos]
    if c0 == "-":
        if pos + 1 < length and (is_ident_start(code[pos + 1]) or code[pos + 1] == "-"):
            return True
        return _valid_escape(code, pos + 1, length)
    if is_ident_start(c0):
        return True
    return _valid_escape(code, pos, length)


def _consume_number(code: str, pos: int, length: int) -> int:
    if pos < length and code[pos] in "+-":
        pos += 1
    pos = scan_while(code, pos, DIGITS, length)
    if pos < length and code[pos] == "." and pos + 1 < length and code[pos + 1] in DIGITS:
        pos += 2
        pos = scan_while(code, pos, DIGITS, length)
    if pos < length and code[pos] in "eE":
        j = pos + 1
        if j < length and code[j] in "+-":
            j += 1
        if j < length and code[j] in DIGITS:
            pos = scan_while(code, j, DIGITS, length)
    return pos


def _consume_url(code: str, start: int, after_paren: int, length: int) -> tuple[Token, int]:
    """Consume an unquoted ``url(...)`` body. ``after_paren`` is just past ``(``."""
    pos = scan_while(code, after_paren, WHITESPACE, length)
    bad = False
    while pos < length:
        ch = code[pos]
        if ch == ")":
            pos += 1
            break
        if ch in WHITESPACE:
            ws_end = scan_while(code, pos, WHITESPACE, length)
            if ws_end < length and code[ws_end] == ")":
                pos = ws_end + 1
            else:
                bad = True
                pos = ws_end
            break
        if ch in _QUOTES or ch == "(":
            bad = True
            break
        if ch == "\\" and _valid_escape(code, pos, length):
            pos += 2
            continue
        pos += 1
    else:
        bad = True
    if bad:
        # Recover by consuming up to the next ")".
        while pos < length and code[pos] != ")":
            pos += 1
        if pos < length:
            pos += 1
        return Token(TokenType.BAD_URL, code[start:pos]), pos
    return Token(TokenType.URL, code[start:pos]), pos


def tokenize(code: str) -> list[Token]:
    """Tokenize ``code`` into a list of :class:`Token` objects."""
    tokens: list[Token] = []
    append = tokens.append
    pos = 0
    length = len(code)

    while pos < length:
        ch = code[pos]

        if ch in WHITESPACE:
            end = scan_while(code, pos, WHITESPACE, length)
            append(Token(TokenType.WHITESPACE, code[pos:end]))
            pos = end
            continue

        if ch == "/" and pos + 1 < length and code[pos + 1] == "*":
            end = scan_block_comment(code, pos + 2, length)
            append(Token(TokenType.COMMENT, code[pos:end]))
            pos = end
            continue

        if ch in _QUOTES:
            end, ok = scan_string(code, pos + 1, ch, length)
            kind = TokenType.STRING if ok else TokenType.BAD_STRING
            append(Token(kind, code[pos:end]))
            pos = end
            continue

        if ch == "#":
            if pos + 1 < length and (
                is_ident_char(code[pos + 1]) or _valid_escape(code, pos + 1, length)
            ):
                end = scan_ident(code, pos + 1, length)
                append(Token(TokenType.HASH, code[pos:end]))
                pos = end
                continue
            append(Token(TokenType.DELIM, "#"))
            pos += 1
            continue

        if ch in _SINGLE_DELIMS:
            append(Token(_SINGLE_DELIMS[ch], ch))
            pos += 1
            continue

        if _starts_number(code, pos, length):
            num_end = _consume_number(code, pos, length)
            if num_end < length and code[num_end] == "%":
                append(Token(TokenType.PERCENTAGE, code[pos : num_end + 1]))
                pos = num_end + 1
            elif num_end < length and _starts_ident(code, num_end, length):
                unit_end = scan_ident(code, num_end, length)
                append(
                    Token(
                        TokenType.DIMENSION,
                        code[pos:unit_end],
                        unit=code[num_end:unit_end],
                    )
                )
                pos = unit_end
            else:
                append(Token(TokenType.NUMBER, code[pos:num_end]))
                pos = num_end
            continue

        if ch == "@":
            if pos + 1 < length and _starts_ident(code, pos + 1, length):
                end = scan_ident(code, pos + 1, length)
                append(Token(TokenType.AT_KEYWORD, code[pos:end]))
                pos = end
                continue
            append(Token(TokenType.DELIM, "@"))
            pos += 1
            continue

        if ch == "<" and code[pos : pos + 4] == "<!--":
            append(Token(TokenType.CDO, "<!--"))
            pos += 4
            continue

        if ch == "-" and code[pos : pos + 3] == "-->":
            append(Token(TokenType.CDC, "-->"))
            pos += 3
            continue

        if _starts_ident(code, pos, length):
            end = scan_ident(code, pos, length)
            name = code[pos:end]
            if end < length and code[end] == "(":
                if name.lower() == "url":
                    after = scan_while(code, end + 1, WHITESPACE, length)
                    if after < length and code[after] in _QUOTES:
                        append(Token(TokenType.FUNCTION, name))
                        pos = end + 1
                    else:
                        tok, pos = _consume_url(code, pos, end + 1, length)
                        append(tok)
                else:
                    append(Token(TokenType.FUNCTION, name))
                    pos = end + 1
                continue
            append(Token(TokenType.IDENT, name))
            pos = end
            continue

        if ch == "\\" and _valid_escape(code, pos, length):
            end = scan_ident(code, pos, length)
            append(Token(TokenType.IDENT, code[pos:end]))
            pos = end
            continue

        append(Token(TokenType.DELIM, ch))
        pos += 1

    return tokens
