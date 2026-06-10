#!/usr/bin/env python3
"""Pre-commit hook to require justification for silent exception swallowing.

Two rules are enforced over production code in ``bengal/``:

1. Every ``contextlib.suppress()`` call must have a ``# silent: <reason>``
   comment on the same line or a nearby line.
2. Every S110 / S112 noqa directive (bare ``except ...: pass`` /
   ``except ...: continue``) must carry an inline reason explaining what is
   swallowed and why it is safe. The reason may be trailing text after the
   noqa code on the same line, or a ``#`` comment on one of the next few
   lines (matching the ``ruff format`` wrapping style used in the codebase,
   e.g. ``finalization.py:626``).

Together these prevent silent, undocumented exception swallowing from creeping
back into the codebase.

Tests are exempt -- suppress is common and harmless in test teardown.

Usage:
    python scripts/check_silent_suppress.py [files...]
"""

import re
import sys
from pathlib import Path

SUPPRESS_RE = re.compile(r"contextlib\.suppress\(")
JUSTIFICATION_RE = re.compile(r"#\s*silent:")

# Matches a noqa silencing S110 (try-except-pass) or S112 (try-except-continue).
NOQA_RE = re.compile(r"#\s*noqa:\s*([A-Z0-9, ]*)")
NOQA_CODE_RE = re.compile(r"S11[02]")
# Bodies that mean "we reached the swallow without finding a reason comment".
_SWALLOW_BODY = {"pass", "continue", "return", "return None"}


def _noqa_has_reason(lines: list[str], i: int) -> bool:
    """Return True if the noqa on ``lines[i]`` carries a reason comment."""
    line = lines[i]
    # 1. Trailing reason on the same line after the noqa code(s), e.g. a
    #    "-- reason" or trailing "# reason" fragment following the codes.
    #    Strip the whole noqa+codes prefix and see if any prose (letters)
    #    remains afterwards.
    m = NOQA_RE.search(line)
    if m is not None:
        rest = line[m.end() :].strip()
        if rest and re.search(r"[A-Za-z]", rest):
            return True
    # 2. Reason comment on one of the next few body lines (before the
    #    pass/continue), matching ruff-format wrapped style.
    for w in lines[i + 1 : i + 4]:
        stripped = w.strip()
        if stripped.startswith("#") and re.search(r"#\s*\S", stripped):
            return True
        if stripped in _SWALLOW_BODY:
            break
    return False


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

        noqa_match = NOQA_RE.search(line)
        if (
            noqa_match
            and NOQA_CODE_RE.search(noqa_match.group(1))
            and not _noqa_has_reason(lines, i)
        ):
            errors.append(
                f"{path}:{i + 1}: noqa: S110/S112 without an inline reason comment "
                "(explain what is swallowed and why it is safe)"
            )
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
        print("Silent exception swallowing requires a justification comment:")
        for err in all_errors:
            print(f"  {err}")
        print(
            f"\n{len(all_errors)} violation(s) found. Add '# silent: <reason>' to "
            "contextlib.suppress(), or a reason comment to each noqa: S110/S112 swallow."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
