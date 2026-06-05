<!-- markdownlint-disable MD013 -->

# Clean-box render-scaling results (#343/#344/#345)

This directory holds the committed measurement outputs of the render-scaling epic.
`benchmarks/run_clean_box.sh` writes here. **Prime invariant: only clean-box numbers
(idle, ≥8 physical cores, free-threaded 3.14t, median-of-N) are eligible to become the
*committed ceiling*.** Anything measured under load or on undersized hardware is recorded
only as explicitly-labeled directional evidence, never as the headline.

## ci-2core-directional.json — directional only, NOT the committed ceiling

First Linux run of `probe_render_ceiling.py`, via the `perf-gate.yml` `workflow_dispatch`
`probe` job (run 26966405956, 2026-06-04, branch `lbliii/render-scaling-clean-box`).

**Hardware (from the job's topology step):** AMD EPYC 9V74, **2 cores per socket, 2 threads
per core → 2 physical cores / 4 vCPU**. 500 pages, median-of-3.

| measurement | value |
|---|--:|
| solo single-thread render | 26.89 s |
| in-process threaded render | 13.18 s → **2.04x** thread speedup |
| 2 isolated processes | per-proc 26.75 s (no slowdown) → **2.01x** aggregate |
| 4 isolated processes | per-proc 44.91 s (1.67x slowdown each) → **2.40x** aggregate |

**Verdict: INCONCLUSIVE — the box is too small to answer the question, and that itself is
the finding.** On 2 physical cores, in-process threads already reach ~2.04x, i.e. they are
*already at the physical-core ceiling*. Process isolation reaches only 2.40x (4 procs sharing
2 cores via SMT). The threads-vs-processes gap the probe looks for cannot appear here because
there is no spare parallelism for isolation to recover.

This is **not** evidence of a hardware wall on real hardware. The free-threading coherency tax
is a *many-core* phenomenon: it shows up as in-process threads plateauing *well below* the
available physical-core count (on the 5P+6E dev Mac, threads plateau at ~1.57x while 5 P-cores
sit available — that gap is the tax). Exposing it requires physical cores ≫ the thread plateau,
i.e. the **idle ≥8-physical-core box of #344**. A 2-core shared runner is structurally
incapable of firing either a GO or a NO-GO on the coherency question.

**Conclusion for #344:** the CI `workflow_dispatch` path is validated as a Linux/3.14t harness
smoke test (the probe runs clean end-to-end on Linux), but it is **confirmed insufficient as the
measurement box**. The committed ceiling number still requires the dedicated ≥8-physical-core
brev/cloud box. The contaminated-but-trustworthy local GO (~2.95x processes vs 1.57x threads on
the 5P+6E Mac) remains the only directional signal that the plateau is fixable; the clean-box
run is what turns it into a committed number.
