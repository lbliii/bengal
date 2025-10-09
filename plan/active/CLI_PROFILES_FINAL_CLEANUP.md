# CLI Profiles - Final Cleanup Needed

## Current Status

✅ **WRITER Profile** - Perfect!
```
    ᓚᘏᗢ  Building your site...

✓ Discovery     Done
✓ Rendering     Done
✓ Assets        Done
✓ Post-process  Done

✨ Built 245 pages in 1.3s
```

❌ **THEME-DEV & DEVELOPER Profiles** - Still showing log noise
```
    ᓚᘏᗢ  Building your site...

● build_start...
● [initialization] phase_start...
● phase_complete...
● [discovery] phase_start...
...  (40+ lines of log events)
```

## The Problem

The profiles have conflicting goals:
- **Want**: Detailed build stats at the end
- **Don't Want**: Console log noise during the build
- **Currently Getting**: Both stats AND log noise

## Root Cause

1. Profile configs set `verbose_build_stats: True`
2. This gets passed as `verbose` parameter to `site.build()`
3. The `verbose` flag controls BOTH:
   - Build stats detail level ✅ (want this)
   - Console log suppression ❌ (don't want logs)

## The Confusion

There are TWO different "verbose" concepts:
1. **Verbose logging** (`logger.info()` → console) - Should be OFF except with `--verbose` flag
2. **Verbose stats** (detailed build summary) - Should be ON for theme-dev/dev profiles

Currently they're conflated!

## Solution Needed

Separate these two concerns:

```python
# In profile configs:
{
    'verbose_build_stats': True,   # Show detailed stats
    'verbose_console_logs': False,  # But DON'T spam console with logs
}
```

Then in build orchestrator:
```python
# Always suppress console logs (they go to file)
set_console_quiet(True)

# But show detailed stats if profile wants them
show_detailed_stats = profile_config['verbose_build_stats']
```

## Current Workaround

Users can use `--full-output` to see everything:
```bash
bengal build --dev --full-output  # Logs + stats
```

But the default should be:
```bash
bengal build --dev  # Just stats, no log noise
```

## Files to Fix

1. **`bengal/utils/profile.py`**
   - Add `verbose_console_logs` to profile configs
   - Keep `verbose_build_stats` separate

2. **`bengal/orchestration/build.py`**
   - Use `verbose_console_logs` for `set_console_quiet()`
   - Use `verbose_build_stats` for stats display

3. **`bengal/cli.py`**
   - Don't pass `verbose_build_stats` as `verbose` to build()
   - Pass both flags separately

## Expected Behavior

### WRITER Profile
```
    ᓚᘏᗢ  Building your site...

✓ Discovery     Done
✓ Rendering     Done
✓ Assets        Done
✓ Post-process  Done

✨ Built 245 pages in 1.3s

📂 Output:
   ↪ /path/to/public
```

### THEME-DEV Profile
```
    ᓚᘏᗢ  Building your site...

✓ Discovery      61ms (245 pages)
✓ Rendering     501ms (173 regular + 72 generated)
✓ Assets         34ms (44 files)
✓ Post-process  204ms

    BUILD COMPLETE

📊 Content Statistics:
   ├─ Pages:       245 (173 regular + 72 generated)
   ├─ Sections:    31
   ├─ Assets:      44
   └─ Taxonomies:  43

⏱️  Performance:
   ├─ Total:       834ms
   ├─ Discovery:   61ms
   ├─ Rendering:   501ms
   ├─ Assets:      34ms
   └─ Postprocess: 204ms
```

### DEVELOPER Profile
```
    ᓚᘏᗢ  Building your site...

✓ Discovery      61ms (245 pages • 31 sections)
✓ Rendering     501ms (173 regular + 72 generated) 
✓ Assets         34ms (44 files)
✓ Post-process  204ms

    BUILD COMPLETE

📊 Content Statistics:
   ├─ Pages:       245 (173 regular + 72 generated)
   ├─ Sections:    31
   ├─ Assets:      44
   └─ Taxonomies:  43

⚙️  Build Configuration:
   └─ Mode:        parallel

⏱️  Performance:
   ├─ Total:       834ms ⚡
   ├─ Discovery:   61ms
   ├─ Taxonomies:  2ms
   ├─ Rendering:   501ms
   ├─ Assets:      34ms
   └─ Postprocess: 204ms

📈 Throughput:
   └─ 293.7 pages/second

💾 Memory:
   └─ Peak: 45.2 MB

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public

💡 Suggestions:
   • Consider parallel build for faster rendering
   • Enable incremental builds to skip unchanged files
```

## Key Insight

Profiles should control **WHAT info is shown**, not **WHERE it comes from**.

- Console logs → Always go to `.bengal-build.log` (except with explicit `--verbose`)
- Build output → Shown on console, level of detail controlled by profile

This way:
- Writers get minimal clean output
- Theme devs get detailed stats
- Developers get full metrics
- All logs still available in file for debugging

## Status

**Needs Implementation** - This is a design clarification issue, not a bug.

The profiles WORK, but they're showing too much during the build. We need to split "verbose stats" from "verbose logs".

