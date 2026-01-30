#!/usr/bin/env python3
"""Check that CSS classes used in templates have corresponding CSS definitions.

This script scans HTML templates for CSS class usage and CSS files for class
definitions, then reports any "orphaned" classes that are used but not defined.

Usage:
    uv run scripts/check_template_css.py [--verbose] [--strict]

Exit codes:
    0 - All template classes have CSS definitions (or only allowlisted classes missing)
    1 - Orphaned classes found (classes used in templates but not defined in CSS)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# Paths relative to repository root
TEMPLATE_DIR = Path("bengal/themes/default/templates")
CSS_DIR = Path("bengal/themes/default/assets/css")

# Classes that are intentionally not defined in our CSS (from external libraries,
# dynamically generated, or utility classes that don't need explicit styles)
ALLOWLIST = frozenset({
    # Utility classes from base/utilities.css that may not have explicit definitions
    "sr-only",
    "visually-hidden",
    # Classes that are set dynamically via JavaScript
    "active",
    "open",
    "is-open",
    "is-active",
    "is-visible",
    "is-hidden",
    "is-loading",
    "is-expanded",
    "is-collapsed",
    "has-toc",
    "no-toc",
    "dark",
    "light",
    # Third-party library classes
    "katex",
    "mermaid",
    "highlight",
    "hljs",
    # Generic HTML/accessibility classes
    "prose",  # Defined in typography.css via complex selectors
    # Jinja/Kida template variable classes (dynamic)
    # These are patterns that may be generated at runtime
})

# Patterns for classes that are dynamically constructed (regex patterns)
DYNAMIC_CLASS_PATTERNS = [
    r"^icon-",  # icon-* classes
    r"^text-",  # text-* utility classes
    r"^bg-",  # background utility classes
    r"^border-",  # border utility classes
    r"^p[xytblr]?-",  # padding utilities
    r"^m[xytblr]?-",  # margin utilities
    r"^flex-",  # flex utilities
    r"^grid-",  # grid utilities
    r"^gap-",  # gap utilities
    r"^col-",  # column utilities
    r"^row-",  # row utilities
    r"^w-",  # width utilities
    r"^h-",  # height utilities
    r"^min-",  # min-width/height utilities
    r"^max-",  # max-width/height utilities
    r"^rounded-",  # border-radius utilities
    r"^shadow-",  # shadow utilities
    r"^opacity-",  # opacity utilities
    r"^z-",  # z-index utilities
    r"^order-",  # order utilities
    r"^space-",  # spacing utilities
    r"^font-",  # font utilities
    r"^leading-",  # line-height utilities
    r"^tracking-",  # letter-spacing utilities
    r"^align-",  # alignment utilities
    r"^justify-",  # justify utilities
    r"^items-",  # align-items utilities
    r"^content-",  # content utilities
    r"^self-",  # self alignment utilities
    r"^place-",  # place utilities
    r"^overflow-",  # overflow utilities
    r"^transition-",  # transition utilities
    r"^duration-",  # duration utilities
    r"^ease-",  # easing utilities
    r"^animate-",  # animation utilities
    r"^cursor-",  # cursor utilities
    r"^pointer-",  # pointer utilities
    r"^select-",  # select utilities
    r"^resize-",  # resize utilities
    r"^scroll-",  # scroll utilities
    r"^snap-",  # scroll snap utilities
    r"^touch-",  # touch utilities
    r"^appearance-",  # appearance utilities
    r"^outline-",  # outline utilities
    r"^ring-",  # ring utilities
    r"^fill-",  # fill utilities
    r"^stroke-",  # stroke utilities
    r"^object-",  # object-fit utilities
    r"^list-",  # list utilities
    r"^decoration-",  # text decoration utilities
    r"^underline-",  # underline utilities
    r"^transform-",  # transform utilities
    r"^origin-",  # transform origin utilities
    r"^scale-",  # scale utilities
    r"^rotate-",  # rotate utilities
    r"^translate-",  # translate utilities
    r"^skew-",  # skew utilities
    r"^filter-",  # filter utilities
    r"^backdrop-",  # backdrop filter utilities
    r"^blur-",  # blur utilities
    r"^brightness-",  # brightness utilities
    r"^contrast-",  # contrast utilities
    r"^grayscale-",  # grayscale utilities
    r"^hue-",  # hue utilities
    r"^invert-",  # invert utilities
    r"^saturate-",  # saturate utilities
    r"^sepia-",  # sepia utilities
    r"^drop-",  # drop shadow utilities
]


@dataclass
class ClassUsage:
    """Tracks where a CSS class is used."""

    file: Path
    line: int
    context: str  # The surrounding HTML for context


@dataclass
class ClassDefinition:
    """Tracks where a CSS class is defined."""

    file: Path
    line: int


def is_dynamic_class(class_name: str) -> bool:
    """Check if a class name matches a dynamic pattern."""
    return any(re.match(pattern, class_name) for pattern in DYNAMIC_CLASS_PATTERNS)


def extract_classes_from_templates(template_dir: Path) -> dict[str, list[ClassUsage]]:
    """Extract all CSS class names from HTML template files.

    Returns a dict mapping class name to list of usages.
    """
    classes: dict[str, list[ClassUsage]] = defaultdict(list)

    # Pattern to match class attributes in HTML
    # Handles: class="foo bar", class='foo bar', :class="..." (Vue-style)
    class_pattern = re.compile(r'class\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    # Pattern to match individual class names (word characters and hyphens)
    class_name_pattern = re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*")

    for template_file in template_dir.rglob("*.html"):
        try:
            content = template_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Skip Jinja/Kida comments
            if "{#" in line and "#}" in line:
                continue

            for match in class_pattern.finditer(line):
                class_attr_value = match.group(1)

                # Skip template expressions that generate classes dynamically
                if "{{" in class_attr_value or "{%" in class_attr_value:
                    # Still extract static parts if present
                    # Remove template expressions first
                    static_part = re.sub(r"\{\{[^}]+\}\}", " ", class_attr_value)
                    static_part = re.sub(r"\{%[^%]+%\}", " ", static_part)
                    class_attr_value = static_part

                # Extract individual class names
                for class_match in class_name_pattern.finditer(class_attr_value):
                    class_name = class_match.group(0)

                    # Skip template variables that look like class names
                    if class_name in ("if", "else", "end", "for", "in", "true", "false"):
                        continue

                    # Get context (trimmed line)
                    context = line.strip()[:100]

                    classes[class_name].append(
                        ClassUsage(file=template_file, line=line_num, context=context)
                    )

    return dict(classes)


def extract_classes_from_css(css_dir: Path) -> dict[str, list[ClassDefinition]]:
    """Extract all CSS class definitions from CSS files.

    Returns a dict mapping class name to list of definitions.
    """
    classes: dict[str, list[ClassDefinition]] = defaultdict(list)

    # Pattern to match CSS class selectors
    # Handles: .class-name, .class-name:hover, .parent .class-name, etc.
    class_selector_pattern = re.compile(r"\.([a-zA-Z_][a-zA-Z0-9_-]*)")

    for css_file in css_dir.rglob("*.css"):
        try:
            content = css_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Track if we're inside a comment
        in_comment = False

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Handle multi-line comments
            if "/*" in line:
                in_comment = True
            if "*/" in line:
                in_comment = False
                continue
            if in_comment:
                continue

            # Skip single-line comments
            line_no_comments = re.sub(r"/\*.*?\*/", "", line)

            for match in class_selector_pattern.finditer(line_no_comments):
                class_name = match.group(1)
                classes[class_name].append(
                    ClassDefinition(file=css_file, line=line_num)
                )

    return dict(classes)


def find_orphaned_classes(
    template_classes: dict[str, list[ClassUsage]],
    css_classes: dict[str, list[ClassDefinition]],
) -> dict[str, list[ClassUsage]]:
    """Find classes used in templates but not defined in CSS.

    Returns a dict mapping orphaned class names to their usages.
    """
    orphaned: dict[str, list[ClassUsage]] = {}

    for class_name, usages in template_classes.items():
        # Skip allowlisted classes
        if class_name in ALLOWLIST:
            continue

        # Skip dynamic classes
        if is_dynamic_class(class_name):
            continue

        # Check if class is defined in CSS
        if class_name not in css_classes:
            orphaned[class_name] = usages

    return orphaned


def main() -> int:
    """Main entry point."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    strict = "--strict" in sys.argv

    # Find repository root (look for pyproject.toml)
    cwd = Path.cwd()
    repo_root = cwd
    for parent in [cwd, *cwd.parents]:
        if (parent / "pyproject.toml").exists():
            repo_root = parent
            break

    template_dir = repo_root / TEMPLATE_DIR
    css_dir = repo_root / CSS_DIR

    if not template_dir.exists():
        print(f"Error: Template directory not found: {template_dir}", file=sys.stderr)
        return 1

    if not css_dir.exists():
        print(f"Error: CSS directory not found: {css_dir}", file=sys.stderr)
        return 1

    if verbose:
        print(f"Scanning templates in: {template_dir}")
        print(f"Scanning CSS in: {css_dir}")
        print()

    # Extract classes
    template_classes = extract_classes_from_templates(template_dir)
    css_classes = extract_classes_from_css(css_dir)

    if verbose:
        print(f"Found {len(template_classes)} unique classes in templates")
        print(f"Found {len(css_classes)} unique classes in CSS")
        print()

    # Find orphaned classes
    orphaned = find_orphaned_classes(template_classes, css_classes)

    if not orphaned:
        print("All template CSS classes have definitions.")
        return 0

    # Report orphaned classes
    print(f"Found {len(orphaned)} orphaned CSS class(es):")
    print()

    for class_name, usages in sorted(orphaned.items()):
        print(f"  .{class_name}")
        if verbose:
            for usage in usages[:3]:  # Show first 3 usages
                rel_path = usage.file.relative_to(repo_root)
                print(f"    - {rel_path}:{usage.line}")
            if len(usages) > 3:
                print(f"    ... and {len(usages) - 3} more")
        print()

    print("These classes are used in templates but have no CSS definition.")
    print("Either add CSS definitions or add them to the ALLOWLIST in this script.")

    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
