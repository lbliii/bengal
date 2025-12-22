"""
Bengal Interactive Dashboards.

Textual-based terminal dashboards for Bengal CLI commands:
- BengalBuildDashboard: Live build progress with phase timing
- BengalServeDashboard: Dev server with file watcher status
- BengalHealthDashboard: Health report explorer with tree view

Usage:
    bengal build --dashboard
    bengal serve --dashboard
    bengal health --dashboard

Or launch the unified dashboard:
    bengal --dashboard

Related:
    - bengal/themes/tokens.py: Shared design tokens
    - bengal.tcss: Textual CSS stylesheet
"""

from __future__ import annotations

# Re-export dashboard classes
from bengal.cli.dashboard.messages import (
    BuildComplete,
    BuildEvent,
    FileChanged,
    HealthScanComplete,
    HealthScanStarted,
    PhaseComplete,
    PhaseProgress,
    PhaseStarted,
    RebuildTriggered,
    WatcherStatus,
)

__all__ = [
    # Messages
    "BuildEvent",
    "PhaseStarted",
    "PhaseProgress",
    "PhaseComplete",
    "BuildComplete",
    "FileChanged",
    "RebuildTriggered",
    "WatcherStatus",
    "HealthScanStarted",
    "HealthScanComplete",
]
