# Rendering Steward

Rendering owns the work that turns domain state into presentation: HTML,
template views, excerpts, TOC structures, URLs, shortcode/link extraction, and
page/section resource views.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/design-principles.md`
- `../../site/content/docs/reference/architecture/rendering/`
- `../../site/content/docs/reference/template-functions/`

## Point Of View

Rendering represents the promise that domain state becomes correct, stable,
themeable output. It should absorb presentation complexity so core stays passive
and themes get dependable data.

## Protect

- Template compatibility for existing themes and plugins.
- Clear helper/service boundaries behind core compatibility shims.
- Deferred imports where rendering and core need to see each other.
- Deterministic rendering under parallel builds.
- URL, reference, anchor, asset, shortcode, and template context correctness.

## Contract Checklist

- Unit tests under `tests/unit/rendering/`, parser tests under
  `tests/rendering/`, and integration roots that exercise rendered output.
- Template-function docs, theming docs, and default-theme templates when context
  changes.
- Protocol impact on `PageLike`, `SectionLike`, `TemplateEngine`, and test
  doubles.
- Cache/incremental impact when rendering records dependencies, references, or
  output hashes.
- Changelog for user-visible rendering changes.

## Advocate

- Rendering-side helpers when templates or core shims need derived content,
  URLs, excerpts, resource views, or safe presentation defaults.
- Better diagnostics and fixtures for parser/template failures instead of
  silent fallback behavior.
- Deterministic, thread-aware services when derived presentation data is cached
  or reused.

## Serve Peers

- Give core small lazy shims instead of asking it to own presentation.
- Give default theme and site docs stable template context, filters, globals,
  and failure behavior they can document.
- Give tests focused fixtures for template, shortcode, URL, and content-view
  regressions.

## Do Not

- Push rendering-derived fields back into `bengal/core/`.
- Add shared mutable state without a thread-safety reason.
- Widen `PageLike`, `SectionLike`, or `SiteLike` just to satisfy one helper.
- Hide parser/template failures behind silent fallbacks.

## Own

- `site/content/docs/reference/architecture/rendering/`
- `site/content/docs/reference/template-functions/`
- Theming docs when rendering helpers change theme contracts
- Checks: `uv run pytest tests/unit/rendering -q`
- Checks: `uv run pytest tests/rendering -q`
- Checks: `uv run ruff check bengal/rendering tests/unit/rendering tests/rendering`
- Run `check-cycles` before hoisting any deferred import across core/rendering.
