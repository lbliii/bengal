# RFC: Bengal Terminal UX with Textual

**Status**: Evaluated  
**Author**: AI Assistant  
**Created**: 2024-12-21  
**Subsystem**: CLI / Output  
**Confidence**: 95% 🟢

---

## Summary

Adopt Textual as Bengal's terminal UI framework, replacing direct Rich usage. This unifies the CLI stack around **Click + Textual**, enables interactive dashboards, and allows sharing design tokens between web and terminal output.

**Visual Identity**: All Textual components and layouts defined in this RFC adhere to the [Bengal Terminal UX Style Guide](rfc-terminal-ux-style-guide.md).

---

## Motivation

### Current State

Bengal uses:
- **Click**: Command-line argument parsing and routing
- **Rich**: Terminal output formatting (colors, tables, panels)

### Problems

1. **Rich is output-only** — no interactivity for long-running operations
2. **Design systems are siloed** — web CSS tokens don't translate to terminal
3. **No dashboard experience** — `bengal serve` has basic output, no live updates
4. **Two separate dependencies** — Rich and Textual are both from Textualize

### Opportunity

Textual:
- **Includes Rich** — reduces dependencies from 3 to 2
- **CSS-like styling** — can share design tokens with web theme
- **Interactive widgets** — DataTable, ProgressBar, Tree for rich dashboards
- **Web deployment** — same TUI can run in browser via textual-web

---

## Goals

1. **Unify CLI stack** around Click + Textual
2. **Share design tokens** between web CSS and terminal `.tcss`
3. **Enable interactive dashboard** for `bengal serve` and build progress
4. **Maintain backward compatibility** — standard CLI output still works
5. **Reduce dependencies** — Textual includes Rich; eventually replace `questionary`
6. **Thread-safe state updates** — handle parallel build events without UI glitches
7. **Cross-terminal accessibility** — support TrueColor and 256-color with fallback

## Non-Goals

- Rewriting all CLI commands immediately
- Requiring interactive mode for basic operations
- Replacing Click with something else (Typer is future consideration)

---

## Design

### 1. Dependency Changes

**Before**:
```toml
dependencies = [
    "click>=8.0",
    "rich>=13.0",
]
```

**After**:
```toml
dependencies = [
    "click>=8.0",
    "textual>=0.89",  # Includes Rich
]
```

### 2. CLI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Click (command routing + argument parsing)                 │
│                                                             │
│  bengal build [OPTIONS]                                     │
│  bengal serve [OPTIONS]                                     │
│  bengal health [OPTIONS]                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────┴────────────────┐
         │                                 │
         ▼                                 ▼
┌─────────────────────┐     ┌─────────────────────────────┐
│  Standard Mode      │     │  Dashboard Mode              │
│  (Rich console)     │     │  (Textual TUI)              │
│                     │     │                              │
│  bengal build       │     │  bengal build --dashboard    │
│  bengal serve       │     │  bengal serve --dashboard    │
│  bengal health      │     │  bengal health --dashboard   │
└─────────────────────┘     └─────────────────────────────┘
```

**Standard mode**: Uses Rich console output (unchanged behavior)  
**Dashboard mode**: Launches Textual TUI with interactive widgets

### 3. Shared Token System

#### Token Source (Python)

```python
# bengal/themes/tokens.py
"""
Shared design tokens for web and terminal.

These tokens are the single source of truth for Bengal's visual identity.
They generate both CSS custom properties and Textual CSS variables.
"""

BENGAL_PALETTE = {
    # Brand
    "primary": "#FF9D00",       # Bengal Orange
    "secondary": "#3498DB",     # Bright Blue
    "accent": "#F1C40F",        # Sunflower Yellow

    # Semantic
    "success": "#2ECC71",       # Emerald Green
    "warning": "#E67E22",       # Carrot Orange
    "error": "#E74C3C",         # Alizarin Crimson
    "info": "#95A5A6",          # Silver
    "muted": "#7F8C8D",         # Grayish

    # Surfaces (dark mode)
    "surface": "#1a1a1a",
    "surface-elevated": "#252525",
    "background": "#0d0d0d",

    # Text
    "text": "#ECF0F1",
    "text-muted": "#95A5A6",
}

# Mascots (always displayed)
BENGAL_MASCOT = "ᓚᘏᗢ"        # Success/headers
MOUSE_MASCOT = "ᘛ⁐̤ᕐᐷ"        # Errors
```

#### Generated Web CSS

The generator script will output CSS that replaces current manual token definitions in `foundation.css` and `semantic.css`.

```css
/* bengal/themes/default/assets/css/tokens/generated.css */
:root {
    --color-primary: #FF9D00;
    --color-secondary: #3498DB;
    --color-accent: #F1C40F;
    --color-success: #2ECC71;
    --color-warning: #E67E22;
    --color-error: #E74C3C;
    --color-bg-primary: #1a1a1a;
    /* ... */
}
```

#### Generated Textual CSS

```css
/* bengal/themes/terminal/bengal.tcss */
$primary: #FF9D00;
$secondary: #3498DB;
$accent: #F1C40F;
$success: #2ECC71;
$warning: #E67E22;
$error: #E74C3C;
$surface: #1a1a1a;
$surface-elevated: #252525;
$text: #ECF0F1;
$text-muted: #95A5A6;

/* Bengal-specific styles */
Header {
    background: $primary;
    color: $surface;
}

Footer {
    background: $surface-elevated;
}

.mascot {
    color: $primary;
    text-style: bold;
}

.error-mascot {
    color: $error;
    text-style: bold;
}

.phase-complete {
    color: $success;
}

.phase-error {
    color: $error;
}

.phase-pending {
    color: $text-muted;
}
```

### 4. Concurrency & Event Safety

#### Parallel Build Handling

Bengal's `BuildOrchestrator` uses `ThreadPoolExecutor` for parallel rendering. To prevent UI flickering or race conditions:

1. **Non-blocking Workers**: Build phases run in Textual `work` threads.
2. **Safe Callbacks**: Orchestrator events use `app.call_from_thread()` to schedule UI updates on the main event loop.
3. **Atomic State**: Reactive variables (`pages_built`, `current_phase`) are updated atomically to ensure the progress bar stays smooth.

```python
# In BuildOrchestrator
def build_with_events(self):
    for phase in self.phases:
        self.emit_event(PhaseStarted(phase))
        # Parallel work happens here
        # Sub-orchestrators call back to this emitter
        self.emit_event(PhaseComplete(phase))
```

### 5. Terminal Compatibility & Accessibility

#### Color Systems
- **TrueColor (24-bit)**: Used by default for modern terminals (iTerm2, VS Code, Kitty).
- **256-color Fallback**: Textual/Rich automatically downsample hex codes to the nearest ANSI 256 color.
- **Monochrome**: Dashboard mode will detect `NO_COLOR=1` or `TERM=dumb` and fall back to standard mode or use high-contrast ASCII symbols.

#### Accessibility
- **Screen Reader Mode**: Textual supports a screen reader mode (`Ctrl+S` toggle) which simplifies the layout for easier navigation.
- **Contrast**: Tokens are verified against WCAG AA standards for terminal background colors.
- **Keyboard-only**: All dashboard features must be reachable via keyboard shortcuts (Bindings).

Reference: [Textual Widget Gallery](https://textual.textualize.io/widget_gallery/)

#### Widget Selection by Priority

| Widget | Bengal Use Case | Priority |
|--------|-----------------|----------|
| `Header` | `ᓚᘏᗢ Bengal Build` branding | 🔴 Critical |
| `Footer` | `[q] Quit [r] Rebuild [o] Open` | 🔴 Critical |
| `DataTable` | Build phase timing, page stats | 🔴 Critical |
| `ProgressBar` | Build progress (65% complete) | 🔴 Critical |
| `Log` / `RichLog` | Streaming build output | 🔴 Critical |
| `Tree` | Content section hierarchy, health report | 🔴 Critical |
| `Static` | Mascot display, status text | 🟢 Medium |
| `TabbedContent` | Switch: Stats / Output / Errors | 🟡 High |
| `TabPane` | Individual tab content | 🟡 High |
| `Sparkline` | Build time history trend | 🟡 High |
| `MarkdownViewer` | Preview rendered content | 🟡 High |
| `Collapsible` | Expandable phase details | 🟢 Medium |
| `Rule` | Section separators | 🟢 Medium |
| `LoadingIndicator` | Spinner for active phase | 🟢 Medium |
| `Digits` | Large build time display | 🟢 Medium |
| `Select` | Theme/palette dropdown | 🔵 Future |
| `Switch` | Toggle settings | 🔵 Future |
| `DirectoryTree` | File picker for `bengal new` | 🔵 Future |

#### Widget Imports

```python
# bengal/cli/dashboard/widgets.py
from textual.widgets import (
    # Core (must have)
    Header,
    Footer,
    DataTable,
    ProgressBar,
    Log,
    RichLog,
    Static,

    # Navigation (high value)
    TabbedContent,
    TabPane,
    Tree,

    # Data visualization (nice to have)
    Sparkline,
    Digits,

    # Content (nice to have)
    MarkdownViewer,
    Markdown,
    Collapsible,
    Rule,
    LoadingIndicator,

    # Interactive (future)
    Select,
    Switch,
    Input,
)

from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    ScrollableContainer,
)
```

### 5. API Integration

Reference: [Textual API Reference](https://textual.textualize.io/api/)

#### Key API Modules

| Module | Purpose | Bengal Use |
|--------|---------|------------|
| `textual.app` | Core App class | Dashboard base class |
| `textual.reactive` | Reactive variables | Live build progress updates |
| `textual.worker` | Background tasks | Run builds without blocking UI |
| `textual.on` | Event decorators | Handle keyboard/build events |
| `textual.binding` | Keyboard shortcuts | `q`, `r`, `o`, `c` commands |
| `textual.message` | Custom messages | Build phase completion signals |
| `textual.timer` | Periodic updates | Refresh file watcher status |

#### Reactive Build State

```python
# bengal/cli/dashboard/state.py
from textual.reactive import reactive

class BengalBuildDashboard(App):
    """Dashboard with reactive state updates."""

    # Reactive variables auto-update UI when changed
    pages_built = reactive(0)
    total_pages = reactive(0)
    current_phase = reactive("Initializing")
    build_time_ms = reactive(0)
    is_building = reactive(False)

    def watch_pages_built(self, count: int) -> None:
        """Called automatically when pages_built changes."""
        progress = self.query_one("#progress", ProgressBar)
        if self.total_pages > 0:
            progress.update(progress=count / self.total_pages * 100)

    def watch_current_phase(self, phase: str) -> None:
        """Called automatically when phase changes."""
        status = self.query_one("#status", Static)
        status.update(f"ᓚᘏᗢ  {phase}...")
```

#### Background Workers for Builds

```python
# bengal/cli/dashboard/workers.py
from textual.worker import Worker, get_current_worker, work

class BengalBuildDashboard(App):

    @work(exclusive=True, thread=True)
    async def run_build(self, output: str) -> None:
        """Run build in background worker (doesn't block UI)."""
        worker = get_current_worker()

        from bengal.orchestration import BuildOrchestrator
        orchestrator = BuildOrchestrator(output=output)

        for event in orchestrator.build_with_events():
            if worker.is_cancelled:
                break

            # Update UI from worker thread safely
            self.call_from_thread(self.handle_build_event, event)

        self.call_from_thread(self.on_build_complete)

    def action_rebuild(self) -> None:
        """Triggered by pressing 'r'."""
        self.run_build(self.output_dir)

    def action_cancel_build(self) -> None:
        """Triggered by pressing 'escape'."""
        self.workers.cancel_all()
```

#### Custom Messages for Build Events

```python
# bengal/cli/dashboard/messages.py
from dataclasses import dataclass
from textual.message import Message

@dataclass
class BuildEvent(Message):
    """Base build event for dashboard integration."""
    pass

@dataclass
class PhaseStarted(BuildEvent):
    """Emitted when a build phase begins."""
    phase: str
    total_items: int

@dataclass
class PhaseProgress(BuildEvent):
    """Emitted during phase execution."""
    phase: str
    current: int
    total: int
    item: str  # e.g., "content/docs/guide.md"

@dataclass
class PhaseComplete(BuildEvent):
    """Emitted when a build phase completes."""
    phase: str
    duration_ms: int
    items_processed: int

@dataclass
class BuildComplete(BuildEvent):
    """Emitted when entire build finishes."""
    total_duration_ms: int
    pages: int
    assets: int
    errors: int

# Dashboard handles these events
class BengalBuildDashboard(App):

    def on_phase_started(self, event: PhaseStarted) -> None:
        self.current_phase = event.phase
        self.total_pages = event.total_items

    def on_phase_progress(self, event: PhaseProgress) -> None:
        self.pages_built = event.current
        log = self.query_one("#output", Log)
        log.write_line(f"Rendering {event.item}...")

    def on_phase_complete(self, event: PhaseComplete) -> None:
        table = self.query_one("#phases", DataTable)
        table.add_row(
            event.phase,
            f"{event.duration_ms}ms",
            f"{event.items_processed} items",
            "✓"
        )

    def on_build_complete(self, event: BuildComplete) -> None:
        self.is_building = False
        status = self.query_one("#status", Static)
        status.update(f"ᓚᘏᗢ  Build complete in {event.total_duration_ms}ms")
```

#### Keyboard Bindings

```python
# bengal/cli/dashboard/bindings.py
from textual.binding import Binding

class BengalDashboard(App):
    """Base dashboard with common bindings."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "rebuild", "Rebuild", show=True),
        Binding("c", "clear_cache", "Clear Cache", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

class BengalBuildDashboard(BengalDashboard):
    """Build-specific bindings."""

    BINDINGS = BengalDashboard.BINDINGS + [
        Binding("v", "toggle_verbose", "Verbose", show=True),
    ]

class BengalServeDashboard(BengalDashboard):
    """Serve-specific bindings."""

    BINDINGS = BengalDashboard.BINDINGS + [
        Binding("o", "open_browser", "Open", show=True),
        Binding("l", "show_logs", "Logs", show=True),
    ]
```

#### Timer for Live Updates

```python
# bengal/cli/dashboard/timers.py

class BengalServeDashboard(App):

    def on_mount(self) -> None:
        """Start periodic updates when dashboard mounts."""
        # Update file watcher status every second
        self.set_interval(1.0, self.refresh_watcher_status)
        # Update build history sparkline every 5 seconds
        self.set_interval(5.0, self.refresh_build_history)

    def refresh_watcher_status(self) -> None:
        """Update file watcher status display."""
        status = self.query_one("#watcher-status", Static)
        status.update(f"○ Watching {self.watched_files} files...")

    def refresh_build_history(self) -> None:
        """Update build time sparkline."""
        sparkline = self.query_one("#history", Sparkline)
        sparkline.data = self.build_times[-20:]  # Last 20 builds
```

### 6. Component Library

#### Standard Output (Rich-based, unchanged)

```python
# bengal/output/core.py
from rich.console import Console

class CLIOutput:
    """Standard CLI output using Rich (included in Textual)."""

    def __init__(self):
        self.console = Console()

    def header(self, text: str) -> None:
        self.console.print(f"[bold orange1]ᓚᘏᗢ  {text}[/]")

    def success(self, text: str) -> None:
        self.console.print(f"[green]✓[/] {text}")

    def error(self, text: str) -> None:
        self.console.print(f"[red bold]ᘛ⁐̤ᕐᐷ[/] {text}")
```

#### Dashboard Base Class

```python
# bengal/cli/dashboard/base.py
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive

class BengalDashboard(App):
    """Bengal interactive dashboard base class."""

    CSS_PATH = "bengal.tcss"
    TITLE = "Bengal"

    # Common reactive state
    status = reactive("Ready")
    is_busy = reactive(False)

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "rebuild", "Rebuild"),
        Binding("c", "clear_cache", "Clear"),
        Binding("?", "help", "Help"),
    ]

    def action_clear_cache(self) -> None:
        """Clear build cache."""
        from bengal.cache import clear_all_caches
        clear_all_caches()
        self.notify("Cache cleared", severity="information")
```

#### Build Dashboard

```python
# bengal/cli/dashboard/build.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, DataTable, ProgressBar, Log, Static
from textual.worker import work

from bengal.cli.dashboard.base import BengalDashboard
from bengal.cli.dashboard.messages import PhaseComplete, BuildComplete

class BengalBuildDashboard(BengalDashboard):
    """Interactive build dashboard."""

    BINDINGS = BengalDashboard.BINDINGS + [
        Binding("escape", "cancel_build", "Cancel"),
        Binding("v", "toggle_verbose", "Verbose"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Static("ᓚᘏᗢ", id="mascot", classes="mascot"),
                Static("Building...", id="status"),
            ),
            ProgressBar(id="progress", total=100),
            DataTable(id="phases"),
            Log(id="output", highlight=True, markup=True),
            id="main"
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#phases", DataTable)
        table.add_columns("Phase", "Time", "Details", "Status")
        # Start build automatically
        self.run_build()

    @work(exclusive=True, thread=True)
    async def run_build(self) -> None:
        """Execute build in background."""
        # Build logic here...
        pass

    def on_phase_complete(self, event: PhaseComplete) -> None:
        table = self.query_one("#phases", DataTable)
        table.add_row(event.phase, f"{event.duration_ms}ms", "✓")
```

#### Serve Dashboard with Tabs and Sparkline

```python
# bengal/cli/dashboard/serve.py
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import (
    Header, Footer, Log, DataTable, Static,
    TabbedContent, TabPane, Sparkline
)

from bengal.cli.dashboard.base import BengalDashboard

class BengalServeDashboard(BengalDashboard):
    """Live dev server dashboard with tabs."""

    BINDINGS = BengalDashboard.BINDINGS + [
        Binding("o", "open_browser", "Open"),
    ]

    # Track build times for sparkline
    build_times: list[float] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("ᓚᘏᗢ  Serving at http://localhost:3000", id="status"),
            TabbedContent(
                TabPane("Changes", Log(id="changes"), id="tab-changes"),
                TabPane("Stats", DataTable(id="stats"), id="tab-stats"),
                TabPane("Errors", Log(id="errors"), id="tab-errors"),
                TabPane("Preview", id="tab-preview"),  # Future: MarkdownViewer
            ),
            Sparkline(self.build_times, id="history"),
            id="main"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_status)

    def action_open_browser(self) -> None:
        import webbrowser
        webbrowser.open("http://localhost:3000")

    def log_change(self, path: str) -> None:
        log = self.query_one("#changes", Log)
        log.write_line(f"● {path} modified")

    def update_build_time(self, duration: float) -> None:
        self.build_times.append(duration)
        self.build_times = self.build_times[-20:]  # Keep last 20
        sparkline = self.query_one("#history", Sparkline)
        sparkline.data = self.build_times
```

#### Health Dashboard with Tree

```python
# bengal/cli/dashboard/health.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Tree, Static, Markdown

from bengal.cli.dashboard.base import BengalDashboard

class BengalHealthDashboard(BengalDashboard):
    """Interactive health report explorer."""

    BINDINGS = BengalDashboard.BINDINGS + [
        Binding("f", "fix_issue", "Fix"),
        Binding("e", "export_report", "Export"),
        Binding("enter", "expand_node", "Expand"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Tree("Health Report", id="tree"),
                Static(id="details", classes="details-panel"),
            ),
            id="main"
        )
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#tree", Tree)
        root = tree.root

        # Build tree from health report
        links = root.add("Links", expand=True)
        links.add_leaf("✓ Internal (45)")
        links.add_leaf("⚠ External (2)")

        images = root.add("Images")
        images.add_leaf("✓ All valid")

        frontmatter = root.add("Frontmatter")
        frontmatter.add_leaf("⚠ Missing required (3)")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        details = self.query_one("#details", Static)
        # Show details for selected node
        details.update(f"Selected: {event.node.label}")
```

### 7. CLI Integration

```python
# bengal/cli/commands/build.py
import click
from bengal.cli.base import BengalCommand

@click.command(cls=BengalCommand)
@click.option("--output", "-o", default="public/", help="Output directory")
@click.option("--dashboard", is_flag=True, help="Show interactive dashboard")
@click.option("--parallel/--no-parallel", default=True, help="Parallel rendering")
def build(output: str, dashboard: bool, parallel: bool) -> None:
    """Build your Bengal site to static HTML."""

    if dashboard:
        from bengal.cli.dashboard.build import BengalBuildDashboard
        app = BengalBuildDashboard(output=output, parallel=parallel)
        app.run()
    else:
        # Standard Rich output (existing behavior)
        from bengal.orchestration import build_site
        build_site(output=output, parallel=parallel)


# bengal/cli/commands/serve.py
@click.command(cls=BengalCommand)
@click.option("--port", "-p", default=3000, help="Server port")
@click.option("--dashboard", is_flag=True, help="Show interactive dashboard")
def serve(port: int, dashboard: bool) -> None:
    """Start development server with live reload."""

    if dashboard:
        from bengal.cli.dashboard.serve import BengalServeDashboard
        app = BengalServeDashboard(port=port)
        app.run()
    else:
        from bengal.server import run_dev_server
        run_dev_server(port=port)


# bengal/cli/commands/health.py
@click.command(cls=BengalCommand)
@click.option("--dashboard", is_flag=True, help="Show interactive explorer")
def health(dashboard: bool) -> None:
    """Run health checks and validation."""

    if dashboard:
        from bengal.cli.dashboard.health import BengalHealthDashboard
        app = BengalHealthDashboard()
        app.run()
    else:
        from bengal.health import run_health_checks
        run_health_checks()
```

### 8. Advanced Features

Reference: [Textual Guide](https://textual.textualize.io/guide/)

#### Toast Notifications

Build feedback via transient pop-up messages:

```python
# bengal/cli/dashboard/notifications.py
from textual.app import App

class BengalDashboard(App):
    """Dashboard with notification support."""

    def on_build_complete(self, event: BuildComplete) -> None:
        """Show success notification."""
        self.notify(
            f"Build complete in {event.duration_ms}ms",
            title="ᓚᘏᗢ Bengal",
            severity="information",
            timeout=5,
        )

    def on_build_error(self, event: BuildError) -> None:
        """Show error notification."""
        self.notify(
            f"Build failed: {event.message}",
            title="ᘛ⁐̤ᕐᐷ Error",
            severity="error",
            timeout=10,
        )

    def on_file_changed(self, path: str) -> None:
        """Show brief change notification."""
        self.notify(f"Changed: {path}", timeout=2)

    def action_clear_cache(self) -> None:
        """Clear cache with confirmation."""
        from bengal.cache import clear_all_caches
        clear_all_caches()
        self.notify("Cache cleared", severity="information")
```

#### Command Palette

Fuzzy search interface for quick command access (like VS Code's `Ctrl+P`):

```python
# bengal/cli/dashboard/commands.py
from textual.command import Provider, Hit, Hits, DiscoveryHit

class BengalCommandProvider(Provider):
    """Provide Bengal-specific commands in command palette."""

    async def discover(self) -> Hits:
        """Commands shown before user types."""
        yield DiscoveryHit(
            "Rebuild Site",
            command=self.app.action_rebuild,
            help="Rebuild the entire site",
        )
        yield DiscoveryHit(
            "Clear Cache",
            command=self.app.action_clear_cache,
            help="Clear all build caches",
        )
        yield DiscoveryHit(
            "Open in Browser",
            command=self.app.action_open_browser,
            help="Open site in default browser",
        )

    async def search(self, query: str) -> Hits:
        """Search pages and commands."""
        matcher = self.matcher(query)

        # Search pages by title
        for page in self.app.site.pages:
            score = matcher.match(page.title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(page.title),
                    command=lambda p=page: self.app.preview_page(p),
                    help=f"Preview: {page.path}",
                )

        # Search health issues
        for issue in self.app.health_issues:
            score = matcher.match(issue.message)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(issue.message),
                    command=lambda i=issue: self.app.show_issue(i),
                    help=f"Health: {issue.severity}",
                )


class BengalDashboard(App):
    """Dashboard with command palette."""

    COMMANDS = {BengalCommandProvider}

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Commands", show=True),
    ]
```

**Command Palette Mockup**:
```
┌─ Bengal ────────────────────────────────────────────────────┐
│                                                             │
│  🔍 > install                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 📄 Installation Guide          docs/guide/install.md   │ │
│  │ 📄 Installing Dependencies     docs/guide/deps.md      │ │
│  │ 🔧 Rebuild Site                                        │ │
│  │ 🗑️  Clear Cache                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Multi-Screen Navigation

Unified dashboard with switchable screens:

```python
# bengal/cli/dashboard/screens.py
from textual.screen import Screen
from textual.binding import Binding

class BuildScreen(Screen):
    """Build dashboard screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("s", "app.push_screen('serve')", "Serve"),
        Binding("h", "app.push_screen('health')", "Health"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield BuildDashboardContent()
        yield Footer()


class ServeScreen(Screen):
    """Dev server screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.push_screen('build')", "Build"),
        Binding("h", "app.push_screen('health')", "Health"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ServeDashboardContent()
        yield Footer()


class HealthScreen(Screen):
    """Health report screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.push_screen('build')", "Build"),
        Binding("s", "app.push_screen('serve')", "Serve"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield HealthDashboardContent()
        yield Footer()


class BengalApp(App):
    """Unified Bengal dashboard application."""

    SCREENS = {
        "build": BuildScreen,
        "serve": ServeScreen,
        "health": HealthScreen,
    }

    BINDINGS = [
        Binding("1", "push_screen('build')", "Build"),
        Binding("2", "push_screen('serve')", "Serve"),
        Binding("3", "push_screen('health')", "Health"),
    ]

    def on_mount(self) -> None:
        """Start with build screen."""
        self.push_screen("build")
```

**Usage**:
```bash
# Unified dashboard (recommended)
bengal --dashboard

# Or individual dashboards
bengal build --dashboard
bengal serve --dashboard
bengal health --dashboard
```

#### Animation

CSS transitions for smooth visual feedback:

```css
/* bengal.tcss - Animation section */

/* Smooth progress bar updates */
ProgressBar {
    transition: bar 200ms linear;
}

ProgressBar > .bar--complete {
    transition: color 300ms ease-out;
}

/* Phase status color transitions */
.phase-complete {
    transition: color 300ms ease-out;
}

.phase-running {
    transition: background 150ms linear;
}

/* Fade in new log entries */
Log > .log--line {
    transition: opacity 150ms linear;
}

/* Tab switch animation */
TabbedContent > ContentSwitcher {
    transition: offset 250ms in_out_cubic;
}

/* Toast notification slide-in */
Toast {
    transition: offset 300ms in_out_cubic;
}

/* Sparkline data update */
Sparkline {
    transition: background 200ms linear;
}
```

#### Devtools Integration

Live debugging during dashboard development:

```bash
# Run with devtools (opens browser console)
textual run --dev bengal.cli.dashboard:BengalBuildDashboard

# Features:
# - Live DOM tree inspection
# - CSS property viewer
# - Event log
# - Hot reload on code changes
# - Console for debugging
```

**Development workflow**:
```python
# bengal/cli/dashboard/__main__.py
"""Run dashboard in development mode."""

if __name__ == "__main__":
    import sys
    from bengal.cli.dashboard.app import BengalApp

    if "--dev" in sys.argv:
        # Enable devtools
        from textual.features import parse_features
        parse_features("devtools")

    app = BengalApp()
    app.run()
```

### 9. Testing Strategy

Reference: [Textual Testing Guide](https://textual.textualize.io/guide/testing/)

#### Headless Testing

Test dashboards without a terminal:

```python
# tests/dashboard/test_build_dashboard.py
import pytest
from bengal.cli.dashboard.build import BengalBuildDashboard

@pytest.mark.asyncio
async def test_build_dashboard_renders():
    """Test build dashboard renders correctly."""
    app = BengalBuildDashboard()

    async with app.run_test() as pilot:
        # Check initial state
        status = app.query_one("#status")
        assert "Ready" in status.renderable or "Building" in status.renderable

        # Check phase table exists
        table = app.query_one("#phases")
        assert table is not None

        # Check footer has expected bindings
        footer = app.query_one("Footer")
        assert footer is not None


@pytest.mark.asyncio
async def test_keyboard_shortcuts():
    """Test keyboard bindings work."""
    app = BengalBuildDashboard()

    async with app.run_test() as pilot:
        # Press 'c' to clear cache
        await pilot.press("c")

        # Check notification appeared
        toasts = app.query(".toast")
        assert len(toasts) > 0


@pytest.mark.asyncio
async def test_rebuild_action():
    """Test rebuild keyboard shortcut."""
    app = BengalBuildDashboard()

    async with app.run_test() as pilot:
        # Press 'r' to rebuild
        await pilot.press("r")

        # Wait for any animations
        await pilot.wait_for_animation()

        # Verify build started (status changed)
        status = app.query_one("#status")
        # Status should indicate building or complete
```

#### Simulating User Interactions

```python
# tests/dashboard/test_interactions.py

@pytest.mark.asyncio
async def test_command_palette():
    """Test command palette search."""
    app = BengalApp()

    async with app.run_test() as pilot:
        # Open command palette
        await pilot.press("ctrl+p")

        # Type search query
        await pilot.type("install")

        # Wait for search results
        await pilot.pause()

        # Check results appeared
        # (implementation depends on command palette structure)


@pytest.mark.asyncio
async def test_screen_navigation():
    """Test switching between screens."""
    app = BengalApp()

    async with app.run_test() as pilot:
        # Start on build screen
        assert isinstance(app.screen, BuildScreen)

        # Press '2' to switch to serve
        await pilot.press("2")
        assert isinstance(app.screen, ServeScreen)

        # Press '3' to switch to health
        await pilot.press("3")
        assert isinstance(app.screen, HealthScreen)

        # Press escape to go back
        await pilot.press("escape")
        assert isinstance(app.screen, ServeScreen)
```

#### Snapshot Testing

Visual regression testing with pytest-textual-snapshot:

```python
# tests/dashboard/test_snapshots.py

@pytest.mark.asyncio
async def test_build_dashboard_snapshot(snap_compare):
    """Snapshot test for build dashboard appearance."""
    app = BengalBuildDashboard()

    async with app.run_test() as pilot:
        # Wait for initial render
        await pilot.pause()

        # Compare to saved snapshot
        assert snap_compare(app)


@pytest.mark.asyncio
async def test_health_dashboard_snapshot(snap_compare):
    """Snapshot test for health dashboard appearance."""
    app = BengalHealthDashboard()

    async with app.run_test() as pilot:
        await pilot.pause()
        assert snap_compare(app)
```

**Run snapshot tests**:
```bash
# Generate initial snapshots
pytest tests/dashboard/ --snapshot-update

# Run comparison tests
pytest tests/dashboard/

# View diffs on failure
pytest tests/dashboard/ --snapshot-details
```

### 10. Brand Identity

#### Mascots (Always Shown)

| Symbol | Name | Usage |
|--------|------|-------|
| `ᓚᘏᗢ` | Bengal Cat | Success headers, dashboard header |
| `ᘛ⁐̤ᕐᐷ` | Mouse | Error headers only |

#### Status Icons

| Status | Icon | Textual Class |
|--------|------|---------------|
| Complete | `✓` | `.phase-complete` |
| Running | `⠹` (spinner) | `.phase-running` |
| Pending | `·` | `.phase-pending` |
| Error | `x` | `.phase-error` |
| Warning | `!` | `.phase-warning` |

---

## Migration Path

### Phase 1: Foundation (Week 1)

1. Replace `rich` with `textual` in dependencies
2. Update imports (Rich is still available via Textual)
3. Verify existing output unchanged
4. Add `bengal.tcss` with shared tokens
5. Add `pytest-textual-snapshot` dev dependency

**Effort**: 0.5 days  
**Risk**: Low (Rich API unchanged)

### Phase 2: Build Dashboard (Week 2)

1. Create `BengalBuildDashboard` class
2. Add `--dashboard` flag to `bengal build`
3. Wire up build events to dashboard updates
4. Add toast notifications for build complete/error
5. Add basic tests for dashboard
6. Test across terminals (iTerm, Terminal.app, VS Code)

**Effort**: 2-3 days  
**Risk**: Medium (new feature)

### Phase 3: Serve Dashboard (Week 3)

1. Create `BengalServeDashboard` class
2. Add `--dashboard` flag to `bengal serve`
3. Integrate file watcher events
4. Add Sparkline for build history
5. Add TabbedContent for Changes/Stats/Errors
6. Add keyboard shortcuts and notifications

**Effort**: 2-3 days  
**Risk**: Medium (event integration)

### Phase 4: Health Dashboard (Week 4)

1. Create `BengalHealthDashboard` class
2. Add Tree widget for issue navigation
3. Add details panel for issue inspection
4. Add `--dashboard` flag to `bengal health`

**Effort**: 1-2 days  
**Risk**: Low (simpler than build/serve)

### Phase 5: Advanced Features (Week 5)

1. Create `BengalCommandProvider` for command palette
2. Add `Ctrl+P` binding for command palette
3. Implement page/command search
4. Add unified `BengalApp` with multi-screen navigation
5. Add `bengal --dashboard` for unified experience

**Effort**: 2-3 days  
**Risk**: Medium (new UX pattern)

### Phase 6: Polish & Testing (Week 6)

1. Add CSS animations for smooth transitions
2. Create snapshot tests for all dashboards
3. Add interaction tests for keyboard shortcuts
4. Shared token generator script
5. Documentation for dashboard development

**Effort**: 2-3 days  
**Risk**: Low (polish)

---

## Effort Summary

| Phase | Work | Days |
|-------|------|------|
| Foundation | Swap dependency, verify, test setup | 0.5 |
| Token System | Source of truth + generator + web integration | 1.5 |
| Build dashboard | TUI + build event integration + parallel safety | 3.0 |
| Serve dashboard | TUI + file watcher + sparkline + persistence | 2.5 |
| Health dashboard | Tree explorer + details panel + fix actions | 2.0 |
| Advanced features | Command palette + unified app | 2.5 |
| Polish & testing | Animations + snapshot tests + docs | 2.0 |
| **Total** | | **14-16 days** |

### Priority Breakdown

| Priority | Features | Days |
|----------|----------|------|
| 🔴 **MVP** | Build + Serve dashboards, notifications | 5-6 |
| 🟡 **Enhanced** | Health dashboard, command palette | 3-5 |
| 🟢 **Polish** | Animations, testing, unified app | 2-4 |

---

## Alternatives Considered

### Alternative 1: Keep Rich Separate

**Rejected**: Textual includes Rich. Adding Textual means Rich comes free.

### Alternative 2: Make Textual Optional

**Partially accepted**: Dashboard mode is opt-in via `--dashboard` flag. Standard output still uses Rich console directly.

```toml
# Could be optional in future
[project.optional-dependencies]
dashboard = ["textual>=0.89"]
```

### Alternative 3: Replace Click with Textual

**Rejected**: Textual doesn't do argument parsing. Click (or Typer) still needed for CLI routing.

---

## Open Questions

1. **Textual-web**: Should `bengal serve --dashboard` be accessible via browser? (Low priority, but possible via `textual-web`).
2. **Token generation**: Build-time or commit-time token generation? (Recommended: commit-time with validation hook).
3. **Palette switching**: Support `--palette charcoal-bengal` in terminal? (Yes, by mapping palette names to token files).
4. **State Persistence**: Should we use `textual.storage` to persist dashboard state (like expanded tree nodes or active tabs)?
5. **Questionary Migration**: When should `bengal new` wizard be migrated from Questionary to Textual?

---

## References

### Bengal Codebase
- `bengal/utils/rich_console.py` — Current Rich theme
- `bengal/output/core.py` — CLIOutput class
- `bengal/output/icons.py` — Icon definitions
- `bengal/themes/default/assets/css/tokens/` — Web token system
- `bengal/cli/commands/` — Current Click commands

### Textual Documentation

- [RFC: Bengal Terminal UX Style Guide](rfc-terminal-ux-style-guide.md) — Visual specification and UX patterns
- [Textual Home](https://textual.textualize.io/) — Framework overview
- [Textual Guide](https://textual.textualize.io/guide/) — Comprehensive guide
- [Textual Widget Gallery](https://textual.textualize.io/widget_gallery/) — Visual widget reference
- [Textual API Reference](https://textual.textualize.io/api/) — Full API docs
- [Textual CSS Guide](https://textual.textualize.io/guide/CSS/) — Styling reference
- [Textual Themes](https://textual.textualize.io/guide/themes/) — Theming system
- [Textual Reactivity](https://textual.textualize.io/guide/reactivity/) — Reactive variables
- [Textual Workers](https://textual.textualize.io/guide/workers/) — Background tasks
- [Textual Events](https://textual.textualize.io/guide/events/) — Event handling
- [Textual Command Palette](https://textual.textualize.io/guide/command_palette/) — Fuzzy search UI
- [Textual Screens](https://textual.textualize.io/guide/screens/) — Multi-screen navigation
- [Textual Animation](https://textual.textualize.io/guide/animation/) — CSS transitions
- [Textual Testing](https://textual.textualize.io/guide/testing/) — Headless testing
- [Textual Devtools](https://textual.textualize.io/guide/devtools/) — Live debugging

---

## Appendix A: Dashboard Mockups

### Build Dashboard

```
┌─ Bengal Build ──────────────────────────────────────────────┐
│                                                             │
│  ᓚᘏᗢ  Building site...                                      │
│                                                             │
│  ████████████░░░░░░░░  65%                                  │
│                                                             │
│  ┌─ Phases ───────────────────────────────────────────────┐ │
│  │ Phase        │    Time │ Details              │ Status │ │
│  ├──────────────┼─────────┼──────────────────────┼────────┤ │
│  │ Discovery    │    45ms │ 245 pages            │ ✓      │ │
│  │ Taxonomies   │    12ms │ 3 taxonomies         │ ✓      │ │
│  │ Rendering    │     ... │ 159/245 pages        │ ⠹      │ │
│  │ Assets       │       - │                      │ ·      │ │
│  │ Postprocess  │       - │                      │ ·      │ │
│  └──────────────┴─────────┴──────────────────────┴────────┘ │
│                                                             │
│  ┌─ Output ───────────────────────────────────────────────┐ │
│  │ Rendering content/docs/guide/installation.md...        │ │
│  │ Rendering content/docs/guide/quickstart.md...          │ │
│  │ Rendering content/blog/2024/new-release.md...          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  [q] Quit  [r] Rebuild  [c] Clear Cache  [v] Verbose        │
└─────────────────────────────────────────────────────────────┘
```

### Serve Dashboard with Tabs and Sparkline

```
┌─ Bengal Dev Server ─────────────────────────────────────────┐
│                                                             │
│  ᓚᘏᗢ  Serving at http://localhost:3000                      │
│                                                             │
│  ┌─ Changes ─┬─ Stats ─┬─ Errors ─┬─ Preview ─┐             │
│  ━━━━━━━━━━━━╸━━━━━━━━━╺━━━━━━━━━━━━━━━━━━━━━━━             │
│  │                                                          │
│  │  ● content/blog/new-post.md          Modified  2s ago    │
│  │  ● themes/default/base.html          Modified  45s ago   │
│  │  ○ Watching 245 files...                                 │
│  │                                                          │
│  └──────────────────────────────────────────────────────────┘
│                                                             │
│  Build History (last 20 builds)                             │
│  ▂▄▂▄▃▃▆▅▃▂▃▂▃▂▄▇▃▃▇▅▄▃▄▄▃▂▃▂▃▄▄█▆▂▃▃▅▃▃▄▃▇▃▃▃              │
│                                                             │
│  ┌─ Last Build ──────────────────────────────────────────┐  │
│  │ ✓ 0.82s  │  245 pages  │  134 assets  │  A (94/100)   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [q] Quit  [r] Rebuild  [o] Open Browser  [c] Clear Cache   │
└─────────────────────────────────────────────────────────────┘
```

### Health Dashboard with Tree Explorer

```
┌─ Bengal Health ─────────────────────────────────────────────┐
│                                                             │
│  ᓚᘏᗢ  Health Report                                         │
│                                                             │
│  ┌─ Issues ─────────────────┐  ┌─ Details ────────────────┐ │
│  │ ▼ Health Report          │  │                          │ │
│  │ ├── ▼ Links              │  │  ⚠️ Broken External Link  │ │
│  │ │   ├── ✓ Internal (45)  │  │                          │ │
│  │ │   └── ⚠ External (2)   │  │  File: docs/api/ref.md   │ │
│  │ ├── ▼ Images             │  │  Line: 45                │ │
│  │ │   └── ✓ All valid      │  │  Link: /api/deprecated   │ │
│  │ ├── ▼ Frontmatter        │  │                          │ │
│  │ │   └── ⚠ Missing (3)    │  │  Suggestion:             │ │
│  │ └── ▼ Performance        │  │  Update to /api/v2       │ │
│  │     └── ✓ Grade: A       │  │                          │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
│                                                             │
│  Summary: 48 checks passed, 5 warnings, 0 errors            │
│                                                             │
│  [q] Quit  [f] Fix Issue  [e] Export  [Enter] Expand        │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Textual CSS Stylesheet

```css
/* bengal/cli/dashboard/bengal.tcss */

/* === Token Variables === */
$primary: #FF9D00;
$secondary: #3498DB;
$accent: #F1C40F;
$success: #2ECC71;
$warning: #E67E22;
$error: #E74C3C;
$info: #95A5A6;
$muted: #7F8C8D;

$surface: #1a1a1a;
$surface-elevated: #252525;
$background: #0d0d0d;
$text: #ECF0F1;
$text-muted: #95A5A6;

/* === Global Styles === */
Screen {
    background: $background;
}

/* === Header === */
Header {
    background: $primary;
    color: $surface;
    text-style: bold;
}

/* === Footer === */
Footer {
    background: $surface-elevated;
}

FooterKey {
    background: $surface;
    color: $text;
}

FooterKey:hover {
    background: $primary;
}

/* === Mascot === */
.mascot {
    color: $primary;
    text-style: bold;
    padding: 0 1;
}

.error-mascot {
    color: $error;
    text-style: bold;
}

/* === Status Indicators === */
.phase-complete {
    color: $success;
}

.phase-running {
    color: $primary;
}

.phase-pending {
    color: $text-muted;
}

.phase-error {
    color: $error;
}

.phase-warning {
    color: $warning;
}

/* === DataTable === */
DataTable {
    height: auto;
    max-height: 50%;
    background: $surface;
}

DataTable > .datatable--header {
    background: $surface-elevated;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $primary 20%;
}

/* === ProgressBar === */
ProgressBar {
    padding: 1 2;
}

ProgressBar > .bar--bar {
    color: $primary;
}

ProgressBar > .bar--complete {
    color: $success;
}

/* === Log === */
Log {
    background: $surface;
    border: solid $surface-elevated;
    height: 1fr;
}

RichLog {
    background: $surface;
    border: solid $surface-elevated;
}

/* === Tree === */
Tree {
    background: $surface;
    width: 50%;
}

Tree > .tree--cursor {
    background: $primary 20%;
}

Tree > .tree--guides {
    color: $muted;
}

/* === Tabs === */
TabbedContent {
    height: 1fr;
}

Tabs {
    background: $surface-elevated;
}

Tab {
    padding: 0 2;
}

Tab:focus {
    text-style: bold;
}

Tab.-active {
    color: $primary;
    text-style: bold underline;
}

/* === Sparkline === */
Sparkline {
    height: 3;
    margin: 1 0;
}

Sparkline > .sparkline--max {
    color: $warning;
}

Sparkline > .sparkline--min {
    color: $success;
}

/* === Static (status text) === */
#status {
    padding: 1 2;
    text-style: bold;
}

/* === Details Panel (Health) === */
.details-panel {
    width: 50%;
    background: $surface;
    border: solid $surface-elevated;
    padding: 1 2;
}

/* === Container Layout === */
#main {
    padding: 1;
}

Horizontal {
    height: auto;
}
```

---

## Appendix C: File Structure

```
bengal/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Add --dashboard flag for unified app
│   ├── commands/
│   │   ├── build.py         # --dashboard flag
│   │   ├── serve.py         # --dashboard flag
│   │   └── health.py        # --dashboard flag
│   └── dashboard/
│       ├── __init__.py
│       ├── __main__.py      # Run dashboard directly (dev mode)
│       ├── app.py           # BengalApp (unified multi-screen)
│       ├── base.py          # BengalDashboard base class
│       ├── build.py         # BengalBuildDashboard
│       ├── serve.py         # BengalServeDashboard
│       ├── health.py        # BengalHealthDashboard
│       ├── screens.py       # Screen classes for navigation
│       ├── commands.py      # BengalCommandProvider
│       ├── messages.py      # Custom Textual messages
│       ├── notifications.py # Toast notification helpers
│       ├── widgets.py       # Widget imports/aliases
│       └── bengal.tcss      # Textual CSS stylesheet
├── themes/
│   ├── tokens.py            # Shared token definitions
│   └── generate.py          # Token generator script
├── output/
│   └── core.py              # CLIOutput (Rich, unchanged)
└── ...

tests/
├── dashboard/
│   ├── __init__.py
│   ├── conftest.py          # Dashboard test fixtures
│   ├── test_build_dashboard.py
│   ├── test_serve_dashboard.py
│   ├── test_health_dashboard.py
│   ├── test_interactions.py # Keyboard/command tests
│   ├── test_snapshots.py    # Visual regression tests
│   └── snapshots/           # Snapshot test data
│       ├── test_build_dashboard_snapshot.svg
│       ├── test_serve_dashboard_snapshot.svg
│       └── test_health_dashboard_snapshot.svg
└── ...
```

### Dev Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest-textual-snapshot>=0.4.0",  # Snapshot testing
    "pytest-asyncio>=0.21.0",          # Async test support
]
```
