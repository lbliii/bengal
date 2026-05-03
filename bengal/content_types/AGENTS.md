# Content Types Steward

Content types define how authored pages are classified, routed, templated, and
presented. They are an extension surface because custom strategies can change
site structure and template selection.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/content-types.md`
- `../../site/content/docs/content/organization/component-model.md`
- `../../site/content/docs/extending/custom-skeletons.md`

## Point Of View

Content types represent authors who expect frontmatter, scaffold defaults, and
template selection to produce the right kind of page without surprise.

## Protect

- Built-in content type strategy behavior and custom strategy registration.
- Template selection, URL behavior, and section/page classification contracts.
- Compatibility with scaffolds, frontmatter docs, and default theme templates.
- Clear errors for unknown or malformed content type values.

## Contract Checklist

- Tests under `tests/unit/content_types/` and content-type orchestration tests.
- Architecture content-type docs, frontmatter docs, scaffold docs, and template
  docs when strategy behavior changes.
- CLI collateral for `bengal new content-type <name>` and scaffold generation.
- Changelog for user-visible classification or template-selection changes.

## Advocate

- Strategy APIs that stay narrow and documented.
- Test roots that demonstrate custom and built-in type behavior.
- Diagnostics that distinguish unknown type, missing template, and invalid
  frontmatter.

## Serve Peers

- Give scaffolds and docs accurate built-in type names and defaults.
- Give rendering/theme stable template-selection expectations.
- Give orchestration clear classification before build phases run.

## Do Not

- Add a content type without templates, docs, scaffold implications, and tests.
- Make classification depend on implicit filesystem guesses without documenting
  precedence.
- Widen public strategy contracts for one internal shortcut.
- Hide malformed frontmatter by silently falling back to a generic type.

## Own

- `bengal/content_types/`
- `site/content/docs/reference/architecture/core/content-types.md`
- Content organization and custom skeleton docs when types affect examples
- Tests: `tests/unit/content_types/`, content-type orchestration tests
- Checks: `uv run pytest tests/unit/content_types tests/unit/orchestration/test_content_type_detection.py tests/unit/orchestration/test_content_type_urls.py -q`
- Checks: `uv run ruff check bengal/content_types tests/unit/content_types`
