# Persona Output Comparison

**Side-by-side comparison of what each persona sees during a build.**

Test case: Building the showcase site (192 pages, 40 assets, 40 taxonomies)

---

## 🔍 Writer Profile (Default)

### Command
```bash
bengal build
```

### Output
```
ᓚᘏᗢ Building...

✨ Built 192 pages in 4.7s

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Line count**: 6 lines  
**Build time**: 4.7s (12% faster than current)

---

### With Warnings (Broken Link)

```bash
bengal build
```

```
ᓚᘏᗢ Building...

⚠️  1 broken link found:
   • about.md → /docs/missing-page

✨ Built 192 pages in 4.7s

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Line count**: 10 lines

---

### With Errors (Template Error)

```bash
bengal build
```

```
ᓚᘏᗢ Building...

❌ 1 template error:
   • page.html: undefined variable 'missing_var'
   
   💡 Check your template for typos. Available variables:
      page, site, config, posts, sections

⚠️  Built with errors - some pages may be incomplete

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Line count**: 13 lines

**Key characteristics:**
- ✅ Clean and minimal
- ✅ Shows critical issues only
- ✅ Actionable error messages
- ✅ No technical jargon
- ❌ No phase details
- ❌ No memory stats
- ❌ No health check summary

---

## 🎨 Theme Developer Profile

### Command
```bash
bengal build --theme-dev
```

### Output
```
ᓚᘏᗢ Building...

🔨 Build phases:
   ├─ Discovery:   78 ms
   ├─ Rendering:   4.29 s
   ├─ Assets:      392 ms
   └─ Postprocess: 539 ms

✨ Built 192 pages (35.8 pages/s)

🏥 Theme Validation:
✅ Configuration     passed
✅ Output            passed
✅ Rendering         passed
⚠️ Directives        1 warning
   • 3 pages have heavy directive usage (>10 directives)
     💡 Consider splitting large pages or reducing directive nesting.
        - strings.md: 21 directives
        - kitchen-sink.md: 19 directives
        - from-hugo.md: 22 directives
✅ Navigation        passed
✅ Menus             passed
✅ Links             passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 6 passed, 1 warning, 0 errors

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Line count**: 32 lines  
**Build time**: 5.1s (5% faster than current)

---

### With Template Error

```bash
bengal build --theme-dev
```

```
ᓚᘏᗢ Building...

🔨 Build phases:
   ├─ Discovery:   78 ms
   ├─ Rendering:   4.29 s (failed)
   ├─ Assets:      392 ms
   └─ Postprocess: 539 ms

❌ Template Error in page.html

  Location: base.html:45
  Problem:  Undefined variable 'author'
  
  Template chain:
    page.html (your file)
    └─ extends: base.html (line 45)
  
  Context:
    43 |     <main class="content">
    44 |       <article>
    45 |         <p class="author">By {{ author }}</p>  ← ERROR HERE
    46 |         {% block content %}
    47 |         {% endblock %}
  
  Available variables:
    ✓ page (Page object)
    ✓ site (Site object)
    ✓ config (dict)
    ✓ posts (list)
    ✗ author (missing)
  
  💡 Suggestion:
     Use {{ page.author }} or check your page frontmatter has 'author' field.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Built with errors

🏥 Theme Validation:
✅ Configuration     passed
❌ Rendering         1 error (template undefined variable)
✅ Navigation        passed
✅ Menus             passed
✅ Links             passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 4 passed, 0 warnings, 1 error

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public
```

**Line count**: 50 lines

**Key characteristics:**
- ✅ Phase timing (high-level)
- ✅ Detailed template errors with context
- ✅ Health checks focused on templates/themes
- ✅ Asset and navigation validation
- ✅ Helpful suggestions
- ❌ No memory tracking
- ❌ No debug output
- ❌ No internal metrics

---

## 🔧 Bengal Developer Profile

### Command
```bash
bengal build --dev
```

### Output
```
ᓚᘏᗢ Building...

🔨 Initial build...

● build_start
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase

  ● [initialization] phase_start
● phase_complete (3.5ms, +0.1MB, peak:0.1MB)

  ● [discovery] phase_start
  ● [discovery] discovery_complete
● phase_complete (78.7ms, +1.5MB, peak:1.8MB)

✨ Generated pages:
  ● [section_finalization] phase_start
● phase_complete (5.6ms, +0.0MB, peak:1.8MB)

  ● [taxonomies] phase_start

🏷️  Taxonomies:
   └─ Found 40 tags ✓
   └─ Total:            41 ✓
  ● [taxonomies] taxonomies_built
● phase_complete (10.2ms, +0.1MB, peak:1.8MB)

  ● [menus] phase_start
  ● [menus] menus_built
● phase_complete (0.2ms, +0.0MB, peak:1.8MB)

  ● [incremental_filtering] phase_start
● phase_complete (0.0ms, +0.0MB, peak:1.8MB)

📄 Rendering content:
  ● [rendering] phase_start
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[Pipeline] Enhanced /Users/llane/Documents/github/python/bengal/examples/showcase/content/api/core/page.md:
  Before: 20327 chars, has markers: True
  After:  21227 chars, has badges: True
[APIDocEnhancer] Made 2 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 2 badge replacements
[APIDocEnhancer] Made 2 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 1 badge replacements
[APIDocEnhancer] Made 1 badge replacements
  ● [rendering] rendering_complete
● phase_complete (4290.8ms, +12.2MB, peak:14.7MB)
   ├─ Regular pages:    125
   ├─ Archive pages:    6
   └─ Total:            192 ✓

  ● [assets] phase_start

📦 Assets:
   └─ 40 files ✓
  ● [assets] assets_complete
● phase_complete (392.4ms, +0.3MB, peak:14.7MB)

  ● [postprocessing] phase_start

🔧 Post-processing:
   ├─ RSS feed ✓
   └─ Sitemap ✓
  ✓ Special pages: 404
   ├─ Output formats: JSON (192 files), index.json ✓
  ● [postprocessing] postprocessing_complete
● phase_complete (540.0ms, +0.3MB, peak:16.4MB)

  ● [cache_save] phase_start
  ● [cache_save] cache_saved
● phase_complete (35.0ms, +0.0MB, peak:16.4MB)

  ● [health_check] phase_start

🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Configuration        passed
✅ Output               passed
✅ Rendering            passed
⚠️ Directives           1 warning(s)
   • 11 page(s) have heavy directive usage (>10 directives)
     💡 Consider splitting large pages or reducing directive nesting. Each directive adds ~20-50ms build time.
        - from-hugo.md: 22 directives
        - strings.md: 21 directives
        - kitchen-sink.md: 19 directives
        ... and 8 more
ℹ️ Navigation           1 info
✅ Navigation Menus     passed
ℹ️ Taxonomies           1 info
✅ Links                passed
ℹ️ Cache Integrity      1 info
ℹ️ Performance          1 info

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 27 passed, 1 warnings, 0 errors
Build Quality: 95% (Excellent)

● phase_complete (4532.5ms, +7.6MB, peak:22.7MB)
● build_complete (5368.0ms)

    BUILD COMPLETE

📊 Content Statistics:
   ├─ Pages:       192 (125 regular + 67 generated)
   ├─ Sections:    28
   ├─ Assets:      40
   └─ Taxonomies:  40

⚙️  Build Configuration:
   └─ Mode:        parallel

⏱️  Performance:
   ├─ Total:       5.37 s 🐌
   ├─ Discovery:   78 ms
   ├─ Taxonomies:  10 ms
   ├─ Rendering:   4.29 s
   ├─ Assets:      392 ms
   └─ Postprocess: 539 ms

📈 Throughput:
   └─ 35.8 pages/second

💾 Memory:
   ├─ RSS:         22.7 MB
   ├─ Heap:        14.7 MB
   └─ Peak:        22.7 MB

📂 Output:
   ↪ /Users/llane/Documents/github/python/bengal/examples/showcase/public

💾 Performance metrics saved to:
   ↪ .bengal-metrics/history.jsonl
   ↪ .bengal-metrics/latest.json
```

**Line count**: 227 lines  
**Build time**: 5.37s (same as current)

**Key characteristics:**
- ✅ Full phase tracking with timing
- ✅ Memory deltas per phase
- ✅ Debug output (APIDocEnhancer, Pipeline)
- ✅ All 10 health checks
- ✅ Complete statistics
- ✅ Performance metrics saved
- ✅ Detailed memory profiling

---

## 📊 Comparison Table

| Aspect | Writer | Theme Dev | Bengal Dev |
|--------|--------|-----------|------------|
| **Lines of output** | 6-13 | 30-50 | 200-230 |
| **Build time (192 pages)** | 4.7s | 5.1s | 5.37s |
| **Speed vs current** | 12% faster ⚡ | 5% faster ⚡ | Same |
| **Phase details** | None | Summary | Full |
| **Memory tracking** | None | None | Per-phase |
| **Health checks** | 3 | 7 | 10 |
| **Debug output** | None | None | All |
| **Error detail** | Basic | Detailed | Full |
| **Template context** | No | Yes | Yes + stack |
| **Metrics saved** | No | No | Yes |
| **Noise level** | Low 🔇 | Medium 🔉 | High 🔊 |
| **Info density** | Essential | Focused | Everything |

---

## 🎯 When to Use Each Profile

### Writer Profile
```
Use when:
✓ Writing blog posts
✓ Creating documentation
✓ Editing content pages
✓ Quick iterations
✓ You just want to know "did it work?"

Avoid when:
✗ Building custom themes
✗ Debugging template errors
✗ Need performance data
```

### Theme Developer Profile
```
Use when:
✓ Creating custom themes
✓ Debugging templates
✓ Building complex layouts
✓ Testing directives
✓ Optimizing asset pipeline
✓ Configuring navigation

Avoid when:
✗ Just editing content
✗ Need full framework debugging
```

### Bengal Developer Profile
```
Use when:
✓ Contributing to Bengal
✓ Debugging build issues
✓ Performance optimization
✓ Memory profiling
✓ CI/CD pipeline debugging
✓ Understanding internals

Avoid when:
✗ Normal day-to-day usage
✗ Performance is critical
✗ You find output overwhelming
```

---

## 💡 Pro Tips

### Switching Mid-Session

```bash
# Start with writer mode
bengal build

# Something looks wrong...
bengal build --theme-dev

# Still not clear...
bengal build --dev
```

You can escalate verbosity as needed!

### CI/CD Recommendation

```yaml
# .github/workflows/build.yml

- name: Build site
  run: bengal build --theme-dev  # Good balance for CI
  
# Or for maximum speed:
- name: Build site  
  run: bengal build  # Writer mode (fastest)
```

### Local Development

```toml
# bengal.toml
[build]
profile = "theme-dev"  # Good default for development
```

Then serve:
```bash
bengal serve  # Uses theme-dev profile from config
```

---

## 🔄 Migration Examples

### Before: Current Verbose Output
```bash
$ bengal build --verbose
# 227 lines of output
# Everything enabled
# 5.37s build time
```

### After: Writer Mode (New Default)
```bash
$ bengal build
# 6 lines of output  ← 97% less noise!
# Only essentials
# 4.7s build time  ← 12% faster!
```

### After: Theme Dev Mode
```bash
$ bengal build --theme-dev
# 30-50 lines of output
# Template-focused
# 5.1s build time  ← 5% faster
```

### After: Dev Mode (Same as Before)
```bash
$ bengal build --dev
# 227 lines of output
# Everything enabled
# 5.37s build time
# (Same as old --verbose)
```

---

## 📈 Expected Adoption

**Week 1 after release:**
- 70% using default (writer)
- 20% using theme-dev
- 10% using dev

**After 1 month:**
- 80% using default (writer)
- 15% using theme-dev
- 5% using dev

**Rationale**: Most users are content authors. They'll appreciate the cleaner default.

---

## 🎨 Visual Summary

```
Writer Profile       Theme Dev Profile      Bengal Dev Profile
═══════════════      ══════════════════     ══════════════════
                                            
  Simple               Focused                Everything
  ↓                    ↓                      ↓
                                            
┌────────┐          ┌─────────────┐        ┌──────────────────┐
│ Status │          │ Status      │        │ Status           │
│ Errors │          │ Phases      │        │ Phases (detail)  │
│ Output │          │ Errors      │        │ Memory           │
└────────┘          │ Theme check │        │ Debug output     │
                    │ Assets      │        │ All health checks│
  6 lines           │ Navigation  │        │ Metrics          │
  4.7s              │ Output      │        │ Cache            │
                    └─────────────┘        │ Performance      │
                                           │ Output           │
                     30-50 lines           └──────────────────┘
                     5.1s
                                            227 lines
                                            5.37s


🔇 Quiet            🔉 Moderate             🔊 Detailed
⚡ Fastest           ⚡ Fast                 🐌 Full profiling
✅ Errors only       ✅ Template focus       ✅ Everything
```

---

## Summary

The persona-based system gives users exactly what they need:

1. **Writers** get fast, clean builds with minimal noise
2. **Theme developers** get template and asset-focused output
3. **Bengal developers** get full observability for optimization

Everyone wins! 🎉

