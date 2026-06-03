<!-- markdownlint-disable MD013 -->

# Native render profiling runbook (Step 0 of the frozen-render-world RFC)

This is the **hard gate** before funding any of `plan/rfc-frozen-render-world.md`'s migration
phases. The render phase plateaus at ~1.7–1.8x on free-threaded CPython 3.14t with
**cpu/wall ≈ 4.3** — cores are *busy, not blocked* (so it is not lock contention). Parallel burns
~2.6x the CPU for the same logical work. The working hypothesis is free-threading's
**atomic-refcount / cache-coherency traffic** on the shared objects every worker touches per page
(`Site`, `SiteSnapshot`, nav trees, taxonomy tables, caches, the Kida `Environment`, config dicts).

Cheap microbenchmarks could **not** settle which objects dominate (see the RFC's Validation
section). The decisive tool is a **native profile on a supported platform**. macOS arm64 cannot do
`py-spy --native`, so this must run on **Linux**.

## The question this run must answer

> Name the objects/functions whose refcount/coherency traffic dominates cross-thread cost in the
> 8-worker 1000-page build.

The answer routes the decision:

- **Site / snapshot container graph dominates** → owning per-page data (RFC Phases 1–2) is
  justified; proceed.
- **Kida `Environment` / compiled-template objects dominate** → owning per-page data will *not*
  help (shared by construction, no public instance-immortalization API); pivot to a C/Cython
  immortalization spike or process/sub-interpreter isolation.
- **Neither clearly dominates (diffuse coherency/allocator microarch)** → the realistic ceiling is
  near the P-core count regardless; **do not migrate.**

## 0. Environment

```sh
# Free-threaded CPython 3.14t, GIL off. Confirm:
python -c "import sys; print('free-threaded:', not sys._is_gil_enabled())"
# Linux. py-spy with --native, and perf for hardware counters:
pip install py-spy           # or: cargo install py-spy
sudo apt-get install linux-tools-common linux-tools-$(uname -r)   # perf
# perf may need: sudo sysctl kernel.perf_event_paranoid=1   (or -1)
# py-spy --native needs ptrace: run as root or grant CAP_SYS_PTRACE.
```

## 1. Confirm the plateau reproduces on THIS box

The driver `benchmarks/profile_render_native.py` is the build target. First confirm the
signature (parallel cpu/wall > 1 and a real render speedup vs sequential) before profiling —
if the box doesn't reproduce it, the profile is meaningless.

```sh
PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --workers 8
PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --sequential
```

Expect something like (numbers vary by box): parallel `cpu/wall≈3–4`, `render_phase` ~2–3x lower
than sequential, while parallel `cpu` is ~2–2.6x the sequential `cpu` for identical work. That CPU
inflation with cores busy is the thing to explain.

## 2. Native sampling profile (py-spy --native)

Pre-generate the site so site-gen is out of the profile, then sample the build with native frames:

```sh
SITE=/tmp/bengal_profile_site
PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir "$SITE"  # generates + warms

# Flamegraph (SVG) + speedscope (interactive) with C frames included:
PYTHON_GIL=0 py-spy record --native --rate 1000 --format speedscope \
  -o render_native.speedscope.json -- \
  python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir "$SITE"

PYTHON_GIL=0 py-spy record --native --rate 1000 -o render_native.svg -- \
  python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir "$SITE"
```

**What to look for** (the refcount/coherency signature):

- Native frames dominated by reference-count machinery: `_Py_DECREF` / `_Py_MergeZeroLocalRefcount`,
  `_Py_Dealloc`, `_PyObject_GC_*`, `_PyCriticalSection*`, `_PyMutex_LockSlow`, biased-refcount
  paths (`_Py_TryIncrefFast`, `_PyObject_SetMaybeWeakref`), and time in the allocator
  (`_PyObject_Malloc`/`mi_*` if mimalloc). A large share here = coherency tax, not Python-level work.
- Walk *up* from those native frames to the Python frames that trigger them, and note **which
  objects** they touch: Site attribute access, `SiteSnapshot`/section graph traversal, the Kida
  `Environment` / template globals, config dict reads, taxonomy/menu tables, caches.
- Aggregate by the *owning object* of the hot dereferences. That aggregation is the answer to the
  question above.

## 3. Hardware-counter confirmation (perf)

Sampling shows *where*; `perf stat` confirms the *mechanism* (cross-core coherency = cache-line
bouncing shows up as last-level-cache / coherency misses that scale with worker count):

```sh
# Parallel vs sequential, same work — compare LLC + coherency-related counters per page.
PYTHON_GIL=0 perf stat -e task-clock,context-switches,cache-references,cache-misses,LLC-loads,LLC-load-misses \
  python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir "$SITE"
PYTHON_GIL=0 perf stat -e task-clock,context-switches,cache-references,cache-misses,LLC-loads,LLC-load-misses \
  python benchmarks/profile_render_native.py --pages 1000 --sequential --reuse-dir "$SITE"

# Hot functions across all threads (kernel + user), then annotate the top refcount/alloc symbols:
PYTHON_GIL=0 perf record -g --call-graph dwarf -- \
  python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir "$SITE"
perf report --stdio | head -80
```

If parallel shows **super-linear growth in LLC-load-misses / cache-misses per page** vs sequential
while task-clock inflates ~2.6x, that corroborates coherency traffic (atomic refcount line bouncing)
as the mechanism — distinct from lock contention (which `perf` would show as context-switches /
futex time, and which we already ruled out via cpu/wall≈4.3).

## 4. (Optional) Refcount-attribution probe

To attribute refcount churn to *specific* objects without reading native stacks, a CPython
**debug build** (`--with-pydebug`) exposes `sys.gettotalrefcount()`; sample it around a fixed render
batch with 1 vs 8 workers and diff. Or instrument the suspected shared roots: wrap the hot Site /
snapshot / Environment dereferences and count accesses per page per worker. High per-worker access
counts on a shared object = a coherency hotspot candidate. (This is a fallback; the native profile
in §2 is the primary evidence.)

## Recording the result

Write the findings back into `plan/rfc-frozen-render-world.md` under "The hard gate: Step 0":
the named dominant objects, the perf-counter deltas, and which of the three decision branches the
evidence selects. Attach `render_native.speedscope.json` / `render_native.svg` / `perf report` output
as artifacts. Only then is the RFC eligible to move from **Hold** to a funded single-step PoC.
