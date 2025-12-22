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
        if hasattr(self.app, "config_changed_signal"):
            self.app.config_changed_signal.subscribe(self, self.on_config_changed)

    def on_config_changed(self, data: tuple[str, object]) -> None:
        """
        Handle config changes from app.

        Args:
            data: Tuple of (key, value) for the changed config
        """
        key, value = data
        # Subclasses can override to handle specific config changes
        pass

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

        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🔨 Build Dashboard", id="screen-title", classes="section-header")

            # Throbber for animated loading
            yield BengalThrobber(id="build-throbber")

            # Flash notifications
            yield BuildFlash(id="build-flash")

            yield ProgressBar(total=100, show_eta=False, id="build-progress")

            with Vertical(classes="section", id="build-stats"):
                yield Static("Build Phases:", classes="section-header")
                yield DataTable(id="phase-table")

            with Vertical(classes="section"):
                yield Static("Output:", classes="section-header")
                yield Log(id="build-log", auto_scroll=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up build screen."""
        super().on_mount()
        from textual.widgets import DataTable

        table = self.query_one("#phase-table", DataTable)
        table.add_columns("Status", "Phase", "Time", "Details")

        phases = ["Discovery", "Taxonomies", "Rendering", "Assets", "Postprocess"]
        for phase in phases:
            table.add_row("○", phase, "-", "", key=phase)

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
        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash

        if not self.site:
            self.app.notify("No site loaded", title="Error", severity="error")
            return

        # Show throbber and flash
        throbber = self.query_one("#build-throbber", BengalThrobber)
        throbber.active = True

        flash = self.query_one("#build-flash", BuildFlash)
        flash.show_building("Starting build...")

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

        from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash
        from bengal.orchestration.build import BuildOrchestrator

        start_time = monotonic()
        log = self.query_one("#build-log", Log)
        table = self.query_one("#phase-table", DataTable)
        progress = self.query_one("#build-progress", ProgressBar)

        def update_phase(name: str, status: str, time_ms: float | None = None) -> None:
            """Update phase status in table."""
            icons = {"pending": "○", "running": "●", "complete": "✓", "error": "✗"}
            icon = icons.get(status, "?")
            time_str = f"{time_ms:.0f}ms" if time_ms else "-"
            try:
                table.update_cell(name, "Status", icon)
                table.update_cell(name, "Time", time_str)
            except Exception:
                pass

        try:
            # Discovery phase
            self.call_from_thread(update_phase, "Discovery", "running")
            self.call_from_thread(log.write_line, "→ Discovery...")
            self.call_from_thread(progress.update, progress=20)

            orchestrator = BuildOrchestrator(self.site)

            # Run the actual build
            phase_start = monotonic()
            stats = orchestrator.build(
                parallel=True,
                incremental=False,
                quiet=True,
            )
            phase_time = (monotonic() - phase_start) * 1000

            # Update all phases as complete
            for phase in ["Discovery", "Taxonomies", "Rendering", "Assets", "Postprocess"]:
                self.call_from_thread(update_phase, phase, "complete", phase_time / 5)

            self.call_from_thread(progress.update, progress=100)

            duration_ms = (monotonic() - start_time) * 1000

            # Show success
            throbber = self.query_one("#build-throbber", BengalThrobber)
            flash = self.query_one("#build-flash", BuildFlash)
            self.call_from_thread(setattr, throbber, "active", False)
            self.call_from_thread(flash.show_success, f"Build complete in {duration_ms:.0f}ms")
            self.call_from_thread(log.write_line, f"✓ Build complete in {duration_ms:.0f}ms")

            # Log rich build stats
            page_count = getattr(stats, "pages_rendered", 0) or len(getattr(self.site, "pages", []))
            asset_count = getattr(stats, "assets_copied", 0) or len(
                getattr(self.site, "assets", [])
            )
            section_count = len(getattr(self.site, "sections", []))

            self.call_from_thread(log.write_line, f"  📄 {page_count} pages rendered")
            self.call_from_thread(log.write_line, f"  🎨 {asset_count} assets copied")
            self.call_from_thread(log.write_line, f"  📁 {section_count} sections")

            # Show phase timings if available
            if hasattr(stats, "phase_times") and stats.phase_times:
                self.call_from_thread(log.write_line, "")
                self.call_from_thread(log.write_line, "Phase timings:")
                for phase_name, phase_ms in stats.phase_times.items():
                    self.call_from_thread(log.write_line, f"  {phase_name}: {phase_ms:.0f}ms")

            # Show output directory
            output_dir = getattr(self.site, "output_dir", "public")
            self.call_from_thread(log.write_line, "")
            self.call_from_thread(log.write_line, f"Output: {output_dir}/")

        except Exception as e:
            duration_ms = (monotonic() - start_time) * 1000

            # Show error
            throbber = self.query_one("#build-throbber", BengalThrobber)
            flash = self.query_one("#build-flash", BuildFlash)
            self.call_from_thread(setattr, throbber, "active", False)
            self.call_from_thread(flash.show_error, str(e))
            self.call_from_thread(log.write_line, f"✗ Build failed: {e}")
            self.call_from_thread(update_phase, "Discovery", "error")

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
        from textual.widgets import Log, Sparkline, TabbedContent, TabPane

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

            with Vertical(classes="section"):
                yield Static("Build History:", classes="section-header")
                yield Sparkline([0], id="build-sparkline")

            with TabbedContent(id="serve-tabs"):
                with TabPane("Changes", id="changes-tab"):
                    yield Log(id="changes-log", auto_scroll=True)
                with TabPane("Pages", id="pages-tab"):
                    yield Log(id="pages-log", auto_scroll=True)
                with TabPane("Errors", id="errors-tab"):
                    yield Log(id="errors-log", auto_scroll=True)

        yield Footer()

    def _get_server_info(self) -> str:
        """Get server info text."""
        url = (
            getattr(self.app, "server_url", "http://localhost:1313")
            if self.app
            else "http://localhost:1313"
        )
        return f"[bold]Server:[/bold] {url}  [dim]Press 'o' to open in browser[/dim]"

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

        # Populate pages log
        pages_log = self.query_one("#pages-log", Log)
        if self.site:
            pages = getattr(self.site, "pages", []) or []
            pages_log.write_line(f"[bold]{len(pages)} pages in site:[/bold]")
            pages_log.write_line("")
            for page in pages[:20]:  # Show first 20
                title = getattr(page, "title", None) or "Untitled"
                url = getattr(page, "url", None) or "/"
                pages_log.write_line(f"  {title[:40]:<40} {url}")
            if len(pages) > 20:
                pages_log.write_line(f"  ... and {len(pages) - 20} more")
        else:
            pages_log.write_line("[yellow]No site loaded[/yellow]")

    def action_open_browser(self) -> None:
        """Open browser to dev server."""
        import webbrowser

        url = getattr(self.app, "server_url", "http://localhost:1313")
        webbrowser.open(url)
        self.app.notify(f"Opening {url}", title="Browser")

    def action_force_rebuild(self) -> None:
        """Force rebuild - switch to build screen and trigger rebuild."""
        self.app.push_screen("build")
        # Give the screen time to mount, then trigger rebuild
        self.set_timer(
            0.1,
            lambda: self.app.screen.action_rebuild()
            if hasattr(self.app.screen, "action_rebuild")
            else None,
        )


class HealthScreen(BengalScreen):
    """
    Health screen for the unified dashboard.

    Shows health issues in a tree with details panel.
    Reuses components from BengalHealthDashboard.
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
        from textual.widgets import Static, Tree

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🏥 Health Dashboard", id="screen-title", classes="section-header")
            yield Static("Select an issue to view details", id="health-summary")

            with Horizontal(classes="health-layout"):
                with Vertical(id="tree-container"):
                    yield Static("Issues:", classes="section-header")
                    yield Tree("Health Report", id="health-tree")

                with Vertical(id="details-container", classes="panel"):
                    yield Static("Details:", classes="panel-title")
                    yield Static("Select an issue", id="issue-details")

        yield Footer()

    def on_mount(self) -> None:
        """Set up health screen."""
        from textual.widgets import Tree

        tree = self.query_one("#health-tree", Tree)
        tree.show_root = False

        if self.site:
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
            self.call_from_thread(summary.update, "Scanning...")

            report = HealthReport.from_site(self.site)

            # Clear and rebuild tree
            self.call_from_thread(tree.root.remove_children)

            # Add issues by category
            total_issues = 0

            if hasattr(report, "link_issues") and report.link_issues:
                links = tree.root.add(f"Links ({len(report.link_issues)})")
                for issue in report.link_issues[:10]:  # Limit display
                    self.call_from_thread(links.add_leaf, f"✗ {issue}")
                total_issues += len(report.link_issues)

            if hasattr(report, "content_issues") and report.content_issues:
                content = tree.root.add(f"Content ({len(report.content_issues)})")
                for issue in report.content_issues[:10]:
                    self.call_from_thread(content.add_leaf, f"⚠ {issue}")
                total_issues += len(report.content_issues)

            if total_issues == 0:
                self.call_from_thread(tree.root.add_leaf, "✓ No issues found")
                self.call_from_thread(summary.update, "Site is healthy!")
            else:
                self.call_from_thread(summary.update, f"Found {total_issues} issue(s)")

            self.call_from_thread(self.app.notify, "Health scan complete", title="Health")

        except Exception as e:
            self.call_from_thread(summary.update, f"Scan failed: {e}")
            self.call_from_thread(self.app.notify, str(e), title="Error", severity="error")


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
