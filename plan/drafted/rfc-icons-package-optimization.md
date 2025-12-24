# RFC: Icons Package Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Icons (`bengal/icons/`)  
**Confidence**: 95% 🟢 (verified against source code)  
**Priority**: P4 (Very Low) — Micro-optimization with negligible real-world impact  
**Estimated Effort**: 0.5 hours

---

## Executive Summary

The `bengal/icons` package is **well-optimized**. One minor opportunity exists but has no measurable impact.

| Aspect | Status |
|--------|--------|
| Hot path (`load_icon()`) | ✅ O(1) amortized via dual caching |
| Lazy + preload modes | ✅ Optimal for dev/prod |
| Initialization (`_get_icon_search_paths`) | 🔵 O(D×P) → O(D) possible, max 20 comparisons |

**Verdict**: Production-ready. Optional fix available if touching this code for other reasons.

---

## Problem Statement

### Current Performance Characteristics

| Function | Current Complexity | Optimal Complexity | Impact |
|----------|-------------------|-------------------|--------|
| `initialize()` | O(D×P + C + N) | O(D + C + N) | Negligible |
| `load_icon()` | **O(1)** amortized | O(1) | ✅ Optimal |
| `get_available_icons()` | O(I log I) | O(I log I) | ✅ Optimal |
| `_preload_all_icons()` | O(I×S) | O(I×S) | ✅ Optimal |

**Variables**:
- `D` = Theme inheritance depth (max 5, typically 1-3)
- `P` = Number of search paths (typically 1-4)
- `I` = Total icons across all paths (10-100)
- `S` = Average SVG file size (500-5000 chars)
- `C` = Cached icons count
- `N` = Not-found cache count

### Issue: List Membership Check in `_get_icon_search_paths`

**Location**: `bengal/icons/resolver.py:64-96`

**Current Implementation**:

```python
def _get_icon_search_paths(site: Site) -> list[Path]:
    paths: list[Path] = []

    for assets_dir in reversed(site._get_theme_assets_chain()):  # O(D) iterations
        icons_dir = assets_dir / "icons"
        if icons_dir.exists() and icons_dir not in paths:  # O(P) list scan!
            paths.append(icons_dir)
    # ...
```

**Problem**:
- `icons_dir not in paths` is O(P) list membership check
- Inside O(D) loop, total: O(D×P)
- With D≤5, P≤4: max 20 comparisons per initialization

**Why This Is Low Priority**:
1. Called once per site initialization, not per-icon lookup
2. D×P ≤ 20 comparisons is imperceptible
3. Hot path (`load_icon()`) is already O(1) amortized

---

## Proposed Solution

### Option A: Add Parallel Set for O(1) Deduplication (Recommended)

**Changes**: `bengal/icons/resolver.py:73-80`

```python
def _get_icon_search_paths(site: Site) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()  # O(1) membership check

    for assets_dir in reversed(site._get_theme_assets_chain()):
        icons_dir = assets_dir / "icons"
        if icons_dir.exists() and icons_dir not in seen:  # O(1) instead of O(P)
            paths.append(icons_dir)
            seen.add(icons_dir)
    # ... rest unchanged ...
```

**Complexity**: O(D×P) → O(D)

**Trade-offs**:
- ✅ Matches pattern already used in `get_available_icons()` (line 165) and `_preload_all_icons()` (line 198)
- ✅ Minimal code change (3 lines)
- ⚠️ Additional set object (~4 Path references, negligible)

### Option A2: Use dict.fromkeys (Alternative)

```python
def _get_icon_search_paths(site: Site) -> list[Path]:
    candidates = [
        assets_dir / "icons"
        for assets_dir in reversed(site._get_theme_assets_chain())
    ]
    # dict.fromkeys preserves order, deduplicates in O(n)
    return list(dict.fromkeys(p for p in candidates if p.exists()))
```

**Trade-offs**:
- ✅ Single-expression, no explicit set
- ⚠️ Less readable than Option A
- ⚠️ Requires additional handling for `extend_defaults` logic

### Option B: No Action (Acceptable)

With D≤5 and P≤4, max 20 comparisons occur once per site build. Defer indefinitely.

---

## Architecture Highlights (Already Optimal)

### 1. Dual Caching Strategy

```python
# resolver.py:37-40
_icon_cache: dict[str, str] = {}      # Found icons
_not_found_cache: set[str] = set()    # Avoid repeated disk checks
```

- Cache hit: O(1) dict lookup
- Not-found hit: O(1) set lookup  
- Prevents repeated filesystem I/O for missing icons

### 2. Lazy Loading with Preload Option

```python
# resolver.py:43-61
def initialize(site: Site, preload: bool = False) -> None:
    # ...
    if preload:
        _preload_all_icons()  # Production: load all upfront
```

- Development: Load on-demand for fast startup
- Production: Preload all icons once, O(1) access thereafter

### 3. O(1) Hot Path

```python
# resolver.py:106-124
def load_icon(name: str) -> str | None:
    if name in _icon_cache:       # O(1)
        return _icon_cache[name]
    if name in _not_found_cache:  # O(1)
        return None
    # ... cold path: O(P×S) first access only
```

### 4. Consistent Set-Based Deduplication (Elsewhere)

The codebase already uses sets for O(1) deduplication in related functions:

```python
# resolver.py:165-176 — get_available_icons()
seen: set[str] = set()
for icons_dir in search_paths:
    for icon_path in sorted(icons_dir.glob("*.svg")):
        if name not in seen:
            icons.append(name)
            seen.add(name)

# resolver.py:198-207 — _preload_all_icons()
seen: set[str] = set()
for icons_dir in _search_paths:
    for icon_path in icons_dir.glob("*.svg"):
        if name not in seen:
            _icon_cache[name] = icon_path.read_text(encoding="utf-8")
            seen.add(name)
```

The `_get_icon_search_paths()` function is the only place where list membership is used instead of a set—an inconsistency rather than a design choice.

---

## Implementation Plan

### If Applying Fix (~15 minutes)

| Step | Action | Location |
|------|--------|----------|
| 1 | Add `seen: set[Path] = set()` | `resolver.py:73` |
| 2 | Change `icons_dir not in paths` → `icons_dir not in seen` | `resolver.py:79` |
| 3 | Add `seen.add(icons_dir)` after `paths.append(icons_dir)` | `resolver.py:80` |
| 4 | Repeat for `default_icons not in paths` | `resolver.py:93` |
| 5 | Run tests | `uv run pytest tests/unit/icons/ -v` |

### Recommended Approach

Apply only when modifying `resolver.py` for other reasons. The current implementation is production-ready.

---

## Testing Strategy

### Existing Coverage

Comprehensive tests exist in `tests/unit/icons/test_resolver.py` (333 lines):

```bash
uv run pytest tests/unit/icons/ -v
```

| Test Class | Coverage |
|------------|----------|
| `TestIconResolutionOrder` | Search path priority, fallthrough, first-match-wins |
| `TestIconCaching` | Cache hit, not-found cache, clear_cache |
| `TestGetAvailableIcons` | Discovery, deduplication |
| `TestPreloading` | `_preload_all_icons()` behavior |
| `TestInitializeWithSite` | `initialize()` with mock Site |

### No New Tests Required

The optimization preserves external behavior. Existing tests validate deduplication semantics.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Path objects not hashable | Very Low | Low | Python's `Path` is hashable by default |
| Behavior change | None | None | Deduplication logic unchanged |

---

## Decision Matrix

| Option | Effort | Benefit | Risk | Recommendation |
|--------|--------|---------|------|----------------|
| **A: Add parallel set** | 15 min | O(D×P)→O(D), pattern consistency | None | ✅ When touching this file |
| **A2: dict.fromkeys** | 15 min | O(D×P)→O(D) | Less readable | ⚪ Not recommended |
| **B: No action** | 0 | None | None | ✅ Acceptable default |

---

## Appendix A: Complete Complexity Analysis

### Function-by-Function Breakdown

| Function | Time | Space | Notes |
|----------|------|-------|-------|
| `initialize()` | O(D×P) | O(P) | O(I×S) with preload |
| `_get_icon_search_paths()` | O(D×P) | O(P) | ⚠️ Minor optimization available |
| `load_icon()` | **O(1)** amortized | O(S) | ✅ Well-optimized |
| `get_search_paths()` | O(P) | O(P) | List copy |
| `get_available_icons()` | O(I log I) | O(I) | Sorting overhead |
| `clear_cache()` | O(C+N) | O(1) | Cache clearing |
| `_preload_all_icons()` | O(I×S) | O(I×S) | File I/O bound |
| `is_initialized()` | O(1) | O(1) | Boolean return |

### Performance Profile

```
Initialization (typical):  O(D) ≈ O(1)   [D ≤ 5 constant]
Icon lookup (warm):        O(1)          [cached]
Icon lookup (cold):        O(P×S)        [first access only]
Full preload:              O(I×S)        [one-time cost]
```

---

## Appendix B: Source References

| Location | Description |
|----------|-------------|
| `resolver.py:37-40` | Cache data structures |
| `resolver.py:43-61` | `initialize()` with preload option |
| `resolver.py:64-96` | `_get_icon_search_paths()` with list membership ⚠️ |
| `resolver.py:106-140` | `load_icon()` with dual caching |
| `resolver.py:155-178` | `get_available_icons()` with set deduplication ✅ |
| `resolver.py:191-210` | `_preload_all_icons()` with set deduplication ✅ |

---

## Conclusion

The `bengal/icons` package demonstrates **excellent algorithmic design**:

| Aspect | Status |
|--------|--------|
| Hot path (`load_icon()`) | ✅ O(1) amortized |
| Caching strategy | ✅ Dual cache (found + not-found) |
| Loading modes | ✅ Lazy (dev) + preload (prod) |
| Deduplication pattern | 🔵 Inconsistent: 2/3 functions use sets, 1 uses list |

**Verdict**: 🟢 **Production-ready**

Optional fix: Apply set-based deduplication to `_get_icon_search_paths()` for pattern consistency when next modifying this file.
