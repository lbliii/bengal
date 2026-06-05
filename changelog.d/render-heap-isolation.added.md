Added an **experimental, opt-in** isolated render backend that renders large
cold builds across separate-heap worker processes (`fork`). It is **off by
default** and gated behind `[build] render_isolation` (`off` | `auto` | `fork`),
with `render_isolation_threshold` (default 400) and `render_isolation_workers`
knobs. Cold CLI/CI builds only — the dev server and incremental builds keep the
in-process thread path, and the backend falls back to threads on any failure, so
it can never break a build. Rendered output is byte-identical to the thread path.
This lands the foundation (transport, partitioning, serial merge, crossover gate,
parity guard, benchmarking) for the heap-isolation epic; note the current
fork-after-parse backend is not yet a guaranteed end-to-end speedup (it can
regress very large builds via copy-on-write), which is why it stays opt-in. See
issue #350.
