# Health Diagnostics and Artifact Audit

**Status**: active implementation

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
3. **Artifact audit**: a post-build scan of the generated output directory. It
   checks that files exist, generated manifests point at real files, and emitted
   HTML references resolve inside the artifact tree without re-running content
   discovery.

`bengal check` remains the author-facing policy command. `bengal health` remains
a compatibility alias while callers migrate. A future `bengal audit` command is
the artifact-focused surface; until that command lands, audit data is exposed
through internal APIs and Kida-ready result envelopes.

## Responsibility Map

| Concern | Owner | Notes |
| --- | --- | --- |
| Config validity | health policy | Keep as a check result; do not move into rendering. |
| URL collisions and ownership | build/rendering registry | Registry construction should surface duplicates as diagnostics. |
| Internal links | rendering resolver | Health consumes resolver findings instead of resolving URLs itself. |
| Anchors | rendering registry | Built from parsed/rendered headings and target directives. |
| Static/resource URLs | rendering/resource registry | Includes theme assets, project assets, and generated resource references. |
| Output files | artifact audit | Verify built files and manifests after output exists. |
| Sitemap/RSS/search/llms.txt | artifact audit | Treat as generated artifact contracts. |
| Connectivity, taxonomy, SEO, accessibility | health policy | Advisory checks; keep separate from hard artifact correctness. |
| External links | health/check policy | Network work is opt-in or CI-tier, not normal build finalization. |
| Terminal output | CLI + Kida templates | Result models expose structured context; templates own layout. |

## Result Envelope

CLI-facing validation and audit reports should converge on a versioned envelope:

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

1. Inventory and decision record.
2. Add a stable diagnostic/result envelope that can adapt existing health
   `CheckResult` values without breaking callers.
3. Move link-target discovery and internal URL resolution into rendering-owned
   registries and resolver helpers.
4. Migrate the build-time link validator to the rendering resolver and fix
   directory-style relative URL semantics.
5. Add artifact audit primitives and Kida-ready audit output.
6. Keep compatibility aliases and deprecation notes for legacy health surfaces.
7. Add focused unit/integration tests and changelog coverage.

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
