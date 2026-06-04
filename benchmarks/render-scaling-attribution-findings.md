<!-- markdownlint-disable MD013 -->

# Render-scaling attribution — findings (2026-06-04, M3 Pro, on-Mac)

Measured on the dev Mac (Apple M3 Pro, 5P+6E, Defender present). Where Defender noise matters,
the **process CPU-time** signal is used instead of wall (the coherency tax shows up as *inflated
CPU* — cpu/wall was 4.29 — so CPU-time, measured on our own process via `getrusage`, is robust to
Defender's separate CPU use). These are directional Mac numbers, not committed clean-box baselines.

## What's been established (each verified, not assumed)

1. **The kida `Environment` is per-thread — there is NO shared-Environment floor.**
   Instrumenting `KidaTemplateEngine.render_template` over a live parallel build: 10 render threads →
   11 distinct engine objects, 11 distinct `_env` objects, 0 shared. Rendering goes through
   `run_page` → a thread-local `RenderingPipeline` (`pipeline_runner.py:76`) that calls `create_engine`
   per pipeline; the scheduler's single engine (`scheduler.py:204`) is precompile/scout only. Kida's
   bytecode cache is disk-based (per-engine). **Correction:** the RFC/epic claim of an
   "un-immortalizable Environment floor" capping the ceiling at ~2.5–3.5x is wrong; the realistic
   *thread* ceiling is the process-isolation number (~2.95x here).

2. **The tax is the shared *containers*, not the strings.** A/B at 400 pages, 3 runs, GIL=0:
   interning the hot shared read-set (config + menu + page/section metadata, 1197 strings →
   immortal) changed **render CPU-time by −0.1%** (render wall ±9% was Defender noise). Immortalizing
   strings doesn't help because the dict/list/object *nodes* holding them are still mortal and shared
   — cross-thread reads bump *their* refcounts. **Consequence: saga #346 (`sys.intern`) is ruled out
   as a perf lever — proven, not just suspected.** (Independently reproduces the RFC's earlier hunch.)
   *Caveat:* interning was applied to source strings pre-build; some snapshot-derived strings are
   rebuilt each build. But config/menu/title are the hottest shared reads and the CPU effect was zero.

3. **The `SiteContext`→live-Site proxy is NOT the hot channel.** Instrumenting
   `SiteContext.__getattr__`: only **7 distinct `site.X` attributes** read, ~1–2 per page (the theme
   caches them into `{% let %}` vars once per render). So RFC "Frozen RenderWorld" Phase 1 (re-point
   `SiteContext` off the live Site) targets a *cold* channel. The heavy shared-container reads are
   **config (`ConfigSnapshot`), menus, and the snapshot collections pages iterate** (posts /
   subsections / nav items) — i.e. **per-page** data, which is exactly the maintainer's
   "owned per-page frame / flat schema → hydrate" framing (#347), not the site-level frozen world.

## What this means for the plan

- **Drop #346** as a perf lever (interning is a no-op here).
- **The lever is owning the per-page container read-set** (config values + menu + the collections a
  page renders), so render workers stop dereferencing the shared graph. This is the FrameBuilder /
  owned-per-page-frame (#347). It is **not** capped by an engine floor, so it targets the full
  1.7x → ~2.9x gap.
- **#348 (chrome memoization)** remains separately de-scoped (dead BlockCache + nav active-state is
  per-page; see `348-chrome-memoization-findings.md`).

## Prize sizing — the ceiling probe (decisive, on-Mac, 2026-06-04)

`benchmarks/probe_render_ceiling.py --pages 400 --procs 5,8 --runs 3`, M3 Pro, Defender present.
The probe is contamination-robust: Defender only biases the *process* side **down**, so these are
**lower bounds**.

| | render | speedup |
|---|--:|--:|
| solo single-thread | 10.33s | 1.00x (baseline) |
| in-process threads | 4.56s | **2.26x** (the plateau) |
| 5 isolated processes | — | **3.80x** |
| 8 isolated processes | — | **4.64x** |

**Verdict (the probe's own): FIXABLE coherency tax, not a hardware wall. Ceiling ~4.6x here.**
Corroborated by the direct seq-vs-parallel measurement: parallel render burns **2.48x the CPU**
for identical work (cpu/wall 1.21 sequential → 7.72 parallel — cores busy, not blocked).

**Implications:**
- The prize is **~2x more render throughput** (threads 2.26x → ceiling ~4.6x), much larger than the
  old "2.5–3.5x, Environment-bound" estimate (no Environment floor — see finding 1).
- The null container experiments (strings, global contexts) were the **wrong/small** containers. What
  processes un-share that threads don't is the **`SiteSnapshot` graph** (pages / sections / nav /
  taxonomy), which every page reads — owned by the main thread, so worker threads hit the
  biased-refcount atomic slow path on every access. **That is the FrameBuilder's target.**
- This is all measured **on the Mac, no Linux, no sudo** — the clean-box gate the epic waited on is,
  for the GO/NO-GO + prize-sizing question, answerable here.

## Pinpoint — render reads the LIVE objects, not the snapshot (2026-06-04)

Immortalizing the entire `SiteSnapshot` graph (23,127 objects, via the exported `_Py_SetImmortal`
so read-only frozen objects skip refcounting) and measuring at 8 threads, 400 pages, 3 runs:

| | render | cpu |
|---|--:|--:|
| baseline (shared snapshot) | 4.43s | 30.81s |
| immortalized snapshot graph | 4.13s | 28.48s |
| delta | **+6.8%** | **+7.5%** |

Both metrics agree and it's clearly above the noise floor (strings −0.1%, global-ctx +0.3%) — so it's
real, but **only ~7%**, a small slice of the ~2x prize. *(3 runs; firm up with 6 before quoting a
magnitude.)* The interpretation is the key result:

**The render workers barely read the snapshot — they read the live, mutable `Site` and `Page`.**
`kida.py:774` injects `self.site` (live) into every context; `run_page` passes the live site to the
pipeline; the scheduler renders live `PageLike`, not the frozen `PageSnapshot` (a known note at
`epic-performance.md:44`: "maps snapshot pages back to mutable PageLike and passes self.site into the
pipeline — workers still read mutable Site/Page"). Those live objects are owned by the main thread →
worker threads hit the biased-refcount atomic slow path on every access. The immutable snapshot is
used mostly for nav/scheduling, so immortalizing it only grazes the tax.

**∴ The exact lever:** re-point render workers off the live mutable `Site`/`Page` onto the frozen
snapshot (then the immutable read-set is ownable/immortalizable → full tax removal). This is
`rfc-snapshot-build-plan-handoff` / T13 — and it is precisely the maintainer's "owned per-page frame":
the worker renders from frozen data, never the live graph. That is the build to fund; immortalizing
the frozen read-set is the cheap complement once render reads it.

## Still open — the one definitive step that needs root

`py-spy --native` would name the *exact* contended container (refcount frames under config vs menu
vs snapshot-collection access). It needs `sudo` on macOS. One command:

```bash
sudo py-spy record --native --rate 250 --format raw -o /tmp/coh.txt -- \
  .venv/bin/python /tmp/build_for_profile.py
# then aggregate the folded stacks in /tmp/coh.txt for _Py_INCREF/_Py_DECREF/_Py_atomic frames
# and which Bengal/Kida call sites sit above them.
```

Not a blocker: the owned-per-page-frame prototype's render-CPU + byte-parity measurement validates the
fix directly without it.
