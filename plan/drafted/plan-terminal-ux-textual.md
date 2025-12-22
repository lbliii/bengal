# Plan: Bengal Terminal UX with Textual

**RFC**: `rfc-terminal-ux-textual.md`  
**Status**: Draft  
**Created**: 2024-12-21  
**Estimated Time**: 14-16 days (see priority breakdown for MVP)

---

## Summary

Implement Textual-based terminal dashboards for Bengal, replacing direct Rich usage. This enables interactive dashboards for `bengal build`, `bengal serve`, and `bengal health` commands while maintaining backward compatibility with standard CLI output.

---

## Priority Breakdown

| Priority | Features | Days |
|----------|----------|------|
| 🔴 **MVP** | Foundation + Build + Serve dashboards | 5-6 |
| 🟡 **Enhanced** | Health dashboard + Command palette | 3-5 |
| 🟢 **Polish** | Animations, testing, unified app | 2-4 |

---

## Tasks

### Phase 1: Foundation (0.5 days)

#### Task 1.1: Replace Rich with Textual in Dependencies
- **Files**: `pyproject.toml`
- **Action**: Replace `rich>=13.7.0` with `textual>=0.89` in dependencies
- **Commit**: `deps: replace rich with textual (includes rich); add pytest-textual-snapshot dev dep`

#### Task 1.2: Verify Rich Import Compatibility
- **Files**: `bengal/utils/rich_console.py`, `bengal/output/core.py`
- **Action**: Verify that all `from rich.*` imports still work (Textual re-exports Rich)
- **Depends on**: Task 1.1
- **Commit**: `output: verify rich imports work via textual; no code changes needed`

#### Task 1.3: Add Test Fixtures for Dashboard Testing
- **Files**: `tests/dashboard/__init__.py`, `tests/dashboard/conftest.py`
- **Action**: Create dashboard test directory with async fixtures for Textual testing
- **Depends on**: Task 1.1
- **Commit**: `tests(dashboard): add conftest with async fixtures for textual testing`

---

### Phase 2: Token System (1.5 days)

#### Task 2.1: Create Shared Token Definitions
- **Files**: `bengal/themes/tokens.py`
- **Action**: Create Python module with `BENGAL_PALETTE`, `BENGAL_MASCOT`, `MOUSE_MASCOT` as single source of truth
- **Commit**: `themes: add tokens.py with shared design tokens for web and terminal`

#### Task 2.2: Create Token Generator Script
- **Files**: `bengal/themes/generate.py`
- **Action**: Create generator that outputs both CSS custom properties and Textual `.tcss` variables
- **Depends on**: Task 2.1
- **Commit**: `themes: add generate.py for web CSS and terminal TCSS generation`

#### Task 2.3: Create Textual CSS Stylesheet
- **Files**: `bengal/cli/dashboard/bengal.tcss`
- **Action**: Create complete Textual CSS with all widget styles from RFC Appendix B
- **Depends on**: Task 2.1
- **Commit**: `cli(dashboard): add bengal.tcss with complete widget styling`

#### Task 2.4: Integrate Token System with Web Theme
- **Files**: `bengal/themes/default/assets/css/tokens/generated.css`
- **Action**: Generate CSS from tokens.py, verify integration with existing foundation.css
- **Depends on**: Task 2.2
- **Commit**: `themes: integrate generated tokens with web theme CSS`

---

### Phase 3: Dashboard Infrastructure (1.5 days)

#### Task 3.1: Create Dashboard Package Structure
- **Files**:
  - `bengal/cli/dashboard/__init__.py`
  - `bengal/cli/dashboard/widgets.py`
  - `bengal/cli/dashboard/messages.py`
- **Action**: Create package with widget imports and custom message types (BuildEvent, PhaseStarted, PhaseComplete, BuildComplete)
- **Commit**: `cli(dashboard): create dashboard package with widgets and messages`

#### Task 3.2: Implement Base Dashboard Class
- **Files**: `bengal/cli/dashboard/base.py`
- **Action**: Create `BengalDashboard(App)` base class with common bindings (q, r, c, ?) and reactive state
- **Depends on**: Task 3.1, Task 2.3
- **Commit**: `cli(dashboard): add BengalDashboard base class with common bindings`

#### Task 3.3: Create Notification Helpers
- **Files**: `bengal/cli/dashboard/notifications.py`
- **Action**: Add toast notification helpers for build complete, errors, file changes
- **Depends on**: Task 3.2
- **Commit**: `cli(dashboard): add notification helpers for toast messages`

---

### Phase 4: Build Dashboard (2.5-3 days)

#### Task 4.1: Implement Build Dashboard Core
- **Files**: `bengal/cli/dashboard/build.py`
- **Action**: Create `BengalBuildDashboard` with Header, Footer, ProgressBar, DataTable for phases, Log for output
- **Depends on**: Task 3.2
- **Commit**: `cli(dashboard): implement BengalBuildDashboard with phase table and progress`

#### Task 4.2: Add Build Event Handlers
- **Files**: `bengal/cli/dashboard/build.py`
- **Action**: Implement `on_phase_started`, `on_phase_progress`, `on_phase_complete`, `on_build_complete` handlers
- **Depends on**: Task 4.1
- **Commit**: `cli(dashboard): add build event handlers for phase tracking`

#### Task 4.3: Implement Background Build Worker
- **Files**: `bengal/cli/dashboard/build.py`
- **Action**: Add `@work(exclusive=True, thread=True)` decorator for `run_build()` method with thread-safe callbacks
- **Depends on**: Task 4.2
- **Commit**: `cli(dashboard): add background build worker with thread-safe UI updates`

#### Task 4.4: Add Build Orchestrator Event Emission
- **Files**: `bengal/orchestration/build_orchestrator.py`
- **Action**: Add optional callback parameter to `build()` for emitting PhaseStarted/PhaseComplete events
- **Depends on**: Task 4.3
- **Commit**: `orchestration: add optional event callback to build orchestrator for dashboard`

#### Task 4.5: Wire --dashboard Flag to Build Command
- **Files**: `bengal/cli/commands/build.py`
- **Action**: Add `--dashboard` flag that launches `BengalBuildDashboard` instead of standard output
- **Depends on**: Task 4.4
- **Commit**: `cli(build): add --dashboard flag to launch interactive build dashboard`

#### Task 4.6: Add Build Dashboard Tests
- **Files**: `tests/dashboard/test_build_dashboard.py`
- **Action**: Add headless tests for dashboard rendering, keyboard shortcuts, phase table updates
- **Depends on**: Task 4.5
- **Commit**: `tests(dashboard): add build dashboard rendering and interaction tests`

---

### Phase 5: Serve Dashboard (2-2.5 days)

#### Task 5.1: Implement Serve Dashboard Core
- **Files**: `bengal/cli/dashboard/serve.py`
- **Action**: Create `BengalServeDashboard` with TabbedContent (Changes/Stats/Errors), Sparkline for build history
- **Depends on**: Task 3.2
- **Commit**: `cli(dashboard): implement BengalServeDashboard with tabs and sparkline`

#### Task 5.2: Integrate File Watcher Events
- **Files**: `bengal/cli/dashboard/serve.py`, `bengal/server/watcher.py`
- **Action**: Connect file watcher events to dashboard Log, update sparkline on rebuilds
- **Depends on**: Task 5.1
- **Commit**: `cli(dashboard): integrate file watcher events with serve dashboard`

#### Task 5.3: Add Timer-Based Updates
- **Files**: `bengal/cli/dashboard/serve.py`
- **Action**: Implement `set_interval` for watcher status refresh and sparkline updates
- **Depends on**: Task 5.2
- **Commit**: `cli(dashboard): add periodic status updates for file watcher`

#### Task 5.4: Wire --dashboard Flag to Serve Command
- **Files**: `bengal/cli/commands/serve.py`
- **Action**: Add `--dashboard` flag that launches `BengalServeDashboard`
- **Depends on**: Task 5.3
- **Commit**: `cli(serve): add --dashboard flag to launch interactive serve dashboard`

#### Task 5.5: Add Serve Dashboard Tests
- **Files**: `tests/dashboard/test_serve_dashboard.py`
- **Action**: Add headless tests for tab switching, sparkline updates, watcher status
- **Depends on**: Task 5.4
- **Commit**: `tests(dashboard): add serve dashboard rendering and interaction tests`

---

### Phase 6: Health Dashboard (1.5-2 days)

#### Task 6.1: Implement Health Dashboard Core
- **Files**: `bengal/cli/dashboard/health.py`
- **Action**: Create `BengalHealthDashboard` with Tree widget for issue navigation, Static for details panel
- **Depends on**: Task 3.2
- **Commit**: `cli(dashboard): implement BengalHealthDashboard with tree explorer`

#### Task 6.2: Populate Tree from Health Report
- **Files**: `bengal/cli/dashboard/health.py`
- **Action**: Build tree hierarchy from health report (Links, Images, Frontmatter, Performance)
- **Depends on**: Task 6.1
- **Commit**: `cli(dashboard): populate health tree from report with issue counts`

#### Task 6.3: Add Tree Node Selection Handler
- **Files**: `bengal/cli/dashboard/health.py`
- **Action**: Implement `on_tree_node_selected` to show issue details in side panel
- **Depends on**: Task 6.2
- **Commit**: `cli(dashboard): add tree selection handler for issue details`

#### Task 6.4: Wire --dashboard Flag to Health Command
- **Files**: `bengal/cli/commands/health.py`
- **Action**: Add `--dashboard` flag that launches `BengalHealthDashboard`
- **Depends on**: Task 6.3
- **Commit**: `cli(health): add --dashboard flag to launch interactive health explorer`

#### Task 6.5: Add Health Dashboard Tests
- **Files**: `tests/dashboard/test_health_dashboard.py`
- **Action**: Add headless tests for tree navigation, details panel updates
- **Depends on**: Task 6.4
- **Commit**: `tests(dashboard): add health dashboard tree navigation tests`

---

### Phase 7: Advanced Features (2-3 days)

#### Task 7.1: Create Command Provider
- **Files**: `bengal/cli/dashboard/commands.py`
- **Action**: Implement `BengalCommandProvider` for command palette with page/command search
- **Depends on**: Phase 6 complete
- **Commit**: `cli(dashboard): add BengalCommandProvider for command palette search`

#### Task 7.2: Create Screen Classes
- **Files**: `bengal/cli/dashboard/screens.py`
- **Action**: Create `BuildScreen`, `ServeScreen`, `HealthScreen` for multi-screen navigation
- **Depends on**: Task 7.1
- **Commit**: `cli(dashboard): add screen classes for multi-screen navigation`

#### Task 7.3: Implement Unified Dashboard App
- **Files**: `bengal/cli/dashboard/app.py`
- **Action**: Create `BengalApp` with `SCREENS` registry and screen navigation bindings (1, 2, 3)
- **Depends on**: Task 7.2
- **Commit**: `cli(dashboard): implement unified BengalApp with screen navigation`

#### Task 7.4: Add --dashboard Flag to Main CLI
- **Files**: `bengal/cli/main.py`
- **Action**: Add `bengal --dashboard` option to launch unified `BengalApp`
- **Depends on**: Task 7.3
- **Commit**: `cli: add top-level --dashboard flag for unified dashboard experience`

#### Task 7.5: Add Advanced Feature Tests
- **Files**: `tests/dashboard/test_interactions.py`
- **Action**: Add tests for command palette, screen navigation, keyboard shortcuts
- **Depends on**: Task 7.4
- **Commit**: `tests(dashboard): add command palette and screen navigation tests`

---

### Phase 8: Polish & Testing (2 days)

#### Task 8.1: Add CSS Animations
- **Files**: `bengal/cli/dashboard/bengal.tcss`
- **Action**: Add CSS transitions for progress bar, phase status, log entries, tab switching
- **Commit**: `cli(dashboard): add CSS animations for smooth transitions`

#### Task 8.2: Add Snapshot Tests
- **Files**: `tests/dashboard/test_snapshots.py`, `tests/dashboard/snapshots/`
- **Action**: Create visual regression tests for all three dashboards
- **Depends on**: Task 8.1
- **Commit**: `tests(dashboard): add snapshot tests for visual regression`

#### Task 8.3: Add Dashboard Development Mode
- **Files**: `bengal/cli/dashboard/__main__.py`
- **Action**: Create entry point for `python -m bengal.cli.dashboard` with devtools support
- **Commit**: `cli(dashboard): add __main__.py for devtools development mode`

#### Task 8.4: Terminal Compatibility Testing
- **Files**: `tests/dashboard/test_compatibility.py`
- **Action**: Test 256-color fallback, NO_COLOR detection, monochrome mode
- **Commit**: `tests(dashboard): add terminal compatibility tests`

#### Task 8.5: Update Documentation
- **Files**: `site/content/docs/reference/cli/build.md`, `site/content/docs/reference/cli/serve.md`, `site/content/docs/reference/cli/health.md`
- **Action**: Document `--dashboard` flag for all commands
- **Commit**: `docs(cli): document --dashboard flag for build, serve, health commands`

---

### Phase 9: Validation

- [ ] Unit tests pass: `pytest tests/dashboard/`
- [ ] Snapshot tests pass: `pytest tests/dashboard/test_snapshots.py`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Linter passes: `ruff check bengal/cli/dashboard/`
- [ ] Type checks pass: `mypy bengal/cli/dashboard/`
- [ ] Health validators pass: `bengal health`
- [ ] Terminal compatibility verified (iTerm, Terminal.app, VS Code, Kitty)
- [ ] 256-color fallback works
- [ ] NO_COLOR=1 gracefully degrades

---

## File Structure (Final)

```
bengal/
├── cli/
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── __main__.py          # Dev mode entry point
│   │   ├── app.py               # BengalApp (unified)
│   │   ├── base.py              # BengalDashboard base
│   │   ├── bengal.tcss          # Textual CSS
│   │   ├── build.py             # BengalBuildDashboard
│   │   ├── commands.py          # BengalCommandProvider
│   │   ├── health.py            # BengalHealthDashboard
│   │   ├── messages.py          # Custom messages
│   │   ├── notifications.py     # Toast helpers
│   │   ├── screens.py           # Screen classes
│   │   ├── serve.py             # BengalServeDashboard
│   │   └── widgets.py           # Widget imports
│   └── commands/
│       ├── build.py             # +--dashboard flag
│       ├── health.py            # +--dashboard flag
│       └── serve.py             # +--dashboard flag
├── themes/
│   ├── tokens.py                # Shared token definitions
│   └── generate.py              # Token generator
└── orchestration/
    └── build_orchestrator.py    # +event callbacks

tests/
└── dashboard/
    ├── __init__.py
    ├── conftest.py              # Async fixtures
    ├── test_build_dashboard.py
    ├── test_serve_dashboard.py
    ├── test_health_dashboard.py
    ├── test_interactions.py     # Command palette, navigation
    ├── test_snapshots.py        # Visual regression
    ├── test_compatibility.py    # Terminal compat
    └── snapshots/               # Snapshot data
```

---

## Changelog Entry

```markdown
### Added
- **Interactive Dashboards**: New `--dashboard` flag for `bengal build`, `bengal serve`, and `bengal health` commands
  - Build dashboard with live progress bar, phase timing table, and streaming output
  - Serve dashboard with tabbed changes/stats/errors and build history sparkline
  - Health dashboard with tree explorer for issue navigation
- **Unified Dashboard**: `bengal --dashboard` for integrated multi-screen experience
- **Command Palette**: `Ctrl+P` fuzzy search for pages and commands
- **Shared Design Tokens**: Single source of truth for web and terminal theming

### Changed
- **Dependencies**: Replaced `rich` with `textual` (includes Rich)
- **Token System**: Web CSS now generated from shared Python tokens

### Developer Experience
- Added snapshot testing for dashboard visual regression
- Added devtools mode: `python -m bengal.cli.dashboard --dev`
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Textual API changes | Pin to `textual>=0.89,<1.0` |
| Terminal compatibility | Test on iTerm, Terminal.app, VS Code, Kitty |
| Thread safety in parallel builds | Use `call_from_thread()` for all UI updates |
| Memory leaks in long-running serve | Bound build history to 20 entries |
| Snapshot test brittleness | Update snapshots only on intentional UI changes |

---

## Dependencies

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
                                 ↓          ↓          ↓
                              (MVP 🔴)  (Enhanced 🟡)  (Polish 🟢)
```

**MVP Checkpoint**: After Phase 5, `bengal build --dashboard` and `bengal serve --dashboard` are functional.

**Enhanced Checkpoint**: After Phase 6, all three dashboards are complete.

**Ship Ready**: After Phase 8, all tests pass and documentation is complete.
