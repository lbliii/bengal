# Health Check INFO Message Display Bug
**Date:** October 4, 2025  
**Status:** Critical UX Issue Discovered

## Issue Summary

INFO-level health check messages are **completely hidden** from users in the default (non-verbose) output. This caused the menu misconfiguration to be silent.

## The Problem

When showcase site had misconfigured menus (`[menus]` instead of `[menu]`):

**What user saw:**
```
ℹ️ Navigation Menus    
```

**What should have been shown:**
```
ℹ️ Navigation Menus    
   • No navigation menus defined
     💡 Add menu configuration to bengal.toml to enable navigation menus.
```

## Root Cause

### Bug #1: Missing INFO count in status line

File: `bengal/health/report.py` lines 227-235

```python
status_line = f"{vr.status_emoji} {vr.validator_name:<20}"

if vr.error_count > 0:
    status_line += f" {vr.error_count} error(s)"
elif vr.warning_count > 0:
    status_line += f" {vr.warning_count} warning(s)"
elif vr.passed_count > 0:
    status_line += f" {vr.passed_count} check(s) passed"
# ❌ BUG: No case for info_count!

lines.append(status_line)
```

When a validator has ONLY INFO results, the status line shows just the emoji and name with no count.

### Bug #2: INFO messages hidden by default

File: `bengal/health/report.py` lines 239-240

```python
for result in vr.results:
    if result.is_problem() or verbose:  # ❌ INFO messages skipped!
        lines.append(f"   • {result.message}")
```

The `is_problem()` method only returns True for WARNING and ERROR, not INFO:

```python
def is_problem(self) -> bool:
    """Check if this is a warning or error (vs success/info)."""
    return self.status in (CheckStatus.WARNING, CheckStatus.ERROR)
```

So INFO messages are never displayed unless verbose mode is enabled.

## Impact

**Critical UX Issue:**
- Users with configuration errors get NO feedback
- Silent failures lead to confusion ("Why isn't X working?")
- Health check appears to pass when it's actually warning about issues

**Affected validators:**
- MenuValidator: "No navigation menus defined"
- TaxonomyValidator: Various info messages
- CacheValidator: Cache status info
- Any validator using `CheckResult.info()`

## The Fix

### Option 1: Always show INFO messages (RECOMMENDED)

INFO messages are important enough to show by default. They indicate missing or unusual configuration.

```python
# Line 234: Add INFO count
elif vr.info_count > 0:
    status_line += f" {vr.info_count} info"

# Lines 239-240: Show INFO messages by default
for result in vr.results:
    if result.is_problem() or result.status == CheckStatus.INFO or verbose:
        lines.append(f"   • {result.message}")
```

### Option 2: Make INFO dismissible but visible

Show INFO on first occurrence, allow user to suppress with flag:

```python
# Show INFO unless explicitly suppressed
if result.is_problem() or (result.status == CheckStatus.INFO and not quiet_mode) or verbose:
    lines.append(f"   • {result.message}")
```

### Option 3: Upgrade INFO to WARNING for critical issues

Change MenuValidator to use WARNING instead of INFO when menus are missing:

```python
# In MenuValidator
if not site.menu:
    results.append(CheckResult.warning(  # Changed from .info()
        "No navigation menus defined",
        recommendation="Add menu configuration to bengal.toml to enable navigation menus."
    ))
```

## Recommendation

**Implement Option 1 + Option 3:**

1. **Fix the report formatter** to always show INFO messages (they're important)
2. **Upgrade MenuValidator** to use WARNING when no menus are defined but templates reference them
3. **Add config validation** to catch typos like `[menus]` vs `[menu]`

This provides:
- ✅ Immediate feedback for users
- ✅ Clear error messages
- ✅ Prevention at config load time
- ✅ Defense in depth

## Test Case

To reproduce:
```bash
# 1. Misconfigure menus in bengal.toml
[[menus.main]]  # Wrong - should be [[menu.main]]
name = "Home"

# 2. Build
bengal build

# 3. Observe: No visible warning about menus!
```

Expected output after fix:
```
ℹ️ Navigation Menus     1 info
   • No navigation menus defined
     💡 Add menu configuration to bengal.toml to enable navigation menus.
```

Or even better with upgraded severity:
```
⚠️ Navigation Menus     1 warning(s)
   • No navigation menus defined
     💡 Check [menu] section in bengal.toml (note: 'menu' is singular, not 'menus')
```

## Priority

**HIGH** - This affects user experience significantly and masks configuration errors.

---

**Next Steps:**
1. Fix report.py to display INFO messages
2. Consider upgrading MenuValidator severity
3. Add tests for INFO message display
4. Review other validators for similar issues

