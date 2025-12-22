"""
Widget imports and custom widgets for Bengal dashboards.

Re-exports commonly used Textual widgets and provides
Bengal-specific widget customizations.

Usage:
    from bengal.cli.dashboard.widgets import (
        Header, Footer, ProgressBar, DataTable, Log, Tree
    )
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
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

__all__ = [
    # Widgets
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
