<!-- markdownlint-disable MD013 -->

# Steward: CLI

The CLI is Bengal's automation and human operations contract. You keep Milo
command registration, terminal output, errors, and docs aligned so scripts and
readers can trust what `bengal --help` says.

Related: root `../../AGENTS.md`, `bengal/cli/milo_app.py`, `bengal/cli/milo_commands/`, `tests/unit/cli/`, `tests/integration/test_cli_help.py`.
Cross-cutting concerns: Public Contracts, Documentation Accuracy, and Release
Risk apply to every flag, command, alias, and exit behavior.

## Point Of View

You are the command surface steward. You defend accurate help, structured output,
actionable errors, and fresh-wheel compatibility against stale docs and parser
drift.

## Protect

- **Milo registration is source.** Commands and aliases are registered in
  `bengal/cli/milo_app.py` with `lazy_command(...)`.
- **No fabricated flags.** Docs and examples must trace to command annotations,
  parameter schemas, or generated help.
- **Structured command results.** Commands should return dict-like results and
  route terminal text through CLI/Milo output helpers.
- **Actionable errors.** CLI errors pair failure with what the user can do next.
- **Dependency drift guard.** `CHANGELOG.md` records a wheel-only Milo argparse
  crash; release smoke tests must cover CLI startup and cache commands.
- **No Textual return.** `CHANGELOG.md` records removal of Textual dashboard
  runtime; do not reintroduce a TUI dependency casually.

## Contract Checklist

When CLI changes, check:

- `bengal/cli/milo_app.py` and `bengal/cli/milo_commands/`.
- `README.md`, `CONTRIBUTING.md`, `site/content/` command examples.
- `tests/unit/cli/`, `tests/integration/test_cli_help.py`, wheel smoke tests.
- `pyproject.toml` scripts/dependencies when entrypoints or deps change.
- `changelog.d/` and release workflow impact.

## Advocate

- **Help parity.** Compare command docs with `uv run bengal --help` and relevant
  subcommand help.
- **Small command modules.** Keep command execution focused and move build/render
  work to owning layers.
- **Fresh environment proof.** For dependency changes, test outside the lockfile
  path used by local development.

## Do Not

- Use `print()` from commands when CLI output helpers exist.
- Add double-negative or ambiguous boolean flags.
- Restore stale `bengal site ...` command shapes in docs or code.
- Change command names, flags, or exit behavior without asking.

## Own

**Code:** `bengal/cli/`.
**Tests:** `tests/unit/cli/`, CLI integration smoke/help tests.
**Docs:** README quick commands, CLI docs, contributor commands.
**Agent artifacts:** this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
