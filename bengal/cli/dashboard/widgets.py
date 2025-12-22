"""
Widget imports and custom widgets for Bengal dashboards.

Re-exports commonly used Textual widgets and provides
Bengal-specific widget customizations.

DEPRECATION: This module is now a compatibility shim.
Import directly from bengal.cli.dashboard.widgets package instead.

Usage:
    from bengal.cli.dashboard.widgets import (
        Header, Footer, ProgressBar, DataTable, Log, Tree,
        BengalThrobber, BuildFlash, BuildPhasePlan, QuickAction
    )
"""

from __future__ import annotations

# Re-export everything from the widgets package
from bengal.cli.dashboard.widgets import (
    # Custom Bengal Widgets
    BengalThrobber,
    BengalThrobberVisual,
    BuildFlash,
    BuildPhase,
    BuildPhasePlan,
    # Standard Widgets
    Button,
    Center,
    Container,
    DataTable,
    Footer,
    Grid,
    Header,
    Horizontal,
    HorizontalScroll,
    Label,
    ListItem,
    ListView,
    Log,
    ProgressBar,
    QuickAction,
    Rule,
    ScrollableContainer,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
    Tree,
    Vertical,
    VerticalScroll,
)

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
