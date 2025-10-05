# Persona-Based Observability - Quick Reference

**Quick lookup table for what each persona sees and needs.**

---

## Command Reference

### Writer (Default)
```bash
# All of these use writer profile
bengal build
bengal build --quiet
```

**Output**: Clean and minimal
```
✨ Built 192 pages in 4.8s

📂 Output:
   ↪ /path/to/public
```

---

### Theme Developer
```bash
# Enable theme developer mode
bengal build --theme-dev

# Or in config
[build]
profile = "theme-dev"
```

**Output**: Template-focused details
```
🔨 Build phases:
   ├─ Rendering:   4.29 s
   ├─ Assets:      392 ms
   └─ Postprocess: 539 ms

🏥 Theme Validation:
✅ Templates    passed
⚠️  Directives  1 warning
✅ Navigation   passed
```

---

### Bengal Developer
```bash
# Enable full observability
bengal build --dev

# Or
bengal build --debug
bengal build --profile dev
```

**Output**: Everything
```
● [discovery] phase_start
● phase_complete (78.7ms, +1.5MB, peak:1.8MB)
[APIDocEnhancer] Made 1 badge replacements
[Pipeline] Enhanced /path/to/page.md
...
📊 Performance:
   ├─ Memory RSS:  22.7 MB
   └─ Throughput:  35.8 pages/s
💾 Metrics saved to: .bengal-metrics/
```

---

## Feature Matrix

| Feature | Writer | Theme Dev | Bengal Dev | Why? |
|---------|--------|-----------|------------|------|
| **Build success/fail** | ✅ | ✅ | ✅ | Everyone needs this |
| **Output location** | ✅ | ✅ | ✅ | Everyone needs this |
| **Broken links** | ✅ | ✅ | ✅ | Critical for all |
| **Template errors** | ⚠️ Basic | ✅ Detailed | ✅ Detailed | Writers just need "it failed", devs need stack traces |
| **Phase timing** | ❌ | ✅ Summary | ✅ Detailed | Writers don't care, devs optimize |
| **Memory tracking** | ❌ | ❌ | ✅ | Only Bengal devs optimize memory |
| **Health checks** | 1/10 | 6/10 | 10/10 | Different validation needs |
| **Debug output** | ❌ | ❌ | ✅ | Internal details only for framework devs |
| **Metrics collection** | ❌ | ⚠️ Basic | ✅ Full | Tracking is for optimization |
| **Asset details** | ❌ | ✅ | ✅ | Theme devs need asset pipeline info |
| **Navigation checks** | ❌ | ✅ | ✅ | Theme devs build navigation |
| **Directive validation** | ❌ | ✅ | ✅ | Theme devs use directives |
| **Cache internals** | ❌ | ❌ | ✅ | Only framework concern |
| **Performance report** | ❌ | ❌ | ✅ | Only for optimization work |

---

## Health Check Breakdown

### What Runs Where?

| Validator | Writer | Theme Dev | Bengal Dev | Cost | Rationale |
|-----------|--------|-----------|------------|------|-----------|
| **Config** | ✅ | ✅ | ✅ | Low | Everyone needs valid config |
| **Output** | ✅ | ✅ | ✅ | Low | Everyone needs valid output |
| **Links** | ✅ | ✅ | ✅ | Medium | Broken links affect all users |
| **Rendering** | ❌ | ✅ | ✅ | Medium | Theme devs need HTML validation |
| **Directives** | ❌ | ✅ | ✅ | Medium | Theme devs use custom directives |
| **Navigation** | ❌ | ✅ | ✅ | Low | Theme devs build nav structures |
| **Menu** | ❌ | ✅ | ✅ | Low | Theme devs configure menus |
| **Taxonomy** | ❌ | ❌ | ✅ | Low | Framework-level validation |
| **Cache** | ❌ | ❌ | ✅ | Medium | Framework-level optimization |
| **Performance** | ❌ | ❌ | ✅ | Low | Framework-level metrics |

**Total validation time:**
- Writer: ~50-100ms (3 checks)
- Theme Dev: ~200-400ms (7 checks)
- Bengal Dev: ~500-750ms (10 checks)

---

## Performance Impact

### Build Time Comparison (192-page site)

| Profile | Time | vs Current | Saved |
|---------|------|------------|-------|
| **Current (all on)** | 5.37s | Baseline | - |
| **Writer** | ~4.7s | **12% faster** | 660ms |
| **Theme Dev** | ~5.1s | **5% faster** | 270ms |
| **Bengal Dev** | 5.37s | Same | - |

### Why Writer Mode is Faster

**Disabled features:**
- Memory tracking (tracemalloc): -100-250ms
- 7 health checks: -400-550ms
- Metrics collection: -50ms
- Debug output: -10ms

**Total savings**: ~660ms (12% faster)

---

## Migration Guide

### For Content Writers

**Before:**
```bash
bengal build --quiet  # Still too noisy
```

**After:**
```bash
bengal build  # Now clean by default!
```

No change needed - default is now optimized for you.

---

### For Theme Developers

**Before:**
```bash
bengal build --verbose  # Showed too much internal stuff
```

**After:**
```bash
bengal build --theme-dev  # Focused on templates and assets
```

Or set in config:
```toml
[build]
profile = "theme-dev"
```

---

### For Bengal Developers

**Before:**
```bash
bengal build --verbose --debug  # Showed everything
```

**After:**
```bash
bengal build --dev  # Same behavior, clearer intent
```

Or keep using `--verbose --debug` - they map to dev profile.

---

## Config Examples

### Writer (Default)

```toml
# No config needed - this is the default!
# Or explicitly:
[build]
profile = "writer"
```

### Theme Developer

```toml
[build]
profile = "theme-dev"

# Optional: customize what you see
[build.theme-dev]
show_phase_timing = true
health_checks = [
  "links",
  "rendering", 
  "directives",
  "navigation",
  "menu"
]
```

### Bengal Developer

```toml
[build]
profile = "dev"

# All features enabled by default
# Optional: fine-tune
[build.dev]
track_memory = true
enable_debug_output = true
collect_metrics = true
health_checks = "all"
```

### Custom Profile

```toml
[build]
profile = "custom"

# Mix and match
[build.custom]
show_phase_timing = true      # Like theme-dev
track_memory = false          # Like writer
health_checks = ["links", "rendering"]  # Pick your own
enable_debug_output = false
```

---

## Troubleshooting

### "I want more details!"

```bash
# Writer → Theme Dev
bengal build --theme-dev

# Writer → Bengal Dev
bengal build --dev
```

### "It's too noisy!"

```bash
# Theme Dev → Writer
bengal build  # Remove --theme-dev flag

# Or use quiet
bengal build --quiet
```

### "I want X but not Y"

Use config to customize:

```toml
[build]
profile = "theme-dev"

[build.theme-dev]
# Turn off specific features
show_phase_timing = false
track_memory = false
health_checks = ["links", "rendering"]  # Only these
```

### "How do I see what profile I'm using?"

```bash
bengal build --help

# Output shows current profile
```

Or add to build output:
```
ᓚᘏᗢ Building (profile: writer)...
```

---

## Common Questions

### Q: Can I override the profile per-build?

**A**: Yes! CLI flags override config:

```toml
# Config says theme-dev
[build]
profile = "theme-dev"
```

```bash
# But this uses dev profile for this build
bengal build --dev
```

### Q: Do profiles affect build output?

**A**: No! Profiles only affect:
- Console output verbosity
- What checks run
- Performance tracking

The actual generated HTML is identical.

### Q: Can I create my own profiles?

**A**: Yes! (Phase 5 feature - coming soon)

```toml
[build.profiles.my-ci]
show_phase_timing = true
track_memory = false
health_checks = ["config", "links"]
```

```bash
bengal build --profile my-ci
```

### Q: What about `bengal serve`?

**A**: Same profiles work:

```bash
bengal serve --theme-dev  # Theme development
bengal serve --dev        # Full debugging
```

Default is theme-dev for serve (more helpful during development).

---

## Decision Tree

```
Are you creating content?
├─ Yes → Use writer profile (default)
│  └─ bengal build
│
└─ No → Are you building/customizing themes?
   ├─ Yes → Use theme-dev profile
   │  └─ bengal build --theme-dev
   │
   └─ No → Are you working on Bengal itself?
      └─ Yes → Use dev profile
         └─ bengal build --dev
```

---

## Summary

**Default (writer)**:
- ✅ Fast
- ✅ Clean
- ✅ Shows errors
- ❌ No technical details

**--theme-dev**:
- ✅ Template errors
- ✅ Asset details
- ✅ Navigation checks
- ⚠️ Some technical details

**--dev**:
- ✅ Everything
- ✅ Memory profiling
- ✅ Debug output
- ✅ Full observability

