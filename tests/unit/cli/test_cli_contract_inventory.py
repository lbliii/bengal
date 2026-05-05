"""CLI command inventory guards for public discovery surfaces."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLI_DOCS = ROOT / "site" / "content" / "docs" / "reference" / "architecture" / "tooling" / "cli.md"
README = ROOT / "README.md"


def _registered_command_keys() -> set[str]:
    from bengal.cli.milo_app import cli

    return {path for path, _command in cli.walk_commands()}


def _registered_invocation_keys() -> set[str]:
    from bengal.cli.milo_app import cli

    return _registered_command_keys() | set(cli._groups)


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


def _docs_inventory() -> set[str]:
    text = CLI_DOCS.read_text(encoding="utf-8")
    match = re.search(r"```text cli-command-inventory\n(?P<body>.*?)\n```", text, re.S)
    assert match, "CLI docs must include a cli-command-inventory fenced block"
    return {line.strip() for line in match.group("body").splitlines() if line.strip()}


def _markdown_command_args(path: Path) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "bengal " not in line:
            continue
        line = line.split("#", 1)[0]
        for match in re.finditer(r"bengal\s+([^`|&]+)", line):
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


def test_cli_docs_inventory_matches_milo_registry():
    """Architecture docs should list the same leaf commands as the Milo registry."""
    assert _docs_inventory() == _registered_command_keys()


def test_llms_txt_advertises_registered_command_inventory():
    """Agent-facing discovery should expose every registered command leaf."""
    from bengal.cli.milo_app import cli

    output = cli.invoke(["--llms-txt"]).output

    for command in sorted(_registered_command_keys()):
        leaf = command.rsplit(".", 1)[-1]
        assert f"**{leaf}**" in output, command


def test_readme_bengal_command_snippets_resolve_to_registered_commands():
    """README command examples should name commands that exist in the public CLI."""
    registered = _registered_invocation_keys()
    commands = _markdown_command_args(README)

    assert commands, "README should include Bengal command snippets"
    assert {args for args in commands if _case_command_key(args, registered) is None} == set()


def test_cli_docs_bengal_command_snippets_resolve_to_registered_commands():
    """Architecture doc command examples should name commands that exist."""
    registered = _registered_invocation_keys()
    commands = [args for args in _markdown_command_args(CLI_DOCS) if not args[0].startswith("-")]

    assert commands, "CLI architecture docs should include Bengal command snippets"
    assert {args for args in commands if _case_command_key(args, registered) is None} == set()


def test_alias_inventory_matches_documented_contract():
    """Documented aliases should resolve to the canonical command help."""
    from bengal.cli.milo_app import cli

    aliases = {
        ("b",): "bengal build",
        ("s",): "bengal serve",
        ("dev",): "bengal serve",
        ("c",): "bengal clean",
        ("v",): "bengal check",
        ("n", "site"): "bengal new site",
        ("plugins", "list"): "bengal plugin list",
    }

    for argv, canonical in aliases.items():
        result = cli.invoke([*argv, "--help"])
        assert result.exit_code == 0, argv
        assert result.output.startswith(f"ᓚᘏᗢ {canonical}"), argv
