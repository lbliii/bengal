# CLI Steward

The CLI is a user-facing contract. Commands should be fast to import, explicit
to discover, structured for machines, and helpful for humans.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/tooling/cli.md`

## Protect

- Milo command patterns: annotated parameters, lazy registration, dict returns.
- Stable command names, flags, and structured output.
- Clear errors and tips for site authors.
- Cold-start performance.

## Do Not

- Add Click-style decorators or parser construction shortcuts.
- `print()` command results instead of returning structured data or using CLI render helpers.
- Add broad imports at CLI startup.
- Change public flags without migration notes.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/tooling/cli.md`.
- Keep command examples and help-output docs in sync with Milo command changes.
- Update migration notes when flags, command names, or structured output changes.

## Local Checks

- `uv run pytest tests/unit/cli tests/integration/test_cli_help.py -q`
- `uv run ruff check bengal/cli tests/unit/cli`
- Run wheel/install smoke tests for packaging-visible command changes.
