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
