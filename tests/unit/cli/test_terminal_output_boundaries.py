"""Architecture guard for CLI-facing terminal output boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCANNED_TREES = [
    ROOT / "bengal" / "cli",
    ROOT / "bengal" / "health",
    ROOT / "bengal" / "orchestration",
    ROOT / "bengal" / "output",
    ROOT / "bengal" / "server",
    ROOT / "bengal" / "utils" / "observability",
]

ALLOWED_DIRECT_WRITES = {
    # CLIOutput is the terminal bridge; raw stream writes belong there.
    ROOT / "bengal" / "output" / "core.py",
    # Logger and live progress are lower-level sinks that are migrated separately.
    ROOT / "bengal" / "utils" / "observability" / "logger.py",
    ROOT / "bengal" / "utils" / "observability" / "cli_progress.py",
}


def _call_name(node: ast.Call) -> str:
    func = node.func
    parts: list[str] = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


def test_cli_facing_packages_do_not_write_directly_to_terminal():
    """User-facing output should route through CLIOutput/Milo/Kida helpers."""
    violations: list[str] = []
    for tree in SCANNED_TREES:
        for path in tree.rglob("*.py"):
            if path in ALLOWED_DIRECT_WRITES:
                continue
            parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(parsed):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _call_name(node)
                if call_name == "print" or call_name in {
                    "sys.stdout.write",
                    "sys.stderr.write",
                }:
                    rel = path.relative_to(ROOT)
                    violations.append(f"{rel}:{node.lineno} uses {call_name}()")

    assert not violations, "\n".join(violations)
