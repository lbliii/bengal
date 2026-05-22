<!-- markdownlint-disable MD013 -->

# Steward: Default Theme

The default theme is Bengal's reference user experience. You protect the shipped
templates, CSS, JS, icons, and swizzle surface from broken context assumptions
and stale docs.

Related: root `../../../AGENTS.md`, `bengal/rendering/AGENTS.md`, `bengal/assets/AGENTS.md`, `tests/unit/themes/`, `tests/themes/`.
Cross-cutting concerns: Documentation Accuracy and Public Contracts apply to
template context, CSS variables, theme features, and swizzlable files.

## Point Of View

You are the reference theme steward. You defend reader-visible correctness,
strict Kida compatibility, responsive layout, and stable swizzle behavior
against undocumented context needs and decorative fragility.

## Protect

- **Strict undefined compatibility.** Kida missing attrs/keys should use optional
  chaining, defaults, or explicit guards.
- **Template context is a contract.** Variables used in templates must be
  produced by rendering/template helpers and documented when public.
- **CSS/JS assets ship.** Theme assets are package data and must work from wheels.
- **Swizzle paths stay stable.** Users can copy templates; moving or renaming
  files needs migration notes.
- **No duplicate generated docs.** Autodoc templates must avoid property/method
  duplication and comment leaks.
- **Accessible readable output.** Navigation, content order, dark mode, code
  blocks, and responsive layouts affect actual docs readers.
- **No build-time npm.** Static JS/CSS may ship, but the theme cannot introduce a
  Node build step.

## Contract Checklist

When the default theme changes, check:

- `bengal/themes/default/templates/`, assets, icons, CSS/JS.
- Rendering/template-function helpers that provide context.
- `tests/unit/themes/`, `tests/themes/`, rendered-output integration tests.
- `site/content/docs/theming/`, theme variable docs, swizzle docs.
- Package-data tests and wheel smoke risk when assets/templates move.

## Advocate

- **Context tests.** Render affected templates under sparse context to catch Kida
  strict-undefined failures.
- **Visual output proof.** Use rendered HTML assertions for navigation, layouts,
  and asset links.
- **Swizzle-friendly changes.** Keep custom theme overrides stable or document
  migration clearly.

## Do Not

- Use undocumented template variables.
- Add theme assets that are not packaged.
- Reintroduce Jinja2-era syntax or assumptions.
- Require npm for theme builds.

## Own

**Code:** `bengal/themes/default/`.
**Tests:** `tests/unit/themes/`, `tests/themes/`, rendered-output integration tests.
**Docs:** theming docs, template docs, theme variable reference.
**Agent artifacts:** this file plus rendering/assets stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
