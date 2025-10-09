# Bengal CLI Excellence - Implementation Plan
## Transforming Bengal's CLI into a Competitive Differentiator

**Status:** Ready for Implementation  
**Timeline:** 6 weeks (3 phases)  
**Owner:** TBD  
**Started:** TBD  
**Target Completion:** TBD

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Animated Feedback](#phase-1-animated-feedback-week-1-2)
3. [Phase 2: Intelligence & Context](#phase-2-intelligence--context-week-3-4)
4. [Phase 3: Interactivity](#phase-3-interactivity-week-5-6)
5. [Testing Strategy](#testing-strategy)
6. [Rollout Plan](#rollout-plan)
7. [Success Metrics](#success-metrics)
8. [Risk Mitigation](#risk-mitigation)

---

## Overview

### Goals

Transform Bengal's CLI from "good" to "exceptional" through:
1. **Animated feedback** - Visual progress indicators and live updates
2. **Intelligent behavior** - Context-aware defaults and smart suggestions
3. **Interactive features** - Conversational prompts and guided workflows

### Principles

- **Persona-aware:** Respect Writer/Theme-Dev/Developer profiles
- **Non-invasive:** Enhance existing code, don't rewrite
- **Graceful degradation:** Work in all terminal environments
- **Performance:** CLI enhancements add <1% overhead

### Dependencies

```toml
# Add to requirements.txt
rich>=13.7.0                # Terminal formatting and animation
questionary>=2.0.0          # Interactive prompts
click-completion>=0.5.2     # Shell completions
```

### Success Criteria

- [ ] Build feedback appears within 200ms
- [ ] Progress visible during long operations (>1s)
- [ ] Error messages include actionable suggestions
- [ ] Zero performance regression in --quiet mode
- [ ] Works on Windows, macOS, Linux
- [ ] Graceful fallback for dumb terminals

---

## Phase 1: Animated Feedback (Week 1-2)

**Goal:** Add visual progress indicators and live updates to make builds feel responsive

**Effort:** 8-12 days  
**Impact:** High - Immediate visual improvement

### 1.1 Add Rich Library Integration

**Files to modify:**
- `requirements.txt`
- `bengal/utils/rich_console.py` (NEW)

**Tasks:**

#### Task 1.1.1: Add Dependencies
```bash
# Add to requirements.txt
rich>=13.7.0
```

**Acceptance Criteria:**
- [ ] Rich installs without conflicts
- [ ] Import `from rich.console import Console` works

**Estimated Time:** 30 minutes

---

#### Task 1.1.2: Create Rich Console Wrapper
Create `bengal/utils/rich_console.py`:

```python
"""
Rich console wrapper with profile-aware output.

Provides a singleton console instance that respects:
- Build profiles (Writer/Theme-Dev/Developer)
- Terminal capabilities
- CI/CD environments
"""

from rich.console import Console
from rich.theme import Theme
from typing import Optional
import os
import sys

# Bengal theme
bengal_theme = Theme({
    'info': 'cyan',
    'success': 'green',
    'warning': 'yellow',
    'error': 'red bold',
    'highlight': 'magenta bold',
    'dim': 'dim',
    'bengal': 'yellow bold',  # For the cat mascot
})

_console: Optional[Console] = None

def get_console() -> Console:
    """
    Get singleton rich console instance.
    
    Returns:
        Configured Console instance
    """
    global _console
    
    if _console is None:
        # Detect environment
        force_terminal = None
        no_color = os.getenv('NO_COLOR') is not None
        ci_mode = os.getenv('CI') is not None
        
        if ci_mode:
            # In CI, force simple output
            force_terminal = False
        
        _console = Console(
            theme=bengal_theme,
            force_terminal=force_terminal,
            no_color=no_color,
            highlight=True,
            emoji=True,  # Support emoji on all platforms
        )
    
    return _console

def should_use_rich() -> bool:
    """
    Determine if we should use rich features.
    
    Returns:
        True if rich features should be enabled
    """
    console = get_console()
    
    # Disable in CI or dumb terminals
    if os.getenv('CI') or os.getenv('TERM') == 'dumb':
        return False
    
    # Disable if no terminal
    if not console.is_terminal:
        return False
    
    return True
```

**Acceptance Criteria:**
- [ ] Console singleton created
- [ ] Environment detection works (CI, NO_COLOR, etc.)
- [ ] Unit tests pass
- [ ] Works on Windows/macOS/Linux

**Estimated Time:** 2 hours

---

### 1.2 Replace Static Build Indicators

**Files to modify:**
- `bengal/utils/build_stats.py`
- `bengal/cli.py`
- `bengal/orchestration/build.py`

#### Task 1.2.1: Update `show_building_indicator()`

**Location:** `bengal/utils/build_stats.py` lines 365-368

**Current code:**
```python
def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator."""
    click.echo(click.style(BENGAL_BUILDING, fg='yellow'))
    click.echo(click.style(f"🔨 {text}...\n", fg='cyan', bold=True))
```

**New code:**
```python
from rich.spinner import Spinner
from bengal.utils.rich_console import get_console, should_use_rich

def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator (static or animated based on terminal)."""
    console = get_console()
    
    if should_use_rich():
        # Rich output with cat mascot
        console.print()
        console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold cyan]Building your site...[/bold cyan]")
        console.print()
    else:
        # Fallback to click (for CI, dumb terminals)
        click.echo(click.style(BENGAL_BUILDING, fg='yellow'))
        click.echo(click.style(f"🔨 {text}...\n", fg='cyan', bold=True))
```

**Acceptance Criteria:**
- [ ] Rich output in normal terminals
- [ ] Fallback works in CI/dumb terminals
- [ ] No visual regression

**Estimated Time:** 1 hour

---

#### Task 1.2.2: Add Spinner to Build Command

**Location:** `bengal/cli.py` lines 105-183 (build command)

**Current code:**
```python
try:
    show_building_indicator("Building site")
    
    root_path = Path(source).resolve()
    config_path = Path(config).resolve() if config else None
    
    # Create and build site
    site = Site.from_config(root_path, config_path)
    # ... build logic ...
```

**New code:**
```python
from bengal.utils.rich_console import get_console, should_use_rich
from rich.status import Status

try:
    console = get_console()
    
    root_path = Path(source).resolve()
    config_path = Path(config).resolve() if config else None
    
    # Create site
    site = Site.from_config(root_path, config_path)
    
    # Override config with CLI flags
    if strict:
        site.config["strict_mode"] = True
    if debug:
        site.config["debug"] = True
    
    # Validate templates if requested
    if validate:
        # ... existing validation code ...
        pass
    
    # Build with status indicator
    if should_use_rich() and not quiet:
        console.print()
        console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold]Building your site...[/bold]")
        console.print()
        
        with console.status("[bold cyan]Working...", spinner="dots") as status:
            stats = site.build(
                parallel=parallel,
                incremental=incremental,
                verbose=profile_config['verbose_build_stats'],
                profile=build_profile,
                memory_optimized=memory_optimized
            )
    else:
        # Fallback for quiet/CI mode
        show_building_indicator("Building site")
        stats = site.build(
            parallel=parallel,
            incremental=incremental,
            verbose=profile_config['verbose_build_stats'],
            profile=build_profile,
            memory_optimized=memory_optimized
        )
```

**Acceptance Criteria:**
- [ ] Spinner shows during build in interactive terminals
- [ ] No spinner in --quiet mode
- [ ] No spinner in CI environments
- [ ] Build still completes successfully

**Estimated Time:** 2 hours

---

### 1.3 Add Progress Bars to Page Rendering

**Files to modify:**
- `bengal/orchestration/render.py`

#### Task 1.3.1: Create Progress-Aware Render Function

**Location:** `bengal/orchestration/render.py` (entire file refactor)

**New code:**
```python
"""
Page rendering orchestration with progress tracking.
"""

from bengal.utils.rich_console import get_console, should_use_rich
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

class RenderOrchestrator:
    def __init__(self, site):
        self.site = site
        self.console = get_console()
    
    def process(self, pages: List, parallel: bool = True, tracker=None, stats=None):
        """
        Process pages with visual progress feedback.
        
        Args:
            pages: List of pages to render
            parallel: Whether to use parallel processing
            tracker: Dependency tracker for incremental builds
            stats: BuildStats object to update
        """
        if not pages:
            return
        
        # Use rich progress if available
        if should_use_rich():
            self._process_with_progress(pages, parallel, tracker, stats)
        else:
            self._process_simple(pages, parallel, tracker, stats)
    
    def _process_with_progress(self, pages, parallel, tracker, stats):
        """Process pages with rich progress bar."""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total} pages"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False  # Keep visible after completion
        ) as progress:
            
            render_task = progress.add_task(
                "[cyan]Rendering pages...",
                total=len(pages)
            )
            
            if parallel:
                self._render_parallel(pages, progress, render_task, tracker, stats)
            else:
                self._render_sequential(pages, progress, render_task, tracker, stats)
    
    def _render_parallel(self, pages, progress, task_id, tracker, stats):
        """Render pages in parallel with progress updates."""
        from bengal.rendering.renderer import render_page
        
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(render_page, page, self.site): page
                for page in pages
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    page = futures[future]
                    
                    # Update tracker
                    if tracker:
                        tracker.mark_rendered(page.output_path)
                    
                    # Update progress
                    progress.update(task_id, advance=1)
                    
                except Exception as e:
                    # Collect error
                    if stats:
                        from bengal.rendering.errors import TemplateRenderError
                        if isinstance(e, TemplateRenderError):
                            stats.add_template_error(e)
                    
                    # Continue rendering other pages
                    progress.update(task_id, advance=1)
    
    def _render_sequential(self, pages, progress, task_id, tracker, stats):
        """Render pages sequentially with progress updates."""
        from bengal.rendering.renderer import render_page
        
        for page in pages:
            try:
                render_page(page, self.site)
                
                if tracker:
                    tracker.mark_rendered(page.output_path)
                
            except Exception as e:
                if stats:
                    from bengal.rendering.errors import TemplateRenderError
                    if isinstance(e, TemplateRenderError):
                        stats.add_template_error(e)
            
            # Update progress
            progress.update(task_id, advance=1)
    
    def _process_simple(self, pages, parallel, tracker, stats):
        """Fallback processing without rich progress."""
        # Existing implementation (current code)
        print(f"\n📄 Rendering {len(pages)} pages...")
        
        if parallel:
            # ... existing parallel code ...
            pass
        else:
            # ... existing sequential code ...
            pass
```

**Acceptance Criteria:**
- [ ] Progress bar shows during rendering
- [ ] Updates in real-time (every page)
- [ ] Works in both parallel and sequential modes
- [ ] Graceful fallback without rich
- [ ] No performance regression (measure with `bengal perf`)

**Estimated Time:** 4-6 hours

---

### 1.4 Enhance Error Display

**Files to modify:**
- `bengal/rendering/errors.py`

#### Task 1.4.1: Add Rich Error Formatting

**Location:** `bengal/rendering/errors.py` line 246 (display_template_error function)

**Current code:**
```python
def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """
    Display a template rendering error with context.
    
    Args:
        error: The template error to display
        use_color: Whether to use colored output
    """
    # ... existing implementation ...
```

**New code:**
```python
from bengal.utils.rich_console import get_console, should_use_rich
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from difflib import get_close_matches

def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """
    Display a template rendering error with context and suggestions.
    
    Args:
        error: The template error to display
        use_color: Whether to use colored output
    """
    console = get_console()
    
    if should_use_rich():
        _display_error_rich(error, console)
    else:
        _display_error_simple(error, use_color)

def _display_error_rich(error: TemplateRenderError, console):
    """Display error with rich formatting."""
    from pathlib import Path
    
    # Get code context
    if error.source_context:
        # Syntax highlight the error context
        syntax = Syntax(
            error.source_context,
            "jinja2",
            line_numbers=True,
            line_range=(error.lineno - 3, error.lineno + 3),
            highlight_lines=[error.lineno],
            theme="monokai",
            word_wrap=False,
        )
        
        # Display in panel
        console.print()
        console.print(Panel(
            syntax,
            title=f"[red bold]Template Error in {Path(error.filename).name}[/red bold]",
            subtitle=f"[dim]Line {error.lineno}[/dim]",
            border_style="red",
            padding=(1, 2),
        ))
    
    # Error message
    console.print()
    console.print(f"[red bold]Error:[/red bold] {error.message}")
    console.print()
    
    # Generate suggestions
    suggestions = _generate_suggestions(error)
    
    if suggestions:
        console.print("[yellow bold]💡 Suggestions:[/yellow bold]")
        console.print()
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"   [yellow]{i}.[/yellow] {suggestion}")
        console.print()
    
    # Documentation link
    if error.error_type in ERROR_DOCS:
        doc_url = ERROR_DOCS[error.error_type]
        console.print(f"[dim]📚 Learn more: {doc_url}[/dim]")
        console.print()

def _generate_suggestions(error: TemplateRenderError) -> List[str]:
    """Generate smart suggestions based on error type."""
    suggestions = []
    
    if error.error_type == 'undefined_variable':
        var_name = error.var_name
        available_vars = error.context.get('available_vars', [])
        
        # Check for similar variable names
        similar = get_close_matches(var_name, available_vars, n=3, cutoff=0.6)
        if similar:
            suggestions.append(f"Did you mean: [cyan]{', '.join(similar)}[/cyan]?")
        
        # Common typos
        typos = {
            'titel': 'title', 'dat': 'date', 'autor': 'author',
            'sumary': 'summary', 'desciption': 'description'
        }
        if var_name.lower() in typos:
            suggestions.append(f"Common typo: try [cyan]'{typos[var_name.lower()]}'[/cyan]")
        
        # Suggest default filter
        suggestions.append(
            f"Use a default: [cyan]{{{{ {var_name} | default('value') }}}}[/cyan]"
        )
        
        # Suggest adding to frontmatter
        if error.context.get('is_page_template'):
            suggestions.append(f"Add [cyan]'{var_name}'[/cyan] to page frontmatter")
    
    elif error.error_type == 'template_not_found':
        template_name = error.template_name
        available = error.context.get('available_templates', [])
        
        similar = get_close_matches(template_name, available, n=3, cutoff=0.6)
        if similar:
            suggestions.append(f"Did you mean: [cyan]{', '.join(similar)}[/cyan]?")
        
        suggestions.append(
            f"Create template: [cyan]templates/{template_name}[/cyan]"
        )
    
    elif error.error_type == 'filter_not_found':
        filter_name = error.filter_name
        available = error.context.get('available_filters', [])
        
        similar = get_close_matches(filter_name, available, n=3, cutoff=0.6)
        if similar:
            suggestions.append(f"Did you mean: [cyan]{', '.join(similar)}[/cyan]?")
    
    return suggestions

def _display_error_simple(error: TemplateRenderError, use_color: bool):
    """Fallback error display (existing implementation)."""
    # Keep existing implementation for compatibility
    pass

# Error documentation URLs
ERROR_DOCS = {
    'undefined_variable': 'https://bengal.dev/docs/templates/variables',
    'template_not_found': 'https://bengal.dev/docs/templates/structure',
    'filter_not_found': 'https://bengal.dev/docs/templates/filters',
    'syntax_error': 'https://bengal.dev/docs/templates/syntax',
}
```

**Acceptance Criteria:**
- [ ] Error messages show syntax-highlighted code context
- [ ] Smart suggestions based on error type
- [ ] Similar variable names suggested (fuzzy matching)
- [ ] Documentation links provided
- [ ] Fallback works without rich

**Estimated Time:** 4-5 hours

---

### 1.5 Add Live Build Phase Table

**Files to modify:**
- `bengal/orchestration/build.py`

#### Task 1.5.1: Create Live Build Dashboard

**Location:** `bengal/orchestration/build.py` (BuildOrchestrator.build method)

**Strategy:** Use Rich's `Live` display to show build phases updating in real-time.

**New code to add:**
```python
from bengal.utils.rich_console import get_console, should_use_rich
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import time

class BuildOrchestrator:
    # ... existing __init__ ...
    
    def build(self, parallel: bool = True, incremental: bool = False, 
              verbose: bool = False, profile: 'BuildProfile' = None,
              memory_optimized: bool = False) -> BuildStats:
        """Execute build with live phase tracking."""
        
        # ... existing setup code ...
        
        # Determine if we should use live dashboard
        use_dashboard = (
            should_use_rich() and
            profile != BuildProfile.WRITER and
            not verbose  # verbose mode uses different output
        )
        
        if use_dashboard:
            return self._build_with_dashboard(
                parallel, incremental, verbose, profile, memory_optimized
            )
        else:
            return self._build_traditional(
                parallel, incremental, verbose, profile, memory_optimized
            )
    
    def _build_with_dashboard(self, parallel, incremental, verbose, profile, memory_optimized):
        """Execute build with live updating dashboard."""
        from rich.live import Live
        
        console = get_console()
        
        # Phase tracking
        phases = {
            'Discovery': {'status': 'pending', 'time': '', 'detail': ''},
            'Sections': {'status': 'pending', 'time': '', 'detail': ''},
            'Taxonomies': {'status': 'pending', 'time': '', 'detail': ''},
            'Menus': {'status': 'pending', 'time': '', 'detail': ''},
            'Related Posts': {'status': 'pending', 'time': '', 'detail': ''},
            'Rendering': {'status': 'pending', 'time': '', 'detail': ''},
            'Assets': {'status': 'pending', 'time': '', 'detail': ''},
            'Postprocess': {'status': 'pending', 'time': '', 'detail': ''},
        }
        
        def make_phase_table():
            """Generate phase status table."""
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Status", width=3)
            table.add_column("Phase", width=18)
            table.add_column("Detail", width=30)
            table.add_column("Time", width=10, justify="right")
            
            for phase_name, phase_data in phases.items():
                status = phase_data['status']
                
                if status == 'complete':
                    icon = "[green]✓[/green]"
                elif status == 'running':
                    icon = "[yellow]⠋[/yellow]"
                elif status == 'error':
                    icon = "[red]✗[/red]"
                else:
                    icon = "[dim]⋯[/dim]"
                
                detail = phase_data['detail']
                time_str = phase_data['time']
                
                # Dim pending phases
                if status == 'pending':
                    phase_style = "dim"
                else:
                    phase_style = ""
                
                table.add_row(
                    icon,
                    f"[{phase_style}]{phase_name}[/{phase_style}]" if phase_style else phase_name,
                    detail,
                    time_str
                )
            
            return Panel(
                table,
                title="[bold cyan]Build Progress[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
        
        # Show initial state
        console.print()
        console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold]Building your site...[/bold]")
        console.print()
        
        # Use Live display
        with Live(make_phase_table(), console=console, refresh_per_second=4) as live:
            
            # Helper to update phase
            def update_phase(name, status, detail='', time_val=''):
                phases[name]['status'] = status
                phases[name]['detail'] = detail
                phases[name]['time'] = time_val
                live.update(make_phase_table())
            
            build_start = time.time()
            
            # Phase 1: Discovery
            update_phase('Discovery', 'running')
            phase_start = time.time()
            
            content_dir = self.site.root_path / "content"
            with self.logger.phase("discovery", content_dir=str(content_dir)):
                discovery_start = time.time()
                self.content.discover()
                self.stats.discovery_time_ms = (time.time() - discovery_start) * 1000
            
            update_phase(
                'Discovery', 
                'complete',
                detail=f"{len(self.site.pages)} pages found",
                time_val=f"{(time.time() - phase_start):.1f}s"
            )
            
            # Phase 2: Sections
            update_phase('Sections', 'running')
            phase_start = time.time()
            
            with self.logger.phase("section_finalization"):
                self.sections.finalize_sections()
                self.site.invalidate_regular_pages_cache()
            
            update_phase(
                'Sections',
                'complete',
                detail=f"{len(self.site.sections)} sections",
                time_val=f"{(time.time() - phase_start):.1f}s"
            )
            
            # Phase 3: Taxonomies
            update_phase('Taxonomies', 'running')
            phase_start = time.time()
            
            with self.logger.phase("taxonomies"):
                taxonomy_start = time.time()
                self.taxonomy.collect_and_generate()
                self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
            
            tax_count = sum(len(terms) for terms in self.site.taxonomies.values())
            update_phase(
                'Taxonomies',
                'complete',
                detail=f"{tax_count} terms",
                time_val=f"{(time.time() - phase_start):.1f}s"
            )
            
            # Continue for all phases...
            # (Similar pattern for Menus, Related Posts, Rendering, Assets, Postprocess)
            
            # Phase 6: Rendering (with sub-progress)
            update_phase('Rendering', 'running')
            phase_start = time.time()
            
            with self.logger.phase("rendering", page_count=len(self.site.pages)):
                rendering_start = time.time()
                self.render.process(self.site.pages, parallel=parallel, tracker=None, stats=self.stats)
                self.stats.rendering_time_ms = (time.time() - rendering_start) * 1000
            
            update_phase(
                'Rendering',
                'complete',
                detail=f"{len(self.site.pages)} pages",
                time_val=f"{(time.time() - phase_start):.1f}s"
            )
            
            # ... continue for remaining phases ...
            
            # Final update
            self.stats.build_time_ms = (time.time() - build_start) * 1000
        
        # Dashboard is now complete, return stats
        return self.stats
    
    def _build_traditional(self, parallel, incremental, verbose, profile, memory_optimized):
        """Traditional build without dashboard (existing implementation)."""
        # This is the EXISTING build() method logic
        # Just refactor current code into this method
        pass
```

**Acceptance Criteria:**
- [ ] Live table shows during build
- [ ] Phases update in real-time
- [ ] Completed phases show checkmark and time
- [ ] Running phase shows spinner
- [ ] Falls back to traditional output in writer mode
- [ ] No dashboard in --quiet mode

**Estimated Time:** 6-8 hours

---

### 1.6 Testing & Validation

#### Task 1.6.1: Unit Tests

**Files to create:**
- `tests/unit/utils/test_rich_console.py`
- `tests/unit/rendering/test_error_display.py`

```python
# tests/unit/utils/test_rich_console.py
"""Tests for rich console utilities."""

import os
import pytest
from bengal.utils.rich_console import get_console, should_use_rich

def test_console_singleton():
    """Test that console is a singleton."""
    console1 = get_console()
    console2 = get_console()
    assert console1 is console2

def test_should_use_rich_in_ci(monkeypatch):
    """Test that rich is disabled in CI."""
    monkeypatch.setenv('CI', 'true')
    # Reset singleton
    import bengal.utils.rich_console
    bengal.utils.rich_console._console = None
    
    assert should_use_rich() is False

def test_should_use_rich_with_no_color(monkeypatch):
    """Test that rich respects NO_COLOR."""
    monkeypatch.setenv('NO_COLOR', '1')
    import bengal.utils.rich_console
    bengal.utils.rich_console._console = None
    
    console = get_console()
    assert console.no_color is True
```

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] Coverage >80% for new code
- [ ] Tests run in CI

**Estimated Time:** 3-4 hours

---

#### Task 1.6.2: Integration Tests

**Files to create:**
- `tests/integration/test_cli_progress.py`

```python
# tests/integration/test_cli_progress.py
"""Integration tests for CLI progress indicators."""

import pytest
from click.testing import CliRunner
from bengal.cli import main
from pathlib import Path

def test_build_with_progress(tmp_path):
    """Test that build shows progress in interactive mode."""
    # Create minimal site
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "content").mkdir()
    (site_dir / "bengal.toml").write_text("[site]\ntitle='Test'")
    (site_dir / "content" / "index.md").write_text("---\ntitle: Home\n---\n\nContent")
    
    runner = CliRunner()
    result = runner.invoke(main, ['build', str(site_dir)])
    
    assert result.exit_code == 0
    # Should complete successfully (progress may not show in test runner)

def test_build_quiet_mode(tmp_path):
    """Test that --quiet mode has minimal output."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "content").mkdir()
    (site_dir / "bengal.toml").write_text("[site]\ntitle='Test'")
    (site_dir / "content" / "index.md").write_text("---\ntitle: Home\n---\n\nContent")
    
    runner = CliRunner()
    result = runner.invoke(main, ['build', '--quiet', str(site_dir)])
    
    assert result.exit_code == 0
    assert "✅ Build complete!" in result.output
    # Should not have progress bars or detailed output
```

**Acceptance Criteria:**
- [ ] Integration tests pass
- [ ] Build still works end-to-end
- [ ] Quiet mode respected

**Estimated Time:** 2-3 hours

---

#### Task 1.6.3: Manual Testing Checklist

Create `tests/manual/phase1_testing.md`:

```markdown
# Phase 1 Manual Testing Checklist

## Test on Multiple Platforms

### macOS
- [ ] Build shows animated spinner
- [ ] Progress bar appears during rendering
- [ ] Error messages are syntax-highlighted
- [ ] Colors display correctly in Terminal.app
- [ ] Colors display correctly in iTerm2

### Linux
- [ ] Test in GNOME Terminal
- [ ] Test in Konsole
- [ ] Test in xterm
- [ ] Test with TERM=dumb (should fallback)

### Windows
- [ ] Test in PowerShell
- [ ] Test in Windows Terminal
- [ ] Test in cmd.exe
- [ ] Test in Git Bash

## Test Build Sizes

- [ ] Small site (10 pages) - progress shows briefly
- [ ] Medium site (100 pages) - progress updates smoothly
- [ ] Large site (1000 pages) - progress doesn't slow build

## Test Profiles

- [ ] Writer mode: simple output, no dashboard
- [ ] Theme-dev mode: dashboard shows
- [ ] Developer mode: full dashboard with details

## Test Error Scenarios

- [ ] Undefined variable error shows suggestions
- [ ] Template not found shows similar templates
- [ ] Syntax error shows highlighted code

## CI/CD Testing

- [ ] GitHub Actions: no ANSI codes, simple output
- [ ] GitLab CI: same
- [ ] --quiet mode: minimal output only
```

**Acceptance Criteria:**
- [ ] All manual tests pass
- [ ] No regressions found
- [ ] Visual quality confirmed

**Estimated Time:** 3-4 hours

---

### Phase 1 Summary

**Total Estimated Time:** 8-12 days

**Deliverables:**
- [ ] Rich library integrated
- [ ] Animated spinners during builds
- [ ] Progress bars for page rendering
- [ ] Enhanced error messages with suggestions
- [ ] Live build phase dashboard
- [ ] All tests passing
- [ ] Works on Windows/macOS/Linux

**Success Metrics:**
- Build feedback appears within 200ms
- Progress visible for operations >1s
- Zero performance regression in --quiet mode
- Error messages include actionable suggestions

---

## Phase 2: Intelligence & Context (Week 3-4)

**Goal:** Make CLI adapt to user context and provide smart suggestions

**Effort:** 10-12 days  
**Impact:** High - Makes CLI feel intelligent

### 2.1 Terminal & Environment Detection

**Files to modify:**
- `bengal/utils/rich_console.py` (enhance)
- `bengal/cli.py` (add smart defaults)

#### Task 2.1.1: Enhanced Environment Detection

**Location:** `bengal/utils/rich_console.py`

**Add new function:**
```python
from typing import Dict, Any
import shutil

def detect_environment() -> Dict[str, Any]:
    """
    Detect terminal and environment capabilities.
    
    Returns:
        Dictionary with environment info
    """
    env = {}
    
    # Terminal info
    console = get_console()
    env['is_terminal'] = console.is_terminal
    env['color_system'] = console.color_system
    env['width'] = console.width
    env['height'] = console.height
    
    # CI detection
    env['is_ci'] = any([
        os.getenv('CI'),
        os.getenv('CONTINUOUS_INTEGRATION'),
        os.getenv('GITHUB_ACTIONS'),
        os.getenv('GITLAB_CI'),
        os.getenv('CIRCLECI'),
        os.getenv('TRAVIS'),
    ])
    
    # Docker detection
    env['is_docker'] = (
        os.path.exists('/.dockerenv') or
        os.path.exists('/run/.containerenv')
    )
    
    # Git detection
    env['is_git_repo'] = os.path.exists('.git')
    
    # CPU cores (for parallel suggestions)
    import multiprocessing
    env['cpu_count'] = multiprocessing.cpu_count()
    
    # Terminal emulator detection
    term_program = os.getenv('TERM_PROGRAM', '')
    env['terminal_app'] = term_program or 'unknown'
    
    return env
```

**Acceptance Criteria:**
- [ ] Detects CI environments correctly
- [ ] Identifies Docker containers
- [ ] Detects Git repositories
- [ ] Determines CPU count
- [ ] Works on all platforms

**Estimated Time:** 2-3 hours

---

#### Task 2.1.2: Smart CLI Defaults

**Location:** `bengal/cli.py` (build command)

**Add smart defaults based on context:**
```python
from bengal.utils.rich_console import detect_environment

@main.command()
@click.option('--parallel/--no-parallel', default=None, help='...')  # None = auto-detect
# ... other options ...
def build(parallel, incremental, ...):
    """Build with smart defaults based on environment."""
    
    # Detect environment
    env = detect_environment()
    
    # Smart defaults
    if parallel is None:
        # Auto-enable parallel if we have multiple cores
        parallel = env['cpu_count'] > 1
    
    # In CI, auto-enable strict mode and disable colors
    if env['is_ci']:
        if strict is None:
            strict = True
        if quiet is None:
            quiet = True  # CI should be quieter by default
    
    # In git repo during dev, suggest incremental
    if env['is_git_repo'] and not incremental and not env['is_ci']:
        console = get_console()
        console.print(
            "[dim]💡 Tip: Use [cyan]--incremental[/cyan] for faster rebuilds "
            "during development[/dim]"
        )
    
    # Small suggestion for first-time users
    if not Path('.bengal-build.log').exists():
        console.print(
            "[dim]💡 First build? Check out [cyan]bengal serve[/cyan] "
            "for live preview[/dim]\n"
        )
    
    # ... rest of build logic ...
```

**Acceptance Criteria:**
- [ ] Parallel enabled by default on multi-core
- [ ] CI mode auto-enables strict and quiet
- [ ] Helpful tips shown for first-time users
- [ ] Tips are subtle (dim text, easy to ignore)

**Estimated Time:** 3-4 hours

---

### 2.2 Performance Analysis & Suggestions

**Files to modify:**
- `bengal/utils/performance_analyzer.py` (NEW)
- `bengal/orchestration/build.py`

#### Task 2.2.1: Create Performance Analyzer

**Create:** `bengal/utils/performance_analyzer.py`

```python
"""
Build performance analyzer that provides optimization suggestions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from bengal.utils.build_stats import BuildStats

@dataclass
class PerformanceHint:
    """A performance optimization hint."""
    severity: str  # 'info', 'warning', 'critical'
    message: str
    suggestion: str
    potential_impact: str  # e.g., "Could save ~4s"
    command: str = None  # e.g., "bengal build --parallel"

class PerformanceAnalyzer:
    """Analyzes build performance and provides optimization hints."""
    
    def __init__(self, stats: BuildStats, site):
        self.stats = stats
        self.site = site
    
    def analyze(self) -> List[PerformanceHint]:
        """
        Analyze build performance and generate hints.
        
        Returns:
            List of performance hints
        """
        hints = []
        
        # Check overall build speed
        hints.extend(self._check_build_speed())
        
        # Check rendering performance
        hints.extend(self._check_rendering())
        
        # Check asset processing
        hints.extend(self._check_assets())
        
        # Check for incremental build opportunity
        hints.extend(self._check_incremental())
        
        return hints
    
    def _check_build_speed(self) -> List[PerformanceHint]:
        """Check overall build speed."""
        hints = []
        
        # Calculate pages per second
        build_time_s = self.stats.build_time_ms / 1000
        pages_per_sec = self.stats.total_pages / build_time_s if build_time_s > 0 else 0
        
        # Thresholds
        if pages_per_sec < 10:
            # Very slow
            hints.append(PerformanceHint(
                severity='warning',
                message=f"Build is slow ({pages_per_sec:.1f} pages/sec)",
                suggestion="Consider enabling parallel processing",
                potential_impact="Could be 2-4x faster",
                command="bengal build --parallel"
            ))
        elif pages_per_sec < 50:
            # Could be faster
            if not self.stats.parallel:
                hints.append(PerformanceHint(
                    severity='info',
                    message=f"Build speed is moderate ({pages_per_sec:.1f} pages/sec)",
                    suggestion="Enable parallel processing for better performance",
                    potential_impact="Could save 30-50%",
                    command="bengal build --parallel"
                ))
        
        return hints
    
    def _check_rendering(self) -> List[PerformanceHint]:
        """Check rendering performance."""
        hints = []
        
        # Check if rendering is the bottleneck
        if self.stats.rendering_time_ms > self.stats.build_time_ms * 0.6:
            hints.append(PerformanceHint(
                severity='info',
                message="Rendering is 60%+ of build time",
                suggestion="Profile templates to identify slow operations",
                potential_impact="Optimization potential",
                command="bengal build --perf-profile profile.stats"
            ))
        
        # Check average time per page
        if self.stats.total_pages > 0:
            avg_ms = self.stats.rendering_time_ms / self.stats.total_pages
            if avg_ms > 100:  # More than 100ms per page
                hints.append(PerformanceHint(
                    severity='warning',
                    message=f"Templates are slow (avg {avg_ms:.0f}ms/page)",
                    suggestion="Check for expensive template operations (filters, includes)",
                    potential_impact="Could significantly speed up builds"
                ))
        
        return hints
    
    def _check_assets(self) -> List[PerformanceHint]:
        """Check asset processing performance."""
        hints = []
        
        if self.stats.assets_time_ms > self.stats.build_time_ms * 0.3:
            hints.append(PerformanceHint(
                severity='info',
                message="Asset processing is 30%+ of build time",
                suggestion="Consider asset fingerprinting and caching",
                potential_impact="Faster incremental builds"
            ))
        
        return hints
    
    def _check_incremental(self) -> List[PerformanceHint]:
        """Check if incremental builds would help."""
        hints = []
        
        if not self.stats.incremental and self.stats.total_pages > 50:
            estimated_speedup = min(10, self.stats.total_pages / 10)
            hints.append(PerformanceHint(
                severity='info',
                message="Incremental builds not enabled",
                suggestion="Use --incremental for much faster rebuilds during development",
                potential_impact=f"Could be {estimated_speedup:.0f}x faster on rebuilds",
                command="bengal build --incremental"
            ))
        
        return hints
    
    def format_hints(self, hints: List[PerformanceHint]) -> str:
        """Format hints for console output."""
        from bengal.utils.rich_console import get_console
        from rich.panel import Panel
        from rich.text import Text
        
        if not hints:
            return ""
        
        console = get_console()
        
        # Group by severity
        warnings = [h for h in hints if h.severity == 'warning']
        infos = [h for h in hints if h.severity == 'info']
        
        text = Text()
        
        if warnings:
            text.append("⚠️  Performance Warnings:\n\n", style="yellow bold")
            for hint in warnings:
                text.append(f"  • {hint.message}\n", style="yellow")
                text.append(f"    💡 {hint.suggestion}\n", style="cyan")
                if hint.potential_impact:
                    text.append(f"    ⚡ {hint.potential_impact}\n", style="green")
                if hint.command:
                    text.append(f"    $ {hint.command}\n", style="dim")
                text.append("\n")
        
        if infos:
            text.append("💡 Performance Tips:\n\n", style="cyan bold")
            for hint in infos:
                text.append(f"  • {hint.message}\n")
                text.append(f"    {hint.suggestion}\n", style="dim")
                if hint.command:
                    text.append(f"    $ {hint.command}\n", style="cyan")
                text.append("\n")
        
        return Panel(text, title="Performance Analysis", border_style="yellow")
```

**Acceptance Criteria:**
- [ ] Detects slow builds
- [ ] Suggests parallel processing when applicable
- [ ] Identifies rendering bottlenecks
- [ ] Recommends incremental builds
- [ ] Suggestions are actionable (include commands)

**Estimated Time:** 4-5 hours

---

#### Task 2.2.2: Integrate Performance Hints

**Location:** `bengal/cli.py` (build command, after stats display)

```python
# After displaying build stats
if not quiet and build_profile != BuildProfile.WRITER:
    from bengal.utils.performance_analyzer import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer(stats, site)
    hints = analyzer.analyze()
    
    if hints:
        console = get_console()
        console.print()
        console.print(analyzer.format_hints(hints))
```

**Acceptance Criteria:**
- [ ] Hints shown after build in theme-dev and dev modes
- [ ] No hints in writer mode (too noisy)
- [ ] No hints in quiet mode
- [ ] Hints are helpful, not annoying

**Estimated Time:** 1-2 hours

---

### 2.3 Command Suggestions

**Files to modify:**
- `bengal/cli.py` (main function)

#### Task 2.3.1: Add Typo Detection

**Location:** `bengal/cli.py` (main group)

```python
from difflib import get_close_matches
import sys

@click.group()
@click.version_option(version=__version__, prog_name="Bengal SSG")
@click.pass_context
def main(ctx) -> None:
    """
    🐯 Bengal SSG - A high-performance static site generator.
    
    Fast & fierce static site generation with personality!
    """
    # Handle unknown commands with suggestions
    if ctx.invoked_subcommand is None and len(sys.argv) > 1:
        unknown_cmd = sys.argv[1]
        
        # Get all available commands
        valid_commands = [cmd for cmd in main.commands.keys()]
        
        # Find similar commands
        matches = get_close_matches(unknown_cmd, valid_commands, n=3, cutoff=0.6)
        
        if matches:
            console = get_console()
            console.print(f"\n[red]Error:[/red] Unknown command '{unknown_cmd}'")
            console.print(f"\n[yellow]Did you mean:[/yellow]")
            for match in matches:
                console.print(f"  • [cyan]bengal {match}[/cyan]")
            console.print()
            console.print("[dim]Run 'bengal --help' for all commands[/dim]\n")
            sys.exit(1)
```

**Acceptance Criteria:**
- [ ] Typos suggest similar commands
- [ ] Suggestions are relevant (fuzzy matching)
- [ ] Works for common typos (buidl → build, serve → serve, etc.)

**Estimated Time:** 2 hours

---

### 2.4 Build Profile Persistence

**Files to create:**
- `bengal/utils/config_cache.py` (NEW)

#### Task 2.4.1: Save/Load Build Preferences

**Create:** `bengal/utils/config_cache.py`

```python
"""
User preference caching for CLI commands.
"""

from pathlib import Path
import json
from typing import Dict, Any, Optional

class ConfigCache:
    """Cache for user preferences and frequently used settings."""
    
    def __init__(self, site_root: Path):
        """Initialize config cache for a site."""
        self.cache_file = site_root / '.bengal-cache' / 'user-prefs.json'
        self.cache_file.parent.mkdir(exist_ok=True)
        self._cache = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            pass  # Fail silently
    
    def get_build_flags(self) -> Dict[str, Any]:
        """Get last used build flags."""
        return self._cache.get('build_flags', {})
    
    def save_build_flags(self, flags: Dict[str, Any]):
        """Save build flags for next time."""
        self._cache['build_flags'] = flags
        self._save()
    
    def get_profile(self) -> Optional[str]:
        """Get last used profile."""
        return self._cache.get('profile')
    
    def save_profile(self, profile: str):
        """Save profile preference."""
        self._cache['profile'] = profile
        self._save()
    
    def remember_tip_shown(self, tip_id: str):
        """Mark a tip as shown (don't show again)."""
        if 'tips_shown' not in self._cache:
            self._cache['tips_shown'] = []
        
        if tip_id not in self._cache['tips_shown']:
            self._cache['tips_shown'].append(tip_id)
            self._save()
    
    def was_tip_shown(self, tip_id: str) -> bool:
        """Check if a tip was already shown."""
        return tip_id in self._cache.get('tips_shown', [])
```

**Usage in CLI:**
```python
# In build command
from bengal.utils.config_cache import ConfigCache

cache = ConfigCache(root_path)

# Load previous flags
prev_flags = cache.get_build_flags()

# If user didn't specify parallel, use their last preference
if parallel is None:
    parallel = prev_flags.get('parallel', True)

# Save flags for next time
cache.save_build_flags({
    'parallel': parallel,
    'incremental': incremental,
    'profile': str(build_profile)
})

# Show tips only once
if not cache.was_tip_shown('incremental_tip'):
    console.print("[dim]💡 Tip: Use --incremental for faster rebuilds[/dim]")
    cache.remember_tip_shown('incremental_tip')
```

**Acceptance Criteria:**
- [ ] Preferences saved per-site
- [ ] Last used flags remembered
- [ ] Tips shown only once
- [ ] Cache file is gitignored

**Estimated Time:** 3-4 hours

---

### 2.5 Testing & Documentation

#### Task 2.5.1: Tests for Phase 2

**Files to create:**
- `tests/unit/utils/test_performance_analyzer.py`
- `tests/unit/utils/test_config_cache.py`

```python
# tests/unit/utils/test_performance_analyzer.py
import pytest
from bengal.utils.performance_analyzer import PerformanceAnalyzer
from bengal.utils.build_stats import BuildStats

def test_analyzer_detects_slow_build():
    """Test that analyzer detects slow builds."""
    stats = BuildStats(
        total_pages=100,
        build_time_ms=60000,  # 60 seconds for 100 pages = slow
        parallel=False
    )
    
    analyzer = PerformanceAnalyzer(stats, site=None)
    hints = analyzer.analyze()
    
    # Should suggest parallel processing
    assert any('parallel' in h.suggestion.lower() for h in hints)

def test_analyzer_no_hints_for_fast_build():
    """Test that fast builds don't generate hints."""
    stats = BuildStats(
        total_pages=100,
        build_time_ms=1000,  # 1 second for 100 pages = fast
        parallel=True
    )
    
    analyzer = PerformanceAnalyzer(stats, site=None)
    hints = analyzer.analyze()
    
    # Might have incremental suggestion, but not performance warnings
    warnings = [h for h in hints if h.severity == 'warning']
    assert len(warnings) == 0
```

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Edge cases covered
- [ ] Performance hints are accurate

**Estimated Time:** 3 hours

---

#### Task 2.5.2: Update Documentation

**Files to update:**
- `README.md`
- `docs/cli-usage.md` (if exists)

Add section on smart features:

```markdown
## Smart CLI Features

Bengal's CLI adapts to your environment and provides intelligent suggestions:

### Context-Aware Defaults
- **CI Detection:** Automatically enables `--strict` and `--quiet` in CI environments
- **Multi-Core:** Enables `--parallel` by default on multi-core systems
- **Git Repos:** Suggests `--incremental` for faster development

### Performance Hints
After builds, Bengal analyzes performance and suggests optimizations:

```bash
bengal build

💡 Performance Tips:
  • Build speed is moderate (45 pages/sec)
    Enable parallel processing for better performance
    $ bengal build --parallel
```

### Preference Persistence
Bengal remembers your build preferences:

```bash
# First time
bengal build --incremental --parallel

# Next time (remembers your preferences)
bengal build  # Uses incremental + parallel automatically
```

### Command Suggestions
Typos? Bengal suggests corrections:

```bash
$ bengal buidl

Error: Unknown command 'buidl'

Did you mean:
  • bengal build
```
```

**Acceptance Criteria:**
- [ ] Documentation updated
- [ ] Examples provided
- [ ] Features clearly explained

**Estimated Time:** 2 hours

---

### Phase 2 Summary

**Total Estimated Time:** 10-12 days

**Deliverables:**
- [ ] Environment detection (CI, Docker, Git)
- [ ] Smart CLI defaults based on context
- [ ] Performance analysis with suggestions
- [ ] Command typo detection
- [ ] Build preference persistence
- [ ] All tests passing
- [ ] Documentation updated

**Success Metrics:**
- CLI adapts to 3+ environment types
- Performance hints help optimize builds
- Users notice "smart" behavior
- Typos suggest correct commands

---

## Phase 3: Interactivity (Week 5-6)

**Goal:** Add interactive features and guided workflows

**Effort:** 10-12 days  
**Impact:** High - Makes CLI feel conversational

### 3.1 Add Questionary Library

#### Task 3.1.1: Install Dependencies

```bash
# Add to requirements.txt
questionary>=2.0.0
```

**Acceptance Criteria:**
- [ ] Library installs without conflicts
- [ ] Works on all platforms

**Estimated Time:** 30 minutes

---

### 3.2 Interactive Project Initialization

**Files to modify:**
- `bengal/cli.py` (new site command)
- `bengal/utils/project_templates.py` (NEW)

#### Task 3.2.1: Create Project Templates

**Create:** `bengal/utils/project_templates.py`

```python
"""
Project templates for interactive site creation.
"""

from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path

@dataclass
class ProjectTemplate:
    """A site project template."""
    id: str
    name: str
    description: str
    theme: str
    content_structure: Dict[str, List[str]]  # directory: [files]
    sample_content: bool
    config_extras: Dict[str, any]

# Define templates
TEMPLATES = {
    'blog': ProjectTemplate(
        id='blog',
        name='Blog',
        description='Personal writing, posts with tags and archives',
        theme='default',
        content_structure={
            'posts': ['first-post.md', 'second-post.md'],
            'pages': ['about.md', 'contact.md'],
        },
        sample_content=True,
        config_extras={
            'taxonomies': {'tags': {}, 'categories': {}},
            'pagination': {'enabled': True, 'per_page': 10}
        }
    ),
    
    'docs': ProjectTemplate(
        id='docs',
        name='Documentation',
        description='Technical docs with sidebar navigation',
        theme='docs',
        content_structure={
            'docs': ['getting-started.md', 'installation.md', 'usage.md'],
            'docs/guides': ['tutorial-1.md'],
            'docs/api': ['reference.md'],
        },
        sample_content=True,
        config_extras={
            'menu': {
                'docs': [
                    {'title': 'Getting Started', 'url': '/docs/getting-started'},
                    {'title': 'Guides', 'children': []}
                ]
            }
        }
    ),
    
    'portfolio': ProjectTemplate(
        id='portfolio',
        name='Portfolio',
        description='Showcase projects and case studies',
        theme='default',
        content_structure={
            'projects': ['project-1.md', 'project-2.md'],
            'pages': ['about.md'],
        },
        sample_content=True,
        config_extras={
            'taxonomies': {'technologies': {}, 'categories': {}}
        }
    ),
    
    'minimal': ProjectTemplate(
        id='minimal',
        name='Minimal',
        description='Start from scratch with basic structure',
        theme='minimal',
        content_structure={
            '': ['index.md'],
        },
        sample_content=False,
        config_extras={}
    ),
}

# Sample content generators
def generate_blog_post(title: str, n: int) -> str:
    """Generate sample blog post content."""
    return f"""---
title: {title}
date: 2025-10-{n:02d}
tags: [sample, blog]
---

# {title}

This is a sample blog post to help you get started with Bengal.

## What's Next?

1. Edit this file to create your own content
2. Create new posts in the `content/posts/` directory
3. Run `bengal serve` to preview your changes

Happy writing! 🐯
"""

def generate_doc_page(title: str, section: str) -> str:
    """Generate sample documentation page."""
    return f"""---
title: {title}
section: {section}
---

# {title}

This is a sample documentation page.

## Overview

Replace this content with your own documentation.

## Example

```python
# Your code examples go here
print("Hello, Bengal!")
```

## Next Steps

- Learn more about [Bengal features](/docs/)
- Check out the [API reference](/docs/api/)
"""

def generate_project_page(title: str, tech: List[str]) -> str:
    """Generate sample project page."""
    return f"""---
title: {title}
technologies: {tech}
featured: true
---

# {title}

A sample project to showcase in your portfolio.

## Overview

Describe your project here.

## Technologies Used

{chr(10).join(f'- {t}' for t in tech)}

## Results

Highlight your achievements and outcomes.
"""

CONTENT_GENERATORS = {
    'blog-post': generate_blog_post,
    'doc-page': generate_doc_page,
    'project': generate_project_page,
}
```

**Acceptance Criteria:**
- [ ] Templates defined for common site types
- [ ] Content generators create realistic samples
- [ ] Templates are extensible

**Estimated Time:** 3-4 hours

---

#### Task 3.2.2: Create Interactive Setup Wizard

**Location:** `bengal/cli.py` (enhance `new site` command)

```python
import questionary
from questionary import Style
from bengal.utils.project_templates import TEMPLATES, CONTENT_GENERATORS

# Bengal-themed questionary style
bengal_style = Style([
    ('qmark', 'fg:#f39c12 bold'),        # Question mark (yellow/bengal)
    ('question', 'bold'),                 # Question text
    ('answer', 'fg:#2ecc71 bold'),       # User's answer (green)
    ('pointer', 'fg:#f39c12 bold'),      # Selection pointer (yellow)
    ('highlighted', 'fg:#f39c12 bold'),  # Highlighted choice (yellow)
    ('selected', 'fg:#2ecc71'),          # Selected choice (green)
    ('instruction', 'fg:#858585'),       # Instructions (dim)
])

@new.command(name='site')
@click.argument('name', required=False)
@click.option('--template', type=click.Choice(['blog', 'docs', 'portfolio', 'minimal']),
              help='Project template (skips wizard)')
@click.option('--no-samples', is_flag=True, help='Skip sample content')
def site_interactive(name, template, no_samples):
    """
    Create a new Bengal site (interactive wizard).
    
    If NAME is provided, creates site with that name.
    Otherwise, prompts for configuration.
    """
    console = get_console()
    
    try:
        # Welcome
        console.print()
        console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold]Let's create your Bengal site![/bold]")
        console.print()
        
        # Get project name
        if not name:
            name = questionary.text(
                "Project name:",
                validate=lambda x: len(x) > 0 and x.replace('-', '').replace('_', '').isalnum(),
                style=bengal_style
            ).ask()
            
            if not name:  # User cancelled
                console.print("\n[yellow]Cancelled[/yellow]")
                return
        
        # Check if directory exists
        site_path = Path(name)
        if site_path.exists():
            overwrite = questionary.confirm(
                f"Directory '{name}' already exists. Overwrite?",
                default=False,
                style=bengal_style
            ).ask()
            
            if not overwrite:
                console.print("\n[yellow]Cancelled[/yellow]")
                return
            
            import shutil
            shutil.rmtree(site_path)
        
        # Get template (if not provided via --template)
        if not template:
            template_choice = questionary.select(
                "What kind of site?",
                choices=[
                    questionary.Choice(
                        f"{t.name} - {t.description}",
                        value=t.id
                    )
                    for t in TEMPLATES.values()
                ],
                style=bengal_style
            ).ask()
            
            if not template_choice:
                console.print("\n[yellow]Cancelled[/yellow]")
                return
            
            template = template_choice
        
        # Get template config
        template_config = TEMPLATES[template]
        
        # Ask about sample content (if template supports it)
        include_samples = not no_samples
        if template_config.sample_content and not no_samples:
            include_samples = questionary.confirm(
                "Include sample content?",
                default=True,
                style=bengal_style
            ).ask()
        
        # Create the site
        console.print()
        with console.status("[bold cyan]Creating your site...", spinner="dots"):
            create_site_from_template(
                name=name,
                template=template_config,
                include_samples=include_samples
            )
            time.sleep(0.5)  # Brief pause for UX
        
        # Success message
        console.print()
        console.print(f"[green bold]✓[/green bold] Site created: [cyan]{name}/[/cyan]")
        console.print()
        
        # Show next steps
        console.print("[yellow bold]Next steps:[/yellow bold]")
        console.print()
        console.print(f"  [dim]1.[/dim] cd {name}")
        console.print(f"  [dim]2.[/dim] bengal serve")
        console.print()
        
        # Optional: open in browser
        if questionary.confirm(
            "Open in editor now?",
            default=False,
            style=bengal_style
        ).ask():
            import subprocess
            try:
                subprocess.run(['code', str(site_path)])  # VS Code
            except FileNotFoundError:
                try:
                    subprocess.run(['open', str(site_path)])  # macOS
                except FileNotFoundError:
                    pass  # Can't auto-open
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[red bold]Error:[/red bold] {e}")
        raise click.Abort()

def create_site_from_template(name: str, template: ProjectTemplate, include_samples: bool):
    """Create site directory structure from template."""
    from bengal.utils.atomic_write import atomic_write_text
    
    site_path = Path(name)
    
    # Create base directories
    site_path.mkdir(parents=True)
    (site_path / 'content').mkdir()
    (site_path / 'assets' / 'css').mkdir(parents=True)
    (site_path / 'assets' / 'js').mkdir()
    (site_path / 'assets' / 'images').mkdir()
    (site_path / 'templates').mkdir()
    
    # Create config file
    config_content = generate_config(name, template)
    atomic_write_text(site_path / 'bengal.toml', config_content)
    
    # Create content structure
    if include_samples and template.sample_content:
        for directory, files in template.content_structure.items():
            if directory:
                content_dir = site_path / 'content' / directory
                content_dir.mkdir(parents=True, exist_ok=True)
            else:
                content_dir = site_path / 'content'
            
            # Generate sample files
            for i, filename in enumerate(files, 1):
                content = generate_sample_content(
                    template.id, 
                    filename, 
                    i
                )
                atomic_write_text(content_dir / filename, content)
    else:
        # Just create index
        atomic_write_text(
            site_path / 'content' / 'index.md',
            "---\ntitle: Home\n---\n\n# Welcome to Bengal\n\nStart editing this file!"
        )
    
    # Create README
    readme = generate_readme(name, template)
    atomic_write_text(site_path / 'README.md', readme)

def generate_config(name: str, template: ProjectTemplate) -> str:
    """Generate bengal.toml config for template."""
    import toml
    
    config = {
        'site': {
            'title': name,
            'baseurl': '',
            'theme': template.theme,
        },
        'build': {
            'output_dir': 'public',
            'parallel': True,
        },
        'assets': {
            'minify': True,
            'fingerprint': True,
        }
    }
    
    # Add template-specific config
    config.update(template.config_extras)
    
    return toml.dumps(config)

def generate_sample_content(template_id: str, filename: str, index: int) -> str:
    """Generate sample content based on template type."""
    # Use content generators
    if template_id == 'blog':
        return CONTENT_GENERATORS['blog-post'](
            f"Sample Post {index}",
            index
        )
    elif template_id == 'docs':
        return CONTENT_GENERATORS['doc-page'](
            filename.replace('.md', '').replace('-', ' ').title(),
            'documentation'
        )
    elif template_id == 'portfolio':
        return CONTENT_GENERATORS['project'](
            f"Project {index}",
            ['Python', 'Web Development']
        )
    else:
        return "---\ntitle: Sample Page\n---\n\n# Sample Page\n\nYour content here."
```

**Acceptance Criteria:**
- [ ] Interactive wizard guides user through setup
- [ ] Templates create realistic site structures
- [ ] Sample content is helpful (not lorem ipsum)
- [ ] Can be skipped with flags for automation
- [ ] Works in non-interactive terminals (falls back to flags)

**Estimated Time:** 6-8 hours

---

### 3.3 Interactive Health Check Review

**Files to modify:**
- `bengal/health/report.py`
- `bengal/cli.py` (build command)

#### Task 3.3.1: Add Interactive Review to Health Checks

**Location:** `bengal/health/report.py`

```python
def interactive_review(self) -> None:
    """
    Interactively review health check results.
    
    Allows user to:
    - View detailed error information
    - Auto-fix some issues
    - Export report
    """
    from bengal.utils.rich_console import get_console, should_use_rich
    import questionary
    
    console = get_console()
    
    if not should_use_rich():
        # Fallback to non-interactive
        console.print(self.format_console(verbose=True))
        return
    
    # Show summary first
    console.print(self._format_normal())
    console.print()
    
    # Ask if user wants to review
    if not questionary.confirm(
        "Review issues in detail?",
        default=True
    ).ask():
        return
    
    # Review each validator with issues
    for vr in self.validator_reports:
        if not vr.has_issues():
            continue
        
        console.print()
        console.print(Panel(
            f"[bold]{vr.validator_name}[/bold]\n\n" +
            "\n".join(f"• {r.message}" for r in vr.results if r.is_problem()),
            title=f"{vr.status_emoji} {vr.validator_name}",
            border_style="yellow"
        ))
        
        # Show details
        for result in vr.results:
            if result.is_problem():
                console.print(f"\n[yellow]Issue:[/yellow] {result.message}")
                
                if result.recommendation:
                    console.print(f"[cyan]💡 {result.recommendation}[/cyan]")
                
                if result.details:
                    console.print("\n[dim]Details:[/dim]")
                    for detail in result.details[:5]:
                        console.print(f"  • {detail}")
                    if len(result.details) > 5:
                        console.print(f"  ... and {len(result.details) - 5} more")
        
        # Offer fixes if available
        if vr.validator_name == "Link Validation":
            if questionary.confirm(
                "Attempt to fix broken internal links?",
                default=False
            ).ask():
                fixed_count = auto_fix_links(vr)
                if fixed_count > 0:
                    console.print(f"[green]✓ Fixed {fixed_count} links[/green]")
                else:
                    console.print("[yellow]No fixable links found[/yellow]")
    
    # Export option
    if questionary.confirm(
        "Export report to file?",
        default=False
    ).ask():
        format_choice = questionary.select(
            "Format:",
            choices=['json', 'markdown', 'html']
        ).ask()
        
        filename = f".bengal-health-report.{format_choice}"
        self.export(filename, format_choice)
        console.print(f"[green]✓ Report saved to {filename}[/green]")
```

**Acceptance Criteria:**
- [ ] Interactive review after build (if issues found)
- [ ] Can drill into specific validators
- [ ] Offers auto-fixes where applicable
- [ ] Can export report in multiple formats
- [ ] Gracefully falls back if not interactive

**Estimated Time:** 4-5 hours

---

### 3.4 Shell Completions

**Files to modify:**
- `bengal/cli.py` (add completion command)

#### Task 3.4.1: Add Shell Completion Install Command

```python
@main.command()
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish']),
              help='Shell type (auto-detected if not specified)')
def completion(shell):
    """
    Install shell completion for bengal commands.
    
    Enables tab-completion in your shell:
      - Commands: bengal [TAB]
      - Options: bengal build --[TAB]
      - Paths: bengal build [TAB]
    
    Examples:
        bengal completion          # Auto-detect shell
        bengal completion --shell bash
        bengal completion --shell zsh
    """
    import click_completion
    from click_completion import get_auto_shell
    
    console = get_console()
    
    # Detect shell if not specified
    if not shell:
        try:
            shell = get_auto_shell()[0]
        except Exception:
            console.print("[red]Error:[/red] Could not detect shell")
            console.print("Please specify: [cyan]bengal completion --shell bash[/cyan]")
            raise click.Abort()
    
    console.print()
    console.print(f"[cyan]Installing completion for {shell}...[/cyan]")
    console.print()
    
    try:
        # Get completion code
        click_completion.init()
        completion_code = click_completion.get_code(shell=shell)
        
        # Install based on shell
        if shell == 'bash':
            install_path = Path.home() / '.bashrc'
            append_line = f"\n# Bengal completion\neval \"$(_BENGAL_COMPLETE={shell}_source bengal)\"\n"
        elif shell == 'zsh':
            install_path = Path.home() / '.zshrc'
            append_line = f"\n# Bengal completion\neval \"$(_BENGAL_COMPLETE={shell}_source bengal)\"\n"
        elif shell == 'fish':
            install_path = Path.home() / '.config' / 'fish' / 'completions' / 'bengal.fish'
            install_path.parent.mkdir(parents=True, exist_ok=True)
            append_line = completion_code
        
        # Check if already installed
        if install_path.exists():
            content = install_path.read_text()
            if 'BENGAL_COMPLETE' in content or 'bengal completion' in content:
                console.print("[yellow]Completion already installed[/yellow]")
                console.print(f"[dim]If having issues, remove from {install_path}[/dim]")
                return
        
        # Install
        with open(install_path, 'a') as f:
            f.write(append_line)
        
        console.print("[green]✓ Completion installed![/green]")
        console.print()
        console.print("[yellow]To activate:[/yellow]")
        console.print(f"  source {install_path}")
        console.print()
        console.print("[dim]Or restart your shell[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[yellow]Manual installation:[/yellow]")
        console.print(f"Add to your {shell} config:")
        console.print(f"  eval \"$(_BENGAL_COMPLETE={shell}_source bengal)\"")
        raise click.Abort()
```

**Acceptance Criteria:**
- [ ] Works on bash, zsh, fish
- [ ] Auto-detects shell
- [ ] Provides manual fallback
- [ ] Doesn't break if already installed

**Estimated Time:** 3-4 hours

---

### 3.5 Testing & Documentation

#### Task 3.5.1: Integration Tests

**Files to create:**
- `tests/integration/test_interactive_cli.py`

```python
"""Integration tests for interactive CLI features."""

import pytest
from click.testing import CliRunner
from bengal.cli import main
from unittest.mock import patch

def test_interactive_site_creation_with_input():
    """Test interactive site creation with simulated input."""
    runner = CliRunner()
    
    # Simulate user input
    user_input = [
        'mysite',           # Project name
        '\x1b[B\n',        # Select 'Blog' (down arrow + enter)
        'y',                # Include samples
        'n',                # Don't open in editor
    ]
    
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ['new', 'site'],
            input='\n'.join(user_input)
        )
        
        # Should succeed
        assert result.exit_code == 0
        
        # Should create site
        assert Path('mysite').exists()
        assert Path('mysite/bengal.toml').exists()
        assert Path('mysite/content').exists()

def test_non_interactive_site_creation():
    """Test site creation with flags (non-interactive)."""
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ['new', 'site', 'mysite', '--template', 'minimal', '--no-samples']
        )
        
        assert result.exit_code == 0
        assert Path('mysite').exists()
```

**Acceptance Criteria:**
- [ ] Tests pass
- [ ] Interactive and non-interactive modes tested
- [ ] Edge cases covered

**Estimated Time:** 3 hours

---

#### Task 3.5.2: Update Documentation

**Files to update:**
- `README.md`
- `docs/getting-started.md`
- `docs/cli-reference.md`

Add examples of interactive features:

```markdown
## Getting Started

### Create a New Site (Interactive)

Bengal's interactive wizard helps you get started:

```bash
bengal new site

    ᓚᘏᗢ  Let's create your Bengal site!

? Project name: myblog
? What kind of site?
  ❯ Blog - Personal writing, posts with tags and archives
    Documentation - Technical docs with sidebar navigation
    Portfolio - Showcase projects and case studies
    Minimal - Start from scratch
? Include sample content? Yes

✓ Site created: myblog/

Next steps:
  1. cd myblog
  2. bengal serve
```

### Non-Interactive Mode

For automation or if you prefer flags:

```bash
bengal new site myblog --template blog --no-samples
```

## Shell Completion

Enable tab-completion for faster workflows:

```bash
# Install completion
bengal completion

# Now you can use tab completion:
bengal b[TAB]      # → bengal build
bengal build --[TAB]  # → shows all options
```

## Interactive Health Checks

After builds, interactively review and fix issues:

```bash
bengal build --dev

🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ Link Validation  3 broken links

? Review issues in detail? Yes
? Attempt to fix broken internal links? Yes

✓ Fixed 1 link
```
```

**Acceptance Criteria:**
- [ ] Documentation complete
- [ ] Examples work as shown
- [ ] Screenshots/GIFs added (optional but nice)

**Estimated Time:** 2-3 hours

---

### Phase 3 Summary

**Total Estimated Time:** 10-12 days

**Deliverables:**
- [ ] Questionary library integrated
- [ ] Interactive project initialization wizard
- [ ] Interactive health check review
- [ ] Shell completions (bash/zsh/fish)
- [ ] All tests passing
- [ ] Documentation complete

**Success Metrics:**
- New users can create site without reading docs
- Health check review helps fix issues
- Shell completions speed up workflows
- Interactive mode feels polished

---

## Testing Strategy

### Unit Tests

**Coverage Target:** >80% for new code

**Key Areas:**
1. Rich console wrapper
2. Environment detection
3. Performance analyzer
4. Config cache
5. Error formatters

**Run:**
```bash
pytest tests/unit/ -v --cov=bengal --cov-report=html
```

---

### Integration Tests

**Key Scenarios:**
1. Build with progress bars
2. Error display in various modes
3. Interactive site creation
4. Health check review
5. Performance hints

**Run:**
```bash
pytest tests/integration/ -v
```

---

### Manual Testing

**Test Matrix:**

| Platform | Terminal | Test Scenario |
|----------|----------|---------------|
| macOS | Terminal.app | Build with progress |
| macOS | iTerm2 | Interactive site creation |
| Linux | GNOME Terminal | Health check review |
| Linux | xterm | Fallback behavior |
| Windows | PowerShell | Build with rich output |
| Windows | Windows Terminal | Color support |
| Windows | cmd.exe | Basic fallback |
| All | CI (GitHub Actions) | No ANSI, quiet mode |

---

### Performance Testing

**Before/After Comparison:**

```bash
# Baseline (before changes)
time bengal build --quiet

# With progress (should be <1% slower)
time bengal build

# Compare
```

**Acceptance:**
- Rich output adds <1% to build time
- Quiet mode has zero overhead
- Memory usage unchanged

---

### Accessibility Testing

**Requirements:**
- Works with screen readers
- Color-blind friendly (use shapes + colors)
- High contrast mode supported
- Works without Unicode fallback

---

## Rollout Plan

### Alpha Release (Internal)

**Timeline:** After Phase 1 complete

**Scope:**
- Rich progress bars
- Enhanced errors
- Build dashboard

**Testing:**
- Internal team testing
- 2-3 friendly beta users
- Gather feedback

---

### Beta Release (Public)

**Timeline:** After Phase 2 complete

**Scope:**
- All Phase 1 + 2 features
- Performance hints
- Smart defaults

**Announcement:**
- Blog post: "Introducing Bengal's Smart CLI"
- Show GIFs/videos of features
- Request feedback

**Success Criteria:**
- No major bugs reported
- Positive feedback on UX
- Performance acceptable

---

### Stable Release (v1.0)

**Timeline:** After Phase 3 complete

**Scope:**
- All features complete
- Interactive wizard
- Shell completions

**Launch Activities:**
1. **Documentation:** Complete guide with examples
2. **Blog Post:** "Why We Obsess Over CLI UX"
3. **Demo Video:** 2-3 minute showcase
4. **Social:** Tweet thread with examples
5. **Community:** Post in relevant subreddits/forums

**Marketing Angle:**
"The SSG with the CLI experience you'll actually enjoy"

---

## Success Metrics

### Quantitative Metrics

**Performance:**
- [ ] First feedback <200ms ✓
- [ ] Progress visible for ops >1s ✓
- [ ] Rich output adds <1% overhead ✓
- [ ] Zero overhead in --quiet mode ✓

**Coverage:**
- [ ] Unit test coverage >80% ✓
- [ ] Integration tests for all features ✓
- [ ] Manual testing on 3+ platforms ✓

**Adoption:**
- [ ] 50%+ of builds use rich output
- [ ] 25%+ use interactive wizard
- [ ] 10%+ install shell completions

---

### Qualitative Metrics

**User Feedback:**
- "Bengal's CLI is a joy to use"
- "The progress bars are so satisfying"
- "Error messages actually helped me fix the problem"
- "The wizard made setup painless"

**Community Response:**
- Positive mentions in comparisons
- CLI cited as differentiator
- Screenshots shared by users
- "Delightful" appears in reviews

**Internal Validation:**
- Team prefers using Bengal over alternatives
- CLI doesn't cause support tickets
- Contributors praise codebase quality

---

## Risk Mitigation

### Risk 1: Terminal Compatibility Issues

**Probability:** Medium  
**Impact:** High

**Mitigation:**
- Test on 10+ terminal types
- Graceful fallback for unsupported features
- Respect NO_COLOR and CI environments
- Provide --simple-output flag

**Contingency:**
- If major compatibility issues, make rich opt-in
- Add --rich flag to explicitly enable

---

### Risk 2: Performance Regression

**Probability:** Low  
**Impact:** High

**Mitigation:**
- Benchmark before/after each phase
- Lazy-load rich library (import only when needed)
- Disable in --quiet mode
- Profile with `bengal perf`

**Contingency:**
- If >2% overhead detected, optimize rendering frequency
- Make progress bars optional (--no-progress flag)

---

### Risk 3: User Confusion

**Probability:** Low  
**Impact:** Medium

**Mitigation:**
- Test with new users
- Provide clear documentation
- Show tips only once (cache)
- Make interactive features skippable

**Contingency:**
- Add --classic flag for old behavior
- Gather feedback and iterate

---

### Risk 4: Maintenance Burden

**Probability:** Medium  
**Impact:** Medium

**Mitigation:**
- Keep dependencies minimal
- Abstract terminal output behind interface
- Comprehensive test coverage
- Document architecture

**Contingency:**
- If dependencies cause issues, vendor critical code
- Provide minimal fallback mode

---

## Dependencies & Prerequisites

### Required Skills

**Team Member 1 (Primary Developer):**
- Python CLI development (click, rich)
- Terminal/ANSI understanding
- UX/UI sensibility

**Team Member 2 (Testing):**
- Cross-platform testing experience
- Test automation
- CI/CD pipelines

**Team Member 3 (Documentation):**
- Technical writing
- Creating demos/videos
- Community engagement

---

### Infrastructure

**Development:**
- Access to macOS, Linux, Windows environments
- CI/CD pipeline (GitHub Actions)
- Test site with various sizes (10, 100, 1000 pages)

**Testing:**
- Virtual machines or containers for platform testing
- Screen recording software for demos
- Beta user group (5-10 people)

---

### Timeline Dependencies

**Phase 1** (Weeks 1-2):
- No blockers, can start immediately
- Requires: rich library approval

**Phase 2** (Weeks 3-4):
- Depends: Phase 1 complete and tested
- Can start performance analyzer in parallel

**Phase 3** (Weeks 5-6):
- Depends: Phase 1 & 2 complete
- Questionary testing needed

---

## Post-Launch Plan

### Month 1: Monitoring

**Activities:**
- Monitor GitHub issues for CLI-related bugs
- Track usage metrics (if telemetry available)
- Collect user feedback
- Fix critical bugs

**Success Criteria:**
- <5 CLI-related bugs reported
- Positive feedback ratio >80%
- No performance regressions

---

### Month 2-3: Iteration

**Activities:**
- Implement most-requested features
- Add more templates to wizard
- Improve error suggestions based on common issues
- Create video tutorials

**Potential Enhancements:**
- More project templates
- AI-powered error suggestions
- Build time predictions
- Template profiler tool

---

### Month 4-6: Expansion

**Advanced Features:**
- Deploy command integration
- Plugin system for custom templates
- Telemetry (opt-in) for usage patterns
- Integration with popular editors

**Community:**
- Showcase sites built with Bengal
- CLI tips & tricks blog series
- Livestream: "Building with Bengal"

---

## Appendix

### A: Code Review Checklist

**For Each PR:**
- [ ] All tests pass (unit + integration)
- [ ] No performance regression (<1% overhead)
- [ ] Works on Windows, macOS, Linux
- [ ] Graceful fallback for dumb terminals
- [ ] Documentation updated
- [ ] Manual testing completed
- [ ] No new dependencies without approval
- [ ] Code follows project style guide

---

### B: Beta Tester Feedback Form

**Questions for Beta Users:**

1. **First Impressions** (1-5 scale):
   - CLI feels modern and polished
   - Progress indicators are helpful
   - Error messages are clear
   - Interactive features are intuitive

2. **Specific Feedback:**
   - What did you love most?
   - What was confusing?
   - Did anything feel slow?
   - What's missing?

3. **Comparison:**
   - Have you used other SSGs? Which?
   - How does Bengal's CLI compare?
   - Would you switch to Bengal? Why/why not?

4. **Technical:**
   - What OS/terminal are you using?
   - Any bugs or issues?
   - Performance acceptable?

---

### C: Performance Benchmarks

**Baseline Metrics (Before):**
```
Site: 100 pages
Build time: 2.34s
Output: Static text
```

**Target Metrics (After):**
```
Site: 100 pages
Build time: 2.36s (<1% increase)
Output: Rich with progress
Quiet mode: 2.34s (no change)
```

**Large Site:**
```
Site: 1000 pages
Build time: 18.2s
Progress updates: 4 FPS
Memory overhead: <5MB
```

---

### D: Launch Checklist

**Pre-Launch:**
- [ ] All 3 phases complete
- [ ] Tests passing (100% pass rate)
- [ ] Documentation complete
- [ ] Demo video created
- [ ] Blog post drafted
- [ ] Beta feedback addressed
- [ ] Performance validated
- [ ] Cross-platform testing done

**Launch Day:**
- [ ] Merge to main
- [ ] Tag release (v1.0.0)
- [ ] Publish blog post
- [ ] Tweet announcement
- [ ] Post on Reddit/HN
- [ ] Update website
- [ ] Email beta users

**Post-Launch:**
- [ ] Monitor GitHub issues
- [ ] Respond to feedback
- [ ] Fix critical bugs within 24h
- [ ] Thank contributors
- [ ] Plan next iteration

---

## Summary

This implementation plan transforms Bengal's CLI from "good" to "exceptional" in 6 weeks through:

1. **Phase 1 (2 weeks):** Animated feedback with rich progress bars and enhanced errors
2. **Phase 2 (2 weeks):** Intelligent behavior with context awareness and performance hints
3. **Phase 3 (2 weeks):** Interactive features with guided workflows and shell completions

**Key Principles:**
- Persona-aware (respect Writer/Theme-Dev/Developer profiles)
- Graceful degradation (works in all environments)
- Performance-conscious (<1% overhead)
- Well-tested (>80% coverage)

**Expected Outcome:**
Bengal's CLI becomes a competitive differentiator—the thing people remember and recommend.

**Next Steps:**
1. Review plan with team
2. Assign roles
3. Set up Phase 1 branch
4. Begin Task 1.1.1 (Add dependencies)

Let's make Bengal's CLI **fierce**! 🐯

