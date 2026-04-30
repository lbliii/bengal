# Page Steward

`Page` is a compatibility surface, not a renderer. It may expose stable
template-facing properties, but the work behind rendered content, URLs, TOC,
excerpts, shortcode/link extraction, and bundle resource views belongs under
`bengal/rendering/`.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Protect

- `PageCore` as the cacheable metadata shape.
- `Page` properties that older templates and plugins already call.
- Thin deferred shims from `Page` to rendering helpers.
- Bundle/resource compatibility without putting filesystem or image behavior in core.

## Do Not

- Move parser, HTML, excerpt, TOC, shortcode, URL, or resource I/O logic into `Page`.
- Add broad convenience fields to `PageCore` for values that require parsing/rendering.
- Recreate deleted `content.py`, `metadata.py`, or relationship mixin modules as behavior sinks.
- Add `# type: ignore` to quiet Page protocol friction.

## Documentation Ownership

- Own Page sections in `site/content/docs/reference/architecture/core/object-model.md`.
- Keep `site/content/docs/reference/architecture/rendering/content-processing-api.md` accurate for Page shims.
- Update `site/content/docs/reference/template-functions/page-properties.md` when template-facing Page access changes.

## Local Checks

- `uv run pytest tests/unit/rendering/test_page_content.py tests/unit/rendering/test_page_operations.py tests/unit/rendering/test_page_urls.py tests/unit/rendering/test_page_resources.py -q`
- `uv run pytest tests/core/test_page_bundles.py tests/unit/core/test_computed_functions.py -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
