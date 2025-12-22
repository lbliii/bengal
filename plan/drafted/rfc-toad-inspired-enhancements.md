# RFC: Toad-Inspired Dashboard Enhancements

**Status**: Draft  
**Created**: 2024-12-21  
**Author**: AI Assistant  
**Source Analysis**: [batrachianai/toad](https://github.com/batrachianai/toad)

---

## Summary

Enhance Bengal's Textual dashboard implementation by adopting proven patterns from Toad, a terminal UI for AI agents built by Will McGugan (creator of Textual). This RFC proposes web serve mode, CLI improvements, new widgets, and architectural patterns that will improve Bengal's dashboard UX.

---

## Background

### What is Toad?

Toad is "a unified interface for AI in your terminal" built with Textual. It provides:
- Agent selection and management
- Conversation UI for AI interactions
- Web serve mode for browser access
- Settings management with reactive updates
- Command palette with fuzzy search

**Repository**: https://github.com/batrachianai/toad  
**Author**: Will McGugan (@willmcgugan)  
**License**: AGPL-3.0

### Why Learn from Toad?

1. **Authoritative Source**: Built by Textual's creator, represents best practices
2. **Similar Use Case**: Multi-screen dashboard with background operations
3. **Production Quality**: 500+ stars, actively maintained
4. **Pattern Catalog**: Rich set of reusable patterns

---

## Current State Analysis

### Bengal Dashboard Architecture

```
bengal/cli/dashboard/
├── app.py          # BengalApp - unified dashboard
├── base.py         # BengalDashboard - base class
├── screens.py      # BuildScreen, ServeScreen, HealthScreen, HelpScreen
├── build.py        # BengalBuildDashboard
├── serve.py        # BengalServeDashboard
├── health.py       # BengalHealthDashboard
├── commands.py     # BengalCommandProvider (planned)
├── messages.py     # Custom messages
├── widgets.py      # Widget imports
└── bengal.tcss     # Styles
```

### Toad Architecture (Reference)

```
src/toad/
├── app.py          # ToadApp - main app with SCREENS/MODES
├── cli.py          # Click CLI with --serve, -a flags
├── screens/
│   ├── main.py     # MainScreen with conversation
│   ├── store.py    # StoreScreen (landing/selection)
│   ├── settings.py # SettingsScreen
│   └── agent_modal.py
├── widgets/
│   ├── grid_select.py   # Custom grid navigation
│   ├── throbber.py      # Animated loading indicator
│   ├── conversation.py  # Chat interface
│   └── 20+ more...
├── toad.tcss       # Main stylesheet
└── data/agents/    # Agent definitions (TOML)
```

---

## Proposed Enhancements

### 1. Web Serve Mode (`--serve`)

**Toad Pattern** (`cli.py:98-116`):

```python
@click.option("--serve", is_flag=True, help="Serve as web application")
@click.option("--port", metavar="PORT", default=8000, type=int)
@click.option("--host", metavar="HOST", default="localhost")
def run(serve: bool, port: int, host: str):
    if serve:
        from textual_serve.server import Server
        server = Server(
            sys.argv[0],
            host=host,
            port=port,
            title="Toad",
        )
        server.serve()
    else:
        app.run()
```

**Bengal Implementation**:

```python
# bengal/cli/commands/dashboard.py

@click.command("dashboard")
@click.option("--serve", is_flag=True, help="Serve dashboard as web app")
@click.option("--port", default=8000, type=int, help="Port for web server")
@click.option("--host", default="localhost", help="Host for web server")
@click.option("--start", type=click.Choice(["build", "serve", "health"]), default="build")
def dashboard(serve: bool, port: int, host: str, start: str):
    """Launch interactive dashboard."""
    if serve:
        from textual_serve.server import Server
        # Reconstruct command without --serve to avoid recursion
        cmd = f"bengal dashboard --start {start}"
        server = Server(cmd, host=host, port=port, title="Bengal Dashboard")
        server.serve()
    else:
        from bengal.cli.dashboard.app import BengalApp
        app = BengalApp(site=site, start_screen=start)
        app.run()
```

**Dependencies**:
```toml
# pyproject.toml
[project.optional-dependencies]
serve = ["textual-serve>=0.1.0"]
```

**Value**:
- Remote build monitoring
- CI/CD dashboard integration
- Team visibility into build status
- Mobile-friendly access

---

### 2. CLI Skip-to-Screen Flag (`--start`)

**Toad Pattern** (`cli.py:65, app.py:405-406`):

```python
# CLI
@click.option("-a", "--agent", metavar="AGENT", default="")
def run(agent: str):
    app = ToadApp(
        mode=None if agent_data else "store",  # Skip to store if no agent
        agent_data=agent_data,
    )

# App
async def on_mount(self) -> None:
    if mode := self._initial_mode:
        self.switch_mode(mode)
```

**Bengal Implementation**:

```python
# Already exists in app.py:82-83
def __init__(self, site=None, *, start_screen: str = "build"):
    self.start_screen = start_screen

# Just need CLI exposure:
@click.option("--start", "-s",
    type=click.Choice(["build", "serve", "health"]),
    default="build",
    help="Start on specific screen")
```

**Value**:
- Quick access to specific dashboard
- Scriptable dashboard launch
- Integration with IDE tasks

---

### 3. Landing Screen with Site Overview

**Toad Pattern** (`screens/store.py`):

StoreScreen provides:
- Version info and branding
- Quick launch grid (1-9, a-f keys)
- Categorized agent list
- Lazy content loading via `mount_compose()`

**Bengal Implementation**:

```python
# bengal/cli/dashboard/screens/landing.py

class LandingScreen(BengalScreen):
    """
    Landing screen with site overview and quick actions.

    Shows:
    - Bengal branding with version
    - Last build status summary
    - Site health score
    - Quick action grid (Build, Serve, Health)
    - Recent activity log
    """

    BINDINGS = [
        Binding("1", "goto_build", "Build", key_display="1"),
        Binding("2", "goto_serve", "Serve", key_display="2"),
        Binding("3", "goto_health", "Health", key_display="3"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with containers.VerticalGroup(id="landing-header"):
            yield Static(self._get_branding(), id="branding")
            yield Static(self._get_site_summary(), id="site-summary")

        with GridSelect(id="quick-actions", min_column_width=25):
            yield QuickAction("▶️", "Build Site", "Start a new build", id="build")
            yield QuickAction("🌐", "Dev Server", "Start development server", id="serve")
            yield QuickAction("🔍", "Health Check", "Run site validators", id="health")

        with containers.Vertical(id="activity"):
            yield Static("Recent Activity:", classes="section-header")
            yield Log(id="activity-log", auto_scroll=True)

        yield Footer()

    def _get_branding(self) -> Content:
        from bengal import __version__
        return Content.assemble(
            (BENGAL_MASCOT.cat, "$primary"),
            f" Bengal v{__version__}\n",
            ("Static Site Generator", "dim"),
        )

    def _get_site_summary(self) -> str:
        if not self.site:
            return "No site loaded"
        return f"""
Site: {self.site.title}
Pages: {len(self.site.pages)} | Assets: {len(self.site.assets)}
Last Build: {self._format_last_build()}
Health: {self._get_health_score()}%
"""
```

**Value**:
- First-run orientation
- Quick status visibility
- Keyboard-driven navigation

---

### 4. Throbber Widget (Animated Loading)

**Toad Pattern** (`widgets/throbber.py`):

```python
class ThrobberVisual(Visual):
    """Gradient animation visual."""
    gradient = Gradient.from_colors(*[Color.parse(c) for c in COLORS])

    def render_strips(self, width, height, style, options):
        time = monotonic()
        strips = [Strip([
            Segment("━", RichStyle.from_color(
                self.gradient.get_rich_color((offset / width - time) % 1.0),
                style.rich_style.bgcolor,
            ))
            for offset in range(width)
        ], width)]
        return strips

class Throbber(Widget):
    def on_mount(self) -> None:
        self.auto_refresh = 1 / 15  # 15 FPS

    def render(self) -> ThrobberVisual:
        return ThrobberVisual()
```

**Bengal Implementation**:

```python
# bengal/cli/dashboard/widgets/throbber.py

BENGAL_COLORS = [
    "#F28C28",  # Bengal orange
    "#E07020",
    "#C85A18",
    "#B04410",
    "#982E08",
    "#B04410",
    "#C85A18",
    "#E07020",
]

class BengalThrobber(Widget):
    """Animated build progress indicator with Bengal colors."""

    DEFAULT_CSS = """
    BengalThrobber {
        height: 1;
        width: 100%;
        visibility: hidden;
    }
    BengalThrobber.-active {
        visibility: visible;
    }
    """

    active = reactive(False)

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 15

    def watch_active(self, active: bool) -> None:
        self.set_class(active, "-active")

    def render(self) -> BengalThrobberVisual:
        return BengalThrobberVisual()
```

**Value**:
- Visual feedback during long operations
- Bengal branding in animation
- Professional polish

---

### 5. Type-Safe Getters Pattern

**Toad Pattern** (`screens/main.py:74-84`):

```python
from textual import getters

class MainScreen(Screen):
    # Type-safe, cached widget queries
    throbber: getters.query_one[Throbber] = getters.query_one("#throbber")
    conversation = getters.query_one(Conversation)
    side_bar = getters.query_one(SideBar)
    project_directory_tree = getters.query_one("#project_directory_tree")

    # Type-safe app access
    app = getters.app(ToadApp)
```

**Bengal Implementation**:

```python
# bengal/cli/dashboard/build.py

from textual import getters

class BengalBuildDashboard(BengalDashboard):
    # Type-safe widget access
    progress_bar: getters.query_one[ProgressBar] = getters.query_one("#build-progress")
    phase_table: getters.query_one[DataTable] = getters.query_one("#phase-table")
    build_log: getters.query_one[Log] = getters.query_one("#build-log")
    stats_panel: getters.query_one[Static] = getters.query_one("#build-stats")

    # Type-safe app access
    app = getters.app(BengalApp)

    def update_progress(self, percent: float) -> None:
        # No query_one() call needed - already typed and cached
        self.progress_bar.update(progress=percent)
```

**Benefits**:
- Compile-time type checking
- Cached queries (performance)
- Cleaner code
- IDE autocomplete

---

### 6. CSS Class Toggles for UI State

**Toad Pattern** (`toad.tcss`, `app.py:371-383`):

```css
/* CSS toggles for UI elements */
App.-hide-footer Footer { display: none; }
App.-hide-sidebar SideBar { display: none; }
App.-hide-thoughts AgentThought { display: none; }

/* State-based visibility */
Throbber { visibility: hidden; }
Throbber.-busy { visibility: visible; }
```

```python
# Python side - setting classes based on settings
def setting_updated(self, key: str, value: object) -> None:
    if key == "ui.footer":
        self.set_class(not bool(value), "-hide-footer")
    elif key == "ui.sidebar":
        self.set_class(bool(value), "-hide-sidebar")
```

**Bengal Implementation**:

```css
/* bengal.tcss additions */

/* Collapsible panels */
BengalDashboard.-hide-stats #build-stats { display: none; }
BengalDashboard.-hide-log #build-log { display: none; }
BengalDashboard.-compact-mode .section { margin: 0; padding: 0; }

/* State indicators */
.phase-row.-running { background: $primary 20%; }
.phase-row.-complete { color: $success; }
.phase-row.-error { color: $error; }

/* Loading states */
.panel.-loading { opacity: 0.5; }
.panel.-loading::after { content: "Loading..."; }
```

```python
# Python toggles
class BengalBuildDashboard(BengalDashboard):
    show_stats = reactive(True)
    show_log = reactive(True)
    compact_mode = reactive(False)

    def watch_show_stats(self, show: bool) -> None:
        self.set_class(not show, "-hide-stats")

    def watch_compact_mode(self, compact: bool) -> None:
        self.set_class(compact, "-compact-mode")
```

**Value**:
- Separation of styling from logic
- User-customizable UI
- Consistent state management

---

### 7. Command Palette with Mode/Page Search

**Toad Pattern** (`screens/main.py:29-61`):

```python
class ModeProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        screen = self.screen

        for mode in screen.conversation.modes.values():
            score = matcher.match(mode.name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(mode.name),
                    partial(screen.conversation.set_mode, mode.id),
                    help=mode.description,
                )

    async def discover(self) -> Hits:
        """Discovery hits shown before user types."""
        for mode in screen.conversation.modes.values():
            yield DiscoveryHit(
                mode.name,
                partial(screen.conversation.set_mode, mode.id),
                help=mode.description,
            )
```

**Bengal Implementation**:

```python
# bengal/cli/dashboard/commands.py

from functools import partial
from textual.command import Provider, Hit, DiscoveryHit, Hits

class BengalPageProvider(Provider):
    """Search site pages from command palette."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        site = self.app.site
        if not site:
            return

        for page in site.pages[:50]:  # Limit for performance
            score = matcher.match(page.title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(page.title),
                    partial(self._open_page, page),
                    help=page.url,
                )

    def _open_page(self, page) -> None:
        import webbrowser
        url = f"http://localhost:1313{page.url}"
        webbrowser.open(url)

    async def discover(self) -> Hits:
        yield DiscoveryHit("Build Site", lambda: self.app.action_rebuild())
        yield DiscoveryHit("Open in Browser", lambda: self.app.action_open_browser())
        yield DiscoveryHit("Check Health", lambda: self.app.switch_screen("health"))


class BengalCommandProvider(Provider):
    """Search commands and keyboard shortcuts."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        commands = [
            ("Rebuild Site", "r", self.app.action_rebuild),
            ("Clear Log", "c", self.app.action_clear_log),
            ("Toggle Stats Panel", "s", self.app.action_toggle_stats),
            ("Open in Browser", "o", self.app.action_open_browser),
            ("Show Keyboard Shortcuts", "?", self.app.action_show_help),
        ]

        for name, key, action in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    action,
                    help=f"Shortcut: {key}",
                )
```

**Value**:
- Fuzzy search for pages
- Quick command access
- Discoverability

---

### 8. Settings Signal for Reactive Updates

**Toad Pattern** (`app.py:260, 385`):

```python
class ToadApp(App):
    def __init__(self):
        self.settings_changed_signal = Signal(self, "settings_changed")

    def setting_updated(self, key: str, value: object) -> None:
        # Update UI based on setting
        if key == "ui.theme":
            self.theme = value
        # Publish for subscribers
        self.settings_changed_signal.publish((key, value))
```

```python
# In screen
async def on_mount(self) -> None:
    self.app.settings_changed_signal.subscribe(self, self.setting_updated)
```

**Bengal Implementation**:

```python
# bengal/cli/dashboard/app.py

from textual.signal import Signal

class BengalApp(App):
    def __init__(self, site=None, **kwargs):
        super().__init__(**kwargs)
        self.config_changed_signal = Signal(self, "config_changed")

    def update_config(self, key: str, value: Any) -> None:
        """Update dashboard config and notify subscribers."""
        self._config[key] = value
        self.config_changed_signal.publish((key, value))
```

**Value**:
- Decoupled configuration
- Reactive UI updates
- Screen-specific responses

---

## Architectural Comparison

| Aspect | Toad | Bengal (Current) | Bengal (Proposed) |
|--------|------|------------------|-------------------|
| Entry points | `MODES` dict | Single entry | Add `MODES` for landing |
| Screen loading | Lazy via functions | Direct instantiation | Lazy loading |
| Widget queries | `getters` pattern | `query_one()` | Adopt `getters` |
| CLI flags | `-a`, `--serve` | `--dashboard` only | Add `--start`, `--serve` |
| Settings | Signals + JSON | N/A | Add signal pattern |
| Loading indicator | `Throbber` | `ProgressBar` | Add `Throbber` |
| Command palette | `ModeProvider` | Planned | Implement with providers |

---

## Implementation Phases

### Phase 1: CLI Enhancements (1 hour)

1. Add `--start` flag to expose existing `start_screen`
2. Add `--serve` flag with `textual-serve` integration
3. Add `--port` and `--host` options
4. Update dependencies in `pyproject.toml`

### Phase 2: Widget Patterns (2 hours)

1. Create `BengalThrobber` widget
2. Adopt `getters` pattern in existing dashboards
3. Add CSS class toggles for panel visibility
4. Update `bengal.tcss` with state classes

### Phase 3: Command Palette (2 hours)

1. Implement `BengalPageProvider`
2. Implement `BengalCommandProvider`
3. Add discovery hits for common actions
4. Wire up to `BengalApp`

### Phase 4: Landing Screen (3 hours)

1. Create `LandingScreen` with site overview
2. Add `QuickAction` widget for grid
3. Add activity log
4. Wire up navigation

### Phase 5: Settings/Config (1 hour)

1. Add `config_changed_signal` to `BengalApp`
2. Add setting subscribers to screens
3. Add UI toggle settings

---

## Dependencies

### Required

```toml
[project.dependencies]
textual = ">=0.89"
```

### Optional (for web serve)

```toml
[project.optional-dependencies]
serve = ["textual-serve>=0.1.0"]
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `textual-serve` stability | Low | Medium | Make optional dependency |
| `getters` API changes | Low | Low | Pin Textual version |
| Learning curve | Medium | Low | Follow existing patterns |
| Scope creep | Medium | Medium | Phase implementation |

---

## Success Criteria

- [ ] `bengal --dashboard --serve` works in browser
- [ ] `bengal --dashboard --start health` jumps to health screen
- [ ] Throbber animates during builds
- [ ] Command palette searches pages
- [ ] All existing tests pass
- [ ] No performance regression

---

## Alternatives Considered

### 1. Full Toad Fork

**Rejected**: Toad is AGPL-licensed and designed for AI agents, not SSGs.

### 2. Minimal Enhancements Only

**Rejected**: Would miss valuable patterns that improve UX significantly.

### 3. Wait for Textual 1.0

**Rejected**: Current patterns are stable and well-documented.

---

## References

- [Toad Repository](https://github.com/batrachianai/toad)
- [Dolphie Repository](https://github.com/charles-001/dolphie)
- [Textual Documentation](https://textual.textualize.io/)
- [textual-serve](https://github.com/Textualize/textual-serve)
- [Textual Examples](https://github.com/Textualize/textual/tree/main/examples)

---

## Appendix G: Dolphie Patterns Analysis

### Overview

Dolphie is a real-time MySQL/MariaDB & ProxySQL monitoring TUI with 500+ stars. It provides excellent patterns for:
- Real-time data refresh with background workers
- Multi-tab connection management
- Comprehensive keyboard command system
- Time-series graphing with plotext
- Command palette with full command discovery

### Architecture Highlights

**File Structure**:
```
dolphie/
├── App.py              # Main app (639 lines)
├── Dolphie.py          # Core data/connection logic
├── Dolphie.tcss        # Styling (662 lines)
├── DataTypes.py        # Type definitions
├── Modules/
│   ├── TabManager.py       # Multi-tab management (900+ lines)
│   ├── KeyEventManager.py  # Full keyboard handler (1600 lines)
│   ├── CommandManager.py   # Command registry
│   ├── CommandPalette.py   # Command palette provider
│   ├── MetricManager.py    # Time-series graphing (1450 lines)
│   ├── WorkerManager.py    # Background workers
│   └── WorkerDataProcessor.py
├── Panels/             # Dashboard panels (12 panels)
└── Widgets/            # Custom widgets (9 widgets)
```

### Key Patterns for Bengal

#### 1. TabManager with Multi-Connection Support

```python
class Tab:
    """Individual tab with its own connection state."""
    def __init__(self, id: str, name: str, dolphie: Dolphie):
        self.id = id
        self.name = name
        self.dolphie = dolphie
        self.worker: Worker = None
        self.worker_timer: Timer = None
    
    def save_references_to_components(self):
        """Cache widget references for performance."""
        app = self.dolphie.app
        self.panel_dashboard = app.query_one("#panel_dashboard")
        self.panel_processlist = app.query_one("#panel_processlist")
        # ... cache all frequently accessed widgets

class TabManager:
    def __init__(self, app: App, config: Config):
        self.tabs: Dict[str, Tab] = {}
        self.active_tab: Tab = None
    
    async def create_tab(self, tab_name: str) -> Tab:
        tab_id = self.generate_tab_id()
        tab = Tab(id=tab_id, name=tab_name)
        tab.save_references_to_components()
        self.tabs[tab_id] = tab
        return tab
```

**Bengal Adaptation**: Multi-site dashboard tabs (monitor multiple sites)

#### 2. KeyEventManager (Centralized Keyboard Handling)

```python
class KeyEventManager:
    """Centralized keyboard event processing with debouncing."""
    
    def __init__(self, app: DolphieApp):
        self.last_key_time = {}
        self.default_debounce_interval = timedelta(milliseconds=50)
        self.key_debounce_intervals = {
            "space": timedelta(milliseconds=300),  # Expensive ops
            "minus": timedelta(milliseconds=300),  # Destructive
        }
    
    async def process_key_event(self, key: str) -> None:
        # Debouncing
        now = datetime.now()
        debounce = self.key_debounce_intervals.get(key, self.default_debounce_interval)
        if now - self.last_key_time.get(key, datetime.min) < debounce:
            return
        self.last_key_time[key] = now
        
        # Validate command
        if not self.app.command_manager.get_commands().get(key):
            self.app.notify(f"Key {key} is not valid", severity="warning")
            return
        
        # Execute command
        if key == "1":
            self.app.toggle_panel("dashboard")
        elif key == "r":
            self.app.push_screen(CommandModal(command=HotkeyCommands.refresh_interval))
        # ... 50+ key handlers
```

**Bengal Adaptation**: Centralized key handling with validation and debouncing

#### 3. CommandPalette with Discovery

```python
class CommandPaletteCommands(Provider):
    """Full command discovery and search."""
    
    def get_command_hits(self):
        commands = self.app.command_manager.get_commands(
            self.app.tab_manager.active_tab.dolphie.connection_source
        )
        
        max_key_length = max(len(data["human_key"]) for data in commands.values())
        
        return {
            key: {
                "display": f"[{data['human_key'].center(max_key_length)}] {data['description']}",
                "command": partial(self.async_command, key),
            }
            for key, data in commands.items()
        }
    
    async def discover(self):
        for data in self.get_command_hits().values():
            yield DiscoveryHit(display=data["display"], command=data["command"])
    
    async def search(self, query: str):
        hits = []
        for data in self.get_command_hits().values():
            score = self.matcher(query).match(data["text"])
            if score > 0:
                hits.append(Hit(score=score, match_display=data["display"], ...))
        hits.sort(key=lambda h: h.score, reverse=True)
        for hit in hits:
            yield hit
```

**Bengal Adaptation**: Show all commands with key bindings in discovery mode

#### 4. TopBar with Reactive Status

```python
class TopBar(Container):
    """Status bar with reactive properties."""
    
    host = reactive("", always_update=True)
    replay_file_size = reactive("", always_update=True)
    connection_status = reactive("")
    
    def _update_topbar_host(self):
        recording = f"| RECORDING: {format_bytes(self.replay_file_size)}" if self.replay_file_size else ""
        self.topbar_host.update(f"[{self.connection_status}] {self.host} {recording}")
    
    def watch_host(self):
        self._update_topbar_host()
    
    def compose(self) -> ComposeResult:
        yield Label(self.app_title, id="topbar_title")
        yield Label("", id="topbar_host")
        yield Label("press ? for commands", id="topbar_help")
```

**Bengal Adaptation**: Build status in top bar with reactive updates

#### 5. SpinnerWidget for Background Operations

```python
class SpinnerWidget(Static):
    """Animated spinner using Rich Spinner."""
    
    def __init__(self, id, text):
        super().__init__("")
        self._spinner = Spinner("bouncingBar", text=f"[label]{text}", speed=0.7)
    
    def on_mount(self) -> None:
        self.update_render = self.set_interval(1 / 60, self.update_spinner)
    
    def hide(self) -> None:
        self.display = False
    
    def show(self) -> None:
        self.display = True
    
    def update_spinner(self) -> None:
        self.update(self._spinner)
```

**Bengal Adaptation**: Spinner during build operations

#### 6. MetricManager with Plotext Graphs

```python
class Graph(Static):
    """Time-series graph widget using plotext."""
    
    def render_graph(self, metric_instance, datetimes):
        plt.clf()
        plt.date_form("d/m/y H:M:S")
        plt.canvas_color((10, 14, 27))
        plt.plotsize(self.size.width, self.size.height)
        
        for metric_name, metric_data in metric_instance.__dict__.items():
            if isinstance(metric_data, MetricData) and metric_data.visible:
                plt.plot(datetimes, metric_data.values, 
                        label=metric_data.label, color=metric_data.color)
        
        self.update(Text.from_ansi(plt.build()))

@dataclass
class MetricData:
    label: str
    color: tuple
    values: deque = field(default_factory=lambda: deque(maxlen=60))
    visible: bool = True
    graphable: bool = True
```

**Bengal Adaptation**: Build time graphs, page count trends

#### 7. Panel Toggle Pattern

```python
def toggle_panel(self, panel_name: str):
    """Toggle panel visibility with state tracking."""
    panel = self.tab_manager.active_tab.get_panel_widget(panel_name)
    new_display = not panel.display
    
    # Update internal state
    setattr(getattr(self.tab_manager.active_tab.dolphie.panels, panel_name), "visible", new_display)
    
    # Refresh panel content if now visible
    if panel_name not in ["graphs"]:
        self.refresh_panel(self.tab_manager.active_tab, panel_name, toggled=True)
    
    panel.display = new_display
```

#### 8. Background Worker Pattern with Thread Safety

```python
class KeyEventManager:
    def execute_command_in_thread(self, key: str, additional_data=None):
        """Run command in background thread."""
        def _run_command():
            self._execute_command(key, additional_data)
        
        thread = threading.Thread(target=_run_command, daemon=True)
        thread.start()
    
    def _execute_command(self, key: str, additional_data=None):
        """Internal implementation with thread-safe UI updates."""
        tab = self.app.tab_manager.active_tab
        
        # Show spinner safely
        self.app.call_from_thread(tab.spinner.show)
        
        try:
            # Do expensive work...
            result = self.fetch_data()
            
            # Update UI safely
            self.app.call_from_thread(self.show_result_screen, result)
        finally:
            self.app.call_from_thread(tab.spinner.hide)
```

### Dolphie CSS Patterns

```css
/* Custom scrollbar colors */
* {
    scrollbar-background: #161e31;
    scrollbar-color: #33405d;
    scrollbar-color-hover: #404f71;
}

/* DataTable styling with zebra stripes */
DataTable {
    background: #0f1525;
    
    & > .datatable--odd-row { background: #131a2c; }
    & > .datatable--even-row { background: #0f1525; }
    & > .datatable--header { background: transparent; }
}

/* TopBar layout */
TopBar {
    dock: top;
    background: #192036;
    height: 1;
    layout: horizontal;
}

/* Percentage-based widths for responsive layout */
#topbar_title { width: 15%; }
#topbar_host { width: 70%; content-align: center middle; }
#topbar_help { width: 15%; content-align: right middle; }

/* Modal styling */
ModalScreen {
    background: #0d1015 70%;
    align: center middle;
}
```

### Priority Updates from Dolphie

| Pattern | Priority | Effort |
|---------|----------|--------|
| SpinnerWidget (Rich Spinner) | **P1** | Low |
| KeyEventManager (debouncing) | **P2** | Medium |
| TopBar with reactive status | **P1** | Low |
| Plotext graphs for metrics | **P3** | Medium |
| Multi-tab TabManager | **P3** | High |
| Command discovery in palette | **P1** | Medium |

### New Bengal Widgets (from Dolphie)

1. **BengalSpinner** - Rich Spinner wrapper for async operations
2. **BengalTopBar** - Reactive status bar with build info
3. **BuildGraph** - Plotext time-series for build metrics
4. **BengalKeyManager** - Centralized keyboard handling with debouncing

---

## Deep Dive: Additional Patterns

### Pattern 1: SideBar with Collapsible Panels

**Toad Implementation** (`widgets/side_bar.py`):

```python
class SideBar(containers.Vertical):
    """Collapsible sidebar with multiple panels."""

    BINDINGS = [("escape", "dismiss", "Dismiss sidebar")]

    @dataclass(frozen=True)
    class Panel:
        title: str
        widget: Widget
        flex: bool = False  # True = grows, False = auto height
        collapsed: bool = False
        id: str | None = None

    def compose(self) -> ComposeResult:
        for panel in self.panels:
            yield widgets.Collapsible(
                panel.widget,
                title=panel.title,
                collapsed=panel.collapsed,
                classes="-flex" if panel.flex else "-fixed",
                id=panel.id,
            )
```

**Bengal Adaptation** (for build stats panel):

```python
# bengal/cli/dashboard/widgets/panels.py

from dataclasses import dataclass
from textual.widgets import Collapsible
from textual import containers

class InfoPanel(containers.Vertical):
    """Collapsible info panel with multiple sections."""

    @dataclass(frozen=True)
    class Section:
        title: str
        widget: Widget
        collapsed: bool = False

    def __init__(self, *sections: Section, **kwargs):
        super().__init__(**kwargs)
        self.sections = list(sections)

    def compose(self) -> ComposeResult:
        for section in self.sections:
            yield Collapsible(
                section.widget,
                title=section.title,
                collapsed=section.collapsed,
            )
```

**Usage in Health Dashboard**:
```python
# Group health issues by severity
yield InfoPanel(
    InfoPanel.Section("Errors", ErrorList(), collapsed=False),
    InfoPanel.Section("Warnings", WarningList(), collapsed=True),
    InfoPanel.Section("Info", InfoList(), collapsed=True),
)
```

---

### Pattern 2: Flash Notifications Widget

**Toad Implementation** (`widgets/flash.py`):

```python
class Flash(Static):
    """Inline flash notifications with auto-dismiss."""

    DEFAULT_CSS = """
    Flash {
        height: 1;
        visibility: hidden;
        text-align: center;

        &.-success { background: $success 10%; color: $text-success; }
        &.-warning { background: $warning 10%; color: $text-warning; }
        &.-error { background: $error 10%; color: $text-error; }
    }
    """

    flash_timer: var[Timer | None] = var(None)

    def flash(
        self,
        content: str | Content,
        *,
        duration: float = 3.0,
        style: Literal["success", "warning", "error"] = "default",
    ) -> None:
        if self.flash_timer is not None:
            self.flash_timer.stop()

        self.update(content)
        self.remove_class("-default", "-success", "-warning", "-error")
        self.add_class(f"-{style}")
        self.visible = True

        self.flash_timer = self.set_timer(duration, lambda: setattr(self, 'visible', False))
```

**Bengal Adaptation** (inline build status):

```python
# bengal/cli/dashboard/widgets/flash.py

class BuildFlash(Static):
    """Inline build status notifications."""

    DEFAULT_CSS = """
    BuildFlash {
        height: 1;
        visibility: hidden;
        text-align: center;

        &.-building { background: $primary 20%; color: $text-primary; }
        &.-success { background: $success 20%; color: $text-success; }
        &.-error { background: $error 20%; color: $text-error; }
    }
    """

    def show_building(self, phase: str) -> None:
        self.update(f"Building: {phase}...")
        self._apply_style("building")

    def show_success(self, duration_ms: int) -> None:
        self.update(f"✓ Build complete in {duration_ms}ms")
        self._apply_style("success")
        self.set_timer(5.0, lambda: setattr(self, 'visible', False))

    def show_error(self, message: str) -> None:
        self.update(f"✗ {message}")
        self._apply_style("error")

    def _apply_style(self, style: str) -> None:
        self.remove_class("-building", "-success", "-error")
        self.add_class(f"-{style}")
        self.visible = True
```

---

### Pattern 3: Plan Widget with Status Tracking

**Toad Implementation** (`widgets/plan.py`):

```python
class Plan(containers.Grid):
    """Grid of plan entries with status indicators."""

    @dataclass(frozen=True)
    class Entry:
        content: Content
        priority: str  # high, medium, low
        status: str    # completed, in_progress, pending

    entries: reactive[list[Entry] | None] = reactive(None, recompose=True)

    PRIORITIES = {
        "high": pill("H", "$error-muted"),
        "medium": pill("M", "$warning-muted"),
        "low": pill("L", "$primary-muted"),
    }

    def render_status(self, status: str) -> Content:
        return {
            "completed": Content.from_markup("✔ "),
            "pending": Content.styled("⏲ "),
            "in_progress": Content.from_markup("⮕"),
        }.get(status, Content())
```

**Bengal Adaptation** (build phase tracker):

```python
# bengal/cli/dashboard/widgets/phase_plan.py

@dataclass(frozen=True)
class BuildPhase:
    name: str
    status: str  # pending, running, complete, error
    duration_ms: int | None = None

class BuildPhasePlan(containers.Grid):
    """Visual build phase tracker."""

    DEFAULT_CSS = """
    BuildPhasePlan {
        grid-size: 3;
        grid-columns: auto 1fr auto;

        .phase-status { width: 3; }
        .phase-name { padding: 0 1; }
        .phase-time { color: $text-secondary; }

        .status-running { color: $primary; }
        .status-complete { color: $success; }
        .status-error { color: $error; }
    }
    """

    phases: reactive[list[BuildPhase]] = reactive([], recompose=True)

    STATUS_ICONS = {
        "pending": "○",
        "running": "●",
        "complete": "✓",
        "error": "✗",
    }

    def compose(self) -> ComposeResult:
        for phase in self.phases:
            yield Static(self.STATUS_ICONS.get(phase.status, "?"),
                        classes=f"phase-status status-{phase.status}")
            yield Static(phase.name, classes=f"phase-name status-{phase.status}")
            yield Static(
                f"{phase.duration_ms}ms" if phase.duration_ms else "",
                classes="phase-time"
            )
```

---

### Pattern 4: Searchable Settings Screen

**Toad Implementation** (`screens/settings.py`):

```python
class SettingsScreen(ModalScreen):
    AUTO_FOCUS = "Input#search"

    def compose(self) -> ComposeResult:
        with containers.Vertical(id="contents"):
            yield Input(id="search", placeholder="Search settings")
            with lazy.Reveal(containers.VerticalScroll()):
                yield from self._generate_settings()

    def filter_settings(self, search_term: str) -> None:
        search_term = search_term.lower()
        for setting in self.query(".setting"):
            if setting.name:
                setting.display = search_term in setting.name

    @on(Input.Changed, "#search")
    def on_search_input(self, event: Input.Changed) -> None:
        self.filter_settings(event.value)
```

**Bengal Adaptation** (searchable page/health explorer):

```python
# bengal/cli/dashboard/widgets/searchable_list.py

class SearchableList(containers.Vertical):
    """List widget with search filtering."""

    def compose(self) -> ComposeResult:
        yield Input(id="search", placeholder="Filter...")
        yield containers.VerticalScroll(id="items")

    @on(Input.Changed, "#search")
    def filter_items(self, event: Input.Changed) -> None:
        term = event.value.lower()
        for item in self.query_one("#items").query(".list-item"):
            item.display = term in (item.name or "").lower()
```

---

### Pattern 5: ProjectDirectoryTree with .gitignore

**Toad Implementation** (`widgets/project_directory_tree.py`):

```python
class ProjectDirectoryTree(DirectoryTree):
    """Directory tree that respects .gitignore."""

    @work(thread=True)
    async def load_path_spec(self, git_ignore_path: Path) -> PathSpec | None:
        if git_ignore_path.is_file():
            spec_text = git_ignore_path.read_text()
            return PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                spec_text.splitlines()
            )
        return None

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if path_spec := self._path_spec:
            for path in paths:
                if not path_spec.match_file(path):
                    yield path
        yield from paths
```

**Bengal Adaptation** (content tree explorer):

```python
# bengal/cli/dashboard/widgets/content_tree.py

class ContentTree(DirectoryTree):
    """Directory tree for site content."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter to show only content files."""
        for path in paths:
            if path.is_dir():
                yield path
            elif path.suffix in {".md", ".html", ".yaml", ".toml"}:
                yield path
```

---

### Pattern 6: Modal Dialogs with Action Dismiss

**Toad Pattern** (dismiss on escape, focus trapping):

```python
class SideBar(containers.Vertical):
    BINDINGS = [("escape", "dismiss", "Dismiss sidebar")]

    class Dismiss(Message):
        pass

    def on_mount(self) -> None:
        self.trap_focus()

    def action_dismiss(self) -> None:
        self.post_message(self.Dismiss())
```

**Bengal Adaptation** (confirmation dialogs):

```python
# bengal/cli/dashboard/widgets/confirm.py

class ConfirmDialog(containers.Vertical):
    """Confirmation dialog with focus trapping."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    class Confirmed(Message):
        pass

    class Cancelled(Message):
        pass

    def on_mount(self) -> None:
        self.trap_focus()

    def action_confirm(self) -> None:
        self.post_message(self.Confirmed())

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())
```

---

### Pattern 7: Reactive Recompose

**Toad Pattern** (`widgets/plan.py`):

```python
class Plan(containers.Grid):
    # When entries changes, entire widget recomposes
    entries: reactive[list[Entry] | None] = reactive(None, recompose=True)

    def watch_entries(self, old_entries: list[Entry], new_entries: list[Entry]) -> None:
        # Track newly completed for animation
        entry_map = {e.content: e for e in old_entries}
        self.newly_completed = {
            e for e in new_entries
            if e.status == "completed" and entry_map.get(e.content, {}).status != "completed"
        }
```

**Bengal Adaptation** (build stats that recompose):

```python
class BuildStats(containers.VerticalGroup):
    """Build statistics that auto-update."""

    stats: reactive[dict | None] = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        if not self.stats:
            yield Static("No stats yet")
            return

        yield Static(f"Pages: {self.stats.get('pages', 0)}")
        yield Static(f"Assets: {self.stats.get('assets', 0)}")
        yield Static(f"Duration: {self.stats.get('duration_ms', 0)}ms")
```

---

### Pattern 8: check_action for Conditional Bindings

**Toad Pattern** (`screens/settings.py`):

```python
def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
    """Control whether action is available."""
    if action == "focus":
        if not self.is_mounted:
            return None  # Unknown yet
        return None if self.search_input.has_focus else True
    return True
```

**Bengal Adaptation** (disable rebuild during build):

```python
class BuildScreen(BengalScreen):
    is_building = reactive(False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Disable rebuild action while building."""
        if action == "rebuild":
            return not self.is_building
        return True
```

---

## Appendix A: Toad File Analysis

### `app.py` (479 lines)

Key patterns:
- `SCREENS` dict for lazy screen loading
- `MODES` dict for entry point modes
- `get_default_screen()` factory method
- Settings with `cached_property`
- `@work` decorator for background tasks
- Double Ctrl+C quit pattern
- Version check in background

### `cli.py` (249 lines)

Key patterns:
- Custom `DefaultCommandGroup` for implicit default command
- `-a/--agent` for skip-to-agent
- `--serve` with `textual_serve.server.Server`
- Subcommands: `run`, `acp`, `settings`, `serve`, `about`

### `screens/store.py` (443 lines)

Key patterns:
- `GridSelect` for keyboard-navigable grid
- Quick launch with digit keys (1-9, a-f)
- `compose_agents()` separate from `compose()`
- `mount_compose()` for lazy content
- `LaunchAgent` message for screen transitions
- Settings signal subscription

### `screens/main.py` (187 lines)

Key patterns:
- `ModeProvider` for command palette
- `getters` for type-safe queries
- `AUTO_FOCUS` for initial focus
- `data_bind()` for reactive properties
- `check_action()` for conditional bindings

### `widgets/throbber.py` (91 lines)

Key patterns:
- Custom `Visual` for rendering
- Gradient animation with `monotonic()`
- `auto_refresh` for animation FPS
- Clean separation of visual from widget

### `widgets/grid_select.py` (209 lines)

Key patterns:
- Cursor navigation (up/down/left/right)
- Highlight management with reactive
- Click handling with ancestor walk
- `Selected` message for selection

### `toad.tcss` (678 lines)

Key patterns:
- Conditional classes (`.-hide-footer`, `.-busy`)
- State-based visibility
- Theme variables extensively
- Footer customization
- Scrollbar sizing variants

---

## Appendix B: Bengal Comparison Files

| Toad File | Bengal Equivalent | Gap |
|-----------|-------------------|-----|
| `app.py` | `dashboard/app.py` | MODES, signals |
| `cli.py` | `cli/main.py` | --serve, --start |
| `screens/store.py` | N/A | Landing screen |
| `screens/main.py` | `dashboard/screens.py` | getters, providers |
| `widgets/throbber.py` | N/A | Throbber widget |
| `widgets/grid_select.py` | N/A | GridSelect widget |
| `toad.tcss` | `dashboard/bengal.tcss` | State classes |
| `widgets/side_bar.py` | N/A | Collapsible panels |
| `widgets/flash.py` | N/A | Flash notifications |
| `widgets/plan.py` | N/A | Phase tracker |
| `widgets/project_directory_tree.py` | N/A | Filtered tree |
| `screens/settings.py` | N/A | Settings screen |

---

## Appendix C: Widget Inventory

### Toad Widgets (33 total)

**High Value for Bengal**:
- `throbber.py` - Animated loading indicator
- `grid_select.py` - Keyboard-navigable grid
- `side_bar.py` - Collapsible panel container
- `flash.py` - Inline flash notifications
- `plan.py` - Status tracking grid
- `project_directory_tree.py` - Filtered directory tree

**Medium Value** (domain-specific but adaptable):
- `conversation.py` - Scrollable content area with cursor
- `prompt.py` - Input with rich features
- `menu.py` - Dropdown/popup menus
- `welcome.py` - Branding/welcome screen

**Low Value** (AI-agent specific):
- `agent_response.py`, `agent_thought.py`
- `terminal.py`, `shell_terminal.py`
- `tool_call.py`, `terminal_tool.py`

### Proposed Bengal Widgets

**Phase 1** (Dashboard Enrichment):
- `BengalThrobber` - Animated build progress
- `BuildFlash` - Inline build status
- `BuildPhasePlan` - Phase status tracker
- `ContentTree` - Filtered content tree

**Phase 2** (Landing Screen):
- `QuickAction` - Grid action item
- `SiteOverview` - Site summary panel
- `ActivityLog` - Recent activity

**Phase 3** (Settings/Config):
- `SettingsScreen` - Dashboard preferences
- `SearchableList` - Filtered list widget

---

## Appendix D: CSS Patterns Catalog

### State Classes

```css
/* Visibility toggle */
.widget.-hidden { display: none; }
.widget.-collapsed { height: auto; }

/* Loading state */
.widget.-loading { opacity: 0.5; }
.widget.-busy { /* animated */ }

/* Status colors */
.status.-success { color: $success; }
.status.-warning { color: $warning; }
.status.-error { color: $error; }
.status.-info { color: $primary; }

/* Phase states */
.phase.-pending { opacity: 0.6; }
.phase.-running { background: $primary 10%; }
.phase.-complete { text-style: bold; }
.phase.-error { background: $error 10%; }
```

### Layout Utilities

```css
/* Responsive panels */
@media (width < 80) {
    .panel.-responsive { display: none; }
}

/* Flex shortcuts */
.flex-1 { height: 1fr; }
.flex-auto { height: auto; }

/* Scrollbar control */
.no-scrollbar { scrollbar-size: 0 0; }
.thin-scrollbar { scrollbar-size: 1 1; }
```

### Animation Patterns

```css
/* Blink animation via timer + class toggle */
.cursor.-blink { opacity: 0.3; }

/* Gradient animation via custom Visual */
/* See throbber.py for implementation */
```

---

## Appendix E: Priority Matrix

| Enhancement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| `--start` CLI flag | High | Low | **P0** |
| `--serve` web mode | High | Medium | **P1** |
| Throbber widget | Medium | Low | **P1** |
| Command palette providers | High | Medium | **P1** |
| CSS state classes | Medium | Low | **P1** |
| Type-safe getters | Medium | Medium | **P2** |
| Landing screen | Medium | High | **P2** |
| Flash notifications | Low | Low | **P2** |
| Settings screen | Low | High | **P3** |
| GridSelect widget | Low | Medium | **P3** |

**Priority Key**:
- **P0**: Quick win, do immediately
- **P1**: High value, include in next sprint
- **P2**: Good to have, schedule after P1
- **P3**: Nice to have, backlog

---

## Appendix F: Implementation Checklist

### Quick Wins (P0, < 1 hour each)

- [ ] Add `--start` flag to dashboard CLI
- [ ] Add state classes to `bengal.tcss`
- [ ] Update Footer bindings to show current screen

### Sprint 1 (P1, ~8 hours total)

- [ ] Implement `BengalThrobber` widget
- [ ] Add `--serve` flag with `textual-serve`
- [ ] Implement `BengalPageProvider` for command palette
- [ ] Implement `BengalCommandProvider` for command palette
- [ ] Add type-safe getters to build/serve/health screens

### Sprint 2 (P2, ~10 hours total)

- [ ] Create `LandingScreen` with site overview
- [ ] Add `QuickAction` grid widget
- [ ] Implement `BuildFlash` inline notifications
- [ ] Add config signal for reactive updates

### Backlog (P3)

- [ ] Settings screen with search
- [ ] GridSelect for navigation
- [ ] Collapsible info panels
