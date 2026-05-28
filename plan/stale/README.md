<!-- markdownlint-disable MD013 -->

# Stale Plan Archive

Updated: 2026-05-28

The stale bodies were removed after distillation. They contained useful ideas,
but their paths, metrics, or architecture assumptions no longer matched current
`main`.

## Worth Rolling Forward

- Reload/output-collector/provenance/short-circuit ideas belong under the active
  incremental plans: `rfc-effect-traced-incremental-builds.md`,
  `rfc-incremental-dependency-indexes.md`, and
  `rfc-snapshot-build-plan-handoff.md`.
- Architecture/protocol/coupling cleanup belongs under
  `epic-immutable-page-pipeline.md` and `epic-delete-forwarding-wrappers.md`.
- UX and CLI sharp-edge ideas belong under `epic-ux-sharp-edges.md`.
- Theme/blog/nav/release layout ideas should only come back through
  `rfc-template-view-model-contracts.md` or `rfc-theme-library-assets.md`.
- Patitas parse optimization ideas should be revalidated before another slice:
  parsed-cache metrics, opt-in token persistence, latest-document reuse, and
  `parse_many_with_toc()` exist, but render-orchestrator integration still needs
  Python 3.14t benchmarks and realistic page-size proof.
- Incremental observability and utility-leaf leftovers are audits, not direct
  patch lists. Revalidate current behavior before reviving `--explain`
  improvements, `lru_cache` miss coalescing, `hash_dict` memoization, or
  excerpt hot-path work.

## Removed As Not Current

Old drafts covered Discourse/docs feedback, broad package restructuring,
navigation labels, release layouts, supply-chain quick wins, stale Mistune
cleanup, old ty/protocol migration plans, old warm-build test matrices, and
several speculative parser/library designs. Keep them out of active planning
until they are re-proposed with current evidence.
