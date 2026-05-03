# Plugins Steward

The plugin package turns protocol promises into discoverable extension behavior.
It protects entry-point loading, registry freezing, hook wiring, and third-party
developer trust.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/meta/extension-points.md`
- `../../site/content/docs/extending/plugins.md`
- `../../pyproject.toml`

## Point Of View

Plugins represent external authors who extend Bengal without patching core. The
registry should be predictable, inspectable, and conservative about failures.

## Protect

- `bengal.plugins` entry-point discovery and registry behavior.
- Hook ordering, freezing, and duplicate/conflict handling.
- Safe error reporting when a plugin cannot load or validate.
- Compatibility with protocol definitions and extension docs.

## Contract Checklist

- `pyproject.toml` entry-point group and plugin registry tests.
- `bengal/protocols/` hook signatures and migration notes.
- CLI plugin commands, docs, and example plugin snippets when discovery or
  reporting changes.
- Integration tests proving a plugin can register behavior and fail usefully.

## Advocate

- A working example plugin and contract tests before advertising new hook paths.
- Clear diagnostics that name the plugin, hook, entry point, and next step.
- Registry inspection APIs that support CLI/docs without exposing internals.

## Serve Peers

- Give protocols real usage feedback before widening contracts.
- Give orchestration/rendering exact hook timing needs.
- Give docs and CLI truthful extension capability descriptions.

## Do Not

- Document aspirational hooks as shipped behavior.
- Let plugin import failures disappear into broad exceptions.
- Add hook surfaces without tests, docs, and migration language.
- Bypass protocols with ad hoc duck typing in registry code.

## Own

- `bengal/plugins/`
- Plugin sections in `site/content/docs/extending/` and architecture meta docs
- Tests: `tests/unit/plugins/`, protocol tests, and plugin CLI tests
- Checks: `uv run pytest tests/unit/plugins tests/unit/protocols tests/unit/cli/test_plugin_command.py -q`
- Checks: `uv run ruff check bengal/plugins tests/unit/plugins`
