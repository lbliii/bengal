"""Character sets for O(1) classification.

All sets are frozensets for:
- O(1) membership testing (vs O(n) for strings)
- Immutability (thread-safe)
- Module-level caching (no per-call allocation)

Reference: CommonMark 0.31.2 specification

Usage:
    from bengal.rendering.parsers.patitas.parsing.charsets import ASCII_PUNCTUATION

    if char in ASCII_PUNCTUATION:  # O(1) lookup
        ...
"""

from __future__ import annotations

import unicodedata

# CommonMark: ASCII punctuation characters
# https://spec.commonmark.org/0.31.2/#ascii-punctuation-character
ASCII_PUNCTUATION: frozenset[str] = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


def is_unicode_punctuation(char: str) -> bool:
    """Check if character is Unicode punctuation (Pc, Pd, Pe, Pf, Pi, Po, Ps, or Sc, Sk, Sm, So).

    CommonMark uses Unicode punctuation categories for flanking rules.
    This includes ASCII punctuation as a subset.
    """
    if not char:
        return False
    if char in ASCII_PUNCTUATION:
        return True
    cat = unicodedata.category(char)
    # P* = Punctuation, S* = Symbol
    return cat.startswith("P") or cat.startswith("S")


# CommonMark: Unicode whitespace (Zs category + control chars)
# https://spec.commonmark.org/0.31.2/#whitespace-character
# Note: ASCII whitespace for basic checks
WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f\v")

# Extended whitespace including empty string (for boundary checks)
WHITESPACE_OR_EMPTY: frozenset[str] = WHITESPACE | frozenset([""])


def is_unicode_whitespace(char: str) -> bool:
    """Check if character is Unicode whitespace.

    CommonMark uses Unicode whitespace for emphasis flanking rules.
    Includes ASCII whitespace and Unicode category Zs (space separator).
    Also treats empty string as whitespace (for boundary checks).
    """
    if not char:
        return True  # Empty string counts as whitespace for boundary checks
    if char in WHITESPACE:
        return True
    cat = unicodedata.category(char)
    return cat == "Zs"  # Space separator (includes non-breaking space)


# Inline special characters that trigger tokenizer dispatch
INLINE_SPECIAL: frozenset[str] = frozenset("*_`[!\\\n<{~$&")

# Emphasis delimiter characters
EMPHASIS_DELIMITERS: frozenset[str] = frozenset("*_~")

# Valid fence characters
FENCE_CHARS: frozenset[str] = frozenset("`~")

# List marker characters
UNORDERED_LIST_MARKERS: frozenset[str] = frozenset("-*+")

# Block quote marker
BLOCK_QUOTE_MARKER: frozenset[str] = frozenset(">")

# Thematic break characters
THEMATIC_BREAK_CHARS: frozenset[str] = frozenset("-*_")

# Digits for ordered list detection
DIGITS: frozenset[str] = frozenset("0123456789")

# Hex digits for entity references
HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdefABCDEF")

# Valid characters in link/image destinations (simplified)
LINK_DEST_SPECIAL: frozenset[str] = frozenset(" \t\n<>")

# Characters that need HTML escaping
HTML_ESCAPE_CHARS: frozenset[str] = frozenset('<>&"')
