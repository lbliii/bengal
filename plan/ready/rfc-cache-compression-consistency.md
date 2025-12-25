# Plan: Cache Compression Consistency

**RFC**: `plan/evaluated/rfc-cache-compression-consistency-evaluation.md`  
**Status**: Ready  
**Created**: 2025-12-25  
**Estimated Effort**: ~2 hours  
**Subsystem**: `bengal/cache/`

---

## Overview

Migrate three auxiliary cache files (`taxonomy_index.json`, `asset_deps.json`, `page_metadata.json`) from raw JSON to compressed `.json.zst` format using existing compression utilities. This brings consistency to the caching layer and reduces `.bengal/` directory size by ~40% (~2.8M savings).

**Key Phases**:
1. **Implementation**: Update three cache classes to use `save_compressed()` and `load_auto()`
2. **Documentation**: Update `BengalPaths` docstrings to reflect compression support
3. **Testing**: Add unit tests for round-trip serialization and migration scenarios

---

## Phase 1: Implementation

### Task 1.1: Migrate TaxonomyIndex to Compression

**Subsystem**: Cache  
**File**: `bengal/cache/taxonomy_index.py`  
**Changes**:
- Replace `json.dump()` with `save_compressed()` in `save_to_disk()`
- Replace `json.load()` with `load_auto()` in `_load_from_disk()`
- Add import: `from bengal.cache.compression import save_compressed, load_auto`
- Update path handling: use `self.cache_path.with_suffix(".json.zst")` for save, `self.cache_path` for load (load_auto handles extension)

**Commit**: `cache: migrate TaxonomyIndex to compressed format using save_compressed/load_auto`

**Details**:
- Line 197-198: Replace `json.dump()` with `save_compressed()`
- Line 140-142: Replace `json.load()` with `load_auto()`
- `load_auto()` automatically tries `.json.zst` first, falls back to `.json` for backward compatibility

---

### Task 1.2: Migrate AssetDependencyMap to Compression

**Subsystem**: Cache  
**File**: `bengal/cache/asset_dependency_map.py`  
**Changes**:
- Replace `json.dump()` with `save_compressed()` in `save_to_disk()`
- Replace `json.load()` with `load_auto()` in `_load_from_disk()`
- Remove `AtomicFile` wrapper (compression utilities handle atomic writes)
- Add import: `from bengal.cache.compression import save_compressed, load_auto`

**Commit**: `cache: migrate AssetDependencyMap to compressed format; remove AtomicFile wrapper`

**Details**:
- Line 186-187: Replace `AtomicFile` + `json.dump()` with `save_compressed()`
- Line 141-142: Replace `json.load()` with `load_auto()`
- `save_compressed()` already provides atomic writes, so `AtomicFile` wrapper is redundant

---

### Task 1.3: Migrate PageDiscoveryCache to Compression

**Subsystem**: Cache  
**File**: `bengal/cache/page_discovery_cache.py`  
**Changes**:
- Replace `json.dump()` with `save_compressed()` in `save_to_disk()`
- Replace `json.load()` with `load_auto()` in `_load_from_disk()`
- Remove `AtomicFile` wrapper (compression utilities handle atomic writes)
- Remove `default=str` parameter (not needed - `save_compressed()` already uses `default=str` internally)
- Add import: `from bengal.cache.compression import save_compressed, load_auto`

**Commit**: `cache: migrate PageDiscoveryCache to compressed format; remove AtomicFile wrapper`

**Details**:
- Line 189-191: Replace `AtomicFile` + `json.dump()` with `save_compressed()`
- Line 140-141: Replace `json.load()` with `load_auto()`
- Note: `save_compressed()` already uses `default=str` internally (line 98 in `compression.py`), so datetime serialization is handled automatically

---

### Task 1.4: Update BengalPaths Docstrings

**Subsystem**: Cache  
**File**: `bengal/cache/paths.py`  
**Changes**:
- Update docstrings for `taxonomy_cache`, `asset_cache`, and `page_cache` properties
- Document that files may be `.json` or `.json.zst` format
- Keep path names as `.json` (compression utilities handle extension automatically)

**Commit**: `cache(paths): update docstrings to document compression support for auxiliary caches`

**Details**:
- Line 105-117: Update docstrings to mention `.json` or `.json.zst` formats
- Keep return values as `.json` paths (load_auto handles detection)

---

## Phase 2: Testing

### Task 2.1: Add Round-Trip Serialization Tests

**Subsystem**: Tests  
**Files**:
- `tests/cache/test_taxonomy_index.py`
- `tests/cache/test_asset_dependency_map.py`
- `tests/cache/test_page_discovery_cache.py`

**Changes**:
- Add tests verifying save/load cycle with compressed format
- Verify data integrity after round-trip
- Verify compression ratio matches expected (~92-93% reduction)

**Commit**: `tests(cache): add round-trip serialization tests for compressed auxiliary caches`

**Details**:
- Test that `save_to_disk()` creates `.json.zst` file
- Test that `_load_from_disk()` reads `.json.zst` file correctly
- Verify data matches original after save/load cycle
- Verify file size reduction matches expected compression ratio

---

### Task 2.2: Add Migration Tests

**Subsystem**: Tests  
**Files**: Same as Task 2.1

**Changes**:
- Add tests for backward compatibility: load old `.json` format, save new `.json.zst` format
- Verify `load_auto()` fallback behavior (tries `.json.zst` first, falls back to `.json`)
- Test version mismatch handling (if applicable)

**Commit**: `tests(cache): add migration tests for backward compatibility with old JSON caches`

**Details**:
- Create old `.json` format cache file
- Verify `load_auto()` successfully loads it
- Verify save creates new `.json.zst` format
- Verify subsequent loads use compressed format

---

### Task 2.3: Add Integration Test for Full Build Cycle

**Subsystem**: Tests  
**File**: `tests/cache/test_cache_compression.py` (new file or existing integration test)

**Changes**:
- Test full site build with compressed caches
- Verify cache sizes match expected compression ratios
- Verify build performance impact is negligible (<3ms)

**Commit**: `tests(cache): add integration test for compressed cache build cycle`

**Details**:
- Build a test site
- Verify all three auxiliary caches are compressed
- Verify cache sizes match expected ratios (92-93% reduction)
- Measure build time impact (should be <3ms)

---

## Implementation Checklist

### Phase 1: Implementation
- [ ] Task 1.1: Migrate TaxonomyIndex to compression
- [ ] Task 1.2: Migrate AssetDependencyMap to compression
- [ ] Task 1.3: Migrate PageDiscoveryCache to compression
- [ ] Task 1.4: Update BengalPaths docstrings

### Phase 2: Testing
- [ ] Task 2.1: Add round-trip serialization tests
- [ ] Task 2.2: Add migration tests
- [ ] Task 2.3: Add integration test for full build cycle

### Verification
- [ ] Verify backward compatibility: existing `.json` caches load correctly
- [ ] Verify migration: old `.json` files are migrated to `.json.zst` on save
- [ ] Verify compression ratios: ~92-93% size reduction achieved
- [ ] Verify performance: build time impact <3ms
- [ ] Verify `bengal clean --cache` removes both formats (already works, no changes needed)

---

## Notes

### Corrections from Evaluation

1. **Function Name**: Use `load_auto()` not `load_with_fallback()` (doesn't exist)
2. **Path Updates**: Keep `BengalPaths` paths as `.json` - update docstrings only
3. **Clean Command**: No changes needed - current implementation already handles both formats

### Implementation Details

- **Atomic Writes**: `save_compressed()` already provides atomic writes, so `AtomicFile` wrapper can be removed from `AssetDependencyMap` and `PageDiscoveryCache`
- **Backward Compatibility**: `load_auto()` automatically tries `.json.zst` first, falls back to `.json` if not found
- **Path Handling**: Keep paths as `.json` in `BengalPaths` - compression utilities handle extension resolution internally
- **DateTime Serialization**: `save_compressed()` already uses `default=str` internally (line 98 in `compression.py`), so `PageDiscoveryCache` doesn't need special handling

### Expected Outcomes

- **Size Reduction**: ~2.8M savings (40% reduction in `.bengal/` directory)
- **Performance Impact**: <3ms total build overhead
- **Backward Compatibility**: Seamless migration from `.json` to `.json.zst`
- **Consistency**: All cache files now use compression

---

## References

- **RFC**: `plan/evaluated/rfc-cache-compression-consistency-evaluation.md`
- **Compression Module**: `bengal/cache/compression.py` (lines 218-249 for `load_auto()`)
- **TaxonomyIndex**: `bengal/cache/taxonomy_index.py` (lines 197-198, 140-142)
- **AssetDependencyMap**: `bengal/cache/asset_dependency_map.py` (lines 186-187, 141-142)
- **PageDiscoveryCache**: `bengal/cache/page_discovery_cache.py` (lines 189-191, 140-141)
- **BengalPaths**: `bengal/cache/paths.py` (lines 105-117)
