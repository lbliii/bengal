# Default Theme UX Steward

The default theme is Bengal's shipped user experience. It should make real
documentation readable, navigable, accessible, and fast without adding a Node or
npm build path.

Related docs:
- root `../../../AGENTS.md`
- `README.md`
- `templates/README.md`
- `templates/SAFE_PATTERNS.md`
- `templates/TEMPLATE-CONTEXT.md`
- `../../../site/content/docs/theming/`

## Point Of View

Default theme represents readers, authors, and theme customizers encountering
Bengal's built-in UX. It should make documentation feel trustworthy at desktop,
mobile, keyboard, and code-heavy scales.

## Protect

- Reader ergonomics for docs, blogs, release notes, API references, CLI
  references, search, navigation, and code-heavy pages.
- Semantic HTML, keyboard navigation, focus states, contrast, and responsive
  behavior.
- Pure-Python delivery: no npm, no Node build step, and no external JS build
  pipeline.
- Stable template contracts and swizzle-friendly template structure.
- CSS token discipline and component scoping that avoids restyling authored
  content accidentally.
- Asset weight and rendering performance on mobile and low-power devices.

## Contract Checklist

- Theme tests under `tests/unit/themes/`, `tests/themes/`, and representative
  integration builds.
- Template context docs, safe patterns, CSS architecture docs, and theming docs.
- Rendering/template-function collateral when templates need new context.
- Accessibility/responsive manual inspection for layout-affecting changes.
- Changelog for user-visible default-theme behavior.

## Advocate

- Reader-first layouts for long-form docs, API references, code-heavy pages,
  release notes, and search results.
- Theme primitives that make common documentation patterns easy without custom
  CSS.
- Accessibility and responsive fixes as correctness work, not cosmetic polish.

## Serve Peers

- Give rendering and template-function stewards clear needs for template
  context, filters, URLs, and content views.
- Give the site documentation steward accurate theming examples and migration
  notes when theme contracts change.
- Provide tests or fixtures when a theme bug exposes a rendering or content
  model ambiguity.

## Do Not

- Treat visual polish as separate from correctness; unreadable content, broken
  nav, and clipped code blocks are product bugs.
- Add broad CSS selectors that leak into prose or user content.
- Move template-facing behavior into core objects when a rendering helper or
  template function belongs there.
- Let default-theme docs describe files, context values, or components that no
  longer exist.
- Add decorative complexity that makes documentation harder to scan.

## Own

- `README.md`, `templates/README.md`, `templates/SAFE_PATTERNS.md`, and
  `templates/TEMPLATE-CONTEXT.md`
- `site/content/docs/theming/`,
  `site/content/docs/reference/theme-variables.md`, and theme customization docs
- Checks: `uv run pytest tests/unit/themes tests/themes -q`
- Checks: `uv run bengal build site`
- Inspect representative docs, release notes, search, tags, autodoc/API, and
  narrow mobile layouts.
- Checks: `rg "^[^@#][^{]*\\b(ul|ol|a|pre|code|table)\\b" bengal/themes/default`
