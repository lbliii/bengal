"""Architecture guard for CLI-facing terminal output boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCANNED_TREES = [ROOT / "bengal"]

ALLOWED_DIRECT_WRITES = {
    # CLIOutput is the terminal bridge; raw stream writes belong there.
    ROOT / "bengal" / "output" / "core.py",
    # Live progress owns carriage-return cursor control and is migrated separately.
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
    forbidden_calls = {
        "click.echo",
        "console.print",
        "print",
        "rich.print",
        "sys.stderr.write",
        "sys.stdout.write",
        "typer.echo",
    }
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
                if call_name in forbidden_calls:
                    rel = path.relative_to(ROOT)
                    violations.append(f"{rel}:{node.lineno} uses {call_name}()")

    assert not violations, "\n".join(violations)
