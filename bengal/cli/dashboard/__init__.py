"""
Bengal Interactive Dashboards.

Textual-based terminal dashboards for Bengal CLI commands:
- BengalBuildDashboard: Live build progress with phase timing
- BengalServeDashboard: Dev server with file watcher status
- BengalHealthDashboard: Health report explorer with tree view
- BengalApp: Unified multi-screen dashboard

Usage:
bengal build --dashboard
bengal serve --dashboard
bengal health --dashboard
bengal --dashboard  # Unified dashboard

Or run directly for development:
python -m bengal.cli.dashboard

Related:
- bengal/themes/tokens.py: Shared design tokens
- bengal.tcss: Textual CSS stylesheet

"""

from __future__ import annotations

# Re-export dashboard classes
from bengal.cli.dashboard.app import BengalApp, run_unified_dashboard
from bengal.cli.dashboard.build import BengalBuildDashboard, run_build_dashboard
from bengal.cli.dashboard.health import BengalHealthDashboard, run_health_dashboard
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
from bengal.cli.dashboard.serve import BengalServeDashboard, run_serve_dashboard

__all__ = [
    # Unified App
    "BengalApp",
    # Individual Dashboards
    "BengalBuildDashboard",
    "BengalHealthDashboard",
    "BengalServeDashboard",
    "BuildComplete",
    # Messages
    "BuildEvent",
    "FileChanged",
    "HealthScanComplete",
    "HealthScanStarted",
    "PhaseComplete",
    "PhaseProgress",
    "PhaseStarted",
    "RebuildTriggered",
    "WatcherStatus",
    "run_build_dashboard",
    "run_health_dashboard",
    "run_serve_dashboard",
    "run_unified_dashboard",
]
