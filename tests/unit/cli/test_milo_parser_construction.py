"""Tests that Bengal's milo CLI builds its argparse parser without conflicts.

Regression guard for the v0.3.1 release, where an auto-generated ``--no-include-version``
flag (added in milo-cli 0.2.2) collided with an explicit ``no_include_version`` param
in ``cache_hash``. Every CLI invocation crashed at parser-build time — ``bengal --version``,
``bengal --help``, everything — before any user code ran.

``build_parser()`` walks every group and command, loads lazy imports, and registers
every flag with argparse. Any duplicate ``--flag``, colliding alias, or import error
surfaces as a fast unit-test failure instead of a runtime crash in a user's terminal.
"""

from __future__ import annotations

import pytest


def test_milo_cli_parser_builds_without_conflicts():
    """Building the root CLI parser must not raise argparse.ArgumentError.

    This is the single test that would have caught v0.3.1's broken release in CI
    had the locked milo-cli matched the published one.
    """
    from bengal.cli.milo_app import cli

    parser = cli.build_parser()
    assert parser is not None


def test_milo_cli_walk_commands_resolves_every_lazy_import():
    """Every lazy-loaded command import_path must resolve.

    ``build_parser`` lazy-loads schemas; ``walk_commands`` forces resolution of
    each registered command so a broken import surfaces with a clear attribution
    (``No module named 'bengal.cli.milo_commands.X'``) rather than a cryptic
    argparse crash further down the call stack.
    """
    from bengal.cli.milo_app import cli

    resolved = list(cli.walk_commands())
    assert resolved, "CLI has no commands registered"


def test_root_help_uses_bengal_kida_command_template():
    """Root help should advertise grouped commands, not argparse's internal subparser dest."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["--help"])

    assert result.exit_code == 0
    assert "Core workflow" in result.output
    assert "Site systems" in result.output
    assert "build" in result.output
    assert "Start dev server with hot reload" in result.output
    assert "_command" not in result.output


def test_no_args_uses_same_milo_command_template():
    """No-arg invocation and --help should share the same root command surface."""
    from bengal.cli.milo_app import cli

    result = cli.invoke([])

    assert result.exit_code == 0
    assert "Useful flags" in result.output
    assert "build" in result.output
    assert "--llms-txt" in result.output
    assert "_command" not in result.output


def test_group_help_uses_bengal_kida_command_template():
    """Group help should render nested commands through Bengal's Kida output path."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["new"])

    assert result.exit_code == 0
    assert result.output.startswith("ᓚᘏᗢ bengal new")
    assert "\n\nCreate new site" in result.output
    assert "Commands" in result.output
    assert "content-type" in result.output
    assert "_command" not in result.output


def test_leaf_help_uses_bengal_kida_command_template():
    """Leaf command help should use Bengal's schema-driven Kida template."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["new", "page", "--help"])

    assert result.exit_code == 0
    assert result.output.startswith("ᓚᘏᗢ bengal new page")
    assert "\n\nCreate a new content page\n\nOptions" in result.output
    assert "--name" in result.output
    assert "(required)" in result.output
    assert "options:" not in result.output


def test_check_help_exposes_kida_security_analysis_flag():
    """Template security checks should be discoverable from check help."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["check", "--help"])

    assert result.exit_code == 0
    assert "--templates-security" in result.output


def test_every_registered_leaf_help_uses_bengal_kida_template():
    """Every registered command should get branded Kida help."""
    from bengal.cli.milo_app import cli

    for path, _command in cli.walk_commands():
        result = cli.invoke([*path.split("."), "--help"])
        assert result.exit_code == 0, path
        assert result.output.startswith(f"ᓚᘏᗢ bengal {path.replace('.', ' ')}"), path
        assert "\n\nOptions" in result.output, path
        assert "options:" not in result.output, path
        assert "_command" not in result.output, path


@pytest.mark.parametrize(
    ("argv", "canonical"),
    [
        (["b", "--help"], "bengal build"),
        (["c", "--help"], "bengal clean"),
        (["n", "page", "--help"], "bengal new page"),
        (["plugins", "list", "--help"], "bengal plugin list"),
    ],
)
def test_alias_help_uses_canonical_bengal_kida_template(argv, canonical):
    """Command and group aliases should still render the branded canonical help."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(argv)

    assert result.exit_code == 0
    assert result.output.startswith(f"ᓚᘏᗢ {canonical}")
    assert "\n\nOptions" in result.output
    assert "options:" not in result.output


def test_unknown_root_command_uses_bengal_kida_error_template():
    """Unknown commands should not fall back to raw argparse usage output."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["bork"])

    assert result.exit_code == 2
    assert result.output == ""
    assert result.stderr.startswith("ᘛ⁐̤ᕐᐷ Unknown command")
    assert "Available commands" in result.stderr
    assert "usage:" not in result.stderr
    assert "invalid choice" not in result.stderr


def test_unknown_group_command_uses_bengal_kida_error_template():
    """Unknown group subcommands should show the group's command list."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["cache", "paths"])

    assert result.exit_code == 2
    assert result.output == ""
    assert result.stderr.startswith("ᘛ⁐̤ᕐᐷ Unknown cache command")
    assert "bengal cache --help" in result.stderr
    assert "inputs" in result.stderr
    assert "hash" in result.stderr
    assert "usage:" not in result.stderr
    assert "invalid choice" not in result.stderr


def test_root_help_brands_with_bengal_logo():
    """Root help should carry the Bengal terminal mark."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["--help"])

    assert result.exit_code == 0
    assert result.output.startswith("ᓚᘏᗢ bengal")
    assert "\n\nStatic site generator" in result.output
    assert "your cores\n\nCore workflow" in result.output


def test_brand_mark_compacts_for_tight_terminals(monkeypatch):
    """Very narrow terminals use the compact Bengal mark."""
    from bengal.cli.milo_app import BengalCLI

    monkeypatch.setenv("COLUMNS", "32")
    assert BengalCLI._brand_mark() == "ᗢ"

    monkeypatch.setenv("COLUMNS", "80")
    assert BengalCLI._brand_mark() == "ᓚᘏᗢ"


def test_milo_builtin_llms_txt_is_exposed():
    """The upgraded Milo built-in llms.txt mode should work on Bengal's command tree."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["--llms-txt"])

    assert result.exit_code == 0
    assert result.output.startswith("# bengal")
    assert "## Commands" in result.output
    assert "**build**" in result.output


def test_milo_builtin_completions_are_exposed():
    """The upgraded Milo shell completion mode should include Bengal commands."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["--completions", "zsh"])

    assert result.exit_code == 0
    assert "#compdef bengal" in result.output
    assert "'build:Build your site'" in result.output


def test_output_file_writes_atomically_and_respects_force(tmp_path):
    """Bengal's Milo bridge should keep the project-wide atomic output invariant."""
    from bengal.cli.milo_app import BengalCLI

    test_cli = BengalCLI(name="test-bengal")

    @test_cli.command("echo")
    def echo() -> dict[str, bool]:
        return {"ok": True}

    output_path = tmp_path / "result.json"
    first = test_cli.invoke(["--output-file", str(output_path), "echo", "--format", "json"])

    assert first.exit_code == 0
    assert output_path.read_text() == '{\n  "ok": true\n}\n'
    assert not list(tmp_path.glob(".*.tmp"))

    blocked = test_cli.invoke(["--output-file", str(output_path), "echo", "--format", "json"])
    assert blocked.exit_code == 1
    assert "Use --force to overwrite" in blocked.stderr

    forced = test_cli.invoke(
        ["--output-file", str(output_path), "--force", "echo", "--format", "json"]
    )
    assert forced.exit_code == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["--version"],
        ["--help"],
        ["build", "--help"],
        ["audit", "--help"],
        ["cache", "hash", "--help"],
        ["check", "--help"],
        ["health", "--help"],
        ["plugin", "list", "--help"],
    ],
    ids=[
        "root-version",
        "root-help",
        "build-help",
        "audit-help",
        "cache-hash-help",
        "check-help",
        "health-help",
        "plugin-list-help",
    ],
)
def test_milo_cli_parse_args_never_raises_argparse_error(argv):
    """Parsing canonical help/version invocations must not raise ArgumentError.

    ``--help``/``--version`` exit with SystemExit(0) on the stdlib parser, which
    we swallow. What we're guarding against is ArgumentError during parser
    construction or argument registration — the v0.3.1 failure mode. ``cache
    hash --help`` is included explicitly because that was the broken command.
    """
    import argparse

    from bengal.cli.milo_app import cli

    parser = cli.build_parser()
    try:
        parser.parse_args(argv)
    except argparse.ArgumentError as exc:
        pytest.fail(f"argparse conflict on {argv!r}: {exc}")
    except SystemExit:
        pass
