Added `benchmarks/probe_render_ceiling.py` — a process-isolation render *ceiling* probe that
answers the prerequisite question of the render-scaling epic (#343/#345) on any box, macOS
included: is the ~1.7x in-process free-threading plateau a fixable cross-thread coherency tax
or a hardware ceiling? It runs K single-threaded render builds concurrently as separate
processes (each with its own heap → zero cross-process refcount coherency) and compares
aggregate throughput to the in-process thread pool. If processes scale ~K toward the P-core
count while threads stay ~1.7x, the gap is pure coherency tax and software un-sharing can
recover it; if processes also plateau, the ceiling is hardware-bound. Must be run on an idle,
free-threaded (3.14t) box, median-of-N. No production code change.
