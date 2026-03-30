#!/usr/bin/env python3
"""Pre-commit hook to block bare ThreadPoolExecutor imports in bengal/.

All parallel work must go through WorkScope (bengal.utils.concurrency.work_scope).
Direct ThreadPoolExecutor usage bypasses shutdown safety, context propagation,
and timeout enforcement — causing CI hangs in free-threaded Python 3.14t.

Allowed files:
- bengal/utils/concurrency/executor.py (managed_executor wrapper)
- bengal/utils/concurrency/work_scope.py (WorkScope implementation)
- bengal/server/build_executor.py (dev server lifecycle management)

Usage:
    python scripts/check_bare_threadpool.py [files...]
"""

import re
import sys
from pathlib import Path

ALLOWED = {
    "bengal/utils/concurrency/executor.py",
    "bengal/utils/concurrency/work_scope.py",
    "bengal/server/build_executor.py",
}

PATTERN = re.compile(
    r"(?:from\s+concurrent\.futures\s+import\s+.*ThreadPoolExecutor"
    r"|concurrent\.futures\.ThreadPoolExecutor"
    r"|=\s*ThreadPoolExecutor\()"
)


def check_file(filepath: Path) -> list[str]:
    errors = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{filepath}: Could not read file: {e}"]

    # Normalize path for comparison
    rel = str(filepath).replace("\\", "/")
    for allowed in ALLOWED:
        if rel.endswith(allowed):
            return []

    for i, line in enumerate(content.splitlines(), 1):
        # Skip comments and docstrings
        stripped = line.lstrip()
        if stripped.startswith(("#", '"""', "'''")):
            continue
        if PATTERN.search(line):
            errors.append(
                f"{filepath}:{i}: Bare ThreadPoolExecutor import. "
                "Use WorkScope from bengal.utils.concurrency.work_scope instead."
            )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    all_errors = []
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if path.suffix == ".py" and "bengal/" in str(path):
            errors = check_file(path)
            all_errors.extend(errors)

    if all_errors:
        print("\n".join(all_errors), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
