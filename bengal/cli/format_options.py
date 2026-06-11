"""Shared render-format vocabulary for Bengal's CLI surface.

Finding 25 (#387) standardizes the machine-readable output-format token across
every command that renders a result for both humans and machines. The rule is
deliberately small:

* ``json`` is the machine-readable token *everywhere*. No command spells the
  machine output ``machine``, ``data``, ``j``, or anything else.
* Each command keeps its own *human* default render. Some of those defaults are
  genuinely distinct renders (a ``yaml`` config dump, a ``table`` of versions,
  an ``html`` directive preview, a ``mermaid``/``dot`` graph export) — those are
  real, separately-allow-listed targets, not just different names for "the
  human one".

This module is CLI presentation only. It carries no rendering behavior; it is a
vocabulary registry that the help renderer and the guard test
(``tests/unit/cli/test_cli_format_vocabulary.py``) consult so new commands
inherit the convention instead of re-inventing it.
"""

from __future__ import annotations

# The token every command uses for machine-readable output.
MACHINE_FORMAT = "json"

# The plain, name-only human render — distinct from a genuinely different target
# like ``yaml`` or ``table``. ``console`` and ``plain`` are two spellings of the
# same "just print it for a person" render that predate this convention.
HUMAN_DEFAULTS = frozenset({"console", "plain", "summary", "text"})

# Genuinely-different human render targets. These are not synonyms for the plain
# human render; each is a separate, intentional output a person might pick. They
# are allow-listed so the guard test does not collapse them into ``json``.
DISTINCT_HUMAN_TARGETS = frozenset(
    {
        "yaml",  # config.show — structured config dump
        "table",  # version.list / inspect.perf — tabular metrics
        "html",  # theme.test / debug.sandbox — rendered directive markup
        "markdown",  # version.diff — prose diff
        "mermaid",  # inspect.graph / debug.deps — graph export
        "dot",  # debug.deps — Graphviz graph export
    }
)

# Every value a render-format flag is allowed to accept. A command's own
# enumerated choices must be a subset of this, and must include ``json`` if it
# offers a machine-readable mode at all.
ALLOWED_RENDER_FORMATS = frozenset({MACHINE_FORMAT}) | HUMAN_DEFAULTS | DISTINCT_HUMAN_TARGETS

# Parameter names a command uses to carry its render-format choice. The CLI help
# renderer treats any of these as the command's own format flag and suppresses
# the injected envelope ``--format`` row to avoid a duplicate. ``export_format``
# selects a genuinely-distinct export target (mermaid/dot) rather than a
# console/json toggle, but it is still the command's own result-render flag.
RENDER_FORMAT_PARAMS = frozenset({"output_format", "format", "export_format"})

# The shared one-line Description template for a render-format parameter.
# ``{choices}`` is the comma-joined list of human-facing choices, always ending
# with the canonical ``json`` machine token (e.g. "console, json").
FORMAT_DESCRIPTION_TEMPLATE = "Output format: {choices}"


def format_description(*choices: str) -> str:
    """Build a render-format Description from the command's choices.

    The choices are rendered in the order given; callers list their human
    default(s) first and ``json`` last so every Description reads the same way.
    """
    return FORMAT_DESCRIPTION_TEMPLATE.format(choices=", ".join(choices))


def is_render_format_param(name: str) -> bool:
    """Return True if *name* is a command's own render-format parameter."""
    return name in RENDER_FORMAT_PARAMS
