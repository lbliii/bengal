"""Guard that the curated root ``--help`` sections track the live registry.

``BengalCLI._ROOT_HELP_SECTIONS`` is a hand-maintained tuple that organizes the
top-level command surface for the fast-path root-help renderer. It has drifted
from the registry before (#387): ``preview`` was missing and fell into a junk
"Other" bucket, while ``health`` (a legacy alias for ``check``) was advertised
as a first-class command. These tests fail if a future top-level command is
registered without a matching section entry, or if a stale name is left behind
in a section.
"""

from __future__ import annotations


def _curated_top_level_names() -> set[str]:
    """Return top-level commands/groups that belong in the curated root help.

    Excluded by design:

    * hidden commands (never shown in root help);
    * group-internal subcommands (dotted paths such as ``theme.preview`` —
      these are not top-level names in ``cli._commands`` at all);
    * registered legacy aliases (e.g. ``health``) that stay in the registry,
      ``--llms-txt``, and the docs inventory but are not distinct commands and
      so are deliberately kept out of the curated sections.
    """
    from bengal.cli.milo_app import BengalCLI, cli

    legacy = set(BengalCLI._ROOT_HELP_LEGACY_ALIASES)
    names = {
        cmd.name
        for cmd in cli._commands.values()
        if not getattr(cmd, "hidden", False) and cmd.name not in legacy
    }
    names |= {group.name for group in cli._groups.values() if not group.hidden}
    return names


def _section_command_names() -> list[str]:
    """Flatten every command name referenced by the curated sections."""
    from bengal.cli.milo_app import BengalCLI

    names: list[str] = []
    for section in BengalCLI._ROOT_HELP_SECTIONS:
        names.extend(section["commands"])
    return names


def test_every_curated_top_level_command_appears_in_exactly_one_section():
    """Each curated top-level command/group must map to exactly one section."""
    curated = _curated_top_level_names()
    section_names = _section_command_names()

    counts = {name: section_names.count(name) for name in curated}

    missing = sorted(name for name, count in counts.items() if count == 0)
    duplicated = sorted(name for name, count in counts.items() if count > 1)

    assert not missing, (
        f"Top-level commands not curated into any _ROOT_HELP_SECTIONS entry: "
        f"{missing}. Add each to the appropriate section in "
        f"bengal/cli/milo_app.py (otherwise it lands in the junk 'Other' bucket)."
    )
    assert not duplicated, (
        f"Commands listed in more than one _ROOT_HELP_SECTIONS entry: {duplicated}."
    )


def test_sections_contain_no_stale_or_excluded_command_names():
    """Every name in a section must be a curated top-level command/group.

    This catches stale entries left behind after a command is renamed, hidden,
    or demoted to a legacy alias (the #387 ``health`` regression).
    """
    curated = _curated_top_level_names()
    section_names = _section_command_names()

    stale = sorted(set(section_names) - curated)

    assert not stale, (
        f"_ROOT_HELP_SECTIONS references names that are not curated top-level "
        f"commands/groups: {stale}. Remove stale entries (e.g. legacy aliases "
        f"like 'health') from bengal/cli/milo_app.py."
    )


def test_root_help_renders_no_other_bucket():
    """The rendered root help must not emit a trailing 'Other' section."""
    from bengal.cli.milo_app import cli

    output = cli.invoke([]).output

    lines = {line.strip() for line in output.splitlines()}
    assert "Other" not in lines, (
        "Root --help rendered an 'Other' bucket, meaning a top-level command is "
        "missing from _ROOT_HELP_SECTIONS:\n" + output
    )


def test_preview_curated_and_health_alias_excluded_but_still_registered():
    """Lock in the #387 fix so the assertions above cannot vacuously pass.

    ``preview`` must be a curated command living in a section. ``health`` must
    stay registered (resolvable, in ``walk_commands()`` for the docs/llms-txt
    contract) yet be excluded from the curated root help so it never re-enters a
    section or the "Other" bucket.
    """
    from bengal.cli.milo_app import BengalCLI, cli

    curated = _curated_top_level_names()
    section_names = _section_command_names()

    assert "preview" in curated
    assert "preview" in section_names

    assert "health" in BengalCLI._ROOT_HELP_LEGACY_ALIASES
    assert "health" in cli._commands  # still registered / resolvable
    assert {path for path, _ in cli.walk_commands() if path == "health"} == {"health"}
    assert "health" not in curated
    assert "health" not in section_names
    assert "health" not in cli._root_help_commands()
