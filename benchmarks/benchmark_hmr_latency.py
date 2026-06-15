#!/usr/bin/env python3
"""
End-to-end HMR save-to-reload latency benchmark (dev loop).
============================================================

Measures the WHOLE save -> reload chain the dev server actually runs, not just
``site.build()``. The committed dev-server warm path (``build_trigger.py``
``_run_warm_build``) times only ``site.build()`` + buffer swap, which hides the
fixed pre-build latency: the file-watch poll interval and the change-debounce
window. Together those constants add ~600ms of latency that every previous
committed number omitted.

This harness drives the REAL components, wired exactly as
``DevServer._create_watcher`` wires them:

    WatcherRunner (watchfiles, poll_delay_ms=300, debounce_ms=300)
        -> BuildTrigger.trigger_build  (full save->build->swap orchestration)
        -> BufferManager double-buffer (prepare staging / swap on success)
        -> ReloadNotifier.send         (the SSE reload-signal endpoint)

We start the watcher, then write a real edit to a real content file on disk and
time from the moment just before the write (``t_save``) to the moment the
reload-signal endpoint fires (``t_reload``). The only substitution vs production
is the ReloadNotifier: we inject an instrumented notifier that records the
wall-clock instant ``BuildTrigger`` calls ``send(...)``. That call site is the
exact endpoint the production ``LiveReloadNotifier`` uses to push the SSE
``reload`` event to the browser, so the recorded total is the honest
save->reload latency.

Timer-floor accounting
----------------------
The measured total is dominated by two *configurable deterministic constants*,
not by Bengal's work:

    poll_delay_ms  = 300  (file_watcher.py: watchfiles poll interval on macOS)
    debounce_ms    = 300  (watcher_runner.py: change-coalescing window)

A naive total would be ~600ms of fixed timer floor + a few ms of real work, so
the number would be uninformative -- it would track a config knob, not Bengal.
We therefore record:

    total_ms           - full save->reload wall clock (what a user feels)
    timer_floor_ms     - poll_delay_ms/2 + debounce_ms + debounce poll granularity
    variable_work_ms   - total_ms - timer_floor_ms (build + swap + signal)

``variable_work_ms`` is the number v0.6.0's proportional-rebuild work
(#332/#333) should drive down. ``total_ms`` is what the developer experiences;
``timer_floor_ms`` explains the gap.

Record-only
-----------
This is a RECORD, not a gate. Driving the async watcher deterministically is
timing-flaky (poll granularity, OS scheduling), so we warm up, take repeated
samples, and report the median. ``compare_hmr_latency.py`` reads the committed
baseline and reports drift WITHOUT failing CI.

Usage:
    # Record the committed baseline JSON (default 50-page site)
    python benchmarks/benchmark_hmr_latency.py --publish

    # Larger representative site, more samples
    python benchmarks/benchmark_hmr_latency.py --pages 200 --samples 7 --publish

    # Print only, do not commit
    python benchmarks/benchmark_hmr_latency.py --pages 50
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import statistics
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = REPO_ROOT / "benchmarks" / "baselines"

# ---------------------------------------------------------------------------
# Deterministic timer floor (configurable constants on the save->reload path)
# ---------------------------------------------------------------------------
# These mirror the production defaults so the floor we subtract tracks the code,
# not a copy-pasted magic number. If a future change moves these constants, this
# harness should move with them so the recorded floor stays honest.
#
#   POLL_DELAY_MS:  watchfiles poll interval (file_watcher.py: poll_delay_ms=300).
#                   On macOS the dev server forces polling, so a save is observed
#                   on average half a poll later; worst case a full poll later.
#   DEBOUNCE_MS:    WatcherRunner change-coalescing window (default 300).
#   DEBOUNCE_TICK_MS: the debounce loop wakes every 50ms (watcher_runner.py:
#                   _debounce_loop -> asyncio.sleep(0.05)), so the trigger fires
#                   up to one tick after the debounce window elapses.
POLL_DELAY_MS = 300
DEBOUNCE_MS = 300
DEBOUNCE_TICK_MS = 50

# The minimum deterministic floor a save waits through before any build can
# start: one debounce window + one debounce-loop tick + the expected (mean) half
# of one poll interval, since a save lands at a uniformly random offset within
# the poll interval.
TIMER_FLOOR_MS = DEBOUNCE_MS + DEBOUNCE_TICK_MS + (POLL_DELAY_MS / 2.0)


# ---------------------------------------------------------------------------
# Fixture site (same shape as benchmark_warm_build_consistency.py)
# ---------------------------------------------------------------------------


def create_test_site(num_pages: int, root: Path) -> Path:
    """Generate a representative ``num_pages`` docs/blog site under ``root``."""
    content_dir = root / "content"
    content_dir.mkdir(parents=True)

    (root / "bengal.toml").write_text(
        'title = "HMR Latency Benchmark"\n'
        'baseurl = "/"\n'
        "\n"
        "[build]\n"
        'theme = "default"\n'
        'output_dir = "public"\n'
        "incremental = true\n"
        "parallel = true\n"
        "minify_assets = false\n"
        "optimize_assets = false\n"
        "fingerprint_assets = false\n"
    )

    for i in range(num_pages):
        section_dir = content_dir / f"section-{i // 20 + 1}"
        section_dir.mkdir(exist_ok=True)
        index = section_dir / "_index.md"
        if not index.exists():
            index.write_text(f"---\ntitle: Section {i // 20 + 1}\n---\n# Section\n")
        (section_dir / f"page-{i + 1:03d}.md").write_text(
            f'---\ntitle: "Page {i + 1}"\ndate: 2025-01-01\n'
            f'tags: ["tag-{i % 10}"]\n---\n\n# Page {i + 1}\n\nContent for page {i + 1}.\n'
        )

    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Welcome\n")
    return root


# ---------------------------------------------------------------------------
# Instrumented reload notifier -- observes the SSE reload-signal endpoint
# ---------------------------------------------------------------------------


class _LatchNotifier:
    """ReloadNotifier that records when BuildTrigger fires the reload signal.

    This is the only production substitution. ``send`` is the exact call the
    real ``LiveReloadNotifier`` makes to push the SSE ``reload`` event; we
    record ``time.perf_counter()`` at that instant and release a latch the
    driver is waiting on. Implements the ``ReloadNotifier`` protocol
    (``send(action, reason, changed_paths)``).
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self.signal_time: float | None = None
        self.action: str | None = None
        self.reason: str | None = None

    def send(self, action: str, reason: str, changed_paths: Sequence[str]) -> None:
        # Record the first reload signal for this edit only.
        if self.signal_time is None:
            self.signal_time = time.perf_counter()
            self.action = action
            self.reason = reason
        self._event.set()

    def reset(self) -> None:
        self._event.clear()
        self.signal_time = None
        self.action = None
        self.reason = None

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout=timeout)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


@dataclass
class Sample:
    total_ms: float
    action: str | None
    reason: str | None


@dataclass
class CellResult:
    pages: int
    samples: list[Sample] = field(default_factory=list)
    error: str | None = None

    @property
    def total_ms_values(self) -> list[float]:
        return [s.total_ms for s in self.samples]

    @property
    def median_total_ms(self) -> float | None:
        vals = self.total_ms_values
        return statistics.median(vals) if vals else None

    @property
    def median_variable_work_ms(self) -> float | None:
        m = self.median_total_ms
        return None if m is None else max(0.0, m - TIMER_FLOOR_MS)


def _build_components(site_root: Path):
    """Wire the real WatcherRunner + BuildTrigger + BufferManager (dev-server shape)."""
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions
    from bengal.server.buffer_manager import BufferManager
    from bengal.server.build_trigger import BuildTrigger
    from bengal.server.ignore_filter import IgnoreFilter
    from bengal.server.watcher_runner import WatcherRunner
    from bengal.utils.observability.profile import BuildProfile

    site = Site.from_config(site_root)
    site.dev_mode = True

    # Cold build first (the dev server always serves a complete snapshot before
    # watching). This populates caches so the first warm rebuild is representative.
    site.build(BuildOptions(incremental=False, profile=BuildProfile.WRITER, quiet=True))

    # Double-buffer wired exactly as DevServer.__init__ does.
    staging_dir = site_root / ".bengal" / "staging"
    buffer_manager = BufferManager.for_dev_server(
        output_dir=site.output_dir,
        staging_dir=staging_dir,
    )
    buffer_manager.setup()

    notifier = _LatchNotifier()
    trigger = BuildTrigger(
        site=site,
        host="localhost",
        port=5173,
        notifier=notifier,
        buffer_manager=buffer_manager,
    )
    # Seed the content-hash cache like the dev server does after the first build,
    # so content-only edits exercise the same path as a live session.
    trigger.seed_content_hash_cache(list(site.pages))

    config = site.config or {}
    raw = getattr(config, "raw", config)
    config_dict = raw if isinstance(raw, dict) else {}
    ignore_filter = IgnoreFilter.from_config(config_dict, output_dir=site.output_dir)

    watch_dirs = [site_root / "content", site_root.resolve()]
    runner = WatcherRunner(
        paths=watch_dirs,
        ignore_filter=ignore_filter,
        on_changes=trigger.trigger_build,
        debounce_ms=DEBOUNCE_MS,
        # Force polling so the floor matches the macOS dev-server default and is
        # deterministic across hosts (FSEvents latency is unbounded/variable).
        force_polling=True,
    )
    return site, runner, trigger, notifier


def run_cell(pages: int, samples: int, warmup: int, timeout_s: float) -> CellResult:
    """Drive the real save->reload path ``samples`` times and record latency."""
    cell = CellResult(pages=pages)
    site_root = Path(tempfile.mkdtemp(prefix="bengal_hmr_"))
    runner = None
    try:
        create_test_site(pages, site_root)
        _site, runner, _trigger, notifier = _build_components(site_root)

        # Pick a representative leaf page to edit on every iteration.
        target = sorted((site_root / "content").glob("section-*/page-*.md"))[0]
        original = target.read_text()

        runner.start()
        # Let the watcher establish its first poll baseline before editing.
        time.sleep(1.0)

        recorded: list[Sample] = []
        attempts = warmup + samples
        # Generous retry budget: flaky misses (poll coalescing, OS scheduling)
        # are retried so the recorded set stays at the requested sample count.
        max_attempts = attempts + samples * 3
        i = 0
        taken = 0
        while taken < attempts and i < max_attempts:
            i += 1
            notifier.reset()
            marker = f"\n\n<!-- hmr-edit-{i} -->\n"
            t_save = time.perf_counter()
            target.write_text(original + marker)

            if not notifier.wait(timeout=timeout_s):
                # Missed signal -- restore and retry without consuming a sample.
                target.write_text(original)
                time.sleep(0.5)
                continue

            assert notifier.signal_time is not None
            total_ms = (notifier.signal_time - t_save) * 1000.0
            # Restore file so the next edit is a clean content-only change again.
            target.write_text(original)
            # Settle so the restore-write debounces out before the next sample.
            time.sleep((DEBOUNCE_MS + POLL_DELAY_MS) / 1000.0 + 0.3)

            if taken >= warmup:
                recorded.append(
                    Sample(total_ms=total_ms, action=notifier.action, reason=notifier.reason)
                )
            taken += 1

        cell.samples = recorded
        if len(recorded) < samples:
            cell.error = (
                f"only captured {len(recorded)}/{samples} samples "
                f"(watcher signal misses; try --samples lower or rerun)"
            )
    except Exception as exc:  # pragma: no cover - harness robustness
        cell.error = f"{type(exc).__name__}: {exc}"
    finally:
        if runner is not None:
            with contextlib.suppress(Exception):
                runner.stop()
        shutil.rmtree(site_root, ignore_errors=True)
    return cell


# ---------------------------------------------------------------------------
# Reporting / publishing
# ---------------------------------------------------------------------------


def _floor_breakdown() -> dict:
    return {
        "poll_delay_ms": POLL_DELAY_MS,
        "debounce_ms": DEBOUNCE_MS,
        "debounce_tick_ms": DEBOUNCE_TICK_MS,
        "expected_poll_contribution_ms": POLL_DELAY_MS / 2.0,
        "timer_floor_ms": TIMER_FLOOR_MS,
        "explanation": (
            "Deterministic, configurable latency a save waits through before "
            "any build can start: one debounce window (debounce_ms) + one "
            "debounce-loop tick (debounce_tick_ms) + the expected half of one "
            "watchfiles poll interval (poll_delay_ms/2). variable_work_ms = "
            "total_ms - timer_floor_ms isolates build+swap+signal -- the part "
            "v0.6.0 proportional-rebuild (#332/#333) should improve."
        ),
    }


def to_payload(cells: list[CellResult]) -> dict:
    return {
        "methodology": (
            "End-to-end dev-loop save->reload latency. Drives the real "
            "WatcherRunner -> BuildTrigger -> BufferManager double-buffer -> "
            "ReloadNotifier chain (wired as DevServer._create_watcher), forcing "
            "polling for a deterministic floor. A real content file is edited on "
            "disk; latency is measured from just before the write to the instant "
            "BuildTrigger fires the SSE reload signal (the same call site the "
            "production LiveReloadNotifier uses to push the browser reload). "
            "Warmup + median-of-N with retries on watcher signal misses. "
            "total_ms is decomposed into timer_floor_ms (poll+debounce constants) "
            "and variable_work_ms (build+swap+signal)."
        ),
        "timer_floor": _floor_breakdown(),
        "cells": [
            {
                "pages": c.pages,
                "error": c.error,
                "samples": len(c.samples),
                "total_ms_median": c.median_total_ms,
                "variable_work_ms_median": c.median_variable_work_ms,
                "timer_floor_ms": TIMER_FLOOR_MS,
                "total_ms_min": min(c.total_ms_values) if c.total_ms_values else None,
                "total_ms_max": max(c.total_ms_values) if c.total_ms_values else None,
                "total_ms_samples": c.total_ms_values,
                "reload_action": c.samples[0].action if c.samples else None,
                "reload_reason": c.samples[0].reason if c.samples else None,
            }
            for c in sorted(cells, key=lambda x: x.pages)
        ],
    }


def print_table(cells: list[CellResult]) -> None:
    print()
    print("=" * 78)
    print("HMR SAVE->RELOAD LATENCY  (end-to-end dev loop)")
    print("=" * 78)
    print(
        f"  timer floor: {TIMER_FLOOR_MS:.0f}ms  "
        f"(debounce {DEBOUNCE_MS} + tick {DEBOUNCE_TICK_MS} + poll/2 {POLL_DELAY_MS / 2:.0f})"
    )
    print("-" * 78)
    print(f"  {'Pages':>8} {'total ms':>12} {'floor ms':>10} {'work ms':>10} {'n':>4}")
    print("-" * 78)
    for c in sorted(cells, key=lambda x: x.pages):
        if c.error and not c.samples:
            print(f"  {c.pages:>8} {'ERR':>12} {'-':>10} {'-':>10} {0:>4}  {c.error[:30]}")
            continue
        print(
            f"  {c.pages:>8} {c.median_total_ms:>12.1f} {TIMER_FLOOR_MS:>10.0f} "
            f"{c.median_variable_work_ms:>10.1f} {len(c.samples):>4}"
        )
        if c.error:
            print(f"           note: {c.error}")
    print()


def publish(cells: list[CellResult], samples: int) -> Path:
    sys.path.insert(0, str(REPO_ROOT / "tests" / "performance"))
    from results_manager import BenchmarkResults

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "python_version": sys.version,
        "free_threaded": not sys._is_gil_enabled(),
        "platform": sys.platform,
        "samples_per_cell": samples,
        "record_only": True,
        "note": (
            "RECORD, not a gate. Captured on the dev machine; re-capture on a "
            "stable host if ever promoted to a gate. compare_hmr_latency.py "
            "reports drift without failing CI."
        ),
    }
    mgr = BenchmarkResults(results_dir=BASELINE_DIR)
    mgr.save_result("hmr_latency", to_payload(cells), metadata=metadata)
    stable = BASELINE_DIR / "hmr_latency.json"
    stable.write_text(
        json.dumps({"metadata": metadata, "data": to_payload(cells)}, indent=2) + "\n"
    )
    return stable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=50, help="Pages in the fixture site")
    parser.add_argument("--scales", default=None, help="Comma-separated page counts (e.g. 50,200)")
    parser.add_argument("--samples", type=int, default=5, help="Recorded samples per cell")
    parser.add_argument("--warmup", type=int, default=2, help="Discarded warmup edits per cell")
    parser.add_argument(
        "--timeout", type=float, default=20.0, help="Per-edit reload-signal timeout (s)"
    )
    parser.add_argument("--publish", action="store_true", help="Write committed JSON baseline")
    parser.add_argument("--output", "-o", default=None, help="Also write raw JSON to this path")
    args = parser.parse_args()

    scales = [int(s) for s in args.scales.split(",")] if args.scales else [args.pages]

    print("HMR save->reload latency benchmark")
    print(f"  interpreter: {sys.version.split()[0]}")
    print(f"  scales:      {', '.join(str(s) for s in scales)} pages")
    print(f"  samples:     {args.samples} (+{args.warmup} warmup) per cell")
    print(f"  timer floor: {TIMER_FLOOR_MS:.0f}ms (subtracted to isolate variable work)")
    print()

    cells: list[CellResult] = []
    for pages in scales:
        print(f"  [{pages} pages] driving real watcher+build+swap+signal...")
        cell = run_cell(
            pages=pages,
            samples=args.samples,
            warmup=args.warmup,
            timeout_s=args.timeout,
        )
        if cell.median_total_ms is not None:
            print(
                f"    median total {cell.median_total_ms:.1f}ms "
                f"-> variable work {cell.median_variable_work_ms:.1f}ms "
                f"({len(cell.samples)} samples)"
            )
        else:
            print(f"    ERROR: {cell.error}")
        cells.append(cell)

    print_table(cells)

    if args.output:
        Path(args.output).write_text(json.dumps(to_payload(cells), indent=2))
        print(f"Raw JSON: {args.output}")

    if args.publish:
        stable = publish(cells, args.samples)
        print(f"Baseline committed: {stable}")

    # Record-only: never fail on the measured value. Only fail if we could not
    # measure at all (every cell errored with zero samples).
    if all(c.error and not c.samples for c in cells):
        print("ERROR: no cell produced any samples.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
