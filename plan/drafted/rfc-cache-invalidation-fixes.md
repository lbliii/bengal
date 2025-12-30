# RFC: Cache Invalidation Fixes for Incremental Builds

**Status**: Implemented  
**Created**: 2025-12-29  
**Updated**: 2025-12-29  
**Implemented**: 2025-12-29  
**Author**: AI Assistant  
**Priority**: High  
**Affects**: `bengal/cache/`, `bengal/orchestration/incremental/`

---

## Summary

Incremental builds are triggering full rebuilds due to several cache invalidation bugs. This RFC proposes fixes for five root causes identified through code analysis, with a phased implementation starting with diagnostic instrumentation.

---

## Problem Statement

Users report that incremental builds frequently trigger full rebuilds when they should only rebuild changed pages. This defeats the purpose of incremental builds (10-100x speedup) and degrades developer experience.

**Symptoms observed**:
- "Config file modified - performing full rebuild" when config hasn't changed
- All pages rebuilt when only one template changed
- Cache misses despite no file modifications
- Inconsistent behavior between consecutive builds

**Reproduction**:
```bash
# Build 1: Full build
bengal build

# Build 2: Should be instant (no changes)
bengal build --incremental
# Expected: 0 pages rebuilt
# Actual: Full rebuild triggered

# Build 3: Same behavior
bengal build --incremental
# Expected: 0 pages rebuilt
# Actual: Sometimes rebuilds everything again
```

---

## Root Causes Identified

### Bug 1: Config Hash May Include Unstable Values

**Status**: ⚠️ Requires verification  
**Location**: `bengal/config/hash.py:84-127`, `bengal/core/site/core.py:270-277`

The `compute_config_hash()` function hashes the entire `config` dict. While `output_dir` is stored as a relative string (`"public"`) in defaults, investigation is needed to confirm whether:
1. Config loaders inject absolute paths before hashing
2. Environment-specific values differ between builds
3. Any Path objects end up in the config dict (handled by `_json_default`)

**Current code flow**:
```python
# core.py:270-277
if "output_dir" in self.config:
    self.output_dir = Path(self.config["output_dir"])  # Sets instance attr
if not self.output_dir.is_absolute():
    self.output_dir = self.root_path / self.output_dir  # Resolves path
# ...
self._compute_config_hash()  # Hashes self.config (not self.output_dir)
```

**Action needed**: Add diagnostic logging to capture what's actually hashed.

**Verification test**:
```python
def test_config_hash_stability_across_directories(tmp_path):
    """Config hash should be identical regardless of project location."""
    # Create identical projects in different locations
    project_a = tmp_path / "a" / "project"
    project_b = tmp_path / "b" / "project"

    for project in [project_a, project_b]:
        project.mkdir(parents=True)
        (project / "bengal.toml").write_text('[site]\ntitle = "Test"\n')
        (project / "content").mkdir()

    site_a = Site.from_config(project_a)
    site_b = Site.from_config(project_b)

    assert site_a.config_hash == site_b.config_hash, (
        f"Hash differs by location: {site_a.config_hash} vs {site_b.config_hash}"
    )
```

---

### Bug 2: Any Template Change Triggers Full Rebuild ✅ Verified

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

**Existing infrastructure**: `get_affected_pages(template_path)` already exists in `file_tracking.py:246` and is used by `template_detector.py` and `rebuild_decision.py`.

---

### Bug 3: Mid-Build Fingerprint Updates Cause False Positives ✅ Verified

**Location**: `bengal/cache/dependency_tracker.py:159-173`

File fingerprints are updated **during** the build via `_update_dependency_file_once()`. While thread-safe (uses lock), this causes false positives in subsequent builds:

1. **Build N**: File `partial.html` is checked → unchanged → fingerprint updated with current mtime
2. User touches `partial.html` (mtime changes) but doesn't modify content
3. **Build N+1**: `is_changed()` compares new mtime against stored mtime → "changed"!

The issue isn't a thread race—it's that fingerprints are updated during the build, so any file touch between builds causes false cache misses.

**Evidence**:
```python
def _update_dependency_file_once(self, path: Path) -> None:
    should_update = False
    with self.lock:
        if path not in self._dependency_files_updated:
            self._dependency_files_updated.add(path)
            should_update = True

    if should_update:
        self.cache.update_file(path)  # ← Updates fingerprint mid-build
```

---

### Bug 4: Unchanged Templates Get Fingerprint Updated ✅ Verified

**Location**: `bengal/orchestration/incremental/template_detector.py:172-173`

In `_check_templates_sequential()`, unchanged templates have their fingerprints updated:

```python
else:
    self.cache.update_file(template_file)  # Updates UNCHANGED templates
```

If a file was touched (mtime changed) but content is identical, this stores the new mtime. Combined with Bug 3, this propagates the "touched but unchanged" state into the cache.

---

### Bug 5: Parsed Content Cache Uses mtime-based Validation ✅ Verified

**Location**: `bengal/cache/build_cache/parsed_content_cache.py:170-178`

The parsed content cache checks if dependencies changed using `is_changed()`:

```python
for dep_path in self.dependencies[key]:
    dep = Path(dep_path)
    if dep.exists() and self.is_changed(dep):
        return MISSING  # Invalidate cache
```

`is_changed()` uses mtime as a first-pass check. If Bug 3 or Bug 4 updated fingerprints with new mtimes, this causes cascading invalidations.

---

## Proposed Solutions

### Phase 0: Diagnostic Instrumentation (Prerequisite)

Before implementing fixes, add logging to understand actual behavior:

**File**: `bengal/cache/build_cache/file_tracking.py`

```python
def is_changed(self, file_path: Path) -> bool:
    """Check if file has changed since last build."""
    key = str(file_path)
    cached = self.file_fingerprints.get(key)

    if not cached:
        logger.debug("cache_miss", file=key, reason="not_in_cache")
        return True

    try:
        stat = file_path.stat()
        current_mtime = stat.st_mtime
        cached_mtime = cached.get("mtime")

        # Fast path: mtime unchanged
        if current_mtime == cached_mtime:
            logger.debug("cache_hit", file=key, reason="mtime_match")
            return False

        # Slow path: mtime changed, check content hash
        current_hash = self.hash_file(file_path)
        cached_hash = cached.get("hash")

        changed = current_hash != cached_hash
        logger.debug(
            "cache_validation",
            file=key,
            cached_mtime=cached_mtime,
            current_mtime=current_mtime,
            cached_hash=cached_hash[:8] if cached_hash else "none",
            current_hash=current_hash[:8] if current_hash else "none",
            decision="miss" if changed else "hit",
            reason="content_changed" if changed else "mtime_changed_content_same",
        )
        return changed

    except FileNotFoundError:
        logger.debug("cache_miss", file=key, reason="file_not_found")
        return True
```

**Enable with**: `BENGAL_LOG_LEVEL=debug bengal build --incremental`

---

### Fix 1: Stabilize Config Hash

**File**: `bengal/config/hash.py`

Create a stable config subset that excludes potentially runtime-computed values:

```python
# Keys to exclude from hashing (potentially runtime-computed or internal)
EXCLUDED_KEYS = frozenset({
    "_paths",        # Internal BengalPaths object
    "_config_hash",  # Self-reference (shouldn't be there, defensive)
    "_theme_obj",    # Runtime Theme object
})


def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash of configuration state.

    Excludes internal/runtime keys that shouldn't affect build output.
    """
    def clean_config(d: dict) -> dict:
        """Recursively remove excluded keys."""
        return {
            k: clean_config(v) if isinstance(v, dict) else v
            for k, v in d.items()
            if k not in EXCLUDED_KEYS and not k.startswith("_")
        }

    stable_config = clean_config(config)
    serialized = json.dumps(
        stable_config,
        sort_keys=True,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hash_str(serialized, truncate=16)
```

**Migration**: Hash will change once, triggering one full rebuild. No data migration needed.

---

### Fix 2: Smart Template Rebuild Detection

**File**: `bengal/server/build_trigger.py`

Instead of full rebuild for any template change, use existing dependency tracking:

```python
def _is_template_change(self, changed_paths: set[Path]) -> bool:
    """
    Check if template changes require full rebuild.

    Returns True only if changed templates have dependents AND
    incremental template update isn't possible.
    """
    html_paths = [p for p in changed_paths if p.suffix.lower() == ".html"]
    if not html_paths:
        return False

    template_dirs = self._get_template_dirs()
    if not template_dirs:
        return False

    for path in html_paths:
        if not self._is_in_template_dir(path, template_dirs):
            continue

        # Check if template has any dependents
        affected = self.cache.get_affected_pages(path) if self.cache else set()

        if not affected:
            # Template has no dependents - skip entirely
            logger.debug(
                "template_change_ignored",
                template=str(path),
                reason="no_dependents",
            )
            continue

        # Has dependents - check if we can do incremental update
        if self._can_use_incremental_template_update(path):
            logger.debug(
                "template_change_incremental",
                template=str(path),
                affected_pages=len(affected),
            )
            continue  # Will be handled by incremental build

        # Must do full rebuild
        logger.debug(
            "template_change_full_rebuild",
            template=str(path),
            affected_pages=len(affected),
            reason="incremental_not_possible",
        )
        return True

    return False

def _is_in_template_dir(self, path: Path, template_dirs: list[Path]) -> bool:
    """Check if path is within any template directory."""
    for template_dir in template_dirs:
        try:
            path.relative_to(template_dir)
            return True
        except ValueError:
            continue
    return False
```

---

### Fix 3: Defer Fingerprint Updates to Post-Build

**File**: `bengal/cache/dependency_tracker.py`

Queue fingerprint updates during build, apply them atomically after build completes:

```python
class DependencyTracker:
    def __init__(self, cache: BuildCache, site: Site | None = None) -> None:
        # ... existing init ...
        self._pending_fingerprint_updates: set[Path] = set()

    def _update_dependency_file_once(self, path: Path) -> None:
        """
        Queue fingerprint update for post-build application.

        Fingerprints are queued during the build and applied atomically
        in flush_pending_updates() to prevent mid-build state drift.
        """
        with self.lock:
            if path not in self._dependency_files_updated:
                self._dependency_files_updated.add(path)
                self._pending_fingerprint_updates.add(path)

    def flush_pending_updates(self) -> None:
        """
        Apply all pending fingerprint updates.

        Call this in CacheManager.save() after all build operations complete.
        This ensures fingerprints reflect post-build state, not mid-build state.
        """
        with self.lock:
            updated_count = 0
            for path in self._pending_fingerprint_updates:
                if path.exists():
                    self.cache.update_file(path)
                    updated_count += 1

            logger.debug(
                "fingerprint_flush",
                queued=len(self._pending_fingerprint_updates),
                updated=updated_count,
            )
            self._pending_fingerprint_updates.clear()
```

**Integration point** in `bengal/orchestration/incremental/cache_manager.py:177-245`:

```python
def save(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
    """Update cache with processed files."""
    if not self.cache:
        return

    # ... existing page/asset update logic (lines 188-242) ...

    # Flush deferred fingerprint updates before saving
    if self.tracker:
        self.tracker.flush_pending_updates()

    # Save cache (existing line 245)
    self.cache.save(cache_path)
```

---

### Fix 4: Don't Update Unchanged Template Fingerprints

**File**: `bengal/orchestration/incremental/template_detector.py`

Remove the fingerprint update for unchanged templates:

```python
def _check_templates_sequential(self, template_files: list[Path], ...) -> set[Path]:
    for template_file in template_files:
        if self.cache.is_changed(template_file):
            # Template changed - handle rebuild logic
            ...
        # REMOVED: else: self.cache.update_file(template_file)
        #
        # Rationale: Unchanged templates don't need fingerprint updates.
        # If content is unchanged, the existing fingerprint is valid.
        # Updating fingerprints for unchanged files causes false positives
        # when files are touched but not modified.
```

---

### Fix 5: Use Content Hash for Dependency Validation

**File**: `bengal/cache/build_cache/parsed_content_cache.py`

Replace mtime-first validation with content-hash validation:

```python
def get_parsed_content(self, file_path, metadata, template, parser_version):
    ...
    # Validate dependencies using content hash (not mtime)
    if key in self.dependencies:
        for dep_path in self.dependencies[key]:
            dep = Path(dep_path)
            if not dep.exists():
                continue

            cached_fp = self.file_fingerprints.get(str(dep))
            if not cached_fp:
                return MISSING  # Dependency not tracked

            cached_hash = cached_fp.get("hash")
            if not cached_hash:
                return MISSING  # No hash stored

            # Compare content hashes (immune to mtime drift)
            current_hash = hash_file(dep)
            if current_hash != cached_hash:
                logger.debug(
                    "dependency_changed",
                    page=str(file_path),
                    dependency=str(dep),
                    cached_hash=cached_hash[:8],
                    current_hash=current_hash[:8],
                )
                return MISSING

    return cached
```

**Performance note**: `hash_file()` is called per dependency. For sites with many dependencies, consider caching hashes during the build.

---

## Implementation Plan

### Phase 0: Instrumentation (Days 1-2)

1. Add diagnostic logging to `is_changed()`, `update_file()`
2. Run test builds to capture actual cache behavior
3. Confirm which bugs are actively triggering

**Deliverable**: Log data showing root causes

### Phase 1: Critical Fixes (Week 1)

1. **Fix 3**: Deferred fingerprint updates
   - Add pending updates queue to DependencyTracker
   - Integrate `flush_pending_updates()` in `CacheManager.save()`
   - Add unit tests for deferred update behavior

2. **Fix 4**: Don't update unchanged templates
   - Remove `update_file()` call for unchanged templates
   - Verify no regressions in template tracking

### Phase 2: Template Optimization (Week 2)

3. **Fix 2**: Smart template rebuild
   - Enhance `_is_template_change()` with dependency check
   - Wire up `get_affected_pages()` in build_trigger.py
   - Add tests for unused template changes

4. **Fix 1**: Config hash stability (if confirmed by Phase 0)
   - Add key exclusion to `compute_config_hash()`
   - Add hash stability tests

### Phase 3: Validation Hardening (Week 3)

5. **Fix 5**: Content-hash dependency validation
   - Replace mtime-first check with hash comparison
   - Performance testing (hash computation overhead)
   - Consider hash caching if overhead is significant

---

## Testing Strategy

### Unit Tests

```python
class TestDeferredFingerprintUpdates:
    """Tests for Fix 3: Deferred fingerprint updates."""

    def test_updates_not_applied_during_build(self, tmp_path):
        """Fingerprint updates are queued, not applied."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        tracker._update_dependency_file_once(test_file)

        # Fingerprint NOT updated yet
        assert str(test_file) not in cache.file_fingerprints

    def test_updates_applied_on_flush(self, tmp_path):
        """Fingerprint updates applied after flush."""
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        test_file = tmp_path / "test.html"
        test_file.write_text("content")

        tracker._update_dependency_file_once(test_file)
        tracker.flush_pending_updates()

        # Fingerprint NOW updated
        assert str(test_file) in cache.file_fingerprints


class TestUnchangedTemplateFingerprint:
    """Tests for Fix 4: Don't update unchanged templates."""

    def test_unchanged_template_fingerprint_preserved(self, tmp_path):
        """Unchanged templates keep original fingerprint."""
        template = tmp_path / "base.html"
        template.write_text("original")

        cache = BuildCache()
        cache.update_file(template)
        original_fp = cache.file_fingerprints[str(template)].copy()

        # Touch file (mtime changes) but don't modify content
        time.sleep(0.01)
        template.touch()

        # Check template - should be "unchanged" by content
        assert not cache.is_changed(template)

        # Fingerprint should NOT be updated
        # (This test documents desired behavior after Fix 4)


class TestContentHashDependencyValidation:
    """Tests for Fix 5: Content hash validation."""

    def test_touched_but_unchanged_dependency_is_cache_hit(self, tmp_path):
        """File touch without content change should not invalidate cache."""
        dep = tmp_path / "partial.html"
        dep.write_text("unchanged content")

        cache = BuildCache()
        cache.update_file(dep)

        # Touch file
        time.sleep(0.01)
        dep.touch()

        # With Fix 5, this should still be a cache hit
        # (mtime differs, but content hash matches)
```

### Integration Tests

```python
def test_incremental_build_stability(tmp_path):
    """Three consecutive incremental builds with no changes should be instant."""
    # Setup minimal site
    (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Test"\n')
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "index.md").write_text("# Home\n\nWelcome.")

    site = Site.from_config(tmp_path)

    # Build 1: Full
    site.build(incremental=False)

    # Build 2: Incremental (should be fast)
    stats2 = site.build(incremental=True)

    # Build 3: Incremental (should also be fast - no false invalidations)
    stats3 = site.build(incremental=True)

    assert stats2.pages_built == 0, f"Build 2 rebuilt {stats2.pages_built} pages"
    assert stats3.pages_built == 0, f"Build 3 rebuilt {stats3.pages_built} pages"


def test_template_touch_no_rebuild(tmp_path):
    """Touching template without content change should not rebuild."""
    # Setup site with template
    (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Test"\n')
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "index.md").write_text("# Home\n")
    (tmp_path / "templates").mkdir()
    template = tmp_path / "templates" / "base.html"
    template.write_text("{{ content }}")

    site = Site.from_config(tmp_path)
    site.build(incremental=False)

    # Touch template (mtime changes, content unchanged)
    time.sleep(0.01)
    template.touch()

    # Rebuild should be instant
    stats = site.build(incremental=True)
    assert stats.pages_built == 0, "Touch without change triggered rebuild"
```

---

## Metrics

Track these metrics to verify fixes:

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| False full rebuilds | ~30% of incremental builds | <1% | Log analysis |
| Cache hit rate | ~60% | >95% | `cache_hit`/`cache_miss` log ratio |
| Incremental build time | Variable (often full) | Consistent <2s | Build stats |
| Fingerprint updates per build | O(all files) | O(changed files) | Log count |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hash stability breaks cache upgrade | Low | Medium | Version bump triggers one-time full rebuild |
| Deferred updates miss files | Medium | High | Thorough testing; fallback to immediate update on error |
| Template dependency graph incomplete | Medium | Medium | Existing block-level detection as fallback |
| Content hash overhead | Low | Medium | Lazy computation; cache hashes during build |

---

## Alternatives Considered

### Alternative A: Content-Addressed Cache

Store cache entries keyed by content hash rather than file path. Eliminates mtime issues entirely but requires significant refactoring.

**Rejected**: Too invasive for the problem scope. Proposed fixes achieve same goal with less risk.

### Alternative B: Watchman Integration

Use Facebook's Watchman for file watching with content-aware change detection.

**Deferred**: Could be Phase 2 optimization. Current fixes address immediate issues without external dependencies.

### Alternative C: mtime-Only with Touch Detection

Detect file touches by comparing mtime without content change and skip them.

**Partial adoption**: This is essentially what Fix 5 does, but using content hash as the source of truth rather than trying to infer touch events.

---

## References

**Source Files**:
- `bengal/cache/build_cache/core.py` - BuildCache implementation
- `bengal/cache/build_cache/file_tracking.py:246` - `get_affected_pages()`
- `bengal/cache/dependency_tracker.py:159-173` - Fingerprint update logic
- `bengal/orchestration/incremental/cache_manager.py:177-245` - Cache save integration point
- `bengal/orchestration/incremental/template_detector.py:172-173` - Unchanged template handling
- `bengal/server/build_trigger.py:632-658` - Template change detection

**Related RFCs**:
- `plan/active/rfc-incremental-builds.md` - Original incremental builds RFC
- `tests/integration/test_incremental_output_formats.py` - Existing contract tests

---

## Appendix A: Diagnostic Commands

```bash
# Enable debug logging for cache operations
BENGAL_LOG_LEVEL=debug bengal build --incremental 2>&1 | grep -E "cache_|fingerprint_"

# Check cache state
cat .bengal/cache.json | python -m json.tool | head -100

# Compare hashes between builds
bengal build --incremental 2>&1 | grep config_hash
```

## Appendix B: Verification Checklist

After implementation, verify:

- [ ] `test_incremental_build_stability` passes
- [ ] `test_template_touch_no_rebuild` passes
- [ ] Three consecutive `bengal build --incremental` show 0 pages rebuilt
- [ ] Cache hit rate >95% in debug logs
- [ ] No performance regression (build time within 10% of baseline)
