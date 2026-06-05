<!-- markdownlint-disable MD013 -->

# Case study: scaling a free-threaded renderer past the in-process plateau

*A reusable methodology for diagnosing — and recovering — free-threading scaling
ceilings. Issue #350; folds in the community write-up #349.*

Bengal is a pure-Python static site generator built for free-threaded CPython
(3.13t/3.14t). Page rendering is ~68% of a cold build, embarrassingly parallel,
and touches a large read-only shared world (the site graph, config, nav trees).
On paper it should scale with cores. It didn't — and *why* it didn't turned out
to be a more interesting (and more general) story than "Python is slow."

This is the honest version: what we measured, the experiment that overturned our
own diagnosis, and the backend we built once we believed the data.

## 1. The symptom: a ~2× plateau that isn't a hardware wall

Parallel render on a free-threaded interpreter plateaued at roughly **2.3×**
regardless of worker count, on a machine with far more cores. The first instinct
— "we're lock-bound" — was wrong: measuring CPU-time vs wall-time showed
`cpu/wall` climbing to **~7.7** under load. Cores were **busy, not blocked**.
Parallel render burned **~2.5× the CPU** for the *same* work, and the cost scaled
**per page, not per worker**.

That signature (busy cores, per-page CPU inflation) is the classic fingerprint of
**free-threading's shared-object overhead**: under PEP 703, every reference to a
shared object touches its refcount, and a refcount written from many cores
bounces the cache line between them. So we assumed the tax was **biased-reference-
counting / refcount coherency** on the shared read-set, and that the fix was to
stop refcounting those objects.

## 2. The ceiling probe: is the prize even real?

Before optimizing, we measured the *ceiling* — how fast the identical render work
goes when it can't share Python objects at all, i.e. in **separate processes**.

`benchmarks/probe_render_ceiling.py` builds a site once (to warm parsing), then
re-renders the same parsed page set three ways, median-of-N:

1. sequential (1 thread) — the baseline;
2. `ThreadPoolExecutor` × W — the production in-process path;
3. fork `Pool` × W — separate heaps, sharing the parsed site read-only via
   copy-on-write, zero serialization.

On a clean M3 Pro at 400 pages: threads plateaued at **2.26×**, fork reached
**4.64×**. The prize — a ~2× throughput gap between in-thread and separate-heap —
is **real and not a hardware wall**. (Reproduced at smaller scale in
`benchmarks/render-scaling-attribution-findings.md`.)

**Lesson 1: measure the separate-process ceiling first.** It tells you whether a
scaling problem is recoverable in software at all, and bounds the prize before you
spend effort chasing it.

## 3. The experiment that refuted our own diagnosis

If the tax were refcount coherency on the shared read-set, then making those
objects **immortal** — CPython 3.14's `_Py_SetImmortal`, which freezes an object's
refcount so reads and DECREFs are no-ops — should remove it. We swept levers from
cheap to nuclear (M3 Pro, 400 pages, render CPU-time, Defender-robust signal):

| in-thread lever | Δ render CPU |
|---|--:|
| `sys.intern` the hot shared strings | −0.1% |
| per-thread (owned) global render contexts | +0.3% |
| frozen `PageSnapshot` view at `context['page']` | +2.3% |
| immortalize the `SiteSnapshot` graph (23K objs) | +7% |
| **immortalize the ENTIRE shared world (142K objs, zero refcount)** | **+2%** |
| freeze + disable GC during render | +3.6% |

The load-bearing experiment is the last big one: **immortalize the whole shared
world.** Immortal objects are never refcounted, so if the plateau were refcount
traffic on shared reads, zeroing *all* of it should have captured the entire tax.
It captured ~2% — noise. Process isolation, by contrast, recovers **+105%**.

**The diagnosis was wrong.** The tax is *not* Python-object refcount coherency.
This corrected our own prior RFCs, which had attributed the plateau to
atomic-refcount / cache-coherency overhead on shared objects.

**Lesson 2: immortalize-the-world is a decisive refutation tool.** If freezing
every refcount in the shared read-set doesn't move the number, the bottleneck is
not refcount coherency — no matter how much the `cpu/wall` signature looks like
it. Use the nuclear option to *kill a hypothesis*, cheaply, before building on it.

## 4. What's actually left, by elimination

With refcounting excluded and the kida template `Environment` already per-thread
(verified: N render threads → N+1 distinct engines, zero shared), the residual ~2×
is **allocator / GC / interpreter-level contention** — heap structures shared
across cores that aren't Python refcounts: the memory allocator's arenas, GC
bookkeeping (~3.6%), and interpreter-global state. GC we measured directly; the
allocator is named by elimination and confirmed with `py-spy --native` (the gate
in `benchmarks/COHERENCY_PROFILING.md`). These are exactly the things that **only
separate heaps** eliminate — which is why fork recovers the gap and no in-thread
lever does.

**Lesson 3: "busy cores + per-work CPU inflation" has more than one cause.** It
fingerprints refcount coherency *and* allocator/GC contention identically at the
wall-clock level. Only an intervention that removes one and not the other (here:
immortalization) can tell them apart.

## 5. The backend: heap isolation for large cold builds

Believing the data, we built a **separate-heap render backend**
(`bengal/orchestration/render/isolated/`) instead of the in-thread owned-frame
work the old diagnosis implied (which we'd have built, and which would have moved
nothing):

- **Partition** the render set into cost-balanced chunks, one per worker
  (deterministic — a prerequisite for reproducible output).
- **Fork** one worker per chunk *after* the parse+snapshot phase. Each worker
  inherits the entire parsed site read-only via copy-on-write — **zero
  serialization**. The catch under free-threading is that *reading* an inherited
  object writes its refcount and dirties the shared COW page; so we **immortalize
  the frozen snapshot** (`_Py_SetImmortal`) so reads write nothing and the pages
  stay shared. (Immortalization here is a transport optimization, not the
  perf thesis — and a deliberately *bounded* walk, so it never escapes into the
  mutable graph and leaks the whole heap.)
- **Serial merge**: each worker writes its HTML straight to disk and returns only
  a small picklable summary (accumulated page data, asset deps, unresolved
  xrefs); the parent replays those so postprocess (search index, per-page JSON,
  sitemap, feeds) produces the same site-global artifacts.

It's gated behind a page-count **crossover** and scoped to **cold CLI/CI builds**:
per-worker startup and immortalization-leak make it a loss for the dev server and
incremental builds, which keep the thread path. And it falls back to threads on
any failure, so isolation can never break a build. Output is **byte-identical** to
the thread path, verified across worker counts
(`tests/integration/test_isolated_render_parity.py`).

## 6. Honest ceiling

~**4.6×** on this M3 Pro (P/E-core-bound) via heap isolation — **not linear**, and
bounded by the serial partition/merge Amdahl tail. The backend recovers the gap
between the in-process plateau (~2.3×) and the separate-heap ceiling (~4.6×) for
large cold builds. The primary beneficiary is the Linux CI / dogfood cold build,
where `fork`+COW is most efficient.

## 7. Takeaways for free-threading work

1. **Measure the separate-process ceiling first** — it bounds the prize and proves
   recoverability before you optimize.
2. **`cpu/wall` separates lock-bound from coherency/allocator-bound**, but does
   *not* separate refcount coherency from allocator/GC contention.
3. **Immortalize-the-world to refute the refcount hypothesis.** A cheap, decisive
   experiment that can save you from building the wrong fix.
4. **Some free-threading ceilings are allocator/GC/interpreter-level**, not
   Python-object-level, and are only recoverable with separate heaps — for which
   `fork`+COW + immortalized read-set is the zero-copy transport.
5. **Guard byte-parity explicitly**, and prove your fast path actually fired — a
   silent fallback makes a parity test pass for the wrong reason.

## References

- Probe & gate: `benchmarks/probe_render_ceiling.py`,
  `benchmarks/render-scaling-attribution-findings.md`,
  `benchmarks/COHERENCY_PROFILING.md`, `benchmarks/calibrate_render_isolation.py`
- Backend: `bengal/orchestration/render/isolated/`,
  `bengal/snapshots/transport.py`
- Parity guard: `tests/integration/test_isolated_render_parity.py`
- Epic #350 (this work); supersedes the in-thread direction of #347; #346
  (`sys.intern`) retired as a perf lever.
