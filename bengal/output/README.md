# CLI Output Conventions

Bengal's CLI output follows an **ASCII-first** policy with semantic styling and consistent formatting.

## Icon Policy

### Default: ASCII Icons

By default, Bengal uses ASCII symbols for status indicators:

| Status | ASCII Icon | Meaning |
|--------|------------|---------|
| Success | `✓` | Operation completed successfully |
| Warning | `!` | Non-critical issue detected |
| Error | `x` | Error occurred |
| Info | `-` | Informational message |
| Tip | `*` | Helpful suggestion |

### Branding: Cat + Mouse

Bengal uses unique Unicode symbols for branding:

- **Success headers**: `ᓚᘏᗢ` (Bengal cat) - appears in main build complete headers
- **Error headers**: `ᘛ⁐̤ᕐᐷ` (Mouse) - appears in error section headers

These branding symbols are **always used** regardless of emoji settings.

### Optional: Emoji Mode

Enable emoji output by setting the environment variable:

```bash
export BENGAL_EMOJI=1
```

With emoji mode enabled:

| Status | Emoji Icon |
|--------|------------|
| Success | ✨ |
| Warning | ⚠️ |
| Error | ❌ |
| Info | ℹ️ |
| Tip | 💡 |

## Casing Conventions

### Section Headers: Sentence Case

All section headers use sentence case (first word capitalized, rest lowercase):

```
Content statistics:
Build configuration:
Performance:
Throughput:
Output:
```

**Not**:
```
Content Statistics:
BUILD CONFIGURATION:
PERFORMANCE:
```

### Status Messages: Sentence Case

```
Build complete
Build complete (with warnings)
No changes detected - build skipped!
```

**Not**:
```
BUILD COMPLETE
BUILD COMPLETE (WITH WARNINGS)
```

## Renderer Bridge

`CLIOutput` is Bengal's Milo/Kida renderer bridge. Milo commands, Kida
templates, prompts, raw progress, and compatibility utilities should share the
same instance from `bengal.output.get_cli_output()`.

Use `cli.output_mode("ci")` or `cli.output_mode("ascii")` as a scoped context
when a command needs ASCII-safe output. The context restores color, glyphs, and
process flags even when a command exits early, so embedded command calls do not
leak CI styling into later output.

Structured logger console events and build phase summaries also route through
this bridge. The only direct terminal writer left outside `CLIOutput` is the
live progress sink that owns carriage-return cursor control.

Repeated author-facing warnings should be aggregated when they share one event
shape and differ only by key, path, or item name. For example, missing icons,
unknown config entries, and URL collision claimants render as compact notices
with sample values and a shared hint instead of one warning per item.

## Color Semantics

Bengal uses semantic Milo theme tokens defined in `bengal/output/theme.py`:

| Token | Usage | Color |
|-------|-------|-------|
| `header` | Section headers | Orange (#FF9D00), bold |
| `success` | Success messages | Green (#2ECC71) |
| `warning` | Warnings | Orange (#E67E22) |
| `error` | Errors | Red (#E74C3C), bold |
| `bengal` | Cat mascot | Orange (#FF9D00), bold |
| `mouse` | Mouse mascot (errors) | Red, bold |
| `info` | Info/dim content | Silver (#95A5A6) |
| `tip` | Tips/suggestions | Grayish (#7F8C8D), italic |
| `path` | File paths | Blue (#3498DB) |
| `phase` | Build phase names | Bold |

## Output Structure

### Phase Lines

Each build phase emits a consistent phase line:

```
✓ Discovery     45ms
✓ Rendering     501ms (245 pages)
✓ Assets        Done
```

### Section Headers

Use the shared CLI output instance for section headers:

```python
from bengal.output import get_cli_output

cli = get_cli_output()
cli.section("Post-processing")  # Outputs: "\nPost-processing:"
```

### No Raw Print

All CLI output should go through the shared output bridge:

```python
# ✅ CORRECT
from bengal.output import get_cli_output

cli = get_cli_output()
cli.section("Processing")
cli.success("Done!")
cli.raw("machine-readable output", level=None)  # Only when semantic helpers do not fit

# ❌ WRONG
print("Processing:")
print("Done!")
```

## Performance Grades

Performance is indicated with ASCII tokens by default:

| Grade | ASCII | Meaning |
|-------|-------|---------|
| Excellent | `++` | Build time < 100ms |
| Fast | `+` | Build time < 1000ms |
| Moderate | `~` | Build time < 5000ms |
| Slow | `-` | Build time >= 5000ms |

With `BENGAL_EMOJI=1`:

| Grade | Emoji |
|-------|-------|
| Excellent | 🚀 |
| Fast | ⚡ |
| Moderate | 📊 |
| Slow | 🐌 |

## API Reference

### IconSet

```python
from bengal.output.icons import get_icon_set, IconSet

# Get default ASCII icons
icons = get_icon_set()
print(icons.success)  # "✓"
print(icons.mascot)   # "ᓚᘏᗢ"

# Get emoji icons
icons = get_icon_set(use_emoji=True)
print(icons.success)  # "✨"
```

### CLIOutput Methods

```python
from bengal.output import get_cli_output

cli = get_cli_output()

# Section headers
cli.section("Processing")      # "\nProcessing:"
cli.subheader("Details")       # "=== Details ======..."

# Status messages
cli.success("Build complete")  # "✓ Build complete"
cli.warning("Check config")    # "! Check config"
cli.error("Build failed")      # "x Build failed"
cli.tip("Try --verbose")       # "* Try --verbose"

# Phase lines
cli.phase("Rendering", duration_ms=500, details="245 pages")

# Paths
cli.path("/public", label="Output")  # "Output:\n   ↪ /public"
```

## Related Files

- `bengal/output/core.py` - CLIOutput implementation
- `bengal/output/icons.py` - Icon set definitions
- `bengal/output/enums.py` - MessageLevel and OutputStyle enums
- `bengal/output/utils.py` - ANSI codes and HTTP color mappings
- `bengal/output/colors.py` - Re-exports from utils.py (backward compat)
- `bengal/output/dev_server.py` - Dev server output mixin
- `bengal/output/globals.py` - Singleton access (get_cli_output)
- `bengal/output/theme.py` - Milo theme tokens for Kida rendering
