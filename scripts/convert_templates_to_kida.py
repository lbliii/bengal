#!/usr/bin/env python3
"""
Convert Jinja2 template syntax to Kida-native syntax.

This script automates the conversion of Bengal templates from Jinja2 syntax
to Kida-native syntax, enabling modern features like:
- Null coalescing: {{ x ?? 'default' }}
- Optional chaining: {{ user?.profile?.name }}
- Unless blocks: {% unless condition %}
- Range literals: {% for i in 1..10 %}
- Pattern matching: {% match x %}

Usage:
    # Dry run (show changes without applying)
    python scripts/convert_templates_to_kida.py --dry-run

    # Convert specific patterns
    python scripts/convert_templates_to_kida.py --patterns default,unless

    # Convert all patterns
    python scripts/convert_templates_to_kida.py --apply

    # Single file
    python scripts/convert_templates_to_kida.py templates/base.html --apply
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "bengal" / "themes" / "default" / "templates"


@dataclass
class Conversion:
    """A template syntax conversion."""

    name: str
    description: str
    pattern: re.Pattern
    replacement: str | Callable[[re.Match], str]
    safe: bool = True  # Can be applied automatically


# =============================================================================
# Conversion Patterns
# =============================================================================

CONVERSIONS: list[Conversion] = [
    # -------------------------------------------------------------------------
    # Phase 1: Already completed (verification only)
    # -------------------------------------------------------------------------
    Conversion(
        name="endif",
        description="{% endif %} → {% end %}",
        pattern=re.compile(r"\{%\s*endif\s*%\}"),
        replacement="{% end %}",
    ),
    Conversion(
        name="endfor",
        description="{% endfor %} → {% end %}",
        pattern=re.compile(r"\{%\s*endfor\s*%\}"),
        replacement="{% end %}",
    ),
    Conversion(
        name="endblock",
        description="{% endblock %} → {% end %}",
        pattern=re.compile(r"\{%\s*endblock\s*%\}"),
        replacement="{% end %}",
    ),
    Conversion(
        name="endmacro",
        description="{% endmacro %} → {% end %}",
        pattern=re.compile(r"\{%\s*endmacro\s*%\}"),
        replacement="{% end %}",
    ),
    Conversion(
        name="endwith",
        description="{% endwith %} → {% end %}",
        pattern=re.compile(r"\{%\s*endwith\s*%\}"),
        replacement="{% end %}",
    ),
    # -------------------------------------------------------------------------
    # Phase 2: Modern Features
    # -------------------------------------------------------------------------
    # Null coalescing: | default('x') → ?? 'x'
    # Note: | default preserves falsy values differently than ??
    # - `| default('x')` returns 'x' if value is undefined/none
    # - `?? 'x'` returns 'x' only if value is None/undefined (preserves 0, '', False)
    # This conversion is SAFE for most cases but should be reviewed
    Conversion(
        name="default_string",
        description="| default('x') → ?? 'x'",
        pattern=re.compile(r"\|\s*default\(\s*'([^']+)'\s*\)"),
        replacement=r"?? '\1'",
    ),
    Conversion(
        name="default_double_string",
        description='| default("x") → ?? "x"',
        pattern=re.compile(r'\|\s*default\(\s*"([^"]+)"\s*\)'),
        replacement=r'?? "\1"',
    ),
    Conversion(
        name="default_number",
        description="| default(30) → ?? 30",
        pattern=re.compile(r"\|\s*default\(\s*(\d+(?:\.\d+)?)\s*\)"),
        replacement=r"?? \1",
    ),
    Conversion(
        name="default_bool_true",
        description="| default(true) → ?? true",
        pattern=re.compile(r"\|\s*default\(\s*(true|True)\s*\)"),
        replacement=r"?? true",
    ),
    Conversion(
        name="default_bool_false",
        description="| default(false) → ?? false",
        pattern=re.compile(r"\|\s*default\(\s*(false|False)\s*\)"),
        replacement=r"?? false",
    ),
    Conversion(
        name="default_empty_list",
        description="| default([]) → ?? []",
        pattern=re.compile(r"\|\s*default\(\s*\[\]\s*\)"),
        replacement=r"?? []",
    ),
    Conversion(
        name="default_empty_dict",
        description="| default({}) → ?? {}",
        pattern=re.compile(r"\|\s*default\(\s*\{\}\s*\)"),
        replacement=r"?? {}",
    ),
    # -------------------------------------------------------------------------
    # Range literals
    # -------------------------------------------------------------------------
    Conversion(
        name="range_start_end",
        description="range(1, 6) → 1..5 (inclusive)",
        pattern=re.compile(r"range\(\s*(\d+)\s*,\s*(\d+)\s*\)"),
        replacement=lambda m: f"{m.group(1)}..{int(m.group(2)) - 1}",
    ),
    Conversion(
        name="range_end_only",
        description="range(5) → 0..4 (inclusive)",
        pattern=re.compile(r"range\(\s*(\d+)\s*\)"),
        replacement=lambda m: f"0..{int(m.group(1)) - 1}",
    ),
]

# Patterns that need manual review (not applied automatically)
MANUAL_REVIEW_PATTERNS: list[Conversion] = [
    Conversion(
        name="unless",
        description="{% if not x %} → {% unless x %}",
        pattern=re.compile(r"\{%\s*if\s+not\s+(\w+(?:\.\w+)*)\s*%\}"),
        replacement=r"{% unless \1 %}",
        safe=False,  # Complex conditions need review
    ),
    Conversion(
        name="optional_chain",
        description="x and x.y and x.y.z → x?.y?.z",
        pattern=re.compile(r"(\w+)\s+and\s+\1\.(\w+)\s+and\s+\1\.\2\.(\w+)"),
        replacement=r"\1?.\2?.\3",
        safe=False,  # Needs context review
    ),
]


@dataclass
class ConversionResult:
    """Result of converting a file."""

    path: Path
    original: str
    converted: str
    changes: list[tuple[str, int]]  # (conversion_name, count)

    @property
    def has_changes(self) -> bool:
        return self.original != self.converted

    @property
    def total_changes(self) -> int:
        return sum(count for _, count in self.changes)


def convert_content(
    content: str,
    conversions: list[Conversion],
) -> tuple[str, list[tuple[str, int]]]:
    """Apply conversions to content."""
    changes = []
    result = content

    for conv in conversions:
        if not conv.safe:
            continue

        if callable(conv.replacement):
            new_result = conv.pattern.sub(conv.replacement, result)
        else:
            new_result = conv.pattern.sub(conv.replacement, result)

        if new_result != result:
            count = len(conv.pattern.findall(result))
            changes.append((conv.name, count))
            result = new_result

    return result, changes


def convert_file(
    path: Path,
    conversions: list[Conversion],
) -> ConversionResult:
    """Convert a single template file."""
    content = path.read_text(encoding="utf-8")
    converted, changes = convert_content(content, conversions)

    return ConversionResult(
        path=path,
        original=content,
        converted=converted,
        changes=changes,
    )


def find_templates(root: Path) -> list[Path]:
    """Find all HTML templates."""
    return sorted(root.rglob("*.html"))


def analyze_opportunities(root: Path) -> dict[str, list[tuple[Path, int]]]:
    """Find conversion opportunities without applying them."""
    all_conversions = CONVERSIONS + MANUAL_REVIEW_PATTERNS
    opportunities: dict[str, list[tuple[Path, int]]] = {c.name: [] for c in all_conversions}

    for path in find_templates(root):
        content = path.read_text(encoding="utf-8")
        for conv in all_conversions:
            matches = conv.pattern.findall(content)
            if matches:
                opportunities[conv.name].append((path, len(matches)))

    return opportunities


def print_analysis(opportunities: dict[str, list[tuple[Path, int]]]) -> None:
    """Print analysis of conversion opportunities."""
    print("=" * 80)
    print("CONVERSION OPPORTUNITIES")
    print("=" * 80)
    print()

    all_conversions = CONVERSIONS + MANUAL_REVIEW_PATTERNS
    conv_map = {c.name: c for c in all_conversions}

    for name, files in sorted(opportunities.items()):
        if not files:
            continue

        conv = conv_map[name]
        total = sum(count for _, count in files)
        safe_marker = "✅" if conv.safe else "⚠️ "

        print(f"{safe_marker} {conv.description}")
        print(f"   Total: {total} occurrences across {len(files)} files")

        # Show top 5 files
        top_files = sorted(files, key=lambda x: x[1], reverse=True)[:5]
        for path, count in top_files:
            rel_path = path.relative_to(TEMPLATES_DIR)
            print(f"   - {rel_path}: {count}")

        print()


def apply_conversions(
    root: Path,
    patterns: list[str] | None = None,
    dry_run: bool = True,
) -> list[ConversionResult]:
    """Apply conversions to all templates."""
    # Filter conversions by pattern names
    if patterns:
        conversions = [c for c in CONVERSIONS if c.name in patterns and c.safe]
    else:
        conversions = [c for c in CONVERSIONS if c.safe]

    results = []
    for path in find_templates(root):
        result = convert_file(path, conversions)
        if result.has_changes:
            results.append(result)

            if not dry_run:
                path.write_text(result.converted, encoding="utf-8")

    return results


def print_results(results: list[ConversionResult], dry_run: bool) -> None:
    """Print conversion results."""
    action = "Would convert" if dry_run else "Converted"

    print("=" * 80)
    print(f"CONVERSION RESULTS ({action})")
    print("=" * 80)
    print()

    total_changes = 0
    for result in results:
        rel_path = result.path.relative_to(TEMPLATES_DIR)
        print(f"📄 {rel_path}")
        for name, count in result.changes:
            print(f"   - {name}: {count} changes")
        total_changes += result.total_changes

    print()
    print(f"Total: {total_changes} changes across {len(results)} files")

    if dry_run:
        print()
        print("Run with --apply to apply changes")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Jinja2 templates to Kida-native syntax")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=TEMPLATES_DIR,
        help="Template file or directory (default: default theme templates)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze conversion opportunities without applying",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply conversions (default is dry-run)",
    )
    parser.add_argument(
        "--patterns",
        type=str,
        help="Comma-separated list of patterns to apply (e.g., default_string,default_number)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show changes without applying (default)",
    )

    args = parser.parse_args()

    # Resolve path
    root = args.path if args.path.is_absolute() else PROJECT_ROOT / args.path

    if not root.exists():
        print(f"Error: Path not found: {root}")
        return 1

    # Analyze mode
    if args.analyze:
        opportunities = analyze_opportunities(root if root.is_dir() else root.parent)
        print_analysis(opportunities)
        return 0

    # Conversion mode
    patterns = args.patterns.split(",") if args.patterns else None
    dry_run = not args.apply

    if root.is_file():
        results = [convert_file(root, CONVERSIONS)]
        results = [r for r in results if r.has_changes]
        if not dry_run and results:
            root.write_text(results[0].converted, encoding="utf-8")
    else:
        results = apply_conversions(root, patterns, dry_run)

    if results:
        print_results(results, dry_run)
    else:
        print("No changes needed.")

    return 0


if __name__ == "__main__":
    exit(main())
