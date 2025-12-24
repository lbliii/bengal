"""
Build Phase Plan Widget.

Visual build phase tracker with status icons.
Inspired by Toad's Plan widget pattern.

Usage:
    from bengal.cli.dashboard.widgets import BuildPhasePlan, BuildPhase

    phases = [
        BuildPhase("Discovery", "complete", 123),
        BuildPhase("Taxonomies", "running"),
        BuildPhase("Rendering", "pending"),
    ]
    plan = BuildPhasePlan()
    plan.phases = phases
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Static


@dataclass(frozen=True)
class BuildPhase:
    """
    Represents a build phase with status.

    Attributes:
        name: Phase name (e.g., "Discovery", "Rendering")
        status: Phase status (pending, running, complete, error)
        duration_ms: Duration in milliseconds (None if not complete)
    """

    name: str
    status: str  # pending, running, complete, error
    duration_ms: int | None = None


class BuildPhasePlan(Grid):
    """
    Visual build phase tracker.

    Displays build phases in a grid with status icons, names, and durations.
    Automatically recomposes when phases are updated.

    Status icons:
        ○ pending (gray)
        ● running (orange, animated)
        ✓ complete (green)
        ✗ error (red)

    Example:
        plan = BuildPhasePlan(id="build-phases")
        plan.phases = [
            BuildPhase("Discovery", "complete", 45),
            BuildPhase("Taxonomies", "running"),
            BuildPhase("Rendering", "pending"),
        ]
    """

    DEFAULT_CSS = """
    BuildPhasePlan {
        grid-size: 3;
        grid-columns: auto 1fr auto;
        height: auto;
        max-height: 10;
    }
    BuildPhasePlan .phase-status {
        width: 3;
        text-align: center;
    }
    BuildPhasePlan .phase-name {
        padding: 0 1;
    }
    BuildPhasePlan .phase-time {
        text-align: right;
        width: 10;
    }
    BuildPhasePlan .status-pending {
        color: #757575;
    }
    BuildPhasePlan .status-running {
        color: #FF9D00;
    }
    BuildPhasePlan .status-complete {
        color: #2ECC71;
    }
    BuildPhasePlan .status-error {
        color: #E74C3C;
    }
    """

    STATUS_ICONS: dict[str, str] = {
        "pending": "○",
        "running": "●",
        "complete": "✓",
        "error": "✗",
    }

    phases: reactive[list[BuildPhase]] = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        """Compose the phase grid."""
        for phase in self.phases:
            icon = self.STATUS_ICONS.get(phase.status, "?")
            status_class = f"status-{phase.status}"

            yield Static(
                icon,
                classes=f"phase-status {status_class}",
            )
            yield Static(
                phase.name,
                classes=f"phase-name {status_class}",
            )
            yield Static(
                f"{phase.duration_ms}ms" if phase.duration_ms is not None else "",
                classes=f"phase-time {status_class}",
            )

    def update_phase(self, name: str, status: str, duration_ms: int | None = None) -> None:
        """
        Update a specific phase's status.

        Args:
            name: Phase name to update
            status: New status (pending, running, complete, error)
            duration_ms: Duration in milliseconds (optional)
        """
        new_phases = []
        for phase in self.phases:
            if phase.name == name:
                new_phases.append(BuildPhase(name, status, duration_ms))
            else:
                new_phases.append(phase)
        self.phases = new_phases

    def set_default_phases(self) -> None:
        """Set default Bengal build phases."""
        self.phases = [
            BuildPhase("Discovery", "pending"),
            BuildPhase("Taxonomies", "pending"),
            BuildPhase("Rendering", "pending"),
            BuildPhase("Assets", "pending"),
            BuildPhase("Postprocess", "pending"),
        ]
