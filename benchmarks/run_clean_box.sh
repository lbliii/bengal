#!/usr/bin/env bash
# Turnkey "measure clean" driver for the render-scaling epic (#343).
#
# Runs the WHOLE gated sequence of #344/#345 in one shot on an idle Linux box,
# dropping every result as committable JSON under benchmarks/clean_box_results/.
# It exists so the clean-box window is ~1 hour of unattended runtime, not an
# hour of re-deriving commands from COHERENCY_PROFILING.md.
#
# WHERE TO RUN THIS (the whole point of #344):
#   An IDLE Linux box with >=8 PHYSICAL cores and free-threaded CPython 3.14t.
#   NOT this dev Mac (Microsoft Defender real-time-scans every file write,
#   ~128% CPU, and there is no perf / py-spy --native). An ephemeral cloud CPU
#   instance (e.g. `brev create ... --cpu`) or a bare-metal Linux host works.
#
# PRIME INVARIANT (this epic already retracted one load-inflated number):
#   NEVER commit a magnitude measured under load. This script refuses to run if
#   the 1-minute load average is already high, and records loadavg/topology
#   alongside every number so the reader can judge cleanliness.
#
# Usage:
#   bash benchmarks/run_clean_box.sh                 # full sequence, defaults
#   PAGES=500 PROCS=2,4,8 RUNS=3 bash benchmarks/run_clean_box.sh
#   SKIP_ATTRIBUTION=1 bash benchmarks/run_clean_box.sh   # steps 1 only, no py-spy/perf
set -euo pipefail

PAGES="${PAGES:-500}"
PROCS="${PROCS:-2,4,8}"
RUNS="${RUNS:-3}"
GIL_SCALES="${GIL_SCALES:-100,1000}"
SKIP_ATTRIBUTION="${SKIP_ATTRIBUTION:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
OUT="benchmarks/clean_box_results"
mkdir -p "$OUT"

say() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mABORT: %s\033[0m\n' "$*" >&2; exit 1; }

say "0. Environment + cleanliness gate"
uname -a | tee "$OUT/env_uname.txt"
if command -v nproc >/dev/null; then nproc | tee "$OUT/env_nproc.txt"; fi
if command -v lscpu >/dev/null; then lscpu | tee "$OUT/env_lscpu.txt"; fi

# Idle gate: refuse to measure under load. 1-min loadavg should be well under
# the core count on an idle box. Override with FORCE_LOADED=1 only if you know
# the loadavg is stale (fresh box) — never to push past real contention.
if [ -r /proc/loadavg ]; then
  cat /proc/loadavg | tee "$OUT/env_loadavg.txt"
  LOAD1="$(cut -d' ' -f1 /proc/loadavg)"
  CORES="$(nproc 2>/dev/null || echo 8)"
  # bash has no float compare; scale by 100 and use integer math.
  LOAD_X100="$(printf '%.0f' "$(echo "$LOAD1 * 100" | bc 2>/dev/null || echo "${LOAD1%.*}00")")"
  THRESH_X100="$(( CORES * 50 ))"   # loadavg > 0.5*cores => too busy to trust
  if [ "${FORCE_LOADED:-0}" != "1" ] && [ "$LOAD_X100" -gt "$THRESH_X100" ]; then
    die "1-min loadavg $LOAD1 is high for $CORES cores — box is not idle. Wait, or set FORCE_LOADED=1 if loadavg is stale on a fresh box."
  fi
fi

say "1. Toolchain (uv + free-threaded 3.14t)"
command -v uv >/dev/null || die "uv not installed. See benchmarks/COHERENCY_PROFILING.md."
uv python install 3.14t
uv sync --no-sources --group dev
uv run python -c "import sys; assert not sys._is_gil_enabled(), 'GIL is ON — install/select 3.14t'; print('OK: free-threaded, GIL disabled')"

say "2. #344 acceptance — reproduce the GIL=0 vs GIL=1 plateau (gil_speedup sweep)"
# Open Question 5: confirm the darwin-measured ~1.9x shape holds on this hardware.
uv run python benchmarks/benchmark_gil_speedup.py \
  --scales "$GIL_SCALES" --archetypes blog --runs "$RUNS" \
  --output "$OUT/gil_speedup.json" 2>&1 | tee "$OUT/gil_speedup.log"

say "3. #345 step 1 — process-isolation ceiling probe (fixable tax vs hardware ceiling)"
uv run python benchmarks/probe_render_ceiling.py \
  --pages "$PAGES" --procs "$PROCS" --runs "$RUNS" \
  --json-out "$OUT/probe_render_ceiling.json" 2>&1 | tee "$OUT/probe_render_ceiling.log"

# Parse the verdict to decide whether step 2 (attribution) is even warranted.
FIXABLE="$(uv run python -c "
import json
r = json.load(open('$OUT/probe_render_ceiling.json'))
thr = r['in_process_thread_speedup']
best = max(r['process_isolation'].values(), key=lambda d: d['process_speedup'])
print('1' if best['process_speedup'] >= thr * 1.6 else '0')
")"

if [ "$FIXABLE" != "1" ]; then
  say "VERDICT: processes did NOT beat threads by 1.6x — looks HARDWARE-bound."
  echo "Per #345: do not migrate render; close #343 with this evidence (still publishable, #349)."
  echo "Skipping attribution (no contended object to name)."
  exit 0
fi

say "VERDICT: process isolation >> threads — coherency tax looks FIXABLE."
if [ "$SKIP_ATTRIBUTION" = "1" ]; then
  echo "SKIP_ATTRIBUTION=1 set — stopping after step 1. Run step 2 manually per COHERENCY_PROFILING.md."
  exit 0
fi

say "4. #345 step 2 — attribution: NAME the dominant contended object"
# This is the architecture-deciding fork. See COHERENCY_PROFILING.md steps 3-5.
sudo sysctl kernel.perf_event_paranoid=1 2>/dev/null || \
  echo "WARN: could not lower perf_event_paranoid — perf counters may be unavailable."
uv pip install py-spy 2>/dev/null || uv run pip install py-spy || \
  echo "WARN: py-spy install failed; do the native flamegraph manually."

# 8-worker 1000-page build under a native flamegraph: look for refcount/GC
# native frames (_Py_INCREF/_Py_DECREF, _Py_atomic_*) sitting under template
# rendering + shared-object attribute access, NOT under markdown parsing.
PYTHON_GIL=0 uv run py-spy record --native --rate 250 --output "$OUT/coherency.svg" -- \
  uv run python -c "
from pathlib import Path; import tempfile
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
import sys; sys.path.insert(0, 'benchmarks')
from benchmarks.benchmark_gil_speedup import create_site
d = Path(tempfile.mkdtemp()); create_site('blog', 1000, d)
Site.from_config(d).build(BuildOptions(force_sequential=False, incremental=False, quiet=True))
" 2>&1 | tee "$OUT/pyspy.log" || echo "WARN: py-spy record failed — see $OUT/pyspy.log"

say "DONE. Results in $OUT/ — commit them (clean-box only) and record the branch decision on #345."
echo "Fork (COHERENCY_PROFILING.md 'From evidence to task'):"
echo "  Site/snapshot graph dominates  -> fund #347 owned-frames-in-threads (UNIVERSAL win)."
echo "  kida Environment dominates     -> heap isolation only (#347 cold-build/CI), gated on crossover."
echo "  neither dominates              -> bank #346 (sys.intern) + #348 (chrome memo) only."
