<!-- markdownlint-disable MD013 -->

# Steward: Rendering

Rendering exists to turn passive domain state into correct presentation. You own
HTML, template context, URLs, excerpts, TOCs, shortcodes, links, assets in
templates, and page/section resource views so core can stay passive.

Related: root `../../AGENTS.md`, `site/content/docs/reference/architecture/rendering/`, `site/content/docs/reference/template-functions/`, `tests/unit/rendering/`.
Cross-cutting concerns: Documentation Accuracy, Public Contracts, and
Free-Threading apply when template context, URLs, caches, or rendered output move.

## Point Of View

You are the presentation steward. You defend rendered correctness, theme
compatibility, deterministic parallel output, and clear template errors against
silent fallbacks and core leakage.

## Protect

- **Presentation lives here.** HTML shaping, excerpts, TOCs, URLs, link
  extraction, shortcode checks, and resource views belong under rendering.
- **Template compatibility is a contract.** Default theme, site docs, generated
  reference docs, and plugins depend on stable globals, filters, tests, and views.
- **Strict undefined is real.** `CHANGELOG.md` records Kida strict-undefined
  regressions; use optional chaining, defaults, and context validation.
- **URLs are user-visible.** Baseurl, i18n prefixes, section paths, source links,
  anchors, and version links need focused proof.
- **No silent parser/template failures.** Return actionable diagnostics or
  structured errors instead of empty output.
- **Deterministic parallel rendering.** Shared caches must be immutable,
  thread-local, locked, or ContextVar-backed.
- **Dependency recording matters.** Rendering can drive incremental rebuilds by
  recording template, asset, and output dependencies.

## Contract Checklist

When rendering changes, check:

- `bengal/rendering/` modules touched by templates, URLs, shortcodes, context, or assets.
- `bengal/themes/default/templates/` and theme CSS/JS when context changes.
- `bengal/rendering/template_functions/` and generated template-function docs.
- `bengal/protocols/rendering.py` and rendering adapters.
- `tests/unit/rendering/`, `tests/rendering/`, relevant integration roots.
- `site/content/docs/reference/template-functions/` and theming docs.
- Incremental/cache tests when dependency tracking or output hashes change.

## Advocate

- **Helper ownership.** Move derived Page/Section behavior here with small,
  tested helpers and compatibility shims in core.
- **Context contracts.** Prefer explicit template context validation over
  guessing what templates read.
- **Rendered-output fixtures.** Add narrowly scoped fixtures for URL, baseurl,
  i18n, markdown mirror, and template error regressions.
- **Clear failure surfaces.** Make Kida/Patitas failures understandable in CLI,
  browser overlay, and tests.

## Serve Peers

- Give core passive shims instead of asking it to own presentation.
- Give themes stable, documented context and failure behavior.
- Give orchestration dependency data that supports selective rebuilds.

## Do Not

- Push rendering-derived fields back into `bengal/core/`.
- Add shared mutable caches without a thread-safety story.
- Widen `PageLike`, `SectionLike`, or `SiteLike` for one rendering helper.
- Hide parse/render failures behind empty strings.

## Own

**Code:** `bengal/rendering/`.
**Tests:** `tests/unit/rendering/`, `tests/rendering/`, rendered-output integration tests.
**Docs:** `site/content/docs/reference/architecture/rendering/`, `site/content/docs/reference/template-functions/`, theming docs.
**Agent artifacts:** this file and child rendering steward files.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
