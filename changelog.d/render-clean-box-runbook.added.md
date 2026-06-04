Added `benchmarks/run_clean_box.sh` — a turnkey "measure clean" driver for the render-scaling
epic (#343/#344). On an idle Linux box with free-threaded 3.14t it bootstraps the toolchain,
refuses to run under load (the epic's prime invariant — one load-inflated number was already
retracted), reproduces the GIL=0/GIL=1 plateau, runs the process-isolation ceiling probe, and —
only if the probe says the plateau is a fixable coherency tax — stages the `py-spy --native`
attribution that names the dominant contended object. All results land as committable JSON under
`benchmarks/clean_box_results/` alongside the box's CPU topology and loadavg. No production code change.
