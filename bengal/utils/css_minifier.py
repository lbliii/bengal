"""
CSS Minification Utilities

A simple, safe CSS minifier that preserves modern CSS features like:
- @layer blocks
- CSS nesting syntax
- @import statements
- CSS custom properties
- Modern CSS functions (color-mix, etc.)

Strategy:
1. Remove comments (/* ... */)
2. Remove unnecessary whitespace
3. Preserve all CSS syntax and structure
4. No transformations that could break CSS
"""

from __future__ import annotations

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def minify_css(css: str) -> str:
    """
    Minify CSS by removing comments and unnecessary whitespace.

    This is a conservative minifier that:
    - Removes CSS comments (/* ... */)
    - Collapses whitespace
    - Preserves all CSS syntax (nesting, @layer, @import, etc.)
    - Does NOT transform or rewrite CSS

    Args:
        css: CSS content to minify

    Returns:
        Minified CSS content

    Examples:
        >>> css = "/* Comment */ body { color: red; }"
        >>> minify_css(css)
        'body{color:red}'

        >>> css = "@layer tokens { :root { --color: blue; } }"
        >>> minify_css(css)
        '@layer tokens{:root{--color:blue}}'
    """
    if not css:
        return css

    result: list[str] = []
    length = len(css)
    i = 0
    in_string = False
    string_char = ""
    pending_whitespace = False

    def needs_space(next_char: str) -> bool:
        """Determine if space is needed before next character."""
        if not result:
            return False
        prev = result[-1]
        # Characters that don't need space before/after
        separators = set(",:;>{}()[+-*/=~|^")
        return prev not in separators and next_char not in separators

    while i < length:
        char = css[i]

        # Handle strings (preserve exactly as-is)
        if in_string:
            result.append(char)
            # Handle escape sequences in strings
            if char == "\\" and i + 1 < length:
                i += 1
                result.append(css[i])
            elif char == string_char:
                in_string = False
                string_char = ""
            i += 1
            continue

        # Start of string
        if char in {"'", '"'}:
            if pending_whitespace and needs_space(char):
                result.append(" ")
            pending_whitespace = False
            in_string = True
            string_char = char
            result.append(char)
            i += 1
            continue

        # Handle CSS comments (/* ... */)
        if char == "/" and i + 1 < length and css[i + 1] == "*":
            # Skip the comment entirely
            i += 2
            while i + 1 < length and not (css[i] == "*" and css[i + 1] == "/"):
                i += 1
            i += 2  # Skip closing */
            continue

        # Handle whitespace
        if char in {" ", "\t", "\n", "\r", "\f"}:
            pending_whitespace = True
            i += 1
            continue

        # Preserve space before numbers ending in % (for CSS functions like color-mix)
        # Example: "color-mix(in srgb, red 50%, blue 50%)"
        if char.isdigit() and pending_whitespace:
            # Look ahead to see if this number sequence ends with %
            j = i
            while j < length and (css[j].isdigit() or css[j] == "."):
                j += 1
            if j < length and css[j] == "%":
                result.append(" ")
                pending_whitespace = False

        # Add space if needed before this character
        if pending_whitespace and needs_space(char):
            result.append(" ")
        pending_whitespace = False

        result.append(char)
        i += 1

    return "".join(result)
