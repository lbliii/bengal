"""Gate: every `cli.error(...)` in bengal/cli/ must be paired with guidance.

Rule (see `.context/cli-tip-classifier.py` for the research that produced it):

  Every `cli.error(...)` call must be followed — within 3 source lines — by a
  guidance call: `cli.tip(...)`, `cli.info(...)`, or `cli.render_write(...)`.

  The pair encodes "what's wrong" + "what to do about it." The error alone is
  a dead end for the user (and for an AI agent driving the CLI).

If this test fails for a new `cli.error` you added, pair it with a tip that
names a concrete action — a command to run, a flag to fix, a file to edit.

Cancellation flows (`cli.warning("Cancelled")`) are not flagged — they are not
errors.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_ROOT = REPO_ROOT / "bengal" / "cli"

GUIDANCE_WINDOW = 3
GUIDANCE = re.compile(r"\bcli\.(tip|info|render_write)\s*\(")


def _is_cli_error_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "error":
        return False
    value = func.value
    return isinstance(value, ast.Name) and value.id == "cli"


def _scan_cli_error_gaps() -> list[tuple[str, int, str]]:
    gaps: list[tuple[str, int, str]] = []
    for py_file in sorted(CLI_ROOT.rglob("*.py")):
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        rel = str(py_file.relative_to(REPO_ROOT))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Expr) and _is_cli_error_call(node.value)):
                continue
            lineno = node.lineno
            end = min(len(lines), lineno + GUIDANCE_WINDOW)
            window = "\n".join(lines[lineno:end])
            if not GUIDANCE.search(window):
                snippet = lines[lineno - 1].strip()
                gaps.append((rel, lineno, snippet))
    return gaps


class TestCliErrorGuidancePairing:
    def test_every_cli_error_has_guidance_follow_up(self) -> None:
        gaps = _scan_cli_error_gaps()
        if gaps:
            formatted = "\n".join(f"  - {rel}:{line}  {snip}" for rel, line, snip in gaps)
            pytest.fail(
                "Found `cli.error(...)` calls without a guidance follow-up "
                "(cli.tip / cli.info / cli.render_write) within "
                f"{GUIDANCE_WINDOW} lines:\n\n{formatted}\n\n"
                "Pair each error with a concrete action the user can take. "
                "Prefer commands (`Run bengal validate`) over prose advice."
            )
