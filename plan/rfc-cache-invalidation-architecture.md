# RFC: Cache Invalidation Architecture

## Status: Draft
## Created: 2026-01-14
## Updated: 2026-01-14

---

## Summary

**Problem**: Bengal's incremental build system has multiple independent caching layers that don't coordinate invalidation. This leads to stale content bugs that are hard to diagnose and fix.

**Evidence**: RFC `rfc-incremental-build-dependency-gaps` required manual cache invalidation in 4 different locations to fix 3 bugs. Each new dependency type requires touching multiple files.

**Solution**: Introduce a unified `CacheCoordinator` that manages all cache layers with explicit invalidation cascades, rebuild reasons, and observability.

**Estimated Effort**: 3-4 days

---

## Problem Statement

### Current Architecture

Bengal has multiple independent caching layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Cache Layers                          │
├─────────────────────────────────────────────────────────┤
│  BuildCache.parsed_content    │ Parsed markdown + meta   │
│  BuildCache.rendered_output   │ Final HTML output        │
│  BuildCache.file_fingerprints │ File mtimes/hashes       │
│  DependencyTracker            │ Page → dependency edges  │
│  Site.taxonomies              │ Taxonomy structures      │
│  Renderer._tag_pages_cache    │ Tag page data            │
└─────────────────────────────────────────────────────────┘
```

### The Problem

Each cache is invalidated independently, leading to:

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

---

## Proposed Solution

### 1. CacheCoordinator Service

A single service that coordinates all cache operations:

```python
# bengal/cache/coordinator.py

from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site


class InvalidationReason(Enum):
    """Why a page's caches were invalidated."""
    CONTENT_CHANGED = auto()      # Source file modified
    DATA_FILE_CHANGED = auto()    # Dependent data file modified
    TEMPLATE_CHANGED = auto()     # Template or partial modified
    TAXONOMY_CASCADE = auto()     # Member page metadata changed
    ASSET_CHANGED = auto()        # Dependent asset modified
    CONFIG_CHANGED = auto()       # Site config modified
    MANUAL = auto()               # Explicit invalidation request
    FULL_BUILD = auto()           # Full rebuild requested


@dataclass
class InvalidationEvent:
    """Record of a cache invalidation."""
    page_path: Path
    reason: InvalidationReason
    trigger: str  # What caused the invalidation (e.g., "data/team.yaml")
    caches_cleared: list[str] = field(default_factory=list)


class CacheCoordinator:
    """
    Coordinates cache invalidation across all cache layers.
    
    Ensures that when any dependency changes, ALL affected caches
    are properly invalidated in the correct order.
    """
    
    def __init__(self, cache: "BuildCache", site: "Site"):
        self.cache = cache
        self.site = site
        self.events: list[InvalidationEvent] = []
    
    def invalidate_page(
        self,
        page_path: Path,
        reason: InvalidationReason,
        trigger: str = "",
    ) -> InvalidationEvent:
        """
        Invalidate all caches for a single page.
        
        This is the ONLY way caches should be invalidated for pages.
        Ensures all layers are cleared consistently.
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
        
        self.events.append(event)
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
                reason=InvalidationReason.DATA_FILE_CHANGED,
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
                reason=InvalidationReason.TEMPLATE_CHANGED,
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
                reason=InvalidationReason.TAXONOMY_CASCADE,
                trigger=str(member_page),
            )
            events.append(event)
        
        return events
    
    def invalidate_all(self, reason: InvalidationReason = InvalidationReason.FULL_BUILD) -> int:
        """
        Invalidate all caches (full rebuild).
        
        Returns count of pages invalidated.
        """
        count = 0
        for page in self.site.pages:
            self.invalidate_page(page.source_path, reason, trigger="full_build")
            count += 1
        return count
    
    def get_invalidation_summary(self) -> dict:
        """
        Get summary of all invalidations for logging/debugging.
        """
        by_reason = {}
        for event in self.events:
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
        self.events.clear()
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
    """
    
    def __init__(self, site: "Site"):
        self.site = site
        self._generated_dir = site.paths.generated_dir
        self._output_dir = site.paths.output_dir
    
    def canonical_source(self, page: "Page") -> Path:
        """
        Get the canonical source path for any page.
        
        This is the path used as the key in all caches.
        """
        if page.metadata.get("_generated"):
            # Virtual page - use virtual source path
            return page.source_path
        return page.source_path
    
    def is_generated(self, path: Path) -> bool:
        """Check if a path represents a generated page."""
        return str(path).startswith(str(self._generated_dir))
    
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
        return self._output_dir / page.url.lstrip("/") / "index.html"
    
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

### 4. Integration with Existing Code

#### 4.1 BuildOrchestrator Integration

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

#### 4.2 Change Detector Integration

```python
# In bengal/orchestration/incremental/change_detector.py

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
                InvalidationReason.CONTENT_CHANGED,
                trigger=str(page_path),
            )
            pages_to_rebuild.add(page_path)
        
        return ChangeResult(pages_to_rebuild=pages_to_rebuild)
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1 day)

1. Create `bengal/cache/coordinator.py` with `CacheCoordinator`
2. Create `bengal/cache/path_registry.py` with `PathRegistry`
3. Create `bengal/cache/manifest.py` with `RebuildManifest`
4. Add missing `invalidate_*` methods to `BuildCache`
5. Write unit tests for each new class

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
coordinator.invalidate_page(page_path, InvalidationReason.CONTENT_CHANGED, trigger="...")
```

Deprecation warnings added in v0.2.0, removed in v0.3.0.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cache/test_coordinator.py

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
            InvalidationReason.CONTENT_CHANGED,
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
        assert events[0].reason == InvalidationReason.DATA_FILE_CHANGED
        assert not cache.has_rendered_output(page_path)
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

- [ ] All cache invalidations go through `CacheCoordinator`
- [ ] No direct `cache.invalidate_*` calls outside coordinator
- [ ] `RebuildManifest` accurately captures all rebuilds
- [ ] `--explain-cache` shows invalidation cascade
- [ ] All existing warm build tests pass
- [ ] New dependency types only require changes in one place

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression from indirection | Low | Medium | Benchmark before/after, coordinator methods are thin wrappers |
| Breaking existing cache behavior | Medium | High | Extensive integration tests, deprecation period |
| Over-invalidation (too conservative) | Low | Low | Monitor build times, can optimize later |

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
  └─ coordinator.invalidate_for_data_file(data_file)
      └─ coordinator.invalidate_page(page, DATA_FILE_CHANGED)
          └─ cache.invalidate_rendered_output(page)
          └─ cache.invalidate_parsed_content(page)
          └─ cache.invalidate_fingerprint(page)
          └─ manifest.add_rebuild(page, reason, trigger)
  
  └─ coordinator.invalidate_taxonomy_cascade(member, term_pages)
      └─ coordinator.invalidate_page(term_page, TAXONOMY_CASCADE)
          └─ (same cascade as above)
```

---

## References

- RFC: `rfc-incremental-build-dependency-gaps.md` (evidence of problem)
- RFC: `rfc-incremental-build-observability.md` (related observability work)
- Prior art: Hugo's dependency tracking, Jekyll's regenerator
