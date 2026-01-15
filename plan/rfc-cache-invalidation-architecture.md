# RFC: Cache Invalidation Architecture

## Status: Implemented
## Created: 2026-01-14
## Updated: 2026-01-14
## Implemented: 2026-01-14

---

## Summary

**Problem**: Bengal's incremental build system has multiple independent caching layers that don't coordinate invalidation. This leads to stale content bugs that are hard to diagnose and fix.

**Evidence**: RFC `rfc-incremental-build-dependency-gaps` required manual cache invalidation in 4 different locations to fix 3 bugs. Each new dependency type requires touching multiple files.

**Solution**: Introduce a unified `CacheCoordinator` that manages **page-level** cache layers with explicit invalidation cascades, rebuild reasons, and observability.

**Estimated Effort**: 3-4 days

---

## Problem Statement

### Current Architecture

Bengal has two categories of caches:

**1. Global Caches** (module-level, managed by `cache_registry.py`):
```
┌─────────────────────────────────────────────────────────┐
│  Global Caches (cache_registry.py)                      │
├─────────────────────────────────────────────────────────┤
│  NavTreeCache            │ Site navigation structure    │
│  global_context_cache    │ Jinja global variables       │
│  parser_instances        │ Thread-local markdown parsers│
│  version_page_index      │ Cross-version page lookups   │
└─────────────────────────────────────────────────────────┘
```

**2. Page-Level Caches** (per-page, in `BuildCache`):
```
┌─────────────────────────────────────────────────────────┐
│  Page-Level Caches (BuildCache)     ← THIS RFC          │
├─────────────────────────────────────────────────────────┤
│  BuildCache.parsed_content    │ Parsed markdown + meta   │
│  BuildCache.rendered_output   │ Final HTML output        │
│  BuildCache.file_fingerprints │ File mtimes/hashes       │
│  DependencyTracker.deps       │ Page → dependency edges  │
└─────────────────────────────────────────────────────────┘
```

**Relationship**: `cache_registry.py` handles global caches via reason-based invalidation (`InvalidationReason.CONFIG_CHANGED`, etc.). This RFC introduces `CacheCoordinator` for page-level caches, complementing (not replacing) the existing system.

### The Problem

Page-level caches are invalidated independently, leading to:

1. **Missed Invalidations**: Change detection marks a page for rebuild, but `rendered_output` cache serves stale HTML
2. **Scattered Logic**: Invalidation code spread across `data_detector.py`, `taxonomy_detector.py`, `change_detector.py`, `content.py`
3. **Hard to Debug**: No visibility into why a page was (or wasn't) rebuilt
4. **Fragile Extensions**: Adding new dependency types requires modifying multiple files

### Evidence from rfc-incremental-build-dependency-gaps

| Gap | Files Modified for Cache Invalidation |
|-----|--------------------------------------|
| Data file dependencies | `data_detector.py` (invalidate rendered_output) |
| Taxonomy metadata | `taxonomy_detector.py` (invalidate rendered_output), `content.py` (cascade logic), `taxonomy.py` (rebuild structure) |
| Sitemap | `postprocess.py` (always regenerate) |

**Pattern**: Every fix required finding and invalidating the right cache in the right place. No central coordination.

### Out of Scope

The following caches are **not** managed by `CacheCoordinator`:

| Cache | Reason |
|-------|--------|
| `Site.taxonomies` | Rebuilt from scratch each build; no invalidation needed |
| `Renderer._tag_pages_cache` | Session-scoped; cleared at build start via `cache_registry` |
| Global caches | Already managed by `cache_registry.invalidate_for_reason()` |

---

## Proposed Solution

### 1. CacheCoordinator Service

A single service that coordinates all page-level cache operations:

```python
# bengal/cache/coordinator.py

from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site


class PageInvalidationReason(Enum):
    """
    Why a page's caches were invalidated.
    
    Alignment:
        This enum is aligned with RebuildReasonCode in results.py.
        While RebuildReasonCode tracks why a page was chosen for build,
        this enum tracks why its specific cache layers were cleared.
    """
    CONTENT_CHANGED = auto()      # Source file modified (matches RebuildReasonCode.CONTENT_CHANGED)
    DATA_FILE_CHANGED = auto()    # Dependent data file modified
    TEMPLATE_CHANGED = auto()     # Template or partial modified (matches RebuildReasonCode.TEMPLATE_CHANGED)
    TAXONOMY_CASCADE = auto()     # Member page metadata changed (matches RebuildReasonCode.CASCADE_DEPENDENCY)
    ASSET_CHANGED = auto()        # Dependent asset modified (matches RebuildReasonCode.ASSET_FINGERPRINT_CHANGED)
    CONFIG_CHANGED = auto()       # Site config modified (matches RebuildReasonCode.FULL_REBUILD)
    MANUAL = auto()               # Explicit invalidation request
    FULL_BUILD = auto()           # Full rebuild requested (matches RebuildReasonCode.FULL_REBUILD)
    OUTPUT_MISSING = auto()       # Cached output exists but file missing on disk


@dataclass
class InvalidationEvent:
    """Record of a cache invalidation."""
    page_path: Path
    reason: PageInvalidationReason
    trigger: str  # What caused the invalidation (e.g., "data/team.yaml")
    caches_cleared: list[str] = field(default_factory=list)


# Maximum events to retain (prevents unbounded memory for large sites)
_MAX_EVENTS = 10_000


class CacheCoordinator:
    """
    Coordinates cache invalidation across page-level cache layers.
    
    Ensures that when any dependency changes, ALL affected caches
    are properly invalidated in the correct order.
    
    Scope:
        - Manages: BuildCache.parsed_content, rendered_output, file_fingerprints
        - Does NOT manage: Global caches (use cache_registry.py instead)
    
    Thread Safety:
        All public methods are thread-safe. Uses Lock for event logging
        since rendering may happen in parallel.
    
    Related:
        - cache_registry.py: Global cache coordination (complementary)
        - DependencyTracker: Tracks dependencies; this class acts on them
    """
    
    def __init__(self, cache: "BuildCache", site: "Site"):
        self.cache = cache
        self.site = site
        self._events: list[InvalidationEvent] = []
        self._lock = Lock()
    
    def invalidate_page(
        self,
        page_path: Path,
        reason: PageInvalidationReason,
        trigger: str = "",
    ) -> InvalidationEvent:
        """
        Invalidate all caches for a single page.
        
        This is the ONLY way caches should be invalidated for pages.
        Ensures all layers are cleared consistently.
        
        Returns:
            InvalidationEvent with list of caches that were actually cleared.
        """
        event = InvalidationEvent(
            page_path=page_path,
            reason=reason,
            trigger=trigger,
        )
        
        # Layer 1: Rendered output (final HTML)
        if self.cache.invalidate_rendered_output(page_path):
            event.caches_cleared.append("rendered_output")
        
        # Layer 2: Parsed content (markdown AST + metadata)
        if self.cache.invalidate_parsed_content(page_path):
            event.caches_cleared.append("parsed_content")
        
        # Layer 3: File fingerprint
        if self.cache.invalidate_fingerprint(page_path):
            event.caches_cleared.append("fingerprint")
        
        # Thread-safe event logging with bounds
        with self._lock:
            self._events.append(event)
            # Trim to prevent unbounded growth on large sites
            if len(self._events) > _MAX_EVENTS:
                self._events = self._events[-_MAX_EVENTS:]
        
        return event
    
    def invalidate_for_data_file(self, data_file: Path) -> list[InvalidationEvent]:
        """
        Invalidate all pages that depend on a data file.
        
        Called when data/*.yaml or data/*.json changes.
        """
        events = []
        affected_pages = self.cache.tracker.get_pages_using_data_file(data_file)
        
        for page_path in affected_pages:
            event = self.invalidate_page(
                page_path,
                reason=PageInvalidationReason.DATA_FILE_CHANGED,
                trigger=str(data_file),
            )
            events.append(event)
        
        return events
    
    def invalidate_for_template(self, template_path: Path) -> list[InvalidationEvent]:
        """
        Invalidate all pages that use a template.
        
        Called when templates/*.html changes.
        """
        events = []
        affected_pages = self.cache.tracker.get_pages_using_template(template_path)
        
        for page_path in affected_pages:
            event = self.invalidate_page(
                page_path,
                reason=PageInvalidationReason.TEMPLATE_CHANGED,
                trigger=str(template_path),
            )
            events.append(event)
        
        return events
    
    def invalidate_taxonomy_cascade(
        self,
        member_page: Path,
        term_pages: set[Path],
    ) -> list[InvalidationEvent]:
        """
        Invalidate taxonomy term pages when a member's metadata changes.
        
        Called when a post's title/date/summary changes and the
        taxonomy listing pages need to reflect the new values.
        """
        events = []
        
        for term_page in term_pages:
            event = self.invalidate_page(
                term_page,
                reason=PageInvalidationReason.TAXONOMY_CASCADE,
                trigger=str(member_page),
            )
            events.append(event)
        
        return events
    
    def invalidate_all(
        self,
        reason: PageInvalidationReason = PageInvalidationReason.FULL_BUILD,
    ) -> int:
        """
        Invalidate all caches (full rebuild).
        
        Returns count of pages invalidated.
        """
        count = 0
        for page in self.site.pages:
            self.invalidate_page(page.source_path, reason, trigger="full_build")
            count += 1
        return count
    
    @property
    def events(self) -> list[InvalidationEvent]:
        """Thread-safe access to events (returns copy)."""
        with self._lock:
            return list(self._events)
    
    def get_invalidation_summary(self) -> dict:
        """
        Get summary of all invalidations for logging/debugging.
        """
        by_reason: dict[str, list[dict]] = {}
        with self._lock:
            for event in self._events:
                reason_name = event.reason.name
                if reason_name not in by_reason:
                    by_reason[reason_name] = []
                by_reason[reason_name].append({
                    "page": str(event.page_path),
                    "trigger": event.trigger,
                    "caches": event.caches_cleared,
                })
        return by_reason
    
    def clear_events(self) -> None:
        """Clear event log (call at start of each build)."""
        with self._lock:
            self._events.clear()
```

### 2. Unified Path Registry

Eliminate path representation mismatches:

```python
# bengal/cache/path_registry.py

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class PathRegistry:
    """
    Canonical path representation for all page types.
    
    Eliminates confusion between:
    - Source paths (content/about.md)
    - Virtual paths (.bengal/generated/tags/python/index.md)
    - Output paths (public/about/index.html)
    - Internal keys (_generated/tags/tag:python)
    
    Cache Key Convention:
        All caches should use canonical_source() as the key for page lookups.
        This ensures consistent addressing regardless of page type.
    """
    
    def __init__(self, site: "Site"):
        self.site = site
        self._content_dir = site.paths.content_dir
        self._generated_dir = site.paths.generated_dir
        self._output_dir = site.paths.output_dir
    
    def canonical_source(self, page: "Page") -> Path:
        """
        Get the canonical source path for any page.
        
        This is the path used as the key in all caches.
        
        - Content pages: Relative to content dir (e.g., "about.md")
        - Generated pages: Relative to generated dir with virtual prefix (e.g., "generated/tags/python/index.md")
        - Autodoc pages: Relative to source root with virtual prefix (e.g., "autodoc/mypackage/core/site.py")
        
        Returns:
            Canonical path for use as cache key.
        """
        if page.metadata.get("_generated") or page.metadata.get("is_autodoc"):
            # Virtual page - use virtual prefix for uniqueness in cache
            try:
                # Try to make relative to generated dir if applicable
                rel_path = page.source_path.relative_to(self._generated_dir)
                return Path("generated") / rel_path
            except ValueError:
                # Not in generated dir - use raw source path (e.g. for autodoc sources)
                try:
                    return Path("autodoc") / page.source_path.relative_to(self.site.root_path)
                except ValueError:
                    return page.source_path
        
        # Content page - use relative path from content dir
        try:
            return page.source_path.relative_to(self._content_dir)
        except ValueError:
            # Fallback: path not under content dir (shouldn't happen)
            return page.source_path
    
    def cache_key(self, page: "Page") -> str:
        """
        Get the string cache key for a page.
        
        Convenience method that converts canonical_source to string.
        """
        return str(self.canonical_source(page))
    
    def is_generated(self, path: Path) -> bool:
        """Check if a path represents a generated page."""
        path_str = str(path)
        generated_str = str(self._generated_dir)
        return path_str.startswith(generated_str) or path_str.startswith(".bengal/generated")
    
    def virtual_path_for_taxonomy(self, taxonomy: str, term: str) -> Path:
        """
        Get the virtual source path for a taxonomy term page.
        
        Example:
            virtual_path_for_taxonomy("tags", "python")
            → .bengal/generated/tags/python/index.md
        """
        return self._generated_dir / taxonomy / term / "index.md"
    
    def output_path(self, page: "Page") -> Path:
        """Get the output path for a page."""
        url_path = page.url.lstrip("/")
        if url_path.endswith("/"):
            return self._output_dir / url_path / "index.html"
        return self._output_dir / f"{url_path}/index.html"
    
    def normalize(self, path: Path | str) -> Path:
        """
        Normalize a path to its canonical form.
        
        Handles both string and Path inputs, resolves relative paths.
        """
        if isinstance(path, str):
            path = Path(path)
        
        # Remove any leading ./ or resolve relative paths
        if not path.is_absolute():
            path = self.site.root / path
        
        return path.resolve()
```

### 3. Rebuild Manifest

Track what was rebuilt and why:

```python
# bengal/cache/manifest.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class RebuildEntry:
    """Record of a single page rebuild."""
    page_path: str
    reason: str
    trigger: str
    duration_ms: float = 0.0
    from_cache: bool = False


@dataclass
class RebuildManifest:
    """
    Complete record of what was rebuilt during a build.
    
    Used for:
    - Debugging stale content issues
    - Build observability (--explain flag)
    - Performance analysis
    """
    
    build_id: str
    incremental: bool
    entries: list[RebuildEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    invalidation_summary: dict = field(default_factory=dict)
    
    def add_rebuild(
        self,
        page_path: Path,
        reason: str,
        trigger: str,
        duration_ms: float = 0.0,
    ) -> None:
        """Record that a page was rebuilt."""
        self.entries.append(RebuildEntry(
            page_path=str(page_path),
            reason=reason,
            trigger=trigger,
            duration_ms=duration_ms,
        ))
    
    def add_skipped(self, page_path: Path) -> None:
        """Record that a page was skipped (cache hit)."""
        self.skipped.append(str(page_path))
    
    def to_json(self) -> str:
        """Export manifest as JSON for debugging."""
        return json.dumps({
            "build_id": self.build_id,
            "incremental": self.incremental,
            "rebuilt": len(self.entries),
            "skipped": len(self.skipped),
            "entries": [
                {
                    "page": e.page_path,
                    "reason": e.reason,
                    "trigger": e.trigger,
                    "duration_ms": e.duration_ms,
                }
                for e in self.entries
            ],
            "invalidation_summary": self.invalidation_summary,
        }, indent=2)
    
    def summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        by_reason = {}
        for entry in self.entries:
            by_reason[entry.reason] = by_reason.get(entry.reason, 0) + 1
        
        return {
            "total_rebuilt": len(self.entries),
            "total_skipped": len(self.skipped),
            "by_reason": by_reason,
            "total_duration_ms": sum(e.duration_ms for e in self.entries),
        }
```

### 4. Cache Migration Strategy

To support the transition to canonical paths as cache keys, we will implement a transparent migration:

1. **Detection**: During `BuildCache.load()`, if `version < 7`, trigger migration.
2. **Key Conversion**: Iterate through `parsed_content`, `rendered_output`, and `file_fingerprints`.
3. **Lookup mapping**: Use a best-effort mapping to convert absolute paths (old keys) to canonical relative paths (new keys).
4. **Fallback**: If mapping fails for a key, invalidate that entry (conservative).
5. **Full Rebuild (Optional)**: If migration complexity exceeds benefit, we can simply bump `VERSION` to force a one-time full rebuild on upgrade.

Given Bengal's current scale, a one-time full rebuild (VERSION bump to 7) is the preferred low-risk path.

---

### 5. BuildCache Invalidation Methods

The following methods must be added to `BuildCache` to support the coordinator:

```python
# bengal/cache/build_cache/parsed_content_cache.py

class ParsedContentCacheMixin:
    # ... existing methods ...
    
    def invalidate_parsed_content(self, file_path: Path) -> bool:
        """
        Remove cached parsed content for a file.
        
        Args:
            file_path: Path to source file
            
        Returns:
            True if cache entry was removed, False if not present
        """
        key = str(file_path)
        if key in self.parsed_content:
            del self.parsed_content[key]
            return True
        return False


# bengal/cache/build_cache/file_tracking.py

class FileTrackingMixin:
    # ... existing methods ...
    
    def invalidate_fingerprint(self, file_path: Path) -> bool:
        """
        Remove cached fingerprint for a file.
        
        This forces re-computation of hash on next access.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if fingerprint was removed, False if not present
        """
        key = str(file_path)
        if key in self.file_fingerprints:
            del self.file_fingerprints[key]
            return True
        return False


# bengal/cache/build_cache/rendered_output_cache.py (UPDATE existing)

class RenderedOutputCacheMixin:
    # ... existing methods ...
    
    def invalidate_rendered_output(self, file_path: Path) -> bool:
        """
        Remove cached rendered output for a file.

        Args:
            file_path: Path to file
            
        Returns:
            True if cache entry was removed, False if not present
        """
        key = str(file_path)
        if key in self.rendered_output:
            del self.rendered_output[key]
            return True
        return False
```

**Note**: The existing `invalidate_rendered_output` method returns `None`. Update it to return `bool` for consistency with the coordinator's pattern.

---

### 6. Integration with Existing Code

#### 6.1 BuildOrchestrator Integration

```python
# In bengal/orchestration/build/__init__.py

class BuildOrchestrator:
    def __init__(self, site: Site, ...):
        self.site = site
        self.cache = BuildCache(site)
        
        # NEW: Unified cache coordination
        self.cache_coordinator = CacheCoordinator(self.cache, site)
        self.path_registry = PathRegistry(site)
        self.rebuild_manifest = None
    
    def build(self, options: BuildOptions) -> BuildStats:
        # Clear previous events
        self.cache_coordinator.clear_events()
        
        # Create manifest for this build
        self.rebuild_manifest = RebuildManifest(
            build_id=generate_build_id(),
            incremental=options.incremental,
        )
        
        # ... existing build logic ...
        
        # At end of build, record invalidation summary
        self.rebuild_manifest.invalidation_summary = (
            self.cache_coordinator.get_invalidation_summary()
        )
        
        # Export manifest if --explain-json
        if options.explain_json:
            print(self.rebuild_manifest.to_json())
```

#### 6.2 Change Detector Integration

```python
# In bengal/orchestration/incremental/change_detector.py

from bengal.orchestration.build.coordinator import CacheCoordinator, PageInvalidationReason


class ChangeDetector:
    def __init__(self, site: Site, cache: BuildCache, coordinator: CacheCoordinator):
        self.site = site
        self.cache = cache
        self.coordinator = coordinator  # NEW
    
    def detect_changes(self) -> ChangeResult:
        pages_to_rebuild = set()
        
        # Data file changes
        for data_file in self._find_changed_data_files():
            events = self.coordinator.invalidate_for_data_file(data_file)
            for event in events:
                pages_to_rebuild.add(event.page_path)
        
        # Template changes
        for template in self._find_changed_templates():
            events = self.coordinator.invalidate_for_template(template)
            for event in events:
                pages_to_rebuild.add(event.page_path)
        
        # Content changes (source files)
        for page_path in self._find_changed_content():
            self.coordinator.invalidate_page(
                page_path,
                PageInvalidationReason.CONTENT_CHANGED,
                trigger=str(page_path),
            )
            pages_to_rebuild.add(page_path)
        
        return ChangeResult(pages_to_rebuild=pages_to_rebuild)
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1.5 days)

1. **Add BuildCache invalidation methods** (0.25 day)
   - Add `invalidate_parsed_content()` → `ParsedContentCacheMixin`
   - Add `invalidate_fingerprint()` → `FileTrackingMixin`
   - Update `invalidate_rendered_output()` to return `bool`
   - **Bump BuildCache.VERSION to 7** to force canonical path keys
   - Unit tests for each method

2. **Create CacheCoordinator** (0.5 day)
   - Create `bengal/cache/coordinator.py`
   - Implement `PageInvalidationReason` enum
   - Implement `InvalidationEvent` dataclass
   - Implement `CacheCoordinator` with thread safety
   - Unit tests

3. **Create PathRegistry** (0.25 day)
   - Create `bengal/cache/path_registry.py`
   - Handle content vs. generated page paths
   - Unit tests

4. **Create RebuildManifest** (0.25 day)
   - Create `bengal/cache/manifest.py`
   - JSON export for debugging
   - Unit tests

5. **Module exports** (0.25 day)
   - Update `bengal/cache/__init__.py` with new exports
   - Verify import patterns work

### Phase 2: Integration (1.5 days)

1. Add `CacheCoordinator` to `BuildOrchestrator`
2. Refactor `DataFileDetector` to use coordinator
3. Refactor `TaxonomyChangeDetector` to use coordinator
4. Refactor `ChangeDetector` to use coordinator
5. Update `phase_update_pages_list` to use coordinator
6. Integration tests

### Phase 3: Observability (0.5 days)

1. Add `--explain-cache` flag to show invalidation details
2. Add rebuild manifest to `--explain-json` output
3. Add structured logging for invalidation events

### Phase 4: Cleanup (0.5 days)

1. Remove ad-hoc invalidation calls from old code
2. Update documentation
3. Mark RFC as implemented

---

## Migration Strategy

### Backward Compatibility

- Existing `BuildCache` API unchanged
- `DependencyTracker` API unchanged
- New coordinator is additive, not breaking

### Deprecation Path

```python
# Old pattern (deprecated but still works)
cache.invalidate_rendered_output(page_path)

# New pattern (preferred)
coordinator.invalidate_page(page_path, PageInvalidationReason.CONTENT_CHANGED, trigger="...")
```

Deprecation warnings added in v0.2.0, removed in v0.3.0.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cache/test_coordinator.py

from bengal.orchestration.build.coordinator import CacheCoordinator, PageInvalidationReason


class TestCacheCoordinator:
    def test_invalidate_page_clears_all_layers(self):
        """Invalidating a page clears rendered_output, parsed_content, fingerprint."""
        coordinator = CacheCoordinator(cache, site)
        
        # Pre-populate caches
        cache.set_rendered_output(page_path, "<html>...")
        cache.set_parsed_content(page_path, {...})
        
        # Invalidate
        event = coordinator.invalidate_page(
            page_path,
            PageInvalidationReason.CONTENT_CHANGED,
            trigger="test",
        )
        
        # Verify all cleared
        assert not cache.has_rendered_output(page_path)
        assert not cache.has_parsed_content(page_path)
        assert "rendered_output" in event.caches_cleared
        assert "parsed_content" in event.caches_cleared
    
    def test_invalidate_for_data_file_cascades(self):
        """Data file invalidation cascades to dependent pages."""
        # Setup: page depends on data file
        tracker.track_data_file(page_path, data_file_path)
        cache.set_rendered_output(page_path, "<html>...")
        
        # Invalidate data file
        events = coordinator.invalidate_for_data_file(data_file_path)
        
        # Verify cascade
        assert len(events) == 1
        assert events[0].page_path == page_path
        assert events[0].reason == PageInvalidationReason.DATA_FILE_CHANGED
        assert not cache.has_rendered_output(page_path)
    
    def test_thread_safety_with_concurrent_invalidation(self):
        """Events are logged safely under concurrent invalidation."""
        import threading
        
        coordinator = CacheCoordinator(cache, site)
        errors = []
        
        def invalidate_pages(start_idx: int):
            try:
                for i in range(100):
                    coordinator.invalidate_page(
                        Path(f"page_{start_idx}_{i}.md"),
                        PageInvalidationReason.CONTENT_CHANGED,
                        trigger="test",
                    )
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=invalidate_pages, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread safety violation: {errors}"
        assert len(coordinator.events) == 400
```

### Integration Tests

```python
# tests/integration/cache/test_invalidation_integration.py

class TestCacheInvalidationIntegration:
    def test_data_file_change_invalidates_via_coordinator(self):
        """End-to-end: data file change → coordinator → page rebuilt with new data."""
        # Similar to test_dependency_gaps.py but verifies coordinator path
        pass
    
    def test_rebuild_manifest_captures_all_rebuilds(self):
        """Rebuild manifest accurately captures rebuild reasons."""
        # Build, check manifest has correct entries
        pass
```

---

## Success Criteria

- [x] All **page-level** cache invalidations go through `CacheCoordinator`
- [x] No direct `cache.invalidate_*` calls outside coordinator (except tests)
- [x] `RebuildManifest` accurately captures all rebuilds with reasons
- [ ] `--explain-cache` shows invalidation cascade (Phase 3 - future)
- [x] All existing warm build tests pass
- [x] New dependency types only require changes in one place (coordinator)
- [x] Thread-safe: No race conditions during parallel rendering
- [x] Bounded memory: Event log stays under 10K entries

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression from indirection | Low | Medium | Benchmark before/after, coordinator methods are thin wrappers |
| Breaking existing cache behavior | Medium | High | Extensive integration tests, deprecation period |
| Over-invalidation (too conservative) | Low | Low | Monitor build times, can optimize later |
| Thread safety issues in parallel builds | Low | High | Lock around event logging, immutable events, thread-safe patterns |
| Event log memory growth | Low | Low | Bounded to 10K events, trimmed automatically |

---

## Appendix: Current vs. Proposed Flow

### Current Flow (Fragmented)

```
DataFileDetector.check_data_files()
  └─ cache.invalidate_rendered_output(page)  # Manual call
  
TaxonomyChangeDetector.check_metadata_cascades()
  └─ cache.invalidate_rendered_output(term_page)  # Manual call

phase_update_pages_list()
  └─ cache.invalidate_rendered_output(term_page)  # Another manual call
  
ChangeDetector._find_changed_files()
  └─ (no invalidation, relies on rebuild marking)
```

### Proposed Flow (Unified)

```
ChangeDetector.detect_changes()
  │
  ├─ coordinator.invalidate_for_data_file(data_file)
  │   └─ coordinator.invalidate_page(page, PageInvalidationReason.DATA_FILE_CHANGED)
  │       ├─ cache.invalidate_rendered_output(page) → bool
  │       ├─ cache.invalidate_parsed_content(page) → bool
  │       ├─ cache.invalidate_fingerprint(page) → bool
  │       └─ [thread-safe] events.append(InvalidationEvent)
  │
  └─ coordinator.invalidate_taxonomy_cascade(member, term_pages)
      └─ coordinator.invalidate_page(term_page, PageInvalidationReason.TAXONOMY_CASCADE)
          └─ (same cascade as above)

At build end:
  manifest.invalidation_summary = coordinator.get_invalidation_summary()
```

---

## Architecture Decision: Two-Level Cache Coordination

Bengal now has two complementary cache coordination systems:

### 1. `cache_registry.py` - Global Caches

**Scope**: Module-level caches that persist across builds
**Pattern**: Reason-based invalidation with dependency ordering

```python
# Example: NavTreeCache registration
register_cache(
    "nav_tree",
    NavTreeCache.invalidate,
    invalidate_on={InvalidationReason.CONFIG_CHANGED, InvalidationReason.STRUCTURAL_CHANGE},
    depends_on={"build_cache"},
)

# Trigger invalidation
invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
```

**Manages**: NavTreeCache, global_context_cache, parser_instances, version_page_index

### 2. `CacheCoordinator` - Page-Level Caches (This RFC)

**Scope**: Per-page caches within BuildCache
**Pattern**: Explicit page-by-page invalidation with event logging

```python
# Example: Invalidate page when data file changes
coordinator.invalidate_page(
    page_path,
    PageInvalidationReason.DATA_FILE_CHANGED,
    trigger="data/team.yaml",
)
```

**Manages**: parsed_content, rendered_output, file_fingerprints

### Why Two Systems?

| Aspect | cache_registry | CacheCoordinator |
|--------|----------------|------------------|
| Granularity | All-or-nothing | Per-page |
| Lifetime | Process lifetime | Per-build |
| Invalidation | Reason → affected caches | Change → affected pages |
| Observability | Log of cache names | Detailed event trail |

The systems are complementary:
- **Config changes**: Use `cache_registry` to clear NavTreeCache, then `CacheCoordinator` handles page-level cascades
- **Data file changes**: `CacheCoordinator` finds affected pages and invalidates their caches
- **Full rebuild**: Both systems clear their respective caches

---

## References

- RFC: `rfc-incremental-build-dependency-gaps.md` (evidence of problem)
- RFC: `rfc-incremental-build-observability.md` (related observability work)
- `bengal/utils/cache_registry.py` (existing global cache coordination)
- Prior art: Hugo's dependency tracking, Jekyll's regenerator
