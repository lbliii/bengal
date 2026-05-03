# Section Steward

`Section` protects structural hierarchy, page membership, query/sort behavior,
and version-aware structural navigation. Presentation belongs in rendering.

Related docs:
- root `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Point Of View

Section represents the site's authored hierarchy and membership rules. It
should answer structural questions without becoming the theme/navigation view
model.

## Protect

- Parent/child relationships, walking, and structural identity.
- Page retrieval, sorting, index-page decisions, and version filters.
- Compatibility shims for older imports and template access.
- Deferred imports for URL and theme ergonomics.

## Contract Checklist

- Structure and sorting tests in `tests/unit/core/` and `tests/unit/test_nav_tree.py`.
- Rendering-side URL and ergonomics tests.
- Navigation template-function docs and object-model docs.
- Protocol impact on `SectionLike` and test mocks.

## Advocate

- Rendering-side section URL and ergonomics helpers.
- Explicit tests for versioned and index-page edge cases.
- Clear docs when section membership or navigation behavior changes.

## Serve Peers

- Give rendering stable section structure without asking core to format URLs.
- Give default theme predictable navigation and hierarchy data.
- Give tests focused roots for navigation and version behavior.

## Do Not

- Put URL presentation, icon/nav display logic, content stats, or template
  application back into core.
- Reintroduce Section mixins.
- Hoist rendering imports to module level.
- Treat theme ergonomics as structural domain logic.

## Own

- Section sections in `site/content/docs/reference/architecture/core/object-model.md`
- `site/content/docs/reference/template-functions/navigation-functions.md`
- Checks: `uv run pytest tests/unit/rendering/test_section_urls.py tests/unit/rendering/test_section_ergonomics.py -q`
- Checks: `uv run pytest tests/unit/core/test_section_sorting.py tests/unit/core/test_section_versioning.py tests/unit/test_nav_tree.py -q`
- Checks: `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
