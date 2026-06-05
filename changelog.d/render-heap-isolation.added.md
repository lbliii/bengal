Large cold builds can now render across separate-heap worker processes via a new
isolated render backend, recovering the in-process→separate-heap throughput gap
that free-threaded threads plateau below. Opt in with `[build] render_isolation`
(`off` default, or `auto`/`fork`), tune the page-count crossover with
`render_isolation_threshold` (default 400) and the worker count with
`render_isolation_workers`. Cold CLI/CI builds only — the dev server and
incremental builds keep the in-process thread path, and the backend falls back to
threads on any failure so it can never break a build. Output is byte-identical to
the thread path. See issue #350.
