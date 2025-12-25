# RFC: Cache Compression Consistency

**Status**: Drafted  
**Created**: 2025-12-25  
**Author**: AI Assistant  
**Effort**: Low (~2 hours)  
**Impact**: 40% reduction in `.bengal/` cache size

---

## Summary

Migrate three auxiliary cache files from raw JSON to compressed format using the existing `CacheStore` infrastructure. This brings consistency to the caching layer and reduces `.bengal/` directory size by ~2.8M (40%).

---

## Problem

The `.bengal/` directory has **inconsistent caching patterns**:

| File | Current Format | Uses CacheStore | Size |
|------|----------------|-----------------|------|
| `cache.json.zst` | Compressed | ✅ Yes | 2.8M |
| `asset_deps.json` | Raw JSON | ❌ No | 1.5M |
| `page_metadata.json` | Raw JSON | ❌ No | 1.3M |
| `taxonomy_index.json` | Raw JSON | ❌ No | 200K |

The three auxiliary caches were written before `CacheStore` existed and use direct `json.dump()` calls, bypassing compression.

**Current total**: 6.8M  
**With compression**: ~4.0M  
**Savings**: ~2.8M (41%)

---

## Background

### CacheStore Architecture

`CacheStore` (`bengal/cache/cache_store.py`) provides:
- Zstandard compression (92-93% size reduction)
- Type-safe serialization via `Cacheable` protocol
- Version management with tolerant loading
- Backward compatibility (reads both `.json.zst` and `.json`)

```python
class CacheStore:
    def __init__(self, cache_path: Path, compress: bool = True):
        ...
```

### Current Auxiliary Cache Pattern

All three auxiliary caches use the same anti-pattern:

```python
# TaxonomyIndex.save_to_disk() - lines 197-198
with open(self.cache_path, "w") as f:
    json.dump(data, f, indent=2)
```

This bypasses:
1. Compression (12-14x size reduction)
2. Atomic writes (crash safety)
3. Version header validation

---

## Proposal

### Phase 1: Migrate to CacheStore

Refactor each auxiliary cache class to use `CacheStore` internally:

#### 1. TaxonomyIndex (`bengal/cache/taxonomy_index.py`)

**Before**:
```python
def save_to_disk(self) -> None:
    data = {
        "version": self.VERSION,
        "tags": {tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()},
        "page_to_tags": {page: list(tags) for page, tags in self._page_to_tags.items()},
    }
    with open(self.cache_path, "w") as f:
        json.dump(data, f, indent=2)
```

**After**:
```python
from bengal.cache.compression import save_compressed, load_with_fallback

def save_to_disk(self) -> None:
    data = {
        "version": self.VERSION,
        "tags": {tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()},
        "page_to_tags": {page: list(tags) for page, tags in self._page_to_tags.items()},
    }
    compressed_path = self.cache_path.with_suffix(".json.zst")
    save_compressed(data, compressed_path)

def _load_from_disk(self) -> None:
    try:
        data = load_with_fallback(self.cache_path)
        # ... rest of loading logic
    except FileNotFoundError:
        self.tags = {}
        self._page_to_tags = {}
```

#### 2. AssetDependencyMap (`bengal/cache/asset_dependency_map.py`)

Same pattern: replace `json.dump()` with `save_compressed()`, use `load_with_fallback()` for backward-compatible loading.

#### 3. PageDiscoveryCache (`bengal/cache/page_discovery_cache.py`)

Same pattern.

### Phase 2: Update BengalPaths

Update `bengal/cache/paths.py` to reflect the new `.zst` extensions:

```python
@property
def taxonomy_cache(self) -> Path:
    """Taxonomy index cache file (.bengal/taxonomy_index.json.zst)."""
    return self.state_dir / "taxonomy_index.json.zst"

@property
def asset_cache(self) -> Path:
    """Asset dependency map file (.bengal/asset_deps.json.zst)."""
    return self.state_dir / "asset_deps.json.zst"

@property
def page_cache(self) -> Path:
    """Page discovery cache file (.bengal/page_metadata.json.zst)."""
    return self.state_dir / "page_metadata.json.zst"
```

**Note**: `load_with_fallback()` already handles backward compatibility by trying `.json.zst` first, then falling back to `.json`.

### Phase 3: Clean Command Update

Update `bengal clean --cache` to clean both compressed and uncompressed variants during migration period.

---

## Migration Strategy

### Backward Compatibility

The `load_with_fallback()` function already provides seamless migration:

```python
def load_with_fallback(path: Path) -> dict[str, Any]:
    """Load cache file with automatic format detection.

    Tries compressed format first (.json.zst), falls back to JSON (.json).
    """
    compressed_path = get_compressed_path(path)
    if compressed_path.exists():
        return load_compressed(compressed_path)

    # Fall back to uncompressed JSON
    json_path = path if path.suffix == ".json" else path.with_suffix(".json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(...)
```

### Rollout

1. **v0.1.7**: Implement changes, save compressed, load both formats
2. **v0.2.0**: Remove fallback loading (breaking change for very old caches)

---

## Implementation

### Files to Modify

| File | Changes |
|------|---------|
| `bengal/cache/taxonomy_index.py` | Use `save_compressed()`, `load_with_fallback()` |
| `bengal/cache/asset_dependency_map.py` | Use `save_compressed()`, `load_with_fallback()` |
| `bengal/cache/page_discovery_cache.py` | Use `save_compressed()`, `load_with_fallback()` |
| `bengal/cache/paths.py` | Update docstrings (paths remain `.json` for fallback) |
| `cli/commands/clean.py` | Clean both `.json` and `.json.zst` variants |

### Estimated Changes

- ~30 lines per cache class (3 classes)
- ~10 lines in paths.py
- ~5 lines in clean.py
- **Total**: ~100 lines changed

---

## Size Impact

Based on current `site/.bengal/` measurements:

| File | Before | After (92% compression) | Savings |
|------|--------|-------------------------|---------|
| `cache.json.zst` | 2.8M | 2.8M (already compressed) | 0 |
| `asset_deps.json` | 1.5M | ~120K | 1.38M |
| `page_metadata.json` | 1.3M | ~104K | 1.2M |
| `taxonomy_index.json` | 200K | ~16K | 184K |
| **Total** | **5.8M** | **~3.0M** | **~2.8M (48%)** |

---

## Performance Impact

Based on compression benchmarks from `bengal/cache/compression.py`:

| Operation | Overhead |
|-----------|----------|
| Compress | <1ms per file |
| Decompress | <0.3ms per file |
| **Total build impact** | <3ms |

Negligible impact on build times.

---

## Testing

1. **Unit tests**: Verify round-trip serialization for each cache type
2. **Migration test**: Load old `.json` format, save new `.zst` format
3. **Build test**: Full site build with fresh cache, verify sizes
4. **Clean test**: `bengal clean --cache` removes both formats

---

## Alternatives Considered

### 1. Keep JSON for Debugging

**Rejected**: Zstd files can be inspected with `zstd -d < file.json.zst | jq .` and the compression benefits outweigh debugging convenience.

### 2. Consolidate into Single Cache File

**Rejected**: Separate files allow independent updates. Taxonomy changes shouldn't invalidate page metadata cache.

### 3. Use Different Compression Levels

**Rejected**: Level 3 (default) provides optimal balance of speed and compression. Higher levels have diminishing returns.

---

## Checklist

- [ ] Update `TaxonomyIndex.save_to_disk()` and `_load_from_disk()`
- [ ] Update `AssetDependencyMap.save_to_disk()` and `load_from_disk()`
- [ ] Update `PageDiscoveryCache.save_to_disk()` and `load_from_disk()`
- [ ] Update `BengalPaths` docstrings
- [ ] Update `bengal clean --cache` to handle both formats
- [ ] Add unit tests for round-trip serialization
- [ ] Verify backward compatibility with existing `.json` caches
- [ ] Update `.bengal/` documentation in `paths.py`
- [ ] Test full build cycle

---

## References

- `bengal/cache/cache_store.py` - CacheStore implementation
- `bengal/cache/compression.py` - Zstd compression utilities
- `bengal/cache/paths.py` - BengalPaths directory structure
- `bengal/cache/build_cache/core.py` - Main build cache (already compressed)
