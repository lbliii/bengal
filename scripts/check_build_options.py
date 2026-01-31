#!/usr/bin/env python3
"""
Pre-commit hook to check for outdated BuildOptions API usage.

The BuildOptions class uses `force_sequential` instead of `parallel`.
This hook catches tests that use the old API.

Usage:
    python scripts/check_build_options.py [files...]
"""

import re
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[str]:
    """Check if a file uses outdated BuildOptions API."""
    errors = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{filepath}: Could not read file: {e}"]

    # Check for outdated BuildOptions(parallel=...) usage
    matches = list(re.finditer(r"BuildOptions\([^)]*parallel\s*=", content))

    for match in matches:
        # Find line number
        line_num = content[: match.start()].count("\n") + 1
        errors.append(
            f"{filepath}:{line_num}: Uses outdated BuildOptions(parallel=...) API. "
            "Use force_sequential=True/False instead."
        )

    # Check for .build(parallel=...) usage
    matches = list(re.finditer(r"\.build\([^)]*parallel\s*=", content))

    for match in matches:
        line_num = content[: match.start()].count("\n") + 1
        errors.append(
            f"{filepath}:{line_num}: Uses outdated .build(parallel=...) API. "
            "Use BuildOptions(force_sequential=...) instead."
        )

    return errors


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        return 0

    all_errors = []
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if path.suffix == ".py" and "tests/" in str(path):
            errors = check_file(path)
            all_errors.extend(errors)

    if all_errors:
        print("\n".join(all_errors), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
