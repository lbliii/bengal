#!/usr/bin/env python3
"""
Free-Threading Speedup Benchmark: PYTHON_GIL=0 vs PYTHON_GIL=1
=============================================================

Proves Bengal's north-star "blazing fast at scale" claim by isolating ONLY the
free-threading variable. The SAME free-threaded CPython 3.14t interpreter builds
the SAME fixture sites twice:

    - once with env PYTHON_GIL=0  (GIL disabled — true free-threading)
    - once with env PYTHON_GIL=1  (GIL re-enabled on the same build)

Because ``PYTHON_GIL`` is read at interpreter start-up, each build runs in a
fresh subprocess of *this* interpreter. The worker asserts
``sys._is_gil_enabled()`` matches the requested mode before timing anything, so a
mislabeled run can never pollute the table.

For each (scale x archetype) cell we record total wall time plus the full
``BuildStats`` phase ledger — the named ``phase_timings_ms`` entries (Discovery,
Parsing, Snapshot, Content, Rendering, Assets, Post-process, Cache save, Stats,
Health check), the ``post_render_timings_ms`` finalization timings (asset_audit
lives here), and the output-format generation breakdown — take the median of N
runs, and emit a speedup ratio (GIL=1 time / GIL=0 time). A ratio > 1.0 means
free-threading is faster. ``unattributed_s`` reports any wall not covered by the
ledger so the accounting can be audited.

Usage:
    # Quick A/B (100, 1000 pages; blog + docs)
    python benchmarks/benchmark_gil_speedup.py

    # Full ladder (100, 1000, 10000) x (blog, docs, autodoc)
    python benchmarks/benchmark_gil_speedup.py --full

    # Single cell
    python benchmarks/benchmark_gil_speedup.py --pages 1000 --archetype docs

    # Publish committed JSON baseline + markdown report
    python benchmarks/benchmark_gil_speedup.py --full --publish

Methodology:
    - In-process ``Site.build`` (no CLI overhead) inside a subprocess per mode.
    - Cold builds: fresh temp site generated per run, output wiped.
    - Median of N>=3 runs (resistant to outliers).
    - The interpreter is asserted to be a free-threaded build; PYTHON_GIL=1
      re-enables the GIL on that same build for the comparison arm.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent

# Reuse the committed results manager for timestamped JSON + latest.json.
sys.path.insert(0, str(REPO_ROOT / "tests" / "performance"))
from results_manager import BenchmarkResults  # noqa: E402

BASELINE_DIR = REPO_ROOT / "benchmarks" / "baselines"

# ---------------------------------------------------------------------------
# Content archetypes
# ---------------------------------------------------------------------------
# Each archetype generates a different *workload shape* so the speedup table
# reflects how free-threading helps each kind of site:
#   blog    — many small posts with tags (taxonomy-heavy fan-out)
#   docs    — nested sections, headings, code blocks, TOC + cross-links
#   autodoc — large API-reference-style pages (render-heavy per page)

PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat "
    "nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui "
    "officia deserunt mollit anim id est laborum.",
    "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque "
    "laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi "
    "architecto beatae vitae dicta sunt explicabo.",
    "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia "
    "consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.",
]

TAG_POOL = [
    "python",
    "javascript",
    "tutorial",
    "guide",
    "tips",
    "howto",
    "web",
    "api",
    "database",
    "devops",
    "frontend",
    "backend",
    "react",
    "django",
    "docker",
]

CODE_BLOCK = """```python
def handler(request, response):
    payload = request.json()
    return response.ok({"id": payload["id"], "status": "created"})
```"""


def _config(title: str, *, taxonomies: bool) -> str:
    return (
        f'title = "{title}"\n'
        'baseurl = "https://example.com"\n'
        "\n"
        "[build]\n"
        'theme = "default"\n'
        "parallel = true\n"
        "minify_assets = false\n"
        "optimize_assets = false\n"
        "fingerprint_assets = false\n"
        f"generate_sitemap = {'true' if taxonomies else 'false'}\n"
        f"generate_rss = {'true' if taxonomies else 'false'}\n"
    )


def _gen_blog(index: int) -> str:
    tags = random.sample(TAG_POOL, k=random.randint(2, 4))
    body = "\n\n".join(random.sample(PARAGRAPHS, 2))
    return (
        f"---\ntitle: Blog Post {index}\n"
        f"date: 2025-{(index % 12) + 1:02d}-{(index % 28) + 1:02d}\n"
        f"tags: {tags}\n---\n\n"
        f"# Blog Post {index}\n\n{body}\n\n"
        f"Related: [more posts](/tags/{tags[0]}).\n"
    )


def _gen_docs(index: int) -> str:
    body = "\n\n".join(random.sample(PARAGRAPHS, 3))
    return (
        f"---\ntitle: Guide {index}\n---\n\n"
        f"# Guide {index}\n\n## Overview\n\n{body}\n\n"
        f"## Example\n\n{CODE_BLOCK}\n\n"
        f"### Details\n\nSome *important* notes with `inline code` and "
        f"[a cross-link](/docs/guide-{(index + 1):05d}/).\n\n"
        f"## Conclusion\n\nWrap-up for guide {index}.\n"
    )


def _gen_autodoc(index: int) -> str:
    # Large, render-heavy "API reference" page: many headings + code blocks.
    sections = [
        (
            f"### `module{index}.func{sym}(arg)`\n\n"
            f"{random.choice(PARAGRAPHS)}\n\n{CODE_BLOCK}\n\n"
            f"**Parameters:** `arg` — the input value.\n\n"
            f"**Returns:** a result object.\n"
        )
        for sym in range(8)
    ]
    return f"---\ntitle: API module{index}\n---\n\n# module{index}\n\n## Reference\n\n" + "\n".join(
        sections
    )


ARCHETYPES = {
    "blog": (_gen_blog, True),
    "docs": (_gen_docs, False),
    "autodoc": (_gen_autodoc, False),
}


def create_site(archetype: str, num_pages: int, root: Path) -> Path:
    """Generate a fixture site of ``num_pages`` for ``archetype`` under ``root``."""
    gen, taxonomies = ARCHETYPES[archetype]
    content = root / "content"
    content.mkdir(parents=True)
    (root / "public").mkdir(exist_ok=True)

    (content / "index.md").write_text(f"---\ntitle: Home\n---\n\n{gen(0)}\n")
    # Docs gets a nested section to exercise section trees.
    nested = content / "docs"
    if archetype == "docs":
        nested.mkdir()
        nested.joinpath("_index.md").write_text("---\ntitle: Docs\n---\n\nDocs section.\n")

    for i in range(1, num_pages):
        target = nested if archetype == "docs" else content
        prefix = "guide" if archetype == "docs" else "page"
        target.joinpath(f"{prefix}-{i:05d}.md").write_text(gen(i))

    (root / "bengal.toml").write_text(_config(f"{archetype} bench", taxonomies=taxonomies))
    return root


# ---------------------------------------------------------------------------
# Worker (runs inside the subprocess with PYTHON_GIL already applied)
# ---------------------------------------------------------------------------


def _run_worker(archetype: str, num_pages: int, runs: int, expect_gil: bool) -> int:
    """Build the fixture ``runs`` times in-process and print JSON to stdout.

    PYTHON_GIL is already baked into this interpreter. We assert the requested
    mode matches reality before timing so a mislabeled environment can never
    silently corrupt the comparison table.
    """
    # Import here so import time is not counted and so an interpreter that is not
    # free-threaded fails loudly rather than producing a bogus row.
    actual_gil = sys._is_gil_enabled()
    if actual_gil is not expect_gil:
        print(
            json.dumps(
                {
                    "error": (
                        f"GIL mismatch: expected _is_gil_enabled()=={expect_gil} "
                        f"(PYTHON_GIL={os.environ.get('PYTHON_GIL')!r}), "
                        f"got {actual_gil}"
                    )
                }
            )
        )
        return 2

    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    random.seed(42)  # identical content across modes/runs
    samples: list[dict[str, float]] = []

    for _ in range(runs):
        tmp = Path(tempfile.mkdtemp(prefix=f"gil_{archetype}_"))
        try:
            create_site(archetype, num_pages, tmp)
            site = Site.from_config(tmp)
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)
            site.output_dir.mkdir(parents=True)

            start = time.perf_counter()
            stats = site.build(
                BuildOptions(force_sequential=False, incremental=False, verbose=False, quiet=True)
            )
            wall = time.perf_counter() - start

            sd = stats.to_dict() if hasattr(stats, "to_dict") else {}
            sample: dict[str, float] = {
                # Original keys (kept verbatim for committed-baseline continuity).
                "wall_s": wall,
                "build_time_s": float(sd.get("build_time_ms", wall * 1000)) / 1000.0,
                "discovery_s": float(sd.get("discovery_time_ms", 0)) / 1000.0,
                "taxonomy_s": float(sd.get("taxonomy_time_ms", 0)) / 1000.0,
                "rendering_s": float(sd.get("rendering_time_ms", 0)) / 1000.0,
                "assets_s": float(sd.get("assets_time_ms", 0)) / 1000.0,
                "postprocess_s": float(sd.get("postprocess_time_ms", 0)) / 1000.0,
                "total_pages": int(sd.get("total_pages", num_pages)),
                # Named scalar phases previously dropped on the floor by this harness.
                "fonts_s": float(sd.get("fonts_time_ms", 0)) / 1000.0,
                "menu_s": float(sd.get("menu_time_ms", 0)) / 1000.0,
                "related_posts_s": float(sd.get("related_posts_time_ms", 0)) / 1000.0,
                "health_check_s": float(sd.get("health_check_time_ms", 0)) / 1000.0,
            }
            # Authoritative named-phase ledger recorded by BuildStats.record_phase_timing
            # (Discovery / Parsing / Snapshot / Content / Rendering / Assets / Post-process /
            # Cache save / Stats / Health check ...). This is what makes the ~31s that the
            # five-field extraction missed attributable.
            phase_ledger = sd.get("phase_timings_ms") or {}
            for name, ms in phase_ledger.items():
                sample[f"phase.{name}_s"] = float(ms) / 1000.0
            # Post-render finalization timings — asset_audit lives HERE, outside the phases.
            for name, ms in (sd.get("post_render_timings_ms") or {}).items():
                sample[f"post_render.{name}_s"] = float(ms) / 1000.0
            # Output-format generation breakdown (page_markdown / page_llm_txt, inside post-process).
            for name, ms in (sd.get("postprocess_output_timings_ms") or {}).items():
                sample[f"ppoutput.{name}_s"] = float(ms) / 1000.0
            # Ledger total and the residual wall not attributed to any ledger entry.
            ledger_total_s = sum(float(v) for v in phase_ledger.values()) / 1000.0
            sample["phase_ledger_total_s"] = ledger_total_s
            sample["unattributed_s"] = max(0.0, sample["build_time_s"] - ledger_total_s)
            samples.append(sample)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(
        json.dumps(
            {
                "archetype": archetype,
                "pages": num_pages,
                "gil_enabled": actual_gil,
                "samples": samples,
            }
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    archetype: str
    pages: int
    gil0: dict[str, float] = field(default_factory=dict)  # median phase times, GIL off
    gil1: dict[str, float] = field(default_factory=dict)  # median phase times, GIL on
    error: str | None = None

    @property
    def speedup(self) -> float | None:
        """GIL=1 wall / GIL=0 wall — >1 means free-threading is faster."""
        a = self.gil1.get("wall_s")
        b = self.gil0.get("wall_s")
        if a and b and b > 0:
            return a / b
        return None

    def pages_per_sec(self, mode: str) -> float | None:
        d = self.gil0 if mode == "gil0" else self.gil1
        w = d.get("wall_s")
        return (self.pages / w) if w and w > 0 else None


def _median_phases(samples: list[dict[str, float]]) -> dict[str, float]:
    """Median every numeric key present across samples.

    The original harness medianed only a fixed five-phase list, which silently
    dropped the parsing/snapshot/content/post-render attribution that BuildStats
    already records. Medianing the union of keys surfaces the full ledger
    (``phase.*``, ``post_render.*``, ``ppoutput.*``, ``unattributed_s``) while
    preserving the original keys verbatim for baseline continuity.
    """
    keys: set[str] = set()
    for s in samples:
        keys.update(s.keys())
    out: dict[str, float] = {}
    for k in sorted(keys):
        vals = [s[k] for s in samples if isinstance(s.get(k), (int, float))]
        if vals:
            out[k] = median(vals)
    return out


def _run_subprocess_mode(
    archetype: str, num_pages: int, runs: int, gil_on: bool
) -> tuple[dict[str, float], str | None]:
    """Launch this same interpreter as a worker with the requested GIL mode."""
    env = {**os.environ, "PYTHON_GIL": "1" if gil_on else "0"}
    cmd = [
        sys.executable,
        os.path.abspath(__file__),
        "--worker",
        "--archetype",
        archetype,
        "--pages",
        str(num_pages),
        "--runs",
        str(runs),
        "--expect-gil",
        "1" if gil_on else "0",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=1800)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-400:]
        return {}, f"exit {proc.returncode}: {tail}"
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return {}, f"bad worker output: {exc}: {proc.stdout[-200:]}"
    if "error" in payload:
        return {}, payload["error"]
    return _median_phases(payload["samples"]), None


def run_cell(archetype: str, num_pages: int, runs: int) -> CellResult:
    print(f"  [{archetype} x {num_pages:,}]")
    cell = CellResult(archetype=archetype, pages=num_pages)

    gil0, err0 = _run_subprocess_mode(archetype, num_pages, runs, gil_on=False)
    if err0:
        cell.error = f"GIL=0 {err0}"
        print(f"    GIL=0: ERROR {err0[:120]}")
        return cell
    cell.gil0 = gil0
    print(f"    GIL=0 (free-threaded): {gil0['wall_s']:.3f}s")

    gil1, err1 = _run_subprocess_mode(archetype, num_pages, runs, gil_on=True)
    if err1:
        cell.error = f"GIL=1 {err1}"
        print(f"    GIL=1: ERROR {err1[:120]}")
        return cell
    cell.gil1 = gil1
    print(f"    GIL=1 (GIL re-enabled): {gil1['wall_s']:.3f}s")

    sp = cell.speedup
    if sp:
        print(f"    -> speedup: {sp:.2f}x")
    return cell


# ---------------------------------------------------------------------------
# Reporting / publishing
# ---------------------------------------------------------------------------


def print_table(cells: list[CellResult]) -> None:
    print()
    print("=" * 78)
    print("FREE-THREADING SPEEDUP  (PYTHON_GIL=1 wall / PYTHON_GIL=0 wall)")
    print("=" * 78)
    print(f"  {'Archetype':<10} {'Pages':>8} {'GIL=0 s':>10} {'GIL=1 s':>10} {'Speedup':>9}")
    print("-" * 78)
    for c in sorted(cells, key=lambda x: (x.archetype, x.pages)):
        if c.error:
            print(f"  {c.archetype:<10} {c.pages:>8,} {'ERR':>10} {'ERR':>10} {'—':>9}")
            continue
        sp = c.speedup
        print(
            f"  {c.archetype:<10} {c.pages:>8,} "
            f"{c.gil0['wall_s']:>10.3f} {c.gil1['wall_s']:>10.3f} "
            f"{(f'{sp:.2f}x' if sp else '—'):>9}"
        )
    print()


def to_payload(cells: list[CellResult]) -> dict:
    return {
        "methodology": (
            "Same free-threaded CPython 3.14t interpreter; each build runs in a "
            "subprocess with PYTHON_GIL=0 vs PYTHON_GIL=1; in-process Site.build; "
            "cold build; median of N runs; worker asserts sys._is_gil_enabled()."
        ),
        "cells": [
            {
                "archetype": c.archetype,
                "pages": c.pages,
                "error": c.error,
                "speedup": c.speedup,
                "gil0_wall_s": c.gil0.get("wall_s"),
                "gil1_wall_s": c.gil1.get("wall_s"),
                "gil0_pages_per_sec": c.pages_per_sec("gil0"),
                "gil1_pages_per_sec": c.pages_per_sec("gil1"),
                "gil0_phases_s": c.gil0,
                "gil1_phases_s": c.gil1,
            }
            for c in sorted(cells, key=lambda x: (x.archetype, x.pages))
        ],
    }


def publish(cells: list[CellResult], runs: int) -> Path:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    mgr = BenchmarkResults(results_dir=BASELINE_DIR)
    metadata = {
        "python_version": sys.version,
        "free_threaded": not sys._is_gil_enabled(),
        "runs_per_cell": runs,
        "platform": sys.platform,
    }
    mgr.save_result("gil_speedup", to_payload(cells), metadata=metadata)
    # Stable, committed top-level file (not under the timestamped subdir).
    stable = BASELINE_DIR / "gil_speedup.json"
    stable.write_text(
        json.dumps({"metadata": metadata, "data": to_payload(cells)}, indent=2) + "\n"
    )
    return stable


# ---------------------------------------------------------------------------
# CI speed-regression gate (epic-performance.md Wave 2 / T6)
# ---------------------------------------------------------------------------
# A single total-wall tolerance would pass while a regression isolated to one
# phase (e.g. asset_audit or rendering) sailed through, so the gate checks each
# protected phase independently against a committed baseline captured on the
# target hardware. It measures only the GIL=0 (free-threaded) arm — the hot path
# the project actually ships.

GATE_BASELINE = BASELINE_DIR / "ci_gate.json"
GATE_KEYS = ("wall_s", "build_time_s", "phase.Rendering_s", "post_render.asset_audit_s")


def _measure_gil0(archetype: str, num_pages: int, runs: int) -> tuple[dict[str, float], str | None]:
    """Median GIL=0 phase ledger for one cell."""
    return _run_subprocess_mode(archetype, num_pages, runs, gil_on=False)


def _gate_metadata(archetype: str, num_pages: int, runs: int) -> dict:
    return {
        "python_version": sys.version,
        "free_threaded": not sys._is_gil_enabled(),
        "platform": sys.platform,
        "archetype": archetype,
        "pages": num_pages,
        "runs": runs,
    }


def run_gate_update(archetype: str, num_pages: int, runs: int) -> int:
    """Capture the current cell as the committed gate baseline (run on CI hardware)."""
    phases, err = _measure_gil0(archetype, num_pages, runs)
    if err:
        print(f"ERROR measuring gate baseline: {err}", file=sys.stderr)
        return 1
    GATE_BASELINE.parent.mkdir(parents=True, exist_ok=True)
    GATE_BASELINE.write_text(
        json.dumps(
            {"metadata": _gate_metadata(archetype, num_pages, runs), "phases_s": phases}, indent=2
        )
        + "\n"
    )
    print(f"Gate baseline written: {GATE_BASELINE}")
    print(f"  cell: {archetype} x {num_pages:,}, GIL=0, median-of-{runs}")
    for k in GATE_KEYS:
        if k in phases:
            print(f"  {k:32} {phases[k]:.3f}s")
    return 0


def run_gate(archetype: str, num_pages: int, runs: int, tolerance: float) -> int:
    """Fail (exit 1) if any protected phase regresses beyond ``tolerance`` vs the baseline."""
    if not GATE_BASELINE.exists():
        print(
            f"ERROR: no gate baseline at {GATE_BASELINE}. Bootstrap it on the target "
            "(CI) hardware with --gate-update first, then commit ci_gate.json.",
            file=sys.stderr,
        )
        return 1
    data = json.loads(GATE_BASELINE.read_text())
    baseline = data.get("phases_s", {})
    # Guard against comparing against a baseline captured for a different cell:
    # a blog/100 gate measured against a docs/1000 baseline is meaningless and
    # would either always pass or always fail. The cell must match exactly.
    meta = data.get("metadata", {})
    b_archetype, b_pages = meta.get("archetype"), meta.get("pages")
    if (b_archetype is not None and b_archetype != archetype) or (
        b_pages is not None and b_pages != num_pages
    ):
        print(
            f"ERROR: gate baseline cell ({b_archetype} x {b_pages}) does not match the "
            f"requested gate cell ({archetype} x {num_pages}). Re-bootstrap ci_gate.json "
            "with --gate-update for this exact cell.",
            file=sys.stderr,
        )
        return 1
    measured, err = _measure_gil0(archetype, num_pages, runs)
    if err:
        print(f"ERROR measuring gate cell: {err}", file=sys.stderr)
        return 1

    print(
        f"\nCI speed gate: {archetype} x {num_pages:,}, GIL=0, "
        f"median-of-{runs}, tolerance +{tolerance:.0%}"
    )
    print(f"  {'metric':32} {'baseline':>10} {'measured':>10} {'delta':>8}  status")
    print("-" * 78)
    regressed: list[tuple[str, float]] = []
    for k in GATE_KEYS:
        b = baseline.get(k)
        m = measured.get(k)
        if not b or m is None:
            continue
        delta = (m - b) / b
        status = "OK"
        if delta > tolerance:
            status = "REGRESSED"
            regressed.append((k, delta))
        print(f"  {k:32} {b:>10.3f} {m:>10.3f} {delta:>+7.1%}  {status}")

    if regressed:
        print(f"\nFAIL: {len(regressed)} phase(s) regressed beyond +{tolerance:.0%}:")
        for k, d in regressed:
            print(f"  - {k}: {d:+.1%}")
        return 1
    print("\nPASS: no protected phase regressed beyond tolerance.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--archetype", default=None)
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--expect-gil", choices=["0", "1"], default=None)
    parser.add_argument("--full", action="store_true", help="100, 1000, 10000 x all archetypes")
    parser.add_argument(
        "--scales", default=None, help="Comma-separated page counts (e.g. 100,1000,10000)"
    )
    parser.add_argument(
        "--archetypes", default=None, help="Comma-separated archetypes (blog,docs,autodoc)"
    )
    parser.add_argument("--publish", action="store_true", help="Write committed JSON baseline")
    parser.add_argument("--output", "-o", default=None, help="Also write raw JSON to this path")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="CI speed gate: compare a cell (GIL=0) vs benchmarks/baselines/ci_gate.json, "
        "fail on per-phase regression",
    )
    parser.add_argument(
        "--gate-update",
        action="store_true",
        help="Capture the current cell as the gate baseline (run on CI hardware, then commit)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.25, help="Gate regression tolerance (default 0.25)"
    )
    args = parser.parse_args()

    # Worker role: just measure and emit JSON for the requested mode.
    if args.worker:
        return _run_worker(
            archetype=args.archetype,
            num_pages=args.pages,
            runs=args.runs,
            expect_gil=args.expect_gil == "1",
        )

    # Driver role. Require a free-threaded *build* (one that can toggle the GIL),
    # not that the GIL is currently off — the per-mode subprocesses set PYTHON_GIL
    # explicitly, so the driver may itself be started under PYTHON_GIL=1.
    if not sysconfig.get_config_var("Py_GIL_DISABLED"):
        print(
            "ERROR: this is not a free-threaded CPython build, so PYTHON_GIL "
            "cannot be toggled. Run with a free-threaded build (e.g. 3.14t).",
            file=sys.stderr,
        )
        return 1

    # CI speed-regression gate modes (single-cell, GIL=0 only).
    if args.gate_update:
        return run_gate_update(args.archetype or "blog", args.pages or 100, args.runs)
    if args.gate:
        return run_gate(args.archetype or "blog", args.pages or 100, args.runs, args.tolerance)

    if args.scales or args.archetypes:
        scales = [int(s) for s in (args.scales or "100,1000").split(",")]
        archetypes = [a.strip() for a in (args.archetypes or "blog,docs,autodoc").split(",")]
    elif args.pages and args.archetype:
        scales = [args.pages]
        archetypes = [args.archetype]
    elif args.full:
        scales = [100, 1000, 10000]
        archetypes = ["blog", "docs", "autodoc"]
    else:
        scales = [100, 1000]
        archetypes = ["blog", "docs"]

    print("Free-threading A/B benchmark")
    print(f"  interpreter: {sys.version.split()[0]} (free-threaded, GIL off)")
    print(f"  scales:      {', '.join(f'{s:,}' for s in scales)}")
    print(f"  archetypes:  {', '.join(archetypes)}")
    print(f"  runs/cell:   {args.runs} (2 GIL modes/cell -> {2 * args.runs} subprocess builds)")
    print()

    cells: list[CellResult] = [
        run_cell(archetype, scale, args.runs) for archetype in archetypes for scale in scales
    ]

    print_table(cells)

    if args.output:
        Path(args.output).write_text(json.dumps(to_payload(cells), indent=2))
        print(f"Raw JSON: {args.output}")

    if args.publish:
        stable = publish(cells, args.runs)
        print(f"Baseline committed: {stable}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
