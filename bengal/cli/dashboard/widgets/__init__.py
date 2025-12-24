"""
Custom widgets for Bengal dashboards.

Provides Bengal-specific widgets inspired by Toad/Dolphie patterns:
- BengalThrobber: Animated loading indicator with Bengal color gradient
- BuildFlash: Inline build status notifications with auto-dismiss
- BuildPhasePlan: Visual build phase tracker with status icons
- QuickAction: Landing screen grid action item

Dashboard API Integration widgets (RFC: rfc-dashboard-api-integration):
- ContentBrowser: Tree view for browsing site pages and sections
- AssetExplorer: Tabbed asset browser grouped by type
- TaxonomyExplorer: Hierarchical taxonomy drill-down
- PhaseProgress: Real-time streaming build phase display
- FileWatcherLog: File change stream display
- RequestLog: HTTP request logging display

Re-exports commonly used Textual widgets for convenience.
"""

from __future__ import annotations

# Re-export containers
from textual.containers import (
    Center,
    Container,
    Grid,
    Horizontal,
    HorizontalScroll,
    ScrollableContainer,
    Vertical,
    VerticalScroll,
)

# Re-export Textual widgets for convenience
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Log,
    ProgressBar,
    Rule,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

# Dashboard API Integration widgets (RFC: rfc-dashboard-api-integration)
from bengal.cli.dashboard.widgets.asset_explorer import AssetExplorer
from bengal.cli.dashboard.widgets.content_browser import ContentBrowser
from bengal.cli.dashboard.widgets.file_watcher_log import FileWatcherLog

# Import custom widgets
from bengal.cli.dashboard.widgets.flash import BuildFlash
from bengal.cli.dashboard.widgets.phase_plan import BuildPhase, BuildPhasePlan
from bengal.cli.dashboard.widgets.phase_progress import PhaseProgress
from bengal.cli.dashboard.widgets.quick_action import QuickAction
from bengal.cli.dashboard.widgets.request_log import RequestLog
from bengal.cli.dashboard.widgets.taxonomy_explorer import TaxonomyExplorer
from bengal.cli.dashboard.widgets.throbber import BengalThrobber, BengalThrobberVisual

__all__ = [
    # Custom Bengal Widgets
    "BengalThrobber",
    "BengalThrobberVisual",
    "BuildFlash",
    "BuildPhase",
    "BuildPhasePlan",
    "QuickAction",
    # Dashboard API Integration (RFC: rfc-dashboard-api-integration)
    "AssetExplorer",
    "ContentBrowser",
    "FileWatcherLog",
    "PhaseProgress",
    "RequestLog",
    "TaxonomyExplorer",
    # Standard Widgets
    "Header",
    "Footer",
    "ProgressBar",
    "DataTable",
    "Log",
    "Tree",
    "Static",
    "Label",
    "Button",
    "Rule",
    "TabbedContent",
    "TabPane",
    "ListView",
    "ListItem",
    "Sparkline",
    # Containers
    "Container",
    "Vertical",
    "Horizontal",
    "Grid",
    "Center",
    "ScrollableContainer",
    "VerticalScroll",
    "HorizontalScroll",
]
