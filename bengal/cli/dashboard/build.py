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
from textual.containers import Horizontal, Vertical
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
    is_loading: reactive[bool] = reactive(True)  # Task 4.1

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

            # Build statistics panel (Task 1.1)
            with Horizontal(classes="section"):
                yield Static(
                    self._get_build_stats_content(),
                    id="build-stats",
                    classes="panel",
                )

            # Phase table with profiling (Task 1.2)
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
        # Configure phase table with percentage column (Task 1.2)
        table = self.query_one("#phase-table", DataTable)
        table.add_columns("Status", "Phase", "Time", "%", "Details")

        # Initialize rows for each phase with waiting state (Task 1.3)
        for phase_name in self.PHASES:
            table.add_row(
                "○",  # waiting icon
                phase_name,
                "-",
                "",
                "Waiting...",
                key=phase_name,
            )

        # Start build if site provided
        if self.site:
            self._start_build()

    def _get_build_stats_content(self) -> str:
        """Generate build stats panel content (Task 1.1)."""
        # Task 4.1: Show loading state
        if self.is_loading and not self.stats:
            return (
                "[bold]Build Statistics[/bold]\n"
                "─────────────────────────────────\n"
                "[dim]Loading... Press 'r' to start build[/dim]"
            )

        # Task 4.2: Empty state
        if not self.stats and self.build_complete is False:
            return (
                "[bold]Build Statistics[/bold]\n"
                "─────────────────────────────────\n"
                "[dim]No builds yet.\n"
                "Press 'r' to start a build.[/dim]"
            )

        stats = self.stats or {}

        # Cache hit rate calculation
        hits = stats.get("cache_hits", 0)
        misses = stats.get("cache_misses", 0)
        total = hits + misses
        hit_rate = f"{(hits / total * 100):.0f}%" if total > 0 else "N/A"

        # Memory from BuildStats (already tracked, no tracemalloc overhead)
        memory_mb = stats.get("memory_rss_mb", 0)

        # Build mode
        mode = "Incremental" if stats.get("incremental") else "Full"

        # Pages and assets
        pages = stats.get("total_pages", 0)
        assets = stats.get("total_assets", 0)
        sections = stats.get("total_sections", 0)

        return (
            f"[bold]Build Statistics[/bold]\n"
            f"─────────────────────────────────\n"
            f"[bold]Pages:[/]    {pages:>6}  │  [bold]Cache:[/]  {hit_rate}\n"
            f"[bold]Assets:[/]   {assets:>6}  │  [bold]Memory:[/] {memory_mb:.0f} MB\n"
            f"[bold]Sections:[/] {sections:>6}  │  [bold]Mode:[/]   {mode}"
        )

    def _update_build_stats(self) -> None:
        """Update the build stats panel with current stats."""
        try:
            stats_panel = self.query_one("#build-stats", Static)
            stats_panel.update(self._get_build_stats_content())
        except Exception:
            pass  # Panel may not exist yet

    def _start_build(self) -> None:
        """Start the build in a background worker."""
        self.build_complete = False
        self.build_success = True
        self.current_phase = ""
        self.progress_percent = 0.0
        self.is_loading = True  # Task 4.1

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
        self._update_phase_row(phase_name, status="⠹", time="...", percent="", details="")

    def _update_phases_from_stats(self, stats: Any) -> None:
        """Update phase display from build stats."""
        # Map BuildStats timing fields to display names
        # BuildStats has: discovery_time_ms, taxonomy_time_ms, rendering_time_ms, etc.
        phase_timing_map = {
            "Discovery": ("discovery_time_ms", None),
            "Taxonomies": ("taxonomy_time_ms", None),
            "Rendering": ("rendering_time_ms", "total_pages"),
            "Assets": ("assets_time_ms", "total_assets"),
            "Postprocess": ("postprocess_time_ms", None),
        }

        for display_name, (time_field, count_field) in phase_timing_map.items():
            duration_ms = getattr(stats, time_field, 0) or 0

            # Build details string from count field if available
            details = ""
            if count_field:
                count = getattr(stats, count_field, 0)
                if count:
                    details = f"{count} items"

            self.call_from_thread(self._update_phase_complete, display_name, duration_ms, details)

    def _update_phase_complete(self, phase_name: str, duration_ms: float, details: str) -> None:
        """Mark a phase as complete (Task 1.2)."""
        if phase_name in self.phases:
            self.phases[phase_name].status = "complete"
            self.phases[phase_name].duration_ms = duration_ms
            self.phases[phase_name].details = details

        time_str = f"{int(duration_ms)}ms" if duration_ms > 0 else "-"

        # Calculate percentage of total build time (Task 1.2)
        total_time = self._get_total_phase_time()
        if total_time > 0 and duration_ms > 0:
            pct = (duration_ms / total_time) * 100
            bar_len = int(pct / 5)  # 5% per character
            bar = "█" * bar_len
            percent_str = f"{pct:.0f}% {bar}"
        else:
            percent_str = ""

        self._update_phase_row(
            phase_name, status="✓", time=time_str, percent=percent_str, details=details
        )

        log = self.query_one("#build-log", Log)
        if duration_ms > 0:
            details_str = f" ({details})" if details else ""
            log.write_line(f"✓ {phase_name} {time_str}{details_str}")

    def _get_total_phase_time(self) -> float:
        """Get total time across all completed phases."""
        return sum(
            phase.duration_ms or 0 for phase in self.phases.values() if phase.status == "complete"
        )

    # === Message Handlers ===

    def on_build_complete(self, message: BuildComplete) -> None:
        """Handle build complete event."""
        self.build_complete = True
        self.build_success = message.success
        self.stats = message.stats or {}
        self.is_loading = False  # Task 4.1

        # Update progress to 100% on success
        if message.success:
            self.progress_percent = 100
            progress = self.query_one("#build-progress", ProgressBar)
            progress.update(progress=100)

        # Update build stats panel (Task 1.1)
        self._update_build_stats()

        # Recalculate phase percentages now that we have all times (Task 1.2)
        self._update_phase_percentages()

        # Update status line
        status = self.query_one("#status-line", Static)
        duration_s = message.duration_ms / 1000

        if message.success:
            pages = self.stats.get("pages_rendered", self.stats.get("total_pages", 0))
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

    def _update_phase_percentages(self) -> None:
        """Recalculate and update all phase percentages (Task 1.2)."""
        total_time = self._get_total_phase_time()
        if total_time <= 0:
            return

        for phase_name, phase in self.phases.items():
            if phase.status == "complete" and phase.duration_ms:
                pct = (phase.duration_ms / total_time) * 100
                bar_len = int(pct / 5)  # 5% per character, max 20 chars
                bar = "█" * bar_len
                percent_str = f"{pct:.0f}% {bar}"
                self._update_phase_row(phase_name, percent=percent_str)

    def _update_phase_row(
        self,
        phase_name: str,
        status: str | None = None,
        time: str | None = None,
        percent: str | None = None,
        details: str | None = None,
    ) -> None:
        """Update a row in the phase table (Task 1.2)."""
        table = self.query_one("#phase-table", DataTable)

        try:
            row_key = phase_name

            if status is not None:
                table.update_cell(row_key, "Status", status)
            if time is not None:
                table.update_cell(row_key, "Time", time)
            if percent is not None:
                table.update_cell(row_key, "%", percent)
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
