"""
File/path filtering logic for Python extractor.

Provides utilities for determining which files should be skipped
during extraction based on exclude patterns and common conventions.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def should_skip(path: Path, exclude_patterns: list[str]) -> bool:
    """
    Check if file should be skipped during extraction.

    Handles common exclusion patterns:
    - Hidden directories (starting with .)
    - Virtual environments (.venv, venv, env, .env)
    - Site-packages (dependencies)
    - Build artifacts (__pycache__, build, dist)
    - Test files and directories

    Args:
        path: Path to check
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if path should be skipped
    """
    # NOTE: We intentionally do not require paths to exist here; callers may pass synthetic paths.
    #
    # IMPORTANT: We treat configured exclude patterns as *globs*, but with path-separator-aware
    # semantics (i.e., "*" should not match "/"). Python's built-in fnmatch works on strings and
    # allows "*" to span "/" which can cause surprising over-matches when applied to full paths.
    # We therefore:
    # - Apply filename patterns to the basename only (e.g., "*_test.py", "*/test_*.py")
    # - Apply directory patterns to path segments (e.g., "*/tests/*", "*/__pycache__/*")
    name = path.name
    path_parts = path.parts

    # Skip hidden directories (any part starting with .)
    for part in path_parts:
        if part.startswith(".") and part not in (".", ".."):
            return True

    # Skip common virtual environment and dependency directories
    common_skip_dirs = {
        "venv",
        ".venv",
        "env",
        ".env",
        "site-packages",
        "__pycache__",
        ".tox",
        ".nox",
        ".eggs",
        "build",
        "dist",
        "node_modules",
    }
    for part in path_parts:
        if part in common_skip_dirs:
            return True
        # Skip egg-info directories
        if part.endswith(".egg-info"):
            return True

    # Apply user-specified exclude patterns
    for pattern in exclude_patterns:
        if not pattern:
            continue

        # 1) Basename-only patterns (recommended): "*_test.py"
        if "/" not in pattern and fnmatch.fnmatchcase(name, pattern):
            return True

        # 2) Common config style: "*/<basename_glob>"
        # Example: "*/test_*.py" should NOT match any directory named "test_*".
        if pattern.startswith("*/") and pattern.count("/") == 1:
            if fnmatch.fnmatchcase(name, pattern[2:]):
                return True
            continue

        # 3) Directory containment: "*/<dir_glob>/*"
        # Example: "*/tests/*", "*/__pycache__/*", "*/.venv/*"
        if pattern.startswith("*/") and pattern.endswith("/*") and pattern.count("/") == 2:
            dir_glob = pattern.split("/")[1]
            if any(fnmatch.fnmatchcase(part, dir_glob) for part in path_parts):
                return True
            continue

        # 4) Extension dir pattern: "*.egg-info/*" (already covered by egg-info check above,
        # but keep this for config parity).
        if pattern.endswith("/*") and pattern.count("/") == 1:
            dir_glob = pattern[:-2]
            if any(fnmatch.fnmatchcase(part, dir_glob) for part in path_parts):
                return True
            continue

        # 5) Fallback: treat as a plain string glob against the basename.
        # This keeps behavior predictable without introducing "/"-spanning matches.
        if fnmatch.fnmatchcase(name, pattern):
            return True

    return False


