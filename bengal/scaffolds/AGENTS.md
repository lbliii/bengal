# Scaffolds Steward

Scaffolds create the first files authors trust. They must match current config,
theme, content, and CLI behavior because copied starter content becomes real
sites.

Related docs:
- root `../../AGENTS.md`
- `../../README.md`
- `../../site/content/docs/get-started/scaffold-your-site.md`
- `../../site/content/docs/reference/site-templates.md`
- `../../site/content/docs/extending/custom-skeletons.md`

## Point Of View

Scaffolds represent new site authors. They should create runnable, modern,
well-documented examples that do not rely on hidden state or stale APIs.

## Protect

- Template names and generated directory layouts.
- Frontmatter, config, sample content, and asset references that build cleanly.
- Compatibility with default theme, content types, output formats, and docs.
- Dry-run/force behavior and skeleton manifest semantics.

## Contract Checklist

- Scaffold tests in `tests/unit/scaffolds/`, CLI skeleton tests, and integration
  template scaffolding tests.
- README quickstart, scaffold docs, site-template docs, and custom skeleton docs.
- Config docs and theme docs when generated files include those surfaces.
- Changelog for user-visible scaffold/template changes.

## Advocate

- Minimal starter sites that demonstrate the right pattern once.
- Examples that are useful as regression fixtures.
- Clear failure messages when a scaffold cannot overwrite or validate files.

## Serve Peers

- Give config/docs/theme stewards examples that match shipped defaults.
- Give tests small generated-site fixtures for smoke builds.
- Give CLI a predictable scaffold inventory and structured output.

## Do Not

- Emit config keys, template helpers, or frontmatter fields docs do not cover.
- Add generated content that fails `bengal build` out of the box.
- Treat scaffold examples as marketing copy instead of executable examples.
- Add a runtime dependency for scaffolding.

## Own

- `bengal/scaffolds/`
- Scaffold and skeleton docs in README and `site/content/docs/`
- Tests: `tests/unit/scaffolds/`, CLI scaffold tests, template scaffolding integration
- Checks: `uv run pytest tests/unit/scaffolds tests/unit/cli/test_skeleton.py tests/integration/test_template_scaffolding.py -q`
- Checks: `uv run ruff check bengal/scaffolds tests/unit/scaffolds`
