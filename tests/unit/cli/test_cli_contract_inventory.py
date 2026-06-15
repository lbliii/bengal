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


# ---------------------------------------------------------------------------
# Doc-tree CLI-contract lint (issue #435)
#
# The entire ``site/content/docs`` tree is greppable for ``bengal <subcommand>``
# invocations. Every one of them must resolve to a command (or alias) registered
# in ``bengal/cli/milo_app.py``. The original failure that motivated this lint
# was a fabricated ``bengal project ...`` command group that was documented but
# never registered.
#
# This tree-wide grep also surfaces a larger, pre-existing doc-vs-CLI drift
# backlog (e.g. ``bengal validate`` for the renamed ``bengal check``, and the
# ``bengal graph ...`` family that actually lives under ``bengal inspect graph``).
# Those are tracked separately and allow-listed below so this lint stays GREEN
# while still failing the moment a *new* fabricated command — or a regression
# re-introducing ``bengal project``/``bengal init`` — lands in the docs.
# ---------------------------------------------------------------------------

DOCS_TREE = ROOT / "site" / "content" / "docs"

# Pre-existing doc-vs-CLI drift, keyed by the leading token of the invocation.
# These are NOT fabricated-but-trivial typos; correcting each needs editorial
# judgement (renamed/relocated command families) and is tracked as separate
# follow-up doc work. ``project`` and ``init`` are deliberately absent so this
# lint keeps guarding against the #435 regression.
_DOCS_DRIFT_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Renamed: `bengal check` (docs still say the old `validate`).
        "validate",
        # Relocated: the graph analysis family now lives under `bengal inspect graph`.
        "graph",
        "g",
        "analyze",
        # Undocumented-in-registry power-user/legacy commands referenced by docs.
        "explain",
        "collections",
        "sources",
        "shortcodes",
        "utils",
        "icons",
        # Prose false positives — sentence fragments that happen to start "bengal X".
        "from",  # "...if you run `bengal` from the wrong directory..."
        "server",  # "...the `bengal serve` server running..."
        "capability",  # "...the core `bengal` capability boundary..."
    }
)


def _resolver_keys() -> set[str]:
    """Registered command leaves, group names, and all CLI aliases."""
    from bengal.cli.milo_app import cli

    keys = _registered_invocation_keys()
    # Top-level command aliases (b -> build, s/dev -> serve, c -> clean, v -> check).
    keys |= set(cli._alias_map)
    # Group aliases (n -> new, plugins -> plugin).
    keys |= set(cli._group_alias_map)
    return keys


def _docs_tree_command_args() -> list[tuple[Path, tuple[str, ...]]]:
    """Every `bengal <subcommand>` invocation across the docs tree, with source path."""
    found: list[tuple[Path, tuple[str, ...]]] = []
    for path in sorted(DOCS_TREE.rglob("*.md")):
        for args in _markdown_command_args(path):
            if not args or args[0].startswith("-"):
                continue
            found.append((path, args))
    return found


def test_docs_tree_bengal_commands_resolve_to_registered_commands():
    """Every documented `bengal <subcommand>` must resolve to a registered command.

    Guards against fabricated command groups in the docs (the #435 regression was
    a documented-but-unregistered `bengal project ...` group). Pre-existing drift
    is allow-listed by leading token; `project`/`init` are not, so they stay caught.
    """
    registered = _resolver_keys()
    invocations = _docs_tree_command_args()

    assert invocations, "docs tree should include Bengal command snippets"

    unresolved: dict[str, set[str]] = {}
    for path, args in invocations:
        if args[0] in _DOCS_DRIFT_ALLOWLIST:
            continue
        if _case_command_key(args, registered) is None:
            rel = str(path.relative_to(ROOT))
            unresolved.setdefault(rel, set()).add(" ".join(args))

    assert not unresolved, (
        "Docs reference unregistered `bengal` commands (fabricated or renamed). "
        "Fix the docs or, for a tracked drift family, extend _DOCS_DRIFT_ALLOWLIST:\n"
        + "\n".join(
            f"  {path}: " + ", ".join(sorted(cmds)) for path, cmds in sorted(unresolved.items())
        )
    )


def test_docs_tree_has_no_bengal_project_command():
    """The fabricated `bengal project ...` group must never reappear in the docs (#435)."""
    offenders: list[str] = []
    for path in sorted(DOCS_TREE.rglob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "bengal project" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, "`bengal project` is not a registered command group:\n" + "\n".join(
        offenders
    )
