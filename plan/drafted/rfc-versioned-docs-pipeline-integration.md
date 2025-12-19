# RFC: Versioned Documentation Pipeline Integration

**Status**: Draft  
**Created**: 2025-12-19  
**Updated**: 2025-12-19  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High)  
**Related**: `plan/drafted/rfc-versioned-documentation.md`

---

## Problem Statement

The versioned documentation RFC (`rfc-versioned-documentation.md`) designed versioning at the content/config/rendering layer but didn't fully anticipate how it integrates with:

1. **Incremental build system** - Shared content changes don't cascade
2. **Dev server rebuild pipeline** - Not version-aware
3. **Dependency tracking** - Cross-version links not tracked
4. **Watcher configuration** - Version directories may not be watched

These gaps cause:
- Stale content when `_shared/` files change (requires manual full rebuild)
- Unnecessary full rebuilds during development
- Broken cross-version links not detected until full build
- Confusion about which version is being previewed/rebuilt

---

## Goals

1. **Shared content cascade** - Changes to `_shared/` trigger rebuilds for all versions
2. **Version-scoped rebuilds** - Only rebuild affected version(s) during dev
3. **Cross-version dependency tracking** - Detect broken `[[v2:path]]` links
4. **Version-aware dev server** - Preview specific versions with smart rebuilds
5. **Backward compatible** - Non-versioned sites unaffected

---

## Non-Goals

- Git mode changes (already well-designed)
- Version selector UI changes
- Cross-version link syntax changes
- Per-version menus (deferred)

---

## Current State Analysis

### Evidence: Incremental Build (Gap 1)

```python
# bengal/orchestration/incremental.py:find_work()

# Current behavior: Only checks if individual files changed
for page in pages_to_check:
    if self.cache.is_changed(page.source_path):
        pages_to_rebuild.add(page.source_path)

# Missing: No cascade logic for _shared/ content
```

**Impact**: When editing `_shared/changelog.md`, only that file is marked for rebuild. Pages in v1, v2, v3 that include shared content are NOT rebuilt.

### Evidence: Build Trigger (Gap 2)

```python
# bengal/server/build_trigger.py:_needs_full_rebuild()

def _needs_full_rebuild(self, changed_paths, event_types):
    # Checks: structural changes, templates, autodoc, SVG icons
    # Missing: Version-aware logic

    # No distinction between:
    # - _versions/v2/docs/guide.md (should only rebuild v2)
    # - _shared/changelog.md (should rebuild ALL versions)
    # - docs/guide.md (should rebuild latest)
```

### Evidence: Cross-Version Links (Gap 3)

```python
# bengal/rendering/pipeline/core.py

# Parser enables cross-references:
version_config = getattr(site, "version_config", None)
self.parser.enable_cross_references(site.xref_index, version_config)

# But no dependency tracking for [[v2:path]] links
# If v2/path changes or is deleted, linking page won't rebuild
```

### Evidence: Watcher (Gap 4)

```python
# bengal/server/watcher_runner.py

# Watches: [content, templates, themes, assets]
# If _versions/ is inside content/, it's covered
# But _shared/ handling is not special-cased
```

---

## Design: Option A - Minimal (Recommended)

Add version-awareness to existing systems with minimal new abstractions.

### A1. Shared Content Cascade in IncrementalOrchestrator

```python
# bengal/orchestration/incremental.py

class IncrementalOrchestrator:
    def find_work(self, verbose: bool = False) -> ...:
        # NEW: Detect shared content changes
        shared_content_changed = self._check_shared_content_changes()

        if shared_content_changed:
            # Mark ALL versioned pages for rebuild
            pages_to_rebuild.update(
                p.source_path for p in self.site.pages
                if p.version is not None
            )
            if verbose:
                change_summary["Shared content cascade"].append(
                    f"{len(pages_to_rebuild)} pages affected"
                )

        # ... existing logic ...

    def _check_shared_content_changes(self) -> bool:
        """Check if any _shared/ content has changed."""
        if not self.site.versioning_enabled:
            return False

        version_config = self.site.version_config
        for shared_path in version_config.shared:
            shared_dir = self.site.content_dir / shared_path
            if not shared_dir.exists():
                continue

            # Check all files in shared directory
            for file_path in shared_dir.rglob("*.md"):
                if self.cache.is_changed(file_path):
                    return True

        return False
```

### A2. Version-Aware Build Trigger

```python
# bengal/server/build_trigger.py

def _needs_full_rebuild(self, changed_paths, event_types) -> bool:
    # ... existing checks ...

    # NEW: Check for shared content changes (forces full rebuild)
    if self._is_shared_content_change(changed_paths):
        logger.debug("full_rebuild_triggered_by_shared_content")
        return True

    return False

def _is_shared_content_change(self, changed_paths: set[Path]) -> bool:
    """Check if any changed path is in _shared/ directory."""
    if not getattr(self.site, "versioning_enabled", False):
        return False

    for path in changed_paths:
        path_str = str(path).replace("\\", "/")
        if "/_shared/" in path_str or path_str.startswith("_shared/"):
            return True

    return False

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
            version_config = self.site.version_config
            if version_config.latest_version:
                affected.add(version_config.latest_version.id)

    return affected
```

### A3. Cross-Version Link Dependencies

```python
# bengal/cache/dependency_tracker.py

class DependencyTracker:
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

**Integration with parser**:

```python
# bengal/rendering/markdown/cross_refs.py

class CrossReferenceProcessor:
    def process_cross_version_link(self, match, page: Page) -> str:
        version, path = self._parse_link(match)

        # NEW: Track dependency
        if self.dependency_tracker:
            self.dependency_tracker.track_cross_version_link(
                source_page=page.source_path,
                target_version=version,
                target_path=path,
            )

        # ... existing link resolution ...
```

### A4. Explicit Watcher Paths

```python
# bengal/server/dev_server.py (or wherever watcher is configured)

def _get_watch_paths(self) -> list[Path]:
    """Get paths to watch for changes."""
    paths = [
        self.site.content_dir,
        self.site.root_path / "templates",
        self.site.root_path / "themes",
        self.site.root_path / "assets",
    ]

    # NEW: Explicitly add versioning directories
    if self.site.versioning_enabled:
        version_config = self.site.version_config

        # Add _versions/ directory
        versions_dir = self.site.content_dir / "_versions"
        if versions_dir.exists():
            paths.append(versions_dir)

        # Add _shared/ directories
        for shared_path in version_config.shared:
            shared_dir = self.site.content_dir / shared_path
            if shared_dir.exists():
                paths.append(shared_dir)

    return [p for p in paths if p.exists()]
```

---

## Design: Option B - Version-Scoped Dev Server

More comprehensive: add `--version` flag to dev server for focused development.

### B1. CLI Flag

```python
# bengal/cli/commands/serve.py

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

### B2. Version-Scoped Rebuilds

```python
# bengal/server/build_trigger.py

def _execute_build(self, changed_paths, event_types):
    # Determine affected versions
    affected_versions = self._get_affected_versions(changed_paths)

    # Check if shared content changed
    shared_changed = self._is_shared_content_change(changed_paths)

    # Determine what to rebuild
    if shared_changed:
        # Rebuild all served versions
        versions_to_rebuild = self.serve_versions or ["all"]
    elif affected_versions:
        # Only rebuild affected versions that we're serving
        if self.serve_versions:
            versions_to_rebuild = affected_versions & set(self.serve_versions)
        else:
            versions_to_rebuild = affected_versions
    else:
        versions_to_rebuild = None  # Full rebuild fallback

    # Build with version scope
    request = BuildRequest(
        site_root=str(self.site.root_path),
        changed_paths=tuple(str(p) for p in changed_paths),
        incremental=True,
        version_scope=versions_to_rebuild,  # NEW
    )
```

### B3. BuildRequest Version Scope

```python
# bengal/server/build_executor.py

@dataclass
class BuildRequest:
    site_root: str
    changed_paths: tuple[str, ...]
    incremental: bool = True
    profile: str = "WRITER"
    version_scope: list[str] | None = None  # NEW: Only rebuild these versions
```

---

## Recommendation

**Option A (Minimal)** for Phase 1:
- Lower risk, faster to implement
- Solves the critical gaps (shared content cascade, version-aware trigger)
- Cross-version dependency tracking is a bonus

**Option B** for Phase 2 (if needed):
- More complex, better UX for large versioned sites
- Significant speedup for version-focused development
- Requires more testing

---

## Implementation Plan

### Phase 1: Core Fixes (P1)

| Task | File | Effort |
|------|------|--------|
| 1.1 Add `_check_shared_content_changes()` | `orchestration/incremental.py` | 2h |
| 1.2 Add `_is_shared_content_change()` to build trigger | `server/build_trigger.py` | 1h |
| 1.3 Add `_get_affected_versions()` to build trigger | `server/build_trigger.py` | 2h |
| 1.4 Update watcher paths for versioning | `server/dev_server.py` | 1h |
| 1.5 Add integration tests | `tests/integration/test_versioned_builds.py` | 3h |

**Total Phase 1**: ~9 hours

### Phase 2: Dependencies (P2)

| Task | File | Effort |
|------|------|--------|
| 2.1 Add `track_cross_version_link()` | `cache/dependency_tracker.py` | 2h |
| 2.2 Integrate with cross-ref processor | `rendering/markdown/cross_refs.py` | 2h |
| 2.3 Add `get_cross_version_dependents()` | `cache/dependency_tracker.py` | 1h |
| 2.4 Wire into incremental rebuild | `orchestration/incremental.py` | 2h |
| 2.5 Add unit tests | `tests/unit/test_dependency_tracker.py` | 2h |

**Total Phase 2**: ~9 hours

### Phase 3: Version-Scoped Dev (P3)

| Task | File | Effort |
|------|------|--------|
| 3.1 Add `--version` flag to serve | `cli/commands/serve.py` | 1h |
| 3.2 Add `version_scope` to BuildRequest | `server/build_executor.py` | 1h |
| 3.3 Implement version-scoped rebuilds | `server/build_trigger.py` | 3h |
| 3.4 Add integration tests | `tests/integration/test_versioned_serve.py` | 2h |

**Total Phase 3**: ~7 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_incremental_versioning.py

def test_shared_content_change_cascades_to_all_versions():
    """Changes to _shared/ should rebuild all versioned pages."""

def test_version_specific_change_only_affects_that_version():
    """Changes to _versions/v2/ should only rebuild v2 pages."""

def test_latest_content_change_affects_latest_version():
    """Changes to docs/ should only rebuild latest version pages."""
```

### Integration Tests

```python
# tests/integration/test_versioned_builds.py

@pytest.mark.bengal(testroot="test-versioned")
def test_incremental_build_with_shared_content(site, build_site):
    """Test that shared content changes cascade correctly."""
    # Initial build
    build_site()

    # Modify _shared/changelog.md
    shared_file = site.content_dir / "_shared" / "changelog.md"
    shared_file.write_text("# Updated Changelog")

    # Incremental build
    stats = build_site(incremental=True)

    # Should rebuild all versioned pages
    assert stats.pages_rebuilt >= 3  # At least 1 per version
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (unnecessary rebuilds) | Low | Start conservative, tune thresholds |
| Missed cascades (stale content) | High | Comprehensive testing, fallback to full rebuild |
| Performance regression | Medium | Cache affected versions, lazy evaluation |
| Backward compatibility | Low | All changes gated on `versioning_enabled` |

---

## Success Criteria

- [ ] `_shared/` content changes trigger rebuilds for all versioned pages
- [ ] Changes to `_versions/v2/` only rebuild v2
- [ ] Dev server correctly detects version-affecting changes
- [ ] Cross-version links tracked as dependencies (Phase 2)
- [ ] All tests pass with versioned test root
- [ ] No performance regression for non-versioned sites

---

## Open Questions

1. **Should shared content cascade be configurable?**
   - Some users might want fine-grained control
   - Default: cascade all, opt-out per file via frontmatter?

2. **How to handle version deletion during dev?**
   - If `_versions/v1/` is deleted, what happens?
   - Should trigger full rebuild of navigation/version selector

3. **Cache invalidation for version config changes?**
   - If `versioning.yaml` changes, full rebuild needed
   - Should be detected and handled explicitly

---

## References

- [RFC: Versioned Documentation](plan/drafted/rfc-versioned-documentation.md)
- [Incremental Build System](bengal/orchestration/incremental.py)
- [Build Trigger](bengal/server/build_trigger.py)
- [Dependency Tracker](bengal/cache/dependency_tracker.py)
