<!-- markdownlint-disable MD013 -->

# Epic: Shard-parallel end-to-end build (issue #350, Phase 2 — the holistic redesign)

> **Status: design DECIDED (2026-06-05), branch-contained.** Phase 1 (sagas
> S1–S7 on `lbliii/render-heap-isolation`) built and *de-risked* a separate-heap
> render backend — and then **measured it honestly**: it does **not** make a real
> build faster. This Phase 2 redesign is what turns the branch into a *holistic,
> superior end-to-end build*. Nothing merges to `main` until that is proven
> (S17). `render_isolation` stays `off` by default throughout.

## Why Phase 1 didn't materialize a win (the measured truth)

On a 4,288-page build (M3 Pro, 3.14t), the Phase-1 fork backend **regressed**:

| | thread | fork (Phase 1) |
|---|--:|--:|
| render *phase* | 49.4s | **68.7s (+39%)** |
| full build wall | ~115–126s | ~144s (+~20%) |

- The clean "2× render" calibration was a **small-heap artifact** — it cycled 135
  warm pages, so the forked parent's heap was tiny and copy-on-write was free.
- A real build forks a parent holding **all parsed pages**; render then reads and
  **mutates that shared graph**, so the fork pays a cost proportional to the
  corpus (COW on the shared mutable page graph + fork of a large RSS + pickling
  thousands of result records) that **exceeds** the parallelism gain.
- The fixed costs I first suspected are negligible (immortalize 0.2s, block-cache
  ×8 ≈ 0.5s), confirming the problem is the **fork boundary placement**, not setup.

### Phase attribution (the real cost map)

The first attribution mis-read two phases; the authoritative `phase_timings_ms`
breakdown (S10) on the 4,288-page fixture, **after S9 landed**, is:

| phase | time | share | note |
|---|--:|--:|---|
| **rendering** | 76.8s | **66%** | the prize; Phase-1 fork regressed it (COW) |
| cache save | 10.2s | 9% | scales with pages; partly optimizable |
| post-process | 9.3s | 8% | global artifacts, mostly serial |
| initialization | 8.0s | 7% | |
| content (taxonomy/menu/related) | 6.4s | 5.5% | related_posts now ~3s after S9 |
| **parsing** | **0.9s** | **0.8%** | NEGLIGIBLE — corrects the earlier "~28%" |

Corrections from S10 (both earlier guesses were wrong):
- **Parsing is ~1%, not ~28%.** patitas parsing is genuinely ~0% of the prize;
  the earlier figure was a residual-arithmetic artifact on a noisy box.
- **`related_posts` was ~17% and is now banked** by S9 (~8×, 24s → 3s),
  byte-identical — so the branch is *already* net-faster before the redesign.

Conclusions that drive (and re-scope) the redesign:
1. **The build is ~66% render-bound.** The entire remaining prize is recovering
   the free-threading render plateau, COW-free: ~77s → ~38s ≈ **a third off the
   whole build**. This vindicates #350's original render thesis.
2. **Parse-parallelization and the parse cache are dead** (parse is ~1%). The
   fork boundary still moves *before* parse, but only so workers **own their
   parsed pages** (avoiding the COW tax that sank Phase 1) — not for any
   parse-speedup. Render isolation done right is the whole game.

## The design: a 3-phase shard-parallel build

```
 parent: discover content files  ─┐
                                   │  (small parent heap — cheap fork)
        ┌──────────────────────────┴───────────────────────────┐
        │            fork N persistent shard workers            │
        └──────────────────────────┬───────────────────────────┘
 phase 1 (parallel, worker heaps): each worker parses ITS shard,
          returns LIGHTWEIGHT metadata (title/tags/date/url/section/excerpt/
          xref-entries) — parsed content stays in the worker's heap
                                   │
 barrier (parent): assemble the immutable, serializable RenderPlan
          (nav trees, menus, taxonomy term→pages, related index, page-view
          map for get_page(), frozen xref index, config/params, generated-page
          assignments) from the union of per-shard metadata
                                   │
 phase 2 (parallel, worker heaps): each worker renders ITS shard from its OWN
          parsed content + the received RenderPlan, writes HTML to disk,
          returns accumulations (page data, asset deps, errors)
                                   │
 reduce (parent): merge accumulations; run global postprocess (sitemap, RSS,
          search index, social cards) from site.pages metadata + merged data
```

**Why this is COW-free and scales:** the parent never holds all parsed pages
(the big heap is *distributed* across workers, each holding ~1/N). Workers render
from their own heap + a freshly-unpickled RenderPlan (their own objects). No
shared mutable graph is read or written across the boundary, so the COW tax that
sank Phase 1 disappears. Render (~66% of the build) runs in separate heaps,
recovering the free-threading allocator/GC plateau that the in-thread path
cannot — the realisation of #350's original render thesis. (Parse moves into the
workers too, but only to keep the parsed pages worker-local; parse is ~1% of the
build, so there is no parse-speedup to chase.)

### The one real blocker, and its fallback

`get_page(other_page).content` (a template embedding *another* page's full
rendered body, not just its metadata/excerpt) is the only genuine cross-shard
*content* dependency. Mitigation, in order: (a) the RenderPlan ships a
**page-view** for every page (title/url/excerpt/date/metadata) — enough for the
overwhelmingly common linking/listing use; (b) detect a cross-shard full-body
access and **fall back to the thread path** for that build (never wrong output).
`related_posts` and `xref` are resolved at the barrier (metadata only), so they
are *not* blockers under this design.

## What Phase 1 we keep, and what we replace

- **Keep / extend:** `snapshots/transport.py` (immortalize, `proxy_to_plain`),
  the partitioner (`isolated/partition.py`), the gate (`isolated/gate.py`), the
  parity harness (`test_isolated_render_parity.py`), the probe + case study.
- **Replace:** `isolated/worker.py` + `isolated/backend.py` (fork-after-parse)
  with persistent two-phase shard workers and a small-parent driver.

## Containment contract

- All Phase-2 work stays on `lbliii/render-heap-isolation`.
- `render_isolation` default stays **`off`**; the shard path is never the default
  until S17's end-to-end A/B is green.
- **Fallback value:** even if the redesign (S13/S14) proves too hard, S8–S10
  already make the branch net-faster end-to-end — so the branch materializes a
  *superior build* regardless of the redesign's fate.

## Sagas

### Group A — Trustworthy measurement + certain wins (bank gains, fix methodology)

- [x] **S8 — Trustworthy end-to-end benchmark (DONE).** A deterministic large-fixture
  generator (no `random-posts` widget), phase-attributed E2E timing, thread-vs-
  experimental A/B, idle-box protocol with variance reporting. Fixes the
  cycled-heap / random-widget / saturated-box flaws that made Phase-1 numbers
  unreliable. The yardstick for "superior end to end." *(m)*
- [x] **S9 — `related_posts` candidate index (DONE: ~8x, 24s→3s, byte-identical).** Replace the O(P·T·N) per-page
  rescan with a co-occurrence inverted index built once from the taxonomy
  (`{page: {candidate: shared_tag_count}}`), score in O(K) per page, keep the
  `_stable_key` tie-break. Est. 3–5× (~24s → ~6s). Fork-independent,
  deterministic. *(m)*
- [x] **S10 — Attribute the residual (DONE).** Dumped the authoritative
  `phase_timings_ms`: build is ~66% render, parsing ~1% (corrects the earlier
  ~28% guess). **Parse cache de-scoped** (parse isn't a cost). Next-tier targets
  if render is exhausted: cache-save (9%), post-process (8%), init (7%). *(s)*

### Group B — The shard redesign (holistic core, gated off)

- [ ] **S11 — RenderPlan: the serializable global plan.** Define the immutable,
  picklable `RenderPlan` (nav trees, menus, taxonomy term→pages, related index,
  page-view map for `get_page`, frozen xref index, config/params) assembled from
  lightweight per-shard metadata. The map/reduce contract; extends `SiteSnapshot`
  + S2 transport. *(l)*
- [ ] **S12 — Content sharder (pre-parse).** Partition discovered content *files*
  (not parsed pages) into balanced shards by estimated cost; deterministic.
  Extends `isolated/partition.py`. *(m)*
- [ ] **S13 — Persistent two-phase shard workers.** `mp.Process` actors forked
  from a *small* parent: parse-shard → return metadata → barrier → receive
  RenderPlan → render-shard from own heap → return accumulations. The COW-free
  core; replaces Phase-1's fork-after-parse worker. *(xl)*
- [ ] **S14 — Cross-shard correctness: RenderPlan completeness + fallbacks.**
  `get_page().content` cross-shard detection → ship-or-fallback; xref
  reconciliation across shards; generated-page (tag/archive) assignment to
  shards. Guarantee byte-identical output or a safe thread-path fallback. *(l)*

### Group C — Prove & gate

- [ ] **S15 — Integrate + recalibrate the gate.** Wire the shard build as the
  cold-build path behind `render_isolation`; recalibrate the crossover on the S8
  benchmark (the real E2E crossover, not the pure-render one). *(m)*
- [ ] **S16 — Byte-parity + determinism guard v2.** Extend S6 to the shard path:
  thread == shard, across worker counts, on a large deterministic fixture; prove
  the shard backend actually fired. *(m)*
- [ ] **S17 — Materialization gate (the merge bar).** Idle-box, median-of-N E2E
  A/B proving the shard build **beats the thread build end-to-end** across sizes.
  The branch stays non-default / unmerged until this is green. *(s)*

### Group D — Close

- [ ] **S18 — Write-up + roadmap.** Update the case study, attribution findings,
  and the #350 issue with the redesign, the honest Phase-1 negative result, and
  the Phase-2 numbers. *(s)*

## Gates & invariants

- **Byte-parity is non-negotiable** (S16) — thread == shard, run-to-run and
  across worker counts, on a deterministic fixture.
- **The merge bar is end-to-end speed** (S17), measured on an idle box,
  median-of-N — not render-phase-only and not a cycled-heap microbench.
- **Cold-build / CLI / CI only**; dev server + incremental keep the thread path.
- **Default `off`** until S17; the build always falls back to the thread path on
  any shard-backend failure or unsupported cross-shard content access.

## Risks

- **S13 actor protocol complexity** (persistent workers, barrier, RenderPlan
  serialization) — the XL. Prototype the protocol on a small fixture before
  wiring the full pipeline.
- **RenderPlan completeness** — missing a Type-A dependency ⇒ a subtle output
  diff. S16's parity guard is the backstop; build the RenderPlan field list from
  the Phase-2 dependency audit (cross-chunk-render-deps).
- **`get_page().content` cross-shard** — the one true blocker; the page-view +
  fallback must be airtight (never silently wrong).
- **Per-platform crossover** — fork-only today; spawn (Windows) remains deferred.

## References

- Phase-1 work + honest negative result: this branch (S1–S7),
  `benchmarks/render-isolation-case-study.md`,
  `benchmarks/render-scaling-attribution-findings.md`.
- Backend to replace: `bengal/orchestration/render/isolated/`.
- Reusable foundation: `bengal/snapshots/transport.py`, `isolated/partition.py`,
  `isolated/gate.py`, `tests/integration/test_isolated_render_parity.py`.
