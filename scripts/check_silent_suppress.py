#!/usr/bin/env python3
"""Pre-commit hook to require justification for contextlib.suppress in production code.

Every contextlib.suppress() call in bengal/ must have a ``# silent: <reason>``
comment on the same line or the preceding line.  This prevents silent exception
swallowing from creeping back into the codebase.

Tests are exempt — suppress is common and harmless in test teardown.

Usage:
    python scripts/check_silent_suppress.py [files...]
"""

import re
import sys
from pathlib import Path

SUPPRESS_RE = re.compile(r"contextlib\.suppress\(")
JUSTIFICATION_RE = re.compile(r"#\s*silent:")


def check_file(path: Path) -> list[str]:
    errors = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if SUPPRESS_RE.search(line):
            # Check current line, preceding line, and next few lines
            # (ruff format may wrap the call across multiple lines)
            window = [lines[i - 1]] if i > 0 else []
            window.append(line)
            window.extend(lines[i + 1 : i + 4])
            has_reason = any(JUSTIFICATION_RE.search(w) for w in window)
            if not has_reason:
                errors.append(f"{path}:{i + 1}: contextlib.suppress() without # silent: <reason>")
    return errors


def main() -> int:
    files = (
        [Path(f) for f in sys.argv[1:]] if len(sys.argv) > 1 else list(Path("bengal").rglob("*.py"))
    )
    # Only check production code
    files = [f for f in files if str(f).startswith("bengal/") or str(f).startswith("bengal\\")]

    all_errors = []
    for f in files:
        if f.is_file():
            all_errors.extend(check_file(f))

    if all_errors:
        print("contextlib.suppress() requires a # silent: <reason> comment:")
        for err in all_errors:
            print(f"  {err}")
        print(
            f"\n{len(all_errors)} violation(s) found. Add '# silent: <reason>' to justify suppression."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
