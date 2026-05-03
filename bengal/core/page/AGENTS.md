# Page Steward

`Page` is a compatibility surface, not a renderer. It may expose stable
template-facing properties, but rendered content, URLs, TOC, excerpts,
shortcode/link extraction, and bundle resource views belong under
`bengal/rendering/`.

Related docs:
- root `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Point Of View

Page represents author content identity and compatibility for existing
templates/plugins. It should preserve stable access while pushing derived
presentation work to rendering helpers.

## Protect

- `PageCore` as the cacheable metadata shape.
- Existing template/plugin property names that are compatibility contracts.
- Thin deferred shims from `Page` to rendering helpers.
- Bundle/resource compatibility without putting filesystem or image behavior in
  core.

## Contract Checklist

- Page metadata and compatibility tests in `tests/unit/core/`, `tests/core/`,
  and `tests/unit/rendering/test_page_*.py`.
- Template docs for Page properties and rendering content-processing docs.
- Protocol surfaces: `PageLike`, mocks in `tests/_testing/`, and plugin-facing
  access.
- Import boundaries: no module-level parser/rendering imports; rerun
  `test_no_core_mixins.py` when helper imports move.

## Advocate

- Rendering helper APIs for every new derived template value.
- Page fixtures that reproduce real frontmatter, bundles, and resource access
  before changing compatibility behavior.
- Deleting vestigial forwarding wrappers when callers can use the composed
  service directly.

## Serve Peers

- Give rendering exact compatibility shims to preserve.
- Give tests canonical fixtures for page metadata, cacheability, bundles, and
  URL behavior.
- Give docs current Page property names and migration notes.

## Do Not

- Move parser, HTML, excerpt, TOC, shortcode, URL, or resource I/O logic into
  `Page`.
- Add broad convenience fields to `PageCore` for values that require parsing or
  rendering.
- Recreate deleted behavior modules as dumping grounds.
- Add `# type: ignore` to quiet Page protocol friction.

## Own

- Page sections in `site/content/docs/reference/architecture/core/object-model.md`
- `site/content/docs/reference/architecture/rendering/content-processing-api.md`
- `site/content/docs/reference/template-functions/page-properties.md`
- Checks: `uv run pytest tests/unit/rendering/test_page_content.py tests/unit/rendering/test_page_operations.py tests/unit/rendering/test_page_urls.py tests/unit/rendering/test_page_resources.py -q`
- Checks: `uv run pytest tests/core/test_page_bundles.py tests/unit/core/test_computed_functions.py -q`
- Checks: `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
