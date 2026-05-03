# Template Functions Steward

Template functions are the supported ergonomic surface for themes. They should
be explicit, registered intentionally, and safe for template authors to compose.

Related docs:
- root `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/rendering/content-processing-api.md`
- `../../../site/content/docs/reference/template-functions/`
- `../../../site/content/docs/theming/templating/`

## Point Of View

Template functions represent the public helper language available to themes and
site authors. Names and behavior are sticky because templates copy them.

## Protect

- The explicit `register(env, site)` pattern.
- Stable filter/global/test names used by bundled and user themes.
- Small helpers that delegate domain-heavy work elsewhere.
- Clear template-facing behavior and useful errors.

## Contract Checklist

- Tests under `tests/unit/rendering/template_functions/`,
  `tests/unit/template_functions/`, and engine parity tests when helpers are
  engine-sensitive.
- Docs under reference template-functions and theming quick references.
- Default theme templates and site examples that call helper names.
- Protocol impact on `TemplateEnvironment` and `TemplateEngine`.

## Advocate

- Helper docs with exact inputs, fallback behavior, and examples.
- Data coercion and useful diagnostics where YAML/frontmatter types vary.
- A small public surface that composes rather than a long list of near-duplicates.

## Serve Peers

- Give default theme stable helpers instead of private object reaches.
- Give docs generated references and realistic snippets.
- Give rendering/core a place for presentation ergonomics without widening core.

## Do Not

- Add filesystem auto-discovery for template helpers.
- Reach into private core internals when a rendering/helper API exists.
- Add helper names casually; template APIs are public enough to preserve.
- Hide missing data or broken links with silent empty output.

## Own

- `site/content/docs/reference/template-functions/`
- `site/content/docs/theming/templating/` and theming recipes using helpers
- Generated/reference docs when adding, renaming, or removing filters/globals
- Checks: `uv run pytest tests/unit/rendering/template_functions tests/unit/template_functions -q`
- Checks: `uv run ruff check bengal/rendering/template_functions tests/unit/template_functions`
