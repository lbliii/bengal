#!/usr/bin/env python3
"""
Speedup Report Generator
========================

Renders a human-readable Markdown report from the committed JSON baselines
produced by ``benchmark_gil_speedup.py`` and ``benchmark_cross_ssg.py``.

This is the "publish" surface for the north-star speed claim: a single
``benchmarks/baselines/SPEEDUP.md`` table that shows the free-threading
(PYTHON_GIL=0 vs PYTHON_GIL=1) speedup across scales x archetypes, plus the
Bengal-vs-Hugo cross-SSG row.

Usage:
    python benchmarks/generate_speedup_report.py
    python benchmarks/generate_speedup_report.py --output benchmarks/baselines/SPEEDUP.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = REPO_ROOT / "benchmarks" / "baselines"
GIL_JSON = BASELINE_DIR / "gil_speedup.json"
CROSS_JSON = BASELINE_DIR / "cross_ssg.json"
RSS_JSON = BASELINE_DIR / "peak_rss.json"


def _fmt(value: float | None, suffix: str = "", places: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{places}f}{suffix}"


def _render_gil_section(doc: dict) -> list[str]:
    data = doc.get("data", doc)
    meta = doc.get("metadata", {})
    cells = data.get("cells", [])
    lines = ["## Free-threading speedup (PYTHON_GIL=0 vs PYTHON_GIL=1)", ""]
    lines.append(
        "Same free-threaded CPython 3.14t interpreter. Each build runs in a "
        "subprocess; the only variable is whether the GIL is disabled "
        "(`PYTHON_GIL=0`, true free-threading) or re-enabled (`PYTHON_GIL=1`). "
        "Speedup = GIL=1 wall time / GIL=0 wall time; **> 1.0x means "
        "free-threading is faster**."
    )
    lines.append("")
    if meta:
        lines.append(f"- Interpreter: `{meta.get('python_version', '?').splitlines()[0]}`")
        lines.append(f"- Free-threaded build: `{meta.get('free_threaded')}`")
        lines.append(f"- Runs per cell (median): `{meta.get('runs_per_cell', '?')}`")
        lines.append("")

    lines.append(
        "| Archetype | Pages | GIL=0 (s) | GIL=1 (s) | GIL=0 pages/s | GIL=1 pages/s | Speedup |"
    )
    lines.append("|---|--:|--:|--:|--:|--:|--:|")
    for c in cells:
        if c.get("error"):
            lines.append(f"| {c['archetype']} | {c['pages']:,} | ERR | ERR | — | — | — |")
            continue
        sp = c.get("speedup")
        lines.append(
            f"| {c['archetype']} | {c['pages']:,} | "
            f"{_fmt(c.get('gil0_wall_s'))} | {_fmt(c.get('gil1_wall_s'))} | "
            f"{_fmt(c.get('gil0_pages_per_sec'), places=1)} | "
            f"{_fmt(c.get('gil1_pages_per_sec'), places=1)} | "
            f"{(f'{sp:.2f}x' if sp else '—')} |"
        )
    lines.append("")

    # Per-phase breakdown for the largest cell of each archetype.
    lines.append("### Per-phase wall time (GIL=0), largest scale per archetype")
    lines.append("")
    lines.append("| Archetype | Pages | discovery | taxonomy | rendering | assets | postprocess |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|")
    by_arch: dict[str, dict] = {}
    for c in cells:
        if c.get("error"):
            continue
        cur = by_arch.get(c["archetype"])
        if cur is None or c["pages"] > cur["pages"]:
            by_arch[c["archetype"]] = c
    for arch, c in sorted(by_arch.items()):
        ph = c.get("gil0_phases_s", {})
        lines.append(
            f"| {arch} | {c['pages']:,} | "
            f"{_fmt(ph.get('discovery_s'))} | {_fmt(ph.get('taxonomy_s'))} | "
            f"{_fmt(ph.get('rendering_s'))} | {_fmt(ph.get('assets_s'))} | "
            f"{_fmt(ph.get('postprocess_s'))} |"
        )
    lines.append("")
    return lines


def _render_cross_section(doc: dict) -> list[str]:
    data = doc.get("data", doc)
    results = data.get("results", [])
    skipped = data.get("skipped", {})
    lines = ["## Cross-SSG cold build (Bengal vs Hugo)", ""]
    lines.append(
        "Identical content, cold builds, median of N runs. Bengal runs on the "
        "free-threaded 3.14t interpreter (`PYTHON_GIL=0`); Hugo uses "
        "auto-generated minimal layouts. This row exists for transparency: Hugo "
        "(compiled Go) is the speed reference; Bengal's headline win is the "
        "free-threading table above, measured against its own GIL-enabled self."
    )
    lines.append("")

    scales = sorted({r["pages"] for r in results})
    ssgs = sorted({r["ssg"] for r in results})
    header = "| Pages | " + " | ".join(f"{s} (s)" for s in ssgs) + " |"
    lines.append(header)
    lines.append("|--:|" + "|".join("--:" for _ in ssgs) + "|")
    for scale in scales:
        row = [f"{scale:,}"]
        for ssg in ssgs:
            match = next((r for r in results if r["ssg"] == ssg and r["pages"] == scale), None)
            secs = match.get("median_seconds") if match else None
            row.append(_fmt(secs))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # pages/sec table.
    lines.append("Throughput (pages/second):")
    lines.append("")
    lines.append("| Pages | " + " | ".join(f"{s}" for s in ssgs) + " |")
    lines.append("|--:|" + "|".join("--:" for _ in ssgs) + "|")
    for scale in scales:
        row = [f"{scale:,}"]
        for ssg in ssgs:
            match = next((r for r in results if r["ssg"] == ssg and r["pages"] == scale), None)
            pps = match.get("pages_per_second") if match else None
            row.append(_fmt(pps, places=0))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    if skipped:
        lines.append("Skipped SSGs:")
        lines.append("")
        for name, reason in sorted(skipped.items()):
            lines.append(f"- **{name}**: {reason}")
        lines.append("")
    return lines


def _render_rss_section(doc: dict) -> list[str]:
    data = doc.get("data", doc)
    cells = data.get("cells", [])
    budget = data.get("budget_mb", 2048.0)
    lines = ["## Peak resident memory (cold build)", ""]
    lines.append(
        "Process RSS sampled on a daemon thread during a cold build on the "
        "free-threaded 3.14t interpreter. The deliverable budget is "
        f"**< {budget:.0f} MB ({budget / 1024:.0f} GB) at 10k pages**."
    )
    lines.append("")
    lines.append("| Archetype | Pages | Peak RSS (MB) | Build (s) | Within budget |")
    lines.append("|---|--:|--:|--:|:--:|")
    for c in cells:
        peak = c.get("peak_rss_mb")
        within = "yes" if peak is not None and peak < budget else "NO"
        lines.append(
            f"| {c['archetype']} | {c['pages']:,} | "
            f"{_fmt(peak, places=0)} | {_fmt(c.get('wall_s'), places=2)} | {within} |"
        )
    lines.append("")
    return lines


def build_report() -> str:
    lines = ["# Bengal performance baselines", ""]
    lines.append(
        "Generated by `benchmarks/generate_speedup_report.py` from the committed "
        "JSON baselines in `benchmarks/baselines/`. Regenerate after running "
        "`benchmark_gil_speedup.py --publish` and `benchmark_cross_ssg.py --publish`."
    )
    lines.append("")

    if GIL_JSON.exists():
        lines += _render_gil_section(json.loads(GIL_JSON.read_text()))
    else:
        lines += [
            "## Free-threading speedup",
            "",
            f"_No baseline yet. Run:_ `python benchmarks/benchmark_gil_speedup.py "
            f"--full --publish` _(expected at {GIL_JSON.relative_to(REPO_ROOT)})_",
            "",
        ]

    if RSS_JSON.exists():
        lines += _render_rss_section(json.loads(RSS_JSON.read_text()))
    else:
        lines += [
            "## Peak resident memory",
            "",
            f"_No baseline yet. Run:_ `python benchmarks/benchmark_peak_rss.py "
            f"--publish` _(expected at {RSS_JSON.relative_to(REPO_ROOT)})_",
            "",
        ]

    if CROSS_JSON.exists():
        lines += _render_cross_section(json.loads(CROSS_JSON.read_text()))
    else:
        lines += [
            "## Cross-SSG cold build",
            "",
            f"_No baseline yet. Run:_ `python benchmarks/benchmark_cross_ssg.py "
            f"--publish` _(expected at {CROSS_JSON.relative_to(REPO_ROOT)})_",
            "",
        ]

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        default=str(BASELINE_DIR / "SPEEDUP.md"),
        help="Where to write the Markdown report",
    )
    parser.add_argument(
        "--stdout", action="store_true", help="Print to stdout instead of writing a file"
    )
    args = parser.parse_args()

    report = build_report()
    if args.stdout:
        print(report)
    else:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        print(f"Report written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
