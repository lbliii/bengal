# Health Check UX: Deep Signal-to-Noise Analysis
**Date:** October 4, 2025  
**Status:** Critical UX Research

## User Feedback

> "I don't necessarily care that we checked taxonomy, links, cache integrity, performance and that they all passed. I really only care about what didn't pass or what may need my attention."

**100% correct.** The current output has too much noise.

## Current Output Analysis

### Example: Successful Build
```
🏥 Health Check Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Configuration        2 check(s) passed      ❌ NOISE
✅ Output               4 check(s) passed      ❌ NOISE
✅ Rendering            4 check(s) passed      ❌ NOISE
⚠️ Directives           3 warning(s)           ✅ SIGNAL!
   • 8 directive(s) may have fence nesting issues
   • 22 directive(s) could be improved
   • 11 page(s) have heavy directive usage
⚠️ Navigation           1 warning(s)           ✅ SIGNAL!
   • 29 page(s) have invalid breadcrumb trails
⚠️ Navigation Menus     1 warning(s)           ✅ SIGNAL!
   • Menu 'main' has 4 item(s) with potentially broken links
ℹ️ Taxonomies           3 check(s) passed      ❌ NOISE
✅ Links                1 check(s) passed      ❌ NOISE
ℹ️ Cache Integrity      4 check(s) passed      ❌ NOISE
✅ Performance          3 check(s) passed      ❌ NOISE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 26 passed, 5 warnings, 0 errors      ✅ SIGNAL!
Build Quality: 90% (Good)
```

**Signal-to-Noise Ratio: 4 lines of signal / 14 lines total = 29% signal**

This is terrible! 71% noise.

## Signal Classification

### 🔴 **ALWAYS SHOW** (Critical - User must act)
- **Errors**: Build failures, broken config, missing files
- **Warnings**: Potential issues that may cause problems
- **Summary line**: Quick overview of health

### 🟡 **CONTEXTUAL** (Show only when relevant)
- **First-time success**: Show once to confirm health checks are working
- **After fixing issue**: Show success for that specific validator
- **Verbose mode**: Show everything on request
- **CI/CD mode**: Show all checks for audit trail

### 🟢 **NEVER SHOW** (By default)
- Individual "X passed" lines when nothing is wrong
- Validators with no issues found
- Info messages about normal operation

## Industry Best Practices

### ESLint
```bash
# ✅ No output when clean
$ eslint src/
$ 

# ⚠️ Only shows problems
$ eslint src/
src/app.js
  12:5  warning  'foo' is defined but never used  no-unused-vars
  45:3  error    'bar' is not defined             no-undef
```

### Prettier
```bash
# ✅ Silent when formatted
$ prettier --check src/
$ 

# ❌ Only shows when action needed
$ prettier --check src/
Checking formatting...
[warn] src/app.js
[warn] Code style issues found. Run with --write to fix.
```

### TypeScript
```bash
# ✅ Minimal output when successful
$ tsc
$

# ❌ Only shows errors
$ tsc
src/app.ts:12:5 - error TS2304: Cannot find name 'foo'.
```

### pytest
```bash
# ✅ Quiet mode (default for CI)
$ pytest -q
......                                               [100%]
6 passed in 0.15s

# 📊 Verbose mode (opt-in)
$ pytest -v
test_feature.py::test_one PASSED
test_feature.py::test_two PASSED
...
```

### GitHub Actions
```yaml
# ✅ Collapsed by default when passing
✓ Run tests (2s)

# ❌ Expanded when failing  
✗ Run tests (5s)
  Error: Test failed at line 42
  Expected: true
  Received: false
```

## Proposed Display Modes

### Mode 1: **QUIET** (Default - Problems Only)

**When everything passes:**
```
✓ Build complete. All health checks passed.
```

**When there are problems:**
```
⚠️ 3 warnings found:

Directives:
  • 8 directive(s) may have fence nesting issues
    💡 Use 4+ backticks for directive fences with code blocks

Navigation:
  • 29 page(s) have invalid breadcrumb trails
    💡 Check section hierarchy and index pages

Navigation Menus:
  • Menu 'main' has 4 broken links: /docs/, /examples/, /blog/
    💡 Create these pages or update menu URLs

Build Quality: 90% (Good) · 26 passed, 3 warnings, 0 errors
```

**Signal-to-Noise: 100% signal!**

### Mode 2: **NORMAL** (Current - Show Summary)

```
🏥 Health Checks: 26 passed, 3 warnings, 0 errors

⚠️ Directives (3 warnings)
⚠️ Navigation (1 warning)
⚠️ Navigation Menus (1 warning)

Build Quality: 90% (Good)

💡 Use --health-check for full report
```

**Signal-to-Noise: ~60% signal**

### Mode 3: **VERBOSE** (Full Audit Trail)

Current output with all validators shown.

**Signal-to-Noise: 29% signal** (but that's OK in verbose mode)

### Mode 4: **CI/CD** (Machine-Readable + Audit)

```
::group::Health Check Report
✅ Configuration: 2 passed
✅ Output: 4 passed
✅ Rendering: 4 passed
⚠️ Directives: 3 warnings
  - Fence nesting issues: 8 directives
  - Suboptimal usage: 22 directives
  - Heavy usage: 11 pages
⚠️ Navigation: 1 warning
  - Invalid breadcrumbs: 29 pages
⚠️ Navigation Menus: 1 warning
  - Broken links: 4 items
✅ Taxonomies: 3 passed
✅ Links: 1 passed
ℹ️ Cache: 4 passed
✅ Performance: 3 passed
::endgroup::

::notice::Build Quality: 90% (Good)
::warning::3 warnings found - review before deploying
```

## Actionability Analysis

### Current Output - Line by Line

| Line | Type | Actionable? | Reason |
|------|------|-------------|---------|
| `✅ Configuration 2 check(s) passed` | SUCCESS | ❌ No | If it passed, user doesn't need to know |
| `✅ Output 4 check(s) passed` | SUCCESS | ❌ No | Ditto |
| `✅ Rendering 4 check(s) passed` | SUCCESS | ❌ No | Ditto |
| `⚠️ Directives 3 warning(s)` | WARNING | ✅ **YES** | User should review directives |
| `• 8 directives may have fence nesting issues` | WARNING | ✅ **YES** | Specific problem to fix |
| `💡 Use 4+ backticks...` | RECOMMENDATION | ✅ **YES** | Tells user how to fix |
| `- kitchen-sink.md:159` | DETAIL | ✅ **YES** | Exact location |
| `⚠️ Navigation 1 warning(s)` | WARNING | ✅ **YES** | Potential navigation issue |
| `• 29 pages have invalid breadcrumbs` | WARNING | ⚠️ Maybe | Depends on if user cares about breadcrumbs |
| `⚠️ Navigation Menus 1 warning(s)` | WARNING | ✅ **YES** | Broken menu links affect UX |
| `ℹ️ Taxonomies 3 check(s) passed` | SUCCESS | ❌ No | Not actionable |
| `✅ Links 1 check(s) passed` | SUCCESS | ❌ No | Not actionable |
| `ℹ️ Cache Integrity 4 check(s) passed` | SUCCESS | ❌ No | Not actionable |
| `✅ Performance 3 check(s) passed` | SUCCESS | ❌ No | Not actionable |
| `Summary: 26 passed, 5 warnings, 0 errors` | SUMMARY | ✅ **YES** | Quick status check |
| `Build Quality: 90% (Good)` | METRIC | ✅ **YES** | Overall quality indicator |

**Actionability Score: 9/16 lines (56%)** - But 7 lines are pure noise!

## Severity-Based Filtering

### Critical Hierarchy

1. **🔴 ERRORS** → Always show, build should fail
   - Broken config
   - Missing required files
   - Rendering failures
   - Broken internal links

2. **🟡 WARNINGS** → Always show, user should review
   - Potential issues (broken menu links)
   - Performance concerns
   - Questionable patterns
   - Missing recommended content

3. **ℹ️ INFO** → Contextual (show first time, or when relevant)
   - "No menus defined" when template uses menus
   - "Cache disabled" in development
   - "New feature available"

4. **✅ SUCCESS** → Hide by default, show in verbose
   - Individual checks that passed
   - Confirmation of features working

## Context-Aware Display

### First Build (Show More)
```
✓ Health checks enabled (10 validators)
✓ Configuration valid
✓ All 57 pages rendered successfully
⚠️ Found 3 warnings - review below

[Show warnings...]

💡 Tip: Health checks run automatically. Use --no-health-check to disable.
```

### Subsequent Builds (Show Less)
```
⚠️ 3 warnings found (same as last build)

Use --health-check for details
```

### After Fixing Issues (Show Confirmation)
```
✓ All previous warnings resolved!
✓ Build quality improved: 85% → 95%
```

### Perfect Build (Minimal)
```
✓ Build complete (57 pages, 0 issues)
```

## Validator Priority Classification

### Tier 1: **USER-CRITICAL** (Always show if problems)
- ❌ **OutputValidator**: Broken pages, missing assets
- ❌ **MenuValidator**: Broken navigation
- ❌ **LinkValidator**: Broken links (internal)
- ❌ **ConfigValidator**: Invalid configuration

**Impact:** Site doesn't work correctly for end users

### Tier 2: **AUTHOR-IMPORTANT** (Show warnings)
- ⚠️ **NavigationValidator**: Breadcrumbs, pagination
- ⚠️ **DirectiveValidator**: Syntax issues, performance
- ⚠️ **RenderingValidator**: Template issues

**Impact:** Author experience degraded, potential future problems

### Tier 3: **DEVELOPER-INFO** (Show in verbose/CI only)
- ℹ️ **TaxonomyValidator**: Tag usage, archive pages
- ℹ️ **CacheValidator**: Cache integrity, staleness
- ℹ️ **PerformanceValidator**: Build metrics

**Impact:** Good to know, but not urgent

## Recommended Implementation

### Default Mode: **PROBLEMS-ONLY**

```python
def format_console(self, mode: str = "auto") -> str:
    """
    Format report for console output.
    
    Args:
        mode: "quiet" | "normal" | "verbose" | "auto"
              auto = quiet if no problems, normal if warnings
    """
    
    # Auto mode: intelligent defaults
    if mode == "auto":
        if self.total_errors > 0:
            mode = "normal"  # Show context
        elif self.total_warnings > 0:
            mode = "normal"  # Show warnings
        else:
            mode = "quiet"   # Just success message
    
    if mode == "quiet":
        return self._format_quiet()
    elif mode == "verbose":
        return self._format_verbose()
    else:
        return self._format_normal()

def _format_quiet(self) -> str:
    """Minimal output - problems only."""
    if not self.has_problems():
        return "✓ Build complete. All health checks passed.\n"
    
    lines = []
    
    # Show only validators with problems
    for vr in self.validator_reports:
        if not vr.has_problems:
            continue
        
        # Show warnings/errors
        for result in vr.results:
            if result.is_problem():
                lines.append(f"⚠️ {vr.validator_name}: {result.message}")
                if result.recommendation:
                    lines.append(f"   💡 {result.recommendation}")
    
    # Summary
    lines.append(f"\nBuild Quality: {self.build_quality_score()}% · {self.total_warnings} warnings")
    
    return "\n".join(lines)
```

### CLI Flags

```bash
# Default: auto-detect
bengal build

# Explicit modes
bengal build --health-check=quiet     # Minimal
bengal build --health-check=normal    # Summary
bengal build --health-check=verbose   # Full report
bengal build --no-health-check        # Skip entirely

# CI mode
bengal build --ci   # Implies verbose health checks
```

## Progressive Disclosure

### Level 1: One-Line Summary (Always)
```
✓ Build complete (90% quality, 3 warnings)
```

### Level 2: Problem List (If warnings/errors)
```
⚠️ 3 warnings:
  • Directives: 8 fence nesting issues
  • Navigation: 29 invalid breadcrumbs
  • Menus: 4 broken links
```

### Level 3: Full Details (Verbose flag)
```
[Current full output]
```

### Level 4: JSON Export (CI/automation)
```json
{
  "quality_score": 90,
  "warnings": 3,
  "errors": 0,
  "details": [...]
}
```

## Comparison: Before vs After

### BEFORE (Current - 14 lines)
```
✅ Configuration        2 check(s) passed
✅ Output               4 check(s) passed
✅ Rendering            4 check(s) passed
⚠️ Directives           3 warning(s)
   • 8 fence nesting issues
   • 22 could be improved
   • 11 heavy usage
⚠️ Navigation           1 warning(s)
   • 29 invalid breadcrumbs
⚠️ Menus                1 warning(s)
   • 4 broken links
ℹ️ Taxonomies           3 check(s) passed
✅ Links                1 check(s) passed
ℹ️ Cache Integrity      4 check(s) passed
✅ Performance          3 check(s) passed
Summary: 26 passed, 5 warnings, 0 errors
```

### AFTER (Proposed - 6 lines)
```
⚠️ 3 issues found:

• Directives: 8 fence nesting issues (kitchen-sink.md +2 more)
• Navigation: 29 invalid breadcrumbs
• Menus: 4 broken links (/docs/, /examples/, /blog/)

Build quality: 90% · Run 'bengal health-check --verbose' for details
```

**Reduction: 14 → 6 lines (57% less noise)**

## Conclusion

### Immediate Actions

1. **Change default to "quiet" mode** - Only show problems
2. **Add `--health-check` flag** - Make verbose opt-in
3. **Fix INFO display bug** - So quiet mode can surface important info when needed
4. **Improve summary line** - Make it actually useful

### Medium-Term Actions

1. **Add context awareness** - Show more on first build, less on subsequent
2. **Progressive disclosure** - Expand for details on demand
3. **Tier validators** - Prioritize user-critical over developer-info
4. **Smart filtering** - Hide noisy warnings (like breadcrumbs)

### Metrics to Track

- **Actionability rate**: % of lines that lead to user action
- **False positive rate**: % of warnings user ignores
- **Time to fix**: How long until user addresses warnings
- **User satisfaction**: Survey feedback on health check usefulness

## Recommended Settings

```toml
[health_check]
# Display mode: "quiet" | "normal" | "verbose" | "auto"
mode = "auto"  # quiet when clean, normal when warnings

# Verbosity by environment
verbose_in_ci = true
quiet_in_dev = true

# Validator tiers to show by default
show_tiers = ["user-critical", "author-important"]

# Hide validators that always pass
hide_clean_validators = true

# Progressive disclosure
show_details_count = 3  # Show first 3 details, then "... X more"
```

---

**Bottom Line:** Show problems, hide success. Let users opt-in to verbose if they want audit trails.

