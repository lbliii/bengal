# CLI Messaging Design System

## Problem

**672 scattered output calls** across 34 files:
- 191 raw `print()`
- 431 `click.echo()`  
- 50 `console.print()`

Each doing its own formatting, indentation, colors → **total chaos!**

## Solution: Centralized CLI Output Manager

Single source of truth for all CLI messages with:
- ✅ Profile-aware formatting
- ✅ Consistent indentation/spacing
- ✅ Automatic TTY detection
- ✅ Rich/fallback rendering
- ✅ Clean API

## API Design

### Before (scattered, inconsistent)

```python
# In orchestration/build.py
print(f"\n✨ Generated pages:")

# In postprocess/rss.py
print(f"   ├─ RSS feed ✓")

# In build_stats.py
click.echo(click.style(f"\n✨ Built {stats.total_pages} pages", fg='green'))

# In cli.py
console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold cyan]Building...[/bold cyan]")
```

**4 different ways to output, 4 different styles!**

### After (unified, clean)

```python
from bengal.utils.cli_output import get_cli_output

cli = get_cli_output()

# Headers
cli.header("Building your site...")

# Phase status
cli.phase("Discovery", duration_ms=61, details="245 pages")
cli.phase("Rendering", duration_ms=501, details="173 regular + 72 generated")
cli.phase("Assets", duration_ms=34, details="44 files")
cli.phase("Post-process", duration_ms=204)

# Details (indented sub-items)
cli.detail("RSS feed ✓", indent=1, icon="├─")
cli.detail("Sitemap ✓", indent=1, icon="└─")

# Success
cli.success("Built 245 pages in 0.8s")

# Paths
cli.path("/Users/.../public", icon="📂", label="Output")
```

**One clean API, automatic profile-aware formatting!**

## How It Works

### 1. Initialization (once per command)

```python
# In cli.py or build orchestrator
from bengal.utils.cli_output import init_cli_output
from bengal.utils.profile import BuildProfile

cli = init_cli_output(
    profile=BuildProfile.WRITER,  # or THEME_DEV, DEVELOPER
    quiet=False,
    verbose=False
)
```

### 2. Usage Throughout Codebase

```python
# Anywhere in the codebase
from bengal.utils.cli_output import get_cli_output

cli = get_cli_output()
cli.phase("Discovery", duration_ms=61)
```

### 3. Automatic Profile-Aware Formatting

**Writer Profile** (minimal):
```
ᓚᘏᗢ  Building...

✓ Discovery     Done
✓ Rendering     Done
✓ Assets        Done
✓ Post-process  Done

✨ Built 245 pages in 0.8s
```

**Theme-Dev Profile** (balanced):
```
ᓚᘏᗢ  Building your site...

✓ Discovery     61ms (245 pages)
✓ Rendering     501ms (173 regular + 72 generated)
✓ Assets        34ms (44 files)
✓ Post-process  204ms

✨ Built 245 pages in 0.8s
```

**Developer Profile** (detailed):
```
ᓚᘏᗢ  Building your site...

✓ Discovery      61ms (245 pages)
✓ Rendering     501ms (173 regular + 72 generated)
✓ Assets         34ms (44 files)
✓ Post-process  204ms
  ├─ RSS feed ✓
  ├─ Sitemap ✓
  └─ Special pages (404)

✨ Built 245 pages in 0.8s (293.7 pages/sec)

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

## Benefits

### 1. Consistency
All messages follow same indentation, spacing, color rules

### 2. Profile-Awareness Built In
```python
cli.phase("Rendering", duration_ms=501, details="245 pages")

# Writer sees:    ✓ Rendering     Done
# Theme-Dev sees: ✓ Rendering     501ms (245 pages)
# Developer sees: ✓ Rendering     501ms (245 pages)
```

### 3. Clean Codebase
Replace 672 scattered calls with clean API:
```python
# Instead of:
if should_use_rich():
    console.print(f"[green]✓[/green] {name}")
else:
    click.echo(click.style(f"✓ {name}", fg='green'))

# Just:
cli.phase(name)
```

### 4. Easy to Change
Want to change phase formatting? **One place!**
```python
def _format_phase_line(self, parts):
    # Change formatting globally here
```

### 5. TTY Detection Automatic
Automatically uses rich in terminal, plain in CI/logs

### 6. Testable
```python
# Easy to test without actual terminal output
cli = CLIOutput(quiet=True)
cli.phase("Test")  # No output
```

## Migration Strategy

### Phase 1: High-Traffic Paths (Quick Win)
Replace output in:
1. `bengal/orchestration/build.py` (24 prints)
2. `bengal/postprocess/*.py` (RSS, Sitemap, 404)
3. `bengal/config/loader.py` (config messages)

**Impact**: Immediate consistency in build output

### Phase 2: Orchestrators
Replace output in:
1. `bengal/orchestration/render.py`
2. `bengal/orchestration/asset.py`
3. `bengal/orchestration/postprocess.py`

### Phase 3: Utilities
Replace output in:
1. `bengal/utils/build_stats.py`
2. `bengal/utils/build_summary.py`
3. `bengal/server/dev_server.py`

### Phase 4: Edge Cases
Replace remaining scattered prints

## Example Migration

### Before
```python
# bengal/orchestration/build.py
print("\n✨ Generated pages:")
print(f"   ├─ Total: {total}")
print(f"   └─ Regular: {regular}")

# bengal/postprocess/rss.py  
print(f"   ├─ RSS feed ✓")

# bengal/postprocess/sitemap.py
print(f"   └─ Sitemap ✓")
```

### After
```python
# bengal/orchestration/build.py
cli.header("Generated pages")
cli.metric("Total", total, indent=1, icon="├─")
cli.metric("Regular", regular, indent=1, icon="└─")

# bengal/postprocess/rss.py
cli.detail("RSS feed ✓", indent=1, icon="├─")

# bengal/postprocess/sitemap.py
cli.detail("Sitemap ✓", indent=1, icon="└─")
```

## Advanced Features (Future)

### 1. Message Templates
```python
cli.template("build_complete", pages=245, duration=0.8)
# Renders: "✨ Built 245 pages in 0.8s"
```

### 2. Spinners/Progress
```python
with cli.spinner("Discovering content..."):
    # Long operation
```

### 3. Interactive Prompts
```python
choice = cli.prompt("Continue?", choices=["yes", "no"])
```

### 4. Message Queue
```python
# Batch messages, flush at end
cli.batch_mode = True
cli.info("Message 1")
cli.info("Message 2")
cli.flush()  # Outputs all at once
```

## Implementation Checklist

- [x] Create `bengal/utils/cli_output.py`
- [ ] Test with all profiles
- [ ] Migrate build orchestrator
- [ ] Migrate postprocess
- [ ] Migrate config loader
- [ ] Remove scattered print statements
- [ ] Update tests
- [ ] Document API

## Next Steps

1. **Test the API**: Run builds with different profiles
2. **Get feedback**: Does the API feel natural?
3. **Start migration**: Begin with build.py
4. **Iterate**: Refine based on real usage

