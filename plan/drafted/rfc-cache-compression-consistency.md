# RFC: Cache Compression Consistency

**Status**: Drafted (Updated after evaluation)  
**Created**: 2025-12-25  
**Updated**: 2025-12-25  
**Author**: AI Assistant  
**Effort**: Low (~2 hours)  
**Impact**: 40% reduction in `.bengal/` cache size  
**Evaluation**: `plan/evaluated/rfc-cache-compression-consistency-evaluation.md`

---

## Summary

Migrate three auxiliary cache files from raw JSON to compressed format using the existing compression utilities (`bengal/cache/compression.py`). This brings consistency to the caching layer and reduces `.bengal/` directory size by ~2.8M (40%).

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

### Compression Infrastructure

Bengal already has compression utilities (`bengal/cache/compression.py`) that provide:
- Zstandard compression (92-93% size reduction, 12-14x ratio)
- Automatic format detection (`load_auto()` tries `.json.zst` first, falls back to `.json`)
- Version header validation
- Atomic writes (crash safety)
- Backward compatibility (reads both compressed and uncompressed formats)

**Key Functions**:
- `save_compressed(data, path)` - Save data as compressed `.json.zst` with version header
- `load_auto(path)` - Load with automatic format detection (`.json.zst` → `.json` fallback)
- `load_compressed(path)` - Load compressed file directly

**Note**: While `CacheStore` (`bengal/cache/cache_store.py`) uses these utilities for `Cacheable` types, the three auxiliary caches have custom formats and will use the compression utilities directly.

### Current Auxiliary Cache Pattern

All three auxiliary caches use the same anti-pattern:

```python
# TaxonomyIndex.save_to_disk() - lines 197-198
with open(self.cache_path, "w") as f:
    json.dump(data, f, indent=2)
```

This bypasses:
1. Compression (12-14x size reduction)
2. Atomic writes (crash safety - though `AssetDependencyMap` and `PageDiscoveryCache` use `AtomicFile`)
3. Version header validation

---

## Proposal

### Phase 1: Migrate to Compression

Refactor each auxiliary cache class to use compression utilities (`save_compressed()`, `load_auto()`) directly:

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
from bengal.cache.compression import save_compressed, load_auto

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
        data = load_auto(self.cache_path)  # Auto-detects .json.zst or .json
        # ... rest of loading logic
    except FileNotFoundError:
        self.tags = {}
        self._page_to_tags = {}
```

**Note**: `load_auto()` automatically tries `.json.zst` first, then falls back to `.json` if not found. This provides seamless backward compatibility during migration.

#### 2. AssetDependencyMap (`bengal/cache/asset_dependency_map.py`)

Same pattern: replace `json.dump()` with `save_compressed()`, use `load_auto()` for backward-compatible loading.

#### 3. PageDiscoveryCache (`bengal/cache/page_discovery_cache.py`)

Same pattern.

### Phase 2: Update BengalPaths Docstrings

Update `bengal/cache/paths.py` docstrings to document compression support. **Keep path names as `.json`** - `load_auto()` and `save_compressed()` handle the `.zst` extension automatically:

```python
@property
def taxonomy_cache(self) -> Path:
    """Taxonomy index cache file (.bengal/taxonomy_index.json or .json.zst)."""
    return self.state_dir / "taxonomy_index.json"

@property
def asset_cache(self) -> Path:
    """Asset dependency map file (.bengal/asset_deps.json or .json.zst)."""
    return self.state_dir / "asset_deps.json"

@property
def page_cache(self) -> Path:
    """Page discovery cache file (.bengal/page_metadata.json or .json.zst)."""
    return self.state_dir / "page_metadata.json"
```

**Rationale**: Keeping paths as `.json` maintains backward compatibility and allows `load_auto()` to automatically detect the correct format. The compression utilities handle extension resolution internally.

### Phase 3: Clean Command (No Changes Needed)

The `bengal clean --cache` command already removes the entire `.bengal/` directory, which automatically cleans both `.json` and `.json.zst` variants. **No code changes required**.

---

## Migration Strategy

### Backward Compatibility

The `load_auto()` function (`bengal/cache/compression.py:218`) provides seamless migration with automatic format detection:

```python
def load_auto(path: Path) -> dict[str, Any]:
    """Load cache file with automatic format detection.

    Tries compressed format first (.json.zst), falls back to JSON (.json).
    This enables seamless migration from uncompressed to compressed caches.
    """
    # Try compressed first
    compressed_path = get_compressed_path(path)
    if compressed_path.exists():
        try:
            return load_compressed(compressed_path)
        except CacheVersionError:
            # Incompatible version - fallback to JSON or re-raise if no JSON
            logger.debug("compressed_cache_incompatible", path=str(compressed_path))

    # Fall back to uncompressed JSON
    json_path = path if path.suffix == ".json" else path.with_suffix(".json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(f"Cache file not found: {path} (tried .json.zst and .json)")
```

**Behavior**:
1. Tries `.json.zst` first (new compressed format)
2. Falls back to `.json` if compressed file doesn't exist (backward compatibility)
3. Handles version mismatches gracefully
4. Raises `FileNotFoundError` if neither format exists

### Rollout

1. **v0.1.7**: Implement changes, save compressed, load both formats
2. **v0.2.0**: Remove fallback loading (breaking change for very old caches)

---

## Implementation

### Files to Modify

| File | Changes |
|------|---------|
| `bengal/cache/taxonomy_index.py` | Use `save_compressed()`, `load_auto()` |
| `bengal/cache/asset_dependency_map.py` | Use `save_compressed()`, `load_auto()` |
| `bengal/cache/page_discovery_cache.py` | Use `save_compressed()`, `load_auto()` |
| `bengal/cache/paths.py` | Update docstrings only (paths remain `.json`) |

### Estimated Changes

- ~30 lines per cache class (3 classes)
- ~10 lines in paths.py (docstrings only)
- **Total**: ~100 lines changed

**Note**: `bengal clean --cache` already removes the entire `.bengal/` directory, so no changes needed for clean command.

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
2. **Migration test**: Load old `.json` format, save new `.zst` format, verify `load_auto()` fallback works
3. **Build test**: Full site build with fresh cache, verify sizes match expected compression ratios
4. **Backward compatibility test**: Verify existing `.json` caches load correctly and are migrated to `.zst` on save
5. **Version mismatch test**: Verify `load_auto()` handles incompatible compressed cache versions gracefully
6. **Clean test**: Verify `bengal clean --cache` removes both `.json` and `.json.zst` formats (already works)

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

- [ ] Update `TaxonomyIndex.save_to_disk()` to use `save_compressed()`
- [ ] Update `TaxonomyIndex._load_from_disk()` to use `load_auto()`
- [ ] Update `AssetDependencyMap.save_to_disk()` to use `save_compressed()`
- [ ] Update `AssetDependencyMap._load_from_disk()` to use `load_auto()`
- [ ] Update `PageDiscoveryCache.save_to_disk()` to use `save_compressed()`
- [ ] Update `PageDiscoveryCache._load_from_disk()` to use `load_auto()`
- [ ] Update `BengalPaths` docstrings (keep paths as `.json`)
- [ ] Add unit tests for round-trip serialization
- [ ] Add migration test (load old `.json`, save new `.zst`)
- [ ] Verify backward compatibility with existing `.json` caches
- [ ] Test `load_auto()` fallback behavior
- [ ] Test version mismatch handling
- [ ] Test full build cycle with compressed caches
- [ ] Verify cache sizes match expected compression ratios (92-93% reduction)

---

## References

- `bengal/cache/cache_store.py` - CacheStore implementation
- `bengal/cache/compression.py` - Zstd compression utilities (`save_compressed()`, `load_auto()`)
- `bengal/cache/paths.py` - BengalPaths directory structure
- `bengal/cache/build_cache/core.py` - Main build cache (already compressed)
- `bengal/cache/taxonomy_index.py` - TaxonomyIndex implementation
- `bengal/cache/asset_dependency_map.py` - AssetDependencyMap implementation
- `bengal/cache/page_discovery_cache.py` - PageDiscoveryCache implementation
