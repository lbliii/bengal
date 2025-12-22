# RFC: Bengal Terminal UX with Textual

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2024-12-21  
**Subsystem**: CLI / Output  

---

## Summary

Adopt Textual as Bengal's terminal UI framework, replacing direct Rich usage. This unifies the CLI stack around **Click + Textual**, enables interactive dashboards, and allows sharing design tokens between web and terminal output.

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
5. **Reduce dependencies** — Textual includes Rich

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

### 4. Component Library

#### Standard Output (Rich-based, unchanged)

```python
# bengal/output/core.py
from rich.console import Console
from textual.app import App  # Available if needed

class CLIOutput:
    """Standard CLI output using Rich (included in Textual)."""

    def __init__(self):
        self.console = Console()

    def header(self, text: str) -> None:
        self.console.print(f"[bold orange1]ᓚᘏᗢ  {text}[/]")

    def success(self, text: str) -> None:
        self.console.print(f"[green]✓[/] {text}")

    def error(self, text: str) -> None:
        self.console.print(f"[red bold]x[/] {text}")
```

#### Dashboard Mode (Textual TUI)

```python
# bengal/cli/dashboard/build.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, ProgressBar, Static, Log
from textual.containers import Container, Horizontal, Vertical

class BengalBuildDashboard(App):
    """Interactive build dashboard."""

    CSS_PATH = "bengal.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "rebuild", "Rebuild"),
        ("c", "clear_cache", "Clear Cache"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Static("ᓚᘏᗢ", id="mascot", classes="mascot"),
                Static("Bengal Build", id="title"),
            ),
            ProgressBar(id="progress", total=100),
            DataTable(id="phases"),
            Log(id="output"),
            id="main"
        )
        yield Footer()

    def on_mount(self) -> None:
        # Initialize phase table
        table = self.query_one("#phases", DataTable)
        table.add_columns("Phase", "Time", "Details", "Status")

    def update_phase(self, name: str, time_ms: int, details: str, status: str) -> None:
        """Update phase in the table."""
        table = self.query_one("#phases", DataTable)
        icon = "✓" if status == "complete" else "⠹" if status == "running" else "·"
        table.add_row(name, f"{time_ms}ms", details, icon)
```

#### Dev Server Dashboard

```python
# bengal/cli/dashboard/serve.py
class BengalServeDashboard(App):
    """Live dev server dashboard."""

    CSS_PATH = "bengal.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "rebuild", "Rebuild"),
        ("o", "open_browser", "Open"),
        ("c", "clear_cache", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("ᓚᘏᗢ  Serving at http://localhost:3000", id="status"),
            TabbedContent(
                TabPane("Changes", Log(id="changes")),
                TabPane("Build", DataTable(id="stats")),
                TabPane("Errors", Log(id="errors")),
            ),
            id="main"
        )
        yield Footer()
```

#### Health Report Explorer

```python
# bengal/cli/dashboard/health.py
class BengalHealthDashboard(App):
    """Interactive health report explorer."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Tree("Health Report", id="tree"),
            Static(id="details"),
            id="main"
        )
        yield Footer()

    def on_tree_node_selected(self, event) -> None:
        """Show details when node selected."""
        details = self.query_one("#details", Static)
        details.update(event.node.data.get("details", ""))
```

### 5. CLI Integration

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
        app = BengalBuildDashboard()
        app.run()
    else:
        # Standard Rich output (existing behavior)
        from bengal.orchestration import build_site
        build_site(output=output, parallel=parallel)
```

### 6. Brand Identity

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

### Phase 1: Add Textual Dependency (Week 1)

1. Replace `rich` with `textual` in dependencies
2. Update imports (Rich is still available via Textual)
3. Verify existing output unchanged
4. Add `bengal.tcss` with shared tokens

**Effort**: 0.5 days  
**Risk**: Low (Rich API unchanged)

### Phase 2: Build Dashboard (Week 2)

1. Create `BengalBuildDashboard` class
2. Add `--dashboard` flag to `bengal build`
3. Wire up build events to dashboard updates
4. Test across terminals

**Effort**: 2-3 days  
**Risk**: Medium (new feature)

### Phase 3: Serve Dashboard (Week 3)

1. Create `BengalServeDashboard` class
2. Add `--dashboard` flag to `bengal serve`
3. Integrate file watcher events
4. Add keyboard shortcuts

**Effort**: 2-3 days  
**Risk**: Medium (event integration)

### Phase 4: Shared Tokens (Week 4)

1. Create token generator script
2. Generate CSS from Python tokens
3. Generate `.tcss` from same tokens
4. Document token system

**Effort**: 1-2 days  
**Risk**: Low (tooling)

---

## Effort Summary

| Phase | Work | Days |
|-------|------|------|
| Textual integration | Swap dependency, verify | 0.5 |
| Build dashboard | TUI + build integration | 2-3 |
| Serve dashboard | TUI + file watcher | 2-3 |
| Token system | Generator + docs | 1-2 |
| **Total** | | **6-9 days** |

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

1. **Textual-web**: Should `bengal serve --dashboard` be accessible via browser?
2. **Token generation**: Build-time or commit-time token generation?
3. **Palette switching**: Support `--palette charcoal-bengal` in terminal?

---

## References

### Bengal Codebase
- `bengal/utils/rich_console.py` — Current Rich theme
- `bengal/output/core.py` — CLIOutput class
- `bengal/output/icons.py` — Icon definitions
- `bengal/themes/default/assets/css/tokens/` — Web token system

### Textual Documentation
- [Textual Home](https://textual.textualize.io/)
- [Textual CSS Guide](https://textual.textualize.io/guide/CSS/)
- [Textual Widgets](https://textual.textualize.io/widgets/)
- [Textual Themes](https://textual.textualize.io/guide/themes/)

---

## Appendix: Dashboard Mockup

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
│  [q] Quit  [r] Rebuild  [c] Clear Cache                     │
└─────────────────────────────────────────────────────────────┘
```

### Serve Dashboard

```
┌─ Bengal Dev Server ─────────────────────────────────────────┐
│                                                             │
│  ᓚᘏᗢ  Serving at http://localhost:3000                      │
│                                                             │
│  ┌─ Changes ─────────────────────────────────────────────┐  │
│  │ ● content/blog/new-post.md          Modified  2s ago  │  │
│  │ ● themes/default/templates/base.html  Modified  45s   │  │
│  │ ○ Watching 245 files...                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Last Build ──────────────────────────────────────────┐  │
│  │ ✓ 0.82s  │  245 pages  │  134 assets  │  A (94/100)   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [q] Quit  [r] Rebuild  [o] Open Browser  [c] Clear Cache   │
└─────────────────────────────────────────────────────────────┘
```
