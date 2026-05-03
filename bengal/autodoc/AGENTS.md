# Autodoc Steward

Autodoc turns Python, CLI, and OpenAPI sources into virtual documentation pages.
It must be resilient because it analyzes user projects and should not import or
execute their code during extraction.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/subsystems/autodoc.md`
- `../../site/content/docs/content/sources/autodoc.md`
- `../../plan/epic-openapi-rest-layout-upgrade.md`

## Point Of View

Autodoc represents developers who expect API docs to reflect source truth
without side effects. Extraction should be static, recoverable, and honest about
partial failures.

## Protect

- Zero-import Python extraction using AST/static analysis.
- `DocElement` model serialization and virtual page generation.
- Configured source discovery, grouping, exclude patterns, and source links.
- Resilience for syntax errors, malformed annotations, partial OpenAPI specs,
  and missing docstrings.

## Contract Checklist

- Tests under `tests/unit/autodoc/` and integration autodoc builds.
- Autodoc docs, template docs, and default-theme API-reference templates.
- Cache/incremental collateral for extractor caching and virtual pages.
- Output format/search collateral when generated API pages are indexed.
- Changelog for user-visible autodoc behavior.

## Advocate

- Static extraction over importing user modules.
- Edge-case fixtures for nested classes, overloaded methods, aliases, schemas,
  and malformed inputs.
- Clear diagnostics that identify source path, object, extractor, and recovery.

## Serve Peers

- Give rendering virtual pages with stable metadata and template context.
- Give cache/incremental stable content hashes and dependency paths.
- Give site docs accurate examples for Python, CLI, and OpenAPI sources.

## Do Not

- Import user code to discover docs.
- Drop malformed elements silently when a warning would preserve trust.
- Change `DocElement` shape without cache and template collateral.
- Treat extractor crashes as full-build crashes when partial recovery is safe.

## Own

- `bengal/autodoc/`
- `site/content/docs/reference/architecture/subsystems/autodoc.md`
- `site/content/docs/content/sources/autodoc.md`
- Tests: `tests/unit/autodoc/`, autodoc integration tests
- Checks: `uv run pytest tests/unit/autodoc tests/integration/test_autodoc_html_generation.py -q`
- Checks: `uv run ruff check bengal/autodoc tests/unit/autodoc`
