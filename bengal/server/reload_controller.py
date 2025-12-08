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

import fnmatch
import os
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.hashing import hash_file


@dataclass(frozen=True)
class SnapshotEntry:
    size: int
    mtime: float


@dataclass
class OutputSnapshot:
    files: dict[str, SnapshotEntry]


@dataclass
class ReloadDecision:
    action: str  # 'none' | 'reload-css' | 'reload'
    reason: str
    changed_paths: list[str]


MAX_CHANGED_PATHS_TO_SEND = 20


class ReloadController:
    def __init__(
        self,
        min_notify_interval_ms: int = 300,
        ignored_globs: list[str] | None = None,
        hash_on_suspect: bool = True,
        suspect_hash_limit: int = 200,
        suspect_size_limit_bytes: int = 2_000_000,
    ) -> None:
        self._previous: OutputSnapshot | None = None
        self._last_notify_time_ms: int = 0
        self._min_interval_ms: int = min_notify_interval_ms
        # Ignore patterns applied relative to output dir
        self._ignored_globs: list[str] = list(ignored_globs or [])
        # Conditional hashing options
        self._hash_on_suspect: bool = hash_on_suspect
        self._suspect_hash_limit: int = suspect_hash_limit
        self._suspect_size_limit_bytes: int = suspect_size_limit_bytes
        # Cache: path -> (size, hex_digest)
        self._hash_cache: dict[str, tuple[int, str]] = {}
        # Config lock for thread-safe updates during dev server runtime
        self._config_lock = threading.RLock()

    # --- Runtime configuration setters ---
    def set_min_notify_interval_ms(self, value: int) -> None:
        with self._config_lock, suppress(Exception):
            self._min_interval_ms = int(value)

    def set_ignored_globs(self, globs: list[str] | None) -> None:
        with self._config_lock:
            self._ignored_globs = list(globs or [])

    def set_hashing_options(
        self,
        *,
        hash_on_suspect: bool | None = None,
        suspect_hash_limit: int | None = None,
        suspect_size_limit_bytes: int | None = None,
    ) -> None:
        with self._config_lock:
            if hash_on_suspect is not None:
                self._hash_on_suspect = bool(hash_on_suspect)
            if suspect_hash_limit is not None:
                with suppress(Exception):
                    self._suspect_hash_limit = int(suspect_hash_limit)
            if suspect_size_limit_bytes is not None:
                with suppress(Exception):
                    self._suspect_size_limit_bytes = int(suspect_size_limit_bytes)

    def _now_ms(self) -> int:
        # Use monotonic clock for interval measurement to avoid wall-clock jumps
        return int(time.monotonic() * 1000)

    def _take_snapshot(self, output_dir: Path) -> OutputSnapshot:
        files: dict[str, SnapshotEntry] = {}
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

    def _diff(self, prev: OutputSnapshot, curr: OutputSnapshot) -> tuple[list[str], list[str]]:
        changed: list[str] = []
        css_changed: list[str] = []

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

        # Optional: filter spurious changes via conditional hashing
        if changed and self._hash_on_suspect:
            from bengal.utils.logger import get_logger  # local import to avoid import cycles

            logger = get_logger(__name__)

            suspects_hashed = 0
            filtered_changed: list[str] = []
            filtered_css_changed: list[str] = []

            prev_files = self._previous.files
            curr_files = curr.files

            for path in changed:
                pentry = prev_files.get(path)
                centry = curr_files.get(path)
                # Only consider suspects where file exists in both snapshots and size is equal but mtime differs
                is_suspect = (
                    pentry is not None
                    and centry is not None
                    and pentry.size == centry.size
                    and pentry.mtime != centry.mtime
                    and centry.size <= self._suspect_size_limit_bytes
                )

                suppressed_due_to_hash = False
                if is_suspect and suspects_hashed < self._suspect_hash_limit and centry is not None:
                    try:
                        # Compute current content hash (md5 for speed on large files)
                        abs_path = (output_dir / path).resolve()
                        digest = hash_file(abs_path, algorithm="md5", chunk_size=1 << 16)
                        suspects_hashed += 1

                        cached = self._hash_cache.get(path)
                        if cached and cached[0] == centry.size and cached[1] == digest:
                            # Content unchanged → suppress this change
                            suppressed_due_to_hash = True
                            logger.info(
                                "reload_controller_hash_equal_suppressed",
                                path=path,
                                size=centry.size,
                            )
                        # Update cache with latest known digest
                        self._hash_cache[path] = (centry.size, digest)
                    except FileNotFoundError:
                        # File disappeared between snapshot and hashing; treat as changed
                        pass
                    except Exception as e:
                        # Hashing failure should not block reload logic
                        logger.debug(
                            "reload_controller_hash_failed",
                            path=path,
                            error=str(e),
                            error_type=type(e).__name__,
                        )

                if not suppressed_due_to_hash:
                    filtered_changed.append(path)
                    if path.lower().endswith(".css"):
                        filtered_css_changed.append(path)

            changed = filtered_changed
            css_changed = filtered_css_changed
            if suspects_hashed:
                try:
                    cap_hit = suspects_hashed >= self._suspect_hash_limit
                except Exception:
                    cap_hit = False
                logger.debug(
                    "reload_controller_hash_stats",
                    suspects_hashed=suspects_hashed,
                    suspect_hash_limit=self._suspect_hash_limit,
                    cap_hit=cap_hit,
                )

        # Apply ignore globs (relative to output dir)
        if changed and self._ignored_globs:

            def _is_ignored(p: str) -> bool:
                return any(fnmatch.fnmatch(p, pat) for pat in self._ignored_globs)

            filtered_changed = [p for p in changed if not _is_ignored(p)]
            if len(filtered_changed) != len(changed):
                css_changed = [p for p in css_changed if p in filtered_changed]
            changed = filtered_changed

        # Prune hash cache entries for deleted files to avoid unbounded growth
        for deleted in self._previous.files.keys() - curr.files.keys():
            self._hash_cache.pop(deleted, None)

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

        # Decide action
        if len(changed) == len(css_changed):
            decision = ReloadDecision(
                action="reload-css", reason="css-only", changed_paths=css_changed
            )
        else:
            decision = ReloadDecision(
                action="reload",
                reason="content-changed",
                changed_paths=changed[:MAX_CHANGED_PATHS_TO_SEND],
            )

        # Log only when we will actually send a reload (post-throttle)
        try:
            from bengal.utils.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "reload_controller_files_changed",
                num_changed=len(changed),
                changed_files=changed[:5],
                action=decision.action,
                reason=decision.reason,
            )
            print(
                f"\n⚠️  RELOAD TRIGGERED: {len(changed)} files changed (action={decision.action}):"
            )
            for f in changed[:5]:
                print(f"    - {f}")
        except Exception:
            pass

        return decision

    def decide_from_changed_paths(self, changed_paths: list[str]) -> ReloadDecision:
        """Classify a given list of changed output paths.

        Applies ignore globs and throttling consistently with decide_and_update.
        """
        # Apply ignore globs first
        paths = list(changed_paths or [])
        if self._ignored_globs:

            def _is_ignored(p: str) -> bool:
                return any(fnmatch.fnmatch(p, pat) for pat in self._ignored_globs)

            paths = [p for p in paths if not _is_ignored(p)]

        if not paths:
            return ReloadDecision(action="none", reason="no-output-change", changed_paths=[])

        # Throttle
        now = self._now_ms()
        if now - self._last_notify_time_ms < self._min_interval_ms:
            return ReloadDecision(action="none", reason="throttled", changed_paths=[])
        self._last_notify_time_ms = now

        css_only = all(p.lower().endswith(".css") for p in paths)
        if css_only:
            return ReloadDecision(
                action="reload-css",
                reason="css-only",
                changed_paths=paths[:MAX_CHANGED_PATHS_TO_SEND],
            )
        return ReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=paths[:MAX_CHANGED_PATHS_TO_SEND],
        )


# Global controller for dev server
controller = ReloadController()
