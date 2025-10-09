# Bengal CLI Excellence Analysis
## Making Bengal's CLI a Differentiation Point

**Date:** October 9, 2025  
**Purpose:** Deep analysis of Bengal's CLI ergonomics across all user personas and identification of opportunities to differentiate through polished CLI experience

---

## Executive Summary

Bengal has a **solid foundation** for CLI excellence but significant opportunities exist to transform it into a true product differentiator. The current CLI is functional, persona-aware, and thoughtfully designed, but lacks the **animated feedback**, **interactive polish**, and **delightful details** that create memorable developer experiences.

**Key Finding:** Bengal's profile-based architecture (Writer/Theme-Dev/Developer) is **brilliant** and provides the perfect foundation for persona-specific CLI experiences. We should lean into this hard.

**Opportunity:** Most SSGs have mediocre CLIs. A truly excellent CLI could be Bengal's "signature" - the thing people remember and recommend it for.

---

## Current State Assessment

### ✅ Strengths

1. **Persona-Aware Design**
   - Three profiles (Writer, Theme-Dev, Developer) with different output levels
   - Smart defaults based on user intent
   - Thoughtful information hierarchy

2. **Good Information Architecture**
   - Clear command structure (`build`, `serve`, `graph`, `autodoc`, etc.)
   - Helpful descriptions and examples
   - Logical flag grouping

3. **Visual Polish (Basic)**
   - Unicode emoji usage (🐯, 📊, ✨, etc.)
   - ASCII art cat mascot (ᓚᘏᗢ)
   - ANSI colors with click.style()
   - Box-drawing characters for structure

4. **Error Handling**
   - Template error display with context
   - Grouped warnings by type
   - Actionable error messages

5. **Developer Experience**
   - Incremental builds
   - File watching with auto-rebuild
   - Performance profiling support
   - Structured logging to file

### ⚠️ Gaps & Opportunities

1. **Static, Not Animated**
   - No spinners during long operations
   - No progress bars for multi-step processes
   - Build happens in silence until it's done
   - No visual feedback that work is happening

2. **Limited Interactivity**
   - No autocomplete for commands
   - No interactive prompts for common tasks
   - Confirmation prompts are basic (yes/no)
   - No command suggestions on typos

3. **Information Density**
   - Lots of sequential print statements
   - No live-updating displays
   - No collapsible/expandable sections
   - Health check output can be overwhelming

4. **Missing Contextual Intelligence**
   - Doesn't adapt to terminal capabilities
   - No special handling for CI/CD environments
   - Doesn't remember user preferences
   - No command history or suggestions

5. **Limited Real-Time Feedback**
   - Dev server shows rebuild results but no progress during rebuild
   - No indication of which files are being processed
   - No throughput metrics during build
   - Build phases are logged but not visualized

---

## User Persona Analysis

### 👩‍💻 Persona 1: Content Writer
**Primary Goal:** "Just tell me if it worked"

**Current Experience:**
```bash
bengal build

    ᓚᘏᗢ Building...

🔨 Building site...
   ↪ /path/to/site

✨ Generated pages:
   ├─ Regular pages:    45
   └─ Total:            45 ✓

✨ Built 45 pages in 2.3s
```

**Gaps:**
- No progress indication during 2.3s wait
- If build is slow (10s+), feels frozen
- No sense of what's happening

**Ideal Experience:**
```bash
bengal build

    ᓚᘏᗢ  Building your site...

[⠋] Discovering content... (0.2s)
[✓] Found 45 pages
[⠋] Rendering pages... 23/45 (2.1s)
[✓] All pages rendered
[⠋] Processing assets... (0.4s)

✨ Built 45 pages in 2.7s

📂 Ready: public/
💡 Preview: bengal serve
```

**Enhancements Needed:**
- Live progress indicators (spinners, counters)
- Clear next steps
- Celebration on success (but not annoying)
- Errors front-and-center with clear fixes

---

### 🎨 Persona 2: Theme Developer
**Primary Goal:** "Show me what broke and where"

**Current Experience:**
- Good: Template errors are shown with context
- Good: Build stats show timing breakdown
- Gap: No live feedback during template compilation
- Gap: Can't see which templates are being processed
- Gap: No "hot paths" highlighting (slowest templates)

**Ideal Experience:**
```bash
bengal build --profile theme-dev

    ᓚᘏᗢ  Building with template debugging...

[⠋] Validating templates...
    ├─ base.html ✓
    ├─ post.html ⚠️  unused variable 'author'
    └─ archive.html ✓

[⠋] Rendering (parallel)...
    ├─ base.html     → 12 pages (0.3s)
    ├─ post.html     → 8 pages  (0.5s) ⚠️  slow
    └─ archive.html  → 2 pages  (0.1s)

⚠️  Rendering Issues (1):
   • post.html is slow (avg 62ms/page)
     💡 Consider: caching expensive filters

📊 Template Coverage:
   ✓ All sections have templates
   ✓ All pages rendered successfully
```

**Enhancements Needed:**
- Template-specific profiling
- Real-time template validation
- Performance warnings (slow templates)
- Visual template dependency graph
- "Replay" failed renders with context

---

### 🔧 Persona 3: SSG Developer/Contributor
**Primary Goal:** "Give me all the data"

**Current Experience:**
- Good: `--dev` profile shows full phase timing
- Good: Structured logging to file
- Good: Performance profiling support
- Gap: No memory usage visualization
- Gap: Phase timing is text-only, no visual
- Gap: Can't drill into specific phases

**Ideal Experience:**
```bash
bengal build --dev

    ᓚᘏᗢ  Full diagnostics mode

┌─ Build Pipeline ──────────────────────────────────────┐
│                                                        │
│  [████████░░] Discovery      156ms  ↑12MB             │
│  [█░░░░░░░░░] Taxonomies     45ms   ↑3MB              │
│  [██████████] Rendering      890ms  ↑45MB  ⚠️         │
│  [███░░░░░░░] Assets         124ms  ↑8MB              │
│  [██░░░░░░░░] Postprocess    67ms   ↑2MB              │
│                                                        │
│  Total: 1.28s  Peak Memory: 156MB                     │
└────────────────────────────────────────────────────────┘

⚠️  Performance Flags:
   • Rendering phase is 70% of build time
   • 12 pages took >50ms each (see .bengal-build.log)
   • Memory spike during taxonomy generation

📊 Full metrics: .bengal-metrics/2025-10-09-143022.json
🔍 Profile data: profile.stats
```

**Enhancements Needed:**
- Visual progress bars for phases
- Memory usage visualization
- Performance anomaly detection
- Quick links to detailed logs
- Exportable metrics for analysis

---

### 🤖 Persona 4: CI/CD Pipeline
**Primary Goal:** "Machine-readable, fast, deterministic"

**Current Experience:**
- Good: Exit codes work correctly
- Good: `--quiet` flag exists
- Gap: No `--json` output mode
- Gap: No machine-readable progress
- Gap: No build cache status reporting

**Ideal Experience:**
```bash
# JSON output mode
bengal build --format json --quiet
{
  "status": "success",
  "duration_ms": 2340,
  "pages_built": 45,
  "assets_processed": 23,
  "warnings": [],
  "errors": [],
  "cache": {
    "hit_rate": 0.85,
    "pages_cached": 38,
    "pages_rebuilt": 7
  }
}

# Or progressive output for live logs
bengal build --format ndjson
{"event":"start","timestamp":"2025-10-09T14:30:22Z"}
{"event":"phase","name":"discovery","duration_ms":156}
{"event":"phase","name":"rendering","duration_ms":890}
{"event":"complete","duration_ms":2340,"pages":45}
```

**Enhancements Needed:**
- JSON/NDJSON output formats
- TAP (Test Anything Protocol) support
- GitHub Actions annotations
- Build artifact checksums
- Deterministic output (no timestamps in --ci mode)

---

### 🆕 Persona 5: First-Time User
**Primary Goal:** "Help me get started without RTFM"

**Current Experience:**
```bash
bengal new site myblog
# Works but basic
```

**Ideal Experience:**
```bash
bengal new site myblog

    ᓚᘏᗢ  Let's create your site!

? What kind of site? (Use arrow keys)
  ❯ Blog (personal writing, posts, tags)
    Documentation (API docs, guides, search)
    Portfolio (projects, case studies)
    Marketing (landing pages, SEO)
    Minimal (start from scratch)

? Choose a theme:
  ❯ default (clean, responsive, ready to go)
    minimal (barebones, bring your own styles)
    docs-pro (sidebar nav, search, dark mode)

? Content structure:
  ❯ Standard (posts, pages, about)
    Custom (I'll set it up myself)

Creating myblog/...
✓ Structure created
✓ Sample content added
✓ Config generated

🎉 You're all set!

Next steps:
  cd myblog
  bengal serve    # Start dev server
  
📚 Learn more: https://bengal.dev/docs/
```

**Enhancements Needed:**
- Interactive initialization wizard
- Template selection
- Example content generation
- Guided first run
- Helpful error messages with docs links

---

## Competitive Analysis: What Makes SSGs Memorable?

### Hugo
**Strengths:**
- FAST (brags about build speed)
- Simple, clean CLI
- Good error messages

**Weaknesses:**
- Bland output (just text)
- No animation
- No interactivity

### Eleventy
**Strengths:**
- Friendly tone
- Good docs
- Plugin ecosystem

**Weaknesses:**
- CLI is basic
- JavaScript stack (not applicable to Bengal)

### Jekyll
**Strengths:**
- Mature ecosystem
- Well-documented

**Weaknesses:**
- Slow
- Boring CLI
- Poor error messages

### Astro
**Strengths:**
- Modern, polished
- Good DX overall
- Nice dev server UI

**Weaknesses:**
- Web-based (different niche)

### **Opportunity:** None of these have truly *delightful* CLIs. There's white space here.

---

## Technical Implementation Strategy

### Phase 1: Foundation (Low-Hanging Fruit)

**Goal:** Add animation and better feedback with minimal refactoring

1. **Add `rich` Library**
   ```toml
   # requirements.txt
   rich>=13.7.0
   ```

2. **Replace Static Indicators with Spinners**
   ```python
   # Before
   show_building_indicator("Building site")
   stats = site.build()
   
   # After
   from rich.console import Console
   from rich.status import Status
   
   console = Console()
   with console.status("[bold green]Building site...") as status:
       stats = site.build()
   ```

3. **Add Progress Bars for Multi-Step Operations**
   ```python
   from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
   
   with Progress(
       SpinnerColumn(),
       TextColumn("[progress.description]{task.description}"),
       BarColumn(),
       TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
   ) as progress:
       task = progress.add_task("[cyan]Rendering pages...", total=len(pages))
       for page in pages:
           render_page(page)
           progress.update(task, advance=1)
   ```

4. **Improve Error Display with Syntax Highlighting**
   ```python
   from rich.syntax import Syntax
   from rich.panel import Panel
   
   # Show code context with highlighting
   syntax = Syntax(code, "jinja2", line_numbers=True, line_range=(10, 20))
   console.print(Panel(syntax, title="[red]Template Error", border_style="red"))
   ```

**Effort:** 2-3 days  
**Impact:** High visual polish, immediate user delight

---

### Phase 2: Live Updates & Intelligence

**Goal:** Real-time feedback and smarter behavior

1. **Live Build Dashboard**
   ```python
   from rich.live import Live
   from rich.table import Table
   from rich.layout import Layout
   
   # Create live-updating display
   layout = Layout()
   layout.split_column(
       Layout(name="header"),
       Layout(name="progress"),
       Layout(name="stats")
   )
   
   with Live(layout, refresh_per_second=4):
       # Update layout as build progresses
       ...
   ```

2. **Smart Command Suggestions**
   ```python
   # typo: "begnal build" → "bengal build"
   # missing command → suggest similar
   from difflib import get_close_matches
   
   if command_not_found:
       matches = get_close_matches(typed_command, valid_commands)
       if matches:
           click.echo(f"Unknown command. Did you mean '{matches[0]}'?")
   ```

3. **Context-Aware Defaults**
   ```python
   # Detect CI environment
   import os
   
   if os.getenv('CI'):
       # Auto-enable --quiet, --strict, disable colors
       default_profile = BuildProfile.WRITER
       use_color = False
   ```

4. **Terminal Capability Detection**
   ```python
   from rich.console import Console
   
   console = Console()
   if not console.is_terminal or not console.color_system:
       # Fallback to simple output
       use_rich_output = False
   ```

**Effort:** 1-2 weeks  
**Impact:** Professional polish, adaptive UX

---

### Phase 3: Interactive Features

**Goal:** Conversational CLI with autocomplete and prompts

1. **Interactive Project Init**
   ```python
   import questionary
   
   site_type = questionary.select(
       "What kind of site?",
       choices=["Blog", "Docs", "Portfolio", "Marketing"]
   ).ask()
   
   theme = questionary.select(
       "Choose a theme:",
       choices=get_available_themes()
   ).ask()
   ```

2. **Shell Completions**
   ```python
   # Add to cli.py
   import click_completion
   
   @main.command()
   def install_completion():
       """Install shell completion for bengal commands."""
       shell = click_completion.install()
       click.echo(f"Completion installed for {shell}")
   ```

3. **Interactive Health Check Review**
   ```python
   # After build, if warnings exist
   if stats.warnings:
       if questionary.confirm("View detailed warnings?").ask():
           show_detailed_warnings(stats)
       
       if questionary.confirm("Fix broken links automatically?").ask():
           fix_broken_links(stats)
   ```

**Effort:** 2-3 weeks  
**Impact:** Makes Bengal feel "smart" and helpful

---

### Phase 4: Advanced Analytics & Visualization

**Goal:** Deep insights and visual data exploration

1. **Build Performance Graphs**
   ```python
   from rich.console import Console
   from rich.bar_chart import BarChart  # if available
   
   # Show build time trends
   # Show memory usage over time
   # Show cache hit rates
   ```

2. **Template Performance Heatmap**
   ```python
   # Visual representation of which templates are slow
   # Identify hot paths in template rendering
   ```

3. **Knowledge Graph Visualization in CLI**
   ```python
   # Use Unicode box drawing to show page relationships
   # Tree view of site structure
   # Dependency visualization
   ```

4. **Export and Analysis Tools**
   ```python
   bengal perf export --format grafana
   bengal perf export --format prometheus
   bengal analyze --slowest-pages 10
   bengal analyze --template-coverage
   ```

**Effort:** 3-4 weeks  
**Impact:** Power-user features, debugging superpowers

---

## Specific Enhancement Proposals

### 1. Animated Build Progress

**Current:**
```
🔨 Building site...
   ↪ /path/to/site

✨ Generated pages:
```

**Proposed:**
```
    ᓚᘏᗢ  Building your site...

┌─ Build Progress ──────────────────────────────┐
│                                                │
│  [✓] Discovery        45 pages found    0.2s  │
│  [⠋] Rendering        23/45 pages       1.1s  │
│  [⋯] Assets           pending                  │
│  [⋯] Postprocess      pending                  │
│                                                │
│  Elapsed: 1.3s  ETA: ~1.2s                     │
└────────────────────────────────────────────────┘
```

**Implementation:**
```python
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn

def build_with_progress(site):
    with Live(generate_table(), refresh_per_second=4) as live:
        for phase in phases:
            live.update(generate_table())  # Update as we go
            phase.execute()
```

**Effort:** 2-3 days  
**Impact:** Immediate visual improvement

---

### 2. Dev Server Live Dashboard

**Current:**
```
╭──────────────────────────────────────────────────────────────╮
│ 🚀 Bengal Dev Server                                         │
│   ➜  Local:   http://localhost:5173/                         │
│   ⚠  File watching enabled (auto-reload on changes)          │
│   Press Ctrl+C to stop                                       │
╰──────────────────────────────────────────────────────────────╯

  TIME     │ METHOD │ STATUS │ PATH
  ─────────┼────────┼────────┼─────────────────
```

**Proposed:**
```
    ᓚᘏᗢ  Bengal Dev Server

┌─ Server ───────────────────────────────────────┐
│  URL:     http://localhost:5173/               │
│  Status:  ● Running                            │
│  Uptime:  12m 34s                              │
└────────────────────────────────────────────────┘

┌─ Activity ─────────────────────────────────────┐
│  14:32:15  GET   200  /                        │
│  14:32:16  GET   200  /css/main.css            │
│  14:32:45  ⟳ File changed: content/post.md    │
│            ⠋ Rebuilding... (23/45 pages)      │
│  14:32:47  ✓ Rebuild complete (1.2s)          │
│            ⟳ Browser reloaded                 │
└────────────────────────────────────────────────┘

Press 'q' to quit, 'r' to force rebuild, 'o' to open browser
```

**Implementation:**
```python
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

def run_dev_server_with_dashboard():
    layout = Layout()
    layout.split_column(
        Layout(name="server_info"),
        Layout(name="activity_log")
    )
    
    with Live(layout, refresh_per_second=2) as live:
        # Update as events happen
        ...
```

**Effort:** 3-4 days  
**Impact:** Makes dev server feel alive and responsive

---

### 3. Intelligent Error Messages

**Current:**
```
❌ Template Error: undefined variable 'author'
   File: post.html, Line: 23
```

**Proposed:**
```
❌ Template Error in post.html

   20 │ <article class="post">
   21 │   <h1>{{ title }}</h1>
   22 │   <time>{{ date }}</time>
   23 │   <p class="author">{{ author }}</p>
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   24 │ </article>

   Variable 'author' is not defined

   💡 Suggestions:
      • Add 'author' to page frontmatter
      • Use {{ page.author | default('Anonymous') }}
      • Check if you meant: 'author_name', 'page.author'

   📚 Learn more: https://bengal.dev/docs/templates#variables
```

**Implementation:**
```python
from rich.syntax import Syntax
from rich.panel import Panel
from rich.console import Console
from difflib import get_close_matches

def display_template_error_rich(error):
    # Get code context
    code_lines = get_source_lines(error.filename, error.lineno, context=3)
    syntax = Syntax(code_lines, "jinja2", line_numbers=True, 
                   highlight_lines=[error.lineno])
    
    # Get suggestions
    suggestions = []
    if error.type == 'undefined_variable':
        similar = get_close_matches(error.var_name, available_vars)
        for var in similar:
            suggestions.append(f"Check if you meant: '{var}'")
    
    # Display
    console.print(Panel(syntax, title=f"[red]{error.message}", border_style="red"))
    if suggestions:
        console.print("\n💡 Suggestions:")
        for s in suggestions:
            console.print(f"   • {s}")
```

**Effort:** 4-5 days  
**Impact:** Dramatically reduces debugging time

---

### 4. Build Time Optimization Hints

**Proposed Feature:**
```
    ᓚᘏᗢ  Build complete in 12.4s

📊 Performance Analysis:

   ⚠️  Your build is slower than expected for 45 pages
   
   Slow Operations:
      • Rendering: 8.2s (66% of total)
        ├─ post.html: avg 145ms/page (expected: <50ms)
        └─ Heavy template filters detected
   
   💡 Recommendations:
      1. Enable --parallel (could save ~4s)
      2. Enable --incremental for dev (10x faster rebuilds)
      3. Consider caching expensive template operations
   
   🎓 Learn about optimization:
      https://bengal.dev/docs/performance/
```

**Implementation:**
```python
def analyze_build_performance(stats):
    hints = []
    
    # Slow build detection
    pages_per_sec = stats.total_pages / (stats.build_time_ms / 1000)
    if pages_per_sec < 20:  # Arbitrary threshold
        hints.append("Build is slower than expected")
        
        # Analyze why
        if stats.rendering_time_ms > stats.build_time_ms * 0.5:
            hints.append("Rendering is the bottleneck")
            
            # Check for common issues
            if not stats.parallel:
                hints.append("Enable --parallel")
            
            # Template-specific analysis
            slow_templates = find_slow_templates(stats)
            if slow_templates:
                hints.append(f"Templates {slow_templates} are slow")
    
    return hints
```

**Effort:** 5-6 days  
**Impact:** Helps users optimize without deep knowledge

---

### 5. Command Aliases and Shortcuts

**Proposed:**
```bash
# Short commands for common tasks
bengal s           # alias for 'bengal serve'
bengal b           # alias for 'bengal build'
bengal b -i        # alias for 'bengal build --incremental'
bengal deploy      # new command: build + deploy

# Smart defaults based on context
bengal build       # in dev → --incremental
bengal build       # in CI → --strict --quiet

# Saved profiles
bengal build --save-profile fast
bengal build --profile fast  # reuses saved flags
```

**Implementation:**
```python
# Add to cli.py
@main.command(name='s')
def serve_alias(*args, **kwargs):
    """Alias for 'serve' command."""
    return serve(*args, **kwargs)

# Context detection
import os

def get_smart_defaults():
    if os.getenv('CI'):
        return {'strict': True, 'quiet': True}
    elif Path('.git').exists():
        return {'incremental': True}
    return {}
```

**Effort:** 2-3 days  
**Impact:** Faster workflows for power users

---

### 6. Health Check Interactive Review

**Proposed:**
```bash
bengal build --dev

    ᓚᘏᗢ  Build complete with 3 warnings

🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Configuration        passed
✓ Output Structure     passed
⚠ Link Validation      3 broken links
✓ Performance          passed
⚠ SEO                  2 issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

? Review warnings? (Y/n) y

⚠ Link Validation (3 broken links):

  1. content/post/intro.md
     → /about → 404 Not Found
     💡 Did you mean /about-us?
     
  2. content/post/tutorial.md
     → https://example.com/api → Timeout
     💡 External link may be down
     
? Fix broken internal links automatically? (Y/n) y

✓ Fixed 1 link (intro.md)
⚠ 2 external links require manual review

💾 Saved report: .bengal-health-report.json
```

**Implementation:**
```python
import questionary

def interactive_health_review(report):
    if not report.has_issues():
        return
    
    # Ask if user wants details
    if questionary.confirm("Review warnings?").ask():
        for validator_report in report.validator_reports:
            if validator_report.has_issues():
                display_validator_results(validator_report)
                
                # Offer fixes
                if validator_report.validator_name == "link_validation":
                    if questionary.confirm("Fix broken internal links?").ask():
                        fixed = auto_fix_links(validator_report)
                        console.print(f"✓ Fixed {fixed} links")
```

**Effort:** 3-4 days  
**Impact:** Makes health checks actionable, not just informative

---

## Library Recommendations

### Core Libraries

1. **`rich`** - Foundation for beautiful output
   - Progress bars, spinners, tables, panels
   - Live updating displays
   - Syntax highlighting
   - Tree views
   - **Effort:** Already using `click`, `rich` integrates well

2. **`questionary`** - Interactive prompts
   - Select menus
   - Confirmation dialogs
   - Autocomplete inputs
   - **Alternative:** `prompt_toolkit` (more powerful but heavier)

3. **`click-completion`** - Shell completions
   - Bash, Zsh, Fish support
   - Auto-generates from Click commands

4. **`yaspin`** or **`halo`** - Spinners (if not using rich)
   - Lightweight alternative
   - Many spinner styles

### Optional Enhancements

5. **`colorama`** - Windows color support
   - Already likely pulled in by `click`
   - Ensures colors work on Windows

6. **`py-cpuinfo`** - System detection
   - Detect CPU cores for parallel builds
   - Show system info in `--dev` mode

7. **`psutil`** - Already using for memory tracking
   - Can expand to show disk usage
   - Network usage for remote builds

---

## Implementation Roadmap

### Sprint 1: Quick Wins (Week 1)
**Goal:** Add animation and better feedback

- [ ] Add `rich` dependency
- [ ] Replace `show_building_indicator` with spinners
- [ ] Add progress bar to page rendering
- [ ] Enhance error display with syntax highlighting
- [ ] Add build progress table (live updating)

**Deliverable:** Builds feel alive, not static

---

### Sprint 2: Intelligence (Week 2)
**Goal:** Smarter, context-aware CLI

- [ ] Terminal capability detection
- [ ] CI environment detection and auto-config
- [ ] Command typo suggestions
- [ ] Performance hints after build
- [ ] Save/load build profiles

**Deliverable:** CLI adapts to user context

---

### Sprint 3: Interactivity (Week 3-4)
**Goal:** Make CLI conversational

- [ ] Add `questionary` dependency
- [ ] Interactive `bengal new site` wizard
- [ ] Interactive health check review
- [ ] Confirmation dialogs for destructive operations
- [ ] Shell completions

**Deliverable:** CLI guides users, doesn't just execute commands

---

### Sprint 4: Dev Server Polish (Week 5)
**Goal:** Make dev server experience delightful

- [ ] Live dashboard with stats
- [ ] Keyboard shortcuts (r=rebuild, o=open browser)
- [ ] Better file change feedback
- [ ] Build progress during auto-rebuild
- [ ] Request logging in dashboard

**Deliverable:** Dev server is a pleasure to use

---

### Sprint 5: Advanced Features (Week 6+)
**Goal:** Power-user capabilities

- [ ] JSON output mode for CI
- [ ] NDJSON streaming for live logs
- [ ] Performance visualization
- [ ] Template profiling and heatmaps
- [ ] Export metrics (Grafana, Prometheus)

**Deliverable:** Professional-grade observability

---

## Success Metrics

### Quantitative
- Build feedback latency: <100ms for first visual indicator
- Spinner/progress visible within 200ms of command start
- Error time-to-understanding: <30s for common errors
- New user time-to-first-build: <2 minutes

### Qualitative
- User feedback: "Bengal's CLI is a joy to use"
- GitHub stars mention: "Love the CLI experience"
- Reduced support questions about "is it working?"
- Positive comparisons to other SSGs' CLIs

---

## Risks & Mitigations

### Risk 1: Too Much Output
**Concern:** Animated CLI could be overwhelming  
**Mitigation:** 
- Respect `--quiet` flag strictly
- Profile-based output (writer vs dev)
- Terminal detection (disable in dumb terminals)

### Risk 2: Performance Overhead
**Concern:** Rich output could slow down builds  
**Mitigation:**
- Render updates at max 4 FPS (every 250ms)
- Disable in CI by default
- Measure overhead (should be <1% of build time)

### Risk 3: Windows Compatibility
**Concern:** Unicode/ANSI not working on Windows  
**Mitigation:**
- Use `colorama` for Windows ANSI support
- Fallback to ASCII-only mode if needed
- Test on Windows in CI

### Risk 4: Dependency Bloat
**Concern:** Adding libraries increases install size  
**Mitigation:**
- `rich` is 600KB, acceptable for benefits
- Make `questionary` optional (only for interactive mode)
- Document minimal install option

---

## Competitive Differentiation

### Why This Matters

Most SSGs treat CLI as an afterthought. By making Bengal's CLI **exceptional**, we:

1. **Create memorable first impressions** - Users immediately notice
2. **Reduce support burden** - Better feedback = fewer questions
3. **Increase productivity** - Faster feedback loops
4. **Enable word-of-mouth** - "You have to try Bengal's CLI"
5. **Attract contributors** - Polished projects attract talent

### The Bengal CLI "Signature"

What makes Bengal's CLI distinctive:

1. **🐯 Personality** - The cat mascot, friendly tone
2. **🎯 Persona-aware** - Writer/Theme-Dev/Developer profiles
3. **⚡ Performance-focused** - Shows speed, suggests optimizations
4. **🎨 Visual polish** - Animation, color, structure
5. **🧠 Intelligent** - Suggestions, auto-fixes, context-aware

---

## Appendix: Example Implementations

### A1: Rich Progress Bar Integration

```python
# bengal/orchestration/render.py
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn
)
from rich.console import Console

console = Console()

def render_pages_with_progress(pages, parallel=True):
    """Render pages with live progress bar."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total} pages"),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        transient=True  # Remove after completion
    ) as progress:
        
        render_task = progress.add_task(
            "[cyan]Rendering pages...",
            total=len(pages)
        )
        
        if parallel:
            # Parallel rendering with progress updates
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(render_page, page): page 
                    for page in pages
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    progress.update(render_task, advance=1)
        else:
            # Sequential rendering
            for page in pages:
                render_page(page)
                progress.update(render_task, advance=1)
```

### A2: Interactive Project Setup

```python
# bengal/cli.py
import questionary
from questionary import Style

# Custom Bengal style
bengal_style = Style([
    ('qmark', 'fg:#f39c12 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#2ecc71 bold'),
    ('pointer', 'fg:#f39c12 bold'),
    ('highlighted', 'fg:#f39c12 bold'),
    ('selected', 'fg:#2ecc71'),
])

@new.command()
def site_interactive():
    """Create a new site with interactive wizard."""
    
    console.print("\n    ᓚᘏᗢ  [bold]Let's create your Bengal site![/bold]\n")
    
    # Project name
    name = questionary.text(
        "Project name:",
        validate=lambda x: len(x) > 0,
        style=bengal_style
    ).ask()
    
    # Site type
    site_type = questionary.select(
        "What kind of site?",
        choices=[
            "Blog (personal writing, posts, tags)",
            "Documentation (API docs, guides, search)",
            "Portfolio (projects, case studies)",
            "Marketing (landing pages, SEO)",
            "Minimal (start from scratch)"
        ],
        style=bengal_style
    ).ask()
    
    # Theme
    theme = questionary.select(
        "Choose a theme:",
        choices=[
            "default (clean, responsive, ready to go)",
            "minimal (barebones, bring your own styles)",
            "docs-pro (sidebar nav, search, dark mode)"
        ],
        style=bengal_style
    ).ask()
    
    # Content structure
    include_samples = questionary.confirm(
        "Include sample content?",
        default=True,
        style=bengal_style
    ).ask()
    
    # Create the site
    with console.status("[bold green]Creating your site...") as status:
        create_site_structure(name, site_type, theme, include_samples)
        time.sleep(0.5)  # Small delay for UX
    
    # Success message
    console.print(f"\n[green bold]✓[/green bold] Site created: [cyan]{name}/[/cyan]\n")
    console.print("[yellow]Next steps:[/yellow]")
    console.print(f"  [dim]$[/dim] cd {name}")
    console.print(f"  [dim]$[/dim] bengal serve\n")
```

### A3: Live Build Dashboard

```python
# bengal/orchestration/build.py
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

def build_with_dashboard(self):
    """Execute build with live dashboard."""
    
    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="progress", size=10),
        Layout(name="stats", size=5)
    )
    
    def make_header():
        return Panel(
            "[bold]ᓚᘏᗢ  Building your site[/bold]",
            style="cyan"
        )
    
    def make_progress_table(phases, current_phase):
        table = Table(show_header=False, box=None)
        table.add_column("Status", width=3)
        table.add_column("Phase", width=20)
        table.add_column("Details", width=30)
        table.add_column("Time", width=10, justify="right")
        
        for phase_name, phase_data in phases.items():
            if phase_data['status'] == 'complete':
                status = "[green]✓[/green]"
            elif phase_data['status'] == 'running':
                status = "[yellow]⠋[/yellow]"
            else:
                status = "[dim]⋯[/dim]"
            
            table.add_row(
                status,
                phase_name.title(),
                phase_data.get('details', ''),
                phase_data.get('time', '')
            )
        
        return Panel(table, title="Build Progress", border_style="blue")
    
    def make_stats(stats):
        text = Text()
        text.append(f"Pages: {stats.get('pages', 0)}\n")
        text.append(f"Assets: {stats.get('assets', 0)}\n")
        text.append(f"Elapsed: {stats.get('elapsed', '0.0s')}")
        return Panel(text, title="Statistics", border_style="green")
    
    # Track phases
    phases = {
        'discovery': {'status': 'pending', 'details': '', 'time': ''},
        'taxonomies': {'status': 'pending', 'details': '', 'time': ''},
        'rendering': {'status': 'pending', 'details': '', 'time': ''},
        'assets': {'status': 'pending', 'details': '', 'time': ''},
        'postprocess': {'status': 'pending', 'details': '', 'time': ''}
    }
    
    current_stats = {'pages': 0, 'assets': 0, 'elapsed': '0.0s'}
    
    # Run build with live updates
    with Live(layout, refresh_per_second=4, screen=False) as live:
        start_time = time.time()
        
        def update_display():
            layout["header"].update(make_header())
            layout["progress"].update(make_progress_table(phases, None))
            layout["stats"].update(make_stats(current_stats))
        
        # Discovery phase
        phases['discovery']['status'] = 'running'
        update_display()
        
        phase_start = time.time()
        self.content.discover()
        phases['discovery']['status'] = 'complete'
        phases['discovery']['time'] = f"{(time.time() - phase_start):.1f}s"
        phases['discovery']['details'] = f"{len(self.site.pages)} pages"
        current_stats['pages'] = len(self.site.pages)
        update_display()
        
        # ... continue for each phase ...
        
        # Rendering phase with sub-progress
        phases['rendering']['status'] = 'running'
        for i, page in enumerate(self.site.pages):
            render_page(page)
            phases['rendering']['details'] = f"{i+1}/{len(self.site.pages)} pages"
            current_stats['elapsed'] = f"{(time.time() - start_time):.1f}s"
            if i % 5 == 0:  # Update every 5 pages (not too often)
                update_display()
        
        phases['rendering']['status'] = 'complete'
        phases['rendering']['time'] = f"{(time.time() - phase_start):.1f}s"
        update_display()
        
        # Final update
        current_stats['elapsed'] = f"{(time.time() - start_time):.1f}s"
        update_display()
```

### A4: Smart Error Context

```python
# bengal/rendering/errors.py
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from difflib import get_close_matches
import re

console = Console()

def display_smart_error(error, context):
    """Display error with intelligent suggestions."""
    
    # Extract code context (3 lines before, 3 after)
    source_lines = get_source_lines(
        error.filename,
        error.lineno,
        before=3,
        after=3
    )
    
    # Syntax highlight with error line marked
    syntax = Syntax(
        source_lines,
        "jinja2",
        line_numbers=True,
        line_range=(error.lineno - 3, error.lineno + 3),
        highlight_lines=[error.lineno],
        theme="monokai"
    )
    
    # Display code
    console.print()
    console.print(Panel(
        syntax,
        title=f"[red bold]Template Error in {Path(error.filename).name}",
        subtitle=f"Line {error.lineno}",
        border_style="red"
    ))
    
    # Error message
    console.print(f"\n[red bold]Error:[/red bold] {error.message}\n")
    
    # Generate smart suggestions
    suggestions = generate_suggestions(error, context)
    
    if suggestions:
        console.print("[yellow bold]💡 Suggestions:[/yellow bold]\n")
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"   {i}. {suggestion}")
        console.print()
    
    # Documentation link
    if error.error_type in ERROR_DOC_LINKS:
        doc_url = ERROR_DOC_LINKS[error.error_type]
        console.print(f"[dim]📚 Learn more: {doc_url}[/dim]\n")

def generate_suggestions(error, context):
    """Generate context-aware suggestions for errors."""
    suggestions = []
    
    if error.error_type == 'undefined_variable':
        var_name = error.var_name
        available_vars = context.get('available_vars', [])
        
        # Check for similar variable names
        similar = get_close_matches(var_name, available_vars, n=3, cutoff=0.6)
        if similar:
            suggestions.append(f"Did you mean: {', '.join(similar)}?")
        
        # Check if it's a common typo
        common_typos = {
            'titel': 'title',
            'dat': 'date',
            'autor': 'author',
            'sumary': 'summary'
        }
        if var_name in common_typos:
            suggestions.append(f"Common typo: try '{common_typos[var_name]}'")
        
        # Suggest default filter
        suggestions.append(f"Use a default: {{{{ {var_name} | default('value') }}}}")
        
        # Suggest adding to frontmatter
        if context.get('is_page_template'):
            suggestions.append(f"Add '{var_name}' to page frontmatter")
    
    elif error.error_type == 'template_not_found':
        template_name = error.template_name
        available_templates = context.get('available_templates', [])
        
        similar = get_close_matches(template_name, available_templates, n=3)
        if similar:
            suggestions.append(f"Did you mean: {', '.join(similar)}?")
        
        suggestions.append(f"Create template: templates/{template_name}")
    
    elif error.error_type == 'filter_not_found':
        filter_name = error.filter_name
        available_filters = context.get('available_filters', [])
        
        similar = get_close_matches(filter_name, available_filters, n=3)
        if similar:
            suggestions.append(f"Did you mean: {', '.join(similar)}?")
        
        suggestions.append("Check if filter is registered in template engine")
    
    return suggestions
```

---

## Conclusion

Bengal has an excellent foundation for CLI excellence. The profile system is brilliant, the error handling is good, and there's clear attention to UX. 

**The opportunity:** Transform Bengal from "good CLI" to "the SSG with the amazing CLI that everyone talks about."

**The path forward:**
1. **Quick wins** (Sprint 1): Add `rich`, spinners, progress bars → immediate visual upgrade
2. **Intelligence** (Sprint 2): Context detection, smart suggestions → feels smarter
3. **Interactivity** (Sprint 3): Conversational prompts → guides users
4. **Polish** (Sprint 4-5): Dev server dashboard, advanced analytics → professional-grade

**Investment:** 6-8 weeks of focused work  
**Payoff:** Significant competitive differentiation and user delight

The technical implementation is straightforward (libraries exist, patterns are known). The challenge is maintaining the **persona-aware philosophy** while adding richness. Always ask: "Does this help writers? Theme devs? Contributors?"

Done right, Bengal's CLI becomes its signature—the thing that makes it memorable and recommendable.

---

**Next Steps:**
1. Review this analysis with the team
2. Prioritize features based on user feedback
3. Start with Sprint 1 (quick wins)
4. Gather user feedback after each sprint
5. Iterate based on real usage

Let's make Bengal's CLI **fierce** 🐯

