"""
ReloadController: Decide when and how to reload based on output diffs.

Scans the built output directory (e.g., public/) after each build and
compares against the prior snapshot to determine whether:
 - no reload is needed
 - CSS-only hot reload is sufficient
 - a full page reload is required

Uses file size and modification time for fast diffing. This is sufficient
for dev; a hashing option can be added later if needed.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SnapshotEntry:
    size: int
    mtime: float


@dataclass
class OutputSnapshot:
    files: Dict[str, SnapshotEntry]


@dataclass
class ReloadDecision:
    action: str  # 'none' | 'reload-css' | 'reload'
    reason: str
    changed_paths: List[str]


MAX_CHANGED_PATHS_TO_SEND = 20


class ReloadController:
    def __init__(self, min_notify_interval_ms: int = 150) -> None:
        self._previous: OutputSnapshot | None = None
        self._last_notify_time_ms: int = 0
        self._min_interval_ms: int = min_notify_interval_ms

    def _now_ms(self) -> int:
        # Use monotonic clock for interval measurement to avoid wall-clock jumps
        return int(time.monotonic() * 1000)

    def _take_snapshot(self, output_dir: Path) -> OutputSnapshot:
        files: Dict[str, SnapshotEntry] = {}
        base = output_dir.resolve()
        if not base.exists():
            return OutputSnapshot(files)

        for root, _dirs, filenames in os.walk(base):
            for name in filenames:
                fp = Path(root) / name
                try:
                    st = fp.stat()
                except (FileNotFoundError, PermissionError):
                    continue
                rel = str(fp.relative_to(base)).replace(os.sep, "/")
                files[rel] = SnapshotEntry(size=st.st_size, mtime=st.st_mtime)
        return OutputSnapshot(files)

    def _diff(self, prev: OutputSnapshot, curr: OutputSnapshot) -> Tuple[List[str], List[str]]:
        changed: List[str] = []
        css_changed: List[str] = []

        prev_files = prev.files
        curr_files = curr.files

        # Added or modified
        for path, entry in curr_files.items():
            pentry = prev_files.get(path)
            if pentry is None or pentry.size != entry.size or pentry.mtime != entry.mtime:
                changed.append(path)
                if path.lower().endswith(".css"):
                    css_changed.append(path)

        # Deleted
        for path in prev_files.keys() - curr_files.keys():
            changed.append(path)
            # deleted CSS still requires full reload; do not count as css_changed

        return changed, css_changed

    def decide_and_update(self, output_dir: Path) -> ReloadDecision:
        curr = self._take_snapshot(output_dir)

        if self._previous is None:
            # First run: set baseline, no reload
            self._previous = curr
            return ReloadDecision(action="none", reason="baseline", changed_paths=[])

        changed, css_changed = self._diff(self._previous, curr)

        # Update baseline before returning to prevent double notifications
        self._previous = curr

        if not changed:
            return ReloadDecision(action="none", reason="no-output-change", changed_paths=[])

        # Throttle identical consecutive notifications if too soon
        now = self._now_ms()
        if now - self._last_notify_time_ms < self._min_interval_ms:
            # Even if changed, suppress to coalesce rapid sequences
            return ReloadDecision(action="none", reason="throttled", changed_paths=[])

        self._last_notify_time_ms = now

        # CSS-only change
        if len(changed) == len(css_changed):
            return ReloadDecision(action="reload-css", reason="css-only", changed_paths=css_changed)

        # Anything else
        return ReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=changed[:MAX_CHANGED_PATHS_TO_SEND],
        )


# Global controller for dev server
controller = ReloadController()


