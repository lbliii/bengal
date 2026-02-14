#!/usr/bin/env python3
"""
Convert CSS nesting syntax to traditional selectors.

This script finds all CSS nesting (&:hover, &.class, etc.) and converts
them to traditional selectors that work in all browsers without transformation.

Usage: python scripts/fix-css-nesting.py [file1.css] [file2.css] ...
If no files provided, processes all CSS files in bengal/themes/default/assets/css/
"""

import re
import sys
from pathlib import Path


def transform_css_nesting(content: str) -> str:
    """
    Transform CSS nesting to traditional selectors.

    Converts:
        .parent {
          color: red;
          &:hover { color: blue; }
          &.active { font-weight: bold; }
        }

    To:
        .parent {
          color: red;
        }
        .parent:hover { color: blue; }
        .parent.active { font-weight: bold; }
    """
    lines = content.split("\n")
    output = []
    parent_stack = []  # Stack of (parent_selector, brace_level)
    brace_level = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        # Count braces in this line
        open_braces = line.count("{")
        close_braces = line.count("}")
        brace_level += open_braces - close_braces

        # Detect selector line (contains { and not starting with @)
        if "{" in stripped and not stripped.startswith("@"):
            # Extract selector
            selector_part = stripped.split("{")[0].strip()
            # Clean @layer prefixes
            selector_clean = re.sub(r"^@layer\s+\w+\s*", "", selector_part).strip()

            if selector_clean and not selector_clean.startswith("@"):
                # Push parent selector
                parent_stack.append((selector_clean, brace_level - open_braces))
                output.append(line)
                i += 1
                continue

        # Detect nested selector starting with &
        if stripped.startswith("&") and parent_stack:
            parent_selector, _parent_level = parent_stack[-1]

            # Extract what comes after &
            nested_part = stripped[1:].strip()  # Remove &

            # Handle different nesting patterns
            if nested_part.startswith(":"):
                # &:hover, &::before, etc.
                new_selector = parent_selector + nested_part.split("{")[0]
            elif nested_part.startswith("."):
                # &.class
                new_selector = parent_selector + nested_part.split("{")[0]
            elif nested_part.startswith("["):
                # &[attr]
                new_selector = parent_selector + nested_part.split("{")[0]
            elif nested_part.startswith(" "):
                # & .child (descendant)
                new_selector = parent_selector + nested_part.split("{")[0]
            else:
                # &child (compound)
                new_selector = parent_selector + nested_part.split("{")[0]

            # Replace the line with transformed selector
            # Preserve indentation of the opening brace
            if "{" in nested_part:
                nested_part.split("{")[0]
                after_brace = "{" + "{".join(nested_part.split("{")[1:])
                new_line = " " * indent + new_selector + after_brace
            else:
                # Multi-line: & on one line, { on next
                new_line = " " * indent + new_selector + " {"

            output.append(new_line)
            i += 1
            continue

        # Pop parent stack when closing brace
        if "}" in stripped:
            while parent_stack and parent_stack[-1][1] >= brace_level:
                parent_stack.pop()

        output.append(line)
        i += 1

    return "\n".join(output)


def process_file(file_path: Path) -> bool:
    """Process a single CSS file. Returns True if changes were made."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Check if file has nesting (with possible whitespace)
        has_nesting = re.search(r"&\s*[:.\[#\w]", content)
        if not has_nesting:
            return False

        # Transform
        transformed = transform_css_nesting(content)

        # Only write if changed
        if transformed != content:
            file_path.write_text(transformed, encoding="utf-8")
            print(f"✓ Fixed: {file_path}")
            return True

        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) > 1:
        # Process specified files
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Process all CSS files in theme
        css_dir = Path("bengal/themes/default/assets/css")
        files = list(css_dir.rglob("*.css"))

    changed = 0
    for file_path in files:
        if process_file(file_path):
            changed += 1

    if changed == 0:
        print("No files needed changes.")
    else:
        print(f"\nFixed {changed} file(s).")


if __name__ == "__main__":
    main()
