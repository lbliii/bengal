# RFC: Formalize Site Runtime State & Eliminate Dynamic Attribute Injection

**Status**: Draft (Revised 2025-12-19)  
**Created**: 2025-12-19  
**Author**: AI Assistant  
**Subsystems**: `bengal/core/site/`, `bengal/rendering/`, `bengal/orchestration/`  
**Confidence**: 85% 🟢  
**Priority**: P2 (Medium)  

---

## Executive Summary

Analysis of Bengal's codebase identified **16 instances** of external code dynamically injecting private attributes onto the `Site` object, with **7 fields not yet formalized** as explicit dataclass fields. The remaining instances use `# type: ignore[attr-defined]` comments unnecessarily on **5 fields that are already formalized**.

This RFC proposes a two-phase approach:
1. **Phase A (Cleanup)**: Remove unnecessary `type: ignore` comments for already-formalized fields
2. **Phase B (Formalize)**: Add the 7 remaining fields as formal Site dataclass fields

**Key findings** (verified):
- 16 dynamic `site._*` attribute injection sites across 10 files
- 42 `type: ignore[attr-defined]` comments (some unnecessary)
- 5 fields already formalized in `Site` (cleanup needed at injection sites)
- 7 fields still need formalization

---

## Problem Statement

### Current State

Two distinct issues exist:

**Issue 1: Unnecessary `type: ignore` on Formalized Fields**

Some fields have been added to `Site` but injection sites weren't updated:

```python
# bengal/core/site/core.py:167 - Field EXISTS
_template_parser: Any = field(default=None, repr=False, init=False)

# bengal/rendering/template_functions/get_page.py:53 - Still uses type: ignore!
site._template_parser = create_markdown_parser(markdown_engine)  # type: ignore[attr-defined]
```

**Issue 2: Truly Dynamic Injections (Not Yet Formalized)**

```python
# bengal/rendering/engines/jinja.py:104-109 - No formal field exists
try:
    if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
        self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
    if not hasattr(self.site, "_asset_manifest_fallbacks_lock"):
        self.site._asset_manifest_fallbacks_lock = threading.Lock()  # type: ignore[attr-defined]
except Exception:
    pass
```

### Fields Already Formalized (Phase A Cleanup)

These fields exist in `bengal/core/site/core.py:155-167`:

| Field | Location | Status |
|-------|----------|--------|
| `_dev_menu_metadata` | `core.py:157` | ✅ Formalized, cleanup needed |
| `_affected_tags` | `core.py:159` | ✅ Formalized, cleanup needed |
| `_page_lookup_maps` | `core.py:161-163` | ✅ Formalized, cleanup needed |
| `_last_build_stats` | `core.py:165` | ✅ Formalized, cleanup needed |
| `_template_parser` | `core.py:167` | ✅ Formalized, cleanup needed |

### Fields NOT Yet Formalized (Phase B)

| Attribute | Injected By | Purpose | Type |
|-----------|-------------|---------|------|
| `_asset_manifest_fallbacks_global` | `jinja.py:105` | Thread-safe fallback set | `set[str]` |
| `_asset_manifest_fallbacks_lock` | `jinja.py:107` | Thread lock | `threading.Lock` |
| `_asset_manifest_previous` | `asset.py:192` | Previous manifest | `AssetManifest \| None` |
| `_discovery_breakdown_ms` | `content.py:216` | Timing stats | `dict[str, float]` |
| `_bengal_template_metadata_cache` | `metadata.py:241` | Template metadata cache | `dict[str, Any]` |
| `_bengal_theme_chain_cache` | `environment.py:185` | Theme chain cache | `dict[str, Any]` |
| `_bengal_template_dirs_cache` | `environment.py:346` | Template dirs cache | `dict[str, Any]` |

### Defensive Coding Patterns (Evidence)

The dynamic injection creates a cascade of defensive coding:

**1. `hasattr(site, ...)` checks (~38 instances)**
```python
# bengal/rendering/engines/jinja.py:104
if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
```

**2. `getattr(site, ...)` with defaults (~70 instances)**
```python
# bengal/utils/metadata.py:239
if not getattr(site, "dev_mode", False):
```

**3. `type: ignore[attr-defined]` comments (42 instances)**
```python
self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
```

### Architectural Violation

This pattern violates Bengal's stated principles:

```python
# bengal/core/__init__.py:22-24
"""
Core models are passive data structures with computed properties.
They do not perform I/O, logging, or side effects.
"""
```

While not performing I/O, the dynamic injection makes the `Site` object unpredictable and harder to type-check.

### Pain Points

1. **Type Safety**: `type: ignore[attr-defined]` comments silence the type checker
2. **Discoverability**: New developers can't understand what `Site` actually contains
3. **Testing**: Mocking requires knowing which undeclared attributes exist
4. **Thread Safety**: Some injected attributes are locks/sets that need initialization order guarantees
5. **IDE Support**: No autocomplete for dynamically-added attributes

---

## Goals

1. **Phase A**: Remove unnecessary `type: ignore` comments for already-formalized fields
2. **Phase B**: Formalize remaining 7 fields as explicit Site dataclass fields
3. **Improve type safety**: All attributes properly typed and discoverable
4. **Preserve performance**: Maintain lazy initialization patterns where needed
5. **Minimal API changes**: Internal refactor, not public API breaking

### Non-Goals

- Changing the semantics of any existing cache or state
- Modifying the public template context API
- Restructuring the Site mixin architecture
- Addressing all `hasattr` checks (many are legitimate duck-typing)

---

## Design Options

### Option A: Two-Phase Cleanup + Formalization (Recommended)

**Phase A**: Remove unnecessary `type: ignore` from sites using already-formalized fields.
**Phase B**: Add 7 remaining fields to Site dataclass.

**Pros**:
- Quick win from Phase A (cleanup only)
- Type-safe, discoverable, IDE-friendly
- Minimal code changes at injection sites
- Consistent with Bengal's dataclass conventions

**Cons**:
- Site dataclass grows larger (mitigated by `repr=False`)

**Effort**: ~3-4 hours  
**Risk**: Low

---

### Option B: Create RuntimeState Context Object

Move all runtime caches to a separate `BuildRuntimeState` object.

**Pros**:
- Clean separation of Site data vs runtime caches
- Easy to reset state between builds

**Cons**:
- Major refactor - must thread `runtime_state` through all call sites
- Breaks existing API patterns

**Effort**: ~12-16 hours  
**Risk**: Medium-High

---

### Option C: Status Quo + Documentation

Document the dynamic injection pattern and accept the `type: ignore` comments.

**Pros**:
- Zero effort

**Cons**:
- Technical debt accumulates
- Leaves unnecessary `type: ignore` comments on formalized fields

**Effort**: ~1 hour  
**Risk**: Low (immediate) / High (long-term)

---

## Recommended Approach: Option A

### Rationale

1. **Quick wins first** - Phase A is pure cleanup with zero risk
2. **Lowest risk** - Minimal structural changes
3. **Best ROI** - Removes unnecessary `type: ignore` comments with small effort
4. **Incremental** - Can stop after Phase A if needed
5. **Consistent** - Follows Bengal's existing dataclass conventions

---

## Technical Design

### Phase A: Cleanup Already-Formalized Fields

Remove `type: ignore` comments from sites using existing fields.

**Example** (`bengal/rendering/template_functions/get_page.py`):

**Before**:
```python
if site._template_parser is None:
    site._template_parser = create_markdown_parser(markdown_engine)  # type: ignore[attr-defined]
parser = site._template_parser  # type: ignore[attr-defined]
```

**After**:
```python
if site._template_parser is None:
    site._template_parser = create_markdown_parser(markdown_engine)
parser = site._template_parser
```

### Phase B: Add Remaining Fields to Site Dataclass

Add 7 new fields to `bengal/core/site/core.py`:

```python
@dataclass
class Site(
    SitePropertiesMixin,
    PageCachesMixin,
    # ... other mixins ...
):
    # ... existing fields ...

    # =========================================================================
    # RUNTIME CACHES (Phase B additions)
    # =========================================================================

    # --- Asset Manifest State ---
    # Previous manifest for incremental asset comparison
    _asset_manifest_previous: Any = field(default=None, repr=False, init=False)

    # Thread-safe set of fallback warnings (avoid duplicate warnings)
    _asset_manifest_fallbacks_global: set[str] = field(
        default_factory=set, repr=False, init=False
    )

    # Lock for thread-safe fallback set access
    _asset_manifest_fallbacks_lock: Any = field(default=None, repr=False, init=False)

    # --- Template Environment Caches ---
    # Theme chain cache for template resolution
    _bengal_theme_chain_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )

    # Template directories cache
    _bengal_template_dirs_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )

    # Template metadata cache
    _bengal_template_metadata_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )

    # --- Discovery State ---
    # Discovery timing breakdown
    _discovery_breakdown_ms: dict[str, float] | None = field(
        default=None, repr=False, init=False
    )

    def __post_init__(self) -> None:
        """Initialize runtime state after dataclass creation."""
        # ... existing __post_init__ code ...

        # Initialize lock if not set (for thread-safe fallback tracking)
        if self._asset_manifest_fallbacks_lock is None:
            import threading
            self._asset_manifest_fallbacks_lock = threading.Lock()
```

### Update Injection Sites

**Before** (`bengal/rendering/engines/jinja.py:104-109`):
```python
try:
    if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
        self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
    if not hasattr(self.site, "_asset_manifest_fallbacks_lock"):
        self.site._asset_manifest_fallbacks_lock = threading.Lock()  # type: ignore[attr-defined]
except Exception:
    pass
```

**After**:
```python
# Fields are pre-initialized in Site.__post_init__(), no setup needed here
# Just access directly:
with self.site._asset_manifest_fallbacks_lock:
    self.site._asset_manifest_fallbacks_global.add(fallback_path)
```

### Update reset_ephemeral_state()

Add new fields to the existing `reset_ephemeral_state()` method:

```python
def reset_ephemeral_state(self) -> None:
    """Clear ephemeral/derived state that should not persist between builds."""
    # ... existing reset code ...

    # Reset Phase B fields
    self._bengal_theme_chain_cache = None
    self._bengal_template_dirs_cache = None
    self._bengal_template_metadata_cache = None
    self._discovery_breakdown_ms = None
    self._asset_manifest_fallbacks_global.clear()
    # Note: Don't reset _asset_manifest_previous (needed for incremental)
```

---

## Implementation Plan

### Phase A: Cleanup (1 hour)

- [ ] Remove `type: ignore[attr-defined]` from `get_page.py` (4 sites for `_template_parser`, `_page_lookup_maps`)
- [ ] Remove `type: ignore[attr-defined]` from `content.py` (1 site for `_affected_tags`)
- [ ] Remove `type: ignore[attr-defined]` from `finalization.py` (1 site for `_last_build_stats`)
- [ ] Remove `type: ignore[attr-defined]` from `menu.py` (2 sites for `_dev_menu_metadata`)
- [ ] Remove `type: ignore[attr-defined]` from `tracks.py` (1 site for `_page_lookup_maps`)
- [ ] Run type checker to verify no new errors
- [ ] Run test suite

### Phase B: Formalize Remaining Fields (2-3 hours)

- [ ] Add 7 new fields to `bengal/core/site/core.py`
- [ ] Update `__post_init__` to initialize lock
- [ ] Update `reset_ephemeral_state()` to include new fields
- [ ] Update `bengal/rendering/engines/jinja.py` (2 sites)
- [ ] Update `bengal/orchestration/asset.py` (2 sites)
- [ ] Update `bengal/orchestration/content.py` (1 site)
- [ ] Update `bengal/utils/metadata.py` (1 site)
- [ ] Update `bengal/rendering/template_engine/environment.py` (2 sites)
- [ ] Remove remaining `type: ignore[attr-defined]` comments
- [ ] Run type checker and test suite

### Phase C: Validation (30 min)

- [ ] Run full test suite
- [ ] Run mypy type checking
- [ ] Verify dev server incremental builds work
- [ ] Verify no regressions

---

## Testing Strategy

### Unit Tests

Add tests to `tests/unit/core/test_site.py`:

```python
class TestSiteRuntimeCaches:
    """Tests for Site runtime cache management."""

    def test_asset_fallback_lock_initialized(self, minimal_site: Site):
        """Verify thread lock is initialized automatically."""
        assert minimal_site._asset_manifest_fallbacks_lock is not None
        import threading
        assert isinstance(
            minimal_site._asset_manifest_fallbacks_lock,
            type(threading.Lock())
        )

    def test_reset_ephemeral_clears_new_fields(self, minimal_site: Site):
        """Verify reset_ephemeral_state clears Phase B fields."""
        # Set some caches
        minimal_site._bengal_theme_chain_cache = {"key": "value"}
        minimal_site._asset_manifest_fallbacks_global.add("test.css")

        # Reset
        minimal_site.reset_ephemeral_state()

        # Verify cleared
        assert minimal_site._bengal_theme_chain_cache is None
        assert len(minimal_site._asset_manifest_fallbacks_global) == 0
```

### Integration Tests

Verify existing tests pass without modification - the refactor should be transparent to external behavior.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Low | Medium | Run full test suite before/after each phase |
| Thread safety regression | Low | High | Keep existing lock patterns; add lock initialization tests |
| Missing an injection site | Low | Low | Type checker will catch remaining `type: ignore` issues |
| Dev server reload issues | Low | Medium | Explicitly test dev server with incremental changes |

---

## Success Criteria

### Phase A (Cleanup)
1. ✅ All unnecessary `type: ignore[attr-defined]` comments removed (~9 sites)
2. ✅ Type checker passes without new errors
3. ✅ All existing tests pass

### Phase B (Formalize)
1. ✅ All 7 remaining fields added to Site dataclass
2. ✅ All `type: ignore[attr-defined]` comments for Site attributes removed
3. ✅ `hasattr(site, "_*")` patterns for injected attributes eliminated
4. ✅ Type checker passes without new errors
5. ✅ All existing tests pass
6. ✅ Dev server incremental builds work correctly

---

## Evidence Trail

| Claim | Evidence | Verification |
|-------|----------|--------------|
| 16 dynamic injection sites | Grep `site\._[a-z_]+\s*=` | 16 matches across 10 files |
| 42 `type: ignore[attr-defined]` | Grep `type:\s*ignore\[attr-defined\]` | 42 matches across 14 files |
| 5 fields already formalized | `core/site/core.py:155-167` | `_dev_menu_metadata`, `_affected_tags`, `_page_lookup_maps`, `_last_build_stats`, `_template_parser` |
| 7 fields need formalization | Grep + Site inspection | Not found in `core/site/core.py` |
| Lock injection needed | `jinja.py:107` | Thread-safe fallback set |
| Existing reset method | `Site.reset_ephemeral_state` | `core/site/core.py:329` |

---

## Confidence Scoring

**Formula**: `confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)`

| Component | Score | Notes |
|-----------|-------|-------|
| Evidence Strength | 38/40 | Direct code matches verified; stats corrected |
| Consistency | 27/30 | Clear pattern, verified existing vs missing fields |
| Recency | 13/15 | Files actively modified this week |
| Test Coverage | 7/15 | Existing tests cover behavior, not specific fields |
| **Total** | **85/100** | 🟢 HIGH |

---

## Open Questions

- [x] ~~Are there fields that are already formalized?~~ Yes, 5 fields exist.
- [ ] Should we add a `Site.validate_state()` method for debugging?
- [ ] Should new fields use a naming convention (`_cache_*` vs `_state_*`)?

---

## Related RFCs

- `rfc-spaghetti-reduction.md` - General code quality improvements
- `rfc-template-functions-robustness.md` - Addresses `_page_lookup_maps` caching

---

## Changelog

### Revision 2025-12-19
- **Corrected statistics**: 16 injection sites (not 43), 42 `type: ignore` (not 47)
- **Identified 5 already-formalized fields**: Split into Phase A (cleanup) and Phase B (formalize)
- **Reduced scope**: From 12 fields to 7 fields needing formalization
- **Reduced effort estimate**: From 4-6 hours to 3-4 hours
- **Updated confidence**: 85% (from 88%)

---

## Next Steps

1. [x] Review and evaluate RFC
2. [ ] Approve RFC
3. [ ] Implement Phase A (cleanup) - Quick win, ~1 hour
4. [ ] Implement Phase B (formalize) - ~2-3 hours
5. [ ] Final validation with `::validate`
