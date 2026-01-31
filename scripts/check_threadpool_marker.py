#!/usr/bin/env python3
"""
Pre-commit hook to check that tests using ThreadPoolExecutor have parallel_unsafe marker.

Tests that spawn their own thread pools can cause pytest-xdist worker crashes
("node down: Not properly terminated") when run in parallel. These tests must
be marked with @pytest.mark.parallel_unsafe.

Usage:
    python scripts/check_threadpool_marker.py [files...]
"""

import re
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[str]:
    """Check if a file uses ThreadPoolExecutor without parallel_unsafe marker."""
    errors = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{filepath}: Could not read file: {e}"]

    # Check if file uses ThreadPoolExecutor or ProcessPoolExecutor
    uses_executor = bool(
        re.search(r"ThreadPoolExecutor|ProcessPoolExecutor|multiprocessing\.Pool", content)
    )

    if not uses_executor:
        return []

    # Check if file has parallel_unsafe marker
    has_marker = bool(re.search(r"parallel_unsafe", content))

    if not has_marker:
        errors.append(
            f"{filepath}: Uses ThreadPoolExecutor/ProcessPoolExecutor but lacks "
            "@pytest.mark.parallel_unsafe marker. Add the marker to prevent "
            "pytest-xdist worker crashes."
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
