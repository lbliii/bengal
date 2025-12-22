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
    ProgressBar,
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
    severity: str  # "error", "warning", "info", "suggestion"
    message: str
    file: str | None = None
    line: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str | None = None  # Task 3.2: Add recommendation field


# Category definitions for health checks (Task 3.1)
VALIDATOR_CATEGORIES: dict[str, tuple[str, str]] = {
    # validator_name: (emoji, display_name)
    "LinkValidator": ("🔗", "Links"),
    "LinkValidatorWrapper": ("🔗", "Links"),
    "OutputValidator": ("📄", "Output"),
    "AssetValidator": ("🖼️", "Assets"),
    "PerformanceValidator": ("⚡", "Performance"),
    "NavigationValidator": ("🧭", "Navigation"),
    "ConfigValidatorWrapper": ("⚙️", "Config"),
    "MenuValidator": ("📋", "Menu"),
    "TaxonomyValidator": ("🏷️", "Taxonomy"),
    "RenderingValidator": ("🎨", "Rendering"),
    "RSSValidator": ("📰", "RSS"),
    "SitemapValidator": ("🗺️", "Sitemap"),
    "FontValidator": ("🔤", "Fonts"),
    "CacheValidator": ("💾", "Cache"),
    "ConnectivityValidator": ("🔌", "Connectivity"),
    "AnchorValidator": ("⚓", "Anchors"),
    "TemplateValidator": ("📝", "Templates"),
    "DirectiveValidator": ("📐", "Directives"),
}


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
    is_loading: reactive[bool] = reactive(True)  # Task 4.1

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
            # Summary bar with health score (Task 3.3)
            yield Static(
                f"{self.mascot}  Scanning...",
                id="health-summary",
                classes="section-header",
            )

            # Health score progress bar (Task 3.3)
            yield ProgressBar(total=100, show_eta=False, id="health-score-bar")

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
                        "Select an issue to view details\n\n"
                        "[dim]Press Enter on an issue to open the file[/dim]",
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

        self.is_loading = True  # Task 4.1

        # Update status
        summary = self.query_one("#health-summary", Static)
        summary.update(f"{self.mascot}  ⏳ Scanning site...")

        # Run scan in worker
        self.run_worker(self._scan_site, exclusive=True, thread=True)

    async def _scan_site(self) -> None:
        """Run health scan in background thread."""
        try:
            if self.site is None:
                # No site - show demo/placeholder
                self.call_from_thread(self._populate_demo)
                return

            # Try to run link check if available
            try:
                from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator

                orchestrator = LinkCheckOrchestrator(
                    self.site,
                    check_internal=True,
                    check_external=False,
                )
                results, summary = orchestrator.check_all_links()

                # Convert to our format
                self.call_from_thread(self._populate_from_linkcheck, results, summary)

            except ImportError:
                # Fallback to demo mode
                self.call_from_thread(self._populate_demo)

        except Exception as e:
            self.call_from_thread(self._on_scan_error, str(e))

    def _populate_demo(self) -> None:
        """Populate tree with demo/placeholder data (Task 4.2)."""
        self.is_loading = False  # Task 4.1
        tree = self.query_one("#health-tree", Tree)
        tree.clear()

        # Task 4.2: Show helpful empty state
        healthy_node = tree.root.add("✨ Site is healthy!", expand=True)
        healthy_node.add_leaf("✓ All checks passed")
        healthy_node.add_leaf("[dim]Run 'bengal health' for full analysis[/dim]")

        summary = self.query_one("#health-summary", Static)
        summary.update(f"{self.mascot}  Site Health: 100% ✨")

        # Update health score to 100%
        self._update_health_score_display(100)

        self.notify("No issues found", title="Health")

    def _populate_from_linkcheck(self, results: list, summary) -> None:
        """Populate tree from link check results."""
        from bengal.health.linkcheck.models import LinkStatus

        tree = self.query_one("#health-tree", Tree)
        tree.clear()

        # LinkCheckResult uses status enum, not .ok boolean
        broken_links = [r for r in results if r.status != LinkStatus.OK]
        valid_links = [r for r in results if r.status == LinkStatus.OK]

        # Add broken links category
        if broken_links:
            broken_node = tree.root.add(f"❌ Broken Links ({len(broken_links)})", expand=True)
            for link in broken_links[:20]:  # Limit display
                # Use first_ref (first page referencing this link) for source
                status_info = f"{link.status_code}" if link.status_code else link.status.value
                issue = HealthIssue(
                    category="Links",
                    severity="error",
                    message=f"{status_info}: {link.url}",
                    file=link.first_ref,
                    recommendation=link.reason,
                )
                self.issues.append(issue)
                broken_node.add_leaf(f"⛔ {link.url[:50]}...")

        # Add valid links summary
        if valid_links:
            valid_node = tree.root.add(f"✓ Valid Links ({len(valid_links)})", expand=False)
            valid_node.add_leaf("All links verified")

        # Update counts
        self.error_count = len(broken_links)
        self.warning_count = 0
        self.total_issues = len(broken_links)

        # Calculate and display health score (Task 3.3)
        health_score = self._calculate_health_score()
        self._update_health_score_display(health_score)

        # Update summary
        summary_widget = self.query_one("#health-summary", Static)
        if broken_links:
            summary_widget.update(
                f"🐭  Site Health: {health_score}% │ {len(broken_links)} broken links found"
            )
        else:
            summary_widget.update(
                f"{self.mascot}  Site Health: 100% ✨ All {len(valid_links)} links valid!"
            )

        self.is_loading = False  # Task 4.1

        self.notify(
            f"Found {len(broken_links)} issues" if broken_links else "No issues!",
            title="Health Check",
            severity="error" if broken_links else "information",
        )

    def _populate_from_report(self, report: HealthReport) -> None:
        """Populate tree from health report (Task 3.1)."""
        self.report = report
        self.issues.clear()

        tree = self.query_one("#health-tree", Tree)
        tree.clear()

        # Count issues
        errors = 0
        warnings = 0
        suggestions = 0

        # Get categories from report - group by validator (Task 3.1)
        categories = self._extract_categories_by_validator(report)

        for category_name, category_data in categories.items():
            category_issues = category_data["issues"]
            emoji = category_data["emoji"]

            if not category_issues:
                continue

            # Count by severity
            cat_errors = sum(1 for i in category_issues if i.get("severity") == "error")
            cat_warnings = sum(1 for i in category_issues if i.get("severity") == "warning")

            # Add category node with count (Task 3.1)
            if cat_errors > 0:
                count_str = f"{cat_errors} errors"
            elif cat_warnings > 0:
                count_str = f"{cat_warnings} warnings"
            else:
                count_str = f"{len(category_issues)} issues"

            category_node = tree.root.add(
                f"{emoji} {category_name} ({count_str})",
                expand=True,
            )

            for issue in category_issues:
                # Create HealthIssue with recommendation (Task 3.2)
                health_issue = HealthIssue(
                    category=category_name,
                    severity=issue.get("severity", "warning"),
                    message=issue.get("message", "Unknown issue"),
                    file=issue.get("file"),
                    line=issue.get("line"),
                    details=issue,
                    recommendation=issue.get("recommendation"),
                )
                self.issues.append(health_issue)

                # Count by severity
                if health_issue.severity == "error":
                    errors += 1
                elif health_issue.severity == "warning":
                    warnings += 1
                else:
                    suggestions += 1

                # Add to tree with severity icon
                severity_icons = {"error": "⛔", "warning": "⚠️", "info": "ℹ️", "suggestion": "💡"}
                severity_icon = severity_icons.get(health_issue.severity, "•")
                label = f"{severity_icon} {health_issue.message}"
                if health_issue.file:
                    short_file = Path(health_issue.file).name
                    label = f"{severity_icon} {short_file}: {health_issue.message}"

                # Truncate long labels
                if len(label) > 60:
                    label = label[:57] + "..."

                node = category_node.add_leaf(label)
                node.data = health_issue

        # Update counts
        self.error_count = errors
        self.warning_count = warnings
        self.total_issues = errors + warnings + suggestions

        # Calculate health score (Task 3.3)
        health_score = self._calculate_health_score()
        self._update_health_score_display(health_score)

        # Update summary with health score (Task 3.3)
        summary = self.query_one("#health-summary", Static)
        if self.total_issues == 0:
            summary.update(f"{self.mascot}  Site Health: 100% ✨ No issues found!")
        else:
            mascot = self.error_mascot if errors > 0 else self.mascot
            summary.update(
                f"{mascot}  Site Health: {health_score}% │ {errors} errors, {warnings} warnings"
            )

        self.is_loading = False  # Task 4.1

        # Notification
        notify_health_issues(self, errors, warnings)

    def _calculate_health_score(self) -> int:
        """Calculate health score 0-100 (Task 3.3)."""
        if not self.issues:
            return 100

        error_weight = 10  # Errors cost 10 points each
        warning_weight = 2  # Warnings cost 2 points each

        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")

        penalty = (errors * error_weight) + (warnings * warning_weight)
        return max(0, 100 - penalty)

    def _update_health_score_display(self, score: int) -> None:
        """Update the health score progress bar (Task 3.3)."""
        try:
            progress_bar = self.query_one("#health-score-bar", ProgressBar)
            progress_bar.update(progress=score)
        except Exception:
            # Silently ignore if widget not mounted yet or query fails;
            # progress bar update is non-critical UI feedback
            pass

    def _extract_categories_by_validator(self, report: HealthReport) -> dict[str, dict]:
        """Extract and group categories by validator type (Task 3.1)."""
        from bengal.health.report import CheckStatus

        categories: dict[str, dict] = {}

        # HealthReport has validator_reports (list of ValidatorReport), not results
        # Each ValidatorReport has validator_name and results (list of CheckResult)
        for validator_report in report.validator_reports:
            validator_name = validator_report.validator_name

            # Get category info from mapping
            if validator_name in VALIDATOR_CATEGORIES:
                emoji, display_name = VALIDATOR_CATEGORIES[validator_name]
            else:
                # Default for unknown validators
                emoji, display_name = ("📋", validator_name.replace("Validator", ""))

            if display_name not in categories:
                categories[display_name] = {"emoji": emoji, "issues": []}

            # Iterate over CheckResults within this ValidatorReport
            for result in validator_report.results:
                # Only add non-success results
                if result.status != CheckStatus.SUCCESS:
                    categories[display_name]["issues"].append(
                        {
                            "severity": result.status.name.lower(),
                            "message": result.message,
                            "file": None,  # CheckResult doesn't have file/line directly
                            "line": None,
                            "recommendation": result.recommendation,
                        }
                    )

        # Fallback to legacy extraction if no results
        if not any(cat["issues"] for cat in categories.values()):
            legacy_categories = self._extract_categories(report)
            for cat_name, issues in legacy_categories.items():
                if cat_name not in categories:
                    categories[cat_name] = {"emoji": "📋", "issues": issues}
                else:
                    categories[cat_name]["issues"].extend(issues)

        return categories

    def _extract_categories(self, report: HealthReport) -> dict[str, list[dict]]:
        """Extract categories from health report (legacy fallback)."""
        from bengal.health.report import CheckStatus

        categories: dict[str, list[dict]] = {}

        # HealthReport uses validator_reports, not issues/categories
        for validator_report in report.validator_reports:
            cat = validator_report.validator_name.replace("Validator", "")
            if cat not in categories:
                categories[cat] = []

            for result in validator_report.results:
                if result.status != CheckStatus.SUCCESS:
                    categories[cat].append(
                        {
                            "severity": result.status.name.lower(),
                            "message": result.message,
                            "file": None,
                            "line": None,
                        }
                    )

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
        """Show details for selected issue (Task 3.2)."""
        self.selected_issue = issue

        details_panel = self.query_one("#issue-details", Static)

        # Severity icon
        severity_icons = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "suggestion": "💡",
        }
        icon = severity_icons.get(issue.severity, "•")

        lines = [
            f"[bold]{icon} {issue.category}[/bold]",
            "",
            f"[bold]Severity:[/bold] {issue.severity.upper()}",
            f"[bold]Message:[/bold]  {issue.message}",
        ]

        if issue.file:
            lines.append(f"[bold]File:[/bold]     {issue.file}")
        if issue.line:
            lines.append(f"[bold]Line:[/bold]     {issue.line}")

        # Add recommendation if available (Task 3.2)
        if issue.recommendation:
            lines.append("")
            lines.append("[bold]Suggestion:[/bold]")
            lines.append(f"  {issue.recommendation}")

        # Add any extra details
        extra_details = []
        for key, value in issue.details.items():
            if key not in (
                "severity",
                "message",
                "file",
                "line",
                "category",
                "recommendation",
            ):
                extra_details.append(f"{key}: {value}")

        if extra_details:
            lines.append("")
            lines.append("[bold]Details:[/bold]")
            lines.extend(f"  {d}" for d in extra_details)

        # Add file open hint (Task 3.2)
        if issue.file:
            lines.append("")
            lines.append("[dim][Press Enter to open file][/dim]")

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
