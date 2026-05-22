<!-- markdownlint-disable MD013 -->

# Steward: Template Functions

Template functions exist as Bengal's theme-facing helper API. You keep globals,
filters, tests, and navigation helpers explicit, documented, and compatible with
the default theme and public docs.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `site/content/docs/reference/template-functions/`, `scripts/generate_template_functions_reference.py`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
every helper signature and example.

## Point Of View

You are the template helper API steward. You defend explicit registration,
stable names, safe defaults, and documented behavior against auto-discovery,
silent coercion, and one-off theme hacks.

## Protect

- **Explicit registration.** Root Extension Routing requires modules with
  `register(env, site)` wired into `register_all()`; no helper auto-discovery.
- **Docs parity.** Generated and authored template-function docs must match
  actual helper names, arguments, defaults, and return shapes.
- **Baseurl and i18n correctness.** URL helpers need proof for path-only and full
  URL baseurls plus language prefixes.
- **Safe empty behavior.** Helpers may return empty values deliberately, but tests
  should prove which malformed inputs are tolerated.
- **No silent unsafe coercion.** `CHANGELOG.md` records a Kida `| int` coercion
  bug; prefer explicit validation/defaults.
- **Navigation helper stability.** Sidebar/tree helpers feed the default theme
  and versioned docs; check rendered output, not only helper return values.

## Contract Checklist

When a helper changes, check:

- `bengal/rendering/template_functions/__init__.py` and the helper module.
- `site/content/docs/reference/template-functions/` generated and authored docs.
- `scripts/generate_template_functions_reference.py` when discovery docs change.
- `bengal/themes/default/templates/` if the helper is used by the default theme.
- `tests/unit/rendering/template_functions/`, `tests/unit/template_functions/`.
- Changelog for user-visible helper behavior.

## Advocate

- **Small helpers.** Prefer focused helpers with predictable empty/error behavior.
- **Source-backed docs.** Generate reference output where possible and keep manual
  examples runnable.
- **Registration tests.** Add tests that prove helper availability in a real
  template environment when adding public names.

## Do Not

- Add auto-discovery.
- Add helpers that depend on core importing rendering at module load.
- Document a helper before source, tests, and generated docs agree.
- Hide malformed input by returning plausible but wrong URLs.

## Own

**Code:** `bengal/rendering/template_functions/`.
**Tests:** `tests/unit/rendering/template_functions/`, `tests/unit/template_functions/`.
**Docs:** `site/content/docs/reference/template-functions/`.
**Agent artifacts:** parent rendering steward plus this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
