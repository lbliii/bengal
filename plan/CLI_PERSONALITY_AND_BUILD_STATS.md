# CLI Personality and Build Stats

## Overview

Enhanced the Bengal CLI with colorful build statistics, ASCII art, and personality - similar to Hugo's build output but with our own Bengal flair!

## Features Implemented

### 1. Build Statistics Display

Created a comprehensive build statistics system that shows:

#### Content Statistics
- Total pages (regular + generated breakdown)
- Total sections
- Total assets
- Taxonomy counts

#### Build Configuration
- Build mode (parallel, incremental, or sequential)
- Visual indicators for mode combinations

#### Performance Metrics
- **Total build time** with color coding:
  - 🚀 Green for super fast (< 100ms)
  - ⚡ Yellow for fast (< 1s)
  - 🐌 Red for slower (> 1s)
- **Phase breakdown**:
  - Discovery time
  - Taxonomy collection time
  - Rendering time
  - Assets processing time
  - Post-processing time
- **Throughput**: Pages per second

### 2. ASCII Art & Personality

Added Bengal tiger ASCII art that changes based on context:

```
Building:
    /\_/\  
   ( -.o ) 
    > ^ <   Building...

Success:
    /\_/\  
   ( ^.^ ) 
    > ^ <

Error:
    /\_/\  
   ( x.x ) 
    > ^ <
```

### 3. Colorful CLI Commands

Enhanced all CLI commands with emojis and personality:

- `build` 🔨 - Shows full build stats table
- `serve` 🚀 - Shows welcome banner
- `clean` 🧹 - Shows cleaning progress
- `new site` 🏗️ - Shows creation progress
- `new page` 📄 - Confirms page creation

### 4. CLI Options

Added new options:
- `--quiet` / `-q`: Minimal output (skips stats table)
- Build stats shown by default on all builds
- Stats shown during dev server rebuilds

## Example Output

### Build Command

```
    /\_/\  
   ( -.o ) 
    > ^ <   Building...

🔨 Building site...

[... build output ...]

    /\_/\  
   ( ^.^ ) 
    > ^ <


┌─────────────────────────────────────────────────────┐
│              🎉 BUILD COMPLETE 🎉                 │
└─────────────────────────────────────────────────────┘

📊 Content Statistics:
   ├─ Pages:       78 (37 regular + 41 generated)
   ├─ Sections:    8
   ├─ Assets:      23
   └─ Taxonomies:  37

⚙️  Build Configuration:
   └─ Mode:        incremental + parallel

⏱️  Performance:
   ├─ Total:       4.09 s 🐌
   ├─ Discovery:   14 ms
   ├─ Taxonomies:  0.44 ms
   ├─ Rendering:   3.76 s
   ├─ Assets:      49 ms
   └─ Postprocess: 7 ms

📈 Throughput:
   └─ 19.1 pages/second

─────────────────────────────────────────────────────
```

### Serve Command

```
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║        /\_/\      BENGAL SSG                        ║
    ║       ( ^.^ )     Fast & Fierce Static Sites        ║
    ║        > ^ <                                         ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝

[... server startup ...]

🚀 Bengal dev server running at http://localhost:8000/
```

### Clean Command

```
🧹 Cleaning output directory...
   ├─ Directory: /path/to/public
   └─ ✓ Clean complete!
```

### Help Output

```
Usage: bengal [OPTIONS] COMMAND [ARGS]...

  🐯 Bengal SSG - A high-performance static site generator.

  Fast & fierce static site generation with personality!

Commands:
  build  🔨 Build the static site.
  clean  🧹 Clean the output directory.
  new    ✨ Create new site, page, or section.
  serve  🚀 Start development server with hot reload.
```

## Technical Implementation

### Files Modified

1. **`bengal/utils/build_stats.py`** (NEW)
   - `BuildStats` dataclass for statistics
   - `display_build_stats()` for formatted output
   - ASCII art variations
   - Helper functions for colorful output

2. **`bengal/core/site.py`**
   - Modified `build()` to return `BuildStats`
   - Added timing collection for each phase
   - Captures statistics throughout build process

3. **`bengal/cli.py`**
   - Updated all command docstrings with emojis
   - Integrated build stats display
   - Added `--quiet` flag for minimal output
   - Enhanced error handling with colorful output

4. **`bengal/server/dev_server.py`**
   - Shows build stats on initial build
   - Shows build stats on file change rebuilds
   - Cleaner output for file watching

### Design Decisions

1. **Color Coding**: Used click's styling for cross-platform compatibility
2. **Performance Indicators**: Emoji-based performance hints (🚀⚡🐌)
3. **Tree Formatting**: Used box-drawing characters for hierarchical display
4. **Quiet Mode**: Allow users to opt-out of verbose stats for CI/automation
5. **ASCII Art**: Simple, terminal-friendly tiger face (no complex art that might break)

## Benefits

1. **Developer Experience**: Fun and informative feedback during builds
2. **Performance Insights**: Easy to spot slow builds and bottlenecks
3. **Debugging**: Phase breakdown helps identify where time is spent
4. **Professionalism**: Polished CLI output similar to modern tools
5. **Personality**: Makes Bengal stand out from other SSGs

## Comparison to Hugo

Hugo shows a simple table like:
```
                   |  EN   
-------------------+-------
  Pages            |   78
  Paginator pages  |    0
  Non-page files   |   23
  Static files     |    0
  Processed images |    0
  Aliases          |    0
  Sitemaps         |    1
  Cleaned          |    0

Total in 523 ms
```

Bengal's approach:
- ✅ More visual with ASCII art and colors
- ✅ More detailed phase breakdown
- ✅ Better performance indicators
- ✅ More personality and fun
- ✅ Still clean and professional
- ✅ Shows throughput (pages/second)

## Future Enhancements

Possible additions:
1. Progress bars for long builds
2. Real-time rendering progress (X/Y pages)
3. Memory usage statistics
4. Cache hit ratio for incremental builds
5. Comparison with previous build (% faster/slower)
6. File size statistics (total output size)
7. Top 5 slowest pages to render
8. Custom ASCII art via config
9. Different color schemes/themes
10. JSON output mode for CI integration

## Testing

Tested on:
- ✅ Regular build (`bengal build`)
- ✅ Incremental build (`bengal build --incremental`)
- ✅ Quiet mode (`bengal build --quiet`)
- ✅ Server builds (`bengal serve`)
- ✅ File change rebuilds (dev server)
- ✅ Clean command
- ✅ New site/page commands
- ✅ Help output

All working as expected with colorful, informative output!

## Status

✅ **COMPLETE** - Ready for use and testing with real projects!

