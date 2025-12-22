"""
Custom widgets for Bengal dashboards.

Provides Bengal-specific widgets inspired by Toad/Dolphie patterns:
- BengalThrobber: Animated loading indicator with Bengal color gradient
- BuildFlash: Inline build status notifications with auto-dismiss
- BuildPhasePlan: Visual build phase tracker with status icons
- QuickAction: Landing screen grid action item

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

# Import custom widgets
from bengal.cli.dashboard.widgets.flash import BuildFlash
from bengal.cli.dashboard.widgets.phase_plan import BuildPhase, BuildPhasePlan
from bengal.cli.dashboard.widgets.quick_action import QuickAction
from bengal.cli.dashboard.widgets.throbber import BengalThrobber, BengalThrobberVisual

__all__ = [
    # Custom Bengal Widgets
    "BengalThrobber",
    "BengalThrobberVisual",
    "BuildFlash",
    "BuildPhase",
    "BuildPhasePlan",
    "QuickAction",
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
