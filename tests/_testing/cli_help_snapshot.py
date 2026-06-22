"""Capture and normalize Bengal CLI help for docs drift guards (issue #628)."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from unittest.mock import patch

from bengal.cli.milo_app import BengalCLI, cli

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SNAPSHOT = (
    _REPO_ROOT / "tests" / "unit" / "docs" / "fixtures" / "cli_root_help_commands.txt"
)
_CLI_DOC = (
    _REPO_ROOT / "site" / "content" / "docs" / "reference" / "architecture" / "tooling" / "cli.md"
)

_VERSION_LINE_RE = re.compile(r"^(?:ᓚᘏᗢ )?bengal \d+\.\d+\.\d+\S*")


def normalize_root_help(text: str) -> str:
    """Normalize help text for stable comparison (version-agnostic)."""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"bengal VERSION", "# bengal VERSION"} or _VERSION_LINE_RE.match(line):
            lines.append("bengal VERSION")
        else:
            lines.append(line.rstrip())
    normalized = "\n".join(lines).strip()
    return f"{normalized}\n" if normalized else ""


def format_doc_embedded_help(help_text: str) -> str:
    """Format normalized help for cli.md without triggering CLI contract lint."""
    lines = help_text.rstrip("\n").splitlines()
    if lines and lines[0] == "bengal VERSION":
        lines[0] = "# bengal VERSION"
    return "\n".join(lines) + "\n"


def capture_root_help_command_sections(cli_app: BengalCLI | None = None) -> str:
    """Return curated root help command sections (excludes flags and examples)."""
    app = cli_app or cli
    buffer = io.StringIO()
    with patch.object(app, "_write_stdout", side_effect=lambda text: buffer.write(text)):
        app._format_root_help()
    text = buffer.getvalue()
    if "\nUseful flags" in text:
        text = text.split("\nUseful flags", maxsplit=1)[0]
    return normalize_root_help(text)


def registered_command_inventory() -> list[str]:
    """Leaf command paths from the Milo registry."""
    app = cli
    return sorted(path for path, _command in app.walk_commands())


def parse_cli_doc_inventory(doc_text: str) -> list[str]:
    """Parse the cli-command-inventory fenced block from cli.md."""
    match = re.search(r"```text cli-command-inventory\n(.*?)```", doc_text, re.DOTALL)
    if match is None:
        raise ValueError("cli.md is missing a ```text cli-command-inventory block")
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def parse_cli_doc_root_help(doc_text: str) -> str:
    """Parse the embedded `$ bengal --help` snapshot from cli.md."""
    match = re.search(r"\$ bengal --help\n(.*?)```", doc_text, re.DOTALL)
    if match is None:
        raise ValueError("cli.md is missing a `$ bengal --help` fenced block")
    return normalize_root_help(match.group(1))


def snapshot_path(path: Path | None = None) -> Path:
    return path or _DEFAULT_SNAPSHOT


def write_snapshot(path: Path | None = None) -> Path:
    """Write the current command-section help snapshot to disk."""
    target = snapshot_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(capture_root_help_command_sections(), encoding="utf-8")
    return target


def snapshot_hash(path: Path | None = None) -> str:
    return hashlib.sha256(snapshot_path(path).read_bytes()).hexdigest()


def update_cli_doc_root_help(doc_path: Path | None = None) -> bool:
    """Replace the embedded root help block in cli.md. Returns True if changed."""
    path = doc_path or _CLI_DOC
    text = path.read_text(encoding="utf-8")
    help_text = format_doc_embedded_help(capture_root_help_command_sections())
    updated, count = re.subn(
        r"(\$ bengal --help\n)(.*?)(```)",
        lambda match: f"{match.group(1)}{help_text}\n{match.group(3)}",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"Could not update root help block in {path}")
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def update_cli_doc_inventory(doc_path: Path | None = None) -> bool:
    """Replace the cli-command-inventory block in cli.md. Returns True if changed."""
    path = doc_path or _CLI_DOC
    text = path.read_text(encoding="utf-8")
    inventory = "\n".join(registered_command_inventory())
    updated, count = re.subn(
        r"(```text cli-command-inventory\n)(.*?)(```)",
        lambda match: f"{match.group(1)}{inventory}\n{match.group(3)}",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"Could not update cli-command-inventory block in {path}")
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True
