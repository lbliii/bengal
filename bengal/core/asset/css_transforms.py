"""
CSS transformation utilities for asset processing.

Provides functions for transforming CSS syntax for browser compatibility:
- Nesting syntax transformation (&:hover, &.class → .parent:hover, .parent.class)
- Duplicate rule removal
- Lossless minification (whitespace/comment removal only)

These are internal utilities used by the Asset class during CSS processing.
"""

from __future__ import annotations

import re
from re import Match


def transform_css_nesting(css: str) -> str:
    """
    Transform CSS nesting syntax (&:hover, &.class, etc.) to traditional selectors.

    Transforms patterns like:
        .parent {
          color: red;
          &:hover { color: blue; }
        }
    Into:
        .parent { color: red; }
        .parent:hover { color: blue; }

    This ensures browser compatibility for CSS nesting syntax.

    NOTE: We should NOT write nested CSS in source files. Use traditional selectors instead.
    This is a safety net for any nested CSS that slips through.

    Args:
        css: CSS content string

    Returns:
        Transformed CSS with nesting syntax expanded
    """
    result = css

    # Pattern to match CSS rule blocks
    rule_pattern = r"([^{]+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"

    def transform_rule(match: Match[str]) -> str:
        selector = match.group(1).strip()
        block_content = match.group(2)

        # Skip @rules
        if selector.strip().startswith("@"):
            return match.group(0)

        # Clean @layer prefixes
        selector_clean = re.sub(r"^@layer\s+\w+\s*", "", selector).strip()
        has_layer = selector.strip().startswith("@layer")
        layer_decl = ""
        if has_layer:
            layer_match = re.match(r"(@layer\s+\w+)\s*", selector)
            if layer_match:
                layer_decl = layer_match.group(1) + " "

        if not selector_clean or selector_clean.startswith("@"):
            return match.group(0)

        # Find nested & selectors
        nested_pattern = r"&\s*([:.#\[\w\s-]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        nested_rules: list[str] = []

        def extract_nested(m: Match[str]) -> str:
            nested_selector_part = m.group(1).strip()
            nested_block = m.group(2)

            # Build full selector
            if (
                nested_selector_part.startswith(":")
                or nested_selector_part.startswith(".")
                or nested_selector_part.startswith("[")
                or nested_selector_part.startswith(" ")
            ):
                full_selector = selector_clean + nested_selector_part
            else:
                full_selector = selector_clean + nested_selector_part

            if has_layer:
                nested_rules.append(f"{layer_decl}{full_selector} {{{nested_block}}}")
            else:
                nested_rules.append(f"{full_selector} {{{nested_block}}}")
            return ""

        remaining_content = re.sub(
            nested_pattern, extract_nested, block_content, flags=re.MULTILINE
        )
        remaining_content = re.sub(r"\n\s*\n\s*\n", "\n\n", remaining_content)

        if nested_rules:
            return f"{selector}{{{remaining_content}}}\n" + "\n".join(nested_rules)
        else:
            return match.group(0)

    # Process iteratively to handle deeply nested cases
    for _ in range(10):
        new_result = re.sub(rule_pattern, transform_rule, result, flags=re.MULTILINE | re.DOTALL)
        if new_result == result:
            break
        result = new_result

    return result


def remove_duplicate_bare_h1_rules(css: str) -> str:
    """
    Remove duplicate bare h1 rules that appear right after scoped h1 rules.

    CSS processing sometimes creates duplicate rules like:
        .browser-header h1 { font-size: var(--text-5xl); }
        h1 { font-size: var(--text-5xl); }  # Duplicate!

    The bare h1 rule overrides the base typography rule, breaking text sizing.
    This function removes the duplicate bare h1 rules.

    Args:
        css: CSS content string

    Returns:
        CSS with duplicate bare h1 rules removed
    """
    # Pattern to match: scoped selector h1 { ... } followed by bare h1 { ... }
    # We need to match the scoped rule, then check if there's a duplicate bare h1
    pattern = r"(\.[\w-]+\s+h1\s*\{[^}]+\})\s*(h1\s*\{[^}]+\})"

    def remove_duplicate(match: Match[str]) -> str:
        scoped_rule = match.group(1)
        bare_rule = match.group(2)

        # Extract content from both rules
        scoped_content_match = re.search(r"\{([^}]+)\}", scoped_rule, re.DOTALL)
        bare_content_match = re.search(r"\{([^}]+)\}", bare_rule, re.DOTALL)

        if scoped_content_match and bare_content_match:
            scoped_content = (
                scoped_content_match.group(1).strip().replace(" ", "").replace("\n", "")
            )
            bare_content = bare_content_match.group(1).strip().replace(" ", "").replace("\n", "")

            # If content is identical, remove the bare rule
            if scoped_content == bare_content:
                return scoped_rule  # Return only the scoped rule

        # Not a duplicate, keep both
        return match.group(0)

    # Process iteratively to catch all duplicates
    result = css
    for _ in range(5):  # Max 5 iterations
        new_result = re.sub(pattern, remove_duplicate, result, flags=re.DOTALL)
        if new_result == result:
            break
        result = new_result

    return result


def lossless_minify_css(css: str) -> str:
    """
    Remove comments and redundant whitespace without touching selectors/properties.

    This intentionally avoids aggressive rewrites so modern CSS (nesting, @layer, etc.)
    remains intact.

    Args:
        css: CSS content string

    Returns:
        Minified CSS with comments and extra whitespace removed
    """
    result: list[str] = []
    length = len(css)
    i = 0
    in_string = False
    string_char = ""
    pending_whitespace = False

    def needs_space(next_char: str) -> bool:
        if not result:
            return False
        prev = result[-1]
        separators = set(",:;>{}()[+-*/")
        return prev not in separators and next_char not in separators

    while i < length:
        char = css[i]

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

        if char in {"'", '"'}:
            if pending_whitespace and needs_space(char):
                result.append(" ")
            pending_whitespace = False
            in_string = True
            string_char = char
            result.append(char)
            i += 1
            continue

        if char == "/" and i + 1 < length and css[i + 1] == "*":
            i += 2
            while i + 1 < length and not (css[i] == "*" and css[i + 1] == "/"):
                i += 1
            i += 2
            continue

        if char in {" ", "\t", "\n", "\r", "\f"}:
            pending_whitespace = True
            i += 1
            continue

        # Preserve space before number sequences ending in % (for CSS functions like color-mix)
        # Check if current char is digit and look ahead to see if % follows the number
        if char.isdigit() and pending_whitespace:
            # Look ahead to find where the number sequence ends
            j = i
            while j < length and (css[j].isdigit() or css[j] == "."):
                j += 1
            # If the sequence ends with %, preserve the space
            if j < length and css[j] == "%":
                result.append(" ")
                pending_whitespace = False

        if pending_whitespace and needs_space(char):
            result.append(" ")
        pending_whitespace = False
        result.append(char)
        i += 1

    return "".join(result)
