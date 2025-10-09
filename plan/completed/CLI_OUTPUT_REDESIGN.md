# CLI Output Composition Redesign

## Problem

Current output has several issues:
1. **Inconsistent indentation**: Cat (4sp), path (3sp), RSS/Sitemap (3sp), phases (0sp)
2. **Scattered info**: RSS/Sitemap appears before phases but is actually post-processing
3. **Early noise**: `● config_file_found`, `config_load_start` still showing
4. **Redundancy**: Path shown at start and end
5. **Visual hierarchy unclear**: What's important vs. supplementary?

## Current Output Analysis

```
    ᓚᘏᗢ  Building your site...              # 4 spaces, header

   ↪ /Users/.../showcase                     # 3 spaces, path (redundant?)

   ├─ RSS feed ✓                             # 3 spaces, post-processing (out of order)
   └─ Sitemap ✓                              # 3 spaces, post-processing
  ✓ Special pages: 404                       # 2 spaces, post-processing
✓ Discovery     Done                         # 0 spaces, phase
✓ Rendering     Done                         # 0 spaces, phase  
✓ Assets        Done                         # 0 spaces, phase
✓ Post-process  Done                         # 0 spaces, phase

✨ Built 245 pages in 0.8s                   # 0 spaces, summary

📂 Output:                                   # 0 spaces, output path
   ↪ /Users/.../public                      # 3 spaces
```

## Design Principles

1. **Hierarchy through indentation**
   - Level 0: Major status (header, phases, summary)
   - Level 1: Details/context (sub-items, paths)

2. **Chronological order**
   - RSS/Sitemap/404 should appear AFTER or WITHIN Post-process phase

3. **Information density**
   - Combine related info on same line when possible
   - Remove redundant info (initial path?)

4. **Consistency**
   - All phase status lines at same indent
   - All detail lines at same indent

## Proposed Redesign Options

### Option A: Ultra-Minimal (Writer Profile)
```
ᓚᘏᗢ  Building...

✓ Discovery
✓ Rendering (245 pages)
✓ Assets (44 files)
✓ Post-process (RSS, Sitemap, 404)

✨ Built in 0.8s → public/
```

**Pros**: Extremely concise, fast to read, no scrolling
**Cons**: Less context, path is relative only

### Option B: Balanced (Current Default)
```
ᓚᘏᗢ  Building your site...

✓ Discovery
✓ Rendering
✓ Assets
✓ Post-process
  ├─ RSS feed
  ├─ Sitemap  
  └─ Special pages (404)

✨ Built 245 pages in 0.8s

📂 /Users/.../showcase/public
```

**Pros**: Clear hierarchy, chronological, consistent indentation
**Cons**: RSS/Sitemap/404 adds vertical space

### Option C: Inline Details (Theme-Dev Profile)
```
ᓚᘏᗢ  Building your site...

✓ Discovery     61ms • 245 pages, 31 sections
✓ Rendering     501ms • 173 regular + 72 generated
✓ Assets        34ms • 44 files
✓ Post-process  204ms • RSS, Sitemap, 404

✨ Built in 0.8s (293.7 pages/sec) → public/
```

**Pros**: Dense, metrics inline, single line per phase
**Cons**: Can be overwhelming, harder to scan

### Option D: Two-Column (Developer Profile)  
```
ᓚᘏᗢ  Building your site...

✓ Discovery          61ms    245 pages, 31 sections
✓ Rendering         501ms    173 regular + 72 generated  
✓ Assets             34ms    44 files processed
✓ Post-process      204ms    RSS • Sitemap • 404

✨ Built in 0.8s (293.7 pages/sec)
📂 /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Pros**: Scannable columns, aligned metrics, detailed
**Cons**: Requires more width, complex formatting

## Recommendations by Profile

### WRITER Profile
**Goal**: Minimal distraction, just show success/failure

```
ᓚᘏᗢ  Building...

✓ Discovered 245 pages
✓ Rendered all pages  
✓ Processed 44 assets
✓ Generated RSS & Sitemap

✨ Built in 0.8s → public/
```

- No detailed paths
- No phase names (use verbs instead)
- Inline post-processing details
- Relative output path

### THEME_DEV Profile  
**Goal**: Show template/asset changes quickly

```
ᓚᘏᗢ  Building your site...

✓ Discovery     61ms
✓ Rendering     501ms (245 pages)
✓ Assets        34ms (44 files)
✓ Post-process  204ms

✨ Built in 0.8s → /Users/.../showcase/public
```

- Phase timing visible
- Counts in parentheses  
- Compact post-processing
- Abbreviated paths

### DEVELOPER Profile
**Goal**: Full metrics and diagnostics

```
ᓚᘏᗢ  Building your site...

✓ Discovery          61ms    245 pages • 31 sections
✓ Rendering         501ms    173 regular • 72 generated
✓ Assets             34ms    44 files
✓ Post-process      204ms    RSS • Sitemap • 404

⚡ Built in 0.8s (293.7 pages/sec) • parallel mode
📂 /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

- Full timing with alignment
- Detailed counts and breakdown
- Throughput metrics
- Full output path

## Early Config Noise

The `● config_file_found`, `● config_load_start` messages should be suppressed by default.

**Fix**: In `bengal/config/loader.py`, only log these at DEBUG level or suppress when live progress is active.

## Implementation Priority

1. **Fix early config noise** (quick win)
2. **Implement profile-specific formatting** (use existing profile system)
3. **Consistent indentation** (all phases at level 0, details at level 1)
4. **Move RSS/Sitemap/404 after Post-process** (chronological order)

## Next Steps

1. Get user feedback on preferred option per profile
2. Update output formatting in:
   - `bengal/orchestration/build.py` (phases)
   - `bengal/postprocess/*.py` (RSS/Sitemap/404)
   - `bengal/config/loader.py` (config messages)
   - `bengal/utils/live_progress.py` (if using live progress)

