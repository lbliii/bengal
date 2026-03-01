"""
Screen classes for Bengal unified dashboard.

Each screen represents a mode of the unified dashboard:
- LandingScreen: Site overview and quick actions
- BuildScreen: Build progress and phase timing
- ServeScreen: Dev server with file watching
- HealthScreen: Site health explorer

Screens are navigated via number keys (0, 1, 2, 3) or command palette.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Log, Static

from bengal.protocols.capabilities import has_action_rebuild, has_config_changed_signal

if TYPE_CHECKING:
    from bengal.core.site import Site


class BengalScreen(Screen):
    """
    Base screen for Bengal unified dashboard.

    All screens share common bindings and styling.
    Subscribes to config_changed_signal for reactive updates.

    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("0", "goto_landing", "Home", show=False),
        Binding("1", "goto_build", "Build", show=True),
        Binding("2", "goto_serve", "Serve", show=True),
        Binding("3", "goto_health", "Health", show=True),
        Binding("q", "quit", "Quit"),
        Binding("?", "toggle_help", "Help"),
    ]

    def on_mount(self) -> None:
        """Subscribe to config changes when mounted."""
        # Subscribe to config signal if app supports it
        if has_config_changed_signal(self.app):
            self.app.config_changed_signal.subscribe(self, self.on_config_changed)

    def on_config_changed(self, data: tuple[str, object]) -> None:
        """
        Handle config changes from app.

        Args:
            data: Tuple of (key, value) for the changed config
        """
        _key, _value = data
        # Subclasses can override to handle specific config changes

    def action_goto_landing(self) -> None:
        """Switch to landing screen."""
        self.app.switch_screen("landing")

    def action_goto_build(self) -> None:
        """Switch to build screen."""
        self.app.switch_screen("build")

    def action_goto_serve(self) -> None:
        """Switch to serve screen."""
        self.app.switch_screen("serve")

    def action_goto_health(self) -> None:
        """Switch to health screen."""
        self.app.switch_screen("health")

    def action_toggle_help(self) -> None:
        """Toggle help screen."""
        self.app.push_screen("help")


class LandingScreen(BengalScreen):
    """
    Landing screen with site overview and quick actions.

    Shows:
    - Bengal branding with version
    - Site summary (pages, assets, last build)
    - Quick action grid (Build, Serve, Health)
    - Recent activity log

    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("b", "goto_build", "Build", show=False),
        Binding("s", "goto_serve", "Serve", show=False),
        Binding("h", "goto_health", "Health", show=False),
    ]

    def __init__(self, site: Site | None = None, **kwargs) -> None:
        """Initialize landing screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose landing screen layout."""
        from bengal.cli.dashboard.widgets import Grid, QuickAction

        yield Header()

        with Vertical(id="main-content"):
            # Branding section
            with Vertical(id="landing-header"):
                yield Static(self._get_branding(), id="branding")
                yield Static(self._get_site_summary(), id="site-summary")

            # Quick action grid
            with Grid(id="quick-actions"):
                yield QuickAction(
                    "🔨",
                    "Build Site",
                    "Run a full site build",
                    id="action-build",
                )
                yield QuickAction(
                    "🌐",
                    "Dev Server",
                    "Start development server",
                    id="action-serve",
                )
                yield QuickAction(
                    "🏥",
                    "Health Check",
                    "Run site validators",
                    id="action-health",
                )

            # Activity log
            with Vertical(id="activity"):
                yield Static("Recent Activity:", classes="section-header")
                yield Log(id="activity-log", auto_scroll=True)

        yield Footer()

    def _get_branding(self) -> str:
        """Get Bengal branding text with version."""
        try:
            from bengal import __version__

            version = __version__
        except ImportError:
            version = "0.1.0"

        # ASCII art Bengal cat
        mascot = getattr(self.app, "mascot", "🐱")

        return f"""
{mascot}  Bengal v{version}
Static Site Generator
"""

    def _get_site_summary(self) -> str:
        """Get rich site summary text."""
        if not self.site:
            return "No site loaded. Run 'bengal new site' to create one."

        title = getattr(self.site, "title", None) or "Untitled Site"
        pages = getattr(self.site, "pages", []) or []
        sections = getattr(self.site, "sections", []) or []
        assets = getattr(self.site, "assets", []) or []
        taxonomies = getattr(self.site, "taxonomies", {}) or {}
        theme = getattr(self.site, "theme", None) or "default"
        baseurl = getattr(self.site, "baseurl", "") or "/"

        # Count taxonomy terms
        taxonomy_info = []
        for tax_name, terms in taxonomies.items():
            if isinstance(terms, dict):
                taxonomy_info.append(f"{len(terms)} {tax_name}")

        # Get recent pages (by date if available)
        recent_pages = []
        for page in pages[:5]:
            page_title = getattr(page, "title", None) or getattr(page, "source_path", "Untitled")
            if hasattr(page_title, "name"):
                page_title = page_title.name
            recent_pages.append(f"  • {page_title[:40]}")

        lines = [
            f"[bold]{title}[/bold]",
            "",
            f"[dim]Theme:[/dim] {theme}  [dim]Base URL:[/dim] {baseurl}",
            "",
            f"📄 [bold]{len(pages)}[/bold] pages  📁 [bold]{len(sections)}[/bold] sections  🎨 [bold]{len(assets)}[/bold] assets",
        ]

        if taxonomy_info:
            lines.append(f"🏷️  {', '.join(taxonomy_info)}")

        if recent_pages:
            lines.append("")
            lines.append("[dim]Recent pages:[/dim]")
            lines.extend(recent_pages[:3])

        return "\n".join(lines)

    def on_mount(self) -> None:
        """Set up landing screen."""
        super().on_mount()

        # Add welcome message to activity log
        log = self.query_one("#activity-log", Log)
        log.write_line("Welcome to Bengal Dashboard!")
        log.write_line("Press 1, 2, or 3 to switch screens")
        log.write_line("Press ? for keyboard shortcuts")

    def on_quick_action_selected(self, message) -> None:
        """Handle quick action selection."""
        action_id = message.action_id
        if action_id == "action-build":
            self.app.switch_screen("build")
        elif action_id == "action-serve":
            self.app.switch_screen("serve")
        elif action_id == "action-health":
            self.app.switch_screen("health")


class BuildScreen(BengalScreen):
    """
    Build screen for the unified dashboard.

    Shows build progress, phase timing, and output log.
    Integrates BengalThrobber for animated loading and BuildFlash for status.

    Dashboard API Integration (RFC: rfc-dashboard-api-integration):
    - PhaseProgress widget with real-time streaming updates
    - Deep BuildStats display after completion

    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("r", "rebuild", "Rebuild"),
        Binding("c", "clear_log", "Clear"),
    ]

    def __init__(self, site: Site | None = None, **kwargs) -> None:
        """Initialize build screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose build screen layout."""
        from textual.widgets import DataTable, ProgressBar

        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash, PhaseProgress

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🔨 Build Dashboard", id="screen-title", classes="section-header")

            # Throbber for animated loading
            yield BengalThrobber(id="build-throbber")

            # Flash notifications
            yield BuildFlash(id="build-flash")

            yield ProgressBar(total=100, show_eta=False, id="build-progress")

            # Phase progress with real-time streaming (RFC: rfc-dashboard-api-integration)
            with Vertical(classes="section", id="build-stats"):
                yield PhaseProgress(id="phase-progress")

            # Build stats table (populated after build completes)
            with Vertical(classes="section", id="stats-section"):
                yield Static("Build Statistics:", classes="section-header")
                yield DataTable(id="stats-table")

            with Vertical(classes="section"):
                yield Static("Output:", classes="section-header")
                yield Log(id="build-log", auto_scroll=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up build screen."""
        super().on_mount()
        from textual.widgets import DataTable

        # Set up stats table (populated after build)
        stats_table = self.query_one("#stats-table", DataTable)
        stats_table.add_columns("Metric", "Value")

        # Log site context
        log = self.query_one("#build-log", Log)
        if self.site:
            title = getattr(self.site, "title", None) or "Untitled"
            pages = getattr(self.site, "pages", []) or []
            sections = getattr(self.site, "sections", []) or []
            assets = getattr(self.site, "assets", []) or []
            output_dir = getattr(self.site, "output_dir", "public")

            log.write_line(f"[bold]Site:[/bold] {title}")
            log.write_line(
                f"  📄 {len(pages)} pages | 📁 {len(sections)} sections | 🎨 {len(assets)} assets"
            )
            log.write_line(f"  Output: {output_dir}/")
            log.write_line("")
            log.write_line("Press [bold]r[/bold] to build")
        else:
            log.write_line("[yellow]No site loaded[/yellow]")
            log.write_line("Run from a Bengal site directory")

    def on_config_changed(self, data: tuple[str, object]) -> None:
        """Handle config changes for UI toggles."""
        key, value = data
        if key == "show_stats":
            self.set_class(not value, "-hide-stats")

    def action_rebuild(self) -> None:
        """Trigger rebuild."""
        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash, PhaseProgress

        if not self.site:
            self.app.notify("No site loaded", title="Error", severity="error")
            return

        # Show throbber and flash
        throbber = self.query_one("#build-throbber", BengalThrobber)
        throbber.active = True

        flash = self.query_one("#build-flash", BuildFlash)
        flash.show_building("Starting build...")

        # Reset phase progress (RFC: rfc-dashboard-api-integration)
        phase_progress = self.query_one("#phase-progress", PhaseProgress)
        phase_progress.reset()

        self.app.notify("Rebuild triggered...", title="Build")

        # Run build in background worker
        self.run_worker(
            self._run_build,
            name="build_worker",
            exclusive=True,
            thread=True,
        )

    async def _run_build(self) -> None:
        """Run the build in a background thread."""
        from time import monotonic

        from textual.widgets import DataTable, ProgressBar

        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash, PhaseProgress
        from bengal.orchestration.build import BuildOrchestrator

        start_time = monotonic()
        log = self.query_one("#build-log", Log)
        phase_progress = self.query_one("#phase-progress", PhaseProgress)
        progress = self.query_one("#build-progress", ProgressBar)
        stats_table = self.query_one("#stats-table", DataTable)

        # Phase progress callbacks for real-time streaming (RFC: rfc-dashboard-api-integration)
        phase_mapping = {
            "discovery": 20,
            "content": 40,
            "assets": 55,
            "rendering": 85,
            "finalization": 95,
            "health": 100,
        }

        def on_phase_start(phase_name: str) -> None:
            """Callback when a build phase starts."""
            self.app.call_from_thread(phase_progress.start_phase, phase_name)
            self.app.call_from_thread(log.write_line, f"→ {phase_name.title()}...")
            pct = phase_mapping.get(phase_name.lower(), 50)
            self.app.call_from_thread(progress.update, progress=pct - 10)

        def on_phase_complete(phase_name: str, duration_ms: float, details: str) -> None:
            """Callback when a build phase completes."""
            self.app.call_from_thread(
                phase_progress.complete_phase, phase_name, duration_ms, details
            )
            self.app.call_from_thread(
                log.write_line, f"  ✓ {phase_name.title()}: {details} ({duration_ms:.0f}ms)"
            )
            pct = phase_mapping.get(phase_name.lower(), 50)
            self.app.call_from_thread(progress.update, progress=pct)

        try:
            self.app.call_from_thread(log.write_line, "Starting build...")

            from bengal.orchestration.build.options import BuildOptions

            orchestrator = BuildOrchestrator(self.site)

            # Run the actual build with streaming callbacks (RFC: rfc-dashboard-api-integration)
            options = BuildOptions(
                force_sequential=False,  # parallel=True
                incremental=False,
                quiet=True,
                on_phase_start=on_phase_start,
                on_phase_complete=on_phase_complete,
            )
            stats = orchestrator.build(options)

            self.app.call_from_thread(progress.update, progress=100)

            duration_ms = (monotonic() - start_time) * 1000

            # Show success
            throbber = self.query_one("#build-throbber", BengalThrobber)
            flash = self.query_one("#build-flash", BuildFlash)
            self.app.call_from_thread(setattr, throbber, "active", False)
            self.app.call_from_thread(flash.show_success, f"Build complete in {duration_ms:.0f}ms")
            self.app.call_from_thread(log.write_line, f"✓ Build complete in {duration_ms:.0f}ms")

            # Extract deep build stats (RFC: rfc-dashboard-api-integration)
            page_count = getattr(stats, "pages_rendered", 0) or len(getattr(self.site, "pages", []))
            asset_count = getattr(stats, "assets_copied", 0) or len(
                getattr(self.site, "assets", [])
            )
            section_count = len(getattr(self.site, "sections", []))
            incremental = getattr(stats, "incremental", False)
            parallel = getattr(stats, "parallel", True)

            # Populate stats table (RFC: rfc-dashboard-api-integration)
            def populate_stats_table() -> None:
                stats_table.clear()
                stats_table.add_row("Pages Rendered", str(page_count))
                stats_table.add_row("Assets Copied", str(asset_count))
                stats_table.add_row("Sections", str(section_count))
                stats_table.add_row("Total Duration", f"{duration_ms:.0f}ms")
                stats_table.add_row("Mode", "Incremental" if incremental else "Full")
                stats_table.add_row("Parallel", "Yes" if parallel else "No")

                # Health report summary if available
                health_report = getattr(stats, "health_report", None)
                if health_report:
                    passed = getattr(health_report, "passed", 0)
                    total = getattr(health_report, "total", 0)
                    stats_table.add_row("Health Checks", f"{passed}/{total} passed")

            self.app.call_from_thread(populate_stats_table)

            self.app.call_from_thread(log.write_line, f"  📄 {page_count} pages rendered")
            self.app.call_from_thread(log.write_line, f"  🎨 {asset_count} assets copied")
            self.app.call_from_thread(log.write_line, f"  📁 {section_count} sections")

            # Show phase timings if available
            if hasattr(stats, "phase_times") and stats.phase_times:
                self.app.call_from_thread(log.write_line, "")
                self.app.call_from_thread(log.write_line, "Phase timings:")
                for phase_name, phase_ms in stats.phase_times.items():
                    self.app.call_from_thread(log.write_line, f"  {phase_name}: {phase_ms:.0f}ms")

            # Show output directory
            output_dir = getattr(self.site, "output_dir", "public")
            self.app.call_from_thread(log.write_line, "")
            self.app.call_from_thread(log.write_line, f"Output: {output_dir}/")

        except Exception as e:
            duration_ms = (monotonic() - start_time) * 1000

            # Show error
            throbber = self.query_one("#build-throbber", BengalThrobber)
            flash = self.query_one("#build-flash", BuildFlash)
            self.app.call_from_thread(setattr, throbber, "active", False)
            self.app.call_from_thread(flash.show_error, str(e))
            self.app.call_from_thread(log.write_line, f"✗ Build failed: {e}")

    def action_clear_log(self) -> None:
        """Clear the build log."""
        log = self.query_one("#build-log", Log)
        log.clear()
        self.app.notify("Log cleared")


class ServeScreen(BengalScreen):
    """
    Serve screen for the unified dashboard.

    Shows dev server status, file changes, and build history.
    Reuses components from BengalServeDashboard.

    Dashboard API Integration (RFC: rfc-dashboard-api-integration):
    - FileWatcherLog for real-time file change display
    - RequestLog for HTTP request logging
    - ContentBrowser for page/section navigation

    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("o", "open_browser", "Open Browser"),
        Binding("r", "force_rebuild", "Rebuild"),
    ]

    def __init__(self, site: Site | None = None, **kwargs):
        """Initialize serve screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose serve screen layout."""
        from textual.widgets import Log, TabbedContent, TabPane

        from bengal.cli.dashboard.widgets import (
            ContentBrowser,
            FileWatcherLog,
            RequestLog,
        )

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🌐 Serve Dashboard", id="screen-title", classes="section-header")
            yield Static(self._get_server_info(), id="server-info")

            with Horizontal(classes="serve-stats"):
                with Vertical(classes="stat-box"):
                    yield Static("📄", classes="stat-icon")
                    yield Static(self._get_page_count(), id="stat-pages")
                with Vertical(classes="stat-box"):
                    yield Static("🎨", classes="stat-icon")
                    yield Static(self._get_asset_count(), id="stat-assets")
                with Vertical(classes="stat-box"):
                    yield Static("⏱️", classes="stat-icon")
                    yield Static("0ms", id="stat-last-build")

            with Horizontal(classes="serve-panels"):
                # Left panel: File watcher log (RFC: rfc-dashboard-api-integration)
                yield FileWatcherLog(id="file-watcher-log")

                # Right panel: Request log (RFC: rfc-dashboard-api-integration)
                yield RequestLog(id="request-log")

            with TabbedContent(id="serve-tabs"):
                with TabPane("Pages", id="pages-tab"):
                    # Content browser (RFC: rfc-dashboard-api-integration)
                    yield ContentBrowser(id="content-browser")
                with TabPane("Changes", id="changes-tab"):
                    yield Log(id="changes-log", auto_scroll=True)
                with TabPane("Errors", id="errors-tab"):
                    yield Log(id="errors-log", auto_scroll=True)

        yield Footer()

    def _get_server_info(self) -> str:
        """Get server info text."""
        url = self._get_full_server_url()
        return f"[bold]Server:[/bold] {url}  [dim]Press 'o' to open in browser[/dim]"

    def _get_full_server_url(self) -> str:
        """Get the full server URL including site baseurl."""
        base_url = (
            getattr(self.app, "server_url", "http://localhost:5173")
            if self.app
            else "http://localhost:5173"
        )
        # Append site's baseurl if it's a path (not absolute URL)
        if self.site:
            site_baseurl = getattr(self.site, "baseurl", "") or ""
            if site_baseurl and not site_baseurl.startswith(("http://", "https://")):
                site_baseurl = site_baseurl.rstrip("/")
                return f"{base_url}{site_baseurl}"
        return base_url

    def _get_page_count(self) -> str:
        """Get page count."""
        if self.site:
            pages = getattr(self.site, "pages", []) or []
            return f"{len(pages)} pages"
        return "- pages"

    def _get_asset_count(self) -> str:
        """Get asset count."""
        if self.site:
            assets = getattr(self.site, "assets", []) or []
            return f"{len(assets)} assets"
        return "- assets"

    def on_mount(self) -> None:
        """Set up serve screen."""
        super().on_mount()

        from bengal.cli.dashboard.widgets import ContentBrowser

        # Populate content browser (RFC: rfc-dashboard-api-integration)
        if self.site:
            content_browser = self.query_one("#content-browser", ContentBrowser)
            content_browser.set_site(self.site)

    def action_open_browser(self) -> None:
        """Open browser to dev server."""
        import webbrowser

        url = self._get_full_server_url()
        webbrowser.open(url)
        self.app.notify(f"Opening {url}", title="Browser")

    def action_force_rebuild(self) -> None:
        """Force rebuild - switch to build screen and trigger rebuild."""
        self.app.push_screen("build")
        # Give the screen time to mount, then trigger rebuild
        self.set_timer(
            0.1,
            lambda: (
                self.app.screen.action_rebuild() if has_action_rebuild(self.app.screen) else None
            ),
        )


class HealthScreen(BengalScreen):
    """
    Health screen for the unified dashboard.

    Shows health issues in a tree with details panel.
    Reuses components from BengalHealthDashboard.

    Dashboard API Integration (RFC: rfc-dashboard-api-integration):
    - ContentBrowser for page/section navigation
    - AssetExplorer for asset inspection
    - TaxonomyExplorer for taxonomy drill-down
    - Deep HealthReport integration with issue categorization

    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("r", "rescan", "Rescan"),
    ]

    def __init__(self, site: Site | None = None, **kwargs):
        """Initialize health screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose health screen layout."""
        from textual.widgets import Static, TabbedContent, TabPane, Tree

        from bengal.cli.dashboard.widgets import AssetExplorer, ContentBrowser, TaxonomyExplorer

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🏥 Health Dashboard", id="screen-title", classes="section-header")
            yield Static(
                "Select an issue to view details | Press 'r' to run health scan",
                id="health-summary",
            )

            with TabbedContent(id="health-tabs"):
                # Health Issues tab
                with TabPane("🩺 Issues", id="issues-tab"), Horizontal(classes="health-layout"):
                    with Vertical(id="tree-container"):
                        yield Tree("Health Report", id="health-tree")

                    with Vertical(id="details-container", classes="panel"):
                        yield Static("Details:", classes="panel-title")
                        yield Static("Select an issue", id="issue-details")

                # Content browser tab (RFC: rfc-dashboard-api-integration)
                with TabPane("📄 Content", id="content-tab"):
                    yield ContentBrowser(id="health-content-browser")

                # Asset explorer tab (RFC: rfc-dashboard-api-integration)
                with TabPane("📦 Assets", id="assets-tab"):
                    yield AssetExplorer(id="health-asset-explorer")

                # Taxonomy explorer tab (RFC: rfc-dashboard-api-integration)
                with TabPane("🏷️ Taxonomies", id="taxonomies-tab"):
                    yield TaxonomyExplorer(id="health-taxonomy-explorer")

        yield Footer()

    def on_mount(self) -> None:
        """Set up health screen."""
        from textual.widgets import Tree

        from bengal.cli.dashboard.widgets import AssetExplorer, ContentBrowser, TaxonomyExplorer

        tree = self.query_one("#health-tree", Tree)
        tree.show_root = False

        if self.site:
            # Populate content browser (RFC: rfc-dashboard-api-integration)
            content_browser = self.query_one("#health-content-browser", ContentBrowser)
            content_browser.set_site(self.site)

            # Populate asset explorer (RFC: rfc-dashboard-api-integration)
            asset_explorer = self.query_one("#health-asset-explorer", AssetExplorer)
            asset_explorer.set_site(self.site)

            # Populate taxonomy explorer (RFC: rfc-dashboard-api-integration)
            taxonomy_explorer = self.query_one("#health-taxonomy-explorer", TaxonomyExplorer)
            taxonomy_explorer.set_site(self.site)

            # Show site stats in tree
            pages = getattr(self.site, "pages", []) or []
            sections = getattr(self.site, "sections", []) or []
            assets = getattr(self.site, "assets", []) or []

            content = tree.root.add(f"📄 Content ({len(pages)} pages)")
            content.add_leaf(f"  {len(sections)} sections")

            asset_node = tree.root.add(f"🎨 Assets ({len(assets)})")
            # Group assets by type
            by_type: dict[str, int] = {}
            for asset in assets:
                ext = getattr(asset, "suffix", ".unknown")
                if callable(ext):
                    ext = ".file"
                by_type[ext] = by_type.get(ext, 0) + 1
            for ext, count in sorted(by_type.items()):
                asset_node.add_leaf(f"  {ext}: {count}")

            # Show taxonomies
            taxonomies = getattr(self.site, "taxonomies", {}) or {}
            if taxonomies:
                tax_node = tree.root.add(f"🏷️ Taxonomies ({len(taxonomies)})")
                for tax_name, terms in taxonomies.items():
                    if isinstance(terms, dict):
                        tax_node.add_leaf(f"  {tax_name}: {len(terms)} terms")

            tree.root.add_leaf("✓ Press 'r' to run health scan")
        else:
            tree.root.add_leaf("⚠ No site loaded")

    def action_rescan(self) -> None:
        """Rescan site health."""
        if not self.site:
            self.app.notify("No site loaded", title="Error", severity="error")
            return

        self.app.notify("Scanning site health...", title="Health")

        # Run health scan in background
        self.run_worker(
            self._run_health_scan,
            name="health_worker",
            exclusive=True,
            thread=True,
        )

    async def _run_health_scan(self) -> None:
        """Run health scan in background thread."""
        from textual.widgets import Tree

        from bengal.health import HealthReport

        tree = self.query_one("#health-tree", Tree)
        summary = self.query_one("#health-summary", Static)

        try:
            # Run health check
            self.app.call_from_thread(summary.update, "Scanning...")

            report = HealthReport.from_site(self.site)

            # Clear and rebuild tree
            self.app.call_from_thread(tree.root.remove_children)

            # Add issues by category
            total_issues = 0

            if hasattr(report, "link_issues") and report.link_issues:
                links = tree.root.add(f"Links ({len(report.link_issues)})")
                for issue in report.link_issues[:10]:  # Limit display
                    self.app.call_from_thread(links.add_leaf, f"✗ {issue}")
                total_issues += len(report.link_issues)

            if hasattr(report, "content_issues") and report.content_issues:
                content = tree.root.add(f"Content ({len(report.content_issues)})")
                for issue in report.content_issues[:10]:
                    self.app.call_from_thread(content.add_leaf, f"⚠ {issue}")
                total_issues += len(report.content_issues)

            if total_issues == 0:
                self.app.call_from_thread(tree.root.add_leaf, "✓ No issues found")
                self.app.call_from_thread(summary.update, "Site is healthy!")
            else:
                self.app.call_from_thread(summary.update, f"Found {total_issues} issue(s)")

            self.app.call_from_thread(self.app.notify, "Health scan complete", title="Health")

        except Exception as e:
            self.app.call_from_thread(summary.update, f"Scan failed: {e}")
            self.app.call_from_thread(self.app.notify, str(e), title="Error", severity="error")


class HelpScreen(Screen):
    """
    Help screen showing keyboard shortcuts.

    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "pop_screen", "Close"),
        Binding("q", "pop_screen", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose help screen."""
        yield Header()

        with Vertical(id="help-content", classes="panel"):
            yield Static("⌨️  Keyboard Shortcuts", classes="panel-title")
            yield Static("""
[bold]Navigation[/bold]
  1, 2, 3      Switch screens (Build, Serve, Health)
  Ctrl+P       Command palette
  ?            Toggle this help

[bold]Build Screen[/bold]
  r            Rebuild site
  c            Clear log

[bold]Serve Screen[/bold]
  o            Open in browser
  r            Force rebuild
  c            Clear log

[bold]Health Screen[/bold]
  r            Rescan site
  Enter        View issue details

[bold]General[/bold]
  q            Quit dashboard
  Escape       Close dialogs
""")

        yield Footer()

    def action_pop_screen(self) -> None:
        """Close help screen."""
        self.app.pop_screen()
