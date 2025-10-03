# CLI Ergonomics Improvements Plan

## Current State Analysis

### What's Working ✅
- Build stats table is informative and colorful
- ASCII art adds personality
- Performance metrics are helpful
- Color coding for speed indicators

### What's Noisy & Problematic 🔊

#### 1. **Per-Page Output Spam**
Current output shows EVERY page:
```
  ✓ api/index.html
  ✓ about/index.html
  ✓ contact/index.html
  ✓ api/v2/authentication/index.html
  ✓ api/v2/index.html
  ... (78 lines total!)
```

**Problem:** For 78 pages, this is 78 lines of noise. Most users don't care about each individual page unless something goes wrong.

#### 2. **Scattered Warnings/Errors**
Warnings are mixed in with success messages:
```
  ✓ docs/configuration-reference/index.html
  ⚠️  Jinja2 syntax error in /path/to/file.md: Missing end of raw directive
  ✓ docs/incremental-builds/index.html
  ⚠️  Error pre-processing /path/to/file.md: 'steps' is undefined
  ✓ docs/content-organization/index.html
```

**Problems:**
- Hard to spot issues
- No color coding on warnings
- Mixed with success messages
- Long file paths are distracting
- No grouping by error type

#### 3. **Generated Pages Noise**
Tag pages especially are noisy:
```
  ✓ tags/markdown/index.html
  ✓ tags/writing/index.html
  ✓ tags/tutorial/index.html
  ✓ tags/tutorial/page/2/index.html
  ✓ tags/features/index.html
  ... (37 tag pages!)
```

**Problem:** Generated pages (tags, archives, pagination) should be summarized, not listed individually.

#### 4. **Asset Processing**
```
Processing 23 assets...
```

**Problem:** No details about what happened. Did they minify? Did any fail?

## Proposed Improvements

### 1. Progress Indicators Instead of Per-Page Output

**Current (noisy):**
```
  ✓ page1/index.html
  ✓ page2/index.html
  ✓ page3/index.html
  ... (78 lines)
```

**Proposed (clean):**
```
📄 Rendering pages... [████████████████████████████] 78/78 (100%)
```

OR for simpler implementation:

**Proposed (summary):**
```
📄 Rendering content:
   ├─ Regular pages:    37
   ├─ Tag pages:        37  
   ├─ Archive pages:    4
   └─ Total:            78 ✓
```

### 2. Grouped & Colorful Error/Warning Summary

**Current (scattered):**
```
  ⚠️  Jinja2 syntax error in /long/path/file1.md: Missing end of raw directive
  ⚠️  Error pre-processing /long/path/file2.md: 'steps' is undefined
  ⚠️  Jinja2 syntax error in /long/path/file3.md: No filter named 'dateformat'
```

**Proposed (grouped at end):**
```
⚠️  Build Warnings (6):

   Jinja2 Template Errors (4):
   ├─ docs/template-system.md
   │  └─ Missing end of raw directive
   ├─ guides/performance-optimization.md
   │  └─ No filter named 'dateformat'
   ├─ tutorials/building-a-blog.md
   │  └─ No filter named 'dateformat'
   └─ tutorials/custom-theme.md
      └─ block 'title' defined twice

   Pre-processing Errors (2):
   ├─ guides/deployment-best-practices.md
   │  └─ 'steps' is undefined
   └─ posts/custom-templates.md
      └─ no loader for this environment specified
```

**With color:**
- File names: `yellow` (easier to spot)
- Error messages: `red` for errors, `yellow` for warnings
- Tree structure: `cyan`

### 3. Verbose Mode for Details

**Normal mode (quiet):**
```
📄 Rendering content... 78 pages ✓
```

**Verbose mode (--verbose):**
```
📄 Rendering content:
   Regular Pages (37):
   ├─ docs/advanced-markdown.md ✓
   ├─ docs/configuration-reference.md ✓
   ├─ guides/deployment.md ✓
   ... (all pages)
   
   Generated Pages (41):
   ├─ Tag pages: 37 ✓
   ├─ Archive pages: 4 ✓
   └─ Pagination: 2 ✓
```

### 4. Better Asset Output

**Current:**
```
Processing 23 assets...
```

**Proposed:**
```
📦 Processing assets:
   ├─ Copied:      18
   ├─ Minified:    3 (CSS)
   ├─ Optimized:   2 (images)
   └─ Total:       23 ✓
```

### 5. Post-Processing Summary

**Current:**
```
Running post-processing...
  ✓ Generated rss.xml
  ✓ Generated sitemap.xml
```

**Proposed:**
```
🔧 Post-processing:
   ├─ RSS feed ✓
   ├─ Sitemap ✓
   └─ Complete
```

## Complete Proposed Output

### Normal Build (No Warnings)
```
    /\_/\  
   ( -.o ) 
    > ^ <   Building...

🔨 Building site...

📂 Discovery:
   ├─ Content:      37 pages
   ├─ Sections:     8
   └─ Assets:       23

🏷️  Taxonomies:
   └─ Found 37 tags ✓

✨ Generated:
   ├─ Tag pages:    37
   ├─ Archives:     4
   └─ Total:        41 pages ✓

📄 Rendering:
   └─ 78 pages ✓

📦 Assets:
   └─ 23 files ✓

🔧 Post-processing:
   ├─ RSS feed ✓
   └─ Sitemap ✓


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
   └─ Mode:        parallel

⏱️  Performance:
   ├─ Total:       523 ms ⚡
   ├─ Discovery:   14 ms
   ├─ Taxonomies:  0.44 ms
   ├─ Rendering:   376 ms
   ├─ Assets:      49 ms
   └─ Postprocess: 7 ms

📈 Throughput:
   └─ 149.1 pages/second

─────────────────────────────────────────────────────
```

### Build With Warnings
```
[... same as above until the end ...]

⚠️  Build completed with warnings (6):

   Jinja2 Template Errors (4):
   ├─ docs/template-system.md
   │  └─ Missing end of raw directive
   ├─ guides/performance-optimization.md
   │  └─ No filter named 'dateformat'
   ├─ tutorials/building-a-blog.md
   │  └─ No filter named 'dateformat'
   └─ tutorials/custom-theme.md
      └─ block 'title' defined twice

   Pre-processing Errors (2):
   ├─ guides/deployment-best-practices.md
   │  └─ 'steps' is undefined
   └─ posts/custom-templates.md
      └─ no loader for this environment specified

💡 Tip: Run with --verbose to see full error details

[... stats table ...]
```

### Verbose Mode
```
[... initial phases same ...]

📄 Rendering (78 pages):
   
   Regular Pages (37):
   ├─ api/index.md ✓
   ├─ about/index.md ✓
   ├─ docs/advanced-markdown.md ✓
   ... [all regular pages]
   
   Generated Pages (41):
   ├─ Tag: markdown (5 posts) ✓
   ├─ Tag: writing (3 posts) ✓
   ├─ Tag: tutorial (12 posts, paginated) ✓
   ... [all tags]
   ├─ Archive: posts ✓
   └─ Pagination: posts (2 pages) ✓

[... rest ...]
```

## Implementation Plan

### Phase 1: Error Collection & Grouping
1. Modify `RenderingPipeline.process_page()` to collect errors instead of printing
2. Add error collector to `BuildStats`
3. Group errors by type

### Phase 2: Quiet Rendering Output
1. Add `quiet` mode to rendering (summary instead of per-page)
2. Respect `verbose` flag for detailed output
3. Use counters instead of individual prints

### Phase 3: Enhanced BuildStats Display
1. Add warnings section to stats table
2. Color code warnings/errors
3. Add "tip" messages for common issues

### Phase 4: Better Progress Indicators
1. Add phase-by-phase summary output
2. Group generated pages by type
3. Better asset processing summary

## Benefits

1. **Cleaner Output**: 78 lines → ~10 lines for rendering
2. **Better Error Visibility**: Grouped, colored, easy to find
3. **Actionable**: Tips and suggestions for fixes
4. **Scalable**: Works for 10 pages or 10,000 pages
5. **Ergonomic**: Easy to scan and understand
6. **Professional**: Like modern build tools (webpack, vite, etc.)

## Backwards Compatibility

- Default mode: New clean output
- `--verbose`: Show detailed per-page output (old behavior)
- `--quiet`: Minimal output (just stats)
- Environment variable: `BENGAL_VERBOSE=1` for CI debugging

## Inspiration

Similar to modern tools:
- **Vite**: Shows concise build summary with file counts
- **Next.js**: Groups pages by type, shows warnings at end
- **Webpack**: Progress bar + summary
- **Hugo**: Simple table (but we'll do better!)

## Next Steps

1. Review & approve this plan
2. Implement Phase 1 (error collection)
3. Implement Phase 2 (quiet rendering)
4. Test with real projects
5. Document new flags and options

