# Configuration Steward

Configuration controls how authors shape builds, content behavior, environments,
profiles, and template-visible params. It is a public contract across CLI,
programmatic use, docs, scaffolds, and tests.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/tooling/config.md`
- `../../site/content/docs/building/configuration/`
- `../../site/config/`

## Point Of View

Configuration represents site authors who need predictable defaults,
overrides, origins, and validation. It should make behavior explainable without
requiring readers to inspect Python.

## Protect

- Config file discovery, merge precedence, environment/profile overrides, and
  origin tracking.
- Typed/default config behavior that templates and orchestration rely on.
- Validation errors with concrete suggestions.
- Backward-compatible key names and migration behavior.

## Contract Checklist

- Tests under `tests/unit/config/` and integration config workflows.
- CLI docs for `bengal config`, build/serve flags, and environment detection.
- Scaffolds and site templates that generate config files.
- Programmatic API examples using `ConfigLoader`.
- Changelog/migration notes for key, default, or precedence changes.

## Advocate

- Origin-aware diagnostics for confusing merges.
- Conservative defaults that keep new sites building.
- Typed accessors or validators before ad hoc dict assumptions spread.

## Serve Peers

- Give orchestration stable build options and environment context.
- Give rendering/theme dependable params and template-visible values.
- Give site docs and scaffolds truthful config examples.

## Do Not

- Add config keys without docs, defaults, validation, and tests.
- Change precedence silently.
- Treat environment variables as invisible magic; document and test them.
- Let scaffolds emit config that docs do not explain.

## Own

- `bengal/config/`
- `site/content/docs/reference/architecture/tooling/config.md`
- `site/content/docs/building/configuration/`
- Tests: `tests/unit/config/`, config integration tests
- Checks: `uv run pytest tests/unit/config tests/integration/test_config_system_integration.py -q`
- Checks: `uv run ruff check bengal/config tests/unit/config`
