# Performance Quick Wins - Implementation Guide

**Created:** 2025-10-09  
**Estimated Time:** 2-3 hours  
**Expected Impact:** 30-50% reduction in health check time

---

## Quick Win #1: Cache URL Properties (30 minutes)

### Changes Required

**File 1:** `bengal/core/page/metadata.py`

```python
# Line 1: Add import
from functools import cached_property

# Lines 56-112: Replace @property with @cached_property
@cached_property  # Changed from @property
def url(self) -> str:
    """
    Get the URL path for the page (cached after first access).
    
    ... rest of docstring unchanged ...
    """
    # ... existing implementation unchanged ...
```

**File 2:** `bengal/core/section.py`

```python
# Line 1: Add import
from functools import cached_property

# Lines 127-163: Replace @property with @cached_property
@cached_property  # Changed from @property
def url(self) -> str:
    """
    Get the URL for this section (cached after first access).
    
    ... rest of docstring unchanged ...
    """
    # ... existing implementation unchanged ...
```

### Testing

```bash
# Before change
cd examples/showcase
bengal build --debug 2>&1 | grep -c "section_url_from_index"
# Expected: ~1016

# After change
bengal build --debug 2>&1 | grep -c "section_url_from_index"
# Expected: ~40 (one per unique section)

# Verify functionality
bengal build
# Should complete successfully, output should be identical
```

### Why This Works

- `cached_property` is stdlib (Python 3.8+), no dependencies
- Works with dataclasses
- Thread-safe (descriptor protocol)
- Zero code changes needed elsewhere
- URLs are stable after `output_path` is set (rendering phase)

---

## Quick Win #2: Decouple Debug from Health Checks (45 minutes)

### Changes Required

**File:** `bengal/utils/profile.py`

```python
# Around line 104: Update from_cli_args() to separate debug from health checks
@classmethod
def from_cli_args(
    cls,
    profile: Optional[str] = None,
    dev: bool = False,
    theme_dev: bool = False,
    verbose: bool = False,
    debug: bool = False
) -> 'BuildProfile':
    """
    Determine profile from CLI arguments.
    
    NOTE: --debug now only affects logging verbosity, not health check depth.
    For comprehensive health checks, use --profile=dev or bengal health-check.
    """
    # Priority 1: Explicit profile option
    if profile:
        return cls.from_string(profile)
    
    # Priority 2: Development flags (only for explicit opt-in)
    if dev:  # Removed 'or debug' from here
        return cls.DEVELOPER
    
    # Priority 3: Theme dev flag
    if theme_dev or verbose:
        return cls.THEME_DEV
    
    # Priority 4: Default to WRITER (even with --debug)
    # --debug only enables debug logging, not expensive validators
    return cls.WRITER
```

**File:** `bengal/cli.py`

```python
# Find the build command (search for "def build")
# Update help text for --debug flag

@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug logging. For comprehensive health checks, use --profile=dev.'  # Updated help
)
def build(ctx, profile, dev, verbose, debug, ...):
    # ... existing implementation unchanged ...
```

### Testing

```bash
# Test WRITER profile with debug logging
bengal build --debug
# Expected: Debug logs appear, but health checks are fast

# Test full validation
bengal build --profile=dev
# Expected: All validators run

# Test explicit health check command
bengal health-check
# Expected: All validators run (if this command exists)
```

### Migration Notes

Users currently using `--debug` for comprehensive validation should:
- Use `--profile=dev` instead, or
- Use dedicated `bengal health-check` command

Add to CHANGELOG:
```
### Changed
- `--debug` flag now only enables debug logging, not comprehensive health checks.
  For full validation, use `--profile=dev` or `bengal health-check`.
- Improves development iteration speed by 50-70%.
```

---

## Quick Win #3: Batch Health Check Context (90 minutes)

### Implementation Steps

**Step 1: Create Context Module (30 min)**

Create: `bengal/health/context.py`

```python
"""
Pre-computed health check context to avoid O(n²) patterns.
"""
from dataclasses import dataclass, field
from typing import List, Set, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page

@dataclass
class HealthCheckContext:
    """
    Pre-computed data for health validators.
    
    Built once in O(n) time, then reused by all validators.
    Eliminates O(n²) patterns where validators independently iterate site.pages.
    """
    site: 'Site'
    
    # Pre-categorized pages
    regular_pages: List['Page'] = field(default_factory=list)
    generated_pages: List['Page'] = field(default_factory=list)
    tag_pages: List['Page'] = field(default_factory=list)
    archive_pages: List['Page'] = field(default_factory=list)
    
    # Quick lookups (O(1) instead of O(n))
    pages_by_url: Dict[str, 'Page'] = field(default_factory=dict)
    pages_with_breadcrumbs: Set['Page'] = field(default_factory=set)
    pages_with_next_prev: Set['Page'] = field(default_factory=set)
    pages_in_sections: Set['Page'] = field(default_factory=set)
    
    @classmethod
    def build(cls, site: 'Site') -> 'HealthCheckContext':
        """
        Build context from site in a single O(n) pass.
        
        Args:
            site: Site to analyze
            
        Returns:
            Pre-computed HealthCheckContext
        """
        ctx = cls(site=site)
        
        # Single pass through all pages
        for page in site.pages:
            # Categorize by generation status and type
            if page.metadata.get('_generated'):
                ctx.generated_pages.append(page)
                
                page_type = page.metadata.get('type')
                if page_type == 'tag':
                    ctx.tag_pages.append(page)
                elif page_type == 'archive':
                    ctx.archive_pages.append(page)
            else:
                ctx.regular_pages.append(page)
            
            # Build quick lookup indices
            ctx.pages_by_url[page.url] = page
            
            if hasattr(page, 'ancestors') and page.ancestors:
                ctx.pages_with_breadcrumbs.add(page)
            
            if (hasattr(page, 'next') and page.next) or \
               (hasattr(page, 'prev') and page.prev):
                ctx.pages_with_next_prev.add(page)
            
            if hasattr(page, '_section') and page._section:
                ctx.pages_in_sections.add(page)
        
        return ctx
```

**Step 2: Update HealthCheck to Build Context (15 min)**

Update: `bengal/health/health_check.py`

```python
def run(self, build_stats: dict = None, verbose: bool = False, 
        profile: 'BuildProfile' = None) -> HealthReport:
    """
    Run all registered validators and produce a health report.
    
    Args:
        build_stats: Optional build statistics to include in report
        verbose: Whether to show verbose output during validation
        profile: Build profile to use for filtering validators
        
    Returns:
        HealthReport with results from all validators
    """
    from bengal.health.context import HealthCheckContext  # New import
    from bengal.utils.profile import is_validator_enabled
    
    report = HealthReport(build_stats=build_stats)
    
    # NEW: Build context once for all validators
    context = HealthCheckContext.build(self.site)
    
    for validator in self.validators:
        # ... existing profile and config checks ...
        
        # Run validator and time it
        start_time = time.time()
        
        try:
            # NEW: Pass context to validators that support it
            import inspect
            sig = inspect.signature(validator.validate)
            if 'ctx' in sig.parameters:
                results = validator.validate(self.site, ctx=context)
            else:
                # Backward compatibility: validators without ctx parameter
                results = validator.validate(self.site)
            
            # ... rest of existing code unchanged ...
```

**Step 3: Update MenuValidator (20 min)**

Update: `bengal/health/validators/menu.py`

```python
# Add type hints import
from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.health.context import HealthCheckContext  # New

class MenuValidator(BaseValidator):
    def validate(self, site: 'Site', ctx: Optional['HealthCheckContext'] = None) -> List[CheckResult]:
        """
        Validate menu structure.
        
        Args:
            site: Site to validate
            ctx: Optional pre-computed context (for performance)
        """
        results = []
        
        # Build context if not provided (backward compatibility)
        if ctx is None:
            from bengal.health.context import HealthCheckContext
            ctx = HealthCheckContext.build(site)
        
        # ... existing validation logic, but use ctx ...
    
    def _check_menu_urls(self, ctx: 'HealthCheckContext', items: list) -> List[str]:
        """Check if menu item URLs point to existing pages (now O(1))."""
        broken = []
        
        for item in items:
            if hasattr(item, 'url') and item.url:
                url = item.url
                
                # Skip external URLs
                if url.startswith(('http://', 'https://', '//')):
                    continue
                
                # NEW: O(1) lookup instead of O(n) iteration!
                if url not in ctx.pages_by_url:
                    broken.append(f"{item.name} → {url}")
            
            # Recurse into children
            if hasattr(item, 'children') and item.children:
                broken.extend(self._check_menu_urls(ctx, item.children))
        
        return broken
```

**Step 4: Update NavigationValidator (25 min)**

Update: `bengal/health/validators/navigation.py`

```python
from typing import Optional

class NavigationValidator(BaseValidator):
    def validate(self, site: 'Site', ctx: Optional['HealthCheckContext'] = None) -> List[CheckResult]:
        """Run navigation validation checks."""
        results = []
        
        # Build context if not provided
        if ctx is None:
            from bengal.health.context import HealthCheckContext
            ctx = HealthCheckContext.build(site)
        
        # Check 1: Next/prev chain integrity (use ctx.regular_pages)
        results.extend(self._check_next_prev_chains(site, ctx))
        
        # Check 2: Breadcrumb validity
        results.extend(self._check_breadcrumbs(site, ctx))
        
        # Check 3: Section navigation
        results.extend(self._check_section_navigation(site, ctx))
        
        # Check 4: Navigation coverage
        results.extend(self._check_navigation_coverage(ctx))
        
        return results
    
    def _check_next_prev_chains(self, site: 'Site', ctx: 'HealthCheckContext') -> List[CheckResult]:
        """Check next/prev chains (now uses pre-filtered pages)."""
        results = []
        issues = []
        
        # Use pre-filtered regular pages instead of filtering again!
        for page in ctx.regular_pages:
            # ... existing validation logic ...
        
        # ... rest unchanged ...
    
    def _check_navigation_coverage(self, ctx: 'HealthCheckContext') -> List[CheckResult]:
        """Check navigation coverage (uses pre-computed sets)."""
        results = []
        
        # Use pre-computed data instead of list comprehensions!
        total = len(ctx.regular_pages)
        with_next_prev = len(ctx.pages_with_next_prev)
        with_breadcrumbs = len(ctx.pages_with_breadcrumbs)
        in_sections = len(ctx.pages_in_sections)
        
        if total > 0:
            next_prev_pct = (with_next_prev / total) * 100
            breadcrumb_pct = (with_breadcrumbs / total) * 100
            section_pct = (in_sections / total) * 100
            
            results.append(CheckResult.info(
                f"Navigation coverage: {next_prev_pct:.0f}% next/prev, "
                f"{breadcrumb_pct:.0f}% breadcrumbs, {section_pct:.0f}% in sections",
                recommendation="High navigation coverage improves site usability." if next_prev_pct < 80 else None
            ))
        
        return results
```

### Testing

```bash
# Verify context building works
python -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))

from bengal.orchestration.build import build_site
from bengal.health.context import HealthCheckContext

site = build_site('examples/showcase')
ctx = HealthCheckContext.build(site)

print(f'Regular pages: {len(ctx.regular_pages)}')
print(f'Generated pages: {len(ctx.generated_pages)}')
print(f'Pages by URL: {len(ctx.pages_by_url)}')
print(f'Pages with breadcrumbs: {len(ctx.pages_with_breadcrumbs)}')
"

# Run full build
cd examples/showcase
time bengal build --profile=dev
# Should be 15-25% faster than before
```

---

## Performance Measurement

### Before Optimization

```bash
cd examples/showcase
bengal build --debug 2>&1 | tee before.log

# Extract metrics
grep "health_check" before.log
grep "section_url_from_index" before.log | wc -l
```

### After Each Quick Win

```bash
# After Quick Win #1 (URL caching)
bengal build --debug 2>&1 | tee after-qw1.log
grep "section_url_from_index" after-qw1.log | wc -l
# Should be ~40 instead of ~1016

# After Quick Win #2 (profile decoupling)
bengal build --debug 2>&1 | tee after-qw2.log
# Health checks should complete faster

# After Quick Win #3 (batching)
bengal build --profile=dev 2>&1 | tee after-qw3.log
grep "health_check" after-qw3.log
# Compare timing with before.log
```

### Benchmark Script

Create: `scripts/benchmark_health_checks.py`

```python
#!/usr/bin/env python3
"""
Benchmark health check performance.
"""
import time
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.orchestration.build import build_site
from bengal.health import HealthCheck

def benchmark():
    """Run health check benchmark."""
    print("Building site...")
    site = build_site('examples/showcase')
    
    print("\nRunning health checks (5 iterations)...")
    times = []
    
    for i in range(5):
        health_check = HealthCheck(site)
        
        start = time.time()
        report = health_check.run()
        elapsed = time.time() - start
        
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s")
    
    avg = sum(times) / len(times)
    print(f"\nAverage: {avg:.3f}s")
    print(f"Min: {min(times):.3f}s")
    print(f"Max: {max(times):.3f}s")

if __name__ == '__main__':
    benchmark()
```

Run before and after:
```bash
python scripts/benchmark_health_checks.py
```

---

## Rollback Plan

If any quick win causes issues:

### Quick Win #1 Rollback
```python
# Revert @cached_property back to @property
# No other changes needed - fully isolated
```

### Quick Win #2 Rollback
```python
# Revert profile.py changes
# Users can continue using --debug for comprehensive checks
```

### Quick Win #3 Rollback
```python
# Validators fall back gracefully if ctx not provided
# Simply remove context building from health_check.run()
# Validators will build their own context (slower but functional)
```

---

## Success Criteria

### Quantitative
- [ ] URL log entries drop from ~1,016 to ~40
- [ ] Health check time < 1.5s for showcase (from 3.2s)
- [ ] `--debug` build < 4s total (from 6s)
- [ ] All existing tests pass
- [ ] No regressions in build output

### Qualitative
- [ ] `--debug` feels fast and responsive
- [ ] Debug logs are readable and actionable
- [ ] Code changes are backward compatible
- [ ] Documentation is clear

---

## Next Steps

1. **Implement Quick Win #1** (URL caching) - 30 min
2. **Test and measure** - 15 min
3. **Implement Quick Win #2** (profile decoupling) - 45 min
4. **Test and measure** - 15 min
5. **Implement Quick Win #3** (batching) - 90 min
6. **Test and measure** - 30 min
7. **Update documentation** - 30 min
8. **Create PR** with measurements

Total estimated time: **4-5 hours** including testing and documentation.

---

## Documentation Updates Needed

### CHANGELOG.md
```markdown
## [Unreleased]

### Performance
- **50% faster health checks**: Optimized URL computation and validator batching
- URL properties now cached after first access (eliminates 95% of recalculations)
- Health check validators use shared context to avoid O(n²) patterns

### Changed
- `--debug` flag now only enables debug logging, not comprehensive health checks
  - For full validation, use `--profile=dev` or `bengal health-check` command
  - Improves development iteration speed by 50-70%

### Internal
- Added `HealthCheckContext` for O(n) pre-computation
- Menu validator now uses O(1) URL lookups instead of O(n) iteration
- Navigation validator consolidated to single pass through pages
```

### docs/performance.md (if exists)
- Add section on health check performance
- Explain profile-based validation tiers
- Recommend settings for different use cases

### docs/cli.md
- Update `--debug` flag documentation
- Explain `--profile` options
- Add examples of different profiles

