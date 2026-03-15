"""Build phase profiler — first-class support for bengal build --profile-phases.

Provides PhaseTimer for per-phase instrumentation and reporting utilities
for scaling analysis. Used by both the CLI (--profile-phases) and the
standalone benchmarks/profile_phases.py script.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

PHASE_GROUPS: dict[str, list[str]] = {
    "Discovery": [
        "fonts",
        "template_validation",
        "discovery",
        "cache_metadata",
        "config_check",
        "incremental_filter",
    ],
    "Content": [
        "sections",
        "taxonomies",
        "taxonomy_index",
        "menus",
        "related_posts",
        "query_indexes",
        "update_pages_list",
        "variant_filter",
        "url_collision",
    ],
    "Parsing": ["parse_content", "snapshot"],
    "Rendering": ["assets", "render", "update_site_pages", "track_assets"],
    "Finalization": ["postprocess", "cache_save", "collect_stats", "finalize"],
    "Health": ["health_check"],
}

LINEAR_THRESHOLD = 2.2


@dataclass
class PhaseTimer:
    """Collects per-phase durations from BuildOptions callbacks.

    Wire into a build via:
        timer = PhaseTimer()
        opts = BuildOptions(
            on_phase_start=timer.on_start,
            on_phase_complete=timer.on_complete,
        )
    """

    phases: dict[str, float] = field(default_factory=dict)
    _starts: dict[str, float] = field(default_factory=dict)

    def on_start(self, name: str) -> None:
        self._starts[name] = time.perf_counter()

    def on_complete(self, name: str, duration_ms: float, _details: str) -> None:
        self.phases[name] = duration_ms

    def group_totals(self) -> dict[str, float]:
        """Aggregate raw phase timings into PHASE_GROUPS buckets."""
        totals: dict[str, float] = {}
        claimed: set[str] = set()
        for group, keys in PHASE_GROUPS.items():
            total = 0.0
            for k in keys:
                for phase_name, ms in self.phases.items():
                    norm = phase_name.lower().replace(" ", "_").replace("-", "_")
                    if norm == k or k in norm:
                        total += ms
                        claimed.add(phase_name)
                        break
            totals[group] = total

        unclaimed = sum(ms for name, ms in self.phases.items() if name not in claimed)
        if unclaimed > 0.5:
            totals["Other"] = unclaimed
        return totals

    def total_ms(self) -> float:
        return sum(self.phases.values())


def format_phase_table(timer: PhaseTimer) -> str:
    """Format a single-build phase timing table as a string."""
    lines: list[str] = []
    total = timer.total_ms()
    lines.append("=" * 72)
    lines.append("BUILD PHASE TIMING")
    lines.append("=" * 72)
    lines.append(f"{'Phase':<30} {'Time (ms)':>10}  {'%':>6}  {'Bar'}")
    lines.append("-" * 72)

    groups = timer.group_totals()
    for group, ms in sorted(groups.items(), key=lambda kv: -kv[1]):
        if ms < 0.5:
            continue
        pct = ms / total * 100 if total > 0 else 0
        bar = "#" * int(pct / 2)
        lines.append(f"  {group:<28} {ms:>10.1f}  {pct:>5.1f}%  {bar}")

    lines.append("-" * 72)
    lines.append(f"  {'TOTAL':<28} {total:>10.1f}")
    lines.append("")

    lines.append("Individual phases:")
    for name, ms in sorted(timer.phases.items(), key=lambda kv: -kv[1]):
        pct = ms / total * 100 if total > 0 else 0
        lines.append(f"    {name:<30} {ms:>8.1f}ms  ({pct:>5.1f}%)")
    lines.append("")
    return "\n".join(lines)


def format_scaling_table(
    results: dict[int, PhaseTimer],
) -> str:
    """Format a multi-size scaling analysis table."""
    lines: list[str] = []
    sizes = sorted(results.keys())
    groups = [*list(PHASE_GROUPS.keys()), "Other"]

    lines.append("=" * 90)
    lines.append("PER-PHASE TIMING (ms) — SCALING ANALYSIS")
    lines.append("=" * 90)

    header = f"{'Phase':<16}"
    for s in sizes:
        header += f"  {s:>6} pages"
    if len(sizes) >= 2:
        header += f"  {'ratio':>8}  {'scaling':>10}"
    lines.append(header)
    lines.append("-" * 90)

    for group in groups:
        vals = [results[s].group_totals().get(group, 0.0) for s in sizes]
        if all(v < 0.5 for v in vals):
            continue

        row = f"{group:<16}"
        for v in vals:
            row += f"  {v:>10.1f}"

        if len(sizes) >= 2 and vals[-2] > 1.0:
            ratio = vals[-1] / vals[-2]
            row += f"  {ratio:>7.2f}x"
            if ratio > LINEAR_THRESHOLD:
                row += f"  {'SUPER-LIN':>10}"
            elif ratio > 1.8:
                row += f"  {'~linear':>10}"
            else:
                row += f"  {'sub-lin':>10}"
        lines.append(row)

    lines.append("-" * 90)
    wall_vals = [results[s].total_ms() for s in sizes]
    row = f"{'TOTAL':<16}"
    for v in wall_vals:
        row += f"  {v:>10.1f}"
    if len(sizes) >= 2 and wall_vals[-2] > 1.0:
        ratio = wall_vals[-1] / wall_vals[-2]
        row += f"  {ratio:>7.2f}x"
    lines.append(row)

    lines.append("")
    for s in sizes:
        total_s = results[s].total_ms() / 1000
        pps = s / total_s if total_s > 0 else 0
        lines.append(f"  {s} pages: {total_s:.2f}s  ({pps:.0f} pages/sec)")

    violations = _find_scaling_violations(results)
    if violations:
        lines.append("")
        lines.append("SCALING VIOLATIONS:")
        lines.extend(f"  {v}" for v in violations)

    lines.append("")
    return "\n".join(lines)


def _find_scaling_violations(results: dict[int, PhaseTimer]) -> list[str]:
    """Identify phases that scale super-linearly."""
    sizes = sorted(results.keys())
    if len(sizes) < 2:
        return []

    violations: list[str] = []
    s_prev, s_last = sizes[-2], sizes[-1]
    groups = [*list(PHASE_GROUPS.keys()), "Other"]

    for group in groups:
        prev_ms = results[s_prev].group_totals().get(group, 0.0)
        last_ms = results[s_last].group_totals().get(group, 0.0)
        if prev_ms < 1.0:
            continue
        ratio = last_ms / prev_ms
        if ratio > LINEAR_THRESHOLD:
            violations.append(
                f"{group}: {ratio:.2f}x for {s_last / s_prev:.0f}x pages "
                f"(budget: < {LINEAR_THRESHOLD}x)  VIOLATION"
            )
    return violations
