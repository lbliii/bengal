# Plan: Toad-Inspired Dashboard Enhancements

**Status**: Draft  
**RFC**: [rfc-toad-inspired-enhancements.md](./rfc-toad-inspired-enhancements.md)  
**Created**: 2024-12-21  
**Estimated Total Effort**: ~20 hours

---

## Overview

Implement dashboard enhancements inspired by Toad and Dolphie patterns, prioritized by impact/effort ratio.

**Key Deliverables**:
1. CLI enhancements (`--start`, `--serve`)
2. New widgets (Throbber, Flash, BuildPhasePlan)
3. Command palette providers
4. CSS state management patterns
5. Landing screen (P2)

---

## Phase 0: Quick Wins (P0)

**Effort**: 1 hour  
**Dependencies**: None

### Task 0.1: Add `--start` CLI Flag

**File**: `bengal/cli/commands/dashboard.py`

- [ ] Add `--start/-s` option with choices `["build", "serve", "health"]`
- [ ] Wire to existing `start_screen` parameter in `BengalApp`
- [ ] Update help text

```bash
git add -A && git commit -m "cli(dashboard): add --start flag to skip directly to specific screen"
```

### Task 0.2: Add CSS State Classes

**File**: `bengal/cli/dashboard/bengal.tcss`

- [ ] Add visibility toggles (`.widget.-hidden`, `.widget.-collapsed`)
- [ ] Add loading states (`.widget.-loading`, `.widget.-busy`)
- [ ] Add status colors (`.status.-success`, `.status.-warning`, `.status.-error`)
- [ ] Add phase states (`.phase.-pending`, `.phase.-running`, `.phase.-complete`, `.phase.-error`)

```bash
git add -A && git commit -m "cli(dashboard): add CSS state classes for visibility, loading, and status"
```

### Task 0.3: Update Footer with Screen Context

**File**: `bengal/cli/dashboard/base.py`

- [ ] Add current screen indicator to footer
- [ ] Show screen-specific key bindings

```bash
git add -A && git commit -m "cli(dashboard): enhance footer with screen context and bindings"
```

---

## Phase 1: Core Widget Patterns (P1)

**Effort**: 4 hours  
**Dependencies**: Phase 0

### Task 1.1: Create BengalThrobber Widget

**File**: `bengal/cli/dashboard/widgets/throbber.py` (new)

- [ ] Create `BengalThrobberVisual` class extending `Visual`
- [ ] Implement gradient animation with Bengal colors (`#F28C28` through `#982E08`)
- [ ] Create `BengalThrobber` widget with `active` reactive property
- [ ] Set `auto_refresh = 1/15` for 15 FPS animation
- [ ] Add CSS with `visibility: hidden` default, `-active` class for visible

```bash
git add -A && git commit -m "cli(widgets): add BengalThrobber animated loading indicator with Bengal color gradient"
```

### Task 1.2: Integrate Throbber in Build Dashboard

**File**: `bengal/cli/dashboard/build.py`

- [ ] Add `BengalThrobber` to compose
- [ ] Set `throbber.active = True` when build starts
- [ ] Set `throbber.active = False` when build completes/errors

```bash
git add -A && git commit -m "cli(dashboard): integrate BengalThrobber in build dashboard"
```

### Task 1.3: Create BuildFlash Widget

**File**: `bengal/cli/dashboard/widgets/flash.py` (new)

- [ ] Create `BuildFlash` widget extending `Static`
- [ ] Implement `show_building(phase: str)`, `show_success(duration_ms: int)`, `show_error(message: str)`
- [ ] Add auto-dismiss timer for success messages (5 seconds)
- [ ] Add CSS with `-building`, `-success`, `-error` states

```bash
git add -A && git commit -m "cli(widgets): add BuildFlash inline notification widget with auto-dismiss"
```

### Task 1.4: Create BuildPhasePlan Widget

**File**: `bengal/cli/dashboard/widgets/phase_plan.py` (new)

- [ ] Create `BuildPhase` dataclass with `name`, `status`, `duration_ms`
- [ ] Create `BuildPhasePlan` widget extending `containers.Grid`
- [ ] Implement grid with 3 columns: status icon, name, duration
- [ ] Add reactive `phases` property with `recompose=True`
- [ ] Status icons: `○` pending, `●` running, `✓` complete, `✗` error

```bash
git add -A && git commit -m "cli(widgets): add BuildPhasePlan visual phase tracker with status icons"
```

### Task 1.5: Adopt Type-Safe Getters Pattern

**Files**:
- `bengal/cli/dashboard/build.py`
- `bengal/cli/dashboard/serve.py`
- `bengal/cli/dashboard/health.py`

- [ ] Import `getters` from textual
- [ ] Replace `query_one()` calls with class-level getter definitions
- [ ] Add `app = getters.app(BengalApp)` for type-safe app access
- [ ] Verify type hints work with IDE

```bash
git add -A && git commit -m "cli(dashboard): adopt type-safe getters pattern for widget queries"
```

---

## Phase 2: Web Serve Mode (P1)

**Effort**: 2 hours  
**Dependencies**: Phase 0

### Task 2.1: Add textual-serve Optional Dependency

**File**: `pyproject.toml`

- [ ] Add `serve = ["textual-serve>=0.1.0"]` to `[project.optional-dependencies]`
- [ ] Verify minimum Textual version is `>=0.89`

```bash
git add -A && git commit -m "config: add textual-serve as optional dependency for web dashboard"
```

### Task 2.2: Implement `--serve` Flag

**File**: `bengal/cli/commands/dashboard.py`

- [ ] Add `--serve` boolean flag
- [ ] Add `--port` option with default 8000
- [ ] Add `--host` option with default "localhost"
- [ ] Import `textual_serve.server.Server` conditionally
- [ ] Reconstruct command without `--serve` to avoid recursion
- [ ] Add error handling for missing `textual-serve` dependency

```bash
git add -A && git commit -m "cli(dashboard): add --serve flag for web-based dashboard access via textual-serve"
```

### Task 2.3: Add Serve Mode Documentation

**File**: `site/content/reference/cli.md`

- [ ] Document `--serve` flag usage
- [ ] Add examples for remote access
- [ ] Note optional dependency installation

```bash
git add -A && git commit -m "docs: document dashboard --serve flag for web access"
```

---

## Phase 3: Command Palette Providers (P1)

**Effort**: 3 hours  
**Dependencies**: Phase 0

### Task 3.1: Create BengalPageProvider

**File**: `bengal/cli/dashboard/commands.py` (new)

- [ ] Create `BengalPageProvider` extending `Provider`
- [ ] Implement `search(query: str)` with fuzzy matching on page titles
- [ ] Limit to 50 pages for performance
- [ ] Implement `_open_page(page)` to open in browser
- [ ] Yield `Hit` with score, highlighted title, and URL as help text

```bash
git add -A && git commit -m "cli(commands): add BengalPageProvider for fuzzy page search in command palette"
```

### Task 3.2: Create BengalCommandProvider

**File**: `bengal/cli/dashboard/commands.py`

- [ ] Create `BengalCommandProvider` extending `Provider`
- [ ] Define command registry with name, key, action tuples
- [ ] Implement `search(query: str)` with fuzzy matching
- [ ] Show keyboard shortcut in help text

```bash
git add -A && git commit -m "cli(commands): add BengalCommandProvider for keyboard shortcut discovery"
```

### Task 3.3: Implement Discovery Hits

**File**: `bengal/cli/dashboard/commands.py`

- [ ] Add `discover()` method to both providers
- [ ] Yield `DiscoveryHit` for common actions:
  - Build Site
  - Open in Browser
  - Check Health
  - Toggle Stats
  - Show Keyboard Shortcuts

```bash
git add -A && git commit -m "cli(commands): add discovery hits for quick command access before typing"
```

### Task 3.4: Wire Providers to BengalApp

**File**: `bengal/cli/dashboard/app.py`

- [ ] Add `COMMAND_PROVIDERS` class variable with providers
- [ ] Import and register `BengalPageProvider`, `BengalCommandProvider`

```bash
git add -A && git commit -m "cli(dashboard): wire command palette providers to BengalApp"
```

---

## Phase 4: Config Signal Pattern (P2)

**Effort**: 2 hours  
**Dependencies**: Phase 1

### Task 4.1: Add Config Signal to BengalApp

**File**: `bengal/cli/dashboard/app.py`

- [ ] Import `Signal` from textual
- [ ] Add `config_changed_signal = Signal(self, "config_changed")` in `__init__`
- [ ] Create `update_config(key: str, value: Any)` method
- [ ] Publish signal on config changes

```bash
git add -A && git commit -m "cli(dashboard): add config_changed_signal for reactive config updates"
```

### Task 4.2: Add UI Toggle Reactives

**File**: `bengal/cli/dashboard/build.py`

- [ ] Add `show_stats = reactive(True)`
- [ ] Add `show_log = reactive(True)`
- [ ] Add `compact_mode = reactive(False)`
- [ ] Implement watchers that toggle CSS classes

```bash
git add -A && git commit -m "cli(dashboard): add reactive UI toggle properties with CSS class binding"
```

### Task 4.3: Subscribe Screens to Config Signal

**Files**: `bengal/cli/dashboard/screens.py`

- [ ] Subscribe to `config_changed_signal` in `on_mount`
- [ ] Implement `setting_updated(key, value)` handler
- [ ] Update relevant reactive properties based on key

```bash
git add -A && git commit -m "cli(dashboard): subscribe screens to config signal for reactive updates"
```

---

## Phase 5: Landing Screen (P2)

**Effort**: 5 hours  
**Dependencies**: Phases 1-4

### Task 5.1: Create QuickAction Widget

**File**: `bengal/cli/dashboard/widgets/quick_action.py` (new)

- [ ] Create `QuickAction` widget with emoji, title, description
- [ ] Add hover/focus styling
- [ ] Emit `Selected` message on click/enter

```bash
git add -A && git commit -m "cli(widgets): add QuickAction grid item widget"
```

### Task 5.2: Create LandingScreen

**File**: `bengal/cli/dashboard/screens/landing.py` (new)

- [ ] Create `LandingScreen` extending `BengalScreen`
- [ ] Add bindings for 1/2/3 quick navigation
- [ ] Compose with Header, branding, site summary
- [ ] Add QuickAction grid for Build/Serve/Health
- [ ] Add activity Log widget

```bash
git add -A && git commit -m "cli(screens): add LandingScreen with site overview and quick actions"
```

### Task 5.3: Implement Branding Display

**File**: `bengal/cli/dashboard/screens/landing.py`

- [ ] Add Bengal mascot/logo (ASCII art or styled text)
- [ ] Display version from `bengal.__version__`
- [ ] Add tagline "Static Site Generator"

```bash
git add -A && git commit -m "cli(screens): add Bengal branding to landing screen"
```

### Task 5.4: Implement Site Summary

**File**: `bengal/cli/dashboard/screens/landing.py`

- [ ] Display site title
- [ ] Show page count and asset count
- [ ] Show last build timestamp (if available)
- [ ] Show health score percentage

```bash
git add -A && git commit -m "cli(screens): add site summary panel to landing screen"
```

### Task 5.5: Wire Landing Screen to App

**File**: `bengal/cli/dashboard/app.py`

- [ ] Add `LandingScreen` to `SCREENS` dict
- [ ] Add `MODES` dict with `landing` as entry point
- [ ] Update `--start` to include `landing` option
- [ ] Make landing the default start screen

```bash
git add -A && git commit -m "cli(dashboard): wire LandingScreen as default entry point"
```

---

## Phase 6: Polish & Tests (P1)

**Effort**: 3 hours  
**Dependencies**: Phases 1-5

### Task 6.1: Add Widget Unit Tests

**File**: `tests/unit/cli/dashboard/test_widgets.py` (new)

- [ ] Test `BengalThrobber` active/inactive states
- [ ] Test `BuildFlash` message display and auto-dismiss
- [ ] Test `BuildPhasePlan` phase updates and recompose

```bash
git add -A && git commit -m "tests: add unit tests for dashboard widgets"
```

### Task 6.2: Add Provider Unit Tests

**File**: `tests/unit/cli/dashboard/test_commands.py` (new)

- [ ] Test `BengalPageProvider` search returns correct hits
- [ ] Test `BengalCommandProvider` discovery returns all commands
- [ ] Test fuzzy matching behavior

```bash
git add -A && git commit -m "tests: add unit tests for command palette providers"
```

### Task 6.3: Add Integration Tests

**File**: `tests/integration/cli/test_dashboard.py`

- [ ] Test dashboard launches with `--start` flags
- [ ] Test screen navigation via keyboard
- [ ] Test command palette opens and searches

```bash
git add -A && git commit -m "tests(integration): add dashboard launch and navigation tests"
```

### Task 6.4: Performance Verification

- [ ] Verify no animation jank (throbber at 15 FPS)
- [ ] Verify command palette search is responsive (<100ms)
- [ ] Verify landing screen loads quickly with large sites

```bash
git add -A && git commit -m "perf: verify dashboard performance meets targets"
```

---

## Backlog (P3)

Future enhancements not in current scope:

### Settings Screen
- [ ] Create `SettingsScreen` with searchable settings
- [ ] Add persistent settings storage (JSON/TOML)
- [ ] Wire to config signal

### GridSelect Widget
- [ ] Port full `GridSelect` from Toad
- [ ] Implement cursor navigation
- [ ] Add keyboard shortcuts (1-9, a-f)

### Collapsible Panels
- [ ] Create `InfoPanel` with collapsible sections
- [ ] Group health issues by severity
- [ ] Add to health dashboard

### Multi-Tab Support
- [ ] Port `TabManager` from Dolphie
- [ ] Support multiple site monitoring
- [ ] Tab-specific state management

### Time-Series Graphs
- [ ] Add `plotext` integration
- [ ] Create `BuildGraph` widget
- [ ] Track build times over sessions

---

## File Manifest

### New Files

| File | Description |
|------|-------------|
| `bengal/cli/dashboard/widgets/throbber.py` | Animated loading indicator |
| `bengal/cli/dashboard/widgets/flash.py` | Inline notifications |
| `bengal/cli/dashboard/widgets/phase_plan.py` | Build phase tracker |
| `bengal/cli/dashboard/widgets/quick_action.py` | Landing screen grid item |
| `bengal/cli/dashboard/commands.py` | Command palette providers |
| `bengal/cli/dashboard/screens/landing.py` | Landing screen |
| `tests/unit/cli/dashboard/test_widgets.py` | Widget tests |
| `tests/unit/cli/dashboard/test_commands.py` | Provider tests |

### Modified Files

| File | Changes |
|------|---------|
| `bengal/cli/commands/dashboard.py` | Add `--start`, `--serve`, `--port`, `--host` |
| `bengal/cli/dashboard/app.py` | Add MODES, signal, providers |
| `bengal/cli/dashboard/bengal.tcss` | Add state classes |
| `bengal/cli/dashboard/base.py` | Update footer |
| `bengal/cli/dashboard/build.py` | Add throbber, getters, reactives |
| `bengal/cli/dashboard/serve.py` | Add getters |
| `bengal/cli/dashboard/health.py` | Add getters |
| `bengal/cli/dashboard/screens.py` | Add signal subscription |
| `pyproject.toml` | Add textual-serve optional dep |

---

## Success Criteria

- [ ] `bengal --dashboard --serve` opens in browser
- [ ] `bengal --dashboard --start health` jumps to health screen
- [ ] Throbber animates during builds
- [ ] Command palette finds pages by title
- [ ] Command palette shows keyboard shortcuts
- [ ] Landing screen displays site summary
- [ ] All existing tests pass
- [ ] No performance regression (build dashboard <100ms)

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| `textual-serve` instability | Make optional, graceful error |
| `getters` API changes | Pin Textual version |
| Animation performance | Use 15 FPS cap, simple gradient |
| Scope creep | Strict phase boundaries |

---

## Sprint Mapping

**Sprint 1** (Week 1): Phases 0-2
- Quick wins + Core widgets + Web serve
- ~7 hours

**Sprint 2** (Week 2): Phases 3-4
- Command palette + Config signal
- ~5 hours

**Sprint 3** (Week 3): Phases 5-6
- Landing screen + Tests
- ~8 hours
