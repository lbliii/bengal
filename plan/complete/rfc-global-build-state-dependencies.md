# RFC: Global Build State Dependencies

## Status: Phase 1 Complete ✅
## Created: 2026-01-13
## Updated: 2026-01-13

---

## Summary

**Problem**: Incremental builds didn't rebuild pages when CSS/JS assets changed, causing stale fingerprinted URLs (e.g., `style.abc123.css` in HTML when actual file is `style.xyz789.css`).

**Solution**:
- **Phase 1** ✅: Force page rebuild when CSS/JS assets change (shipped v0.1.10)
- **Phase 2**: ContextVar pattern for thread-safe manifest access (free-threading hardening)
- **Phase 3**: `BuildStateHash` abstraction (unified global state tracking)

**Key Insight**: The rendered HTML cache was never the issue—pages weren't being rebuilt AT ALL when only assets changed because the incremental filter only looked at content changes.

---

## Problem Statement

The incremental build system has a blind spot for **asset fingerprint changes** - when CSS/JS assets change, pages must be rebuilt because they embed fingerprinted asset URLs.

### The Bug That Exposed This

Home page served with stale CSS fingerprint after CSS-only change:
- CSS changed → new fingerprint (`style.4df19bd5.css`)
- Asset manifest updated correctly
- Incremental filter checked: "Did `index.md` change?" → No
- Result: `index.md` not in `pages_to_build` → page NOT rebuilt
- Old HTML with `style.9b0fa869.css` remained on disk → 404 for CSS

### Root Cause Analysis

The bug was **NOT** in the rendered HTML cache validation—it was earlier in the pipeline:

```
phase_incremental_filter():
  pages_to_build = find_work_early()  # Only content changes!
  # CSS/JS changes → assets_to_process, but NOT pages_to_build
```

Pages embed fingerprinted asset URLs (`style.abc123.css`). When CSS changes:
- Assets phase correctly creates new fingerprint
- But pages weren't in `pages_to_build` → never rebuilt → old fingerprint remains

### Why This Class of Bugs Is Hard to Catch

1. **Full builds work fine**: Assets → Manifest → Render → Correct fingerprints
2. **Test focus**: Tests check content changes, not CSS-only changes
3. **Phase ordering illusion**: "Assets run before render" is true, but pages must be IN the render list
4. **Incremental filter scope**: `find_work_early()` looks at content, not asset dependencies

## Free-Threading Considerations (Python 3.14+)

Bengal targets Python 3.14+ with free-threading support (PEP 703). Global mutable state must be avoided or properly protected.

### Current Free-Threading-Safe Patterns ✅

| Component | Approach | Safe? |
|-----------|----------|-------|
| `BuildState` | Fresh per-build, passed through phases | ✅ |
| `BuildCache` | Loaded/saved per-build, not shared | ✅ |
| `DependencyTracker` | `threading.Lock` + `threading.local()` | ✅ |
| `ThreadLocalCache` | Thread-local storage | ✅ |
| `cache_registry` | Lock-protected, populated at import time | ✅ |
| `TemplateEngine._asset_manifest_cache` | Per-engine (one per thread) | ✅ |

### Known Thread Safety Issue ⚠️

**`Site._asset_manifest_cache`** in `rendering/assets.py:104-117`:

```python
# _resolve_fingerprinted() is called during parallel rendering
def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    cache_attr = "_asset_manifest_cache"
    manifest_cache = getattr(site, cache_attr, None)  # Read

    if manifest_cache is None:
        manifest_path = site.output_dir / "asset-manifest.json"
        manifest = AssetManifest.load(manifest_path)  # Race: multiple threads load
        if manifest is None:
            setattr(site, cache_attr, {})             # Race: multiple threads write
            return None
        manifest_cache = dict(manifest.entries)
        setattr(site, cache_attr, manifest_cache)     # Race: multiple threads write

    entry = manifest_cache.get(logical_path)
    # ...
```

This is a classic TOCTOU (Time-Of-Check-Time-Of-Use) race condition:

1. Thread A checks `manifest_cache is None` → True
2. Thread B checks `manifest_cache is None` → True (before A writes)
3. Both threads load manifest from disk (redundant I/O)
4. Both threads call `setattr()` (undefined behavior without GIL)

With GIL, this was "safe enough" (redundant loads, but consistent final state). With free-threading (PEP 703), this is a data race that must be fixed.

### Proposed Fix: ContextVar Pattern (Recommended)

Bengal already uses ContextVar extensively for Patitas integration:
- `ParseConfig` + `_parse_config: ContextVar` - thread-local parser config
- `RenderConfig` + `_render_config: ContextVar` - thread-local renderer config
- `RenderMetadata` + `_metadata: ContextVar` - thread-local metadata accumulator
- `RequestContext` + `_request_context: ContextVar` - per-request state

**Apply the same pattern for asset manifest:**

```python
# bengal/rendering/assets.py
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AssetManifestContext:
    """Immutable asset manifest context - set once per build, read many.

    Thread Safety:
        ContextVars are thread-local by design (PEP 567).
        Each thread has independent storage - no locks needed.
    """
    entries: dict[str, str]  # logical_path -> fingerprinted_path
    mtime: float | None      # For cache invalidation

# Thread-local manifest via ContextVar
_asset_manifest: ContextVar[AssetManifestContext | None] = ContextVar(
    "asset_manifest",
    default=None,
)

def get_asset_manifest() -> AssetManifestContext | None:
    """Get current asset manifest (thread-local). ~8M ops/sec."""
    return _asset_manifest.get()

def set_asset_manifest(manifest: AssetManifestContext) -> None:
    """Set asset manifest for current context."""
    _asset_manifest.set(manifest)

@contextmanager
def asset_manifest_context(manifest: AssetManifestContext):
    """Context manager for scoped manifest usage."""
    token = _asset_manifest.set(manifest)
    try:
        yield manifest
    finally:
        _asset_manifest.reset(token)

def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    """Resolve asset path using ContextVar - no locks, thread-safe by design."""
    ctx = get_asset_manifest()
    if ctx is None:
        return None
    return ctx.entries.get(logical_path)
```

**Why ContextVar is Better Than Locks:**

| Approach | Throughput | Lock Contention | Complexity |
|----------|------------|-----------------|------------|
| `Site._attr` (current) | N/A | Race condition! | Low |
| `BuildState.get_lock()` | ~8M ops/sec | Yes | Medium |
| **ContextVar** | **~8M ops/sec** | **None** | **Low** |

From `plan/rfc-free-threading-patterns.md`:
> ContextVar lookup is ~8M ops/sec (Pattern 2 benchmarks)
> ContextVars eliminate synchronization for thread-local data

**Usage in Build Orchestrator:**

```python
# In phase_render (before parallel rendering starts):
manifest = AssetManifest.load(output_dir / "asset-manifest.json")
ctx = AssetManifestContext(
    entries={k: v.output_path for k, v in manifest.entries.items()},
    mtime=manifest_path.stat().st_mtime,
)

with asset_manifest_context(ctx):
    # All parallel page rendering happens here
    # Each thread reads from ContextVar - no locks needed
    render_pages_parallel(pages)
```

### Why Proposed Solutions Are Free-Threading Safe

All solutions avoid global mutable state by using established patterns:

| Solution | Pattern | Why Safe |
|----------|---------|----------|
| **ContextVar manifest** | Thread-local state | Each thread has independent copy |
| **Option A (BuildStateHash)** | Immutable snapshot | Computed once, read-only after |
| **Option B (ASSET_CHANGE)** | Lock-protected registry | Existing infrastructure |
| **Option C (Dependency tracking)** | Per-page state | Not shared between threads |

**ContextVar is the recommended pattern** because:
- Already used throughout Bengal (ParseConfig, RenderConfig, RequestContext)
- ~8M ops/sec throughput (benchmarked in `rfc-free-threading-patterns.md`)
- Zero lock contention
- Matches Patitas architecture exactly

## Current Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Cache Invalidation Layers                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: In-Memory Caches (cache_registry.py)                  │
│  ├─ InvalidationReason enum (CONFIG_CHANGED, TEMPLATE_CHANGE)   │
│  ├─ Caches register which reasons they respond to               │
│  └─ Topological sort for dependency ordering                    │
│                                                                  │
│  Layer 2: Parsed Content Cache (ParsedContentCacheMixin)        │
│  ├─ Per-page validation: content hash, metadata, template       │
│  └─ Dependency graph: templates, partials                       │
│                                                                  │
│  Layer 3: Rendered Output Cache (RenderedOutputCacheMixin)      │
│  ├─ Per-page validation: content, metadata, template, deps      │
│  └─ ✅ FIXED (v0.1.9): asset_manifest_mtime validation          │
│                                                                  │
│  Global Invalidation:                                           │
│  ├─ config_hash → full cache clear                              │
│  └─ ⚠️ TACTICAL: asset_manifest_mtime (not hash-based yet)      │
│                                                                  │
│  Thread Safety (rendering/assets.py):                           │
│  └─ ❌ RACE CONDITION: Site._asset_manifest_cache               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Identified Global Dependencies

State that affects ALL rendered HTML:

| Dependency | Affects | Current Tracking | Thread-Safe? |
|-----------|---------|------------------|--------------|
| Config | All pages | ✅ `config_hash` | ✅ Yes |
| Asset manifest | All pages (fingerprinted URLs) | ✅ `asset_manifest_mtime` (v0.1.9) | ❌ Race condition |
| Theme assets | All pages (CSS/JS content) | ❌ None | N/A |
| Parser version | All pages (HTML structure) | ✅ Per-page | ✅ Yes |
| Base templates | All pages | ✅ Per-page dependency | ✅ Yes |

**Note**: Phase 1 tactical fix (v0.1.9) added `asset_manifest_mtime` validation, but the underlying cache lookup in `rendering/assets.py` still has a race condition that Phase 2 will fix.

## Proposed Solution

### Option A: Global Build State Hash (Recommended)

Add a unified `build_state_hash` that captures all global dependencies:

```python
@dataclass
class BuildStateHash:
    """Hash of all global state that affects rendered output."""
    config_hash: str
    asset_manifest_hash: str  # Hash of asset-manifest.json content
    theme_version: str        # Hash of theme config/assets

    def compute(self) -> str:
        """Combined hash for cache validation."""
        return hash_str(f"{self.config_hash}:{self.asset_manifest_hash}:{self.theme_version}")
```

**Validation flow:**
1. At build start, compute `BuildStateHash`
2. Store hash in rendered output cache entries
3. At cache retrieval, compare stored hash with current hash
4. Mismatch → invalidate cache

**Pros:**
- Single point of truth for global state
- Easy to extend with new global dependencies
- Clear semantics: "if global state changed, re-render"

**Cons:**
- Requires computing hash at build start
- All-or-nothing invalidation (can't selectively invalidate)

### Option B: Add ASSET_CHANGE to InvalidationReason

Extend the cache registry:

```python
class InvalidationReason(Enum):
    CONFIG_CHANGED = auto()
    STRUCTURAL_CHANGE = auto()
    NAV_CHANGE = auto()
    TEMPLATE_CHANGE = auto()
    ASSET_CHANGE = auto()  # NEW: Asset fingerprints changed
    FULL_REBUILD = auto()
```

Register rendered output cache to respond:

```python
register_cache(
    "rendered_output",
    cache.clear_rendered_output,
    invalidate_on={
        InvalidationReason.CONFIG_CHANGED,
        InvalidationReason.TEMPLATE_CHANGE,
        InvalidationReason.ASSET_CHANGE,  # NEW
    },
)
```

**Pros:**
- Uses existing infrastructure
- Clear semantics

**Cons:**
- BuildCache isn't in the registry (it's per-site, not global)
- Requires detecting asset manifest changes and triggering event

### Option C: Treat Asset Manifest as Global Dependency

Add `asset-manifest.json` to every page's dependency set:

```python
# In phase_assets, after manifest is written:
manifest_path = output_dir / "asset-manifest.json"
for page in site.pages:
    tracker.cache.add_dependency(page.source_path, manifest_path)
```

**Pros:**
- Uses existing dependency tracking
- Leverages existing validation logic

**Cons:**
- Semantic mismatch: manifest is an output, not a source
- Dependency graph explosion (every page → manifest)
- **O(n) overhead per build**: For a 1000-page site, adds 1000 `add_dependency()` calls
- **Validation overhead**: Every page cache lookup now checks manifest mtime
- **Reverse dependency bloat**: `reverse_dependencies[manifest_path]` contains ALL pages

**Performance Analysis:**

| Site Size | Dependency Entries Added | Memory Impact |
|-----------|-------------------------|---------------|
| 100 pages | +100 | ~8 KB |
| 1,000 pages | +1,000 | ~80 KB |
| 10,000 pages | +10,000 | ~800 KB |

While manageable, this creates unnecessary work when the manifest changes—the system would invalidate pages one-by-one via dependency graph traversal instead of a single "clear all rendered" operation.

## Recommendation

**Implement Option A (Global Build State Hash)** with immediate tactical fix:

### Phase 1: Tactical Fix (Done ✅)
Add `asset_manifest_mtime` to rendered output cache validation (implemented).

### Phase 2: ContextVar Asset Manifest (Free-Threading Fix)

Currently there are TWO asset manifest caches:

| Cache | Location | Scope | Thread-Safe? |
|-------|----------|-------|--------------|
| `Site._asset_manifest_cache` | `rendering/assets.py` | Per-site (shared) | ❌ No |
| `TemplateEngine._asset_manifest_cache` | `rendering/template_engine/manifest.py` | Per-engine (per-thread) | ✅ Yes |

**Consolidate to ContextVar pattern** (matches existing Patitas patterns):

1. Create `AssetManifestContext` frozen dataclass
2. Create `_asset_manifest: ContextVar[AssetManifestContext | None]`
3. Set context in `phase_render` before parallel rendering starts
4. Update `resolve_asset_url()` to use `get_asset_manifest()`
5. Remove `Site._asset_manifest_cache` pattern
6. Update `TemplateEngine` to use shared ContextVar (or keep per-engine, both work)

#### TemplateEngine Cache Consolidation Decision

**Recommendation**: Keep `TemplateEngine._asset_manifest_cache` for now.

| Approach | Pros | Cons |
|----------|------|------|
| **Consolidate to shared ContextVar** | Single source of truth, simpler mental model | Requires TemplateEngine refactor, may break subclasses |
| **Keep per-engine cache** | No breaking changes, already thread-safe | Two caches to maintain, potential consistency drift |

The TemplateEngine cache is already thread-safe (one engine per thread). Phase 2 focuses on fixing the `Site._asset_manifest_cache` race condition. Full consolidation can be deferred to Phase 3/4 if needed.

#### Cache Coherence Guarantees (Post-Phase 2)

After Phase 2, asset manifest access will have these guarantees:

1. **Set-Once-Per-Build**: Manifest is loaded once in `phase_render`, before parallel rendering starts
2. **Immutable During Render**: `AssetManifestContext` is frozen; entries dict is not mutated
3. **Thread-Local Access**: Each thread reads from ContextVar; no shared mutable state
4. **Automatic Cleanup**: Context manager resets ContextVar after render phase completes

```
┌─────────────────────────────────────────────────────────────┐
│                    Build Lifecycle                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  phase_assets:                                              │
│  └─ Generate asset-manifest.json (fingerprinted paths)     │
│                                                             │
│  phase_render:                                              │
│  ├─ Load manifest ONCE → AssetManifestContext (frozen)     │
│  ├─ Set ContextVar (_asset_manifest)                       │
│  ├─ Parallel render (threads read from ContextVar)         │
│  │   ├─ Thread 1: get_asset_manifest() → same ctx          │
│  │   ├─ Thread 2: get_asset_manifest() → same ctx          │
│  │   └─ Thread N: get_asset_manifest() → same ctx          │
│  └─ Reset ContextVar (context manager cleanup)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: Build State Abstraction
1. Create `BuildStateHash` dataclass
2. Compute at build start
3. Store in rendered output cache entries
4. Validate at retrieval

### Phase 4: Extend with Other Global Dependencies
- Theme version hash
- Environment-specific state
- Plugin state

## Test Coverage Improvements

Add tests for:

1. **Asset fingerprint change** → cache invalidation
2. **Theme asset change** → cache invalidation  
3. **CI cache restore with new asset fingerprints**
4. **Warm build with CSS content change**
5. **ContextVar thread isolation** (Phase 2)

### Test: Asset Manifest Change Invalidates Rendered Cache

```python
# tests/integration/cache/test_asset_manifest_invalidation.py
import json

def test_rendered_cache_invalidated_on_asset_manifest_change(tmp_path):
    """Rendered HTML cache should invalidate when asset fingerprints change."""
    site_dir = tmp_path / "site"
    content_dir = site_dir / "content"
    content_dir.mkdir(parents=True)

    # Create minimal site with CSS reference
    (content_dir / "_index.md").write_text("# Home\n")
    (site_dir / "assets" / "css").mkdir(parents=True)
    css_file = site_dir / "assets" / "css" / "style.css"
    css_file.write_text("body { color: black; }")

    # Build 1: Generate with fingerprint A
    site = Site.from_directory(site_dir)
    build(site)

    # Capture fingerprint from manifest
    manifest_path = site.output_dir / "asset-manifest.json"
    manifest_v1 = json.loads(manifest_path.read_text())
    fingerprint_v1 = manifest_v1["css/style.css"]["output_path"]

    # Verify HTML contains fingerprint A
    home_html = (site.output_dir / "index.html").read_text()
    assert fingerprint_v1 in home_html

    # Modify CSS → new fingerprint
    css_file.write_text("body { color: red; }")

    # Build 2 (incremental): Should detect manifest change
    build(site, incremental=True)

    # Verify new fingerprint in manifest
    manifest_v2 = json.loads(manifest_path.read_text())
    fingerprint_v2 = manifest_v2["css/style.css"]["output_path"]
    assert fingerprint_v1 != fingerprint_v2, "CSS change should produce new fingerprint"

    # Verify HTML updated with fingerprint B
    home_html_v2 = (site.output_dir / "index.html").read_text()
    assert fingerprint_v2 in home_html_v2, "Rendered cache should have been invalidated"
    assert fingerprint_v1 not in home_html_v2, "Old fingerprint should not be present"
```

### Test: ContextVar Thread Isolation (Phase 2)

```python
# tests/unit/rendering/test_asset_manifest_contextvar.py

def test_asset_manifest_contextvar_thread_isolation():
    """Each thread should have independent asset manifest context."""
    import threading
    import time
    from bengal.rendering.assets import (
        AssetManifestContext,
        asset_manifest_context,
        get_asset_manifest,
    )

    results = {}

    def worker(thread_id: int, entries: dict[str, str]):
        ctx = AssetManifestContext(entries=entries, mtime=None)
        with asset_manifest_context(ctx):
            # Simulate some work
            time.sleep(0.01)
            # Each thread should see its own entries
            manifest = get_asset_manifest()
            results[thread_id] = manifest.entries.get("test.css")

    threads = [
        threading.Thread(target=worker, args=(1, {"test.css": "test.abc.css"})),
        threading.Thread(target=worker, args=(2, {"test.css": "test.xyz.css"})),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Each thread should have seen its own value
    assert results[1] == "test.abc.css"
    assert results[2] == "test.xyz.css"
```

## Migration Path

1. **v0.1.10**: CSS/JS change detection in incremental filter ✅ (this fix)
2. **v0.2.0**: ContextVar pattern for asset manifest (free-threading hardening)
3. **v0.2.x**: BuildStateHash abstraction
4. **v0.3.x**: Additional global dependencies as needed

### v0.1.10 Changes (CSS/JS Detection) ✅

**Files Changed**:
- `bengal/orchestration/build/initialization.py` - Add fingerprint asset change detection
- `bengal/core/page/proxy.py` - Add `links` setter for PageProxy

**Key Code Addition** (`phase_incremental_filter`):

```python
# CRITICAL: If CSS/JS assets are changing, fingerprints will change.
# All pages embed fingerprinted asset URLs, so they must be rebuilt.
fingerprint_assets_changed = any(
    asset.source_path.suffix.lower() in {".css", ".js"}
    for asset in assets_to_process
)
if fingerprint_assets_changed and not pages_to_build:
    # Assets change but no content changes - force all pages to rebuild
    pages_to_build = list(orchestrator.site.pages)
    orchestrator.logger.info(
        "fingerprint_assets_changed_forcing_page_rebuild",
        assets_changed=len([a for a in assets_to_process if a.source_path.suffix.lower() in {".css", ".js"}]),
        pages_to_rebuild=len(pages_to_build),
    )
```

**Test Coverage**: `tests/integration/test_warm_build_virtual_page_assets.py`
- `test_css_change_triggers_page_rebuild` - Core regression test
- `test_js_change_triggers_page_rebuild` - JS variant
- `test_output_cleared_cache_retained_css_changed` - CI scenario

### v0.2.0 Changes (Free-Threading via ContextVar)

```python
# rendering/assets.py - BEFORE (race condition)
cache_attr = "_asset_manifest_cache"
manifest_cache = getattr(site, cache_attr, None)
if manifest_cache is None:
    setattr(site, cache_attr, loaded_cache)  # Race!

# rendering/assets.py - AFTER (ContextVar pattern)
from bengal.rendering.assets import get_asset_manifest

def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    ctx = get_asset_manifest()  # Thread-local, no lock needed
    if ctx is None:
        return None
    return ctx.entries.get(logical_path)
```

```python
# orchestration/render.py - Set context before parallel rendering
from bengal.rendering.assets import asset_manifest_context, AssetManifestContext

def phase_render(site: Site, ...):
    # Load manifest once
    manifest = AssetManifest.load(site.output_dir / "asset-manifest.json")
    ctx = AssetManifestContext(
        entries={k: v.output_path for k, v in manifest.entries.items()},
        mtime=manifest_path.stat().st_mtime if manifest_path.exists() else None,
    )

    # All parallel rendering happens inside context
    with asset_manifest_context(ctx):
        _render_parallel(pages, ...)  # Each thread reads from ContextVar
```

## Related Issues

- Home page missing assets on GH Pages (this bug) → **Fixed in v0.1.10** ✅
- `api/` and `cli/` autodoc pages missing on warm builds → Verified NOT an issue (existing `_check_autodoc_output_missing` handles this)
- Potential: Theme changes not reflected in cached pages
- Potential: Parser version changes not clearing rendered cache

## Open Questions

1. **TemplateEngine consolidation timing**: Should we consolidate `TemplateEngine._asset_manifest_cache` in Phase 2 or defer to later?
   - **Current recommendation**: Defer (no breaking changes, already thread-safe)

2. **Hash vs mtime for manifest validation**: Phase 1 uses mtime; Phase 3 (BuildStateHash) would use content hash.
   - **Trade-off**: Hash is more robust (survives CI cache restore with different mtimes) but adds compute cost
   - **Recommendation**: Keep mtime for Phase 2, add hash in Phase 3

3. **Theme version tracking**: How to detect theme asset changes?
   - **Option**: Hash all files in `themes/{theme}/assets/`
   - **Option**: Use theme config's `version` field if present
   - **Deferred to Phase 4**

## Appendix: Other SSGs' Approaches

| SSG | Global State Tracking | Cache Invalidation Strategy |
|-----|----------------------|----------------------------|
| **Hugo** | Content hashes + render output hashes | Per-page hash comparison |
| **Gatsby** | Full config/plugin hash | Full rebuild on config change, incremental on content |
| **Eleventy** | Dependency graph (includes data files) | Graph traversal, no asset tracking |
| **Zola** | Full rebuild always | No incremental builds |

Bengal's approach (Phase 3+) will be closest to Hugo: per-page validation with global state hash.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | Tactical fix: `asset_manifest_mtime` | Immediate bug fix for GH Pages |
| 2026-01-13 | RFC approved for Phase 2 | ContextVar pattern aligns with existing Bengal patterns |
| 2026-01-13 | Phase 2: ContextVar implementation ✅ | Fix race condition for free-threading |
| 2026-01-13 | Created `rfc-asset-resolution-observability.md` | Observability gap discovered during Phase 2 implementation |
| TBD | Phase 3: BuildStateHash | Unified global state tracking |

---

## Related RFCs

- **`rfc-asset-resolution-observability.md`** - Structured logging and stats tracking for asset resolution (created during Phase 2)
