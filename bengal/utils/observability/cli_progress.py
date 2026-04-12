"""
Live progress display system with profile-aware output.

This module provides the LiveProgressManager class for displaying
real-time build progress in the terminal. It supports multiple
user profiles (Writer, Theme-Dev, Developer) with varying levels
of detail, and uses sequential print output for all environments.

Note:
    This module was moved from bengal.cli.progress to
    bengal.utils.observability.cli_progress to fix layer violations
    (orchestration importing from cli). The old import path still
    works for backward compatibility.

Classes:
PhaseStatus: Enum for tracking build phase states
PhaseProgress: Dataclass for individual phase progress data
LiveProgressManager: Main progress display manager

Features:
- Profile-aware display density
- Graceful fallback for CI/non-TTY environments
- Context manager for clean setup/teardown

Related:
- bengal/utils/observability/profile.py: BuildProfile definitions
- bengal/output/: CLI output utilities

"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.observability.terminal import is_interactive_terminal

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from bengal.utils.observability.profile import BuildProfile

logger = get_logger(__name__)


class PhaseStatus(Enum):
    """
    Status of a build phase.

    Values:
        PENDING: Phase not yet started
        RUNNING: Phase currently in progress
        COMPLETE: Phase finished successfully
        FAILED: Phase encountered an error

    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PhaseProgress:
    """
    Track progress for a single build phase.

    Attributes:
        name: Display name for the phase (e.g., 'Rendering', 'Discovery')
        status: Current phase status
        current: Number of items processed so far
        total: Total items to process (None if unknown)
        current_item: Name/path of item currently being processed
        elapsed_ms: Time elapsed since phase start in milliseconds
        start_time: Unix timestamp when phase started
        metadata: Additional phase-specific data (e.g., error messages)
        recent_items: Rolling list of recently processed items

    """

    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    current: int = 0
    total: int | None = None
    current_item: str = ""
    elapsed_ms: float = 0
    start_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    recent_items: list[str] = field(default_factory=list)

    def get_percentage(self) -> float | None:
        """
        Get completion percentage.

        Returns:
            Percentage complete (0-100), or None if total is unknown.
        """
        if self.total and self.total > 0:
            return (self.current / self.total) * 100
        return None

    def get_elapsed_str(self) -> str:
        """
        Get human-readable elapsed time string.

        Returns:
            Formatted string like '245ms' or '1.2s', or empty string if no time recorded.
        """
        if self.elapsed_ms > 0:
            if self.elapsed_ms < 1000:
                return f"{int(self.elapsed_ms)}ms"
            return f"{self.elapsed_ms / 1000:.1f}s"
        return ""


class LiveProgressManager:
    """
    Manager for live progress updates across build phases.

    Features:
    - Profile-aware display (Writer/Theme-Dev/Developer)
    - Sequential print output (no Rich dependency)
    - Graceful fallback for CI/non-TTY
    - Context manager for clean setup/teardown

    Example:
        with LiveProgressManager(profile) as progress:
            progress.add_phase('rendering', 'Rendering', total=100)
            progress.start_phase('rendering')

            for i in range(100):
                process_page(i)
                progress.update_phase('rendering', current=i+1,
                                     current_item=f"page_{i}.html")

            progress.complete_phase('rendering', elapsed_ms=1234)

    """

    def __init__(
        self,
        profile: BuildProfile,
        console: object | None = None,
        enabled: bool = True,
        render_fn: Callable[..., str] | None = None,
    ):
        """
        Initialize live progress manager.

        Args:
            profile: Build profile (Writer/Theme-Dev/Developer)
            console: Ignored — kept for backward compatibility.
            enabled: Whether live progress is enabled
            render_fn: Optional template render function (e.g. CLIOutput.render).
                Takes a template name and keyword context, returns rendered string.
        """
        self.profile = profile
        self.phases: dict[str, PhaseProgress] = {}
        self.phase_order: list[str] = []  # Preserve insertion order
        self.enabled = enabled
        self.use_live = enabled and is_interactive_terminal()
        self._render_fn = render_fn

        # Number of lines in the previous live frame (for ANSI cursor rewind).
        self._prev_frame_lines: int = 0

        # Get profile configuration
        profile_config = profile.get_config()
        self.live_config = profile_config.get(
            "live_progress",
            {
                "enabled": True,
                "show_recent_items": False,
                "show_metrics": False,
                "max_recent": 0,
            },
        )

        if not self.live_config.get("enabled", True):
            self.use_live = False

        # Lock protecting phase state mutations.
        self._lock = threading.Lock()

        # Track last printed state for fallback
        self._last_fallback_phase: str | None = None

    def start(self) -> LiveProgressManager:
        """
        Start the progress display.

        Returns:
            Self for method chaining.
        """
        return self

    def stop(self) -> None:
        """Stop the progress display."""
        if self._prev_frame_lines > 0:
            # Ensure the cursor is below the last rendered frame.
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._prev_frame_lines = 0

    def __enter__(self) -> LiveProgressManager:
        """Enter context manager."""
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        self.stop()

    def add_phase(self, phase_id: str, name: str, total: int | None = None) -> None:
        """
        Register a new phase.

        Args:
            phase_id: Unique identifier for the phase
            name: Display name for the phase
            total: Total number of items to process (if known)
        """
        self.phases[phase_id] = PhaseProgress(name=name, total=total)
        if phase_id not in self.phase_order:
            self.phase_order.append(phase_id)

    def start_phase(self, phase_id: str) -> None:
        """
        Mark phase as running.

        Args:
            phase_id: Phase identifier
        """
        if phase_id in self.phases:
            phase = self.phases[phase_id]
            phase.status = PhaseStatus.RUNNING
            phase.start_time = time.time()
            self._print_fallback()

    def update_phase(
        self,
        phase_id: str,
        current: int | None = None,
        current_item: str | None = None,
        **metadata: Any,
    ) -> None:
        """
        Update phase progress.

        Args:
            phase_id: Phase identifier
            current: Current progress count
            current_item: Current item being processed
            **metadata: Additional metadata to track
        """
        if phase_id not in self.phases:
            return

        with self._lock:
            phase = self.phases[phase_id]

            if current is not None:
                phase.current = current

            if current_item is not None:
                phase.current_item = current_item
                max_recent = self.live_config.get("max_recent", 0)
                if max_recent > 0:
                    phase.recent_items.append(current_item)
                    phase.recent_items = phase.recent_items[-max_recent:]

            phase.metadata.update(metadata)

            if phase.status == PhaseStatus.RUNNING and phase.start_time:
                phase.elapsed_ms = (time.time() - phase.start_time) * 1000

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        """
        Mark phase as complete.

        Args:
            phase_id: Phase identifier
            elapsed_ms: Total elapsed time in milliseconds (optional)
        """
        if phase_id in self.phases:
            phase = self.phases[phase_id]
            phase.status = PhaseStatus.COMPLETE

            if elapsed_ms is not None:
                phase.elapsed_ms = elapsed_ms
            elif phase.start_time:
                phase.elapsed_ms = (time.time() - phase.start_time) * 1000

            if phase.total:
                phase.current = phase.total

            self._print_fallback()

    def fail_phase(self, phase_id: str, error: str) -> None:
        """
        Mark phase as failed.

        Args:
            phase_id: Phase identifier
            error: Error message
        """
        if phase_id in self.phases:
            phase = self.phases[phase_id]
            phase.status = PhaseStatus.FAILED
            phase.metadata["error"] = error
            self._print_fallback()

    def _build_state(self) -> dict[str, Any]:
        """Convert phase data to pipeline_progress state format."""
        total_elapsed = 0.0
        completed = 0
        total = len(self.phase_order)
        phases: list[dict[str, Any]] = []

        for phase_id in self.phase_order:
            phase = self.phases[phase_id]
            status_map = {
                PhaseStatus.PENDING: "pending",
                PhaseStatus.RUNNING: "running",
                PhaseStatus.COMPLETE: "completed",
                PhaseStatus.FAILED: "failed",
            }
            phases.append(
                {
                    "name": phase.name,
                    "status": status_map[phase.status],
                    "elapsed": phase.elapsed_ms / 1000.0,
                    "error": phase.metadata.get("error", ""),
                }
            )
            if phase.status == PhaseStatus.COMPLETE:
                completed += 1
                total_elapsed += phase.elapsed_ms / 1000.0
            elif phase.status == PhaseStatus.RUNNING:
                total_elapsed += phase.elapsed_ms / 1000.0

        # Determine overall status
        if any(p.status == PhaseStatus.FAILED for p in self.phases.values()):
            overall = "failed"
        elif all(p.status == PhaseStatus.COMPLETE for p in self.phases.values()):
            overall = "completed"
        else:
            overall = "running"

        progress = completed / total if total > 0 else 0.0

        return {
            "status": overall,
            "progress": progress,
            "elapsed": total_elapsed,
            "phases": phases,
        }

    def _render_live(self) -> None:
        """Render progress with kida template and ANSI cursor control."""
        if not self._render_fn:
            return

        state = self._build_state()
        try:
            frame = self._render_fn("build_progress.kida", state=state).strip("\n")
        except Exception:
            return  # Silently fall back if template rendering fails

        lines = frame.split("\n")

        # Move cursor up to overwrite previous frame
        if self._prev_frame_lines > 0:
            sys.stdout.write(f"\033[{self._prev_frame_lines}A")

        for line in lines:
            sys.stdout.write(f"\033[2K{line}\n")
        sys.stdout.flush()

        self._prev_frame_lines = len(lines)

    def _print_fallback(self) -> None:
        """
        Print sequential progress output.

        Uses live ANSI rendering when a render function is available
        in an interactive terminal, otherwise prints traditional
        sequential lines showing phase starts and completions.
        """
        if self.use_live and self._render_fn:
            self._render_live()
            return

        for phase_id in self.phase_order:
            phase = self.phases[phase_id]

            if phase.status == PhaseStatus.RUNNING:
                if self._last_fallback_phase != phase_id:
                    print(f"  * {phase.name}...", file=sys.stdout)
                    self._last_fallback_phase = phase_id

            elif phase.status == PhaseStatus.COMPLETE:
                if self._last_fallback_phase == phase_id:
                    elapsed = phase.get_elapsed_str()
                    if elapsed:
                        print(f"  + {phase.name} ({elapsed})", file=sys.stdout)
                    else:
                        print(f"  + {phase.name}", file=sys.stdout)
                    self._last_fallback_phase = None

            elif phase.status == PhaseStatus.FAILED:
                error = phase.metadata.get("error", "Unknown error")
                print(f"  x {phase.name}: {error}", file=sys.stdout)
                self._last_fallback_phase = None
