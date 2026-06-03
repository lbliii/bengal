<!-- markdownlint-disable MD013 -->

# Runbook: Profiling the Free-Threading Coherency Tax

**Status**: Active runbook · **Owner**: perf epic (`plan/epic-performance.md`, T4-scaling → T13/T14)
**Created**: 2026-06-03

This is the concrete measurement plan for the epic's diagnosed-but-not-yet-attributed
bottleneck. It exists so the next render-scaling investigation starts from commands, not
from re-deriving the theory.

## The hypothesis (already diagnosed, not yet attributed to objects)

From `epic-performance.md` ("The real ceiling — DIAGNOSED 2026-06-02"):

| | wall | CPU-time | cpu/wall |
|---|--:|--:|--:|
| sequential (1 core) | 63.6s | 59.2s | 0.93 |
| 8 workers | 35.6s | **152.9s** | **4.29** |

`cpu/wall = 4.29` ⇒ cores are **busy, not blocked**, so the ~1.7x plateau is **not** Python
lock contention (FIX C was correctly abandoned). Parallel render burns **2.6x the CPU for
the same 1000-page work**, scaling **per-page, not per-worker** — the signature of
free-threading's **atomic-refcount / cache-coherency tax** on shared objects (`Site`,
`SiteSnapshot`, nav trees, caches, config) that every worker touches on every page.

**What's still unknown — and what this runbook resolves:** *which specific shared objects*
generate the cross-core refcount traffic. Naming them is the prerequisite for T13 (frozen
per-worker views) and decides whether immortalizing hot immutables is enough or a
snapshot-handoff is required.

## Environment: why NOT Docker-on-Mac, and what to use instead

This diagnosis is microarchitectural (cross-core cache-line bouncing on atomic refcounts).
The measurement environment must expose real hardware behavior:

- **Docker Desktop on macOS is unsuitable.** It runs in a Linux VM that virtualizes CPU
  topology (hiding the P/E asymmetry the worker analysis depends on) and does **not** pass
  through the PMU — so `perf` hardware counters, the one tool that can *prove* the coherency
  hypothesis, are unavailable or inaccurate. A VM-on-a-laptop is strictly worse than the bare
  laptop for wall-time too.
- **macOS bare metal is partial.** `py-spy --native` works but interpreter/extension
  symbolication fights SIP, and there is no accessible equivalent of Linux `perf stat`
  hardware counters.
- **Use a real Linux box** — a dedicated cloud CPU instance (the `brev-cli` skill can spin one
  up) or a bare-metal Linux host. Requirements: ≥8 physical cores, free-threaded CPython
  3.14t, root or `perf_event_paranoid` lowered for counter access, and an **idle** machine
  (no co-tenant noise — the epic already has one load-contaminated number it had to retract).

```bash
# One-time setup on the Linux box
uv python install 3.14t
uv sync --no-sources --group dev
sudo sysctl kernel.perf_event_paranoid=1   # allow user-space perf counter reads
python -c "import sysconfig; assert sysconfig.get_config_var('Py_GIL_DISABLED'); print('OK: free-threaded')"
```

## Step 1 — Confirm the plateau reproduces on Linux

Before profiling, verify the macOS-measured shape holds on this hardware (Open Question 5:
nothing in the epic is yet confirmed off a single darwin laptop).

```bash
# Full GIL=0 vs GIL=1 sweep — does the 1000-page free-threading ratio land near 1.94x here?
uv run python benchmarks/benchmark_gil_speedup.py --scales 100,1000 --archetypes blog --runs 3
```

Record the 1000-page GIL=0 wall, GIL=1 wall, and the ratio. If the ratio is materially
different on Linux, that itself is a finding worth committing before any optimization.

## Step 2 — cpu/wall, to re-confirm "busy not blocked" on this box

```bash
# Sequential
PYTHON_GIL=0 /usr/bin/time -v uv run python -c "
from pathlib import Path; import tempfile
from bengal.core.site import Site; from bengal.core.build_options import BuildOptions
from benchmarks.benchmark_gil_speedup import create_site
d=Path(tempfile.mkdtemp()); create_site('blog',1000,d)
s=Site.from_config(d); s.build(BuildOptions(force_sequential=True, incremental=False, quiet=True))
"
# 8 workers: same, force_sequential=False. Compare 'User time'+'System time' vs 'Elapsed'.
```

A cpu/wall well above 1 at N workers confirms busy cores. If it has *dropped* toward 1 on
Linux, the bottleneck moved (e.g. to a real lock) and the strategy below changes — recheck
before proceeding.

## Step 3 — py-spy --native: where the busy CPU actually goes

```bash
uv pip install py-spy
# Record a native+python flamegraph of an 8-worker 1000-page build.
PYTHON_GIL=0 py-spy record --native --rate 250 --output coherency.svg -- \
  uv run python -c "
from pathlib import Path; import tempfile
from bengal.core.site import Site; from bengal.core.build_options import BuildOptions
from benchmarks.benchmark_gil_speedup import create_site
d=Path(tempfile.mkdtemp()); create_site('blog',1000,d)
Site.from_config(d).build(BuildOptions(force_sequential=False, incremental=False, quiet=True))
"
```

**What to look for** (the tell that distinguishes coherency tax from ordinary CPU):
disproportionate native time in CPython refcount/GC machinery —
`_Py_DECREF` / `_Py_INCREF`, `_PyObject_GC_*`, `_Py_atomic_*`, and (under contention)
mutex/`pthread` frames around shared structures. If the heavy native frames sit under
template rendering and shared-object attribute access rather than under markdown parsing,
that corroborates the refcount-traffic hypothesis.

## Step 4 — `perf` hardware counters: prove cache-coherency, not just CPU

This is the step Docker-on-Mac cannot do, and the one that turns "we think it's coherency"
into evidence.

```bash
# Compare sequential vs 8-worker for the SAME work. The coherency signature is that
# cache-misses / LLC-load-misses / (on supported CPUs) HITM events scale with worker count
# while instructions-retired stays ~flat per page.
for mode in seq par; do
  fs=$([ $mode = seq ] && echo True || echo False)
  PYTHON_GIL=0 perf stat -e instructions,cache-references,cache-misses,LLC-load-misses \
    uv run python -c "
from pathlib import Path; import tempfile
from bengal.core.site import Site; from bengal.core.build_options import BuildOptions
from benchmarks.benchmark_gil_speedup import create_site
d=Path(tempfile.mkdtemp()); create_site('blog',1000,d)
Site.from_config(d).build(BuildOptions(force_sequential=$fs, incremental=False, quiet=True))
" 2>&1 | tee perf-$mode.txt
done
# On Intel with c2c support, this directly names the contended cache lines:
# sudo perf c2c record -- <build>; sudo perf c2c report
```

**Decision signal:** if `cache-misses` and `LLC-load-misses` rise ~linearly with worker count
while `instructions` per page is flat, the plateau is memory-coherency-bound — the architectural
path (T13/immortalization) is justified. If instructions-per-page *rise* with workers instead,
something is doing redundant per-worker work and the fix is algorithmic, not coherency.

## Step 5 — Name the objects (refcount probe)

`perf`/py-spy localize the *cost*; this localizes the *objects*. On a debug or
`--with-pydebug`-ish build, or via `sys.getrefcount` sampling, snapshot the refcounts of the
prime suspects across a parallel build and see which climb fastest under fan-out:

```bash
# Suspects to instrument (per epic): the Site, the active SiteSnapshot, the nav/menu tree,
# the BlockCache, and the loaded config object. Sample getrefcount before/after the render
# phase at 1 vs 8 workers; the objects whose refcount churn scales with workers are the
# cross-thread hot set that T13's per-worker frozen view must stop sharing.
```

## From evidence to task

| Finding | Implies |
|---|---|
| Refcount/GC native frames dominate; misses scale with workers; a few objects own the churn | **T13** — route those objects through a frozen per-worker `BuildPlan`/`PagePlan` (`rfc-snapshot-build-plan-handoff`); and/or **immortalize** the hot read-only immutables so their refcounts aren't atomically bumped |
| Instructions-per-page rise with workers | Algorithmic redundancy per worker — fix that first; coherency work is premature |
| cpu/wall collapsed toward 1 on Linux | A real stall/lock reappeared — re-profile; FIX C may be back on the table on this hardware |

Every change ships with the byte-parity fixtures (builds are now byte-reproducible run-to-run
and across worker counts) and is judged against the committed CI baseline (`ci_gate.json`,
once bootstrapped via `.github/workflows/perf-gate.yml`). Per the epic's prime invariant: **no
magnitude is committed without a clean baseline on the hardware it was measured on.**
