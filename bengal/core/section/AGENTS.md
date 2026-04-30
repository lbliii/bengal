# Section Steward

`Section` protects structural hierarchy, page membership, query/sort behavior,
and version-aware structural navigation. Presentation belongs in rendering.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Protect

- Parent/child relationships, section walking, and structural identity.
- Page retrieval, sorting, and index-page decisions.
- Version filters that describe content membership.
- Compatibility shims for older imports and template access.

## Do Not

- Put URL presentation, icon/nav display logic, content stats, or template
  application back into core.
- Reintroduce Section mixins.
- Hoist rendering imports to module level.
- Treat theme ergonomics as structural domain logic.

## Documentation Ownership

- Own Section sections in `site/content/docs/reference/architecture/core/object-model.md`.
- Keep `site/content/docs/reference/architecture/rendering/content-processing-api.md` accurate for Section shims.
- Update `site/content/docs/reference/template-functions/navigation-functions.md` when navigation-facing behavior changes.

## Local Checks

- `uv run pytest tests/unit/rendering/test_section_urls.py tests/unit/rendering/test_section_ergonomics.py -q`
- `uv run pytest tests/unit/core/test_section_sorting.py tests/unit/core/test_section_versioning.py tests/unit/test_nav_tree.py -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
