"""
Phase Progress Widget.

Real-time streaming build phase display.
Extends BuildPhasePlan with live update support for dashboard integration.

Usage:
    from bengal.cli.dashboard.widgets import PhaseProgress

    progress = PhaseProgress()
    progress.reset()  # Reset to pending state

    # Connect to build callbacks
    def on_phase_start(phase_name: str) -> None:
        progress.start_phase(phase_name)

    def on_phase_complete(phase_name: str, duration_ms: float, details: str) -> None:
        progress.complete_phase(phase_name, duration_ms, details)

RFC: rfc-dashboard-api-integration
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from bengal.cli.dashboard.widgets.phase_plan import BuildPhase, BuildPhasePlan


@dataclass
class PhaseInfo:
    """Extended phase information with details."""

    name: str
    status: str
    duration_ms: float | None = None
    details: str = ""


class PhaseProgress(Vertical):
    """
    Real-time streaming build phase progress display.

    Extends BuildPhasePlan with:
    - Live phase updates via callbacks
    - Phase details display (item counts, etc.)
    - Total elapsed time tracking
    - Current phase highlighting

    Default phases match Bengal build pipeline:
    - Discovery → Content → Assets → Rendering → Finalization → Health

    Example:
        progress = PhaseProgress(id="build-progress")

        # Set as build callbacks
        orchestrator.build(
            on_phase_start=progress.start_phase,
            on_phase_complete=progress.complete_phase,
        )

    """

    DEFAULT_CSS = """
    PhaseProgress {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    PhaseProgress .progress-header {
        height: 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    PhaseProgress .phase-details {
        height: 1;
        color: $text-muted;
        margin-top: 1;
        text-align: center;
    }
    PhaseProgress .elapsed-time {
        height: 1;
        color: $success;
        margin-top: 1;
        text-align: right;
    }
    """

    # Phase names matching BuildOrchestrator callbacks
    PHASE_NAMES: list[str] = [
        "discovery",
        "content",
        "assets",
        "rendering",
        "finalization",
        "health",
    ]

    current_phase: reactive[str | None] = reactive(None)
    elapsed_ms: reactive[float] = reactive(0.0)
    current_details: reactive[str] = reactive("")

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize phase progress."""
        super().__init__(id=id, classes=classes)
        self._phases: dict[str, PhaseInfo] = {}
        self._phase_plan: BuildPhasePlan | None = None

    def compose(self) -> ComposeResult:
        """Compose the phase progress display."""
        yield Static("Build Progress", classes="progress-header")
        self._phase_plan = BuildPhasePlan(id="phase-plan")
        yield self._phase_plan
        yield Static("", classes="phase-details", id="phase-details")
        yield Static("", classes="elapsed-time", id="elapsed-time")

    def on_mount(self) -> None:
        """Initialize phases on mount."""
        self.reset()

    def reset(self) -> None:
        """Reset all phases to pending state."""
        self._phases = {}
        phases = []
        for name in self.PHASE_NAMES:
            self._phases[name] = PhaseInfo(name=name, status="pending")
            phases.append(BuildPhase(name=name.title(), status="pending"))

        if self._phase_plan is not None:
            self._phase_plan.phases = phases

        self.current_phase = None
        self.elapsed_ms = 0.0
        self.current_details = ""
        self._update_details("")
        self._update_elapsed()

    def start_phase(self, phase_name: str) -> None:
        """
        Mark a phase as started/running.

        Args:
            phase_name: Name of the phase (e.g., "discovery", "rendering")
        """
        phase_key = phase_name.lower()
        if phase_key not in self._phases:
            # Unknown phase - add it dynamically
            self._phases[phase_key] = PhaseInfo(name=phase_key, status="running")
        else:
            self._phases[phase_key] = PhaseInfo(
                name=phase_key,
                status="running",
            )

        self.current_phase = phase_key
        self._rebuild_phase_plan()
        self._update_details(f"Running: {phase_name.title()}...")

    def complete_phase(
        self,
        phase_name: str,
        duration_ms: float,
        details: str = "",
    ) -> None:
        """
        Mark a phase as complete.

        Args:
            phase_name: Name of the phase
            duration_ms: Duration in milliseconds
            details: Optional details (e.g., "45 pages rendered")
        """
        phase_key = phase_name.lower()
        if phase_key in self._phases:
            self._phases[phase_key] = PhaseInfo(
                name=phase_key,
                status="complete",
                duration_ms=duration_ms,
                details=details,
            )

        # Accumulate elapsed time
        self.elapsed_ms += duration_ms

        self._rebuild_phase_plan()
        self._update_details(f"✓ {phase_name.title()}: {details}" if details else "")
        self._update_elapsed()

    def fail_phase(self, phase_name: str, error: str = "") -> None:
        """
        Mark a phase as failed.

        Args:
            phase_name: Name of the phase
            error: Optional error message
        """
        phase_key = phase_name.lower()
        if phase_key in self._phases:
            self._phases[phase_key] = PhaseInfo(
                name=phase_key,
                status="error",
                details=error,
            )

        self._rebuild_phase_plan()
        self._update_details(f"✗ {phase_name.title()}: {error}" if error else "")

    def _rebuild_phase_plan(self) -> None:
        """Rebuild the phase plan widget."""
        if self._phase_plan is None:
            return

        phases = []
        for name in self.PHASE_NAMES:
            info = self._phases.get(name, PhaseInfo(name=name, status="pending"))
            duration = int(info.duration_ms) if info.duration_ms else None
            phases.append(
                BuildPhase(
                    name=name.title(),
                    status=info.status,
                    duration_ms=duration,
                )
            )

        self._phase_plan.phases = phases

    def _update_details(self, text: str) -> None:
        """Update the details display."""
        try:
            details = self.query_one("#phase-details", Static)
            details.update(text)
        except Exception:
            pass  # Widget may not be mounted yet during compose

    def _update_elapsed(self) -> None:
        """Update the elapsed time display."""
        try:
            elapsed = self.query_one("#elapsed-time", Static)
            if self.elapsed_ms > 0:
                if self.elapsed_ms < 1000:
                    elapsed.update(f"Elapsed: {self.elapsed_ms:.0f}ms")
                else:
                    elapsed.update(f"Elapsed: {self.elapsed_ms / 1000:.1f}s")
            else:
                elapsed.update("")
        except Exception:
            pass  # Widget may not be mounted yet during compose

    @property
    def is_complete(self) -> bool:
        """Check if all phases are complete."""
        return all(
            self._phases.get(name, PhaseInfo(name=name, status="pending")).status == "complete"
            for name in self.PHASE_NAMES
        )

    @property
    def has_errors(self) -> bool:
        """Check if any phase has errors."""
        return any(
            self._phases.get(name, PhaseInfo(name=name, status="pending")).status == "error"
            for name in self.PHASE_NAMES
        )
