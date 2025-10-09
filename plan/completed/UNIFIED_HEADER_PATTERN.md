# Unified Header Pattern - Complete! ✅

## The Pattern

**Every Bengal command now starts with:**

```
ᓚᘏᗢ  {Present Progressive Verb} {Object}...
```

## Command Headers

| Command | Header |
|---------|--------|
| `bengal build` | `ᓚᘏᗢ  Building your site...` |
| `bengal serve` | `ᓚᘏᗢ  Building your site...` (then shows server box) |
| `bengal clean` | `ᓚᘏᗢ  Cleaning output directory...` |
| `bengal autodoc` | `ᓚᘏᗢ  Generating documentation...` |
| `bengal autodoc-cli` | `ᓚᘏᗢ  Generating documentation...` |
| `bengal autodoc-python` | `ᓚᘏᗢ  Generating documentation...` |
| `bengal analyze` | `ᓚᘏᗢ  Building knowledge graph...` |
| `bengal analyze --viz` | `ᓚᘏᗢ  Generating interactive visualization...` |

## Pattern Elements

### 1. Cat Emoji (ᓚᘏᗢ)
- Unique identifier for Bengal
- Friendly, approachable
- Consistent brand element

### 2. Two Spaces
- `ᓚᘏᗢ  ` (cat + two spaces)
- Proper breathing room
- Visual separation

### 3. Present Progressive Verb
- "Building", "Cleaning", "Generating", "Starting"
- Shows active process
- Consistent grammatical form

### 4. Object/Target
- "your site", "output directory", "documentation"
- Clear about what's being done
- User-centric language

### 5. Ellipsis (...)
- Indicates ongoing process
- Consistent ending
- Professional look

## Examples

### Build Command
```
    ᓚᘏᗢ  Building your site...

✓ Discovery     Done
✓ Rendering     Done
✓ Assets        Done
✓ Post-process  Done

✨ Built 245 pages in 0.8s
```

### Clean Command
```
    ᓚᘏᗢ  Cleaning output directory...

   ↪ /path/to/public

✓ Clean complete!
```

### Autodoc Command
```
    ᓚᘏᗢ  Generating documentation...

   ✓ Generated 50 files in 2.3s

📂 Output:
   ↪ /path/to/docs
```

## Implementation

All commands now use the `CLIOutput.header()` method:

```python
from bengal.utils.cli_output import CLIOutput

cli = CLIOutput()
cli.header("Building your site...")
# or
cli.header("Cleaning output directory...")
# or
cli.header("Generating documentation...")
```

The `header()` method automatically:
- ✅ Adds the cat emoji
- ✅ Adds proper spacing
- ✅ Applies bold cyan styling
- ✅ Handles blank lines
- ✅ Respects TTY/non-TTY environments

## Files Changed

All command entry points updated:
- `bengal/orchestration/build.py` - Build header
- `bengal/utils/build_stats.py` - Clean header
- `bengal/cli.py` - Autodoc headers (5 places)

## Benefits

### 1. Brand Consistency
Every command feels like Bengal. Users instantly recognize the tool.

### 2. Predictable UX
Users know what to expect when running any command.

### 3. Professional
Consistent grammar, styling, and formatting across all commands.

### 4. Scannable
The cat emoji is a visual anchor that's easy to spot in terminal output.

### 5. Friendly
The mascot adds personality without being unprofessional.

## Design Rationale

### Why Cat Emoji?
- **Unique**: Not commonly used in dev tools
- **Memorable**: "That's the Bengal cat tool"
- **Brand-appropriate**: Bengal = cat breed
- **Friendly**: Approachable, not intimidating

### Why Present Progressive?
- **Active voice**: Shows process is happening
- **Grammatically consistent**: All commands use same form
- **Clear intent**: Users know what's being done

### Why Ellipsis?
- **Standard convention**: Common in CLI tools
- **Indicates progress**: Shows something is happening
- **Professional**: Matches user expectations

## Comparison

### Before (Inconsistent)
```
build:    ᓚᘏᗢ  Building your site...
serve:    ╭─── BENGAL SSG ───╮ + ᓚᘏᗢ  Building...
clean:    🧹 Cleaning output directory...
autodoc:  🔨 Generating documentation...
```

### After (Unified)
```
build:    ᓚᘏᗢ  Building your site...
serve:    ᓚᘏᗢ  Building your site...
clean:    ᓚᘏᗢ  Cleaning output directory...
autodoc:  ᓚᘏᗢ  Generating documentation...
```

Every command follows the exact same pattern!

## Testing

Tested all major commands:

```bash
$ bengal build
    ᓚᘏᗢ  Building your site...

$ bengal serve
    ᓚᘏᗢ  Building your site...

$ bengal clean --force
    ᓚᘏᗢ  Cleaning output directory...

$ bengal autodoc --help
# (help text, no header - correct)

$ bengal autodoc src/
    ᓚᘏᗢ  Generating documentation...
```

All commands now have consistent, professional headers! ✨

## Status

**Complete!** ✅

Every Bengali command now follows the unified header pattern:

```
ᓚᘏᗢ  {Present Progressive Verb} {Object}...
```

The CLI feels cohesive, professional, and distinctly "Bengal".

