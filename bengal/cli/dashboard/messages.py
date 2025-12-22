"""
Custom Textual messages for Bengal dashboards.

Messages enable communication between dashboard components:
- Build events (phase start/complete, build complete)
- File watcher events (file changed, rebuild triggered)
- Health events (issue found, scan complete)

These messages are posted by background workers and handled
by the main Textual app to update the UI reactively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.message import Message

# === Build Messages ===


class BuildEvent(Message):
    """Base class for all build-related events."""

    pass


@dataclass
class PhaseStarted(BuildEvent):
    """
    A build phase has started.

    Posted by the build worker when a phase begins.
    Dashboard updates progress bar and phase table.
    """

    name: str
    total_items: int | None = None


@dataclass
class PhaseProgress(BuildEvent):
    """
    Progress update within a build phase.

    Posted periodically during rendering/asset processing.
    Dashboard updates progress bar percentage.
    """

    name: str
    current: int
    total: int
    details: str | None = None


@dataclass
class PhaseComplete(BuildEvent):
    """
    A build phase has completed.

    Posted by the build worker when a phase finishes.
    Dashboard updates phase table with duration and status.
    """

    name: str
    duration_ms: float
    details: str | None = None
    error: str | None = None


@dataclass
class BuildComplete(BuildEvent):
    """
    The entire build has completed.

    Posted by the build worker when all phases finish.
    Dashboard shows completion toast and final stats.
    """

    success: bool
    duration_ms: float
    stats: dict[str, Any] | None = None
    error: str | None = None


# === File Watcher Messages ===


@dataclass
class FileChanged(Message):
    """
    A watched file has changed.

    Posted by the file watcher when content/assets change.
    Dashboard logs the change and triggers rebuild.
    """

    path: str
    change_type: str  # "created", "modified", "deleted"


@dataclass
class RebuildTriggered(Message):
    """
    A rebuild has been triggered by file changes.

    Posted when the watcher initiates a rebuild.
    Dashboard starts showing build progress.
    """

    changed_files: list[str]


@dataclass
class WatcherStatus(Message):
    """
    File watcher status update.

    Posted periodically with watcher statistics.
    Dashboard updates watcher status indicator.
    """

    watching: bool
    watched_files: int
    last_event_time: float | None = None


# === Health Messages ===


@dataclass
class HealthScanStarted(Message):
    """Health scan has started."""

    categories: list[str]


@dataclass
class HealthIssueFound(Message):
    """A health issue was found during scanning."""

    category: str
    severity: str  # "error", "warning", "info"
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class HealthScanComplete(Message):
    """Health scan has completed."""

    summary: dict[str, Any]
