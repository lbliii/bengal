# Rich CLI Features - Usage Guide

## Overview

Bengal now uses the Rich library extensively to provide beautiful terminal output with syntax highlighting, better error messages, and enhanced visualizations.

## New Features

### 1. Beautiful Error Tracebacks

**What it does:** Automatically shows syntax-highlighted tracebacks with local variables when errors occur.

**How to use:** It's automatic! Just run any Bengal command. If an error occurs, you'll see:
- Syntax-highlighted Python code
- Local variable values at each frame
- Clean, readable stack traces
- Automatic suppression of internal Click frames

**Example:**
```bash
bengal build
# If an error occurs, you'll see a beautiful traceback instead of plain text
```

**CI/CD:** Automatically disabled in CI environments (detects `CI` environment variable).

---

### 2. Tree Visualization for Site Structure

**What it does:** Shows your site structure as a beautiful hierarchical tree with link statistics.

**How to use:**
```bash
# Basic graph stats (existing)
bengal graph

# NEW: Tree visualization
bengal graph --tree

# Combine with stats
bengal graph --tree --stats
```

**Output example:**
```
📁 Site Structure
├── 📁 blog (25 pages)
│   ├── 🏠 _index.md (5↓ 3↑)
│   ├── 📝 post-1.md (2↓ 5↑)
│   ├── 📝 post-2.md (1↓ 4↑)
│   └── ... and 22 more pages
├── 📁 docs (50 pages)
│   ├── 🏠 _index.md (10↓ 2↑)
│   ├── 📄 getting-started.md (15↓ 8↑)
│   └── ... and 48 more pages
└── 📁 Root (3 pages)
    ├── 🏠 index.md (20↓ 5↑)
    └── 📄 about.md (3↓ 2↑)
```

**Legend:**
- 🏠 = Index/home page
- 📝 = Blog post
- 📄 = Regular page
- (5↓ 3↑) = 5 incoming links, 3 outgoing links

---

### 3. Animated Status Spinners

**What it does:** Shows animated spinners during long-running operations instead of static messages.

**Affected commands:**
```bash
bengal graph       # Spinner during discovery and analysis
bengal pagerank    # Spinner during computation
bengal communities # Spinner during detection
bengal bridges     # Spinner during path analysis
bengal suggest     # Spinner during link analysis
```

**What you see:**
```
⠋ Discovering site content...
⠙ Building knowledge graph from 150 pages...
⠹ Computing PageRank (damping=0.85)...
```

---

### 4. Enhanced Logger Output

**What changed:** Logger now uses Rich console markup instead of ANSI codes.

**Benefits:**
- Cleaner, more consistent colors
- Better terminal compatibility
- Easier to read phase markers
- Automatic fallback for non-color terminals

**Example output:**
```
16:47:58 ● [discovery] phase_start items=100
16:47:58   ● [discovery] found_pages count=100
16:47:58 ● [discovery] phase_complete (145.3ms)
```

**For developers:**
```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing page", path="/blog/post.md")
logger.warning("Slow render", duration_ms=500)

# Phase tracking
with logger.phase("custom_phase", count=50):
    # Your code here
    logger.info("Working...")
```

---

### 5. Pretty Config Display

**What it does:** Displays configuration with syntax highlighting and proper formatting.

**How to use (in Python code):**
```python
from bengal.config.loader import pretty_print_config

# Display config with title
pretty_print_config(site.config, title="Site Configuration")

# Display any dict
pretty_print_config(debug_data, title="Debug Info")
```

**Output:**
```
Site Configuration

{
│   'site': {
│   │   'title': 'My Site',
│   │   'baseurl': 'https://example.com'
│   },
│   'build': {
│   │   'parallel': True,
│   │   'output_dir': 'public'
│   }
}
```

---

### 6. Rich Interactive Prompts

**What changed:** Confirmation prompts now use Rich styling for consistency.

**Affected commands:**
```bash
bengal clean      # Confirmation before deleting files
bengal cleanup    # Confirmation before killing processes
```

**What you see:**
```
⚠️  Delete all files?
Proceed (y/n): 
```

Instead of plain Click prompts, you get styled prompts that match the rest of the CLI.

---

### 7. Syntax-Highlighted Template Errors

**What it does:** Template errors show code context with Jinja2 syntax highlighting.

**When it triggers:** Automatically when template errors occur during build.

**Example output:**
```
╭────────────────────── Template Syntax Error in base.html:42 ──────────────────────╮
│   40 │ {% for post in posts %}                                                     │
│   41 │   <article>                                                                 │
│ → 42 │     <h2>{{ post.titel }}</h2>  <!-- typo here -->                          │
│   43 │   </article>                                                                │
│   44 │ {% endfor %}                                                                │
╰────────────────────────────────────────────────────────────────────────────────────╯

Error: 'Page' object has no attribute 'titel'

💡 Suggestions:
   1. Common typo: try 'title' instead
   2. Use safe access: {{ post.title | default('Untitled') }}
   3. Add 'titel' to page frontmatter

Did you mean:
   • title
   • content
   • metadata
```

---

## Environment Compatibility

### Terminal Detection

Rich features automatically adapt to your environment:

| Environment | Behavior |
|------------|----------|
| **macOS Terminal** | ✅ Full Rich features |
| **iTerm2** | ✅ Full Rich features |
| **Linux Terminal** | ✅ Full Rich features |
| **Windows Terminal** | ✅ Full Rich features |
| **CI/CD (GitHub Actions, etc.)** | ⚠️ Automatic fallback to plain text |
| **Piped output (`bengal build > log.txt`)** | ⚠️ Automatic fallback to plain text |
| **`NO_COLOR=1`** | ⚠️ Colors disabled |
| **`TERM=dumb`** | ⚠️ Automatic fallback |

### Force Disable Rich

If you want to disable Rich features manually:

```bash
# Set NO_COLOR environment variable
NO_COLOR=1 bengal build

# Or set CI variable
CI=1 bengal build
```

### Verify Rich Status

Check if Rich features are enabled:

```python
from bengal.utils.rich_console import should_use_rich, detect_environment

print(f"Rich enabled: {should_use_rich()}")
print(f"Environment: {detect_environment()}")
```

---

## Developer Tips

### Using Rich in Your Code

If you're extending Bengal, you can use Rich features:

```python
from bengal.utils.rich_console import get_console, should_use_rich
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax

console = get_console()

# Check if Rich should be used
if should_use_rich():
    # Use Rich features
    console.print("[bold green]Success![/bold green]")
    console.print(Panel("Important message", border_style="yellow"))
else:
    # Fallback to plain print
    print("Success!")
    print("Important message")
```

### Adding Status Spinners

To add spinners to your commands:

```python
from bengal.utils.rich_console import get_console, should_use_rich
from rich.status import Status

if should_use_rich():
    console = get_console()
    with console.status("[bold green]Processing...", spinner="dots") as status:
        # Long operation
        do_work()
        status.update("[bold green]Finishing up...")
        finish_work()
else:
    # Fallback
    print("Processing...")
    do_work()
    print("Finishing up...")
    finish_work()
```

### Rich Markup Reference

Quick reference for Rich markup in strings:

```python
# Colors
"[red]text[/red]"
"[green]text[/green]"
"[yellow]text[/yellow]"
"[blue]text[/blue]"
"[magenta]text[/magenta]"
"[cyan]text[/cyan]"

# Styles
"[bold]text[/bold]"
"[italic]text[/italic]"
"[underline]text[/underline]"
"[dim]text[/dim]"
"[strike]text[/strike]"

# Combined
"[bold red]text[/bold red]"
"[underline cyan]text[/underline cyan]"

# Links (in supported terminals)
"[link=https://example.com]Click here[/link]"
```

---

## Testing Rich Features

Run the test suite to verify all Rich features are working:

```bash
python tests/manual/test_rich_features.py
```

Expected output:
```
============================================================
TEST SUMMARY
============================================================

Passed: 6/6

✓ All tests passed! Rich CLI enhancements are working correctly.
```

---

## Troubleshooting

### Issue: No colors in output

**Possible causes:**
1. Terminal doesn't support colors
2. `NO_COLOR` environment variable is set
3. Output is being piped
4. Running in CI environment

**Solution:**
- Check `echo $NO_COLOR` (should be empty)
- Verify you're running in an interactive terminal
- Try a different terminal emulator

### Issue: Weird characters in output

**Cause:** Terminal doesn't support Unicode or Rich's box-drawing characters.

**Solution:**
- Use a modern terminal emulator (iTerm2, Windows Terminal, etc.)
- Rich will automatically fall back if it detects issues

### Issue: Spinner not showing

**Cause:** Not running in a TTY (interactive terminal).

**Solution:** This is expected behavior. Spinners automatically fall back to static messages when:
- Output is piped (`bengal build > log.txt`)
- Running in CI
- Not in an interactive terminal

---

## Performance Impact

Rich features have minimal performance impact:

- **Traceback handler:** No overhead unless error occurs
- **Logger:** ~5% slower than ANSI codes (negligible in practice)
- **Tree display:** Only runs when explicitly requested with `--tree`
- **Status spinners:** Minimal CPU usage (updates 4x per second)
- **Syntax highlighting:** Only when displaying errors

All Rich features are lazy-loaded and only import when needed.

---

## Future Enhancements

Potential future additions (not yet implemented):

- **Markdown rendering** for help text
- **Progress bars** for file processing (complementing existing LiveProgress)
- **Rich Layout** for complex multi-panel displays
- **Custom renderables** for specialized output formats
- **More status spinners** in additional commands

---

## Related Documentation

- [Rich Library Docs](https://rich.readthedocs.io/)
- [Bengal CLI Reference](../GETTING_STARTED.md#cli-commands)
- [Bengal Build Profiles](../plan/CLI_IMPLEMENTATION_PLAN.md)
- [Logging System](../ARCHITECTURE.md#logging)

---

**Questions or issues?** Check the [implementation summary](./completed/RICH_CLI_ENHANCEMENTS.md) for technical details.

