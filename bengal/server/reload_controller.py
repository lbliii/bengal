"""
Intelligent reload decision engine for Bengal dev server.

Analyzes output directory changes after each build to determine the optimal
reload strategy: no reload, CSS-only hot reload, or full page reload.

Features:
- Fast diffing using file size and mtime (no hashing by default)
- CSS-only hot reload when only stylesheets change
- Configurable throttling to coalesce rapid rebuild sequences
- Glob-based ignore patterns for output paths
- Optional content hashing for suspected false positives
- Thread-safe configuration updates
- Content-hash based change detection (RFC: Output Cache Architecture)

Classes:
ReloadController: Main decision engine with snapshot diffing
SnapshotEntry: Immutable file metadata (size, mtime)
OutputSnapshot: Directory state at a point in time
ReloadDecision: Action recommendation with reason and changed paths
EnhancedReloadDecision: Extended decision with output type breakdown

Constants:
MAX_CHANGED_PATHS_TO_SEND: Limit paths sent to client (20)

Architecture:
The controller maintains a baseline snapshot of the output directory.
After each build, it takes a new snapshot and diffs against baseline:

1. Take snapshot (walk output dir, collect size/mtime)
2. Diff against previous (find added/modified/deleted files)
3. Apply ignore globs and optional hash verification
4. Decide action: 'none', 'reload-css', or 'reload'
5. Update baseline for next comparison

CSS-only reload is chosen when ALL changed files are CSS. Any non-CSS
change triggers a full page reload.

RFC: Output Cache Architecture Enhancement:
When use_content_hashes=True, the controller uses embedded content hashes
from bengal:content-hash meta tags for accurate change detection:

1. capture_content_hash_baseline(): Capture hashes BEFORE build starts
2. decide_with_content_hashes(): Compare hashes to detect real changes
3. Aggregate-only changes (sitemap, feeds) don't trigger reload

Related:
- bengal/server/build_trigger.py: Calls decide_and_update after builds
- bengal/server/live_reload.py: Sends reload events to connected clients
- bengal/utils/hashing.py: Content hashing for suspect verification
- bengal/rendering/pipeline/output.py: Content hash embedding

"""

from __future__ import annotations

import fnmatch
import os
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.server.utils import get_icons
from bengal.utils.primitives.hashing import hash_file

if TYPE_CHECKING:
    from bengal.core.output import OutputRecord


@dataclass(frozen=True)
class SnapshotEntry:
    """
    Immutable file metadata for snapshot comparison.

    Attributes:
        size: File size in bytes
        mtime: Modification time as float (from os.stat)

    """

    size: int
    mtime: float


@dataclass
class OutputSnapshot:
    """
    Point-in-time snapshot of output directory state.

    Attributes:
        files: Map of relative paths to their metadata entries

    """

    files: dict[str, SnapshotEntry]


@dataclass
class ReloadDecision:
    """
    Reload action recommendation from the controller.

    Attributes:
        action: One of 'none', 'reload-css', or 'reload'
        reason: Machine-readable reason (e.g., 'css-only', 'throttled')
        changed_paths: List of changed output paths (limited to MAX_CHANGED_PATHS_TO_SEND)

    """

    action: str  # 'none' | 'reload-css' | 'reload'
    reason: str
    changed_paths: list[str]


@dataclass
class EnhancedReloadDecision:
    """
    Extended reload decision with output type breakdown.

    RFC: Output Cache Architecture - Categorizes changes by output type for
    smarter hot reload decisions.

    Attributes:
        action: One of 'none', 'reload-css', or 'reload'
        reason: Machine-readable reason
        changed_paths: List of changed output paths
        content_changes: Paths to changed content pages
        aggregate_changes: Paths to changed aggregate files (sitemap, feeds)
        asset_changes: Paths to changed assets

    """

    action: str  # 'none' | 'reload-css' | 'reload'
    reason: str
    changed_paths: list[str]
    content_changes: list[str]
    aggregate_changes: list[str]
    asset_changes: list[str]

    @property
    def meaningful_change_count(self) -> int:
        """Count of changes that affect user-visible content."""
        return len(self.content_changes) + len(self.asset_changes)


MAX_CHANGED_PATHS_TO_SEND = 20


class ReloadController:
    """
    Intelligent reload decision engine based on output directory diffs.

    Compares output directory snapshots to determine optimal reload strategy.
    Supports throttling, ignore patterns, and optional content hashing.

    Attributes:
        _previous: Last baseline snapshot for comparison
        _last_notify_time_ms: Timestamp of last reload notification
        _min_interval_ms: Minimum interval between notifications (throttling)
        _ignored_globs: Glob patterns for paths to ignore
        _hash_on_suspect: Enable content hashing for suspected false positives
        _hash_cache: LRU cache of path → (size, digest) for hash verification

    Thread Safety:
        Configuration setters are protected by _config_lock for runtime updates.

    Example:
            >>> controller = ReloadController(min_notify_interval_ms=500)
            >>> decision = controller.decide_and_update(Path("public/"))
            >>> if decision.action == "reload-css":
            ...     send_css_reload(decision.changed_paths)

    """

    def __init__(
        self,
        min_notify_interval_ms: int = 300,
        ignored_globs: list[str] | None = None,
        hash_on_suspect: bool = True,
        suspect_hash_limit: int = 200,
        suspect_size_limit_bytes: int = 2_000_000,
        use_content_hashes: bool = False,
    ) -> None:
        """
        Initialize the reload controller.

        Args:
            min_notify_interval_ms: Minimum milliseconds between reload notifications.
                                    Helps coalesce rapid rebuild sequences.
            ignored_globs: Glob patterns for output paths to ignore (e.g., '*.map').
            hash_on_suspect: Enable MD5 hashing to verify suspected changes.
                            Catches false positives from mtime-only changes.
            suspect_hash_limit: Maximum files to hash per decision (performance cap).
            suspect_size_limit_bytes: Skip hashing files larger than this (2MB default).
            use_content_hashes: Enable content-hash based change detection
                               (RFC: Output Cache Architecture).
        """
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

        # RFC: Output Cache Architecture - Content hash mode
        self._use_content_hashes: bool = use_content_hashes
        self._baseline_content_hashes: dict[str, str] = {}
        self._output_types: dict[str, str] = {}  # Store type name as string

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

    def set_use_content_hashes(self, value: bool) -> None:
        """Enable or disable content-hash based change detection."""
        with self._config_lock:
            self._use_content_hashes = bool(value)

    # --- Shared decision helpers ---

    def _is_throttled(self) -> bool:
        """
        Check if notification should be throttled.

        Returns True if the time since last notification is less than
        the minimum interval, indicating we should suppress this notification.

        Returns:
            True if notification should be suppressed, False otherwise.
        """
        now = self._now_ms()
        return now - self._last_notify_time_ms < self._min_interval_ms

    def _record_notification(self) -> None:
        """Record that a notification was sent (for throttling)."""
        self._last_notify_time_ms = self._now_ms()

    def _apply_ignore_globs(self, paths: list[str]) -> list[str]:
        """
        Filter paths through ignore globs.

        Args:
            paths: List of paths to filter

        Returns:
            Filtered list with ignored paths removed.
        """
        if not self._ignored_globs:
            return paths

        def is_ignored(p: str) -> bool:
            return any(fnmatch.fnmatch(p, pat) for pat in self._ignored_globs)

        return [p for p in paths if not is_ignored(p)]

    def _make_css_decision(self, paths: list[str], css_paths: list[str]) -> ReloadDecision:
        """
        Make reload decision based on changed paths.

        Args:
            paths: All changed paths
            css_paths: CSS-only changed paths

        Returns:
            ReloadDecision with appropriate action.
        """
        if not paths:
            return ReloadDecision(action="none", reason="no-output-change", changed_paths=[])

        # CSS-only if all changes are CSS
        if len(paths) == len(css_paths):
            return ReloadDecision(
                action="reload-css",
                reason="css-only",
                changed_paths=css_paths[:MAX_CHANGED_PATHS_TO_SEND],
            )

        return ReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=paths[:MAX_CHANGED_PATHS_TO_SEND],
        )

    # --- RFC: Output Cache Architecture - Content hash methods ---

    def capture_content_hash_baseline(self, output_dir: Path) -> None:
        """
        Capture content hashes before build for comparison.

        RFC: Output Cache Architecture - MUST be called BEFORE build starts
        to establish baseline. Build writes may overlap with this scan if
        called during build.

        Args:
            output_dir: Path to output directory (e.g., public/)

        """
        from bengal.orchestration.build.output_types import classify_output
        from bengal.rendering.pipeline.output import extract_content_hash
        from bengal.utils.primitives.hashing import hash_str

        self._baseline_content_hashes.clear()
        self._output_types.clear()

        if not output_dir.exists():
            return

        # Capture HTML file hashes
        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            try:
                content = html_file.read_text(errors="ignore")

                # Extract embedded hash (O(1) regex) or compute (O(n) hash)
                hash_val = extract_content_hash(content)
                if hash_val is None:
                    hash_val = hash_str(content, truncate=16)

                self._baseline_content_hashes[rel_path] = hash_val
                self._output_types[rel_path] = classify_output(html_file).name
            except OSError:
                # File may have been deleted during scan - skip
                continue

        # Capture CSS file hashes for accurate CSS-only hot reload detection
        for css_file in output_dir.rglob("*.css"):
            rel_path = str(css_file.relative_to(output_dir))
            try:
                css_hash = hash_file(css_file, truncate=16)
                self._baseline_content_hashes[rel_path] = css_hash
                self._output_types[rel_path] = "ASSET"
            except OSError:
                # File may have been deleted during scan - skip
                continue

    def decide_with_content_hashes(self, output_dir: Path) -> EnhancedReloadDecision:
        """
        Analyze changes using content hashes for accurate detection.

        RFC: Output Cache Architecture - Compares content hashes instead of
        mtimes for accurate change detection. Categorizes changes by output
        type for clear reporting.

        Args:
            output_dir: Path to output directory (e.g., public/)

        Returns:
            EnhancedReloadDecision with action and categorized changes.

        """
        from bengal.orchestration.build.output_types import classify_output
        from bengal.rendering.pipeline.output import extract_content_hash
        from bengal.utils.primitives.hashing import hash_str

        content_changes: list[str] = []
        aggregate_changes: list[str] = []
        asset_changes: list[str] = []

        for html_file in output_dir.rglob("*.html"):
            rel_path = str(html_file.relative_to(output_dir))
            try:
                content = html_file.read_text(errors="ignore")
            except OSError:
                continue

            current_hash = extract_content_hash(content)
            if current_hash is None:
                current_hash = hash_str(content, truncate=16)

            baseline_hash = self._baseline_content_hashes.get(rel_path)

            # New file or changed content
            if baseline_hash is None or current_hash != baseline_hash:
                output_type_name = self._output_types.get(rel_path)
                if output_type_name is None:
                    output_type = classify_output(html_file)
                    output_type_name = output_type.name

                if output_type_name in ("CONTENT_PAGE", "GENERATED_PAGE"):
                    content_changes.append(rel_path)
                elif output_type_name in ("AGGREGATE_INDEX", "AGGREGATE_FEED", "AGGREGATE_TEXT"):
                    aggregate_changes.append(rel_path)
                elif output_type_name == "ASSET":
                    asset_changes.append(rel_path)

        # Apply throttling (reuse existing mechanism)
        now = self._now_ms()
        if now - self._last_notify_time_ms < self._min_interval_ms:
            return EnhancedReloadDecision(
                action="none",
                reason="throttled",
                changed_paths=[],
                content_changes=[],
                aggregate_changes=[],
                asset_changes=[],
            )

        # CSS-only reload
        css_changes = self._check_css_changes_hashed(output_dir)
        if not content_changes and not aggregate_changes and css_changes:
            self._last_notify_time_ms = now
            return EnhancedReloadDecision(
                action="reload-css",
                reason="css-only",
                changed_paths=css_changes[:MAX_CHANGED_PATHS_TO_SEND],
                content_changes=[],
                aggregate_changes=[],
                asset_changes=css_changes,
            )

        # Content changed - full reload
        if content_changes:
            self._last_notify_time_ms = now
            all_changes = content_changes + aggregate_changes + asset_changes
            return EnhancedReloadDecision(
                action="reload",
                reason="content-changed",
                changed_paths=all_changes[:MAX_CHANGED_PATHS_TO_SEND],
                content_changes=content_changes,
                aggregate_changes=aggregate_changes,
                asset_changes=asset_changes,
            )

        # Aggregate-only changes - no reload needed
        if aggregate_changes and not content_changes:
            return EnhancedReloadDecision(
                action="none",
                reason="aggregate-only-changes",
                changed_paths=[],
                content_changes=[],
                aggregate_changes=aggregate_changes,
                asset_changes=[],
            )

        return EnhancedReloadDecision(
            action="none",
            reason="no-changes",
            changed_paths=[],
            content_changes=[],
            aggregate_changes=[],
            asset_changes=[],
        )

    def _check_css_changes_hashed(self, output_dir: Path) -> list[str]:
        """Check CSS files for content changes using hashes."""
        changed: list[str] = []
        for css_file in output_dir.rglob("*.css"):
            rel_path = str(css_file.relative_to(output_dir))
            try:
                current_hash = hash_file(css_file, truncate=16)
                if self._baseline_content_hashes.get(rel_path) != current_hash:
                    changed.append(rel_path)
            except OSError:
                continue
        return changed

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
        """
        Take a snapshot, diff against baseline, and decide reload action.

        This is the main entry point called after each build completes.
        It performs the full decision workflow:
        1. Snapshot current output directory
        2. Diff against previous baseline
        3. Apply ignore globs and optional hash verification
        4. Choose action based on changed file types
        5. Update baseline for next comparison

        Args:
            output_dir: Path to the output directory (e.g., public/)

        Returns:
            ReloadDecision with action, reason, and changed paths.
            Action is 'none' if no reload needed (baseline, no change, throttled).
            Action is 'reload-css' if only CSS files changed.
            Action is 'reload' for any other changes.
        """
        curr = self._take_snapshot(output_dir)

        if self._previous is None:
            # First run: set baseline, no reload
            self._previous = curr
            return ReloadDecision(action="none", reason="baseline", changed_paths=[])

        changed, css_changed = self._diff(self._previous, curr)

        # Optional: filter spurious changes via conditional hashing
        if changed and self._hash_on_suspect:
            from bengal.utils.observability.logger import (
                get_logger,  # local import to avoid import cycles
            )

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
                except Exception as e:
                    logger.debug(
                        "reload_controller_cap_check_failed",
                        suspects_hashed=suspects_hashed,
                        limit=self._suspect_hash_limit,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
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
            from bengal.utils.observability.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "reload_controller_files_changed",
                num_changed=len(changed),
                changed_files=changed[:5],
                action=decision.action,
                reason=decision.reason,
            )
            icons = get_icons()
            print(
                f"\n{icons.warning} RELOAD TRIGGERED: {len(changed)} files changed (action={decision.action}):"
            )
            for f in changed[:5]:
                print(f"    - {f}")
        except Exception as e:
            logger.debug(
                "reload_controller_debug_output_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        return decision

    def decide_from_outputs(self, outputs: list[OutputRecord]) -> ReloadDecision:
        """
        Decide reload action from typed output records.

        This is the preferred entry point when builder provides typed output information.
        No snapshot diffing required - uses OutputType classification directly.

        Args:
            outputs: List of OutputRecord from the build

        Returns:
            ReloadDecision with action based on output types.
            CSS-only changes → 'reload-css', otherwise → 'reload'.
        """
        from bengal.core.output import OutputType

        if not outputs:
            return ReloadDecision(action="none", reason="no-outputs", changed_paths=[])

        # Throttle check
        if self._is_throttled():
            return ReloadDecision(action="none", reason="throttled", changed_paths=[])

        # Apply ignore globs to filter outputs
        all_paths = [str(o.path) for o in outputs]
        filtered_paths = self._apply_ignore_globs(all_paths)

        if not filtered_paths:
            return ReloadDecision(action="none", reason="all-ignored", changed_paths=[])

        # Filter outputs to match filtered paths
        filtered_path_set = set(filtered_paths)
        filtered_outputs = [o for o in outputs if str(o.path) in filtered_path_set]

        # Record notification time
        self._record_notification()

        # Classify by output type - use typed classification, not extension checking
        css_only = all(o.output_type == OutputType.CSS for o in filtered_outputs)

        if css_only:
            return ReloadDecision(
                action="reload-css",
                reason="css-only",
                changed_paths=filtered_paths[:MAX_CHANGED_PATHS_TO_SEND],
            )
        return ReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=filtered_paths[:MAX_CHANGED_PATHS_TO_SEND],
        )

    def decide_from_changed_paths(self, changed_paths: list[str]) -> ReloadDecision:
        """
        Classify pre-computed changed paths into a reload decision.

        Alternative entry point when changed paths are already known
        (e.g., from incremental build output). Applies the same ignore
        globs and throttling as decide_and_update.

        Args:
            changed_paths: List of changed output paths (relative to output dir)

        Returns:
            ReloadDecision with action based on file types in changed_paths.
            CSS-only changes → 'reload-css', otherwise → 'reload'.
        """
        # Apply ignore globs first
        paths = self._apply_ignore_globs(list(changed_paths or []))

        if not paths:
            return ReloadDecision(action="none", reason="no-output-change", changed_paths=[])

        # Throttle check
        if self._is_throttled():
            return ReloadDecision(action="none", reason="throttled", changed_paths=[])

        # Record notification time
        self._record_notification()

        # Determine CSS-only paths
        css_paths = [p for p in paths if p.lower().endswith(".css")]

        return self._make_css_decision(paths, css_paths)


# Global controller for dev server
# RFC: Output Cache Architecture - Enable content-hash mode by default for accurate change detection
controller = ReloadController(use_content_hashes=True)
