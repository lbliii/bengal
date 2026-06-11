"""Guard the CLI render-format vocabulary (Finding 25, #387).

Bengal injects an envelope ``--format`` flag onto every command (it drives the
``-o FILE`` serialization path). Commands that render a result for humans *and*
machines also declare their own ``output_format``/``export_format`` parameter.
Before #387 those two collided: ``bengal inspect page --help`` advertised both
``--output-format`` and ``--format``, two competing format rows for one concept.

These tests enumerate the live command tree via ``cli.walk_commands()`` and
assert the standardized vocabulary holds:

* a command never shows two render-format rows in ``--help`` — the injected
  ``--format`` is suppressed when the command carries its own format flag;
* every render-format flag that offers a machine-readable mode spells it
  ``json`` (no ``j``/``machine``/``data`` synonyms);
* every render-format default is a value the shared vocabulary registry allows.

Discriminating-assertion note (#130 lesson): ``test_injected_format_flag_is_
suppressed_when_command_owns_one`` fails the moment the ``milo_app`` suppression
is reverted — verified by temporarily restoring the unconditional ``--format``
row and watching this test go red before finalizing.
"""

from __future__ import annotations

import re

import pytest

from bengal.cli.format_options import (
    ALLOWED_RENDER_FORMATS,
    MACHINE_FORMAT,
    RENDER_FORMAT_PARAMS,
)
from bengal.cli.milo_app import cli

# A leaf-help option row for a flag named like a format selector, e.g.
# "  --output-format   Output format: console, json (default: console)".
_FORMAT_ROW = re.compile(r"^\s+--(?P<flag>[\w-]*format)\b", re.MULTILINE)

# The injected envelope flag, rendered exactly as ``--format`` (not a prefix of
# ``--output-format``/``--export-format``, which embed the word "format").
_INJECTED_FORMAT_ROW = re.compile(r"^\s+--format\b", re.MULTILINE)


def _commands_with_own_render_format() -> list[tuple[str, object]]:
    """Return (dotted_path, command) for every command that declares a render-format param."""
    found = []
    for path, cmd in cli.walk_commands():
        properties = cmd.schema.get("properties", {})
        if any(name in RENDER_FORMAT_PARAMS for name in properties):
            found.append((path, cmd))
    assert found, "no commands declare a render-format param — registry empty?"
    return found


def _render_format_params() -> list[tuple[str, str, dict]]:
    """Return (dotted_path, param_name, spec) for every render-format parameter."""
    params = []
    for path, cmd in cli.walk_commands():
        for name, spec in cmd.schema.get("properties", {}).items():
            if name in RENDER_FORMAT_PARAMS and isinstance(spec, dict):
                params.append((path, name, spec))
    assert params, "no render-format parameters discovered"
    return params


def _enumerated_choices(description: str) -> list[str]:
    """Pull the comma/``or``-separated choice tokens out of a format Description.

    Handles both the standardized "Output format: a, b, c" template and the
    export-only "Export format: mermaid or dot" phrasing.
    """
    _, _, tail = description.partition(":")
    tail = tail.strip()
    if not tail:
        return []
    tail = tail.replace(" or ", ", ").replace(", or ", ", ")
    return [tok.strip() for tok in tail.split(",") if tok.strip()]


def test_command_tree_is_not_empty():
    """Sanity: walk_commands() must yield commands or every other test is vacuous."""
    assert list(cli.walk_commands()), "CLI exposes no commands"


@pytest.mark.parametrize("path", [path for path, _ in _commands_with_own_render_format()])
def test_injected_format_flag_is_suppressed_when_command_owns_one(path):
    """A command with its own render-format flag must not also show ``--format``.

    This is the discriminating assertion: reverting the ``_command_help_options``
    suppression in ``milo_app`` makes the injected ``--format`` row reappear in
    ``--help`` for these commands and this test goes red.
    """
    result = cli.invoke([*path.split("."), "--help"])
    assert result.exit_code == 0, path

    format_rows = _FORMAT_ROW.findall(result.output)
    assert len(format_rows) == 1, (
        f"{path} --help shows {len(format_rows)} render-format rows "
        f"({format_rows}); expected exactly one (the command's own flag)."
    )
    assert not _INJECTED_FORMAT_ROW.search(result.output), (
        f"{path} --help still advertises the injected envelope --format row; "
        f"it must be suppressed when the command declares its own format flag."
    )


def test_command_without_own_render_format_keeps_injected_format_flag():
    """Commands with no render-format param keep the injected ``--format`` row.

    Counterpart to the suppression test — proves the suppression is targeted,
    not a blanket removal that would strip ``--format`` from every command.
    """
    own = {path for path, _ in _commands_with_own_render_format()}
    sampled = []
    for path, cmd in cli.walk_commands():
        if path in own or cmd.hidden:
            continue
        sampled.append(path)
    assert sampled, "expected at least one command without its own format flag"

    # ``new.page`` is a stable command with no render-format param.
    result = cli.invoke(["new", "page", "--help"])
    assert result.exit_code == 0
    assert _INJECTED_FORMAT_ROW.search(result.output), (
        "new page --help should still expose the injected --format envelope flag"
    )


@pytest.mark.parametrize(
    ("path", "name", "spec"),
    [
        pytest.param(path, name, spec, id=f"{path}:{name}")
        for path, name, spec in _render_format_params()
    ],
)
def test_render_format_default_is_in_shared_vocabulary(path, name, spec):
    """Every render-format default must be an allowed vocabulary token (or empty)."""
    default = spec.get("default", "")
    if default in ("", None):
        return  # export-only flags (e.g. debug.deps) default to "no export".
    assert default in ALLOWED_RENDER_FORMATS, (
        f"{path}:{name} default {default!r} is not in the shared render-format "
        f"vocabulary {sorted(ALLOWED_RENDER_FORMATS)}"
    )


@pytest.mark.parametrize(
    ("path", "name", "spec"),
    [
        pytest.param(path, name, spec, id=f"{path}:{name}")
        for path, name, spec in _render_format_params()
    ],
)
def test_render_format_choices_are_in_shared_vocabulary(path, name, spec):
    """Every enumerated render-format choice must be an allowed vocabulary token."""
    choices = _enumerated_choices(str(spec.get("description", "")))
    assert choices, f"{path}:{name} Description does not enumerate any choices"
    unknown = [c for c in choices if c not in ALLOWED_RENDER_FORMATS]
    assert not unknown, (
        f"{path}:{name} enumerates unknown render-format tokens {unknown}; "
        f"allowed: {sorted(ALLOWED_RENDER_FORMATS)}"
    )


@pytest.mark.parametrize(
    ("path", "name", "spec"),
    [
        pytest.param(path, name, spec, id=f"{path}:{name}")
        for path, name, spec in _render_format_params()
    ],
)
def test_machine_readable_mode_uses_json_token(path, name, spec):
    """Any render-format flag offering a machine-readable mode spells it ``json``.

    The only allow-listed machine-readable token is ``json``. We assert no
    non-``json`` machine synonym sneaks in, and that ``json`` is present whenever
    the flag is a console/table/yaml -> structured toggle (i.e. anything that is
    not a purely-distinct export target like mermaid/dot).
    """
    choices = _enumerated_choices(str(spec.get("description", "")))
    machine_aliases = {"machine", "data", "j", "raw-json"}
    leaked = [c for c in choices if c in machine_aliases]
    assert not leaked, (
        f"{path}:{name} uses a non-canonical machine token {leaked}; "
        f"machine output must be spelled {MACHINE_FORMAT!r}"
    )

    # Distinct export-only flags (mermaid/dot, no console/structured pairing)
    # legitimately have no json mode.
    export_only = set(choices) <= {"mermaid", "dot"}
    if not export_only:
        assert MACHINE_FORMAT in choices, (
            f"{path}:{name} offers human renders {choices} but no {MACHINE_FORMAT!r} "
            f"machine-readable mode"
        )
