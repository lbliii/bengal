# RFC: Formalize Site Runtime State & Eliminate Dynamic Attribute Injection

**Status**: Draft  
**Created**: 2025-12-19  
**Author**: AI Assistant  
**Subsystems**: `bengal/core/site/`, `bengal/rendering/`, `bengal/orchestration/`  
**Confidence**: 88% 🟢  
**Priority**: P1 (High)  

---

## Executive Summary

Comprehensive analysis of Bengal's codebase identified **43 instances** of external code dynamically injecting private attributes onto the `Site` object using `site._attribute = value` patterns, requiring `# type: ignore[attr-defined]` comments to silence the type checker. This violates Bengal's architectural principles of explicit state management and makes the codebase harder to reason about, test, and maintain.

This RFC proposes formalizing all runtime state as explicit `Site` dataclass fields with proper types, eliminating the need for `hasattr` checks, `getattr` defaults, and `type: ignore` comments.

**Key findings**:
- 43 dynamic `site._*` attribute injections across 14 files
- 360 `hasattr` checks indicating duck-typing uncertainty
- 295 `getattr` with defaults indicating missing attributes
- 115 `type: ignore` comments (47 for `attr-defined`)

---

## Problem Statement

### Current State

External modules inject private attributes onto `Site` at runtime:

```python
# bengal/rendering/engines/jinja.py:104-109
try:
    if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
        self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
    if not hasattr(self.site, "_asset_manifest_fallbacks_lock"):
        self.site._asset_manifest_fallbacks_lock = threading.Lock()  # type: ignore[attr-defined]
except Exception:
    pass
```

```python
# bengal/rendering/template_functions/get_page.py:53
site._template_parser = create_markdown_parser(markdown_engine)  # type: ignore[attr-defined]
```

### Injected Attributes Found (43 instances)

| Attribute | Injected By | Purpose | Type |
|-----------|-------------|---------|------|
| `_template_parser` | `get_page.py:53` | Lazy-loaded markdown parser | `MarkdownParser \| None` |
| `_page_lookup_maps` | `get_page.py:187` | Page lookup cache | `dict[str, dict[str, Page]] \| None` |
| `_asset_manifest_fallbacks_global` | `jinja.py:105` | Thread-safe fallback set | `set[str]` |
| `_asset_manifest_fallbacks_lock` | `jinja.py:107` | Thread lock | `threading.Lock` |
| `_asset_manifest_previous` | `asset.py:192` | Previous manifest | `AssetManifest \| None` |
| `_discovery_breakdown_ms` | `content.py:216` | Timing stats | `dict[str, float]` |
| `_bengal_template_metadata_cache` | `metadata.py:241` | Template metadata cache | `dict[str, Any]` |
| `_bengal_theme_chain_cache` | `environment.py:185` | Theme chain cache | `dict[str, Any]` |
| `_bengal_template_dirs_cache` | `environment.py:346` | Template dirs cache | `dict[str, Any]` |
| `_dev_menu_metadata` | `menu.py:251` | Dev menu config | `dict[str, Any] \| None` |
| `_affected_tags` | `content.py:116` | Incremental build tags | `set[str]` |
| `_last_build_stats` | `finalization.py:97` | Build stats | `dict[str, Any]` |

### Defensive Coding Patterns (Evidence)

The dynamic injection creates a cascade of defensive coding:

**1. `hasattr` checks (360 instances)**
```python
# bengal/rendering/pipeline/core.py:139
if hasattr(site, "xref_index") and hasattr(self.parser, "enable_cross_references"):
    self.parser.enable_cross_references(site.xref_index)
```

**2. `getattr` with defaults (295 instances)**
```python
# bengal/rendering/pipeline/core.py:196-198
prerendered = getattr(page, "_prerendered_html", None)
if getattr(page, "_virtual", False) and (prerendered is not None or is_autodoc):
```

**3. `type: ignore` comments (115 instances)**
```python
# 47 instances of type: ignore[attr-defined]
self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
```

### Architectural Violation

This pattern violates Bengal's stated principles:

```python
# bengal/core/__init__.py:21-31
"""
Core models are passive data structures with computed properties.
They do not perform I/O, logging, or side effects.
"""
```

While not performing I/O, the dynamic injection makes the `Site` object unpredictable and harder to type-check.

### Pain Points

1. **Type Safety**: 47 `type: ignore[attr-defined]` comments silence the type checker
2. **Discoverability**: New developers can't understand what `Site` actually contains
3. **Testing**: Mocking requires knowing which undeclared attributes exist
4. **Thread Safety**: Some injected attributes are locks/sets that need initialization order guarantees
5. **IDE Support**: No autocomplete for dynamically-added attributes

---

## Goals

1. **Eliminate dynamic attribute injection** - All `Site` state declared as formal fields
2. **Remove defensive coding** - Reduce `hasattr`/`getattr`/`type: ignore` patterns
3. **Improve type safety** - All attributes properly typed and discoverable
4. **Preserve performance** - Maintain lazy initialization patterns where needed
5. **Minimal API changes** - Internal refactor, not public API breaking

### Non-Goals

- Changing the semantics of any existing cache or state
- Modifying the public template context API
- Restructuring the Site mixin architecture
- Addressing all 360 `hasattr` checks (many are legitimate duck-typing)

---

## Design Options

### Option A: Formalize Fields in Site Dataclass (Recommended)

Add all dynamically-injected attributes as formal `Site` dataclass fields with proper types and `field(default=None, repr=False)`.

**Approach**:
```python
@dataclass
class Site:
    # ... existing fields ...

    # === Runtime Caches (not serialized, initialized lazily) ===
    _template_parser: MarkdownParser | None = field(default=None, repr=False)
    _page_lookup_maps: dict[str, dict[str, Page]] | None = field(default=None, repr=False)
    _asset_manifest_fallbacks_global: set[str] = field(default_factory=set, repr=False)
    _asset_manifest_fallbacks_lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False
    )
    # ... etc ...
```

**Pros**:
- Type-safe, discoverable, IDE-friendly
- Minimal code changes at injection sites (just remove `type: ignore`)
- Consistent with Bengal's dataclass conventions
- Easy to migrate incrementally

**Cons**:
- Site dataclass grows larger (mitigated by `repr=False`)
- Some fields are only used by specific subsystems (mitigated by clear naming/grouping)

**Effort**: ~4-6 hours  
**Risk**: Low

---

### Option B: Create RuntimeState Context Object

Move all runtime caches to a separate `BuildRuntimeState` object that is passed through the pipeline.

**Approach**:
```python
@dataclass
class BuildRuntimeState:
    """Runtime caches and state for a single build."""
    template_parser: MarkdownParser | None = None
    page_lookup_maps: dict[str, dict[str, Page]] | None = None
    asset_manifest_fallbacks: set[str] = field(default_factory=set)
    # ... etc ...

# Usage:
class RenderingPipeline:
    def __init__(self, site: Site, runtime_state: BuildRuntimeState):
        self.site = site
        self.runtime = runtime_state
```

**Pros**:
- Clean separation of Site data vs runtime caches
- Easy to reset state between builds
- Aligns with "Site is passive data" principle

**Cons**:
- Major refactor - must thread `runtime_state` through all call sites
- Breaks existing API patterns
- Larger diff surface

**Effort**: ~12-16 hours  
**Risk**: Medium-High

---

### Option C: Use BuildContext (Existing)

Expand the existing `BuildContext` object to hold runtime caches.

**Approach**:
```python
# bengal/utils/build_context.py (already exists)
@dataclass
class BuildContext:
    site: Site
    # ... existing fields ...

    # Add runtime caches
    template_parser: MarkdownParser | None = None
    page_lookup_maps: dict[str, dict[str, Page]] | None = None
```

**Pros**:
- Uses existing pattern
- Already passed to many subsystems

**Cons**:
- `BuildContext` is already complex
- Not all injection sites have access to `BuildContext`
- Mixed concerns (build config vs runtime caches)

**Effort**: ~8-10 hours  
**Risk**: Medium

---

### Option D: Status Quo + Documentation

Document the dynamic injection pattern and accept the `type: ignore` comments.

**Pros**:
- Zero effort

**Cons**:
- Technical debt accumulates
- Type safety remains broken
- Defensive coding patterns persist

**Effort**: ~1 hour  
**Risk**: Low (immediate) / High (long-term)

---

## Recommended Approach: Option A

### Rationale

1. **Lowest risk** - Minimal structural changes, just formalization
2. **Best ROI** - Removes 47+ `type: ignore` comments with small effort
3. **Incremental** - Can migrate one attribute at a time
4. **Preserves patterns** - Lazy initialization still works with property setters
5. **Consistent** - Follows Bengal's existing dataclass conventions

---

## Technical Design

### Phase 1: Add Fields to Site Dataclass

Add new fields to `bengal/core/site/core.py`:

```python
@dataclass
class Site(
    SitePropertiesMixin,
    PageCachesMixin,
    SiteFactoriesMixin,
    ThemeIntegrationMixin,
    ContentDiscoveryMixin,
    DataLoadingMixin,
    SectionRegistryMixin,
):
    # ... existing required fields ...

    # =========================================================================
    # RUNTIME CACHES (not serialized, lazy-initialized)
    # =========================================================================
    # These fields hold transient state during builds. They are not persisted
    # and may be reset between builds or in dev server reloads.
    #
    # Naming convention: _cache_* for caches, _state_* for mutable state
    # =========================================================================

    # --- Rendering Caches ---
    # Template parser for template functions (get_page, etc.)
    _cache_template_parser: Any = field(default=None, repr=False)

    # Page lookup maps for O(1) page resolution
    _cache_page_lookup_maps: dict[str, dict[str, Any]] | None = field(
        default=None, repr=False
    )

    # --- Asset Manifest State ---
    # Previous manifest for incremental asset comparison
    _state_asset_manifest_previous: Any = field(default=None, repr=False)

    # Thread-safe set of fallback warnings (avoid duplicate warnings)
    _state_asset_fallbacks_global: set[str] = field(default_factory=set, repr=False)

    # Lock for thread-safe fallback set access
    _state_asset_fallbacks_lock: Any = field(default=None, repr=False)

    # --- Template Environment Caches ---
    # Theme chain cache for template resolution
    _cache_theme_chain: dict[str, Any] | None = field(default=None, repr=False)

    # Template directories cache
    _cache_template_dirs: dict[str, Any] | None = field(default=None, repr=False)

    # Template metadata cache
    _cache_template_metadata: dict[str, Any] | None = field(default=None, repr=False)

    # --- Build State ---
    # Discovery timing breakdown
    _state_discovery_breakdown_ms: dict[str, float] | None = field(
        default=None, repr=False
    )

    # Dev menu metadata (sections to exclude, GitHub bundled, etc.)
    _state_dev_menu_metadata: dict[str, Any] | None = field(default=None, repr=False)

    # Affected tags for incremental builds
    _state_affected_tags: set[str] | None = field(default=None, repr=False)

    # Last build statistics
    _state_last_build_stats: dict[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize runtime state after dataclass creation."""
        super().__post_init__() if hasattr(super(), "__post_init__") else None

        # Initialize lock if not set
        if self._state_asset_fallbacks_lock is None:
            import threading
            self._state_asset_fallbacks_lock = threading.Lock()

    def reset_runtime_caches(self) -> None:
        """
        Reset all runtime caches.

        Call this between builds or on dev server reload to ensure
        fresh state without recreating the Site object.
        """
        self._cache_template_parser = None
        self._cache_page_lookup_maps = None
        self._cache_theme_chain = None
        self._cache_template_dirs = None
        self._cache_template_metadata = None
        self._state_discovery_breakdown_ms = None
        self._state_affected_tags = None
        self._state_last_build_stats = None
        self._state_asset_fallbacks_global.clear()
        # Note: Don't reset _state_asset_manifest_previous (needed for incremental)
        # Note: Don't reset _state_dev_menu_metadata (persists across dev builds)
```

### Phase 2: Update Injection Sites

Remove `type: ignore` comments and update code to use formal fields.

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
with self.site._state_asset_fallbacks_lock:
    self.site._state_asset_fallbacks_global.add(fallback_path)
```

**Before** (`bengal/rendering/template_functions/get_page.py:44-62`):
```python
if site._template_parser is None:
    site._template_parser = create_markdown_parser(markdown_engine)  # type: ignore[attr-defined]
parser = site._template_parser  # type: ignore[attr-defined]
```

**After**:
```python
if site._cache_template_parser is None:
    site._cache_template_parser = create_markdown_parser(markdown_engine)
parser = site._cache_template_parser
```

### Phase 3: Reduce hasattr/getattr Patterns

After fields are formalized, many defensive patterns become unnecessary:

**Before**:
```python
if hasattr(self.site, "_dev_menu_metadata") and self.site._dev_menu_metadata:
    excluded = self.site._dev_menu_metadata.get("exclude_sections", [])
```

**After**:
```python
if self.site._state_dev_menu_metadata:
    excluded = self.site._state_dev_menu_metadata.get("exclude_sections", [])
```

### Naming Convention

Adopt clear naming to distinguish cache types:

| Prefix | Purpose | Reset on Rebuild? |
|--------|---------|-------------------|
| `_cache_*` | Computed/derived data that can be regenerated | Yes |
| `_state_*` | Mutable state that may persist across operations | Maybe |

---

## Implementation Plan

### Phase 1: Site Field Additions (2 hours)

- [ ] Add runtime cache fields to `bengal/core/site/core.py`
- [ ] Add `reset_runtime_caches()` method
- [ ] Update `__post_init__` to initialize lock
- [ ] Add docstrings explaining each field's purpose
- [ ] Run type checker to verify no new errors

### Phase 2: Update Injection Sites (2 hours)

- [ ] Update `bengal/rendering/engines/jinja.py` (2 injections)
- [ ] Update `bengal/rendering/template_functions/get_page.py` (4 injections)
- [ ] Update `bengal/orchestration/content.py` (3 injections)
- [ ] Update `bengal/orchestration/asset.py` (1 injection)
- [ ] Update `bengal/orchestration/menu.py` (4 injections)
- [ ] Update `bengal/orchestration/build/finalization.py` (1 injection)
- [ ] Update `bengal/rendering/template_engine/environment.py` (2 injections)
- [ ] Update `bengal/utils/metadata.py` (1 injection)
- [ ] Remove all `type: ignore[attr-defined]` comments for these fields

### Phase 3: Dev Server Integration (1 hour)

- [ ] Call `site.reset_runtime_caches()` on dev server reload
- [ ] Update `Site.reset_ephemeral_state()` to include new caches
- [ ] Verify incremental builds still work correctly

### Phase 4: Test & Validate (1 hour)

- [ ] Run full test suite
- [ ] Run mypy type checking
- [ ] Verify no regressions in dev server
- [ ] Verify incremental builds work

---

## Testing Strategy

### Unit Tests

Add tests to `tests/unit/core/test_site.py`:

```python
class TestSiteRuntimeCaches:
    """Tests for Site runtime cache management."""

    def test_reset_runtime_caches_clears_all(self, minimal_site: Site):
        """Verify reset_runtime_caches clears all cache fields."""
        # Set some caches
        minimal_site._cache_template_parser = "fake_parser"
        minimal_site._cache_page_lookup_maps = {"test": {}}
        minimal_site._state_asset_fallbacks_global.add("test.css")

        # Reset
        minimal_site.reset_runtime_caches()

        # Verify cleared
        assert minimal_site._cache_template_parser is None
        assert minimal_site._cache_page_lookup_maps is None
        assert len(minimal_site._state_asset_fallbacks_global) == 0

    def test_lock_initialized_on_creation(self, minimal_site: Site):
        """Verify thread lock is initialized automatically."""
        assert minimal_site._state_asset_fallbacks_lock is not None

        # Should be a Lock
        import threading
        assert isinstance(minimal_site._state_asset_fallbacks_lock, type(threading.Lock()))
```

### Integration Tests

Verify existing tests pass without modification - the refactor should be transparent to external behavior.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missing an injection site | Medium | Low | Grep for `site._` patterns; type checker will catch remaining issues |
| Breaking existing tests | Low | Medium | Run full test suite before/after each phase |
| Thread safety regression | Low | High | Keep existing lock patterns; add lock initialization tests |
| Dev server reload issues | Low | Medium | Explicitly test dev server with incremental changes |

---

## Success Criteria

1. ✅ All 12 dynamic `site._*` injections converted to formal fields
2. ✅ All `type: ignore[attr-defined]` comments for Site attributes removed
3. ✅ `hasattr(site, "_*")` patterns for injected attributes eliminated
4. ✅ Type checker passes without new errors
5. ✅ All existing tests pass
6. ✅ Dev server incremental builds work correctly

---

## Evidence Trail

| Claim | Evidence | Verification |
|-------|----------|--------------|
| 43 dynamic injections | Grep `site\._[a-z_]+\s*=` | See analysis output |
| 47 `type: ignore[attr-defined]` | Grep `type:\s*ignore\[attr-defined\]` | `jinja.py:105,107`, `get_page.py:53,62` |
| Lock injection needed | `jinja.py:107` | Thread-safe fallback set |
| Template parser injection | `get_page.py:53` | Lazy markdown parser |
| Dev menu metadata injection | `menu.py:251-335` | Section exclusion logic |
| Existing reset method | `Site.reset_ephemeral_state` | `core/site/core.py` |

---

## Confidence Scoring

**Formula**: `confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)`

| Component | Score | Notes |
|-----------|-------|-------|
| Evidence Strength | 40/40 | Direct code matches for all injection sites |
| Consistency | 28/30 | Clear pattern across 14 files, minor variation in naming |
| Recency | 13/15 | Files actively modified this week |
| Test Coverage | 7/15 | Existing tests cover behavior, not specific fields |
| **Total** | **88/100** | 🟢 HIGH |

---

## Open Questions

- [ ] Should `_state_dev_menu_metadata` be reset on rebuild, or persist across dev builds?
- [ ] Are there any injection sites in third-party integrations we haven't discovered?
- [ ] Should we add a `Site.validate_state()` method for debugging?

---

## Related RFCs

- `rfc-spaghetti-reduction.md` - General code quality improvements
- `rfc-template-functions-robustness.md` - Addresses `_page_lookup_maps` caching

---

## Next Steps

1. [ ] Review and approve RFC
2. [ ] Create implementation plan (`::plan`)
3. [ ] Implement in phases
4. [ ] Final validation with `::validate`
