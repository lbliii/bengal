<!-- markdownlint-disable MD013 -->

# RFC: Frozen Render-World + Owned Per-Page Frames (free-threading render scaling)

**Status**: Draft — **investigation; NOT approved for migration.** The central bet is
**unvalidated** and the cheap experiments to date are inconclusive-to-negative (see
Validation). Do not start the migration until Step 0 (native profiling on a supported
platform) confirms the fixable share.
**Created**: 2026-06-02
**Owner**: performance
**Related**: `plan/epic-performance.md`, `plan/rfc-snapshot-build-plan-handoff.md` (this is
its potential completion), `benchmarks/baselines/phase_attribution.json`.

---

## Problem (measured, robust)

On free-threaded CPython 3.14t, Bengal's render phase scales sub-linearly and **plateaus
at ~1.7–1.8x** regardless of worker count. Measured on a 5P+6E Apple Silicon machine,
1000-page blog, in-process `Site.build`:

| | wall | CPU-time | cpu/wall |
|---|--:|--:|--:|
| sequential (1 worker) | 63.6s | 59.2s | 0.93 |
| 8 workers | 35.6s | **152.9s** | **4.29** |

`cpu/wall = 4.29` ⇒ cores are **busy, not blocked** (so it is **not** lock contention).
Parallel burns **2.6× the CPU for the same logical work** (152.9s vs 59.2s), and the extra
~94s scales **per-page, not per-worker**. The cores spend cycles on something other than
useful rendering throughput.

## What we ruled out (with evidence)

- **Lock contention** — `cpu/wall=4.29` (busy, not blocked). Bengal's per-page
  `threading.Lock` sites are not the bottleneck. (FIX C — thread-local accumulators — was
  scoped and then **not implemented** for this reason.)
- **The scheduler barrier** — the blog has one dominant render group (`[300, 94, 1]` of
  395), so the `WaveScheduler` per-template-group barrier is cheap here.
- **Worker count / E-core oversubscription** — an FT-aware worker-profile tweak helped at
  500 pages but was scale-dependent and added variance at 1000; reverted.
- **Allocation / GC** — a **clean** microbenchmark of pure thread-local allocation work
  (build strings/lists/dicts per round, no shared data) scales **5.4× on 8 threads with
  only 1.49× CPU inflation, and GC on/off is identical.** So allocation and GC parallelize
  fine; they are **not** the ceiling. (This also means the `asset_extractor` scanner's
  CPU reduction, while real, won't move the parallel wall — confirmed.)

## What we believe (associated, but NOT cleanly validated)

The tax co-occurs with **reading/iterating shared Python container objects** across
threads: a microbenchmark traversing the build's real shared `config`/`menu`/section graph
shows **4–6× CPU inflation at 8 threads** for the same work, versus 1.49× for thread-local
allocation. The working hypothesis is **free-threading's atomic-refcount / cache-coherency
traffic** on the shared objects (`Site`, `SiteSnapshot`, nav trees, taxonomy tables,
caches, the Kida `Environment`, config dicts) that every worker touches on every page.

## ⚠️ Validation status — why this is a Draft, not a plan

I tried to validate the fix cheaply on Bengal's real data and **could not**:

- A generic synthetic probe (owned vs shared deep-graph walk) showed a 33.7× owned-vs-shared
  difference — but **it did not replicate on Bengal's real data shapes.**
- **`deepcopy`-owning the shared graph did not help** (and measured worse) — because
  `deepcopy` does **not** copy strings (they're immutable; the same objects stay shared),
  so shared-string refcounts still thrash; and per-thread copies add cache-footprint.
- **`sys.intern()` immortalizes strings on 3.14t** (verified: interned refcount = immortal
  sentinel, `sys._is_immortal` True). But interning the shared graph's strings **did not
  reduce** the traversal inflation (~6× before and after) — implying the contention is on
  the **containers**, not the strings. Yet owning the containers didn't help either.
- These results are **contradictory**, which means the mechanism is subtler than the
  synthesis assumed and **microbenchmarks cannot settle it.** The decisive tool — native
  refcount/coherency profiling (`py-spy --native`) — is **not supported on macOS arm64**,
  and scalene/yappi aren't installed.

**Conclusion: the central architectural bet (own per-page data / immortalize the shared
read-set to cut the tax) is currently UNSUPPORTED by any clean experiment on Bengal's real
workload.** The honest position is that we know the *symptom* (2.6× CPU inflation tied to
shared reads, not locks/allocation/GC) but not the *fixable share* or the *effective lever*.

## Proposed direction (IF Step 0 validates it)

"Frozen Read-World + Owned Per-Page Frames" — the completion of
`rfc-snapshot-build-plan-handoff`, in composable phases, each independently shippable,
`cpu/wall`-measured, and byte-parity-gated (builds are now byte-reproducible, so parity is
checkable):

1. **Frozen RenderWorld** — one frozen world derived from the existing `SiteSnapshot`;
   re-point the verified hot-path Site dereferences in `bengal/rendering/engines/kida.py`
   (`ctx.update({"site": self.site, "config": self.site.config})`, `_get_menu`) and
   `SiteContext`'s backing off the live mutable `Site`. Delete `_raw_site`
   (`context/__init__.py:301`, zero production consumers). Intern the world's hot strings
   (`sys.intern` ⇒ immortal).
2. **Owned per-page `RenderFrame`** — a single-threaded `FrameBuilder` emits one flat
   frozen record per page (every template-visible value pre-resolved to plain
   str/int/tuple/MappingProxy; posts/subsections as frozen `PageRef` tuples, never live
   pages). Workers render from `RenderFrame` + the shared world only.
3. **Remove `site` from the worker signature** + a guard test that the worker context holds
   no live-`Site` reference.

## The hard gate: Step 0 (do this BEFORE funding 1–3)

Run a native refcount/coherency profile of the 8-worker 1000-page build on a **supported
platform** (Linux + `py-spy --native`, or an instrumented/`perf` run, or a debug-build
refcount counter) and **name the objects whose refcounts dominate cross-thread traffic.**

- If the **Site/snapshot container graph** dominates → Phases 1–2 are justified; proceed.
- If the **Kida `Environment` / compiled-template objects** dominate → owning per-page data
  will **not** help (those are shared by construction and there is no public API to
  immortalize arbitrary instances); re-point to a C/Cython immortalization spike or to
  isolation (below).
- If neither clearly dominates → the 2.6× is diffuse coherency/allocator-microarch and the
  realistic ceiling is near the P-core count regardless; **do not migrate.**

## Alternatives (size-gated complements, not the primary path)

- **Isolation** (`ProcessPoolExecutor` / PEP 734 sub-interpreters — both verified present on
  3.14t): the only approach that *structurally* eliminates cross-thread refcounting (separate
  heaps), but pays per-worker import/Environment-rebuild + serialization + cross-page-cache
  loss that scale the wrong way for incremental/dev-loop builds. Validate with a standalone
  startup-amortization micro-benchmark and a proven crossover page-count before any
  integration. Candidate for **large cold builds only**.
- **C/Cython immortalization shim** on the few shared roots — removes the shared-engine
  refcount floor, but is CPython-version-fragile; benchmark-gated only.

## Honest ceiling

Even if Phases 1–2 validate, the realistic render speedup is **~2.5–3.5×, not linear 8×**,
bounded by: (a) the shared-engine refcount floor (no public instance-immortalization API for
the `Environment`); (b) P/E-core asymmetry (~5 effective P-cores ⇒ ~3–4× structural cap);
(c) the Amdahl tail (single-threaded `FrameBuilder` + write/merge). And per Validation, even
~2.5× is **not yet evidenced** — it is the synthesis's estimate, which the cheap experiments
did not corroborate.

## Decision

**Hold.** Do not begin the migration. Fund only Step 0 (native profiling on a supported
platform) and, separately and cheaply, the isolation startup-amortization micro-benchmark.
Re-open this RFC for approval once Step 0 names the dominant contended objects and a
single-step PoC shows a real `cpu/wall` drop with byte-identical output. The shipped
correctness/measurement work (byte-reproducible builds, fast extraction, honest baselines,
CI gate) stands on its own regardless of this RFC's outcome.
