# RFC: Asset Resolution Observability

## Status: Implemented
## Created: 2026-01-13
## Updated: 2026-01-13

---

## Summary

**Problem**: Asset manifest resolution has zero observability—fallback to disk I/O is silent, making it impossible to detect misconfigurations, performance regressions, or verify the ContextVar pattern is working correctly.

**Solution**: Add structured logging, ContextVar-based stats tracking, and integration tests to the asset resolution path.

**Scope**: Small, focused improvement (~70 LOC changes across 3 phases).

**Origin**: Discovered during Phase 2 implementation of `rfc-global-build-state-dependencies.md`.

---

## Problem Statement

### The Observability Gap

The `_resolve_fingerprinted()` function in `bengal/rendering/assets.py` has two code paths:

1. **Primary path**: ContextVar lookup (~8M ops/sec, thread-safe)
2. **Fallback path**: Disk I/O (slower, safe but unexpected during full builds)

```python
def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    ctx = get_asset_manifest()
    if ctx is not None:
        return ctx.entries.get(logical_path)  # Primary: ContextVar

    # Fallback: Load from disk - SILENT, no logging
    manifest = AssetManifest.load(manifest_path)
    # ...
```

**The problem**: The fallback is completely silent. If:
- The orchestration code forgets to set up `asset_manifest_context()`
- There's a bug in the phase ordering
- A code path bypasses the normal build pipeline

...we have no indication that the slower fallback is being used.

### Why This Matters

| Scenario | Impact Without Observability |
|----------|------------------------------|
| Orchestration bug | Silent performance regression (~100-1000x slower per asset lookup) |
| Test configuration error | Tests pass but don't exercise intended code path |
| Dev server mode | Can't verify ContextVar is properly disabled |
| Production build | Can't verify ContextVar is properly enabled |
| Performance profiling | Can't attribute time to ContextVar vs. disk I/O |

### Evidence from Troubleshooting

During Phase 2 implementation:
1. Logger is imported but never used (`logger = get_logger(__name__)` at line 41)
2. Tests initially failed because they checked `site._asset_manifest_cache` (old implementation)
3. No way to verify ContextVar was actually being used during builds
4. Required manual code inspection to confirm correct behavior

### Alignment with Existing Patterns

Bengal has established observability patterns that are **not** applied to asset resolution:

| Pattern | Where Used | Used in Asset Resolution? |
|---------|------------|---------------------------|
| `ComponentStats` | Validators, health checks | ❌ No |
| `logger.debug()` | Link transformer, cache checker | ❌ No |
| `logger.warning()` | Highlighting, template rendering | ❌ No |
| `HasStats` protocol | Multiple components | ❌ No |

---

## Proposed Solution

### Phase 1: Structured Logging

Add logging to distinguish code paths and warn on unexpected fallback.

**File**: `bengal/rendering/assets.py`

```python
# Track whether we've already warned about fallback (avoid log spam)
_fallback_warned: set[str] = set()

def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    """Resolve a logical asset path to its fingerprinted output path."""
    ctx = get_asset_manifest()
    if ctx is not None:
        # Primary path: ContextVar (fast, thread-safe)
        return ctx.entries.get(logical_path)

    # Fallback path: Disk I/O
    # Warning if this happens outside dev mode (suggests missing context setup)
    dev_mode = getattr(site, "dev_mode", False)
    if not dev_mode:
        # Warn once per unique path to avoid log spam during render
        if logical_path not in _fallback_warned:
            _fallback_warned.add(logical_path)
            logger.warning(
                "asset_manifest_disk_fallback",
                logical_path=logical_path,
                output_dir=str(site.output_dir),
                hint="ContextVar not set - was asset_manifest_context() called?",
            )
    else:
        logger.debug(
            "asset_manifest_dev_mode_fallback",
            logical_path=logical_path,
        )

    # ... existing fallback code ...
```

**Benefits**:
- Zero overhead when ContextVar is set (no logging on happy path)
- Warning surfaces misconfigurations immediately
- Debug logging for dev mode helps verify expected behavior
- Deduplication prevents log spam during page rendering
- `output_dir` context helps identify which site/build

**LOC**: ~20 lines changed

### Phase 2: Stats Tracking (ContextVar-Based)

Add `ComponentStats` integration for performance profiling, using ContextVar for thread safety.

**File**: `bengal/rendering/assets.py`

```python
from contextvars import ContextVar
from bengal.utils.observability import ComponentStats

# Thread-safe stats via ContextVar (matches manifest pattern)
_resolution_stats: ContextVar[ComponentStats | None] = ContextVar(
    "resolution_stats", default=None
)

def get_resolution_stats() -> ComponentStats | None:
    """Get resolution stats for current context (thread-safe)."""
    return _resolution_stats.get()

def _ensure_resolution_stats() -> ComponentStats:
    """Get or create resolution stats for current context."""
    stats = _resolution_stats.get()
    if stats is None:
        stats = ComponentStats()
        _resolution_stats.set(stats)
    return stats

def clear_manifest_cache(site: Site | None = None) -> None:
    """Clear the asset manifest cache and reset stats."""
    global _fallback_warned
    reset_asset_manifest()
    _resolution_stats.set(None)
    _fallback_warned = set()
```

**Updated resolution function** (complete implementation):

```python
def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    """
    Resolve a logical asset path to its fingerprinted output path.

    Uses ContextVar for thread-safe manifest access (no locks needed).
    Falls back to loading manifest from disk if ContextVar is not set.

    Thread Safety (Free-Threading / PEP 703):
        Primary path uses ContextVar - thread-local by design.
        Fallback path loads from disk (safe but slower).
        Stats tracking uses ContextVar - no global mutable state.
    """
    ctx = get_asset_manifest()
    stats = _ensure_resolution_stats()

    if ctx is not None:
        # Primary path: ContextVar (fast, thread-safe)
        stats.cache_hits += 1
        return ctx.entries.get(logical_path)

    # Fallback path: Disk I/O
    stats.cache_misses += 1
    
    dev_mode = getattr(site, "dev_mode", False)
    if not dev_mode:
        stats.items_skipped["unexpected_fallback"] = (
            stats.items_skipped.get("unexpected_fallback", 0) + 1
        )
        if logical_path not in _fallback_warned:
            _fallback_warned.add(logical_path)
            logger.warning(
                "asset_manifest_disk_fallback",
                logical_path=logical_path,
                output_dir=str(site.output_dir),
                hint="ContextVar not set - was asset_manifest_context() called?",
            )
    else:
        stats.items_skipped["dev_mode_fallback"] = (
            stats.items_skipped.get("dev_mode_fallback", 0) + 1
        )
        logger.debug(
            "asset_manifest_dev_mode_fallback",
            logical_path=logical_path,
        )

    # Existing fallback code
    from bengal.assets.manifest import AssetManifest

    manifest_path = site.output_dir / "asset-manifest.json"
    if not manifest_path.exists():
        return None

    manifest = AssetManifest.load(manifest_path)
    if manifest is None:
        return None

    entry = manifest.get(logical_path)
    if entry:
        return entry.output_path
    return None
```

**Benefits**:
- Quantitative data on ContextVar effectiveness
- Thread-safe via ContextVar (consistent with parent RFC)
- Integrates with existing `HasStats` protocol
- Distinguishes expected (dev mode) vs. unexpected fallbacks
- Can surface in CLI output when thresholds exceeded

**LOC**: ~35 lines changed

### Phase 3: Integration Test

Add a test that explicitly verifies ContextVar is set during builds, using Phase 2 stats.

**File**: `tests/integration/test_asset_manifest_contextvar.py`

```python
import pytest
from pathlib import Path

def test_contextvar_always_set_during_full_build(tmp_project: Path) -> None:
    """Verify ContextVar is set during phase_render, not using fallback."""
    from bengal.rendering.assets import get_resolution_stats, clear_manifest_cache
    from tests.helpers import build_site
    
    # Clear any previous state
    clear_manifest_cache()
    
    # Build site
    result = build_site(tmp_project)
    assert result.success
    
    # Verify stats
    stats = get_resolution_stats()
    assert stats is not None, "Resolution stats should be tracked during build"
    
    unexpected = stats.items_skipped.get("unexpected_fallback", 0)
    assert unexpected == 0, (
        f"Asset resolution used disk fallback {unexpected} times during build.\n"
        f"ContextVar should always be set via asset_manifest_context() in phase_render.\n"
        f"Stats: {stats.format_summary('AssetResolution')}"
    )


def test_dev_server_uses_expected_fallback(tmp_project: Path) -> None:
    """Dev server should use disk fallback (no manifest context needed)."""
    from bengal.rendering.assets import get_resolution_stats, clear_manifest_cache
    from tests.helpers import build_site_dev_mode
    
    clear_manifest_cache()
    
    result = build_site_dev_mode(tmp_project)
    assert result.success
    
    stats = get_resolution_stats()
    if stats:
        # Dev mode fallbacks are expected, not errors
        assert stats.items_skipped.get("unexpected_fallback", 0) == 0
        # dev_mode_fallback count can be > 0 (expected)


def test_stats_reset_between_builds(tmp_project: Path) -> None:
    """Stats should reset on clear_manifest_cache()."""
    from bengal.rendering.assets import (
        get_resolution_stats,
        clear_manifest_cache,
        _ensure_resolution_stats,
    )
    
    # Create some stats
    stats = _ensure_resolution_stats()
    stats.cache_hits = 100
    
    # Clear should reset
    clear_manifest_cache()
    
    assert get_resolution_stats() is None
```

**Benefits**:
- Catches orchestration bugs that bypass ContextVar setup
- Documents expected behavior explicitly
- Uses quantitative stats (not patching) for cleaner tests
- Covers both production and dev server modes
- Verifies stats reset properly between builds

**LOC**: ~50 lines (new test file)

---

## Implementation Plan

### Recommended Order

| Order | Phase | Priority | LOC | Risk |
|-------|-------|----------|-----|------|
| 1 | Phase 1 - Logging | 🟢 High | ~20 | None |
| 2 | Phase 2 - Stats | 🟢 High | ~35 | None |
| 3 | Phase 3 - Tests | 🟢 High | ~50 | None |

**Rationale**: 
- Phase 1 provides immediate observability
- Phase 2 enables quantitative assertions in Phase 3
- Phase 3 tests are cleaner when they can use Phase 2 stats (no patching required)
- All phases are backward compatible

**Total**: ~105 LOC (tests included)

### Implementation Checklist

**Phase 1**:
- [x] Add `_fallback_warned` set for deduplication
- [x] Add warning log for non-dev-mode fallback (with `output_dir` context)
- [x] Add debug log for dev-mode fallback
- [x] Verify no performance impact (happy path has no logging)
- [x] Reset `_fallback_warned` in `clear_manifest_cache()`

**Phase 2**:
- [x] Add `_resolution_stats` ContextVar
- [x] Add `get_resolution_stats()` and `_ensure_resolution_stats()`
- [x] Track `cache_hits` on ContextVar path
- [x] Track `cache_misses` and categorized `items_skipped` on fallback path
- [x] Integrate reset with `clear_manifest_cache()`

**Phase 3**:
- [x] Add unit tests for warning logging and deduplication
- [x] Add unit tests for stats tracking
- [x] Add integration tests for ContextVar usage during builds
- [x] Add integration tests for stats reset between builds

---

## Alternatives Considered

### 1. No Observability (Status Quo)

**Pros**: Zero code changes  
**Cons**: Silent failures, impossible to diagnose performance issues

**Rejected**: The Phase 2 ContextVar implementation specifically relies on correct orchestration setup. Without observability, misconfigurations are invisible.

### 2. Exception Instead of Warning

```python
if ctx is None and not dev_mode:
    raise RuntimeError("asset_manifest_context not set during build")
```

**Pros**: Fail-fast behavior  
**Cons**: 
- Breaks backward compatibility with custom build scripts
- Too aggressive for a fallback that technically works
- Makes incremental adoption harder

**Rejected**: Warning is sufficient—it surfaces issues without breaking builds.

### 3. Environment Variable to Enable Strict Mode

```python
STRICT_ASSET_RESOLUTION = os.environ.get("BENGAL_STRICT_ASSET_RESOLUTION", "0") == "1"

if ctx is None and not dev_mode and STRICT_ASSET_RESOLUTION:
    raise RuntimeError(...)
```

**Pros**: Opt-in strictness for CI  
**Cons**: Adds complexity, another config knob

**Deferred**: Could add later if warning-based approach proves insufficient.

### 4. Module-Level Global Stats (Original Phase 2)

```python
_resolution_stats: ComponentStats | None = None  # Module-level global
```

**Pros**: Simpler implementation  
**Cons**: Conflicts with free-threading goals from parent RFC

**Rejected**: ContextVar provides thread safety consistent with the manifest pattern.

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/rendering/test_asset_resolution_observability.py`

```python
def test_warning_logged_on_unexpected_fallback(caplog, mock_site):
    """Warning should be logged when fallback used outside dev mode."""
    from bengal.rendering.assets import _resolve_fingerprinted, clear_manifest_cache
    
    clear_manifest_cache()
    mock_site.dev_mode = False
    
    with caplog.at_level("WARNING"):
        _resolve_fingerprinted("css/style.css", mock_site)
    
    assert "asset_manifest_disk_fallback" in caplog.text
    assert "css/style.css" in caplog.text


def test_no_warning_when_contextvar_set(caplog, mock_site):
    """No warning when ContextVar is properly set."""
    from bengal.rendering.assets import (
        _resolve_fingerprinted,
        asset_manifest_context,
        AssetManifestContext,
        clear_manifest_cache,
    )
    
    clear_manifest_cache()
    ctx = AssetManifestContext(entries={"css/style.css": "assets/css/style.abc123.css"})
    
    with caplog.at_level("WARNING"):
        with asset_manifest_context(ctx):
            _resolve_fingerprinted("css/style.css", mock_site)
    
    assert "asset_manifest_disk_fallback" not in caplog.text


def test_debug_log_in_dev_mode(caplog, mock_site):
    """Debug log in dev mode (expected fallback)."""
    from bengal.rendering.assets import _resolve_fingerprinted, clear_manifest_cache
    
    clear_manifest_cache()
    mock_site.dev_mode = True
    
    with caplog.at_level("DEBUG"):
        _resolve_fingerprinted("css/style.css", mock_site)
    
    assert "asset_manifest_dev_mode_fallback" in caplog.text


def test_warning_deduplicated(caplog, mock_site):
    """Same path should only warn once."""
    from bengal.rendering.assets import _resolve_fingerprinted, clear_manifest_cache
    
    clear_manifest_cache()
    mock_site.dev_mode = False
    
    with caplog.at_level("WARNING"):
        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("css/style.css", mock_site)
        _resolve_fingerprinted("css/style.css", mock_site)
    
    assert caplog.text.count("asset_manifest_disk_fallback") == 1
```

### Integration Tests

1. **Test full build never hits fallback** (Phase 3 - `test_contextvar_always_set_during_full_build`)
2. **Test dev server correctly uses fallback** (Phase 3 - `test_dev_server_uses_expected_fallback`)
3. **Test incremental build with manifest changes** (existing tests)

---

## Rollout Plan

1. **Implement Phase 1** (logging) - immediate
2. **Implement Phase 2** (stats) - immediate
3. **Implement Phase 3** (integration tests) - immediate
4. **Monitor logs in CI** for unexpected warnings
5. **Add CLI stats output** (future) - if detailed performance profiling needed

---

## Success Criteria

- [x] **No silent fallbacks**: Any unexpected disk I/O produces a warning
- [x] **Dev mode documented**: Debug logging confirms expected fallback behavior
- [x] **CI coverage**: Integration tests verify observability infrastructure works
- [x] **Zero happy-path overhead**: No logging when ContextVar is properly set
- [x] **Thread-safe stats**: ContextVar-based stats work correctly under free-threading
- [x] **Quantitative metrics**: `cache_hits`/`cache_misses` available for profiling

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | Draft RFC | Discovered observability gap during Phase 2 implementation |
| 2026-01-13 | Use ContextVar for stats | Maintains thread-safety consistency with parent RFC |
| 2026-01-13 | Add warning deduplication | Prevents log spam during page rendering |
| 2026-01-13 | Reorder phases (1→2→3) | Phase 3 tests benefit from Phase 2 stats |
| 2026-01-13 | Implemented all phases | All phases implemented with unit and integration tests |

---

## References

- `rfc-global-build-state-dependencies.md` - Origin RFC (Phase 2 ContextVar pattern)
- `bengal/utils/observability.py` - Existing `ComponentStats` pattern
- `bengal/utils/logger.py` - Existing structured logging infrastructure
- `bengal/rendering/assets.py` - Target file for changes
- `tests/unit/rendering/test_asset_manifest_contextvar.py` - Existing ContextVar tests