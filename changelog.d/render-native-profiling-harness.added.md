Added `benchmarks/profile_render_native.py` and `benchmarks/PROFILE_RENDER_NATIVE.md` — a
deterministic single-build driver and runbook for native profiling of the free-threaded render
plateau (Step 0 gate of `plan/rfc-frozen-render-world.md`). The driver pins worker count, prints
the cpu/wall signature + render-phase time so the plateau is confirmable on any box, and is meant
to be wrapped by `py-spy --native` / `perf` on Linux to name the objects whose refcount/coherency
traffic dominates the 8-worker build. No production code change.
