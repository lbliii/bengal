# Plan: Dashboard Test Suite

**Status**: Draft  
**Created**: 2025-12-21  
**Estimated Effort**: 11-15 hours  
**Test Count**: ~30 tests across 4 phases

---

## Overview

Set up a comprehensive test suite for Bengal's Textual CLI dashboard using `pytest-textual-snapshot` for visual regression testing and Textual's pilot API for interaction testing.

**Reference**: [Textual Testing Guide](https://textual.textualize.io/guide/testing/)

---

## Current State

| Component | Location | Lines | Current Coverage |
|-----------|----------|-------|------------------|
| Main App | `bengal/cli/dashboard/app.py` | 267 | Import/instantiation only |
| Screens | `bengal/cli/dashboard/screens.py` | 521 | Import only |
| Build Dashboard | `bengal/cli/dashboard/build.py` | 546 | Instantiation only |
| Health Dashboard | `bengal/cli/dashboard/health.py` | 610 | Instantiation only |
| Serve Dashboard | `bengal/cli/dashboard/serve.py` | ~300 | Instantiation only |
| Custom Widgets | `bengal/cli/dashboard/widgets/` | 4 files | Basic init tests |
| CSS Styling | `bengal/cli/dashboard/bengal.tcss` | 707 | None |

**Existing Test Files**:
- `tests/dashboard/test_dashboards.py` (436 lines) — Import and instantiation tests
- `tests/dashboard/conftest.py` (149 lines) — Mock data fixtures

**Dependencies**: `pytest-textual-snapshot>=0.4.0` ✅ already installed

---

## Phase 1: Foundation

**Goal**: Set up test infrastructure and fixtures  
**Effort**: 2-3 hours

### Task 1.1: Create Snapshot Test Scaffold

**File**: `tests/dashboard/test_snapshots.py`

```python
"""
Snapshot tests for Bengal Textual dashboards.

Uses pytest-textual-snapshot for visual regression testing.
Run with: pytest tests/dashboard/test_snapshots.py
Update snapshots: pytest --snapshot-update
"""

from __future__ import annotations

from pathlib import Path


# Path to dashboard app module
APP_PATH = Path(__file__).parent.parent.parent / "bengal" / "cli" / "dashboard" / "app.py"


def test_landing_screen(snap_compare):
    """Snapshot of landing screen (default start)."""
    assert snap_compare(str(APP_PATH), press=["0"])


def test_build_screen(snap_compare):
    """Snapshot of build screen."""
    assert snap_compare(str(APP_PATH), press=["1"])


def test_serve_screen(snap_compare):
    """Snapshot of serve screen."""
    assert snap_compare(str(APP_PATH), press=["2"])


def test_health_screen(snap_compare):
    """Snapshot of health screen."""
    assert snap_compare(str(APP_PATH), press=["3"])
```

**Commit**: `tests(dashboard): add snapshot test scaffold with pytest-textual-snapshot`

---

### Task 1.2: Enhance conftest.py with Pilot Fixtures

**File**: `tests/dashboard/conftest.py` (additions)

```python
import pytest
from bengal.cli.dashboard.app import BengalApp


@pytest.fixture
def bengal_app(mock_site):
    """Create BengalApp instance for testing."""
    return BengalApp(site=mock_site, start_screen="landing")


@pytest.fixture
def mock_site():
    """Create a mock Site object for dashboard testing."""
    from unittest.mock import MagicMock

    site = MagicMock()
    site.title = "Test Site"
    site.pages = [MagicMock(title=f"Page {i}") for i in range(5)]
    site.assets = [MagicMock() for _ in range(10)]
    site.sections = [MagicMock(title="Docs")]
    return site


@pytest.fixture
async def pilot(bengal_app):
    """Async fixture for Textual pilot testing."""
    async with bengal_app.run_test() as pilot:
        yield pilot
```

**Commit**: `tests(dashboard): add pilot fixtures and mock site for interaction testing`

---

### Task 1.3: Verify Snapshot Plugin Works

**Action**: Run initial snapshot test to generate baseline

```bash
cd /Users/llane/Documents/github/python/bengal
pytest tests/dashboard/test_snapshots.py -v
# First run will fail (no baseline), then:
pytest tests/dashboard/test_snapshots.py --snapshot-update
```

**Commit**: `tests(dashboard): generate initial snapshot baselines for dashboard screens`

---

## Phase 2: Snapshot Tests

**Goal**: Visual regression tests for all screens and states  
**Effort**: 3-4 hours

### Task 2.1: Screen Default States

| Test | Description | Keys |
|------|-------------|------|
| `test_landing_screen` | Landing screen with branding | `["0"]` |
| `test_build_screen` | Build screen with phase table | `["1"]` |
| `test_serve_screen` | Serve screen with tabs | `["2"]` |
| `test_health_screen` | Health screen with tree | `["3"]` |
| `test_help_screen` | Help overlay | `["?"]` |

**Commit**: `tests(dashboard): add snapshot tests for all screen default states`

---

### Task 2.2: Navigation Sequence Snapshots

```python
def test_navigation_build_to_serve(snap_compare):
    """Navigate from build to serve screen."""
    assert snap_compare(str(APP_PATH), press=["1", "2"])


def test_navigation_cycle(snap_compare):
    """Cycle through all screens."""
    assert snap_compare(str(APP_PATH), press=["1", "2", "3", "0"])
```

**Commit**: `tests(dashboard): add navigation sequence snapshot tests`

---

### Task 2.3: Terminal Size Variants

```python
def test_small_terminal(snap_compare):
    """Dashboard in small terminal (40x20)."""
    assert snap_compare(str(APP_PATH), terminal_size=(40, 20))


def test_large_terminal(snap_compare):
    """Dashboard in large terminal (200x60)."""
    assert snap_compare(str(APP_PATH), terminal_size=(200, 60))


def test_wide_terminal(snap_compare):
    """Dashboard in wide terminal (160x24)."""
    assert snap_compare(str(APP_PATH), terminal_size=(160, 24))
```

**Commit**: `tests(dashboard): add terminal size variant snapshot tests`

---

### Task 2.4: Widget State Snapshots

```python
def test_throbber_active(snap_compare):
    """Throbber in active state."""
    async def run_before(pilot):
        throbber = pilot.app.query_one("#build-throbber")
        throbber.active = True
        await pilot.pause()

    assert snap_compare(str(APP_PATH), press=["1"], run_before=run_before)


def test_build_flash_success(snap_compare):
    """BuildFlash showing success message."""
    async def run_before(pilot):
        flash = pilot.app.query_one("#build-flash")
        flash.show_success("Build complete in 245ms")
        await pilot.pause()

    assert snap_compare(str(APP_PATH), press=["1"], run_before=run_before)


def test_build_flash_error(snap_compare):
    """BuildFlash showing error message."""
    async def run_before(pilot):
        flash = pilot.app.query_one("#build-flash")
        flash.show_error("Template not found: base.html")
        await pilot.pause()

    assert snap_compare(str(APP_PATH), press=["1"], run_before=run_before)
```

**Commit**: `tests(dashboard): add widget state snapshot tests for throbber and flash`

---

## Phase 3: Interaction Tests

**Goal**: Test keyboard navigation and user interactions  
**Effort**: 4-5 hours

### Task 3.1: Screen Navigation Tests

**File**: `tests/dashboard/test_navigation.py`

```python
"""
Navigation tests for Bengal dashboard.

Tests keyboard navigation between screens using Textual pilot.
"""

from __future__ import annotations

import pytest


class TestScreenNavigation:
    """Test screen navigation via keyboard."""

    @pytest.mark.asyncio
    async def test_press_1_goes_to_build(self, pilot):
        """Pressing '1' switches to build screen."""
        await pilot.press("1")
        assert pilot.app.screen.name == "build"

    @pytest.mark.asyncio
    async def test_press_2_goes_to_serve(self, pilot):
        """Pressing '2' switches to serve screen."""
        await pilot.press("2")
        assert pilot.app.screen.name == "serve"

    @pytest.mark.asyncio
    async def test_press_3_goes_to_health(self, pilot):
        """Pressing '3' switches to health screen."""
        await pilot.press("3")
        assert pilot.app.screen.name == "health"

    @pytest.mark.asyncio
    async def test_press_0_goes_to_landing(self, pilot):
        """Pressing '0' switches to landing screen."""
        await pilot.press("1")  # Go somewhere first
        await pilot.press("0")
        assert pilot.app.screen.name == "landing"

    @pytest.mark.asyncio
    async def test_help_toggle(self, pilot):
        """Pressing '?' opens help, 'escape' closes it."""
        await pilot.press("?")
        assert pilot.app.screen.name == "help"

        await pilot.press("escape")
        assert pilot.app.screen.name != "help"

    @pytest.mark.asyncio
    async def test_quit_action(self, pilot):
        """Pressing 'q' exits the app."""
        await pilot.press("q")
        assert pilot.app._exit
```

**Commit**: `tests(dashboard): add screen navigation interaction tests`

---

### Task 3.2: Build Screen Interaction Tests

```python
class TestBuildScreenInteractions:
    """Test build screen specific interactions."""

    @pytest.mark.asyncio
    async def test_clear_log(self, pilot):
        """Pressing 'c' clears the build log."""
        await pilot.press("1")  # Go to build screen

        log = pilot.app.query_one("#build-log")
        log.write_line("Test line")
        assert log.line_count > 0

        await pilot.press("c")
        assert log.line_count == 0

    @pytest.mark.asyncio
    async def test_rebuild_without_site_shows_notification(self, pilot_no_site):
        """Pressing 'r' without site shows error notification."""
        await pilot_no_site.press("1")
        await pilot_no_site.press("r")

        # Check notification was posted
        assert len(pilot_no_site.app._notifications) > 0
```

**Commit**: `tests(dashboard): add build screen interaction tests`

---

### Task 3.3: Quick Action Click Tests

```python
class TestQuickActionInteractions:
    """Test QuickAction widget interactions."""

    @pytest.mark.asyncio
    async def test_click_build_action_switches_screen(self, pilot):
        """Clicking Build quick action switches to build screen."""
        await pilot.press("0")  # Go to landing

        await pilot.click("#action-build")
        assert pilot.app.screen.name == "build"

    @pytest.mark.asyncio
    async def test_click_serve_action_switches_screen(self, pilot):
        """Clicking Serve quick action switches to serve screen."""
        await pilot.press("0")

        await pilot.click("#action-serve")
        assert pilot.app.screen.name == "serve"

    @pytest.mark.asyncio
    async def test_click_health_action_switches_screen(self, pilot):
        """Clicking Health quick action switches to health screen."""
        await pilot.press("0")

        await pilot.click("#action-health")
        assert pilot.app.screen.name == "health"
```

**Commit**: `tests(dashboard): add QuickAction click interaction tests`

---

### Task 3.4: Command Palette Tests

```python
class TestCommandPalette:
    """Test command palette functionality."""

    @pytest.mark.asyncio
    async def test_ctrl_p_opens_command_palette(self, pilot):
        """Ctrl+P opens the command palette."""
        await pilot.press("ctrl+p")

        # Command palette should be visible
        palette = pilot.app.query_one("CommandPalette")
        assert palette is not None

    @pytest.mark.asyncio
    async def test_command_palette_quit_command(self, pilot):
        """Selecting Quit from command palette exits app."""
        await pilot.press("ctrl+p")
        await pilot.press("q", "u", "i", "t")  # Type "quit"
        await pilot.press("enter")

        assert pilot.app._exit
```

**Commit**: `tests(dashboard): add command palette interaction tests`

---

## Phase 4: Widget Unit Tests

**Goal**: Isolated tests for custom widgets  
**Effort**: 2-3 hours

### Task 4.1: Throbber Widget Tests

**File**: `tests/dashboard/test_widgets.py`

```python
"""
Unit tests for Bengal dashboard custom widgets.
"""

from __future__ import annotations

import pytest

from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash, QuickAction
from bengal.cli.dashboard.widgets.phase_plan import BuildPhase, BuildPhasePlan


class TestBengalThrobber:
    """Tests for BengalThrobber widget."""

    def test_init_inactive(self):
        """Throbber starts inactive."""
        throbber = BengalThrobber()
        assert throbber.active is False

    def test_activate_throbber(self):
        """Setting active=True starts animation."""
        throbber = BengalThrobber()
        throbber.active = True
        assert throbber.active is True

    def test_deactivate_throbber(self):
        """Setting active=False stops animation."""
        throbber = BengalThrobber()
        throbber.active = True
        throbber.active = False
        assert throbber.active is False
```

**Commit**: `tests(dashboard): add BengalThrobber widget unit tests`

---

### Task 4.2: BuildFlash Widget Tests

```python
class TestBuildFlash:
    """Tests for BuildFlash widget."""

    def test_init_empty(self):
        """Flash starts with no message."""
        flash = BuildFlash()
        assert flash is not None

    @pytest.mark.asyncio
    async def test_show_success(self):
        """show_success displays green message."""
        async with BuildFlash().run_test() as pilot:
            flash = pilot.app.query_one(BuildFlash)
            flash.show_success("Build complete")

            assert "success" in flash.classes or flash.has_class("success")

    @pytest.mark.asyncio
    async def test_show_error(self):
        """show_error displays red message."""
        async with BuildFlash().run_test() as pilot:
            flash = pilot.app.query_one(BuildFlash)
            flash.show_error("Build failed")

            assert "error" in flash.classes or flash.has_class("error")

    @pytest.mark.asyncio
    async def test_show_building(self):
        """show_building displays building state."""
        async with BuildFlash().run_test() as pilot:
            flash = pilot.app.query_one(BuildFlash)
            flash.show_building("Rendering pages...")

            assert "building" in flash.classes or flash.has_class("building")
```

**Commit**: `tests(dashboard): add BuildFlash widget unit tests`

---

### Task 4.3: BuildPhasePlan Widget Tests

```python
class TestBuildPhasePlan:
    """Tests for BuildPhasePlan widget."""

    def test_status_icons_defined(self):
        """All status icons are defined."""
        icons = BuildPhasePlan.STATUS_ICONS
        assert icons["pending"] == "○"
        assert icons["running"] == "●"
        assert icons["complete"] == "✓"
        assert icons["error"] == "✗"

    def test_build_phase_dataclass(self):
        """BuildPhase dataclass works correctly."""
        phase = BuildPhase(
            name="discovery",
            status="running",
            duration_ms=150,
        )
        assert phase.name == "discovery"
        assert phase.status == "running"
        assert phase.duration_ms == 150
```

**Commit**: `tests(dashboard): add BuildPhasePlan widget unit tests`

---

### Task 4.4: QuickAction Widget Tests

```python
class TestQuickAction:
    """Tests for QuickAction widget."""

    def test_init_with_params(self):
        """QuickAction initializes with emoji, title, description."""
        action = QuickAction(
            "🚀",
            "Launch",
            "Launch the app",
            id="launch-action",
        )
        assert action.emoji == "🚀"
        assert action.action_title == "Launch"
        assert action.description == "Launch the app"

    def test_selected_message_class_exists(self):
        """QuickAction has Selected message class."""
        assert hasattr(QuickAction, "Selected")

    @pytest.mark.asyncio
    async def test_click_posts_selected_message(self):
        """Clicking QuickAction posts Selected message."""
        messages = []

        async with QuickAction("🔨", "Build", "Build site", id="build").run_test() as pilot:
            pilot.app.on(QuickAction.Selected, lambda m: messages.append(m))

            await pilot.click("#build")

            assert len(messages) == 1
```

**Commit**: `tests(dashboard): add QuickAction widget unit tests`

---

## Final File Structure

```
tests/dashboard/
├── __init__.py
├── conftest.py              # Enhanced with pilot fixtures
├── test_dashboards.py       # Existing import tests ✅
├── test_snapshots.py        # NEW: Visual regression (12 tests)
├── test_navigation.py       # NEW: Screen navigation (6 tests)
├── test_widgets.py          # NEW: Widget units (12 tests)
└── snapshots/               # Auto-generated
    ├── test_landing_screen.svg
    ├── test_build_screen.svg
    ├── test_serve_screen.svg
    ├── test_health_screen.svg
    ├── test_help_screen.svg
    └── ...
```

---

## Running Tests

```bash
# Run all dashboard tests
pytest tests/dashboard/ -v

# Run only snapshot tests
pytest tests/dashboard/test_snapshots.py -v

# Update snapshots after visual changes
pytest tests/dashboard/test_snapshots.py --snapshot-update

# Run with coverage
pytest tests/dashboard/ --cov=bengal.cli.dashboard --cov-report=html

# Skip slow tests (if marked)
pytest tests/dashboard/ -m "not slow"
```

---

## Success Criteria

- [ ] All 4 screens have snapshot baseline coverage
- [ ] Navigation keys (0, 1, 2, 3, ?) tested with pilot
- [ ] Quit action (q) tested
- [ ] Custom widgets have unit tests
- [ ] Terminal size variants captured
- [ ] Widget state variants (throbber, flash) captured
- [ ] CI can run `pytest tests/dashboard/` successfully

---

## Maintenance Notes

**When to update snapshots**:
- After intentional CSS/styling changes
- After layout modifications
- After adding new widgets/content

**Review process**:
1. Run `pytest tests/dashboard/test_snapshots.py`
2. Open snapshot report in browser
3. Visually verify changes are intentional
4. Run `pytest --snapshot-update` to accept

---

## Related Files

- `bengal/cli/dashboard/` — Source modules
- `tests/dashboard/conftest.py` — Test fixtures
- [Textual Testing Guide](https://textual.textualize.io/guide/testing/)
- [pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot)


