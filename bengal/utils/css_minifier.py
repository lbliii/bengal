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

    # Validate input is a string
    if not isinstance(css, str):
        logger.warning("css_minifier_invalid_input", input_type=type(css).__name__)
        return str(css) if css else ""

    result: list[str] = []
    length = len(css)
    i = 0
    in_string = False
    string_char = ""
    pending_whitespace = False

    def needs_space(next_char: str) -> bool:
        """Determine if space is needed before next character.

        Returns True if a space is semantically required (e.g., descendant selectors).
        Returns False if space can be removed (e.g., around operators, combinators).
        """
        if not result:
            return False
        prev = result[-1]

        # CRITICAL: Preserve spaces after commas inside function calls
        # Pattern: rgba(255, 255, 255) - space after comma is required
        # Check if we're inside a function call by counting unmatched opening parens
        if prev == ",":
            # Count opening and closing parens to see if we're inside a function
            open_parens = result.count("(")
            close_parens = result.count(")")
            if open_parens > close_parens:
                # We're inside a function call - preserve space after comma
                return True

        # CRITICAL: CSS keywords that require spaces around them
        # Check BEFORE checking no_space_chars, because keywords override that rule
        # Keywords like "and", "or", "not", "only" in @media queries need spaces
        if next_char.isalpha():
            # Look ahead in original CSS to see if this starts a keyword
            lookahead_pos = i
            keyword = ""
            while (
                lookahead_pos < length and lookahead_pos < i + 10 and css[lookahead_pos].isalpha()
            ):
                keyword += css[lookahead_pos]
                lookahead_pos += 1

            css_keywords = {"and", "or", "not", "only"}
            if keyword.lower() in css_keywords and (prev == ")" or prev.isalnum()):
                # Keywords need space before them if preceded by ) or alphanumeric
                return True
                # Keywords also need space after them if followed by ( or alphanumeric
                # This will be handled when processing the character after the keyword

        # CRITICAL: Preserve spaces around / in grid and border-radius properties
        # Pattern: grid-area: 1 / 1 / -1 / -1 or border-radius: 10px / 20px
        # While spaces are optional, preserving them improves readability
        if prev == "/" or next_char == "/":
            # Check if we're in a property that uses slash notation
            lookback_start = max(0, len(result) - 100)
            recent_context = "".join(result[lookback_start:])

            slash_props = [
                "grid-area:",
                "grid-column:",
                "grid-row:",
                "grid-column-start:",
                "grid-column-end:",
                "grid-row-start:",
                "grid-row-end:",
                "border-radius:",
                "aspect-ratio:",
            ]

            if any(prop in recent_context for prop in slash_props):
                # Preserve space around / in these properties
                return True

        # Characters that don't need space before/after (operators, combinators, separators)
        # These can be adjacent without spaces
        no_space_chars = set(",:;>{}()[+-*/=~|^&")

        # If either character is a no-space char, we don't need space
        # (unless it's a keyword case handled above, comma inside function, or slash in grid/border-radius)
        if prev in no_space_chars or next_char in no_space_chars:
            return False

        # For alphanumeric characters, we need space (e.g., ".a .b" descendant selector)
        if prev.isalnum() and next_char.isalnum():
            return True

        # Default: preserve space for safety (better to have extra space than break CSS)
        return True

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

        # CRITICAL: Preserve spaces around operators (+ -) in calc() and clamp() functions
        # Pattern: calc(100% - 20px) or clamp(1rem, 2vw + 1rem, 3rem)
        # Operators need spaces when between values with units: 0.65rem + 0.15vw
        if char in ("+", "-"):
            # Check if we're in a function context (calc, clamp, etc.)
            lookback_start = max(0, len(result) - 100)
            recent_context = "".join(result[lookback_start:])

            # Check if we're inside calc(), clamp(), or similar function
            function_keywords = ["calc(", "clamp(", "min(", "max("]
            in_function = any(keyword in recent_context for keyword in function_keywords)

            if in_function and pending_whitespace:
                # Preserve space BEFORE operator if there was one
                result.append(" ")
                pending_whitespace = False

                # Also ensure space AFTER operator (will be handled when processing next char)
                # But mark that we need to preserve it
                # We'll check this when processing the character after the operator

        # CRITICAL: Check if we just finished a CSS keyword and need space after it
        # Keywords like "and", "or", "not", "only" need spaces after them
        css_keywords = {"and", "or", "not", "only"}
        if (
            result and char != " " and not char.isalpha()
        ):  # We're processing a non-letter after potential keyword
            # Look backwards to see if we just finished a keyword
            keyword_end = len(result)
            if keyword_end > 0 and result[-1].isalpha():
                keyword_start = keyword_end - 1
                while keyword_start > 0 and result[keyword_start - 1].isalpha():
                    keyword_start -= 1

                keyword = "".join(result[keyword_start:keyword_end]).lower()
                if (
                    keyword in css_keywords
                    and (char == "(" or char.isalnum())
                    and pending_whitespace
                ):
                    # After a keyword, if next char is ( or alphanumeric, we need space
                    result.append(" ")
                    pending_whitespace = False

        # CRITICAL: Font shorthand requires space between line-height and font-family
        # Pattern: font: size/line-height family
        # After / and a value (ending in ) for var()), we need space before font-family
        if result and char.isalnum() and pending_whitespace:
            # Look backwards to see if we're in font shorthand context
            # Check if we have "font:" followed by something with "/"
            lookback_start = max(0, len(result) - 100)  # Look back up to 100 chars
            recent_context = "".join(result[lookback_start:])

            # Check if we're in a font shorthand: font:.../... and we just finished a value
            if "font:" in recent_context:
                # Check if there's a / in the recent context after "font:"
                font_pos = recent_context.find("font:")
                if font_pos >= 0:
                    after_font = recent_context[font_pos + 5 :]  # After "font:"
                    if "/" in after_font and result[-1] == ")":
                        # Check if we just closed a value with ) and next is alphanumeric
                        # This handles: font: var(--size)/var(--lh) [space] var(--family)
                        # We're after a var() or function call, and next char is alphanumeric
                        # This is the font-family starting - we need the space
                        result.append(" ")
                        pending_whitespace = False

        # CRITICAL: Preserve spaces after commas in font-family lists
        # Pattern: font-family: "Font1", "Font2", sans-serif;
        # Spaces after commas are usually optional but safer to preserve
        if result and char.isalnum() and pending_whitespace:
            lookback_start = max(0, len(result) - 50)
            recent_context = "".join(result[lookback_start:])

            # Check if we're in a font-family declaration
            if (
                ("font-family:" in recent_context or "font:" in recent_context)
                and result
                and result[-1] == ","
            ):
                # Check if previous char is a comma (we're after a comma in font list)
                # Preserve space after comma in font-family lists
                result.append(" ")
                pending_whitespace = False

        # CRITICAL: After an operator (+ -) in calc/clamp, preserve space before next value
        # Pattern: calc(100% - 20px) - space after - is required
        if result and result[-1] in ("+", "-") and char.isalnum():
            # Check if we're in calc/clamp context
            lookback_start = max(0, len(result) - 50)
            recent_context = "".join(result[lookback_start:])
            if (
                any(kw in recent_context for kw in ["calc(", "clamp(", "min(", "max("])
                and pending_whitespace
            ):
                # We're after an operator in a function - preserve space before value
                result.append(" ")
                pending_whitespace = False

        # CRITICAL: Preserve spaces after commas in multi-value properties
        # Pattern: box-shadow: value1, value2, value3
        # Multi-value properties: box-shadow, background, transform, etc.
        if result and result[-1] == "," and pending_whitespace:
            # Look back to see if we're in a multi-value property context
            lookback_start = max(0, len(result) - 100)
            recent_context = "".join(result[lookback_start:])

            # Multi-value properties that require spaces after commas
            multi_value_props = [
                "box-shadow:",
                "background:",
                "transform:",
                "transition:",
                "animation:",
                "border:",
                "margin:",
                "padding:",
                "grid-template-",
                "filter:",
                "backdrop-filter:",
            ]

            if any(prop in recent_context for prop in multi_value_props):
                # Preserve space after comma in multi-value properties
                result.append(" ")
                pending_whitespace = False

        # CRITICAL: Preserve spaces between values in multi-value properties
        # Pattern: box-shadow: -0.5px -0.5px 1px (space between -0.5px and -0.5px)
        # This MUST run BEFORE the inset keyword check to catch value-to-value spacing
        if result and pending_whitespace and (char.isdigit() or char == "-"):
            # Use larger lookback to catch property names even in long multi-value properties
            lookback_start = max(0, len(result) - 150)
            recent_context = "".join(result[lookback_start:])

            # Check if we're in a multi-value property
            multi_value_props = [
                "box-shadow:",
                "background:",
                "transform:",
                "transition:",
                "animation:",
                "border:",
                "margin:",
                "padding:",
                "grid-template-",
                "filter:",
                "backdrop-filter:",
            ]

            if any(prop in recent_context for prop in multi_value_props):
                prev_char = result[-1] if result else ""
                # Check if we just finished a value
                if prev_char in (")", ","):
                    # Preserve space between values
                    result.append(" ")
                    pending_whitespace = False
                elif prev_char.isalnum():
                    # Check if recent context ends with a CSS unit
                    css_units = [
                        "px",
                        "em",
                        "rem",
                        "vw",
                        "vh",
                        "%",
                        "ch",
                        "ex",
                        "pt",
                        "pc",
                        "in",
                        "cm",
                        "mm",
                    ]
                    for unit in css_units:
                        if (
                            len(recent_context) >= len(unit)
                            and recent_context[-len(unit) :].lower() == unit
                            and len(recent_context) > len(unit)
                        ):
                            # Check if we end with this unit
                            # Check if unit is preceded by a number or decimal point
                            char_before_unit = recent_context[-len(unit) - 1]
                            # Unit is valid if preceded by digit, decimal, or minus sign
                            if char_before_unit.isdigit() or char_before_unit in ".-":
                                result.append(" ")
                                pending_whitespace = False
                                break

                # CRITICAL: If previous char is alphanumeric (like 'x' from 'px') and next is minus sign,
                # we're between values in a multi-value property: -0.5px -0.5px
                # This check runs AFTER the unit check above, so it catches cases where unit detection failed
                if prev_char.isalnum() and char == "-" and pending_whitespace:
                    # We're after something like "px" and next is "-" (start of negative value)
                    # This means we need space between values: -0.5px -0.5px
                    result.append(" ")
                    pending_whitespace = False

        # CRITICAL: Preserve spaces between negative values (fallback check)
        # Pattern: -1px -1px (space between negative values)
        # This runs OUTSIDE the multi-value property check to catch all cases
        # Check if previous char is alphanumeric (like 'x' from 'px') and next is minus sign
        if result and pending_whitespace and char == "-":
            prev_char = result[-1] if result else ""
            if prev_char.isalnum():
                # We're after something like "px" and next is "-" (start of negative value)
                # This means we need space between values: -1px -1px
                # This is a safe heuristic - better to have extra space than break CSS
                result.append(" ")
                pending_whitespace = False

        # CRITICAL: Preserve spaces after closing parens when followed by function names
        # Pattern: filter: blur(5px) brightness(1.2) - space between functions is required
        # This applies to filter, backdrop-filter, transform, etc.
        if result and result[-1] == ")" and pending_whitespace and char.isalpha():
            lookback_start = max(0, len(result) - 100)
            recent_context = "".join(result[lookback_start:])

            # Properties that can have multiple space-separated functions
            function_list_props = [
                "filter:",
                "backdrop-filter:",
                "transform:",
                "transition:",
                "animation:",
                "background:",
                "mask:",
                "clip-path:",
            ]

            if any(prop in recent_context for prop in function_list_props):
                # We're after a closing paren in a function-list property
                # and next char starts a function name - preserve space
                result.append(" ")
                pending_whitespace = False

        # CRITICAL: Preserve spaces after CSS keywords like "inset" in box-shadow
        # Pattern: box-shadow: inset 0 0 0 1px, inset -0.5px -0.5px 1px
        # Keywords that need spaces after them: inset, outset, repeat, no-repeat, etc.
        # This MUST run AFTER multi-value property check and BEFORE needs_space() check
        if result and pending_whitespace and (char == "-" or char.isdigit()):
            # Look backwards to see if we just finished a CSS keyword
            lookback_start = max(0, len(result) - 30)
            recent_context = "".join(result[lookback_start:])

            # CSS keywords that require spaces after them when followed by values
            css_value_keywords = {"inset", "outset", "repeat", "no-repeat", "space", "round"}

            # Find the last word (alphanumeric sequence)
            if recent_context:
                last_word_start = len(recent_context) - 1
                while last_word_start > 0 and recent_context[last_word_start - 1].isalnum():
                    last_word_start -= 1

                last_word = recent_context[last_word_start:].lower()
                if last_word in css_value_keywords:
                    # Keyword is followed by value - preserve space
                    result.append(" ")
                    pending_whitespace = False

        # Add space if needed before this character
        # This will handle CSS keywords via needs_space() function
        if pending_whitespace and needs_space(char):
            result.append(" ")
        pending_whitespace = False

        result.append(char)
        i += 1

    minified = "".join(result)

    # Basic validation: check for balanced braces/parentheses/brackets
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
