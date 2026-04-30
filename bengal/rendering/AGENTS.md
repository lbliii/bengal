# Rendering Steward

Rendering owns the work that turns domain state into presentation: HTML,
template views, excerpts, TOC structures, URLs, shortcode/link extraction, and
page/section resource views.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/design-principles.md`
- `../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Protect

- Template compatibility for existing themes and plugins.
- Clear helper/service boundaries behind core compatibility shims.
- Deferred imports where rendering and core need to see each other.
- Rendering behavior that is deterministic under parallel builds.

## Do Not

- Push rendering-derived fields back into `bengal/core/`.
- Add shared mutable state without a thread-safety reason.
- Widen `PageLike`, `SectionLike`, or `SiteLike` just to satisfy one helper.
- Hide parser/template failures behind silent fallbacks.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/rendering/`.
- Keep `site/content/docs/reference/template-functions/` accurate for template-facing behavior.
- Update theming docs when rendering helpers change what themes can rely on.

## Local Checks

- `uv run pytest tests/unit/rendering -q`
- `uv run pytest tests/rendering -q`
- `uv run ruff check bengal/rendering tests/unit/rendering tests/rendering`
- Run `check-cycles` before hoisting any deferred import across core/rendering.
