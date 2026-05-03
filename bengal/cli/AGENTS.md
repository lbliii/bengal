# CLI Steward

The CLI is a user-facing contract. Commands should be fast to import, explicit
to discover, structured for machines, and helpful for humans.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/tooling/cli.md`
- `../../README.md`
- `../../CONTRIBUTING.md`

## Point Of View

CLI represents site authors and automation. It should be predictable for
scripts while giving humans clear next steps when something goes wrong.

## Protect

- Milo command patterns: annotated parameters, lazy registration, dict returns.
- Stable command names, aliases, flags, structured output, and exit behavior.
- Clear errors and tips for site authors.
- Cold-start performance and limited import fan-out.

## Contract Checklist

- CLI tests under `tests/unit/cli/` and smoke/integration CLI tests.
- README, site docs, snippets, and generated help examples.
- Config, plugin, health, build, and scaffold stewards for commands that route
  to their domains.
- Changelog and migration notes for command/flag/output changes.
- Wheel/install smoke tests for packaging-visible command changes.

## Advocate

- Structured output envelopes for machine-readable commands.
- Command examples that match actual help output and defaults.
- Lazy imports and narrow command modules for startup speed.

## Serve Peers

- Give config, build, health, plugins, and scaffolds stable entrypoints.
- Give docs exact help text and runnable examples.
- Give tests command-level proof for user-facing workflows.

## Do Not

- Add Click-style decorators or parser construction shortcuts.
- `print()` command results instead of returning structured data or using CLI
  render helpers.
- Add broad imports at CLI startup.
- Change public flags without migration notes.

## Own

- `site/content/docs/reference/architecture/tooling/cli.md`
- CLI examples in README and site docs
- Tests: `tests/unit/cli/`, CLI integration smoke tests
- Checks: `uv run pytest tests/unit/cli tests/integration/test_cli_smoke.py tests/integration/test_cli_output_integration.py -q`
- Checks: `uv run ruff check bengal/cli tests/unit/cli`
- Run wheel/install smoke tests for packaging-visible command changes.
