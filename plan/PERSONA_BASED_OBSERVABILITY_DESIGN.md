# Persona-Based Observability Design

**Date**: October 5, 2025  
**Status**: Design Phase  
**Priority**: High - Performance and UX Impact

---

## Problem Statement

Bengal now has extensive observability features:
- Structured logging with phase tracking
- Performance metrics collection
- 10 health check validators
- Memory profiling
- Debug output (APIDocEnhancer, Pipeline)
- Build statistics

**Issues:**
1. **Too noisy for writers**: Default output shows developer-focused details (memory deltas, phase timing, API doc badges)
2. **Performance overhead**: Some features may slow builds unnecessarily for regular use
3. **No persona alignment**: All features run for everyone regardless of their needs
4. **Hardcoded debug output**: Some messages go directly to stderr without controls

---

## Three Personas

### 1. **Writers** (Content Authors)
**Goal**: Create content quickly without technical friction

**Needs:**
- ✅ Simple "build succeeded" confirmation
- ✅ Error messages when content has issues
- ✅ Clear indication of broken links or missing images
- ✅ Minimal console noise
- ❌ Don't need: Memory usage, phase timing, cache details, performance metrics

**Example User Story:**
> "I just edited a blog post and ran `bengal build`. I want to know if it worked, if there are any broken links, and where the output is. I don't care about memory usage or build phases."

### 2. **Theme Developers** (Template Authors)
**Goal**: Build and customize themes without debugging Bengal internals

**Needs:**
- ✅ Template error details (Jinja2 syntax, undefined variables)
- ✅ Asset processing information
- ✅ Navigation/menu validation
- ✅ Rendering validation (HTML quality)
- ✅ Directive syntax validation (for custom components)
- ⚠️ Some performance info (to optimize templates)
- ❌ Don't need: Deep internals, memory profiling, cache algorithms

**Example User Story:**
> "I'm creating a custom theme with complex navigation. I need to see template errors clearly, know if my assets are processed correctly, and ensure my custom directives work. Basic performance info helps me optimize templates."

### 3. **Bengal Developers** (Framework Contributors)
**Goal**: Optimize Bengal, debug issues, track performance regressions

**Needs:**
- ✅ Everything: Full observability
- ✅ Memory profiling and tracking
- ✅ Per-phase timing breakdown
- ✅ Cache integrity checks
- ✅ Performance metrics and trends
- ✅ Debug output (API doc enhancer, pipeline details)
- ✅ Historical performance data

**Example User Story:**
> "I'm optimizing the rendering pipeline. I need detailed phase timing, memory usage per phase, cache hit rates, and historical metrics to detect regressions. Debug output helps me understand what's happening internally."

---

## Current Feature Categorization

### By Persona Need

| Feature | Writers | Theme Devs | Bengal Devs | Performance Impact | Current State |
|---------|---------|------------|-------------|-------------------|---------------|
| **Basic build status** | ✅ | ✅ | ✅ | None | Always on |
| **Content errors** | ✅ | ✅ | ✅ | Low | Always on |
| **Link validation** | ✅ | ✅ | ✅ | Medium | Health check |
| **Template errors** | ⚠️ | ✅ | ✅ | None | Always on |
| **Asset processing** | ⚠️ | ✅ | ✅ | None | Always shown |
| **Navigation validation** | ⚠️ | ✅ | ✅ | Low | Health check |
| **Directive validation** | ⚠️ | ✅ | ✅ | Medium | Health check |
| **Rendering validation** | ❌ | ✅ | ✅ | Medium | Health check |
| **Menu validation** | ❌ | ✅ | ✅ | Low | Health check |
| **Phase timing** | ❌ | ⚠️ | ✅ | None | Always shown |
| **Memory tracking** | ❌ | ❌ | ✅ | Medium (~2-5%) | Always on |
| **Cache validation** | ❌ | ❌ | ✅ | Medium | Health check |
| **Performance metrics** | ❌ | ❌ | ✅ | Low | Health check |
| **Debug output** | ❌ | ❌ | ✅ | None | Hardcoded |
| **Metrics collection** | ❌ | ❌ | ✅ | Low | Always on |

---

## Proposed Solution: Profile System

### Design Philosophy

1. **Zero-config for writers**: Default behavior optimized for content authors
2. **Opt-in complexity**: Advanced features available via flags or config
3. **Performance by default**: Heavy profiling only when needed
4. **Discoverable**: Help users understand what's available

### Profile Definitions

#### **Profile 1: Writer Mode** (Default)

```bash
# Default - no flags needed
bengal build
```

**What runs:**
- ✅ Basic build status
- ✅ Content errors (broken frontmatter, missing files)
- ✅ Link validation (broken internal/external links)
- ✅ Simple statistics (pages built, time, output location)
- ❌ Health checks disabled (except critical errors)
- ❌ No phase timing
- ❌ No memory tracking
- ❌ No debug output
- ❌ No metrics collection

**Output Example:**
```
ᓚᘏᗢ Building...

✨ Built 192 pages in 4.8s

⚠️  2 broken links found:
   • about.md → /docs/missing-page
   • blog/post.md → https://dead-site.com

📂 Output:
   ↪ /path/to/public
```

Clean, focused, minimal noise.

#### **Profile 2: Theme Developer Mode**

```bash
# Enable with flag
bengal build --theme-dev

# Or set in config
[build]
profile = "theme-dev"
```

**What runs:**
- ✅ Everything from Writer mode
- ✅ Template validation and error details
- ✅ Asset processing details
- ✅ Navigation/menu validation (health checks)
- ✅ Directive validation (syntax, completeness)
- ✅ Rendering validation (HTML quality)
- ✅ Basic performance stats (to help optimize)
- ✅ Phase timing (summary only)
- ❌ No memory profiling
- ❌ No debug output (internals)
- ❌ No cache internals
- ⚠️ Minimal metrics collection (just timing)

**Output Example:**
```
ᓚᘏᗢ Building...

🔨 Build phases:
   ├─ Discovery:   78 ms
   ├─ Rendering:   4.29 s
   ├─ Assets:      392 ms
   └─ Postprocess: 539 ms

✨ Built 192 pages (35.8 pages/s)

🏥 Theme Validation:
✅ Templates         passed
✅ Navigation        passed
⚠️  Directives       1 warning
   • 3 pages have heavy directive usage
✅ Rendering         passed
✅ Assets            passed

📂 Output: /path/to/public
```

More detail, focused on theme concerns.

#### **Profile 3: Developer Mode**

```bash
# Enable with flags
bengal build --dev

# Or explicitly
bengal build --profile dev

# Individual flags still work
bengal build --verbose --debug
```

**What runs:**
- ✅ **Everything**: Full observability
- ✅ All health checks
- ✅ Memory profiling (tracemalloc + psutil)
- ✅ Per-phase timing with memory deltas
- ✅ Debug output (API doc enhancer, pipeline)
- ✅ Performance metrics collection
- ✅ Cache integrity checks
- ✅ Detailed error tracebacks

**Output Example:**
```
ᓚᘏᗢ Building...

● build_start

 ● [initialization] phase_start
● phase_complete (3.5ms, +0.1MB, peak:0.1MB)

 ● [discovery] phase_start
[APIDocEnhancer] Made 1 badge replacements
[Pipeline] Enhanced /path/to/page.md
● phase_complete (78.7ms, +1.5MB, peak:1.8MB)

[... full phase output ...]

🏥 Health Check Summary (all 10 validators)
✅ Configuration       passed
✅ Output             passed
[... all checks ...]

📊 Performance:
   ├─ Total:       5.37 s
   ├─ Memory RSS:  22.7 MB
   ├─ Memory heap: 14.7 MB
   └─ Throughput:  35.8 pages/s

💾 Metrics saved to: .bengal-metrics/
```

Full detail for debugging and optimization.

---

## Implementation Plan

### Phase 1: Add Profile System (2 hours)

#### 1.1 Create Profile Enum and Config

**File**: `bengal/utils/profile.py` (NEW)

```python
"""Build profile system for persona-based observability."""

from enum import Enum
from typing import Dict, Any


class BuildProfile(Enum):
    """Build profiles for different user personas."""
    WRITER = "writer"
    THEME_DEV = "theme-dev"
    DEVELOPER = "dev"
    
    @classmethod
    def from_string(cls, value: str) -> 'BuildProfile':
        """Parse profile from string."""
        mapping = {
            'writer': cls.WRITER,
            'theme-dev': cls.THEME_DEV,
            'theme_dev': cls.THEME_DEV,
            'dev': cls.DEVELOPER,
            'developer': cls.DEVELOPER,
            'debug': cls.DEVELOPER,  # Alias
        }
        return mapping.get(value.lower(), cls.WRITER)
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration for this profile."""
        if self == BuildProfile.WRITER:
            return {
                'show_phase_timing': False,
                'track_memory': False,
                'enable_debug_output': False,
                'collect_metrics': False,
                'health_checks': {
                    'enabled': ['links'],  # Only critical
                    'disabled': [
                        'performance', 'cache', 'directives',
                        'rendering', 'navigation', 'menu', 'taxonomy'
                    ]
                },
                'verbose_build_stats': False,
            }
        elif self == BuildProfile.THEME_DEV:
            return {
                'show_phase_timing': True,  # Summary only
                'track_memory': False,
                'enable_debug_output': False,
                'collect_metrics': True,  # Basic timing only
                'health_checks': {
                    'enabled': [
                        'config', 'output', 'links', 'rendering',
                        'directives', 'navigation', 'menu'
                    ],
                    'disabled': ['performance', 'cache', 'taxonomy']
                },
                'verbose_build_stats': True,
            }
        else:  # DEVELOPER
            return {
                'show_phase_timing': True,
                'track_memory': True,
                'enable_debug_output': True,
                'collect_metrics': True,
                'health_checks': {
                    'enabled': 'all',
                    'disabled': []
                },
                'verbose_build_stats': True,
            }
```

#### 1.2 Update CLI to Support Profiles

**File**: `bengal/cli.py`

```python
@main.command()
@click.option('--parallel/--no-parallel', default=True, help='Enable parallel processing')
@click.option('--incremental', is_flag=True, help='Perform incremental build')
@click.option('--profile', type=click.Choice(['writer', 'theme-dev', 'dev']), 
              help='Build profile (writer=simple, theme-dev=templates, dev=full debugging)')
@click.option('--theme-dev', 'use_theme_dev', is_flag=True, 
              help='Shorthand for --profile theme-dev')
@click.option('--dev', 'use_dev', is_flag=True, 
              help='Shorthand for --profile dev (full observability)')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose output (legacy: use --dev instead)')
@click.option('--debug', is_flag=True, 
              help='Show debug output (legacy: use --dev instead)')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output - only errors')
# ... rest of existing options ...
def build(parallel, incremental, profile, use_theme_dev, use_dev, verbose, debug, quiet, ...):
    """🔨 Build the static site."""
    
    # Determine profile (priority: explicit flag > profile option > legacy flags > default)
    if use_dev or debug:
        build_profile = BuildProfile.DEVELOPER
    elif use_theme_dev:
        build_profile = BuildProfile.THEME_DEV
    elif profile:
        build_profile = BuildProfile.from_string(profile)
    elif verbose:
        # Legacy: --verbose maps to theme-dev profile
        build_profile = BuildProfile.THEME_DEV
    else:
        # Check config for default profile
        # (will implement config loading)
        build_profile = BuildProfile.WRITER  # Default
    
    # Get profile config
    profile_config = build_profile.get_config()
    
    # Configure logging based on profile
    log_level = LogLevel.DEBUG if build_profile == BuildProfile.DEVELOPER else LogLevel.WARNING
    
    configure_logging(
        level=log_level,
        log_file=log_path,
        verbose=profile_config['verbose_build_stats'],
        track_memory=profile_config['track_memory']
    )
    
    # Pass profile to build
    stats = site.build(
        parallel=parallel,
        incremental=incremental,
        profile=build_profile
    )
    
    # Display based on profile
    if not quiet:
        if build_profile == BuildProfile.WRITER:
            display_simple_build_stats(stats, output_dir=str(site.output_dir))
        else:
            display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
```

#### 1.3 Create Simple Output Display

**File**: `bengal/utils/build_stats.py`

Add new function:

```python
def display_simple_build_stats(stats: BuildStats, output_dir: str) -> None:
    """
    Display simple build statistics for writers.
    
    Clean, minimal output focused on success/errors only.
    """
    from click import style, echo
    
    # Success indicator
    if stats.error_count == 0:
        echo(style(f"\n✨ Built {stats.total_pages} pages in {stats.build_time_ms/1000:.1f}s\n", 
                  fg='green', bold=True))
    else:
        echo(style(f"\n⚠️  Built with {stats.error_count} error(s)\n", 
                  fg='yellow', bold=True))
    
    # Show critical issues only
    if stats.broken_links:
        echo(style(f"⚠️  {len(stats.broken_links)} broken links found:", fg='yellow'))
        for link in stats.broken_links[:5]:  # Show first 5
            echo(f"   • {link['source']} → {link['target']}")
        if len(stats.broken_links) > 5:
            echo(f"   ... and {len(stats.broken_links) - 5} more")
        echo()
    
    # Show template errors if any
    if stats.template_errors:
        echo(style(f"❌ {len(stats.template_errors)} template error(s):", fg='red'))
        for error in stats.template_errors[:3]:
            echo(f"   • {error.template_context.template_name}: {error.message}")
        if len(stats.template_errors) > 3:
            echo(f"   ... and {len(stats.template_errors) - 3} more")
        echo()
    
    # Output location
    echo(style("📂 Output:", fg='cyan'))
    echo(style(f"   ↪ {output_dir}", fg='cyan'))
```

### Phase 2: Conditional Features (1.5 hours)

#### 2.1 Make Debug Output Conditional

**File**: `bengal/rendering/api_doc_enhancer.py`

```python
def enhance(self, html: str, page_type: str = None) -> str:
    """Enhance API documentation with visual badges."""
    # ... existing code ...
    
    # Debug: Report if badges were added (only in dev mode)
    if replacements_made > 0:
        from bengal.utils.profile import should_show_debug
        if should_show_debug():  # Only show in dev profile
            import sys
            print(f"[APIDocEnhancer] Made {replacements_made} badge replacements", file=sys.stderr)
```

**File**: `bengal/rendering/pipeline.py`

```python
# Line 150-154 - make conditional
if enhancer.should_enhance(page_type):
    before_enhancement = page.parsed_ast
    page.parsed_ast = enhancer.enhance(page.parsed_ast, page_type)
    
    # Debug output only in dev mode
    from bengal.utils.profile import should_show_debug
    if should_show_debug() and '@property' in before_enhancement and 'page.md' in str(page.source_path):
        import sys
        print(f"[Pipeline] Enhanced {page.source_path}:", file=sys.stderr)
        # ... rest of debug output
```

#### 2.2 Make Health Checks Profile-Aware

**File**: `bengal/health/health_check.py`

```python
def run(self, build_stats: dict = None, verbose: bool = False, 
        profile: 'BuildProfile' = None) -> HealthReport:
    """Run all registered validators."""
    # ... existing code ...
    
    # Filter validators based on profile
    if profile:
        profile_config = profile.get_config()
        health_config = profile_config.get('health_checks', {})
        enabled = health_config.get('enabled', [])
        disabled = health_config.get('disabled', [])
        
        # Filter validators
        if enabled == 'all':
            validators_to_run = self.validators
        else:
            validators_to_run = [
                v for v in self.validators
                if v.name.lower().replace(' ', '_') in [e.lower() for e in enabled]
            ]
    else:
        validators_to_run = self.validators
    
    # Run filtered validators
    for validator in validators_to_run:
        # ... existing validation logic ...
```

#### 2.3 Make Metrics Collection Conditional

**File**: `bengal/orchestration/build.py`

```python
def build(self, parallel: bool = True, incremental: bool = False, 
          verbose: bool = False, profile: 'BuildProfile' = None) -> BuildStats:
    """Build the site."""
    
    # Determine if we should collect metrics
    collect_metrics = True
    if profile:
        profile_config = profile.get_config()
        collect_metrics = profile_config.get('collect_metrics', True)
    
    # Initialize performance collector only if needed
    if collect_metrics:
        from bengal.utils.performance_collector import PerformanceCollector
        collector = PerformanceCollector()
        collector.start_build()
    else:
        collector = None
    
    # ... existing build logic ...
    
    # Save metrics only if collecting
    if collector:
        stats = collector.end_build(self.stats)
        collector.save(stats)
    
    return self.stats
```

### Phase 3: Config File Support (30 minutes)

**File**: `bengal.toml` (example)

```toml
[build]
# Set default profile for all builds
# Options: "writer" (default), "theme-dev", "dev"
profile = "writer"

# Override specific profile settings
# (optional - profiles have sensible defaults)
[build.writer]
show_phase_timing = false
health_checks = ["links"]  # Only check links

[build.theme-dev]
show_phase_timing = true
health_checks = ["links", "rendering", "directives", "navigation", "menu"]

[build.dev]
# Full observability - all features enabled
track_memory = true
enable_debug_output = true
health_checks = "all"
```

**File**: `bengal/config/loader.py`

Add profile loading logic (integrate with existing config loader).

### Phase 4: Documentation & Help (30 minutes)

#### 4.1 Update CLI Help

```python
# Add helpful profile descriptions to --help
@click.option('--profile', type=click.Choice(['writer', 'theme-dev', 'dev']), 
              help='''Build profile for your workflow:
              
    writer    - Clean output, minimal noise (default)
    theme-dev - Template errors, asset details, navigation checks
    dev       - Full observability, memory profiling, debug output
              ''')
```

#### 4.2 Create Profile Guide

**File**: `docs/PROFILES.md`

Document each profile, when to use them, and what they enable.

---

## Performance Impact Analysis

### Current Overhead (All Features On)

Based on profiling:

| Feature | Overhead | Impact on 192-page build |
|---------|----------|--------------------------|
| Memory tracking (tracemalloc) | ~2-5% | +100-250ms |
| Performance collector | <1% | ~50ms |
| Health checks (all 10) | ~10-15% | +500-750ms |
| Debug output | Negligible | <10ms |
| Phase logging | Negligible | <10ms |
| **TOTAL** | **~13-21%** | **~660-1020ms** |

### Writer Profile (Minimal)

| Feature | Status | Overhead |
|---------|--------|----------|
| Memory tracking | Disabled | 0% |
| Performance collector | Disabled | 0% |
| Health checks | 1/10 enabled | ~1-2% |
| Debug output | Disabled | 0% |
| **TOTAL** | | **~1-2%** (~50-100ms) |

### Expected Speed Improvement

- **Writer mode**: ~10-20% faster (660-920ms saved on 5.3s build)
- **Theme-dev mode**: ~5-10% faster (partial health checks)
- **Dev mode**: Same as current (full observability)

**Result**: Writers get fastest builds by default, developers get full observability when they need it.

---

## Migration Path

### Backward Compatibility

1. **Existing flags work**: `--verbose`, `--debug` still function (map to profiles)
2. **Default behavior**: Writer profile (simpler than current)
3. **Opt-in**: Users can enable more features via profiles
4. **Config support**: Existing configs unchanged (new `[build.profile]` is optional)

### Communication

```
⚠️  BREAKING CHANGE (v2.0):

Default build output is now cleaner and faster!

We've introduced build profiles for different workflows:
- `bengal build` → Clean output for writers (new default)
- `bengal build --theme-dev` → Template/theme development
- `bengal build --dev` → Full debugging (old behavior)

If you prefer the old detailed output, use --dev or set:
[build]
profile = "dev"
```

---

## Testing Strategy

### Unit Tests

1. Test profile config loading
2. Test profile filtering (health checks, features)
3. Test CLI flag parsing (precedence)

### Integration Tests

1. Test writer profile produces minimal output
2. Test theme-dev profile shows template errors
3. Test dev profile shows all debug output
4. Test performance difference between profiles

### Manual Testing

1. Build small site with each profile
2. Build large site (2000 pages) with each profile
3. Verify output matches persona expectations
4. Measure performance differences

---

## Success Metrics

### Quantitative

- [ ] Writer mode is 10-20% faster than current default
- [ ] Writer mode produces <20 lines of output (vs ~200 currently)
- [ ] Dev mode has full observability (same as current)
- [ ] All existing tests pass with profile system

### Qualitative

- [ ] Writers report cleaner, less intimidating output
- [ ] Theme developers find template errors easily
- [ ] Bengal developers have full debugging power
- [ ] Documentation clearly explains profiles

---

## Future Enhancements

### Phase 5 (Future)

1. **Custom profiles**: Let users define their own profiles in config
2. **Profile templates**: Pre-made profiles for common workflows (CI/CD, production, staging)
3. **Auto-detection**: Detect CI environment and use appropriate profile
4. **Interactive setup**: `bengal init --profile writer` to configure project
5. **Profile switching**: `bengal serve --watch --profile theme-dev` for development

---

## Summary

This design:

1. ✅ **Solves the noise problem**: Writers get clean, minimal output by default
2. ✅ **Improves performance**: Writer mode is ~10-20% faster
3. ✅ **Maintains power**: Developers still have full observability when needed
4. ✅ **Backward compatible**: Existing flags and configs work
5. ✅ **Discoverable**: Clear help and documentation for each profile
6. ✅ **Flexible**: Config and CLI flags allow customization

**Recommended Action**: Proceed with implementation in 4 phases (~4.5 hours total).

---

## Implementation Checklist

- [ ] Phase 1: Profile system and CLI (2h)
- [ ] Phase 2: Conditional features (1.5h)
- [ ] Phase 3: Config support (30m)
- [ ] Phase 4: Documentation (30m)
- [ ] Testing (1h)
- [ ] Migration guide (30m)

**Total Estimated Time**: ~6 hours

