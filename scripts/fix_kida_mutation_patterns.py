#!/usr/bin/env python3
"""
Fix Kida template mutation patterns.

Converts Jinja2-style mutation patterns to Kida-native syntax:
- {% set _ = list.append(...) %} → {% do list.append(...) %}
- {% set _ = list.extend(...) %} → {% do list.extend(...) %}
- {% set _ = dict.update(...) %} → {% do dict.update(...) %}

Usage:
    python scripts/fix_kida_mutation_patterns.py [--dry-run] [--template-dir DIR]

Options:
    --dry-run          Show what would be changed without modifying files
    --template-dir     Template directory (default: bengal/themes/default/templates)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from re import Match

# Pattern to match {% set _ = obj.method(...) %}
# Captures: (1) whitespace before, (2) object.method, (3) arguments, (4) whitespace after
SET_MUTATION_PATTERN = re.compile(
    r"(\s*){%\s+set\s+_\s*=\s*([a-zA-Z_][a-zA-Z0-9_.]*\.(?:append|extend|update|insert|remove|clear|pop|sort|reverse)\([^)]*\))\s*%}(\s*)",
    re.MULTILINE,
)

# Methods that are safe to convert (mutation methods)
MUTATION_METHODS = {
    "append",
    "extend",
    "update",
    "insert",
    "remove",
    "clear",
    "pop",
    "sort",
    "reverse",
}


def find_templates(template_dir: Path) -> list[Path]:
    """Find all HTML template files."""
    if not template_dir.exists():
        print(f"Error: Template directory does not exist: {template_dir}", file=sys.stderr)
        sys.exit(1)

    return list(template_dir.rglob("*.html"))


def fix_template_content(content: str, file_path: Path) -> tuple[str, int]:
    """
    Fix mutation patterns in template content.

    Returns:
        (fixed_content, number_of_replacements)
    """
    replacements = 0
    fixed_lines: list[str] = []
    lines = content.splitlines(keepends=True)

    for line in lines:
        # Match {% set _ = obj.method(...) %}
        def replace_match(match: Match[str]) -> str:
            nonlocal replacements
            indent = match.group(1)
            method_call = match.group(2)
            trailing = match.group(3)

            # Verify it's a mutation method
            if not any(f".{method}(" in method_call for method in MUTATION_METHODS):
                return match.group(0)  # Don't replace if not a mutation method

            replacements += 1
            return f"{indent}{{% do {method_call} %}}{trailing}"

        line = SET_MUTATION_PATTERN.sub(replace_match, line)

        fixed_lines.append(line)

    return "".join(fixed_lines), replacements


def process_template(file_path: Path, dry_run: bool = False) -> int:
    """Process a single template file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    fixed_content, replacements = fix_template_content(content, file_path)

    if replacements > 0:
        if dry_run:
            print(f"Would fix {replacements} pattern(s) in: {file_path}")
            # Show diff preview
            original_lines = content.splitlines()
            fixed_lines = fixed_content.splitlines()
            for i, (orig, fixed) in enumerate(zip(original_lines, fixed_lines, strict=False), 1):
                if orig != fixed:
                    print(f"  Line {i}:")
                    print(f"    - {orig.rstrip()}")
                    print(f"    + {fixed.rstrip()}")
        else:
            file_path.write_text(fixed_content, encoding="utf-8")
            print(f"Fixed {replacements} pattern(s) in: {file_path}")

    return replacements


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fix Kida template mutation patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=Path("bengal/themes/default/templates"),
        help="Template directory (default: bengal/themes/default/templates)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a single file instead of scanning directory",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")

    # Find templates to process
    if args.file:
        templates = [args.file] if args.file.exists() else []
    else:
        templates = find_templates(args.template_dir)

    if not templates:
        print("No templates found to process.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(templates)} template file(s)...\n")

    total_replacements = 0
    files_modified = 0

    for template_path in sorted(templates):
        replacements = process_template(template_path, dry_run=args.dry_run)
        if replacements > 0:
            total_replacements += replacements
            files_modified += 1

    print(f"\n{'Would modify' if args.dry_run else 'Modified'} {files_modified} file(s)")
    print(f"Total replacements: {total_replacements}")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
