"""
Live progress display system with profile-aware output.

This module provides the LiveProgressManager class for displaying
real-time build progress in the terminal. It supports multiple
user profiles (Writer, Theme-Dev, Developer) with varying levels
of detail, and gracefully falls back to sequential output in
non-TTY environments.

Classes:
    PhaseStatus: Enum for tracking build phase states
    PhaseProgress: Dataclass for individual phase progress data
    LiveProgressManager: Main progress display manager

Features:
    - Profile-aware display density
    - In-place terminal updates (no scrolling)
    - Graceful fallback for CI/non-TTY environments
    - Context manager for clean setup/teardown
    - Throttled rendering to reduce overhead

Related:
    - bengal/utils/profile.py: BuildProfile definitions
    - bengal/output/: CLI output utilities
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from types import TracebackType
from typing import Any

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text

from bengal.utils.logger import get_logger
from bengal.utils.profile import BuildProfile
from bengal.utils.rich_console import get_console, should_use_rich

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
            else:
                return f"{self.elapsed_ms / 1000:.1f}s"
        return ""


class LiveProgressManager:
    """
    Manager for live progress updates across build phases.

    Features:
    - Profile-aware display (Writer/Theme-Dev/Developer)
    - In-place updates (no scrolling)
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

    def __init__(self, profile: BuildProfile, console: Console | None = None, enabled: bool = True):
        """
        Initialize live progress manager.

        Args:
            profile: Build profile (Writer/Theme-Dev/Developer)
            console: Rich console instance (creates one if not provided)
            enabled: Whether live progress is enabled
        """
        self.profile = profile
        self.console = console or get_console()
        self.phases: dict[str, PhaseProgress] = {}
        self.phase_order: list[str] = []  # Preserve insertion order
        self.live: Live | None = None
        self.enabled = enabled

        # Determine if we should use live updates
        self.use_live = (
            enabled
            and should_use_rich()
            and self.console.is_terminal
            and not self.console.is_jupyter
        )

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

        # Override with profile setting
        if not self.live_config.get("enabled", True):
            self.use_live = False

        # Throttle rendering to reduce overhead during very frequent updates.
        # Default to ~2 Hz (500ms) for better performance (was 200ms/5Hz)
        # This reduces Rich rendering overhead while still providing smooth progress feedback
        min_interval_ms = self.live_config.get("min_interval_ms", 500)
        try:
            self._min_render_interval_sec = max(0.0, float(min_interval_ms) / 1000.0)
        except Exception as e:
            logger.debug(
                "live_progress_interval_parse_failed",
                min_interval_ms=min_interval_ms,
                error=str(e),
                error_type=type(e).__name__,
                action="using_default_0_5_sec",
            )
            self._min_render_interval_sec = 0.5
        self._last_render_ts: float = 0.0

        # Track last printed state for fallback
        self._last_fallback_phase: str | None = None

    def __enter__(self) -> LiveProgressManager:
        """Enter context manager."""
        if self.use_live:
            # Create Live display
            self.live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=4,
                transient=False,  # Keep final output
            )
            self.live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        if self.live:
            # Final update before closing
            self._update_display(force=True)
            try:
                self.live.__exit__(exc_type, exc_val, exc_tb)
            finally:
                # Ensure Live display is fully released
                self.live = None

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
        self._update_display(force=True)

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
            self._update_display(force=True)

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

        phase = self.phases[phase_id]

        if current is not None:
            phase.current = current

        if current_item is not None:
            phase.current_item = current_item
            # Add to recent items for theme-dev/dev profiles
            max_recent = self.live_config.get("max_recent", 0)
            if max_recent > 0:
                phase.recent_items.append(current_item)
                # Keep only last N items
                phase.recent_items = phase.recent_items[-max_recent:]

        # Update metadata
        phase.metadata.update(metadata)

        # Update elapsed time if phase is running
        if phase.status == PhaseStatus.RUNNING and phase.start_time:
            phase.elapsed_ms = (time.time() - phase.start_time) * 1000

        # Frequent updates are throttled; no force here
        self._update_display()

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

            # Calculate elapsed time
            if elapsed_ms is not None:
                phase.elapsed_ms = elapsed_ms
            elif phase.start_time:
                phase.elapsed_ms = (time.time() - phase.start_time) * 1000

            # Set current to total if we have a total
            if phase.total:
                phase.current = phase.total

            self._update_display(force=True)

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
            self._update_display(force=True)

    def _update_display(self, force: bool = False) -> None:
        """Update the live display or print fallback."""
        if self.live:
            now = time.time()
            if not force and (now - self._last_render_ts) < self._min_render_interval_sec:
                return
            self.live.update(self._render())
            self._last_render_ts = now
        else:
            # Fallback for CI/non-TTY: print incremental updates
            self._print_fallback()

    def _render(self) -> RenderableType:
        """Render the progress display based on profile."""
        if self.profile == BuildProfile.WRITER:
            return self._render_writer()
        elif self.profile == BuildProfile.THEME_DEV:
            return self._render_theme_dev()
        else:  # DEVELOPER
            return self._render_developer()

    def _render_writer(self) -> RenderableType:
        """
        Render compact display for Writer profile.

        Optimized for minimal distraction during content creation.
        Shows only essential progress: phase name, progress bar,
        current count, and current item being processed.

        Returns:
            Rich renderable group of styled text lines.
        """
        lines = []

        for phase_id in self.phase_order:
            phase = self.phases[phase_id]

            # Build phase line
            status_icon = self._get_status_icon(phase.status)

            if phase.status == PhaseStatus.COMPLETE:
                # Completed phase: just show checkmark and name
                line = f"{status_icon} [green]{phase.name:<13}[/green] [dim]Done[/dim]"
            elif phase.status == PhaseStatus.RUNNING:
                # Running phase: show progress
                if phase.total:
                    # Show progress bar
                    bar_width = 20
                    filled = int((phase.current / phase.total) * bar_width)
                    bar = (
                        "━" * filled + "╸" + "─" * (bar_width - filled - 1)
                        if filled < bar_width
                        else "━" * bar_width
                    )

                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] [{bar}] [bold]{phase.current}/{phase.total}[/bold]"

                    # Add current item (truncated)
                    if phase.current_item:
                        item = (
                            phase.current_item[:50] + "..."
                            if len(phase.current_item) > 50
                            else phase.current_item
                        )
                        line += f"  [dim]{item}[/dim]"
                else:
                    # No total: just show current item
                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] {phase.current_item}"
            else:
                # Pending phase
                line = f"  [dim]{phase.name:<13}[/dim] [dim]Waiting...[/dim]"

            lines.append(Text.from_markup(line))

        return Group(*lines)

    def _render_theme_dev(self) -> RenderableType:
        """
        Render detailed display for Theme-Dev profile.

        Provides more context than Writer profile, including
        recently processed items and elapsed time. Useful for
        theme developers debugging template rendering issues.

        Returns:
            Rich renderable group of styled text lines.
        """
        lines = []

        for phase_id in self.phase_order:
            phase = self.phases[phase_id]

            # Build main phase line
            status_icon = self._get_status_icon(phase.status)

            if phase.status == PhaseStatus.COMPLETE:
                elapsed = phase.get_elapsed_str()
                line = f"{status_icon} [green]{phase.name:<13}[/green] [dim]Done[/dim]"
                if elapsed:
                    line += f" [dim]({elapsed})[/dim]"
                lines.append(Text.from_markup(line))

            elif phase.status == PhaseStatus.RUNNING:
                if phase.total:
                    bar_width = 20
                    filled = int((phase.current / phase.total) * bar_width)
                    bar = (
                        "━" * filled + "╸" + "─" * (bar_width - filled - 1)
                        if filled < bar_width
                        else "━" * bar_width
                    )

                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] [{bar}] [bold]{phase.current}/{phase.total}[/bold]"

                    # Add current item
                    if phase.current_item:
                        item = (
                            phase.current_item[:40] + "..."
                            if len(phase.current_item) > 40
                            else phase.current_item
                        )
                        line += f"  [dim]{item}[/dim]"

                    # Add elapsed time
                    elapsed = phase.get_elapsed_str()
                    if elapsed:
                        line += f"  [dim]({elapsed})[/dim]"

                    lines.append(Text.from_markup(line))

                    # Show recent items
                    if phase.recent_items and self.live_config.get("show_recent_items", False):
                        lines.append(Text.from_markup("  [dim]Recent:[/dim]"))
                        for item in phase.recent_items[-3:]:
                            short_item = item[:60] + "..." if len(item) > 60 else item
                            lines.append(
                                Text.from_markup(f"    [green]✓[/green] [dim]{short_item}[/dim]")
                            )
                else:
                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] {phase.current_item}"
                    lines.append(Text.from_markup(line))
            else:
                # Pending
                line = f"  [dim]{phase.name:<13}[/dim] [dim]Waiting...[/dim]"
                lines.append(Text.from_markup(line))

        return Group(*lines)

    def _render_developer(self) -> RenderableType:
        """
        Render full observability display for Developer profile.

        Shows maximum detail including all phases, throughput
        metrics, performance statistics, and error details.
        Intended for debugging build performance issues.

        Returns:
            Rich renderable group of styled text lines.
        """
        lines = []

        for phase_id in self.phase_order:
            phase = self.phases[phase_id]

            status_icon = self._get_status_icon(phase.status)

            if phase.status == PhaseStatus.COMPLETE:
                elapsed = phase.get_elapsed_str()
                line = f"{status_icon} [green]{phase.name:<13}[/green] [dim]Done[/dim]"
                if elapsed:
                    line += f" [dim]({elapsed})[/dim]"

                # Add metadata
                if phase.metadata:
                    meta_parts = []
                    for key, value in phase.metadata.items():
                        if key != "error":
                            meta_parts.append(f"{key}={value}")
                    if meta_parts:
                        line += f"  [dim]{', '.join(meta_parts)}[/dim]"

                lines.append(Text.from_markup(line))

            elif phase.status == PhaseStatus.RUNNING:
                if phase.total:
                    bar_width = 20
                    filled = int((phase.current / phase.total) * bar_width)
                    bar = (
                        "━" * filled + "╸" + "─" * (bar_width - filled - 1)
                        if filled < bar_width
                        else "━" * bar_width
                    )

                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] [{bar}] [bold]{phase.current}/{phase.total}[/bold]"

                    # Add current item
                    if phase.current_item:
                        item = (
                            phase.current_item[:40] + "..."
                            if len(phase.current_item) > 40
                            else phase.current_item
                        )
                        line += f"  [dim]{item}[/dim]"

                    # Add elapsed time
                    elapsed = phase.get_elapsed_str()
                    if elapsed:
                        line += f"  [dim]({elapsed})[/dim]"

                    lines.append(Text.from_markup(line))

                    # Show metrics
                    if phase.metadata and self.live_config.get("show_metrics", False):
                        metric_parts = []

                        # Calculate throughput
                        if phase.elapsed_ms > 0 and phase.current > 0:
                            throughput = (phase.current / phase.elapsed_ms) * 1000
                            metric_parts.append(f"Throughput: {throughput:.1f} items/sec")

                        # Add other metadata
                        for key, value in phase.metadata.items():
                            if key not in ["error", "throughput"]:
                                metric_parts.append(f"{key}: {value}")

                        if metric_parts:
                            lines.append(
                                Text.from_markup(f"  [dim]{' | '.join(metric_parts)}[/dim]")
                            )
                else:
                    line = f"{status_icon} [cyan]{phase.name:<13}[/cyan] {phase.current_item}"
                    lines.append(Text.from_markup(line))

            elif phase.status == PhaseStatus.FAILED:
                error = phase.metadata.get("error", "Unknown error")
                line = f"✗ [red]{phase.name:<13}[/red] [red]{error}[/red]"
                lines.append(Text.from_markup(line))
            else:
                # Pending
                line = f"  [dim]{phase.name:<13}[/dim] [dim]Waiting...[/dim]"
                lines.append(Text.from_markup(line))

        return Group(*lines)

    def _get_status_icon(self, status: PhaseStatus) -> str:
        """
        Get display icon for phase status.

        Args:
            status: Current phase status

        Returns:
            Unicode character representing the status.
        """
        if status == PhaseStatus.COMPLETE:
            return "✓"
        elif status == PhaseStatus.RUNNING:
            return "●"
        elif status == PhaseStatus.FAILED:
            return "✗"
        else:
            return " "

    def _print_fallback(self) -> None:
        """
        Fallback output for non-TTY environments.

        Used in CI systems or when output is redirected to a file.
        Prints traditional sequential lines rather than in-place
        updates, showing phase starts and completions.
        """
        for phase_id in self.phase_order:
            phase = self.phases[phase_id]

            # Only print when phase changes state or completes
            if phase.status == PhaseStatus.RUNNING:
                # Print phase start (only once)
                if self._last_fallback_phase != phase_id:
                    print(f"  ● {phase.name}...")
                    self._last_fallback_phase = phase_id

            elif phase.status == PhaseStatus.COMPLETE:
                # Print completion
                if self._last_fallback_phase == phase_id:
                    elapsed = phase.get_elapsed_str()
                    if elapsed:
                        print(f"  ✓ {phase.name} ({elapsed})")
                    else:
                        print(f"  ✓ {phase.name}")
                    self._last_fallback_phase = None

            elif phase.status == PhaseStatus.FAILED:
                error = phase.metadata.get("error", "Unknown error")
                print(f"  ✗ {phase.name}: {error}")
                self._last_fallback_phase = None
