<!-- markdownlint-disable MD013 MD060 -->

# Epic: Performance — Trustworthy Numbers, Then the Free-Threading Hot Path

**Status**: Active
**Created**: 2026-06-02
**Target**: v0.4.0 (beta)
**Estimated Effort**: 4 sagas (Wave 1 ~1 sprint; Waves 2–4 sequenced behind it)
**Dependencies**: None to start (Wave 1 is docs + harness + tests). Engineering waves gate on Wave 1.
**Source**: `bengal-perf-prioritize` analysis workflow (2026-06-02) — 7 parallel dimension deep-dives → score → adversarial critique → reconcile. Load-bearing Wave-1 claims independently re-verified against source (see Verification Log).
**North Star**: Free-threading is the product thesis. 3.14t delivers a committed **1.94x at 1000 pages** over GIL-on. The roadmap serves that thesis; it does not chase absolute throughput.

---

## Why This Matters

Bengal has a real, committed, reproduced performance headline — and a credibility problem sitting on top of it.

**The real headline (keep it):** On free-threaded CPython 3.14t, a 1000-page cold build runs **56.3s with `PYTHON_GIL=0` vs 109.2s with `PYTHON_GIL=1`** — a **1.94x** free-threading speedup (1.24x at 100 pages), measured against Bengal's own GIL-enabled self. Rendering is the dominant phase (~21.9s, ~39% of captured wall), which is exactly where that scaling lives. This is the defensible differentiator and the thing worth optimizing.

**The credibility problem (fix it first):** The public numbers do not match the committed baselines.

1. `benchmarks/README.md:136,141` advertises **"~256 pages/sec (3.14)"** and **"~373 pages/sec (3.14t)"** as bare prose with no runnable benchmark behind it. Every committed baseline measures **~18–20 pages/s** end-to-end — a **~13–20x gap**.
2. `benchmarks/baselines/peak_rss.json` **does not exist** (SPEEDUP.md self-flags "No baseline yet"), so memory tables in the docs are unbacked.
3. The only "performance-evidence" CI job validates a **PR-body checklist** (`scripts/check_performance_evidence.py`) — it runs **no benchmark and compares no number**, so the hot path can regress arbitrarily and merge green.
4. ~31s of the committed 56.3s 1000-page wall is **unattributed to any captured phase** — the harness records only discovery/taxonomy/rendering/assets/postprocess (~25s); parsing, snapshot, content, output-format generation, and `asset_audit` are invisible.

**The honest framing on Hugo:** Bengal is ~22x slower per page than Hugo (compiled Go, ~417 pages/s vs ~19 at 100 pages). That gap is language/interpreter-bound, is **not winnable**, and must be stated plainly and **never used as a headline**. Bengal plays the free-threading game, not the absolute-throughput game.

**The discipline this epic holds itself to:** the reconcile pass caught the analysis's *own* integrity failures — it had quoted an unproven "`asset_audit` is the single largest non-render cost, 26s/42s" magnitude (sourced from a non-committed run under a heavier feature config) and branded a *caveated* docs table "fabricated." Both were corrected. Every engineering magnitude below that comes from a non-committed run is tagged **measure-first** and gated on Wave 1. We do not commit the cherry-pick we condemn in the README.

### Evidence Table

| Source | Finding | Status | Wave |
|--------|---------|--------|------|
| `benchmarks/README.md:136,141` | "~256 pps" / "~373 pps" unqualified prose; no runnable backing | **Verified** | W1·T1 |
| `site/content/docs/about/benchmarks.md:44–51` | 250–285 pps table is an explicitly captioned *best-case, minimal-content* render-light number — a workload-labeling problem, **not** fabrication | Per reconcile | W1·T1 |
| `benchmarks/baselines/peak_rss.json` | Absent; memory docs unbacked | **Verified (missing)** | W3·T9 |
| `.github/workflows/tests.yml:18–25` | `performance-evidence` job runs `check_performance_evidence.py` only — checklist, no benchmark | **Verified** | W2·T6 |
| `benchmark_gil_speedup.py:256–261,309–318` | Captures 5 phases (~25s); ~31s of 56.3s wall unattributed; `asset_audit` → `post_render_timings_ms`, outside baseline | Per analysis | W1·T2,T3 |
| `test_import_overhead.py:187,195,404–405` | Guard tests import dead modules `bengal.utils.logger` / `bengal.utils.hashing` | **Verified (modules absent)** | W1·T4 |
| `bengal/rendering/asset_audit.py:36`; `finalization.py:93–112` | Serial `output_dir.rglob("*.html")` + disk re-read; scoped to changed paths only on incremental (full rglob on cold/strict) | **Verified** | W2·T7 |
| kida `render_helpers.py:152–175,501` (build-time **0.9.0**, workspace `.venv`) | `_make_macro_wrapper` calls `inspect.signature` once per wrapper; per-*call* cost already eliminated, but `_import_macros` re-runs per page → signature runs once per imported macro **per page** | **Verified w/ correction** | W2·T5 |
| `bengal/snapshots/scheduler.py:83,98` | Render path maps snapshot pages back to mutable `PageLike` and passes `self.site` into the pipeline — workers still read mutable Site/Page | Per analysis | W4·T13 |
| `bengal/utils/concurrency/workers.py:116` | MIXED/LOCAL profile `(5,2,12,0.75)`, no `is_free_threaded()` awareness (GIL-era heuristic) | Per analysis | W4·T14 |
| `bengal/snapshots/scheduler.py:300–331` | `WaveScheduler` does `scope.map()` per template group in a loop — each group's straggler idles all workers | Per analysis | W4·T14 |
| `bengal/orchestration/incremental/__init__.py` | `EffectBasedDetector`/`find_work_early` is docstring-referenced only; `phase_incremental_filter_provenance` is the live path | Per analysis | W4·T15 |

### Invariants

These must remain true throughout, or we stop and reassess:

1. **No magnitude without a committed baseline.** Any "this saves Ns" claim must cite a committed JSON cell or be tagged *measure-first*. This epic does not repeat the README's sin.
2. **Architectural constraints hold.** No new core mixins (CI-enforced), no rendering/presentation logic into core `Page`/`Section`, direction of travel toward frozen immutable snapshots and leaf locks — never new shared mutable state. (See `CLAUDE.md`.)
3. **Output-byte parity on every render-path change.** Rendering and incremental changes ship with parity fixtures proving identical output.
4. **Free-threading safety.** New caches must be lock-free idempotent or per-worker; no Tier-2 global locks on the per-page hot path.
5. **Honest public docs.** README/site numbers trace to committed baselines or carry an explicit workload label. Hugo gap stated plainly, never as headline.

---

## Wave 1 Results — Executed 2026-06-02

Wave 1 (T1–T4) is **done and verified**, with down-payments on T7 and T12. The
phase-accounting audit produced the headline finding that re-orders the engineering plan.

**Headline finding — rendering is the dominant cost; `asset_audit` is modest.**
Clean re-measurement on an idle machine (committed `benchmarks/baselines/phase_attribution.json`,
`PHASE_ATTRIBUTION.md`) attributes 93–99.7% of the wall:

| Phase (GIL=0, blog) | 100 pages (median-of-3) | 1,000 pages (single run) |
|---|--:|--:|
| **Rendering** | **1.32 s (45%)** | **23.9 s (68%)** |
| asset_audit | 0.36 s (12%) | 3.9 s (11%) |
| Free-threading | 1.78x | **2.50x** |

Rendering is **the** lever — ~68% at 1000 pages and growing with scale — and the free-threading
speedup (2.50x clean) lives there.

> **⚠️ Self-correction (measurement integrity).** A prior version of this section reported
> `asset_audit` at **22.7 s / 41%** and called it co-equal with rendering, concluding a "~1.7x"
> win. **That was a load artifact** — the single 1000-page run was taken while the machine was
> saturated with concurrent benchmarks/agents (inflated ~14x). Re-measured idle, `asset_audit`
> is ~11–12%. The epic's own discipline ("no magnitude without a clean committed baseline")
> applies to its own numbers; the lesson is recorded in `PHASE_ATTRIBUTION.md`. The
> attribution *shape* (rendering dominates) was robust; the contaminated *magnitude* was not.

**Shipped this pass (all verified):**

- **T1** — `benchmarks/README.md` `256/373 pps` prose replaced with committed baselines + the
  honest free-threading framing; site-doc `benchmarks.md` tables labeled (render-light best
  case; committed 1.94x note; no-memory-baseline note) using correct `:::{warning}`/`:::{note}` syntax.
- **T2** — `benchmark_gil_speedup.py` now surfaces the full `BuildStats` ledger (`phase.*`,
  `post_render.*`, `ppoutput.*`, `unattributed_s`); `_median_phases` medians the key union.
  Baseline keys preserved.
- **T3** — committed `phase_attribution.json` + `PHASE_ATTRIBUTION.md` (≥98% accounted).
- **T4** — 3 dead import-overhead guards repointed to live modules (`primitives.hashing`,
  `observability.logger`) and **passing**; `test_build.py` bit-rot fixed (orphaned
  `small_site`/`large_site` scenarios now auto-generated via `create_minimal_site`; stale
  `page50.md` → `posts/post-50.md`); an incremental test passes end-to-end.
- **T6 (gate shipped, baseline pending)** — added a `--gate`/`--gate-update` mode to
  `benchmark_gil_speedup.py` that checks **per-phase** tolerance (wall, build, rendering,
  `asset_audit`) against a committed baseline, plus `.github/workflows/perf-gate.yml`
  (bootstrap + PR gate). Logic validated locally both directions (PASS within tolerance;
  exit 1 on an injected regression). The baseline (`ci_gate.json`) must be captured on CI
  hardware via the bootstrap job — a laptop baseline isn't comparable, so none was committed.
- **T7 (DONE — serial + memoized)** — `asset_audit.py`: memoized `expected.exists()` by resolved
  path (the same theme assets were stat'd once per page) and skipped the redundant post-`rglob`
  stat. **Byte-identical findings**; the full output-tree `rglob` stays the authority (catches
  `{% cache %}` fragment / special-page / raw refs — a tracked-assets-only design was **rejected**
  by the critique for false negatives). A threadpool parallelization was prototyped but
  **reverted**: bare `ThreadPoolExecutor` is banned in `bengal/` (WorkScope-only, to avoid 3.14t
  CI hangs), and the coherency finding below made the parallel wall benefit on an ~11% phase
  not worth the coupling. Magnitude corrected: asset_audit is ~11% of the build, not the 41% a
  load-contaminated run had claimed.
- **T12 (psutil half)** — deferred `import psutil` out of `performance_collector.py` module
  scope into `PerformanceCollector.__init__`. Verified: importing `bengal.core.site` (and all
  of `bengal.utils`) no longer pulls `psutil`. `asyncio` deferral remains.

**Discovered follow-ups (not regressions from this work — proven via stash):**

- The `kida` / `bengal.rendering.highlighting` import-overhead *timing* thresholds in
  `test_import_overhead.py` are **stale**: kida 0.9.0 cold-imports ~90ms vs a 50ms "lightweight"
  threshold / 10ms baseline. These fail on pristine `main` too. Either kida's import regressed
  (file upstream) or the thresholds need re-baselining — a decision, not a silent bump. Adds a
  task to W3/T16 measurement family.

**Caveats:** numbers measured on a single darwin laptop under load; the 1000-page cell is a
single (slow) run, 100-page is median-of-3. The committed `gil_speedup.json` (authoritative
timing baseline) was deliberately **not** overwritten — the attribution artifact is separate.

---

## Render-scaling investigation + reproducibility wins — 2026-06-02

Pursued the dominant lever (rendering, ~68%). Outcome: a **major reproducibility win
shipped**, the worker-profile tweak **investigated and reverted**, and the real render
ceiling **identified** for a follow-up.

**Shipped — Bengal builds are now byte-reproducible (the headline result).**
Subprocess-isolated builds revealed Bengal was **non-deterministic run-to-run** (two
identical builds differed in `graph/index.html` + many content pages + `tags/index.html`).
For a free-threading-first SSG this is foundational — non-reproducible parallel output breaks
caching, CDN trust, and git diffs. Three root causes found and fixed, each verified:

- **related-posts tie-break** (`related_posts.py`) — scored candidates were sorted by score
  only; equal-score ties resolved by non-deterministic dict-insertion order (set iteration +
  parallel tag→pages build), so each page showed *different* related posts every build. Fixed
  with a stable secondary sort by `source_path`. This alone collapsed the diff from many pages
  to one.
- **tag ordering** (`taxonomies.py` `tag_views`) — single-key sort left equal-count tags
  breaking ties by unstable dict order. Fixed with a name-ordered stable base sort.
- **tag accent** (`taxonomies.py` `tag_accent_index_filter`) — used the builtin `hash()`,
  which Python **randomizes per process** (`PYTHONHASHSEED`), so `data-tag-accent` (and the
  content-hash meta) changed every build. Fixed with a stable `hashlib` digest.

Verified: subprocess-isolated builds are now **byte-identical run-to-run AND across worker
counts (5 vs 8)**; 488 related/taxonomy/worker/thread-safety tests green. This also unblocks
per-phase byte-parity testing for all future render work.

**Investigated then reverted — free-threading-aware worker profile (FIX B).** Render uses
`max_workers=8` on this 5P+6E machine (`int(11×0.75)`), with no `is_gil_disabled()` awareness.
A worker sweep showed E-core oversubscription: at **500 pages**, 5–6 workers beat 8 by ~10–30%.
But a min-of-3 sweep at **1000 pages** showed it is **scale-dependent and adds variance** — by
median, 8 workers was best and far more consistent (capping at P-cores leaves no slack, so
background contention stalls the build). A global default change validated on one machine, that
helps small sites but adds variance at the headline scale, is not defensible — **reverted**.

**Shipped — fast asset extraction (the dominant *profiled* render cost).** `asset_extractor.py`
re-parsed every page's full HTML with the stdlib `HTMLParser` to collect asset dependencies
(the render-time `AssetTracker` is defeated by block/fragment caching). A workflow design +
adversarial critique (the critique caught 3 would-be incremental-correctness bugs: entity
unescaping, the empty-srcset abort, whitespace-tolerant close tags) produced a faithful
single-pass scanner. Verified: **byte-identical** asset set vs the reference parser across 47
adversarial cases + a real build, **~4.1x faster** extraction (4.84 → 1.19 ms/page), builds
still byte-reproducible, 2045 rendering tests green. **Honest result, though:** the end-to-end
*parallel* 1000-page wall did **not** measurably improve (within ±5s run noise). Two lessons:
(1) **cProfile over-attributed it** — the HTMLParser's millions of calls inflated its profiled
share to ~24%, but unprofiled it is ~5s of CPU at 1000 pages; (2) **parallel render is
plateau-bound**, so ~5s of CPU saved across ~5 workers is ~1s wall — below noise. The scanner is
still a real win for sequential builds, CPU/energy, and headroom, and it is correct foundational
work — but it confirms the wall-time lever is the plateau, not per-page CPU.

**The real ceiling — DIAGNOSED 2026-06-02 (and it is NOT lock contention).** A CPU-time vs
wall-time measurement settles it:

| | wall | CPU-time | cpu/wall |
|---|--:|--:|--:|
| sequential (1 core) | 63.6s | 59.2s | 0.93 |
| 8 workers | 35.6s | **152.9s** | **4.29** |

`cpu/wall = 4.29` means the cores are **BUSY, not idle** — so the plateau is **not** my Python
locks (`BuildContext`/`RenderStats`/`BlockCache`); blocked threads would show *low* cpu/wall.
**FIX C as originally scoped (move those locks to thread-local) was therefore NOT implemented —
it would be wasted, risky churn that does not touch the real bottleneck.** The decisive signal:
parallel burns **2.6x the CPU for the same 1000-page work** (152.9s vs 59.2s), and that ~94s of
extra CPU scales **per-page, not per-worker** — the signature of **free-threading's atomic-
refcount / cache-coherency overhead** on the shared objects (Site, SiteSnapshot, nav trees,
caches, config) every worker touches on every page. The render scanner result corroborates:
cutting per-page CPU did not move the wall, because the wall is gated by this coherency tax, not
by CPU throughput.

**The real lever (architectural, hard).** Raising the free-threading ceiling means **minimizing
cross-thread shared-object access in the render hot path** — give each worker a frozen, per-worker
view so shared refcounts stop thrashing (the direction of `rfc-snapshot-build-plan-handoff`,
T13), and/or immortalize hot shared immutables so their refcounts aren't atomically bumped per
access, and/or cut per-page allocation (less GC/refcount traffic). This is a real architectural
program, not a hot-function fix. Next diagnostic to target it precisely: a refcount/coherency
profile (py-spy --native or a sampling refcount probe) to name the specific hot shared objects. The WaveScheduler per-group barrier is
**not** the issue for the blog archetype either: it has one dominant render group (`[300, 94, 1]`
of 395), so the barrier is cheap. Breaking the ~1.7x plateau (thread-local accumulators to remove
`BuildContext`/`RenderStats`/`BlockCache` per-page locks; or confirming a bandwidth ceiling) is
the genuine render lever and the next focused investigation.

## Render-scaling — reframed as actionable epic #343 — 2026-06-04

The 2026-06-02 diagnosis above stands; what changed is the *path to the fix*. The follow-up
was briefly parked (issues #308/#309 closed "not planned", this epic re-scoped) because its
decision gate looked Linux-bound — native refcount attribution (`py-spy --native` + `perf`)
is unsupported on macOS arm64. The 2026-06-04 review reopened it as **epic #343 "Render
scaling — measure clean, then un-share the world"** (sagas #344–#349, superseding #308/#309)
on two insights:

1. **The first question needs no attribution.** Before naming objects, ask whether the ~1.7x
   plateau is fixable at all. A **process-isolation ceiling probe**
   (`benchmarks/probe_render_ceiling.py`, #345) answers that on *any* box — separate heaps =
   zero cross-thread refcounting — and because contamination only biases the process side
   *down*, a positive (processes ≫ threads) is trustworthy even off a noisy machine. A
   contaminated local run already fired a preliminary **GO** (~2.95x processes vs 1.57x
   threads): the plateau is very likely the coherency tax, not a hardware ceiling.
2. **The blocker was a clean measurement environment, not Linux ownership.** This dev Mac runs
   Microsoft Defender (~128% CPU real-time file scanning) and lacks `perf`/`py-spy --native`.
   An ephemeral idle Linux box (#344, driven by `benchmarks/run_clean_box.sh`; a directional
   `workflow_dispatch` probe job also wired into `perf-gate.yml`) supplies both the clean
   numbers and the native attribution.

The attribution then forks the architecture (this is #345 step 2, and maps onto T13 below):
**Site/snapshot graph dominates → owned per-page frames in threads (#347) = universal win;
kida `Environment` dominates → heap isolation only (#347 cold-build/CI), gated on a page-count
crossover; neither → bank #346 (`sys.intern` the hot read-set) + #348 (render invariant chrome
once) alone.** Honest ceiling remains ~2.5–3.5x (P-core bound + un-immortalizable `Environment`
floor + serial FrameBuilder/merge Amdahl tail). See `plan/rfc-frozen-render-world.md` and
`benchmarks/COHERENCY_PROFILING.md`. **Prime invariant: no magnitude committed under load**
(this epic already retracted one load-inflated number).

---

## Goals (Sagas)

Mapped to the repo saga-goal model: a **goal** = a saga-level objective; the ranked **tasks** are its commit-sized slices. Scores are `impact × confidence ÷ effort`, adjusted for strategic fit; higher = sooner.

### Goal 1 — Trustworthy, attributed numbers · Wave 1 · **P0** · do now

You cannot prioritize what you cannot trust. This wave is docs + a few-line harness change + test repair, and it **gates the magnitude-based scoring of every engineering task**.

| # | Task | Score | Eff/Conf | First step | Proof |
|---|------|------:|----------|-----------|-------|
| T1 | Replace unqualified `~256/373 pps` in `benchmarks/README.md`; **label** (don't delete) the site-doc best-case table as render-light/minimal-content | 24 | s/high | Edit README:135–142 to cite `gil_speedup.json` (100p=4.86s/20.6pps, 1000p=56.3s/17.8pps; FT 1.24x/1.94x) + `SPEEDUP.md`; add a "render-light minimal content, not blog archetype" label above the site-doc table | `grep '256 pages/sec\|373 pages/sec'` returns nothing unqualified; site-doc table labeled + points to committed end-to-end numbers |
| T2 | Extend `benchmark_gil_speedup.py` to capture **parsing, snapshot, content, post_render(`asset_audit`)** phase wall in JSON | 24 | s/high | Add `stats.to_dict()` reads + flattened `post_render_timings_ms` sum; append keys to the sample dict and `_median_phases`; regenerate `gil_speedup.json` on the FT build | 1000-page cells expose the new phase keys; their sum + existing five > 90% of `build_time_s` |
| T3 | **Phase-accounting audit** of the ~31s unattributed 1000-page wall; commit the attribution artifact | 24 | s/high | With T2 landed, run blog@1000 GIL=0 median-of-3; produce a committed attribution table (parsing/snapshot/discovery/taxonomy/content/rendering/assets/postprocess/`asset_audit`/output-format) | Artifact accounts for ≥90% of 56.3s wall; the largest non-render serial phase is **named with a committed number** |
| T4 | Fix harness `bengal` import fragility; repair the **dead** import-overhead guards; fix or delete bit-rotted `test_build.py` | 20 | s/high | Add a `PYTHONPATH`/editable-install assertion to harness drivers; rewrite the 3 stale tests to assert `psutil`/`asyncio`/`aiohttp` absent after importing `bengal.core.site` (**drop PIL** — already absent); generate the missing `scenarios/` fixture or delete `test_build.py` and repoint README | Fresh checkout: `benchmark_gil_speedup.py --pages 100` emits non-error JSON; `test_import_overhead.py` collects & passes against live module names |

**Depends:** T3 ⇐ T2.

### Goal 2 — Render hot-path constant + worst serial anchor, in proven order · Wave 2 · **P1** · after the CI gate exists

Lead with the proven slice; do not lead with an unmeasured "huge."

| # | Task | Score | Eff/Conf | First step | Proof |
|---|------|------:|----------|-----------|-------|
| T5 | **Memoize kida's `inspect.signature` by code-object identity** (lock-free) — best risk-adjusted win, leads the wave | 16 | s/high | In kida `render_helpers.py` `_make_macro_wrapper`, add a module-level `{id(macro_fn.__code__): needs_outer_ctx}` cache so signature runs once per distinct macro, not once per page-import. Prototype against `.venv` copy, then **upstream to `kida-templates` and bump the pin** | cProfile `_signature_from_callable` count over a 200-page build drops from tens-of-thousands to #distinct-macros; render avg/pg drops; kida+bengal template suites green |
| ✅ T6 | **Real CI speed-regression gate** — SHIPPED (gate mode + `perf-gate.yml`; logic validated both directions). **Remaining:** bootstrap `ci_gate.json` on CI hardware via the workflow_dispatch job, then watch ~10 PRs for flake at the +30% tolerance | 7 | m/med | Done: `--gate`/`--gate-update` with per-phase keys (wall/build/rendering/`asset_audit`). Run the bootstrap job, commit the artifact | A deliberate 30% slowdown in rendering **or** `asset_audit` fails the job (verified locally); 10 normal PRs pass green (pending CI bootstrap) |
| ✅ T7 | Speed up the post-render `asset_audit` scan — **DONE (serial + memoized).** (Magnitude corrected: ~11% of the build, not the 41% a load-contaminated run claimed.) Memoized `exists()` by resolved path + skipped redundant stats; **byte-identical** findings; full output tree still walked (no false negatives). Threadpool parallelization reverted (bare `ThreadPoolExecutor` banned; coherency finding made the wall benefit not worth it on an 11% phase). | done | s/high | Done. A rejected design (reuse render-tracked assets only) would have introduced false negatives on `{% cache %}` fragments / special pages / raw refs — the critique caught it. | byte-identical findings ✅; 7 audit tests + integration green ✅ |
| T4-scaling | **Render scaling — the REAL dominant lever (68%).** Diagnosed 2026-06-02: barrier is NOT it (one dominant group); worker-profile (FIX B) reverted; **locks are NOT it either** (cpu/wall=4.29 → cores busy, not blocked). Root cause is **free-threading atomic-refcount / cache-coherency overhead** — parallel burns 2.6x CPU for the same work, per-page. The ~1.7x plateau is Python 3.14t's coherency tax on shared objects. | high | xl/med | Refcount/coherency profile (py-spy --native) to name hot shared objects; then minimize cross-thread shared-object access in render (frozen per-worker views — T13/snapshot handoff), immortalize hot shared immutables, cut per-page allocation | FT ratio rises above ~1.7x at 1000p with byte-parity (now guaranteed) |
| ❌ FIX C (locks) | Thread-local accumulators for `BuildContext`/`RenderStats`/`BlockCache` per-page locks | n/a | — | **NOT pursued** — diagnostic proved the cores are busy (cpu/wall=4.29), not blocked on these locks; the bottleneck is free-threading coherency overhead, so removing the locks would be wasted churn | — |
| ✅ reproducibility | **Builds are now byte-reproducible** (run-to-run AND across worker counts) | done | m/high | Done: stable related-posts tiebreak, stable tag ordering, stable (non-`hash()`) tag accent | subprocess builds byte-identical ✅; 488 tests green ✅ |
| T8 | Harvest assets from cached blocks to kill per-page asset-dependency HTML re-parsing | 6 | m/med | In `warm_site_blocks`, run `extract_assets_from_html` once per cached site-scoped block; seed/union the per-page tracker so the HTMLParser fallback is skipped | RenderProfiler "Asset dep accumulate" avg/pg drops; blog@1000 `rendering_s` drops vs the CI gate; asset-dep incremental tests green |

**Depends:** T5,T7,T8 ⇐ T6 (provability); T7 ⇐ T3 (magnitude).

> **Note on T5↔T11:** the per-*call* `inspect.signature` cost is already eliminated in kida 0.9.0; the residual is per-page (because `_import_macros` re-runs per page). T11 (don't re-import per page at all) would **subsume** T5 — so T5 is a cheap foothold that may be made moot by T11. Sequence T5 first only because it's proven and tiny; re-evaluate after T3/T6 quantify the macro-import cost.

### Goal 3 — Author dev-loop + remaining render constant · Wave 3 · **P1** · parallel with late Wave 2

| # | Task | Score | Eff/Conf | First step | Proof |
|---|------|------:|----------|-----------|-------|
| T9 | Publish a committed **peak-RSS baseline** + memory CI gate | 16 | s/high | `benchmark_peak_rss.py --publish` median-of-3 at 1k (+5k if time); commit `peak_rss.json`; replace unbacked site-doc MB table with measured medians | `peak_rss.json` exists with 1k+ cells; SPEEDUP.md renders a peak-RSS table; CI row asserts `peak_rss_mb < budget` |
| T10 | Commit a **warm-build baseline**, then make single-page warm builds cost **proportional to changed pages** | 5.6 | l/med | Commit no-change/single/multi/template-edit baselines @100/500/1000; then reuse persisted discovered pages instead of re-running discovery; gate content phase on `affected_tags`/`affected_sections` non-empty | Single-edit warm build flat vs site size; Discovery/Content/Filter no longer scale with total pages; incremental-correctness + new parity tests green |
| T11 | Full kida macro-import memoization per build (after T5 foothold) — **medium/low-confidence bet** | 2.67 | l/low | Memoize the imported macro namespace per `(template_name, with_context)` within a build; share **only** context-free imports (with-context macros close over page state, must not be shared) | Render avg/pg drops beyond the T5 gain vs the CI gate; output-byte parity across fixtures |
| T12 | Defer `psutil`/`asyncio` off the build path — **`psutil` half DONE** (deferred into `PerformanceCollector.__init__`; `bengal.core.site` no longer pulls psutil; T4 guard green) | 12 | s/high | **Remaining:** trace + defer the eager `asyncio` chain from `bengal.core.site` | `from bengal.core.site import Site` leaves `psutil` ✅ and `asyncio` out of `sys.modules`; T4 guard stays green |
| T16 | Add a **docs/autodoc-archetype FT baseline** (directive-heavy workload) | 16 | s/high | Add a directive-rich/syntax-highlighted archetype cell to `benchmark_gil_speedup.py` @100/1000; commit alongside blog cells | `gil_speedup.json` contains docs-archetype cells; FT speedup reported for directive-heavy, not just blog |

**Depends:** T9,T12,T16 ⇐ T4; T10 ⇐ T6; T11 ⇐ T5.

### Goal 4 — Architectural scaling + cleanup · Wave 4 · **P2/P3** · after the cheaper wins prove out

| # | Task | Score | Eff/Conf | First step | Proof |
|---|------|------:|----------|-----------|-------|
| T13 | Execute the **snapshot build-plan handoff** to remove mutable Site/Page reads from render workers (sanctioned `rfc-snapshot-build-plan-handoff`) | 5.6 | l/med | RFC Migration step 2: route one measured render hot path through a frozen `BuildPlan`/`PagePlan`, keep the mutable fallback, prove output-byte parity (cold/warm/template-edit/content-edit) | Worker-scaling speedup improves; `gil_speedup.json` 1000-page speedup rises **above 1.94x** with parity fixtures green |
| T14 | FT-aware worker profile + replace `WaveScheduler` per-group barriers with a continuous queue | 6 | m/med | Run `calibrate_worker_thresholds.py` on FT at workers ∈ {8,11,16}; add an `is_free_threaded()`-aware profile; submit all pages to one `WorkScope` in template-locality order | `rendering_time_ms` improves at the calibrated count without p95 regressing; render speedup vs GIL=1 rises; `block_cache_hits` flat after the barrier change |
| T15 | Delete/consolidate the **dead second incremental system** (`EffectBasedDetector`/`find_work_early`) | 6 | m/high | Confirm provenance-filter data-file/template fallback lookups are served by the dependency index, then delete the tracer path or fold its read model into the provenance filter as single source of truth | Single live incremental path; LOC drop in `bengal/orchestration/incremental`; incremental + dev-server suites green |
| T17 | Fix or **retire `--memory-optimized`** ("80–90% reduction" claim; measured the opposite) | 4 | m/high | Demote to experimental + remove the claim; attempt a fix only after T9 baseline + snapshot dedup exist | `peak_rss.json` with `memory_optimized=True` ≤ standard at 1k+5k median-of-3, **or** the flag/claim is removed and the matrix updated |
| T18 | Reconcile **duplicate cross-SSG generators**; purge contradictory `tests/performance` docs | 3 | m/med | Designate the generator behind committed `cross_ssg.json` canonical; point matrix + publish path at it; delete the other; purge contradicting pps figures | Exactly one cross-SSG generator referenced by matrix + publish; no `tests/performance` pps figure contradicts `cross_ssg.json` |
| T19 | Validate or down-scope the **effect-traced Merkle DAG cache** before broad investment (largest speculative bet; global-lock FT hazard) | 1 | xl/low | Build the Phase-2 prototype + benchmark on `tests/roots/full_site` **after** T10/T15; honor the RFC abort criterion (<15% ⇒ revise/abandon); shard effect state per worker | Prototype shows ≥25% warm-build improvement with zero false-negative rebuilds, **or** the RFC is formally down-scoped |

**Depends:** T13,T14 ⇐ T6; T15 ⇐ T10; T17 ⇐ T9; T19 ⇐ T10,T15.

---

## Open Questions (gate Wave-2 ordering)

1. After T2+T3: which serial phase actually dominates the ~31s — `asset_audit`, markdown parsing, snapshot build, content phase, or output-format generation? **T7's rank depends on this.** `asset_audit` may not be the largest under the committed config.
2. Is render's sub-linear scaling memory-bandwidth-bound, P/E-core asymmetry (5P+6E), the `WaveScheduler` barrier, or kida-internal contention? Needs a worker sweep + thread-aware profiler before T14's worker-ceiling change.
3. How much of per-page render cost is recoverable by T11 given with-context macros can't be shared? Determines whether T11 earns its large effort beyond the T5 slice.
4. Which downstream consumers read `page.rendered_html`/`html_content` after the render phase? Must be enumerated before any release-after-write memory change or the T7 in-memory scan (repo history: ~50% false-positive rate on surface-level retention analysis).
5. All committed baselines are single-machine (darwin laptop), single interpreter (3.14.2t), median-of-3 — no Linux/CI, no CIs, no Python-peer comparison (mkdocs/pelican "not installed"). How much of 1.94x and the 22x-Hugo gap hold on CI hardware, and is there an honest Python-vs-Python positioning?
6. Has the 0.3.3 warm-build batch (lazy Kida context, cached template-dependency discovery, parsed-cache reuse) already captured part of the effect-traced RFC's ~40% target? Re-baseline (T10) before T19 is worth prototyping.
7. What is `bengal serve` end-to-end HMR/restart latency? Most user-perceived surface; no committed baseline captures it.
8. kida is a pinned dep (`kida-templates>=0.9.0`), not a workspace sibling — T5/T11 both require upstreaming + re-pin. Who owns that release path?

---

## Verification Log (2026-06-02)

Independently confirmed against source before committing this plan (per the verify-before-refactoring standard):

- ✅ `benchmarks/README.md:136,141` — "~256 pages/sec" / "~373 pages/sec" present and unqualified.
- ✅ `benchmarks/baselines/peak_rss.json` — absent.
- ✅ `.github/workflows/tests.yml` `performance-evidence` job — runs `check_performance_evidence.py` only; no benchmark.
- ✅ `bengal/utils/logger.py` and `bengal/utils/hashing.py` — do **not** exist; the import-overhead guards reference dead modules.
- ✅ `bengal/rendering/asset_audit.py:36` — serial `output_dir.rglob("*.html")` + disk re-read; `finalization.py:100–102` scopes to changed paths only on incremental.
- ✅ Build-time kida is **0.9.0** (workspace `.venv`, `uv run`), not the stale global 0.6.0. `render_helpers.py:161–165` already pre-computes `needs_outer_ctx` once per wrapper — **correction to the analysis:** the per-*call* signature cost is already gone; the residual is per-page-per-imported-macro via `_import_macros`. T5's memoization is still valid; its framing and magnitude are corrected accordingly.

Magnitudes sourced from non-committed runs (asset_audit 26s/42s; render 2.1–2.3x; warm 6–9x; ~597 MB) are tagged **measure-first** and are explicitly **not** load-bearing for Wave 1.
