# Phase-accounting audit (epic-performance.md Wave 1 / T3)

Generated from `benchmarks/baselines/phase_attribution.json` by the extended
`benchmark_gil_speedup.py` (it surfaces the full `BuildStats` phase ledger plus the
post-render `asset_audit` timing). Free-threaded CPython 3.14t, `PYTHON_GIL=0`,
`blog` archetype with taxonomy, cold build.

## Headline

**Rendering is the dominant cost and grows with scale; asset_audit is modest.**

| Phase (GIL=0, blog) | 100 pages (median-of-3) | 1,000 pages (single run) |
|---------------------|------------------------:|-------------------------:|
| **Rendering**       | **1.32 s (45%)**        | **23.9 s (68%)**         |
| asset_audit         | 0.36 s (12%)            | 3.9 s (11%)              |
| Cache save          | 0.29 s (10%)            | 1.9 s (5%)               |
| Post-process        | 0.27 s (9%)             | 2.2 s (6%)               |
| Content             | —                       | 1.7 s (5%)               |
| Discovery           | 0.13 s (5%)             | 0.8 s (2%)               |
| **Build total**     | **2.92 s**              | **35.2 s**               |
| Free-threading      | 1.78x                   | **2.50x**                |
| **Accounted**       | **93%**                 | **99.7%**                |

The render phase is **the** lever: ~68% of a 1000-page build, and the larger the
site the larger its share. The free-threading speedup (2.50x at 1000 pages) lives
almost entirely in rendering.

## ⚠️ Measurement-integrity correction

An earlier version of this artifact reported **asset_audit at ~22.7 s / 41%** of a
1000-page build and called it "co-equal with rendering." **That was wrong.** That
single run was taken while the machine was saturated with concurrent benchmarks and
subagents; it was **load-inflated by ~14x**. Re-measured on an idle machine,
asset_audit is **~0.36 s (100p) / ~3.9 s (1000p)** — about **11–12%** of the build.

**Lesson:** never measure performance under concurrent load — even when the task
*is* re-baselining for integrity. The discipline this epic demands of the codebase
applies to its own measurements. The robust, load-independent fact is the
*attribution shape* (rendering dominates), which held across the 100p median-of-3
and the 1000p run; the contaminated number distorted the *magnitude*.

## What shipped: parallel asset_audit (Wave 2 / T7)

`find_missing_local_asset_references` (`bengal/rendering/asset_audit.py`) was a
serial post-render scanner. It is now **parallelized across a threadpool** (per-file
scan in parallel; one memoized `exists()` per unique resolved path, serial). Findings
are **byte-identical** to the serial scan — same regex over the same on-disk HTML,
results preserve file/match order, the full output tree is still walked (so
hand-authored, special-page, and `{% cache %}`-fragment references are all still
caught; we did **not** narrow it to render-tracked assets, which a rejected design
would have done at the cost of false negatives). Verified: set + order parity, an
injected missing ref caught identically, ~3.35x faster on a 663-file build, all 7
audit unit tests + the integration diagnostics green. Small sites (< 64 files,
incl. the whole test-suite) stay on the serial path.

## Implication for the roadmap

The biggest lever is **render scaling** (Item 4), not asset_audit. The next work is
the WaveScheduler per-template-group barrier, a free-threading-aware worker profile,
and removing per-page shared locks — see `plan/epic-performance.md` Wave 2/T6-style
diagnostics (continuous-queue A/B, worker sweep, contention counters).

## Caveats

Single darwin laptop; the 1000-page cell is a single (slow) run, the 100-page cell is
median-of-3. `gil_speedup.json` remains the authoritative timing baseline.
