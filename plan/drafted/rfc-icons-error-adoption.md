# RFC: Icons Resolver Debug Logging

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/icons/resolver.py`  
**Confidence**: 95% 🟢 (all claims verified via direct source inspection)  
**Priority**: P3 (Low) — Icons have graceful fallback; callers already log T010 warnings  
**Estimated Effort**: 10-15 minutes (single dev)

---

## Executive Summary

The `bengal/icons/resolver.py` module is a **pure utility** that resolves icons and returns content or `None`. By design, it has no error system integration — error handling is delegated to callers who have the context to make appropriate decisions.

**Current architecture** (working correctly):

| Layer | Responsibility | Status |
|-------|---------------|--------|
| `resolver.py` | Resolve icons, return content or `None` | ✅ Working |
| Callers (template functions, directives, plugins) | Log warnings with T010, searched paths, hints | ✅ Working |

**The gap**: `resolver.py` has zero debug logging, making it difficult to troubleshoot OSError failures during file I/O.

**Recommendation**: Add debug-level logging to `resolver.py` for OSError handling and icon-not-found cases. This is the only change needed.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Current State Evidence](#current-state-evidence)
3. [The Actual Gap](#the-actual-gap)
4. [Proposed Changes](#proposed-changes)
5. [Implementation](#implementation)
6. [Success Criteria](#success-criteria)
7. [Risks and Mitigations](#risks-and-mitigations)

---

## Architecture Overview

### Design Philosophy

The icons system follows **separation of concerns**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CALLERS (have context for error decisions)                             │
│  ├── bengal/rendering/template_functions/icons.py                       │
│  │   ✅ Logs warning with T010, searched paths, hints                   │
│  │   ✅ Deduplicates warnings per icon name                             │
│  ├── bengal/directives/icon.py                                          │
│  │   ✅ Logs warning with T010, searched paths, hints                   │
│  │   ✅ Renders fallback ❓ placeholder                                  │
│  └── bengal/rendering/plugins/inline_icon.py                            │
│      ✅ Logs warning with T010, searched paths, hints                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RESOLVER (pure utility, context-free)                                  │
│  bengal/icons/resolver.py                                               │
│  ✅ Returns SVG content or None                                         │
│  ✅ Provides get_search_paths() for caller error messages               │
│  ✅ Thread-safe caching                                                 │
│  ❌ No debug logging for troubleshooting                                │
└─────────────────────────────────────────────────────────────────────────┘
```

This is the **correct design**:
- The resolver doesn't know if it's being called for a strict-mode build, a conditional template, or a dev server preview
- Callers have that context and can make appropriate error decisions
- T010 warnings are already logged by all callers with full context

### Why This RFC Is Focused

Previous versions of this RFC incorrectly claimed:
- ❌ "T010 is never used" — **False**: Used by 3+ callers
- ❌ "No error codes used" — **False**: Callers log with `ErrorCode.T010.name`
- ❌ "No logging" — **Misleading**: Callers log warnings; only resolver lacks logging

The only actual gap is **debug logging in the resolver itself**.

---

## Current State Evidence

### T010 Is Actively Used by Callers

**File**: `bengal/rendering/template_functions/icons.py:179-188`

```python
# Warn if icon not found (deduplicated per icon name)
if not svg_html and name not in _warned_icons:
    _warned_icons.add(name)
    logger.warning(
        "icon_not_found",
        icon=name,
        code=ErrorCode.T010.name,
        searched=[str(p) for p in icon_resolver.get_search_paths()],
        hint=f"Add to theme: themes/{{theme}}/assets/icons/{name}.svg",
    )
```

**File**: `bengal/directives/icon.py:137-144`

```python
if svg_content is None:
    logger.warning(
        "icon_not_found",
        icon=name,
        code=ErrorCode.T010.name,
        searched=[str(p) for p in icon_resolver.get_search_paths()],
        hint=f"Add to theme: themes/{{theme}}/assets/icons/{name}.svg",
    )
```

**File**: `bengal/rendering/plugins/inline_icon.py:156-159`

```python
logger.warning(
    "icon_not_found",
    ...
    code=ErrorCode.T010.name,
)
```

**Integration test**: `tests/integration/test_theme_icons.py:207-238` verifies T010 warnings work.

### Resolver Has No Logging

**File**: `bengal/icons/resolver.py`

- 0 imports from `bengal.utils.logger`
- 0 logging calls
- Silent `except OSError: continue` and `except OSError: pass` patterns

**Silent failure points**:

| Location | Trigger | Current Behavior |
|----------|---------|------------------|
| `resolver.py:151-152` | `OSError` on file read | `continue` (no log) |
| `resolver.py:154-156` | Icon not found | `return None` (no log) |
| `resolver.py:244-245` | `OSError` on preload | `pass` (no log) |

---

## The Actual Gap

### Problem: No Debug Visibility in Resolver

When troubleshooting icon issues, developers may need to understand:
1. Which search paths were checked
2. Whether an `OSError` occurred (permissions, encoding, etc.)
3. Whether the icon was checked at all vs. served from cache

**Current behavior**: Only callers log at `warning` level. There's no way to see resolver internals without adding breakpoints.

**Proposed behavior**: Add `debug`-level logging to resolver for:
- OSError during file reads
- Icon not found after exhausting search paths
- (Optional) Cache hits/misses for performance debugging

### What's NOT a Gap

| Not a Gap | Reason |
|-----------|--------|
| T010 not used | ✅ Used by all callers |
| No warnings logged | ✅ Callers log warnings |
| No error session recording | ✅ Callers could add this; not resolver's job |
| No investigation helpers | ✅ Callers include searched paths and hints |

---

## Proposed Changes

### Add Debug Logging to Resolver

**File**: `bengal/icons/resolver.py`

**Change 1**: Add logger import

```python
# At top of file, after existing imports
from bengal.utils.logger import get_logger

logger = get_logger(__name__)
```

**Change 2**: Log OSError in `load_icon()`

```python
# In load_icon(), line ~151
except OSError as e:
    logger.debug(
        "icon_read_error",
        icon=name,
        path=str(icon_path),
        error=str(e),
    )
    continue
```

**Change 3**: Log icon-not-found at debug level

```python
# After search loop exhausted, before return None
logger.debug(
    "icon_not_found_in_resolver",
    icon=name,
    search_paths=[str(p) for p in search_paths],
)
with _icon_lock:
    _not_found_cache.add(name)
return None
```

**Change 4**: Log OSError in `_preload_all_icons()`

```python
# In _preload_all_icons(), line ~244
except OSError as e:
    logger.debug(
        "icon_preload_error",
        icon=name,
        path=str(icon_path),
        error=str(e),
    )
```

---

## Implementation

### Single Phase: Add Debug Logging (10-15 min)

| Task | Time | Priority |
|------|------|----------|
| Add logger import | 1 min | P2 |
| Add debug logging to `load_icon()` | 5 min | P2 |
| Add debug logging to `_preload_all_icons()` | 3 min | P3 |
| Run existing tests | 2 min | P2 |

**Total**: ~10-15 minutes

### Files Changed

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `bengal/icons/resolver.py` | Add logger + debug logging | +15 |

---

## Success Criteria

### Must Have

- [ ] Logger imported in `resolver.py`
- [ ] Debug logging added for OSError during file reads
- [ ] Debug logging added for icon-not-found (resolver level)
- [ ] All existing tests pass
- [ ] No changes to function signatures (backward compatible)

### Should Have

- [ ] Search paths included in debug log for not-found
- [ ] Error details included for OSError cases

### Not In Scope

- [ ] ~~Error session recording~~ — Callers' responsibility
- [ ] ~~T010 usage~~ — Already handled by callers
- [ ] ~~Warning-level logging~~ — Callers already log warnings

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance impact from logging | Very Low | Low | Debug level only; structured logging is cheap |
| Log noise | Very Low | Low | Debug level not shown by default |
| Test failures | Very Low | Low | No functional changes; logging only |

---

## Design Rationale

### Why Only Debug Logging?

1. **Callers already log warnings** — Adding warning logging to resolver would cause duplicate warnings
2. **Separation of concerns** — Resolver doesn't know the context (strict mode, conditional rendering, etc.)
3. **Debug is for developers** — OSError details are useful for debugging, not end-user warnings

### Why Not Add `record_failures` Parameter?

Previous RFC versions proposed adding a `record_failures: bool = False` parameter. This was rejected because:

1. **Callers already handle error reporting** — They log with T010, searched paths, and hints
2. **Would duplicate responsibility** — Error handling would exist in two places
3. **Resolver is context-free** — It doesn't know what the "right" error message is
4. **API surface increase** — Adds complexity for no clear benefit

### Comparison with Fonts Package

The fonts package (`bengal/fonts/downloader.py`) DOES use `record_error()` because:
- Font downloads are **external API calls** (Google Fonts)
- Failures indicate configuration problems or network issues
- There's no "caller" that can better handle the error

Icons are different:
- Icon resolution is **local file lookup**
- Missing icons are often intentional (conditional rendering)
- Callers have context to decide if it's an error

---

## References

- `bengal/icons/resolver.py:143-156,238-245` — Silent failure points
- `bengal/rendering/template_functions/icons.py:179-188` — Caller T010 usage
- `bengal/directives/icon.py:137-144` — Caller T010 usage
- `bengal/rendering/plugins/inline_icon.py:156-159` — Caller T010 usage
- `tests/integration/test_theme_icons.py:207-238` — T010 warning tests
- `bengal/errors/codes.py:212` — `T010 = "icon_not_found"`
