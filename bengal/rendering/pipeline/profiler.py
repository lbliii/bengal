"""
Render pipeline profiler — lightweight per-step timing.

Thread-safe accumulator that times each stage of the rendering pipeline across
all worker threads. Enable by setting BENGAL_PROFILE_RENDER=1 in the environment
or via BuildContext.profile_render.

Usage in build::

    BENGAL_PROFILE_RENDER=1 bengal build

Report is printed automatically at the end of the render phase.

"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager


class RenderProfiler:
    """Thread-safe accumulator for per-step rendering timings."""

    _instance: RenderProfiler | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._step_lock = threading.Lock()
        # {step_name: total_seconds}
        self._totals: dict[str, float] = defaultdict(float)
        # {step_name: call_count}
        self._counts: dict[str, int] = defaultdict(int)
        # {step_name: max_seconds}
        self._maxes: dict[str, float] = defaultdict(float)
        self._page_count = 0
        self._wall_start: float = 0.0
        self._wall_end: float = 0.0

    @classmethod
    def get(cls) -> RenderProfiler:
        """Return (or create) the process-level singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def start_wall(self) -> None:
        self._wall_start = time.perf_counter()

    def stop_wall(self) -> None:
        self._wall_end = time.perf_counter()

    def record(self, step: str, elapsed: float) -> None:
        with self._step_lock:
            self._totals[step] += elapsed
            self._counts[step] += 1
            if elapsed > self._maxes[step]:
                self._maxes[step] = elapsed

    def record_page(self) -> None:
        with self._step_lock:
            self._page_count += 1

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.record(name, time.perf_counter() - t0)

    def report(self) -> str:
        """Return a formatted breakdown table."""
        wall = self._wall_end - self._wall_start if self._wall_end else 0.0
        pages = self._page_count or 1

        # Ordered steps (pipeline order)
        STEPS = [
            ("cache_check", "Cache check"),
            ("parse_markdown", "Markdown parse"),
            ("flush_highlight", "Syntax highlight flush"),
            ("html_transform", "HTML transform"),
            ("plain_text", "plain_text compute"),
            ("api_enhance", "API doc enhance"),
            ("link_extract", "Link extraction"),
            ("cache_parsed", "Cache write (parsed)"),
            ("render_content", "render_content()"),
            ("render_template", "render_page() template"),
            ("format_html", "format_html()"),
            ("cache_rendered", "Cache write (rendered)"),
            ("write_output", "write_output()"),
            ("json_accumulate", "JSON accumulate"),
            ("asset_deps", "Asset dep accumulate"),
        ]

        lines: list[str] = []
        lines.append("")
        lines.append("╔══ Render Pipeline Profile ══════════════════════════════════════╗")
        lines.append(
            f"  Pages: {self._page_count:,}   Wall time: {wall * 1000:.0f}ms   "
            f"Throughput: {self._page_count / wall:.0f}/sec"
            if wall
            else f"  Pages: {self._page_count:,}"
        )
        lines.append("")
        lines.append(f"  {'Step':<32} {'Total':>8}  {'Avg/pg':>8}  {'Max':>8}  {'% wall':>7}")
        lines.append("  " + "─" * 65)

        accounted = 0.0
        for key, label in STEPS:
            total = self._totals.get(key, 0.0)
            count = self._counts.get(key, 0)
            mx = self._maxes.get(key, 0.0)
            if count == 0:
                continue
            avg = total / pages
            pct = (total / wall * 100) if wall else 0.0
            accounted += total
            marker = " ◀" if pct > 20 else "  "
            lines.append(
                f"  {label:<32} {total * 1000:>7.0f}ms  {avg * 1000:>6.2f}ms  "
                f"{mx * 1000:>6.1f}ms  {pct:>6.1f}%{marker}"
            )

        # Unaccounted (overhead, GIL contention, thread scheduling)
        unaccounted = wall - accounted
        if wall:
            lines.append("  " + "─" * 65)
            pct = unaccounted / wall * 100
            lines.append(
                f"  {'Unaccounted (GIL/sched/overhead)':<32} {unaccounted * 1000:>7.0f}ms"
                f"  {'':>8}  {'':>8}  {pct:>6.1f}%"
            )

        # Cache summary
        hits_rendered = self._counts.get("cache_hit_rendered", 0)
        hits_parsed = self._counts.get("cache_hit_parsed", 0)
        full_renders = self._counts.get("full_render", 0)
        lines.append("")
        lines.append(
            f"  Cache hits  →  rendered: {hits_rendered:,}  "
            f"parsed: {hits_parsed:,}  full render: {full_renders:,}"
        )
        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        lines.append("")
        return "\n".join(lines)


def is_enabled() -> bool:
    return bool(os.environ.get("BENGAL_PROFILE_RENDER"))
