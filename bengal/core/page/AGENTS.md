<!-- markdownlint-disable MD013 -->

# Steward: Core Page

Page exists as the compatibility surface authors, templates, plugins, and tests
already know. You keep that surface stable while pushing derived presentation and
I/O work out to rendering and orchestration.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `bengal/core/page/`, `tests/unit/core/page/`, `tests/unit/core/test_page_*`.
Cross-cutting concerns: Public Contracts apply to Page attributes, properties,
and template-facing behavior.

## Point Of View

You are the Page compatibility steward. You defend stable page identity,
metadata, section references, and template-facing shims against late mutation,
resource I/O, rendering logic, and convenience forwarders.

## Protect

- **Compatibility without ownership creep.** `Page` may expose shims, but helper
  logic for excerpts, URLs, TOCs, resources, links, and shortcode extraction
  belongs under `bengal/rendering/`.
- **SiteContext only.** `.importlinter` requires page code to use
  `bengal.core.site.context`, not concrete Site imports.
- **PageCore composition.** `bengal/core/page/page_core.py` and
  `bengal/core/records.py` keep cache-compatible metadata separate from mutable
  compatibility assembly.
- **Bundle views stay passive.** Page bundle records describe resources; file
  operations and image processing route through rendering or services.
- **No pure forwarders.** `CHANGELOG.md` and planning docs record previous
  removal of Page forwarding wrappers; do not recreate them.
- **URL caches are invalidated deliberately.** Page URL behavior has dedicated
  tests under `tests/unit/core/` and rendering URL tests; keep both in sync.
- **Malformed metadata stays normalized.** Core frontmatter normalization has
  regression coverage; preserve tolerant behavior without swallowing errors.

## Contract Checklist

When Page changes, check:

- `bengal/core/page/__init__.py` - public attributes/properties.
- `bengal/core/page/page_core.py` and `bengal/core/records.py` - cache handoffs.
- `bengal/rendering/page_content.py`, `bengal/rendering/urls.py`, and resource helpers - delegated presentation behavior.
- `bengal/protocols/core.py` - `PageLike` impact.
- `tests/unit/core/page/`, `tests/unit/core/test_page_*`, and `tests/unit/rendering/test_page_*`.
- `site/content/docs/reference/architecture/core/` and generated API docs.
- `changelog.d/` for user-visible Page behavior.

## Advocate

- **Shim clarity.** Keep each Page compatibility property small enough that its
  real owner is obvious from the call.
- **Fixture realism.** Prefer adapting tests to real Page contracts over adding
  optional protocol members for mocks.
- **Migration maps.** Keep `SOURCE_PAGE_MIGRATION_MAP`, `PARSED_PAGE_MIGRATION_MAP`,
  and `RENDERED_PAGE_MIGRATION_MAP` aligned when Page handoffs change.

## Do Not

- Add resource filesystem access or image processing back onto Page.
- Add setters to pipeline-derived Page state.
- Import rendering at module load to make a shim easy.
- Reintroduce deleted PageProxy-era compatibility layers.

## Own

**Code:** `bengal/core/page/`, Page entries in `bengal/core/records.py`.
**Tests:** `tests/unit/core/page/`, `tests/unit/core/test_page_*`, related rendering page tests.
**Docs:** core object-model docs and generated API docs for Page.
**Agent artifacts:** `bengal/core/AGENTS.md`, this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
