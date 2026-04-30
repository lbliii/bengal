# Template Functions Steward

Template functions are the supported ergonomic surface for themes. They should
be explicit, registered intentionally, and safe for template authors to compose.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`

## Protect

- The explicit `register(env, site)` pattern.
- Stable filter/global names used by bundled and user themes.
- Small helpers that delegate domain-heavy work elsewhere.
- Clear template-facing behavior and useful errors.

## Do Not

- Add filesystem auto-discovery for template helpers.
- Reach into private core internals when a rendering/helper API exists.
- Add helper names casually; template APIs are public enough to preserve.
- Hide missing data or broken links with silent empty output.

## Documentation Ownership

- Own `site/content/docs/reference/template-functions/`.
- Keep `site/content/docs/theming/templating/` and theming recipes accurate when helper behavior changes.
- Update generated/reference docs when adding, renaming, or removing filters/globals.

## Local Checks

- `uv run pytest tests/unit/rendering tests/unit/template_functions -q`
- `uv run ruff check bengal/rendering/template_functions tests/unit/template_functions`
