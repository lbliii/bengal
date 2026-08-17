"""CI guard: author skills must not invent unregistered ``bengal`` commands.

Author skills under ``agent-plugin/skills/**/SKILL.md`` teach site authors to
run Bengal from the CLI. A fabricated group such as ``bengal project ...``
(the #435 docs regression) would silently train agents on commands that do
not exist. This inventory uses the same code-context scanner rules as
``tests/unit/cli/test_cli_contract_inventory.py`` and resolves invocations
against the Milo registry plus aliases.

Root flags (``bengal --mcp``, ``bengal --llms-txt``) are not subcommands and
are skipped. Unregistered commands are proven with a ``tmp_path`` fixture —
never by writing a fake skill into ``agent-plugin/``.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from tests._testing.cli_help_snapshot import registered_command_inventory

# tests/unit/docs/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILLS_ROOT = _REPO_ROOT / "agent-plugin" / "skills"

# A markdown line opens/closes a fenced code block.
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
# An inline-code span: `...`.
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
# A `bengal <subcommand> ...` invocation inside a code segment.
_BENGAL_INVOCATION_RE = re.compile(r"bengal\s+([^`|&]+)")


def _resolver_keys() -> set[str]:
    """Registered command leaves, group names, and all CLI aliases."""
    from bengal.cli.milo_app import cli

    keys = set(registered_command_inventory())
    keys |= set(cli._groups)
    # Top-level command aliases (b -> build, s/dev -> serve, c -> clean, v -> check).
    keys |= set(cli._alias_map)
    # Group aliases (n -> new, plugins -> plugin).
    keys |= set(cli._group_alias_map)
    return keys


def _case_command_key(args: tuple[str, ...], registered: set[str]) -> str | None:
    parts: list[str] = []
    match: str | None = None
    for arg in args:
        if arg.startswith("-"):
            break
        parts.append(arg)
        candidate = ".".join(parts)
        if candidate in registered:
            match = candidate
    return match


def _code_segments(text: str) -> list[str]:
    """Return text fragments that are in a *code context* — a fenced block or an
    inline `code` span.
    """
    segments: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            segments.append(line)
        else:
            segments.extend(m.group(1) for m in _INLINE_CODE_RE.finditer(line))
    return segments


def _markdown_command_args(path: Path) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    for segment in _code_segments(path.read_text(encoding="utf-8")):
        if "bengal " not in segment:
            continue
        segment = segment.split("#", 1)[0]
        for match in _BENGAL_INVOCATION_RE.finditer(segment):
            command = "bengal " + match.group(1).strip()
            try:
                tokens = shlex.split(command)
            except ValueError:
                continue
            if len(tokens) > 1:
                args = tuple(tokens[1:])
                if args[0][:1].isdigit():
                    continue
                commands.append(args)
    return commands


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def _skill_markdown_paths() -> list[Path]:
    return sorted(_SKILLS_ROOT.rglob("SKILL.md"))


def _unresolved_commands(paths: list[Path]) -> dict[str, set[str]]:
    """Map display path -> unregistered ``bengal <subcommand>`` invocations."""
    registered = _resolver_keys()
    unresolved: dict[str, set[str]] = {}
    for path in paths:
        for args in _markdown_command_args(path):
            if not args or args[0].startswith("-"):
                continue
            if _case_command_key(args, registered) is None:
                unresolved.setdefault(_display_path(path), set()).add(" ".join(args))
    return unresolved


def test_author_skill_bengal_commands_resolve_to_registered_commands() -> None:
    """Every `bengal <subcommand>` in author skills must exist in the Milo registry.

    Guards against fabricated command groups in skills (the #435 docs regression
    was a documented-but-unregistered `bengal project ...` group). Root flags
    such as `--mcp` / `--llms-txt` are skipped, not treated as subcommands.
    """
    skills = _skill_markdown_paths()
    assert skills, "expected agent-plugin/skills/**/SKILL.md"

    invocations = [
        args
        for path in skills
        for args in _markdown_command_args(path)
        if args and not args[0].startswith("-")
    ]
    assert invocations, "author skills should include Bengal command snippets"

    unresolved = _unresolved_commands(skills)
    assert not unresolved, (
        "Author skills reference unregistered `bengal` commands "
        "(fabricated or renamed):\n"
        + "\n".join(
            f"  {path}: " + ", ".join(sorted(cmds)) for path, cmds in sorted(unresolved.items())
        )
    )


def test_unregistered_skill_command_is_reported(tmp_path: Path) -> None:
    """A fabricated group such as ``bengal project`` must fail the scanner.

    The fake SKILL.md lives under ``tmp_path`` so ``agent-plugin/`` stays clean.
    Root flags in the same file must not be reported as unresolved commands.
    """
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "# Fake skill\n\n```bash\nbengal --mcp\nbengal --llms-txt\nbengal project foo\n```\n",
        encoding="utf-8",
    )

    unresolved = _unresolved_commands([skill])
    reported = {cmd for cmds in unresolved.values() for cmd in cmds}
    assert reported == {"project foo"}, reported
