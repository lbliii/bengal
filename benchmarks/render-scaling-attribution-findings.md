<!-- markdownlint-disable MD013 -->

# Render-scaling attribution — findings & funding gate (issue #350 / S1)

**Status**: Funding gate for the heap-isolation render backend.
**Probe**: `benchmarks/probe_render_ceiling.py` (self-contained, reproducible).
**Companion runbook**: `benchmarks/COHERENCY_PROFILING.md` (`py-spy --native` allocator gate).

## The prize, restated

Page rendering is ~68% of a cold build. On free-threaded CPython (3.14t) the
in-process (ThreadPool) render path **plateaus** well below the speedup the same
work reaches in **separate heaps** (fork ProcessPool) on the same machine and the
same parsed page set. Recovering that gap for large cold builds is the whole point
of epic #350.

## What the probe measures

`probe_render_ceiling.py` builds a site once to warm markdown parsing (so every
timed render reads `page.html_content` from memory — we time *rendering*, not
parsing), then re-renders the identical page set three ways, median-of-N:

1. **sequential** — one thread (the baseline).
2. **threads × W** — `ThreadPoolExecutor`, the production in-process path.
3. **fork × W** — `multiprocessing` fork `Pool`; like the production backend,
   workers inherit the parsed site read-only via copy-on-write, zero serialization.

It reports each variant's speedup over sequential and the separate-heap advantage
(`fork_speedup / thread_speedup`).

## Reproduced here (not the headline box)

Measured on this workspace's dev Mac (M3 Pro, free-threaded 3.14.2t) against
`tests/roots/test-large` (135 rendered pages incl. generated), `--workers 8
--runs 3`:

| variant | wall | speedup |
|---|--:|--:|
| sequential (1 core) | 1116 ms | 1.00× |
| threads × 8 | 575 ms | **1.94×** |
| fork procs × 8 | 276 ms | **4.04×** |

**Separate-heap advantage over threads: 2.08×.** The in-thread path plateaus near
~2× while separate heaps reach ~4×, on identical work — the gap the backend exists
to recover. (This is a small, dev-box reproduction to validate the *shape*; it is
not a clean-room committed magnitude.)

## The authoritative measurement (epic #343 / saga #345, clean box)

The clean-room attribution recorded in issue #350 (branch
`lbliii/render-scaling-clean-box`, `benchmarks/run_clean_box.sh`) found, on an
idle M3 Pro at 400 pages, median-of-3:

- in-process plateau **2.26×**, separate-process ceiling **4.64×**;
- parallel render burns **2.48× the CPU** for identical work (cpu/wall 1.21 → 7.72)
  — cores are **busy, not blocked**.

### Why NOT in-thread (the decisive experiment)

Every in-thread lever the clean-box sweep tried recovered ≤7% (≈ 3-run noise):

| in-thread lever | Δ render CPU |
|---|--:|
| `sys.intern` hot shared strings | −0.1% |
| per-thread (owned) global contexts | +0.3% |
| frozen `PageSnapshot` view at `context['page']` | +2.3% |
| immortalize the `SiteSnapshot` graph (23K objs) | +7% |
| **immortalize the ENTIRE shared world (142K objs, zero refcount)** | **+2%** |
| freeze + disable GC during render | +3.6% |

Process isolation recovers **+105%**. The load-bearing experiment is whole-world
immortalization: immortal objects are never refcounted, so removing *all* refcount
traffic on the shared read-set should have captured the entire biased-refcount tax
— and it captured ~nothing.

### Corrected diagnosis (supersedes prior RFCs)

- **The tax is NOT Python-object refcount coherency.** This corrects
  `plan/epic-performance.md` / `plan/rfc-frozen-render-world.md`, which attributed
  the plateau to atomic-refcount / cache-coherency overhead. Immortalizing those
  objects disproves it.
- The kida `Environment` is already per-thread (no shared-Environment floor).
- The residual ~2× is **allocator / GC / interpreter-level contention** (GC ≈ 3.6%;
  the remainder is, by elimination, the memory allocator), recoverable only by
  **separate heaps**.
- Therefore **in-thread owned-per-page frames will not move the number — do not
  build them** (redirects #347). `sys.intern` (#346) is dead as a perf lever.

## Funding gate (the one thing left to *name*)

The prize (4.64×) and "it's not refcount" (whole-world immortalization) are already
strong. S1's remaining job is to name the *allocator* specifically rather than infer
it by elimination:

```sh
# 8-worker cold build, native stacks, then fold for allocator vs refcount frames.
sudo py-spy record --native --rate 250 --format raw -o coh.txt -- \
    .venv/bin/python -m bengal build --workers 8 <large-site>
```

Aggregate folded stacks for `malloc`/`free`/`mi_*` (mimalloc) frames vs
`_Py_atomic`/refcount frames. **Allocator-dominant ⇒ gate passes**, the residual is
the allocator, and the heap-isolation backend (S2–S6) is funded. See
`benchmarks/COHERENCY_PROFILING.md` for the full environment requirements (real PMU,
not Docker-on-Mac).

## Honest ceiling

~**4.6×** on this M3 Pro (P/E-core-bound), via heap isolation — **not linear**, and
bounded by the serial partition/merge Amdahl tail. The backend recovers the gap
between the in-process plateau and the separate-heap ceiling for **large cold
builds only** (CLI / CI). It regresses the dev loop and incremental builds, so it
sits behind a crossover gate (S5).
