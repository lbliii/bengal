# RFC: Incremental Build & Hot Reload Invariants

- **Status:** Draft
- **Owner:** AI (pairing with llane)
- **Date:** 2025-12-11
- **Scope:** Dev server incremental builds, cache validity, change classification, and reload delivery

## Problem
- Recent hot-reload regressions showed that stale content can surface when any of these layers disagree: file watching, change classification, incremental filtering, cache validity, rendering/cache bypass, and reload delivery.
- Section index edits (`_index.md`) can fan out widely; distinguishing body vs nav/cascade is error-prone without explicit invariants and cached metadata hashes.
- Cache checks (`is_changed`) can mask changes when hashes are updated too early or when revert-to-same-content occurs; bypass needs a single source of truth, not ad hoc flags.
- Observability is thin: missing structured logs/metrics made it hard to see why reloads weren’t firing or why pages were skipped.

## Goals
- Prevent stale renders on Markdown edits (body and frontmatter) with incremental speed preserved.
- Make change classification and cache bypass explicit and testable.
- Improve observability for change decisions and reload emission.
- Reduce blast radius of section index edits to only when nav/cascade actually changes.

## Non-Goals
- No change to production (non-dev) build semantics.
- No redesign of SSE transport; focus on correctness and visibility.

## Pain Points (from recent debugging)
- **Layer coupling:** Watch events → incremental filter → cache checks → rendering cache reuse → reload. A miss in any step leads to stale pages; no single invariant enforced.
- **Section filtering:** Section-level pruning skipped forced changes; deep pages didn’t rebuild. Forced/nav-changed paths must always bypass filters.
- **Frontmatter ambiguity:** `_index.md` edits always triggered large rebuilds; we needed a cheap metadata hash compare to tell body-only vs nav changes.
- **Cache reuse vs. change sets:** `is_changed` alone isn’t sufficient (revert-to-same-content, hash update timing). We needed `changed_sources` as a first-class signal for cache bypass.
- **Low observability:** No standard logs for change classification, selected pages, cache bypass counts, reload sends; debugging relied on guesswork.

## Proposed Invariants
1) **Structured change set:** Build pipeline receives `{changed_sources, nav_changed_sources, structural_changed}`. These must be threaded through incremental filtering and rendering.
2) **Cache bypass contract:** Rendering caches (parsed/rendered) must skip when `source in changed_sources` OR `cache.is_changed(source)` is true. One helper governs this.
3) **Frontmatter diff:** For Markdown, compare current metadata hash against cached metadata hash. If nav/cascade keys changed → section rebuild; otherwise page-only.
4) **Section filter safety:** Forced/nav-changed pages always included in pages-to-check; their sections are always in the changed set.
5) **Hash update ordering:** File hashes update only after successful render (`save_cache`), never before cache checks.
6) **Reload emission:** After any non-skipped build, emit structured reload payload; log action/reason/changed_paths_count/sent_count.

## Implementation Plan (phased)
### Phase 1 (stability & observability)
- Centralize cache bypass helper that takes `changed_sources` + `is_changed`.
- Standard logs/metrics: change classification, pages selected, cache bypass hits, reload sends.

### Phase 2 (frontmatter-aware scope)
- Persist metadata hashes in cache for all pages; add compare for Markdown changes.
- Nav/cascade keys changed → section rebuild; otherwise page-only. Keep prev/next propagation.

### Phase 3 (tests & guardrails)
- Unit: frontmatter hash compare (same vs different), forced-changed bypass, cache bypass helper.
- Integration: body-only page, body-only section index, nav-changing section index, CSS-only, no-change/touch, revert-to-same-content.

### Phase 4 (cleanup)
- Remove legacy ad hoc cache-skip flags; rely on the invariant helper.
- Document invariants in dev docs; add a short “incremental invariants” page.

## Risks
- Slight overhead for metadata hash compare (cheap YAML + hash).
- If cache is missing/invalid, we fall back to conservative behavior (full/section rebuild).
- Metrics/log volume: keep path lists truncated (we already cap to 5).

## Success Metrics
- Body-only Markdown edits rebuild only the target page (plus nav adjacency), not entire sections.
- Nav changes rebuild only affected sections, not whole site.
- Zero stale renders after edits without manual refresh.
- Observability: logs show change counts, cache bypass hits, reload sends; easy to spot regressions.

## Open Questions
- Should we store per-key nav hashes to avoid parsing YAML on every change?
- Do we need a max-pages-per-incremental safeguard for extremely large sections?
- Should reload payload include a small “changed pages count” for debugging clients?
