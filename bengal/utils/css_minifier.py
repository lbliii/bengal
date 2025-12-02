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

Performance: O(n) complexity via incremental context tracking.
"""

from __future__ import annotations

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Pre-compiled property patterns for context detection
_MULTI_VALUE_PROPS = frozenset(
    [
        "box-shadow",
        "background",
        "transform",
        "transition",
        "animation",
        "border",
        "margin",
        "padding",
        "filter",
        "backdrop-filter",
        "grid-template",
    ]
)
_FUNCTION_LIST_PROPS = frozenset(
    [
        "filter",
        "backdrop-filter",
        "transform",
        "transition",
        "animation",
        "background",
        "mask",
        "clip-path",
    ]
)
_SLASH_PROPS = frozenset(
    [
        "grid-area",
        "grid-column",
        "grid-row",
        "grid-column-start",
        "grid-column-end",
        "grid-row-start",
        "grid-row-end",
        "border-radius",
        "aspect-ratio",
    ]
)
_CALC_FUNCTIONS = frozenset(["calc", "clamp", "min", "max"])
_CSS_KEYWORDS = frozenset(["and", "or", "not", "only"])
_VALUE_KEYWORDS = frozenset(["inset", "outset", "repeat", "no-repeat", "space", "round"])
_CSS_UNITS = frozenset(["px", "em", "rem", "vw", "vh", "ch", "ex", "pt", "pc", "in", "cm", "mm"])
_NO_SPACE_CHARS = frozenset(",:;>{}()[+-*/=~|^&")


def minify_css(css: str) -> str:
    """
    Minify CSS by removing comments and unnecessary whitespace.

    This is a conservative minifier that:
    - Removes CSS comments (/* ... */)
    - Collapses whitespace
    - Preserves all CSS syntax (nesting, @layer, @import, etc.)
    - Does NOT transform or rewrite CSS

    Performance: O(n) via incremental context tracking.

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

    if not isinstance(css, str):
        logger.warning("css_minifier_invalid_input", input_type=type(css).__name__)
        return str(css) if css else ""

    result: list[str] = []
    length = len(css)
    i = 0
    in_string = False
    string_char = ""
    pending_whitespace = False

    # Context tracking (O(1) updates instead of O(n) lookbacks)
    paren_depth = 0  # Track function nesting
    current_property = ""  # Current CSS property name
    in_calc_function = False  # Inside calc/clamp/min/max
    in_multi_value = False  # Inside multi-value property
    in_function_list = False  # Inside filter/transform etc
    in_slash_prop = False  # Inside grid-area/border-radius etc
    in_font = False  # Inside font/font-family
    last_token = ""  # Last word/identifier (for keyword detection)

    def update_property_context(prop_name: str) -> None:
        """Update context flags based on property name."""
        nonlocal in_multi_value, in_function_list, in_slash_prop, in_font
        prop_lower = prop_name.lower()

        # Check each property category
        in_multi_value = any(p in prop_lower for p in _MULTI_VALUE_PROPS)
        in_function_list = any(p in prop_lower for p in _FUNCTION_LIST_PROPS)
        in_slash_prop = any(p in prop_lower for p in _SLASH_PROPS)
        in_font = "font" in prop_lower

    def reset_property_context() -> None:
        """Reset context at end of declaration."""
        nonlocal current_property, in_multi_value, in_function_list, in_slash_prop, in_font
        nonlocal in_calc_function
        current_property = ""
        in_multi_value = False
        in_function_list = False
        in_slash_prop = False
        in_font = False
        in_calc_function = False

    def needs_space_before(next_char: str) -> bool:
        """Determine if space is needed before next character. O(1) complexity."""
        if not result:
            return False

        prev = result[-1]

        # Inside function call - preserve space after comma
        if prev == "," and paren_depth > 0:
            return True

        # CSS keywords need spaces
        if next_char.isalpha() and last_token.lower() in _CSS_KEYWORDS:
            return True

        # After closing paren in function list property
        if prev == ")" and in_function_list and next_char.isalpha():
            return True

        # Slash in grid/border-radius properties
        if (prev == "/" or next_char == "/") and in_slash_prop:
            return True

        # Operators in calc/clamp need spaces around + and -
        # CSS spec: "both + and - operators must be surrounded by whitespace"
        # Note: * and / do NOT require spaces
        if in_calc_function:
            # Space after + or - (before number/variable)
            if prev in "+-" and (next_char.isalnum() or next_char == "-"):
                return True
            # Space before + or - (after number/variable, closing paren, or %)
            if next_char in "+-" and (prev.isalnum() or prev in ")%"):
                return True

        # Value keywords (inset, etc.) need space before values
        if last_token.lower() in _VALUE_KEYWORDS and (next_char.isdigit() or next_char == "-"):
            return True

        # After unit before negative value: "10px -5px"
        if prev.isalnum() and next_char == "-" and paren_depth == 0 and len(result) >= 2:
            # Check if last chars are a unit
            last_two = result[-2] + result[-1]
            if last_two.lower() in _CSS_UNITS or result[-1] == "%":
                return True

        # Multi-value property: space between values
        if in_multi_value and pending_whitespace:
            if prev in ")" and (next_char.isdigit() or next_char == "-" or next_char.isalpha()):
                return True
            # After unit, before next value
            if prev.isalnum() and (next_char.isdigit() or next_char == "-"):
                return True

        # Font shorthand: space before font-family after line-height
        if in_font and prev == ")" and next_char.isalpha():
            return True

        # Standard no-space characters
        if prev in _NO_SPACE_CHARS or next_char in _NO_SPACE_CHARS:
            return False

        # Alphanumeric to alphanumeric needs space (descendant selector)
        if prev.isalnum() and next_char.isalnum():
            return True

        # Selector combinators: space between selectors (.a .b, .a #b, etc.)
        # If prev ends a selector (alphanumeric) and next starts one (., #, [, alphanumeric)
        if prev.isalnum() and next_char in ".#[":
            return True

        # Default: preserve space for safety (better to have extra space than break CSS)
        return True

    # Main processing loop
    while i < length:
        char = css[i]

        # Handle strings (preserve exactly as-is)
        if in_string:
            result.append(char)
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
            if pending_whitespace and needs_space_before(char):
                result.append(" ")
            pending_whitespace = False
            in_string = True
            string_char = char
            result.append(char)
            i += 1
            continue

        # Handle CSS comments (/* ... */)
        if char == "/" and i + 1 < length and css[i + 1] == "*":
            i += 2
            while i + 1 < length and not (css[i] == "*" and css[i + 1] == "/"):
                i += 1
            i += 2
            continue

        # Handle whitespace
        if char in " \t\n\r\f":
            pending_whitespace = True
            i += 1
            continue

        # Track parentheses for function context
        if char == "(":
            # Check if entering a calc function
            if last_token.lower() in _CALC_FUNCTIONS:
                in_calc_function = True
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
            if paren_depth == 0:
                in_calc_function = False

        # Track property declarations
        if char == ":":
            # We just finished a property name
            current_property = last_token
            update_property_context(current_property)

        # Reset context at end of declaration
        if char in ";}" and paren_depth == 0:
            reset_property_context()

        # Decide whether to emit space
        if pending_whitespace:
            if needs_space_before(char):
                result.append(" ")
            pending_whitespace = False

        # Emit the character
        result.append(char)

        # Track last token (for keyword detection)
        if char.isalnum() or char in "-_":
            last_token += char
        else:
            last_token = ""

        i += 1

    minified = "".join(result)

    # Validation (unchanged)
    open_braces = minified.count("{")
    close_braces = minified.count("}")
    open_parens = minified.count("(")
    close_parens = minified.count(")")
    open_brackets = minified.count("[")
    close_brackets = minified.count("]")

    if open_braces != close_braces:
        logger.warning(
            "css_minifier_unbalanced_braces",
            open=open_braces,
            close=close_braces,
            input_length=len(css),
            output_length=len(minified),
        )
    if open_parens != close_parens:
        logger.warning(
            "css_minifier_unbalanced_parens",
            open=open_parens,
            close=close_parens,
        )
    if open_brackets != close_brackets:
        logger.warning(
            "css_minifier_unbalanced_brackets",
            open=open_brackets,
            close=close_brackets,
        )

    return minified
