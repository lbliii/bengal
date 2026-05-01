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


@pytest.mark.parametrize(
    "argv",
    [
        ["--version"],
        ["--help"],
        ["build", "--help"],
        ["cache", "hash", "--help"],
        ["check", "--help"],
        ["plugin", "list", "--help"],
    ],
    ids=[
        "root-version",
        "root-help",
        "build-help",
        "cache-hash-help",
        "check-help",
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
