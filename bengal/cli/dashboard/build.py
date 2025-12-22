"""
Build Dashboard for Bengal.

Interactive Textual dashboard for `bengal build --dashboard` that shows:
- Live progress bar for build phases
- Phase timing table with status indicators
- Streaming build output log
- Keyboard shortcuts (q=quit, r=rebuild)

Usage:
    bengal build --dashboard

The dashboard runs the build in a background worker thread and updates
the UI reactively based on build stats.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Log, ProgressBar, Static

from bengal.cli.dashboard.base import BengalDashboard
from bengal.cli.dashboard.messages import BuildComplete
from bengal.cli.dashboard.notifications import notify_build_complete

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.profile import BuildProfile


@dataclass
class PhaseInfo:
    """Information about a build phase."""

    name: str
    status: str = "pending"  # pending, running, complete, error
    duration_ms: float | None = None
    details: str = ""


class BengalBuildDashboard(BengalDashboard):
    """
    Interactive build dashboard with live progress.

    Shows:
    - Header with Bengal branding
    - Progress bar for current phase
    - DataTable with phase timing
    - Log widget for build output
    - Footer with keyboard shortcuts

    Bindings:
        q: Quit
        r: Rebuild (if build complete)
        c: Clear log
        ?: Help
    """

    TITLE: ClassVar[str] = "Bengal Build"
    SUB_TITLE: ClassVar[str] = "Dashboard"

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalDashboard.BINDINGS,
        Binding("r", "rebuild", "Rebuild", show=True),
        Binding("c", "clear_log", "Clear Log"),
    ]

    # Reactive state
    current_phase: reactive[str] = reactive("")
    progress_percent: reactive[float] = reactive(0.0)
    build_complete: reactive[bool] = reactive(False)
    build_success: reactive[bool] = reactive(True)

    # Build phases (standard Bengal phases)
    PHASES: ClassVar[list[str]] = [
        "Discovery",
        "Taxonomies",
        "Rendering",
        "Assets",
        "Postprocess",
    ]

    def __init__(
        self,
        site: Site | None = None,
        *,
        parallel: bool = True,
        incremental: bool | None = None,
        quiet: bool = False,
        profile: BuildProfile | None = None,
        **build_kwargs: Any,
    ):
        """
        Initialize build dashboard.

        Args:
            site: Site instance to build
            parallel: Enable parallel rendering
            incremental: Use incremental build
            quiet: Suppress verbose output
            profile: Build profile
            **build_kwargs: Additional build options
        """
        super().__init__()
        self.site = site
        self.parallel = parallel
        self.incremental = incremental
        self.quiet = quiet
        self.build_profile = profile
        self.build_kwargs = build_kwargs

        # Phase tracking
        self.phases: dict[str, PhaseInfo] = {name: PhaseInfo(name=name) for name in self.PHASES}

        # Build stats
        self.stats: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()

        with Vertical(id="main-content"):
            # Status line
            yield Static(
                f"{self.mascot}  Ready to build",
                id="status-line",
                classes="section-header",
            )

            # Progress bar
            yield ProgressBar(total=100, show_eta=False, id="build-progress")

            # Phase table
            with Vertical(classes="section"):
                yield Static("Build Phases:", classes="section-header")
                yield DataTable(id="phase-table")

            # Build output log
            with Vertical(classes="section"):
                yield Static("Output:", classes="section-header")
                yield Log(id="build-log", auto_scroll=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up widgets when dashboard mounts."""
        # Configure phase table
        table = self.query_one("#phase-table", DataTable)
        table.add_columns("Status", "Phase", "Time", "Details")

        # Initialize rows for each phase
        for phase_name in self.PHASES:
            table.add_row(
                "·",  # pending icon
                phase_name,
                "-",
                "",
                key=phase_name,
            )

        # Start build if site provided
        if self.site:
            self._start_build()

    def _start_build(self) -> None:
        """Start the build in a background worker."""
        self.build_complete = False
        self.build_success = True
        self.current_phase = ""
        self.progress_percent = 0.0

        # Update status
        status = self.query_one("#status-line", Static)
        status.update(f"{self.mascot}  Building...")

        # Mark all phases as pending
        for phase_name in self.PHASES:
            self._update_phase_row(phase_name, status="·", time="-", details="")

        # Reset progress
        progress = self.query_one("#build-progress", ProgressBar)
        progress.update(progress=0)

        # Log start
        log = self.query_one("#build-log", Log)
        log.write_line(f"{self.mascot}  Starting build...")

        # Run build in background thread
        self.run_worker(
            self._run_build,
            name="build_worker",
            exclusive=True,
            thread=True,
        )

    async def _run_build(self) -> dict[str, Any]:
        """
        Run the build in a background thread.

        Returns build stats on completion.
        """
        from time import monotonic

        from bengal.orchestration.build import BuildOrchestrator

        start_time = monotonic()

        # Get log widget for output
        log = self.query_one("#build-log", Log)

        try:
            # Discovery phase
            self.call_from_thread(self._update_phase_running, "Discovery")
            self.call_from_thread(log.write_line, "→ Discovery...")

            orchestrator = BuildOrchestrator(self.site)

            # Run the actual build
            stats = orchestrator.build(
                parallel=self.parallel,
                incremental=self.incremental,
                quiet=True,  # Dashboard handles output
                profile=self.build_profile,
                **self.build_kwargs,
            )

            duration_ms = (monotonic() - start_time) * 1000

            # Update phases based on stats
            self._update_phases_from_stats(stats)

            # Post build complete
            self.call_from_thread(
                self.post_message,
                BuildComplete(
                    success=True,
                    duration_ms=duration_ms,
                    stats=stats.__dict__ if hasattr(stats, "__dict__") else {},
                ),
            )

            return stats

        except Exception as e:
            duration_ms = (monotonic() - start_time) * 1000

            self.call_from_thread(log.write_line, f"✗ Error: {e}")

            self.call_from_thread(
                self.post_message,
                BuildComplete(
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ),
            )

            raise

    def _update_phase_running(self, phase_name: str) -> None:
        """Mark a phase as running."""
        if phase_name in self.phases:
            self.phases[phase_name].status = "running"
        self._update_phase_row(phase_name, status="⠹", time="...")

    def _update_phases_from_stats(self, stats: Any) -> None:
        """Update phase display from build stats."""
        # Get timing info from stats if available
        phase_timings = getattr(stats, "phase_timings", {})

        # Map stats phase names to display names
        phase_map = {
            "discovery": "Discovery",
            "taxonomies": "Taxonomies",
            "rendering": "Rendering",
            "assets": "Assets",
            "postprocess": "Postprocess",
        }

        completed_phases = set()

        for internal_name, display_name in phase_map.items():
            timing = phase_timings.get(internal_name)
            if timing:
                duration_ms = timing.get("duration_ms", 0)
                details = timing.get("details", "")
                self.call_from_thread(
                    self._update_phase_complete, display_name, duration_ms, details
                )
                completed_phases.add(display_name)

        # Mark any remaining phases as complete with dash
        for phase_name in self.PHASES:
            if phase_name not in completed_phases:
                self.call_from_thread(self._update_phase_complete, phase_name, 0, "")

    def _update_phase_complete(self, phase_name: str, duration_ms: float, details: str) -> None:
        """Mark a phase as complete."""
        if phase_name in self.phases:
            self.phases[phase_name].status = "complete"
            self.phases[phase_name].duration_ms = duration_ms
            self.phases[phase_name].details = details

        time_str = f"{int(duration_ms)}ms" if duration_ms > 0 else "-"
        self._update_phase_row(phase_name, status="✓", time=time_str, details=details)

        log = self.query_one("#build-log", Log)
        if duration_ms > 0:
            details_str = f" ({details})" if details else ""
            log.write_line(f"✓ {phase_name} {time_str}{details_str}")

    # === Message Handlers ===

    def on_build_complete(self, message: BuildComplete) -> None:
        """Handle build complete event."""
        self.build_complete = True
        self.build_success = message.success
        self.stats = message.stats or {}

        # Update progress to 100% on success
        if message.success:
            self.progress_percent = 100
            progress = self.query_one("#build-progress", ProgressBar)
            progress.update(progress=100)

        # Update status line
        status = self.query_one("#status-line", Static)
        duration_s = message.duration_ms / 1000

        if message.success:
            pages = self.stats.get("pages_rendered", self.stats.get("pages", 0))
            status.update(f"{self.mascot}  Build complete! {pages} pages in {duration_s:.2f}s")

            # Show notification
            notify_build_complete(
                self,
                duration_ms=message.duration_ms,
                pages=pages,
                success=True,
            )

            # Final log entry
            log = self.query_one("#build-log", Log)
            log.write_line("")
            log.write_line(f"{self.mascot}  Build complete! {pages} pages in {duration_s:.2f}s")
            log.write_line("   Press 'r' to rebuild, 'q' to quit")
        else:
            status.update(f"{self.error_mascot}  Build failed: {message.error}")

            # Log error
            log = self.query_one("#build-log", Log)
            log.write_line("")
            log.write_line(f"{self.error_mascot}  Build failed: {message.error}")

            notify_build_complete(
                self,
                duration_ms=message.duration_ms,
                pages=0,
                success=False,
            )

    def _update_phase_row(
        self,
        phase_name: str,
        status: str | None = None,
        time: str | None = None,
        details: str | None = None,
    ) -> None:
        """Update a row in the phase table."""
        table = self.query_one("#phase-table", DataTable)

        try:
            row_key = phase_name

            if status is not None:
                table.update_cell(row_key, "Status", status)
            if time is not None:
                table.update_cell(row_key, "Time", time)
            if details is not None:
                table.update_cell(row_key, "Details", details)
        except Exception:
            # Row may not exist yet
            pass

    # === Actions ===

    def action_rebuild(self) -> None:
        """Trigger a rebuild."""
        if self.build_complete and self.site:
            # Reset phase state
            for phase in self.phases.values():
                phase.status = "pending"
                phase.duration_ms = None
                phase.details = ""

            # Clear log
            log = self.query_one("#build-log", Log)
            log.clear()

            # Start new build
            self._start_build()
        else:
            self.notify("Build in progress...", severity="warning")

    def action_clear_log(self) -> None:
        """Clear the build log."""
        log = self.query_one("#build-log", Log)
        log.clear()


def run_build_dashboard(
    site: Site,
    *,
    parallel: bool = True,
    incremental: bool | None = None,
    profile: BuildProfile | None = None,
    **kwargs: Any,
) -> None:
    """
    Run the build dashboard for a site.

    This is the entry point called by `bengal build --dashboard`.

    Args:
        site: Site instance to build
        parallel: Enable parallel rendering
        incremental: Use incremental build
        profile: Build profile
        **kwargs: Additional build options
    """
    app = BengalBuildDashboard(
        site=site,
        parallel=parallel,
        incremental=incremental,
        profile=profile,
        **kwargs,
    )
    app.run()
