# Health Diagnostics and Artifact Audit

**Status**: Active implementation
**Updated**: 2026-05-29
**2026-05-29 Check**: Kept as active because `bengal audit` and audit envelopes
now exist, but health, rendering-owned reference resolution, artifact audit, and
terminal reporting ownership are still not fully separated.

## Problem

Bengal's health system grew into a mixed responsibility layer. It runs policy
checks, rediscovers rendering facts, validates links from partially transformed
page state, formats terminal output, and reports post-build artifact problems
through the same "health" vocabulary. That makes the link checker noisy, makes
build output harder to trust, and keeps terminal presentation tied to old
ad-hoc result shapes instead of Milo and Kida templates.

The current false-positive pattern is a symptom of that split ownership:
rendering knows the URLs, anchors, output targets, and resource references, but
health rebuilds its own link registry and resolver after the fact. Relative
links such as `./quickstart-writer` from directory-style page URLs are especially
easy to misread when the validator is not using the same URL semantics as the
renderer and browser.

## Decision

Split validation into three orthogonal surfaces:

1. **Build diagnostics**: structured facts emitted by build, rendering, and
   validators while the site is being produced. These are machine-shaped first
   and then rendered through Milo/Kida at the CLI boundary.
2. **Rendering registries and resolvers**: immutable, rendering-owned indexes for
   URLs, anchors, resources, and output targets. These are the source of truth
   for internal reference validation.
3. **Artifact audit**: a post-build scan of the generated output directory. The
   shipped audit currently checks generated HTML `href`/`src` references. The
   broader generated-manifest, sitemap, feed, search-index, and `llms.txt`
   artifact contracts are intended follow-up work, not current coverage.

`bengal check` remains the author-facing policy command. `bengal health` remains
a compatibility alias while callers migrate. `bengal audit` is now the
artifact-focused surface, backed by `bengal.audit.audit_output_dir()` and a
`bengal.audit.v1` envelope rendered through Kida/JSON output. Remaining work is
about ownership and overlap: health should not rediscover rendering truth, and
audit/check reports should not duplicate noisy findings.

## Responsibility Map

| Concern | Owner | Notes |
| --- | --- | --- |
| Config validity | health policy | Keep as a check result; do not move into rendering. |
| URL collisions and ownership | build/rendering registry | Registry construction should surface duplicates as diagnostics. |
| Internal links | rendering resolver | Health consumes resolver findings instead of resolving URLs itself. |
| Anchors | rendering registry | Built from parsed/rendered headings and target directives. |
| Static/resource URLs | rendering/resource registry | Includes theme assets, project assets, and generated resource references. |
| Output files | artifact audit | HTML reference audit is shipped; manifest/file-existence coverage beyond HTML refs remains follow-up. |
| Sitemap/RSS/search/llms.txt | artifact audit | Intended generated artifact contracts; not yet covered by the shipped HTML reference audit. |
| Connectivity, taxonomy, SEO, accessibility | health policy | Advisory checks; keep separate from hard artifact correctness. |
| External links | health/check policy | Network work is opt-in or CI-tier, not normal build finalization. |
| Terminal output | CLI + Kida templates | Result models expose structured context; templates own layout. |

## Result Envelope

CLI-facing validation and audit reports should use versioned, presentation-neutral
envelopes. Health and audit currently have separate schemas:
`bengal.check.v1` for source health and `bengal.audit.v1` for generated artifact
audits.

```json
{
  "schema_version": "bengal.check.v1",
  "command": "check",
  "status": "failed",
  "policy": {"errors_fail": true, "warnings_fail": false},
  "summary": {"errors": 1, "warnings": 2, "passed": 17},
  "findings": []
}
```

The envelope is intentionally presentation-neutral. Kida templates can render
tables, grouped issue lists, status lines, and hints without validators
constructing terminal strings.

## Implementation Waves

1. ✅ Inventory and decision record.
2. ✅ Add stable diagnostic/result envelopes for health and audit command output.
3. Pending: move link-target discovery and internal URL resolution into
   rendering-owned registries and resolver helpers.
4. Pending: migrate the build-time link validator to the rendering resolver and
   fix directory-style relative URL semantics.
5. ✅ Add artifact audit primitives and Kida-ready/JSON audit output for HTML
   internal references.
6. Partial: keep compatibility aliases and deprecation notes for legacy health
   surfaces. `bengal health` is registered as a `check` alias; docs and migration
   notes still need a focused pass.
7. Partial: focused audit/check CLI tests and changelog coverage exist; resolver
   ownership, site-wide generated artifact contracts, and health/audit overlap
   still need integration proof.

## Steward Notes

- **Rendering**: owns URL, anchor, resource, and output-target facts; health may
  consume those facts but should not rediscover rendering truth.
- **Build orchestration**: no new build phase; registries are built inside
  existing handoff points and artifact audit runs after outputs exist.
- **Core**: no new behavior on `Page`, `Section`, or immutable pipeline records.
  Registries remain separate service objects.
- **CLI**: commands return structured data and terminal presentation goes
  through Milo/Kida templates.
- **Tests/cache**: audit is a correctness backstop, not an invalidation engine.
  Fixtures should prove full and incremental builds report the same issues.
