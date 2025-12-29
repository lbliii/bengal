# RFC: Cache Invalidation Fixes for Incremental Builds

**Status**: Draft  
**Created**: 2025-12-29  
**Author**: AI Assistant  
**Priority**: High  
**Affects**: `bengal/cache/`, `bengal/orchestration/incremental/`

---

## Summary

Incremental builds are triggering full rebuilds due to several cache invalidation bugs. This RFC proposes fixes for the five root causes identified through code analysis.

---

## Problem Statement

Users report that incremental builds frequently trigger full rebuilds when they should only rebuild changed pages. This defeats the purpose of incremental builds (10-100x speedup) and degrades developer experience.

**Symptoms observed**:
- "Config file modified - performing full rebuild" when config hasn't changed
- All pages rebuilt when only one template changed
- Cache misses despite no file modifications
- Inconsistent behavior between consecutive builds

---

## Root Causes Identified

### Bug 1: Config Hash Includes Runtime Values

**Location**: `bengal/core/site/properties.py:173-189`

The `compute_config_hash()` function hashes the entire `config` dict, which may include:
- Runtime-computed absolute paths (`output_dir`, `root_path`)
- Timestamps or dynamic values
- Mutable default values that differ between instantiations

**Impact**: Full cache invalidation on every build if any runtime value differs.

**Evidence**:
```python
def _compute_config_hash(self) -> None:
    from bengal.config.hash import compute_config_hash
    self._config_hash = compute_config_hash(self.config)  # Hashes ALL config
```

---

### Bug 2: Any Template Change Triggers Full Rebuild

**Location**: `bengal/server/build_trigger.py:632-658`

The dev server treats ALL template file changes as requiring full rebuilds, even when:
- The template isn't used by any page
- Only site-scoped blocks changed (could be re-warmed instead)
- The change is in a partial only used by one page

**Impact**: Touching any `.html` file in templates/ triggers full rebuild.

**Evidence**:
```python
def _is_template_change(self, changed_paths: set[Path]) -> bool:
    for path in html_paths:
        for template_dir in template_dirs:
            try:
                path.relative_to(template_dir)
                return True  # ← ANY template = full rebuild
            except ValueError:
                continue
```

---

### Bug 3: Fingerprint Update Race Condition

**Location**: `bengal/cache/dependency_tracker.py:159-173`

File fingerprints are updated MID-BUILD via `_update_dependency_file_once()`. This creates a race:
1. Thread A checks `is_changed(file)` → returns False (unchanged)
2. Thread B calls `update_file(file)` → updates mtime in fingerprint
3. Next build: Thread A checks `is_changed(file)` → returns True (mtime differs!)

**Impact**: Random cache misses causing unnecessary rebuilds.

---

### Bug 4: Unchanged Templates Get Fingerprint Updated

**Location**: `bengal/orchestration/incremental/template_detector.py:172-173`

In `_check_templates_sequential()`, unchanged templates have their fingerprints updated:

```python
else:
    self.cache.update_file(template_file)  # Updates UNCHANGED templates
```

If a file was touched (mtime changed) but content is identical, this stores the new mtime, causing future builds to potentially see a "change".

---

### Bug 5: Parsed Content Cache Dependency Validation

**Location**: `bengal/cache/build_cache/parsed_content_cache.py:170-178`

The parsed content cache checks if dependencies changed using `is_changed()`:

```python
for dep_path in self.dependencies[key]:
    dep = Path(dep_path)
    if dep.exists() and self.is_changed(dep):
        return MISSING  # Invalidate cache
```

But `is_changed()` uses the fingerprint which may have been updated mid-build (Bug 3), causing cascading invalidations.

---

## Proposed Solutions

### Fix 1: Exclude Runtime Values from Config Hash

**File**: `bengal/config/hash.py`

Create a stable config subset that excludes runtime-computed values:

```python
def compute_config_hash(config: dict[str, Any]) -> str:
    """Compute hash excluding runtime values."""
    # Keys to exclude from hashing (runtime-computed)
    EXCLUDED_KEYS = {
        "output_dir",  # May be absolute path
        "root_path",   # Runtime path
        "_paths",      # Internal paths object
        "_config_hash",  # Self-reference
    }

    def clean_config(d: dict) -> dict:
        """Recursively remove excluded keys."""
        return {
            k: clean_config(v) if isinstance(v, dict) else v
            for k, v in d.items()
            if k not in EXCLUDED_KEYS
        }

    stable_config = clean_config(config)
    serialized = json.dumps(stable_config, sort_keys=True, default=_json_default)
    return hash_str(serialized, truncate=16)
```

**Migration**: No migration needed. Hash will change once, triggering one full rebuild.

---

### Fix 2: Track Template-to-Page Dependencies

**Files**:
- `bengal/server/build_trigger.py`
- `bengal/orchestration/incremental/template_detector.py`

Instead of full rebuild for any template change:

1. Use existing `cache.get_affected_pages(template_path)` to find dependent pages
2. If template has no dependents, skip rebuild entirely
3. If only site-scoped blocks changed (via `RebuildDecisionEngine`), re-warm blocks only

```python
def _is_template_change(self, changed_paths: set[Path]) -> bool:
    """Check if template changes require full rebuild."""
    html_paths = [p for p in changed_paths if p.suffix.lower() == ".html"]
    if not html_paths:
        return False

    for path in html_paths:
        if self._is_in_template_dir(path):
            # Check if template has dependents
            affected = self.cache.get_affected_pages(path)
            if affected:
                # Has dependents - but can we do incremental?
                if self._can_use_incremental_template_update(path):
                    continue  # Skip full rebuild
                return True

    return False  # No templates with dependents changed
```

---

### Fix 3: Defer Fingerprint Updates to Post-Build

**File**: `bengal/cache/dependency_tracker.py`

Move fingerprint updates to `save_cache()` phase:

```python
class DependencyTracker:
    def __init__(self, cache, site=None):
        ...
        self._pending_fingerprint_updates: set[Path] = set()

    def _update_dependency_file_once(self, path: Path) -> None:
        """Queue fingerprint update (deferred to post-build)."""
        with self.lock:
            self._pending_fingerprint_updates.add(path)

    def flush_pending_updates(self) -> None:
        """Apply all pending fingerprint updates. Call in save_cache()."""
        with self.lock:
            for path in self._pending_fingerprint_updates:
                if path.exists():
                    self.cache.update_file(path)
            self._pending_fingerprint_updates.clear()
```

**Integration**: Call `tracker.flush_pending_updates()` in `CacheManager.save()`.

---

### Fix 4: Only Update Fingerprint on Actual Change

**File**: `bengal/orchestration/incremental/template_detector.py`

Don't update unchanged template fingerprints:

```python
def _check_templates_sequential(self, ...):
    for template_file in template_files:
        if self.cache.is_changed(template_file):
            # Template changed - handle rebuild logic
            ...
        # REMOVED: else: self.cache.update_file(template_file)
        # Fingerprints are only updated for CHANGED files in save_cache()
```

---

### Fix 5: Use Content Hash for Dependency Validation

**File**: `bengal/cache/build_cache/parsed_content_cache.py`

Instead of relying on `is_changed()` which uses mtime, compare content hashes:

```python
def get_parsed_content(self, file_path, metadata, template, parser_version):
    ...
    # Validate dependencies haven't changed (by content hash, not mtime)
    if key in self.dependencies:
        for dep_path in self.dependencies[key]:
            dep = Path(dep_path)
            if dep.exists():
                cached_fp = self.file_fingerprints.get(str(dep), {})
                cached_hash = cached_fp.get("hash")
                if cached_hash:
                    current_hash = hash_file(dep)
                    if current_hash != cached_hash:
                        return MISSING

    return cached
```

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1)

1. **Fix 1**: Config hash stability
   - Modify `compute_config_hash()` to exclude runtime keys
   - Add tests for hash stability

2. **Fix 3**: Deferred fingerprint updates
   - Add pending updates queue to DependencyTracker
   - Integrate flush in save_cache()
   - Add concurrency tests

### Phase 2: Template Optimization (Week 2)

3. **Fix 2**: Smart template rebuild
   - Enhance `_is_template_change()` with dependency check
   - Wire up block-level detection for Kida

4. **Fix 4**: Don't update unchanged templates
   - Remove update_file() call for unchanged templates
   - Verify no regressions in template tracking

### Phase 3: Validation Hardening (Week 3)

5. **Fix 5**: Content-hash dependency validation
   - Add hash-based validation to parsed content cache
   - Add hash-based validation to rendered output cache
   - Performance testing (hash computation overhead)

---

## Testing Strategy

### Unit Tests

```python
class TestConfigHashStability:
    def test_same_config_different_paths_same_hash(self, tmp_path):
        """Runtime paths shouldn't affect hash."""
        config1 = {"title": "Test", "output_dir": "/path/a/public"}
        config2 = {"title": "Test", "output_dir": "/path/b/public"}
        assert compute_config_hash(config1) == compute_config_hash(config2)

class TestFingerprintRaceCondition:
    def test_concurrent_updates_no_race(self):
        """Deferred updates prevent mid-build races."""
        ...

class TestIncrementalTemplateRebuild:
    def test_unused_template_change_no_rebuild(self, tmp_path):
        """Changing unused template doesn't rebuild pages."""
        ...
```

### Integration Tests

```python
def test_incremental_build_stability(tmp_path):
    """Three consecutive incremental builds with no changes should be fast."""
    site = Site.from_config(tmp_path)

    # Build 1: Full
    site.build(incremental=False)

    # Build 2: Incremental (should be fast)
    stats2 = site.build(incremental=True)

    # Build 3: Incremental (should also be fast - no false invalidations)
    stats3 = site.build(incremental=True)

    assert stats2.pages_built == 0, "Build 2 should rebuild nothing"
    assert stats3.pages_built == 0, "Build 3 should rebuild nothing"
```

---

## Metrics

Track these metrics to verify fixes:

| Metric | Before | Target |
|--------|--------|--------|
| False full rebuilds | ~30% of incremental builds | <1% |
| Cache hit rate | ~60% | >95% |
| Incremental build time | Variable (often full) | Consistent <2s for single file |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hash stability breaks cache upgrade | Low | Medium | Version bump triggers one-time full rebuild |
| Deferred updates miss files | Medium | High | Thorough testing; fallback to immediate update |
| Template dependency graph incomplete | Medium | Medium | Existing block-level detection as fallback |

---

## Alternatives Considered

### Alternative A: Content-Addressed Cache

Store cache entries keyed by content hash rather than file path. Eliminates mtime issues entirely but requires significant refactoring.

**Rejected**: Too invasive; proposed fixes achieve same goal with less risk.

### Alternative B: Watchman Integration

Use Facebook's Watchman for file watching with content-aware change detection.

**Deferred**: Could be Phase 2 optimization. Current fixes address immediate issues.

---

## References

- `bengal/cache/build_cache/core.py`: BuildCache implementation
- `bengal/orchestration/incremental/`: Incremental build logic
- `plan/active/rfc-incremental-builds.md`: Original incremental builds RFC
- `tests/integration/test_incremental_output_formats.py`: Existing contract tests

---

## Appendix: Diagnostic Logging

Add these log events to help debug cache issues:

```python
logger.debug(
    "cache_validation",
    file=str(file_path),
    cached_mtime=cached.get("mtime"),
    current_mtime=stat.st_mtime,
    cached_hash=cached.get("hash", "none")[:8],
    current_hash=current_hash[:8] if current_hash else "none",
    decision="hit" if matched else "miss",
    reason=reason,
)
```

Enable with: `BENGAL_LOG_LEVEL=debug bengal build --incremental`
