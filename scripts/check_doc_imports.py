#!/usr/bin/env python3
"""Pre-release documentation validation script.

Checks for stale import paths and outdated references in documentation
after package extractions (patitas, rosettes, kida).

Usage:
    python scripts/check_doc_imports.py
    python scripts/check_doc_imports.py --fix  # Show suggested fixes

Exit codes:
    0 - No issues found
    1 - Issues found (see output)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns that indicate stale imports after patitas extraction
STALE_PATTERNS = [
    # Old embedded patitas imports (now external)
    (
        r"from bengal\.rendering\.parsers\.patitas\.parser import",
        "from patitas.parser import",
        "Parser now comes from external patitas package",
    ),
    (
        r"from bengal\.rendering\.parsers\.patitas\.lexer",
        "from patitas.lexer",
        "Lexer now comes from external patitas package",
    ),
    (
        r"from bengal\.rendering\.parsers\.patitas\.parsing",
        "from patitas.parsing",
        "Parsing modules now in external patitas package",
    ),
    (
        r"from bengal\.rendering\.parsers\.patitas\.nodes import",
        "from patitas.nodes import",
        "Nodes now come from external patitas package",
    ),
    (
        r"from bengal\.rendering\.parsers\.patitas\.tokens import",
        "from patitas.tokens import",
        "Tokens now come from external patitas package",
    ),
    # Patitas listed as template engine (it's a markdown parser)
    (
        r"template_engine.*patitas",
        None,  # Manual fix needed
        "patitas is a markdown parser, not a template engine",
    ),
    # Old kida imports (now external)
    (
        r"from bengal\.rendering\.kida",
        "from kida",
        "Kida now comes from external kida package",
    ),
    # Old rosettes imports (now external)
    (
        r"from bengal\.rendering\.rosettes",
        "from rosettes",
        "Rosettes now comes from external rosettes package",
    ),
]

# Directories to check
DOC_DIRS = [
    "site/content",
    "docs",
]

# File extensions to check
DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}


def find_issues(root: Path) -> list[tuple[Path, int, str, str, str | None]]:
    """Find stale imports in documentation files.

    Returns:
        List of (file, line_num, line_content, message, suggested_fix)
    """
    issues = []

    for doc_dir in DOC_DIRS:
        dir_path = root / doc_dir
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.suffix not in DOC_EXTENSIONS:
                continue
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern, replacement, message in STALE_PATTERNS:
                    if re.search(pattern, line):
                        issues.append(
                            (
                                file_path.relative_to(root),
                                line_num,
                                line.strip(),
                                message,
                                replacement,
                            )
                        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show suggested fixes for each issue",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory to check (default: current directory)",
    )
    args = parser.parse_args()

    print(f"Checking documentation in {args.root}...")
    print()

    issues = find_issues(args.root)

    if not issues:
        print("✅ No stale imports found")
        return 0

    print(f"❌ Found {len(issues)} issue(s):")
    print()

    for file_path, line_num, line_content, message, suggested_fix in issues:
        print(f"  {file_path}:{line_num}")
        print(f"    Line: {line_content[:80]}{'...' if len(line_content) > 80 else ''}")
        print(f"    Issue: {message}")
        if args.fix and suggested_fix:
            print(f"    Fix: Change to '{suggested_fix}'")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
