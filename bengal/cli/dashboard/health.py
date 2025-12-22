"""
Health Dashboard for Bengal.

Interactive Textual dashboard for `bengal health --dashboard` that shows:
- Tree view of health issues by category
- Details panel for selected issue
- Summary statistics
- Keyboard shortcuts (q=quit, r=rescan, enter=view details)

Usage:
    bengal health --dashboard

The dashboard displays health report data in an interactive tree
that can be navigated with arrow keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Static,
    Tree,
)

from bengal.cli.dashboard.base import BengalDashboard
from bengal.cli.dashboard.notifications import notify_health_issues

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.health.report import HealthReport


@dataclass
class HealthIssue:
    """A single health issue."""

    category: str
    severity: str  # "error", "warning", "info"
    message: str
    file: str | None = None
    line: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


class BengalHealthDashboard(BengalDashboard):
    """
    Interactive health dashboard with tree explorer.

    Shows:
    - Header with Bengal branding
    - Summary bar with issue counts
    - Tree view of issues by category
    - Details panel for selected issue
    - Footer with keyboard shortcuts

    Bindings:
        q: Quit
        r: Rescan
        enter: View details
        ?: Help
    """

    TITLE: ClassVar[str] = "Bengal Health"
    SUB_TITLE: ClassVar[str] = "Site Health Check"

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalDashboard.BINDINGS,
        Binding("r", "rescan", "Rescan", show=True),
        Binding("enter", "view_details", "Details"),
    ]

    # Reactive state
    total_issues: reactive[int] = reactive(0)
    error_count: reactive[int] = reactive(0)
    warning_count: reactive[int] = reactive(0)
    selected_issue: reactive[HealthIssue | None] = reactive(None)

    def __init__(
        self,
        site: Site | None = None,
        report: HealthReport | None = None,
        **kwargs: Any,
    ):
        """
        Initialize health dashboard.

        Args:
            site: Site instance for rescanning
            report: Pre-computed health report (optional)
            **kwargs: Additional options
        """
        super().__init__()
        self.site = site
        self.report = report
        self.issues: list[HealthIssue] = []

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()

        with Vertical(id="main-content"):
            # Summary bar
            yield Static(
                f"{self.mascot}  Scanning...",
                id="health-summary",
                classes="section-header",
            )

            # Main content: tree + details side by side
            with Horizontal(classes="health-layout"):
                # Issue tree (left side)
                with Vertical(id="tree-container"):
                    yield Static("Issues:", classes="section-header")
                    yield Tree("Health Report", id="health-tree")

                # Details panel (right side)
                with Vertical(id="details-container", classes="panel"):
                    yield Static("Details:", classes="panel-title")
                    yield Static(
                        "Select an issue to view details",
                        id="issue-details",
                    )

        yield Footer()

    def on_mount(self) -> None:
        """Set up widgets when dashboard mounts."""
        # Initialize tree
        tree = self.query_one("#health-tree", Tree)
        tree.show_root = False

        # If we have a report, populate immediately
        if self.report:
            self._populate_from_report(self.report)
        elif self.site:
            # Run health scan
            self._run_scan()

    def _run_scan(self) -> None:
        """Run health scan in background."""
        if not self.site:
            return

        # Update status
        summary = self.query_one("#health-summary", Static)
        summary.update(f"{self.mascot}  Scanning site...")

        # Run scan in worker
        self.run_worker(self._scan_site, exclusive=True, thread=True)

    async def _scan_site(self) -> None:
        """Run health scan in background thread."""
        from bengal.health.report import HealthReporter

        try:
            # Create reporter and run scan
            reporter = HealthReporter(self.site)
            report = reporter.generate_report()

            # Update UI from main thread
            self.call_from_thread(self._populate_from_report, report)

        except Exception as e:
            self.call_from_thread(self._on_scan_error, str(e))

    def _populate_from_report(self, report: HealthReport) -> None:
        """Populate tree from health report."""
        self.report = report
        self.issues.clear()

        tree = self.query_one("#health-tree", Tree)
        tree.clear()

        # Count issues
        errors = 0
        warnings = 0

        # Get categories from report
        # The report structure varies - adapt to actual format
        categories = self._extract_categories(report)

        for category_name, category_issues in categories.items():
            if not category_issues:
                continue

            # Add category node
            category_node = tree.root.add(
                f"{category_name} ({len(category_issues)})",
                expand=True,
            )

            for issue in category_issues:
                # Create HealthIssue
                health_issue = HealthIssue(
                    category=category_name,
                    severity=issue.get("severity", "warning"),
                    message=issue.get("message", "Unknown issue"),
                    file=issue.get("file"),
                    line=issue.get("line"),
                    details=issue,
                )
                self.issues.append(health_issue)

                # Count by severity
                if health_issue.severity == "error":
                    errors += 1
                else:
                    warnings += 1

                # Add to tree
                severity_icon = "✗" if health_issue.severity == "error" else "!"
                label = f"{severity_icon} {health_issue.message}"
                if health_issue.file:
                    short_file = Path(health_issue.file).name
                    label = f"{severity_icon} {short_file}: {health_issue.message}"

                node = category_node.add_leaf(label)
                node.data = health_issue

        # Update counts
        self.error_count = errors
        self.warning_count = warnings
        self.total_issues = errors + warnings

        # Update summary
        summary = self.query_one("#health-summary", Static)
        if self.total_issues == 0:
            summary.update(f"{self.mascot}  No issues found!")
        else:
            mascot = self.error_mascot if errors > 0 else self.mascot
            summary.update(f"{mascot}  {errors} errors, {warnings} warnings")

        # Notification
        notify_health_issues(self, errors, warnings)

    def _extract_categories(self, report: HealthReport) -> dict[str, list[dict]]:
        """Extract categories from health report."""
        categories: dict[str, list[dict]] = {}

        # Try to extract from report structure
        # This adapts to the actual HealthReport structure
        if hasattr(report, "issues"):
            # Group by category
            for issue in report.issues:
                cat = getattr(issue, "category", "Other")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(
                    {
                        "severity": getattr(issue, "severity", "warning"),
                        "message": getattr(issue, "message", str(issue)),
                        "file": getattr(issue, "file", None),
                        "line": getattr(issue, "line", None),
                    }
                )
        elif hasattr(report, "categories"):
            # Already categorized
            for cat_name, cat_data in report.categories.items():
                if hasattr(cat_data, "issues"):
                    categories[cat_name] = [
                        {
                            "severity": getattr(i, "severity", "warning"),
                            "message": getattr(i, "message", str(i)),
                            "file": getattr(i, "file", None),
                            "line": getattr(i, "line", None),
                        }
                        for i in cat_data.issues
                    ]

        return categories

    def _on_scan_error(self, error: str) -> None:
        """Handle scan error."""
        summary = self.query_one("#health-summary", Static)
        summary.update(f"{self.error_mascot}  Scan failed: {error}")

        details = self.query_one("#issue-details", Static)
        details.update(f"Error: {error}")

    # === Tree Events ===

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if node.data and isinstance(node.data, HealthIssue):
            self._show_issue_details(node.data)

    def _show_issue_details(self, issue: HealthIssue) -> None:
        """Show details for selected issue."""
        self.selected_issue = issue

        details_panel = self.query_one("#issue-details", Static)

        lines = [
            f"[bold]{issue.category}[/bold]",
            "",
            f"Severity: {issue.severity}",
            f"Message: {issue.message}",
        ]

        if issue.file:
            lines.append(f"File: {issue.file}")
        if issue.line:
            lines.append(f"Line: {issue.line}")

        # Add any extra details
        for key, value in issue.details.items():
            if key not in ("severity", "message", "file", "line", "category"):
                lines.append(f"{key}: {value}")

        details_panel.update("\n".join(lines))

    # === Actions ===

    def action_rescan(self) -> None:
        """Rescan the site."""
        if self.site:
            self._run_scan()
        else:
            self.notify("No site loaded", severity="warning")

    def action_view_details(self) -> None:
        """View details for selected issue."""
        if self.selected_issue and self.selected_issue.file:
            # Already showing details, could open in editor
            self.notify(
                f"File: {self.selected_issue.file}",
                title="Issue Location",
            )


def run_health_dashboard(
    site: Site,
    report: HealthReport | None = None,
    **kwargs: Any,
) -> None:
    """
    Run the health dashboard for a site.

    This is the entry point called by `bengal health --dashboard`.

    Args:
        site: Site instance to check
        report: Pre-computed health report (optional)
        **kwargs: Additional options
    """
    app = BengalHealthDashboard(
        site=site,
        report=report,
        **kwargs,
    )
    app.run()
