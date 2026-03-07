# Short-Circuit Solution Patterns

**Status**: Proposal  
**Created**: 2026-03-07  
**Category**: Build / Performance

---

## Code Deep Dive Summary

### Pattern 1: mtime-Before-Hash (FileTrackingMixin)

**Location**: `bengal/cache/build_cache/file_tracking.py:127-208`

**Current implementation** (already optimal):
```python
# Fast path: mtime + size unchanged = definitely no change
if cached_mtime == current_mtime and cached_size == current_size:
    return False
# mtime or size changed - verify with hash (handles touch/rsync)
current_hash = self.hash_file(file_path)
```

**Pattern**: Check cheap metadata (mtime, size) first; only hash when metadata suggests change.

---

### Pattern 2: Provenance Filter (Needs mtime Short-Circuit)

**Location**: `bengal/build/provenance/filter.py:252-306`, `507-566`

**Current flow**:
1. `_verify_page_provenance` called for every page with stored hash
2. `_compute_provenance_fast` / `_compute_provenance` always hashes:
   - Content file
   - Cascade sources (_index.md)
   - Config (cached)
   - Autodoc source (virtual pages)

**Gap**: No mtime check before hashing. Every page triggers file reads + SHA256.

**Solution**: See `plan/rfc-provenance-mtime-short-circuit.md`. Store `input_paths` + `last_build_time`; check `all(mtime ≤ last_build)` before hashing.

---

### Pattern 3: Parsed Content Cache – Dependency Validation

**Location**: `bengal/cache/build_cache/parsed_content_cache.py:184-233`

**Current implementation**:
```python
# Validate dependencies using content hash (not mtime).
if key in self.dependencies:
    for dep_path in self.dependencies[key]:
        dep = Path(dep_path)
        cached_fp = self.file_fingerprints.get(dep_path)
        # ...
        current_hash = hash_file(dep)  # ALWAYS hashes
        if current_hash != cached_hash:
            return MISSING
```

**Gap**: Bypasses `is_changed()` (which does mtime-first) and always hashes. Comment says "content hash prevents false invalidations" but `is_changed` already handles touch/rsync via mtime+size then hash.

**Solution**: Use `is_changed()` instead of direct `hash_file()`. Requires resolving `dep_path` (CacheKey string) to full Path.

```python
# Proposed change
if key in self.dependencies:
    for dep_path in self.dependencies[key]:
        full_dep = self._resolve_dep_path(dep_path)
        if full_dep is None or self.is_changed(full_dep):
            return MISSING
```

**Path resolution**: `dep_path` is content_key format (e.g. `templates/base.html`). BuildCache has `site_root`. Resolve: `site_root / dep_path` when `dep_path` not absolute. Handle `site_root is None` (fallback to Path(dep_path) or skip).

---

### Pattern 4: Asset Hashing in Provenance Filter

**Location**: `bengal/build/provenance/filter.py:767-813`

**Current implementation**:
```python
# OPTIMIZATION: If we have a stored hash, check mtime first
if stored_hash is not None:
    _ = asset.source_path.stat().st_mtime  # Does NOT use result!
# Compute hash (necessary for correctness)
current_hash = self._get_file_hash(asset.source_path)  # Always hashes
```

**Gap**: mtime is read but never used. Always hashes.

**Solution**: Store mtime+size in `asset_hashes.json`; short-circuit when unchanged.

**Data format change**:
```json
// Current: {"layouts/style.css": "abc123"}
// Proposed: {"layouts/style.css": {"hash": "abc123", "mtime": 1709827353.0, "size": 1024}}
```

**Logic**:
```python
def _is_asset_changed(self, asset: Asset) -> bool:
    if not asset.source_path.exists():
        return True
    asset_path = self._get_asset_key(asset)
    stored = self._asset_hashes.get(asset_path)

    try:
        stat = asset.source_path.stat()
        current_mtime, current_size = stat.st_mtime, stat.st_size
    except OSError:
        return True

    # Short-circuit: mtime+size match → unchanged
    if stored and isinstance(stored, dict):
        if stored.get("mtime") == current_mtime and stored.get("size") == current_size:
            return False
        cached_hash = stored.get("hash") if isinstance(stored, dict) else stored
    else:
        cached_hash = stored  # Backward compat: old format was hash-only

    current_hash = self._get_file_hash(asset.source_path)
    self._asset_hashes[asset_path] = {"hash": current_hash, "mtime": current_mtime, "size": current_size}
    return current_hash != (cached_hash if isinstance(cached_hash, str) else cached_hash)
```

---

### Pattern 5: Rendered Output Cache – Template Deps

**Location**: `bengal/cache/build_cache/rendered_output_cache.py:186-191`

**Current implementation**:
```python
for dep_path in cached.get("dependencies", []):
    dep = Path(dep_path)
    if dep.exists() and self.is_changed(dep):
        return MISSING
```

**Status**: Already uses `is_changed()` which does mtime-first. No change needed.

---

### Pattern 6: Fast Mode (Already Implemented)

**Location**: `bengal/rendering/pipeline/output.py:305-306`

```python
if build_cfg.get("fast_mode", False):
    return html  # Return raw HTML without formatting
```

**Status**: Implemented. Users enable via `build.fast_mode: true` in config.

---

## Proposed Solution Patterns (Reusable)

### Pattern A: mtime-Before-Hash

**When**: Validating file unchanged for cache hit.

**Steps**:
1. Store `{mtime, size, hash}` when first seen
2. On check: `stat()` → if mtime+size match stored → return "unchanged"
3. If mismatch: hash → compare → update stored mtime/size if content same (touch case)

**Used by**: FileTrackingMixin ✅, Provenance asset hashes ❌, Parsed content deps (via is_changed) ❌

### Pattern B: Input-Paths + Timestamp

**When**: Validating N inputs for a single output (e.g. page provenance).

**Steps**:
1. Store `last_build_time` when build completes
2. Store `input_paths: [rel_path, ...]` per output
3. On check: for each path, `stat().st_mtime`; if all ≤ last_build_time → skip hashing

**Used by**: Provenance filter (planned)

### Pattern C: Delegate to Existing mtime-Check

**When**: Dependency validation where `is_changed()` exists and accepts Path.

**Steps**:
1. Resolve dependency key to Path (may need site_root)
2. Call `is_changed(resolved_path)` instead of `hash_file()`
3. Ensure dependency is in file_fingerprints (tracked during render)

**Used by**: Parsed content cache (replace hash loop with is_changed)

### Pattern D: Structured Cache Entry

**When**: Cache stores single value but could store metadata for short-circuit.

**Steps**:
1. Extend format: `{value, mtime?, size?}` with backward compat
2. Load: accept both old (value) and new (dict) format
3. Check: use mtime/size when available

**Used by**: Asset hashes in provenance

---

## Implementation Order

| # | Change | File(s) | Effort | Impact |
|---|--------|---------|--------|--------|
| 1 | Provenance mtime short-circuit | store.py, filter.py | Medium | High |
| 2 | Asset hash mtime+size | filter.py | Low | Medium |
| 3 | Parsed content: use is_changed for deps | parsed_content_cache.py | Low | Medium |
| 4 | Parsed content: dep path resolution | parsed_content_cache.py | Low | — |

---

## Path Resolution for Parsed Content Deps

**Problem**: `dependencies[key]` contains CacheKey strings (e.g. `templates/base.html`, `content/docs/_index.md`). Need Path for `is_changed()`.

**BuildCache** has `site_root: Path | None`. Dependencies are added via `add_dependency(source, dependency)` where dependency is a Path. The stored key is `_cache_key(dependency)` = `content_key(dependency, site_root)`.

For `content_key`, paths relative to site_root produce keys like `content/docs/foo.md`. For templates at `site_root/templates/base.html`, key is `templates/base.html`.

**Resolution**:
```python
def _resolve_dep_path(self, dep_key: str) -> Path | None:
    """Resolve CacheKey to filesystem Path for is_changed()."""
    if self.site_root is None:
        return None
    # dep_key is relative to site_root (from content_key)
    if dep_key.startswith("/"):
        return Path(dep_key)
    full = self.site_root / dep_key
    return full if full.exists() else None
```

**Edge case**: Template paths. `template_key` uses templates_dir. When add_dependency is called, what path format is used? Need to trace. If templates are under site root, `content_key` would work. If theme templates are external, key might be absolute. The `content_key` for path outside base uses `path.resolve()` (absolute). So we need: if key starts with `/` or has `:`, handle specially. For simple case: `site_root / dep_key`.

---

## Backward Compatibility

| Change | Migration |
|--------|-----------|
| Provenance index v2 | Old index: skip mtime, full verify |
| Asset hashes format | Accept `"hash"` (str) or `{"hash", "mtime", "size"}` |
| Parsed content deps | No format change; logic change only |
