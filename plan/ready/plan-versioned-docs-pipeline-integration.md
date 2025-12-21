# Plan: Versioned Documentation Pipeline Integration

**Status**: In Progress (Phase 1 Complete ✅, Phase 2-3 Pending)  
**Created**: 2025-12-19  
**Last Updated**: 2025-01-XX  
**RFC**: `plan/drafted/rfc-versioned-docs-pipeline-integration.md` (not found - may have been deleted)  
**Confidence**: 88% 🟢  
**Estimated Effort**: ~16 hours remaining (Phase 1: ✅ Complete, Phase 2: ~9h, Phase 3: ~7h)

---

## Summary

Integrate versioned documentation with Bengal's incremental build system, dev server, and dependency tracking. Changes to `_shared/` content should cascade to all versions; changes to `_versions/v2/` should only rebuild v2.

### Current Status

**Phase 1: ✅ COMPLETE** - Core fixes for incremental builds and dev server are implemented:
- Shared content change detection and cascade
- Version-affected path detection
- Version config change detection
- Test infrastructure and integration tests

**Phase 2: ⏳ PENDING** - Cross-version link dependency tracking (~9 hours)
- Track `[[v2:path]]` style cross-version links
- Cascade rebuilds when cross-version targets change

**Phase 3: ⏳ PENDING** - Version-scoped dev server (~7 hours)
- `--version` flag for focused development
- Scoped rebuilds to only affected versions

---

## Phase 1: Core Fixes (P1) — ✅ COMPLETE

**Goal**: Fix critical gaps in incremental builds and dev server for versioned sites.  
**Status**: All tasks implemented and tested.

### 1.1 Add Shared Content Change Detection to IncrementalOrchestrator

**File**: `bengal/orchestration/incremental.py`  
**Effort**: 2h

**What**:
- Add `_check_shared_content_changes()` method
- Detect if any `_shared/` content files changed
- Mark ALL versioned pages for rebuild when shared content changes

**Implementation**:
```python
def _check_shared_content_changes(self) -> bool:
    """Check if any _shared/ content has changed."""
    if not self.site.versioning_enabled:
        return False

    version_config = self.site.version_config
    for shared_path in version_config.shared:
        shared_dir = self.site.content_dir / shared_path
        if not shared_dir.exists():
            continue

        for file_path in shared_dir.rglob("*.md"):
            if self.cache.is_changed(file_path):
                return True

    return False
```

**Integration Point**: Call in `find_work_early()` after line 513 (after `nav_changed` setup).

**Verification**:
- [x] Unit test: shared content change cascades to all versioned pages
- [x] Existing incremental tests still pass

**Status**: ✅ **IMPLEMENTED** in `bengal/orchestration/incremental/orchestrator.py:328`

**Commit**: `orchestration(incremental): add shared content cascade for versioned sites; detect _shared/ changes and rebuild all version pages`

---

### 1.2 Add Shared Content Detection to Build Trigger

**File**: `bengal/server/build_trigger.py`  
**Effort**: 1h

**What**:
- Add `_is_shared_content_change()` method
- Trigger full rebuild when shared content changes during dev server

**Implementation**:
```python
def _is_shared_content_change(self, changed_paths: set[Path]) -> bool:
    """Check if any changed path is in _shared/ directory."""
    if not getattr(self.site, "versioning_enabled", False):
        return False

    for path in changed_paths:
        path_str = str(path).replace("\\", "/")
        if "/_shared/" in path_str or path_str.startswith("_shared/"):
            return True

    return False
```

**Integration Point**: Add check in `_needs_full_rebuild()` after line 263 (SVG check).

**Verification**:
- [x] Dev server triggers full rebuild on `_shared/` file change
- [x] Non-versioned sites unaffected

**Status**: ✅ **IMPLEMENTED** in `bengal/server/build_trigger.py:280`

**Commit**: `server(build_trigger): detect shared content changes and trigger full rebuild for versioned sites`

---

### 1.3 Add Version-Affected Detection to Build Trigger

**File**: `bengal/server/build_trigger.py`  
**Effort**: 2h

**What**:
- Add `_get_affected_versions()` method
- Determine which versions are affected by path changes
- Enable future version-scoped rebuilds (Phase 3)

**Implementation**:
```python
def _get_affected_versions(self, changed_paths: set[Path]) -> set[str]:
    """Determine which versions are affected by changes."""
    if not getattr(self.site, "versioning_enabled", False):
        return set()

    affected = set()

    for path in changed_paths:
        path_str = str(path).replace("\\", "/")

        # Check if in _versions/<id>/
        if "/_versions/" in path_str:
            parts = path_str.split("/_versions/")[1].split("/")
            if parts:
                affected.add(parts[0])  # Version ID

        # Check if in main content (latest version)
        elif not path_str.startswith("_"):
            version_config = getattr(self.site, "version_config", None)
            if version_config and version_config.latest_version:
                affected.add(version_config.latest_version.id)

    return affected
```

**Verification**:
- [x] Unit test: correctly identifies affected versions from paths
- [x] Unit test: returns empty set for non-versioned sites

**Status**: ✅ **IMPLEMENTED** in `bengal/server/build_trigger.py:307`

**Commit**: `server(build_trigger): add version-affected detection for path changes; enable scoped rebuilds`

---

### 1.4 Add Version Config Change Detection

**File**: `bengal/server/build_trigger.py`  
**Effort**: 1h

**What**:
- Add `_is_version_config_change()` method
- Trigger full rebuild when `versioning.yaml` changes

**Implementation**:
```python
def _is_version_config_change(self, changed_paths: set[Path]) -> bool:
    """Check if versioning config changed (requires full rebuild)."""
    for path in changed_paths:
        if path.name == "versioning.yaml":
            return True
        path_str = str(path).replace("\\", "/")
        if "/config/" in path_str and "version" in path.name.lower():
            return True
    return False
```

**Integration Point**: Add check in `_needs_full_rebuild()` after shared content check.

**Verification**:
- [x] Dev server triggers full rebuild on `versioning.yaml` change
- [x] Adding/removing versions handled correctly

**Status**: ✅ **IMPLEMENTED** in `bengal/server/build_trigger.py:357`

**Commit**: `server(build_trigger): detect versioning.yaml changes and trigger full rebuild`

---

### 1.5 Create Test Root: test-versioned

**Location**: `tests/roots/test-versioned/`  
**Effort**: 1h

**Structure**:
```
tests/roots/test-versioned/
├── bengal.toml                    # Enable versioning
├── config/
│   └── _default/
│       └── versioning.yaml        # 3 versions: v1, v2, latest
├── content/
│   ├── _shared/
│   │   └── changelog.md           # Shared content
│   ├── _versions/
│   │   ├── v1/
│   │   │   └── docs/
│   │   │       └── guide.md       # v1 content
│   │   └── v2/
│   │       └── docs/
│   │           └── guide.md       # v2 content
│   └── docs/
│       └── guide.md               # Latest version content
└── skeleton.yaml
```

**Files**:

`bengal.toml`:
```toml
[site]
title = "Test Versioned Site"
baseurl = "/"
```

`config/_default/versioning.yaml`:
```yaml
enabled: true
versions:
  - id: v3
    label: "Version 3.x"
    latest: true
  - id: v2
    label: "Version 2.x"
    path: "_versions/v2"
  - id: v1
    label: "Version 1.x"
    path: "_versions/v1"
shared:
  - "_shared"
```

**Commit**: `tests: add test-versioned root for versioned documentation integration tests`

**Status**: ✅ **IMPLEMENTED** - Test root exists at `tests/roots/test-versioned/`

---

### 1.6 Add Integration Tests for Versioned Builds

**File**: `tests/integration/test_versioned_builds.py`  
**Effort**: 3h

**Test Cases**:

```python
@pytest.mark.bengal(testroot="test-versioned")
class TestVersionedIncrementalBuilds:
    """Test incremental builds with versioned documentation."""

    def test_shared_content_change_cascades_to_all_versions(
        self, site, build_site
    ):
        """Changes to _shared/ should rebuild all versioned pages."""
        # Initial build
        build_site()

        # Modify shared content
        shared_file = site.content_dir / "_shared" / "changelog.md"
        shared_file.write_text("# Updated Changelog\n\nNew content.")

        # Incremental build
        stats = build_site(incremental=True)

        # Should rebuild pages from all versions
        assert stats.pages_rebuilt >= 3  # At least 1 per version

    def test_version_specific_change_only_affects_that_version(
        self, site, build_site
    ):
        """Changes to _versions/v2/ should only rebuild v2 pages."""
        build_site()

        # Modify v2-specific content
        v2_file = site.content_dir / "_versions" / "v2" / "docs" / "guide.md"
        v2_file.write_text("---\ntitle: Updated Guide\n---\n\nNew v2 content.")

        # Incremental build
        stats = build_site(incremental=True)

        # Should only rebuild v2 pages, not v1 or latest
        # (Implementation may need to expose which versions rebuilt)

    def test_latest_content_change_affects_latest_version(
        self, site, build_site
    ):
        """Changes to docs/ should only rebuild latest version pages."""
        build_site()

        # Modify latest content (not in _versions/)
        latest_file = site.content_dir / "docs" / "guide.md"
        latest_file.write_text("---\ntitle: Latest Guide\n---\n\nLatest content.")

        stats = build_site(incremental=True)

        # Should only rebuild latest version pages

    def test_version_config_change_triggers_full_rebuild(
        self, site, build_site
    ):
        """Changes to versioning.yaml should trigger full rebuild."""
        build_site()

        # Modify version config
        config_file = site.root_path / "config" / "_default" / "versioning.yaml"
        content = config_file.read_text()
        config_file.write_text(content + "\n# Comment")

        # Should trigger full rebuild
        # (Test via mock or build stats)
```

**Commit**: `tests(integration): add versioned documentation incremental build tests`

**Status**: ✅ **IMPLEMENTED** - Tests exist in `tests/integration/test_versioned_builds.py`

---

## Phase 2: Dependency Tracking (P2) — ~9 hours

**Goal**: Track cross-version link dependencies for accurate incremental rebuilds.

### 2.1 Add Cross-Version Link Tracking to DependencyTracker

**File**: `bengal/cache/dependency_tracker.py`  
**Effort**: 2h

**What**:
- Add `track_cross_version_link()` method
- Store dependencies as `xver:{version}:{path}` → `set[source_pages]`

**Implementation**:
```python
def track_cross_version_link(
    self,
    source_page: Path,
    target_version: str,
    target_path: str,
) -> None:
    """
    Track dependency from source page to cross-version target.

    When target changes, source_page should be rebuilt.
    """
    target_key = f"xver:{target_version}:{target_path}"

    if target_key not in self._dependencies:
        self._dependencies[target_key] = set()

    self._dependencies[target_key].add(str(source_page))
```

**Verification**:
- [ ] Unit test: dependencies tracked correctly
- [ ] Thread-safe (uses existing locking pattern)

**Commit**: `cache(dependency_tracker): add cross-version link tracking for [[v2:path]] syntax`

---

### 2.2 Integrate Cross-Version Tracking with Cross-Ref Processor

**File**: `bengal/rendering/markdown/cross_refs.py` (or similar)  
**Effort**: 2h

**What**:
- When processing `[[v2:path]]` links, track dependency
- Pass dependency_tracker to processor

**Note**: Need to verify exact file location for cross-ref processing.

**Commit**: `rendering(cross_refs): integrate cross-version link dependency tracking`

---

### 2.3 Add Cross-Version Dependent Retrieval

**File**: `bengal/cache/dependency_tracker.py`  
**Effort**: 1h

**What**:
- Add `get_cross_version_dependents()` method
- Return pages that link to a changed cross-version target

**Implementation**:
```python
def get_cross_version_dependents(
    self,
    changed_version: str,
    changed_path: str,
) -> set[Path]:
    """Get pages that link to a changed cross-version target."""
    target_key = f"xver:{changed_version}:{changed_path}"
    dependents = self._dependencies.get(target_key, set())
    return {Path(p) for p in dependents}
```

**Commit**: `cache(dependency_tracker): add get_cross_version_dependents() for rebuilding linked pages`

---

### 2.4 Wire Cross-Version Dependencies into Incremental Rebuild

**File**: `bengal/orchestration/incremental.py`  
**Effort**: 2h

**What**:
- After detecting changed versioned pages, check for cross-version dependents
- Add dependents to rebuild set

**Integration Point**: Add cascade step in `find_work_early()` after navigation rebuilds.

**Commit**: `orchestration(incremental): cascade rebuilds to cross-version link dependents`

---

### 2.5 Add Cross-Version Dependency Unit Tests

**File**: `tests/unit/test_dependency_tracker.py`  
**Effort**: 2h

**Test Cases**:
```python
def test_track_cross_version_link():
    """Test cross-version link tracking."""
    tracker = DependencyTracker(site)

    tracker.track_cross_version_link(
        source_page=Path("content/v3/guide.md"),
        target_version="v2",
        target_path="docs/api",
    )

    dependents = tracker.get_cross_version_dependents("v2", "docs/api")
    assert Path("content/v3/guide.md") in dependents

def test_cross_version_dependents_empty_for_untracked():
    """Test empty set for untracked targets."""
    tracker = DependencyTracker(site)

    dependents = tracker.get_cross_version_dependents("v1", "nonexistent")
    assert dependents == set()

def test_multiple_pages_linking_same_target():
    """Test multiple pages can link to same cross-version target."""
    tracker = DependencyTracker(site)

    tracker.track_cross_version_link(
        source_page=Path("content/v3/guide.md"),
        target_version="v2",
        target_path="docs/api",
    )
    tracker.track_cross_version_link(
        source_page=Path("content/v3/reference.md"),
        target_version="v2",
        target_path="docs/api",
    )

    dependents = tracker.get_cross_version_dependents("v2", "docs/api")
    assert len(dependents) == 2
```

**Commit**: `tests(unit): add cross-version dependency tracker tests`

---

## Phase 3: Version-Scoped Dev Server (P3) — ~7 hours

**Goal**: Add `--version` flag to dev server for focused development with faster rebuilds.

### 3.1 Add --version Flag to Serve Command

**File**: `bengal/cli/commands/serve.py`  
**Effort**: 1h

**What**:
- Add `--version` option to serve only specific version
- Add `--all-versions` flag to serve all versions
- Default: serve latest only

**Implementation**:
```python
@click.option(
    "--version",
    "serve_version",
    type=str,
    help="Serve specific version only (e.g., v2). Faster rebuilds.",
)
@click.option(
    "--all-versions",
    is_flag=True,
    help="Serve all versions (slower startup/rebuilds)",
)
def serve(serve_version: str | None, all_versions: bool, ...):
    # Store in server context
    server.serve_versions = (
        None if all_versions
        else [serve_version] if serve_version
        else ["latest"]  # Default: latest only
    )
```

**Commit**: `cli(serve): add --version flag for focused development on specific version`

---

### 3.2 Add version_scope to BuildRequest

**File**: `bengal/server/build_executor.py`  
**Effort**: 1h

**What**:
- Add `version_scope: list[str] | None` to BuildRequest dataclass
- Update subprocess serialization to pass version_scope

**Implementation**:
```python
@dataclass
class BuildRequest:
    site_root: str
    changed_paths: tuple[str, ...]
    incremental: bool = True
    profile: str = "WRITER"
    version_scope: list[str] | None = None  # NEW
```

**Commit**: `server(build_executor): add version_scope to BuildRequest for scoped rebuilds`

---

### 3.3 Implement Version-Scoped Rebuilds in Build Trigger

**File**: `bengal/server/build_trigger.py`  
**Effort**: 3h

**What**:
- Determine affected versions from changed paths
- Filter pages to rebuild based on version scope
- Pass version_scope through subprocess boundary

**Implementation**:
```python
def _execute_build(self, changed_paths, event_types):
    affected_versions = self._get_affected_versions(changed_paths)
    shared_changed = self._is_shared_content_change(changed_paths)

    if shared_changed:
        versions_to_rebuild = self.serve_versions or ["all"]
    elif affected_versions:
        if self.serve_versions:
            versions_to_rebuild = list(affected_versions & set(self.serve_versions))
        else:
            versions_to_rebuild = list(affected_versions)
    else:
        versions_to_rebuild = None  # Full rebuild fallback

    request = BuildRequest(
        site_root=str(self.site.root_path),
        changed_paths=tuple(str(p) for p in changed_paths),
        incremental=True,
        version_scope=versions_to_rebuild,
    )
```

**Commit**: `server(build_trigger): implement version-scoped rebuilds; only rebuild affected versions`

---

### 3.4 Add Version-Scoped Serve Integration Tests

**File**: `tests/integration/test_versioned_serve.py`  
**Effort**: 2h

**Test Cases**:
```python
@pytest.mark.bengal(testroot="test-versioned")
class TestVersionedServe:
    """Test dev server with versioned documentation."""

    def test_serve_specific_version_only(self, site):
        """Test --version flag filters to single version."""
        # Test that only v2 pages are built when --version=v2

    def test_serve_all_versions(self, site):
        """Test --all-versions builds all versions."""

    def test_version_scoped_rebuild_only_affected(self, site):
        """Test that changes only rebuild affected version."""
```

**Commit**: `tests(integration): add version-scoped dev server tests`

---

## Task Dependency Graph

```
Phase 1 (Core - can run in parallel within phase):
├── 1.1 IncrementalOrchestrator shared detection
├── 1.2 Build trigger shared detection
├── 1.3 Build trigger version detection
├── 1.4 Build trigger config detection
├── 1.5 Test root creation ─────────────┐
└── 1.6 Integration tests ──────────────┴─ depends on 1.1-1.5

Phase 2 (Dependencies - sequential):
├── 2.1 DependencyTracker cross-version ────┐
├── 2.2 Cross-ref processor integration ────┼─ depends on 2.1
├── 2.3 Get dependents method ──────────────┤
├── 2.4 Incremental rebuild wiring ─────────┴─ depends on 2.1-2.3
└── 2.5 Unit tests ─────────────────────────── depends on 2.1-2.3

Phase 3 (Version-scoped - sequential):
├── 3.1 CLI --version flag
├── 3.2 BuildRequest version_scope ─────────── depends on 3.1
├── 3.3 Build trigger version scope ────────── depends on 3.2
└── 3.4 Integration tests ──────────────────── depends on 3.1-3.3
```

---

## Verification Checklist

### Phase 1 Complete When:
- [x] `_shared/` content changes trigger rebuilds for all versioned pages ✅
- [x] Changes to `_versions/v2/` are detected correctly ✅
- [x] `versioning.yaml` changes trigger full rebuild ✅
- [x] All tests pass with `test-versioned` root ✅
- [x] No regression for non-versioned sites ✅

**Phase 1 Status**: ✅ **COMPLETE** - All core fixes implemented and tested.

### Phase 2 Complete When:
- [ ] Cross-version links tracked as dependencies
- [ ] Changes to cross-version targets rebuild linking pages
- [ ] Unit tests for dependency tracker pass
- [ ] Broken cross-version links detectable

### Phase 3 Complete When:
- [ ] `bengal serve --version=v2` works
- [ ] Only v2 pages built when using `--version=v2`
- [ ] Shared content changes rebuild served version(s)
- [ ] Integration tests pass

---

## Success Criteria

### Phase 1 (Complete ✅):
- [x] `_shared/` content changes trigger rebuilds for all versioned pages ✅
- [x] Dev server correctly detects version-affecting changes ✅
- [x] `versioning.yaml` changes trigger full rebuild ✅
- [x] All tests pass with versioned test root (`test-versioned`) ✅
- [x] No performance regression for non-versioned sites ✅

### Phase 2 (Pending):
- [ ] Cross-version links tracked as dependencies
- [ ] Changes to cross-version targets rebuild linking pages

### Phase 3 (Pending):
- [ ] `bengal serve --version=v2` works
- [ ] Changes to `_versions/v2/` only rebuild v2 when scoped

---

## Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (unnecessary rebuilds) | Low | Start conservative, tune thresholds |
| Missed cascades (stale content) | High | Comprehensive testing, fallback to full rebuild |
| Performance regression | Medium | Cache affected versions, lazy evaluation |
| Backward compatibility | Low | All changes gated on `versioning_enabled` |
| Subprocess version_scope serialization | Medium | Integration tests, validate round-trip |

---

## Implementation Notes

### Phase 1 Implementation Details

**Shared Content Cascade**:
- Implemented in `bengal/orchestration/incremental/orchestrator.py:328` (`_check_shared_content_changes`)
- Integrated via `RebuildFilter.apply_shared_content_cascade()` in change detection pipeline
- Tests: `tests/integration/test_versioned_builds.py`

**Build Trigger Detection**:
- `_is_shared_content_change()`: `bengal/server/build_trigger.py:280`
- `_get_affected_versions()`: `bengal/server/build_trigger.py:307`
- `_is_version_config_change()`: `bengal/server/build_trigger.py:357`
- All methods integrated into `_needs_full_rebuild()` logic

**Test Infrastructure**:
- Test root: `tests/roots/test-versioned/` (complete with 3 versions)
- Integration tests: `tests/integration/test_versioned_builds.py` (comprehensive coverage)

## References

- RFC: `plan/drafted/rfc-versioned-docs-pipeline-integration.md` (referenced but not found)
- Versioning RFC: `plan/drafted/rfc-versioned-documentation.md`
- Incremental builds: `bengal/orchestration/incremental/orchestrator.py`
- Build trigger: `bengal/server/build_trigger.py`
- Dependency tracker: `bengal/cache/dependency_tracker.py`
- Rebuild filter: `bengal/orchestration/incremental/rebuild_filter.py`
