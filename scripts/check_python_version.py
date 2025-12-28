#!/usr/bin/env python3
"""Check Python version and exit with error if incorrect.

This script enforces Python 3.14+ requirement and warns if not using free-threading build.
Can be used as a pre-commit hook or in CI/CD pipelines.
"""

from __future__ import annotations

import sys

MIN_VERSION = (3, 14)


def main() -> int:
    """Check Python version and return exit code."""
    version = sys.version_info[:3]
    is_freethreading = "free-threading" in sys.version

    # Check minimum version
    if version < MIN_VERSION:
        print(
            f"ERROR: Python {MIN_VERSION[0]}.{MIN_VERSION[1]}+ required, "
            f"but found {version[0]}.{version[1]}.{version[2]}",
            file=sys.stderr,
        )
        print(f"Current Python: {sys.executable}", file=sys.stderr)
        print(
            "Solution: Use 'uv run <command>' instead of direct commands to use the project's Python version.",
            file=sys.stderr,
        )
        return 1

    # Warn if not free-threading build
    if not is_freethreading:
        print(
            f"WARNING: Not using free-threading build (3.14t). Current: {sys.executable}",
            file=sys.stderr,
        )
        print(
            "Expected: Python 3.14t free-threading build. Solution: Ensure .python-version contains '3.14t' and use 'uv run <command>'",
            file=sys.stderr,
        )
        return 0  # Don't fail, just warn

    print(f"✓ Python {version[0]}.{version[1]}.{version[2]} (free-threading build)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
