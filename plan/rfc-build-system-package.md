# RFC: Build System Package Extraction

**Status**: Draft — Not Implemented  
**Author**: AI Assistant  
**Created**: 2026-01-15  
**Updated**: 2026-02-14  
**Python Version**: 3.14  
**Related**: rfc-incremental-build-contracts.md, rfc-effect-traced-incremental-builds.md, rfc-cache-invalidation-architecture.md

> **Architecture note (2026-02-14)**: The `bengal/build/` package described here was never created. The codebase uses `bengal/orchestration/build/` (BuildOrchestrator, coordinator, phases) and `bengal/orchestration/incremental/` (EffectBasedDetector, CacheManager). Pipeline inputs were consolidated via BuildInput in orchestration/build/inputs.py. Re-evaluate this RFC against current structure before implementing.

---

## Executive Summary

Bengal's incremental build system has grown organically across two packages (`cache/` and `orchestration/`) with significant overlap, unclear boundaries, and two competing systems (deprecated DependencyTracker-based and new provenance-based). This RFC proposes extracting incremental build logic into a dedicated `bengal/build/` package to establish clear responsibility boundaries and complete the migration to provenance-based builds.

**Key Changes**:
1. Create `bengal/build/` package owning incremental build **logic**
2. Simplify `bengal/cache/` to pure **storage**
3. Simplify `bengal/orchestration/` to execution **coordination**
4. Complete migration from deprecated system to provenance-based system

**Estimated Effort**: TBD (requires planning)

---

## Goals and Non-Goals

### Goals

1. **Clear Package Boundaries**: Each package has a single, well-defined responsibility
2. **Complete Deprecation Migration**: Remove old DependencyTracker-based system
3. **Canonical Path Keys**: Eliminate path format mismatches via centralized key functions
4. **Detector Protocol**: Uniform interface for all change detectors enabling composition and testing
5. **Reduced Coupling**: `cache/` has no build logic; `orchestration/` has no detection logic
6. **Backward Compatibility**: Existing sites work without configuration changes

### Non-Goals

1. **New Caching Strategy**: Not introducing effect-traced builds (separate RFC)
2. **Performance Optimization**: Focus is architecture, not speed (though clarity may help)
3. **Cache Format Changes**: Existing `.bengal/` structure remains compatible
4. **User-Facing Changes**: Build output should be identical
5. **API Breaking Changes**: External integrations continue working

---

## Problem Statement

### Current Architecture

The incremental build system is split across two packages with overlapping responsibilities:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT STATE (PROBLEMATIC)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/cache/                                                          │
│  ├── build_cache/core.py                   ← Storage + Logic mixed      │
│  ├── dependency_tracker.py                 ← Orchestration concern!     │
│  ├── coordinator.py                        ← Orchestration concern!     │
│  └── provenance/                           ← Build logic!               │
│      ├── types.py                                                            │
│      ├── cache.py                                                            │
│      └── filter.py                             ← Detection logic!            │
│                                                                              │
│  bengal/orchestration/incremental/                                           │
│  ├── orchestrator.py                           ← Uses cache.DependencyTracker│
│  ├── pipeline.py                               ← Change detection pipeline   │
│  ├── filter_engine.py (DEPRECATED)             ← Still in codebase!          │
│  ├── cache_manager.py                          ← Cache concern!              │
│  ├── file_detector.py                                                        │
│  ├── data_detector.py                                                        │
│  ├── taxonomy_detector.py                                                    │
│  ├── template_detector.py                                                    │
│  ├── version_detector.py                                                     │
│  └── 5 more files...                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Problem 1: Legacy and Provenance Systems Co-exist

Two incremental build systems exist:

**Legacy System (Deprecated)**:
- `cache/dependency_tracker.py` - Explicit `track_*()` calls
- `orchestration/incremental/filter_engine.py` - Marked deprecated
- `orchestration/build/initialization.py:phase_incremental_filter()` - Deprecated entry point

**Provenance System (Default in build orchestrator)**:
- `cache/provenance/` - Content-addressed hashing
- `orchestration/build/provenance_filter.py` - Provenance-based filtering
- `orchestration/build/__init__.py` - Uses provenance filter by default

```python
# bengal/orchestration/build/__init__.py:396-410
# Build orchestrator uses provenance-based filtering by default.
from bengal.orchestration.build.provenance_filter import (
    phase_incremental_filter_provenance,
)
filter_result = phase_incremental_filter_provenance(
    self,
    cli,
    cache,
    incremental,
    verbose,
    build_start,
    changed_sources=changed_sources,
    nav_changed_sources=nav_changed_sources,
)
```

**Evidence**: Legacy API remains while build orchestrator uses provenance by default:

- Legacy filter is deprecated and still present: `bengal/orchestration/incremental/filter_engine.py:394-440`
- Deprecated phase still exists: `bengal/orchestration/build/initialization.py:552-657`
- Build orchestrator uses provenance filtering by default: `bengal/orchestration/build/__init__.py:396-410`
- Provenance filter implementation and imports: `bengal/orchestration/build/provenance_filter.py:1-71`
- Incremental package deprecation notice: `bengal/orchestration/incremental/__init__.py:4-39`
- Documentation string claims "30x faster" (needs validation): `bengal/orchestration/build/provenance_filter.py:1-50`, `bengal/orchestration/build/initialization.py:563-569`

```python
# bengal/orchestration/incremental/filter_engine.py:394-401
class IncrementalFilterEngine:
    """
    .. deprecated:: 0.2.0
    Use ``bengal.build.provenance.ProvenanceFilter`` instead.
    """
```

### Problem 2: Responsibility Bleed

Components live in wrong packages:

| Component | Lives In | Actual Responsibility |
|-----------|----------|----------------------|
| `DependencyTracker` | `cache/` | Runtime dependency tracking (orchestration) |
| `CacheCoordinator` | `cache/` | Build invalidation coordination (orchestration) |
| `ProvenanceFilter` | `cache/provenance/` | What to build filtering (orchestration) |
| `ChangeDetector` | `orchestration/` | Cache state queries (cache) |
| `CacheManager` | `orchestration/incremental/` | Cache lifecycle (cache) |

**Evidence**:

- `CacheCoordinator` depends on `BuildCache`, `DependencyTracker`, and `Site`: `bengal/cache/coordinator.py:78-121`
- `DependencyTracker` uses prefixed dependency keys and writes into cache: `bengal/cache/dependency_tracker.py:294-349`
- `ProvenanceFilter` imported from `bengal.build.provenance`: `bengal/orchestration/build/provenance_filter.py:20-71`
- Incremental package exposes `ChangeDetector` and `CacheManager`: `bengal/orchestration/incremental/__init__.py:10-73`

**Evidence** (example signature):
```python
# bengal/cache/coordinator.py:106-119
class CacheCoordinator:
    """Coordinates cache invalidation across page-level cache layers."""
    
    def __init__(
        self,
        cache: BuildCache,
        tracker: DependencyTracker,  # ← Depends on orchestration concepts
        site: Site,                   # ← Depends on core models
    ) -> None:
```

### Problem 3: Path Format Inconsistency

Examples of non-canonical key formats in use today:

```python
# bengal/cache/build_cache/file_tracking.py:131
file_key = str(file_path)

# bengal/cache/dependency_tracker.py:315-318
dep_key = f"data:{data_file}"
self.cache.add_dependency(page_path, Path(dep_key))

# bengal/orchestration/incremental/data_detector.py:112-120
if self.cache.is_changed(data_file):
    changed_data_files.append(data_file)
```

**Evidence**:
- File tracking stores raw `str(file_path)` keys: `bengal/cache/build_cache/file_tracking.py:131-141`
- Dependency tracker prefixes data dependencies: `bengal/cache/dependency_tracker.py:315-318`
- Data detector uses `is_changed(data_file)` without prefix: `bengal/orchestration/incremental/data_detector.py:112-120`
- Incremental filter uses `is_changed(page.source_path)` (absolute path): `bengal/orchestration/incremental/filter_engine.py:756-763`
- Provenance filter uses relative path strings: `bengal/cache/provenance/filter.py:306-311`

### Problem 4: No Detector Contract

Each detector uses a distinct method signature, which blocks uniform composition:

```python
# bengal/orchestration/incremental/file_detector.py:78-87
def check_pages(
    self,
    *,
    pages_to_check: list[Page],
    changed_sections: set[Section] | None,
    all_changed: set[Path],
    pages_to_rebuild: set[Path],
    change_summary: ChangeSummary,
    verbose: bool,
) -> None:

# bengal/orchestration/incremental/data_detector.py:84-90
def check_data_files(
    self,
    *,
    pages_to_rebuild: set[Path],
    change_summary: ChangeSummary,
    verbose: bool,
) -> int:

# bengal/orchestration/incremental/taxonomy_detector.py:71-77
def check_taxonomy_changes(
    self,
    *,
    pages_to_rebuild: set[Path],
    change_summary: ChangeSummary,
    verbose: bool,
) -> None:
```

**Problems**:
- No shared protocol or return type for composition
- Hard to swap implementations in tests without adapters

### Impact Summary

| Problem | Impact | Frequency |
|---------|--------|-----------|
| Legacy and provenance systems co-exist | Maintenance burden; unclear ownership | TBD |
| Responsibility bleed | Tight coupling across packages | TBD |
| Path format inconsistency | Inconsistent cache key usage | TBD |
| No detector contract | Harder composition and testing | TBD |

---

## Proposed Solution

### New Package Structure

Create `bengal/build/` package that owns incremental build **domain logic**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROPOSED ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/build/ (NEW - Owns incremental build logic)                          │
│  ├── __init__.py                                                             │
│  │                                                                           │
│  ├── contracts/              # From RFC: Incremental Build Contracts         │
│  │   ├── __init__.py                                                         │
│  │   ├── keys.py            # CacheKey, content_key(), data_key()            │
│  │   ├── results.py         # ChangeDetectionResult, RebuildReason           │
│  │   └── protocol.py        # ChangeDetector protocol                        │
│  │                                                                           │
│  ├── provenance/             # Moved from cache/provenance/                  │
│  │   ├── __init__.py                                                         │
│  │   ├── types.py            # Provenance, InputRecord, ContentHash          │
│  │   ├── store.py            # ProvenanceStore (was cache.py)                │
│  │   └── filter.py           # ProvenanceFilter                              │
│  │                                                                           │
│  ├── detectors/              # Protocol-based, composable                    │
│  │   ├── __init__.py                                                         │
│  │   ├── base.py             # BaseDetector, DetectorResult                  │
│  │   ├── content.py          # ContentChangeDetector                         │
│  │   ├── data.py             # DataChangeDetector                            │
│  │   ├── template.py         # TemplateChangeDetector                        │
│  │   ├── taxonomy.py         # TaxonomyCascadeDetector                       │
│  │   ├── autodoc.py          # AutodocChangeDetector                         │
│  │   └── version.py          # VersionChangeDetector                         │
│  │                                                                           │
│  ├── tracking/               # Dependency tracking                           │
│  │   ├── __init__.py                                                         │
│  │   ├── tracker.py          # DependencyTracker (moved from cache/)         │
│  │   └── invalidator.py      # CacheInvalidator                              │
│  │                                                                           │
│  └── pipeline.py             # DetectionPipeline (composable)                │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/cache/ (SIMPLIFIED - Pure storage)                                   │
│  ├── __init__.py                                                             │
│  │                                                                           │
│  ├── build_cache/            # Storage only, no logic                        │
│  │   ├── core.py             # BuildCache dataclass (fingerprints, deps)     │
│  │   ├── file_tracking.py    # FileTrackingMixin (I/O operations)            │
│  │   └── serialization.py    # Load/save with compression                    │
│  │                                                                           │
│  ├── indexes/                # Read-only query indexes                       │
│  │   ├── __init__.py                                                         │
│  │   ├── taxonomy_index.py                                                   │
│  │   └── query_index.py                                                      │
│  │                                                                           │
│  ├── compression.py          # Zstd utilities                                │
│  ├── paths.py                # Cache path management                         │
│  └── version.py              # Cache version handling                        │
│                                                                              │
│  REMOVED (moved to bengal/build/):                                           │
│  - dependency_tracker.py     → build/tracking/tracker.py                     │
│  - coordinator.py            → orchestration/build/coordinator.py            │
│  - provenance/               → build/provenance/                             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/orchestration/ (SIMPLIFIED - Execution coordination)                 │
│  ├── build/                                                                  │
│  │   ├── __init__.py         # BuildOrchestrator                             │
│  │   ├── initialization.py   # Build phase setup (uses build.pipeline)       │
│  │   ├── coordinator.py      # CacheCoordinator (moved from cache/)          │
│  │   ├── finalization.py     # Build phase teardown                          │
│  │   └── results.py          # BuildResult, BuildStats                       │
│  │                                                                           │
│  ├── render/                 # Rendering coordination                        │
│  │                                                                           │
│  REMOVED (moved/deleted):                                                    │
│  - incremental/filter_engine.py    → DELETED (deprecated)                    │
│  - incremental/change_detector.py  → build/pipeline.py                       │
│  - incremental/*_detector.py       → build/detectors/                        │
│  - incremental/cache_manager.py    → build/tracking/                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Package Responsibilities

| Package | Responsibility | Does NOT |
|---------|---------------|----------|
| `bengal/build/` | Incremental build logic, change detection, dependency tracking | Execute builds, manage I/O |
| `bengal/cache/` | Cache storage, serialization, compression | Make build decisions |
| `bengal/orchestration/` | Build execution, coordination, rendering | Detect changes, track dependencies |

### Recommended Approach

Adopt the proposed package split and execute the phased migration plan (Phases 1-5). Use compatibility re-exports during migration, then remove deprecated incremental components after new detectors and pipeline are in place.

### Architecture Impact

**Target dependency direction**: `core → cache → build → orchestration`.

**Current anchor**: Build orchestrator already uses provenance-based filtering by default, so the proposed build package can align with existing runtime usage.  
**Evidence**: `bengal/orchestration/build/__init__.py:396-410`, `bengal/orchestration/build/provenance_filter.py:1-71`

### Key Design: Contracts Package

From RFC-incremental-build-contracts, the `build/contracts/` module provides:

#### 1. Canonical Path Keys (`keys.py`)

```python
# bengal/build/contracts/keys.py
"""
Canonical cache key generation.

ALL cache operations MUST use these functions for path keys.
This ensures consistent lookup regardless of how paths arrive
(absolute, relative, with/without prefix).
"""

from __future__ import annotations

from pathlib import Path
from typing import NewType

# Type-safe cache key - prevents accidental str mixing
CacheKey = NewType("CacheKey", str)


def content_key(path: Path, site_root: Path) -> CacheKey:
    """
    Canonical key for content files (pages, sections).
    
    Always relative to site root, forward slashes, no leading dot.
    
    Examples:
        content_key(Path("/site/content/about.md"), Path("/site"))
        → "content/about.md"
    """
    try:
        rel = path.resolve().relative_to(site_root.resolve())
        return CacheKey(str(rel).replace("\\", "/"))
    except ValueError:
        # External path - use resolved absolute
        return CacheKey(str(path.resolve()).replace("\\", "/"))


def data_key(path: Path, site_root: Path) -> CacheKey:
    """
    Canonical key for data files.
    
    Prefixed with "data:" to distinguish from content.
    
    Examples:
        data_key(Path("/site/data/team.yaml"), Path("/site"))
        → "data:data/team.yaml"
    """
    rel = content_key(path, site_root)
    return CacheKey(f"data:{rel}")


def template_key(path: Path, templates_dir: Path) -> CacheKey:
    """Canonical key for template files."""
    try:
        rel = path.resolve().relative_to(templates_dir.resolve())
        return CacheKey(str(rel).replace("\\", "/"))
    except ValueError:
        return CacheKey(str(path.resolve()).replace("\\", "/"))


def asset_key(path: Path, assets_dir: Path) -> CacheKey:
    """Canonical key for asset files."""
    try:
        rel = path.resolve().relative_to(assets_dir.resolve())
        return CacheKey(str(rel).replace("\\", "/"))
    except ValueError:
        return CacheKey(str(path.resolve()).replace("\\", "/"))


def parse_key(key: CacheKey) -> tuple[str, str]:
    """
    Parse a cache key into (prefix, path).
    
    Examples:
        parse_key("data:data/team.yaml") → ("data", "data/team.yaml")
        parse_key("content/about.md") → ("", "content/about.md")
    """
    if ":" in key and not key.startswith("/"):
        prefix, path = key.split(":", 1)
        return (prefix, path)
    return ("", key)
```

#### 2. Immutable Results (`results.py`)

```python
# bengal/build/contracts/results.py
"""
Immutable result types for change detection.

All detectors return ChangeDetectionResult. Results are merged
with `.merge()` to compose detector outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from bengal.build.contracts.keys import CacheKey


class RebuildReasonCode(Enum):
    """Why a page needs rebuilding."""
    
    CONTENT_CHANGED = auto()
    DATA_FILE_CHANGED = auto()
    TEMPLATE_CHANGED = auto()
    TAXONOMY_CASCADE = auto()
    ASSET_FINGERPRINT_CHANGED = auto()
    CONFIG_CHANGED = auto()
    OUTPUT_MISSING = auto()
    CROSS_VERSION_DEPENDENCY = auto()
    ADJACENT_NAV_CHANGED = auto()
    FORCED = auto()
    FULL_REBUILD = auto()


@dataclass(frozen=True, slots=True)
class RebuildReason:
    """Detailed reason for page rebuild."""
    
    code: RebuildReasonCode
    trigger: str = ""  # What triggered it (e.g., "data/team.yaml")
    
    def __str__(self) -> str:
        if self.trigger:
            return f"{self.code.name}: {self.trigger}"
        return self.code.name


@dataclass(frozen=True, slots=True)
class ChangeDetectionResult:
    """
    Immutable result of change detection.
    
    Produced by each detector, merged to accumulate changes.
    
    Thread Safety:
        Frozen dataclass - inherently thread-safe.
        Can be safely passed between threads without copying.
    
    Example:
        >>> content_result = content_detector.detect(ctx)
        >>> data_result = data_detector.detect(ctx)
        >>> combined = content_result.merge(data_result)
    """
    
    # Pages that need rebuilding (canonical keys)
    pages_to_rebuild: frozenset[CacheKey] = field(default_factory=frozenset)
    
    # Why each page needs rebuilding (for logging/debugging)
    rebuild_reasons: Mapping[CacheKey, RebuildReason] = field(default_factory=dict)
    
    # Assets that need processing
    assets_to_process: frozenset[CacheKey] = field(default_factory=frozenset)
    
    # What changed (for downstream detectors)
    content_files_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    data_files_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    templates_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    
    # Affected taxonomies (for taxonomy detector)
    affected_tags: frozenset[str] = field(default_factory=frozenset)
    affected_sections: frozenset[CacheKey] = field(default_factory=frozenset)
    
    # Global flags
    config_changed: bool = False
    force_full_rebuild: bool = False
    
    @classmethod
    def empty(cls) -> ChangeDetectionResult:
        """Create empty result."""
        return cls()
    
    @classmethod
    def full_rebuild(cls, reason: str = "forced") -> ChangeDetectionResult:
        """Create result indicating full rebuild needed."""
        return cls(force_full_rebuild=True)
    
    def merge(self, other: ChangeDetectionResult) -> ChangeDetectionResult:
        """
        Merge two results (immutable - returns new instance).
        
        Used to compose results from multiple detectors.
        """
        return ChangeDetectionResult(
            pages_to_rebuild=self.pages_to_rebuild | other.pages_to_rebuild,
            rebuild_reasons={**self.rebuild_reasons, **other.rebuild_reasons},
            assets_to_process=self.assets_to_process | other.assets_to_process,
            content_files_changed=self.content_files_changed | other.content_files_changed,
            data_files_changed=self.data_files_changed | other.data_files_changed,
            templates_changed=self.templates_changed | other.templates_changed,
            affected_tags=self.affected_tags | other.affected_tags,
            affected_sections=self.affected_sections | other.affected_sections,
            config_changed=self.config_changed or other.config_changed,
            force_full_rebuild=self.force_full_rebuild or other.force_full_rebuild,
        )
    
    def with_pages(
        self,
        pages: frozenset[CacheKey],
        reason: RebuildReason,
    ) -> ChangeDetectionResult:
        """Add pages with reason (returns new instance)."""
        new_reasons = {**self.rebuild_reasons}
        for page in pages:
            if page not in new_reasons:  # Don't overwrite existing reason
                new_reasons[page] = reason
        return ChangeDetectionResult(
            pages_to_rebuild=self.pages_to_rebuild | pages,
            rebuild_reasons=new_reasons,
            assets_to_process=self.assets_to_process,
            content_files_changed=self.content_files_changed,
            data_files_changed=self.data_files_changed,
            templates_changed=self.templates_changed,
            affected_tags=self.affected_tags,
            affected_sections=self.affected_sections,
            config_changed=self.config_changed,
            force_full_rebuild=self.force_full_rebuild,
        )
    
    @property
    def needs_rebuild(self) -> bool:
        """Check if any pages need rebuilding."""
        return bool(self.pages_to_rebuild) or self.force_full_rebuild
    
    def summary(self) -> str:
        """Human-readable summary."""
        parts = []
        if self.force_full_rebuild:
            parts.append("FULL REBUILD")
        if self.pages_to_rebuild:
            parts.append(f"{len(self.pages_to_rebuild)} pages")
        if self.assets_to_process:
            parts.append(f"{len(self.assets_to_process)} assets")
        if self.data_files_changed:
            parts.append(f"{len(self.data_files_changed)} data files")
        if self.templates_changed:
            parts.append(f"{len(self.templates_changed)} templates")
        return ", ".join(parts) or "no changes"
```

#### 3. Detector Protocol (`protocol.py`)

```python
# bengal/build/contracts/protocol.py
"""
Change detector protocol.

All detectors implement this interface, enabling:
- Uniform testing
- Composable pipelines
- Swappable implementations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.build.contracts.keys import CacheKey
    from bengal.build.contracts.results import ChangeDetectionResult
    from bengal.cache import BuildCache
    from bengal.core.site import Site


@dataclass(frozen=True, slots=True)
class DetectionContext:
    """
    Immutable context passed to detectors.
    
    Contains everything a detector needs to detect changes.
    Accumulated results from previous detectors are available
    for cascade detection (e.g., template changes affect pages).
    """
    
    # Core dependencies
    cache: BuildCache
    site: Site
    
    # Accumulated results from previous detectors
    previous: ChangeDetectionResult = field(default_factory=ChangeDetectionResult.empty)
    
    # Configuration
    verbose: bool = False
    
    # Forced changes (from file watcher)
    forced_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    
    # Nav-affecting changes (structural)
    nav_changed: frozenset[CacheKey] = field(default_factory=frozenset)
    
    def with_previous(self, result: ChangeDetectionResult) -> DetectionContext:
        """Create new context with updated previous results."""
        return DetectionContext(
            cache=self.cache,
            site=self.site,
            previous=self.previous.merge(result),
            verbose=self.verbose,
            forced_changed=self.forced_changed,
            nav_changed=self.nav_changed,
        )


@runtime_checkable
class ChangeDetector(Protocol):
    """
    Protocol for change detection components.
    
    Each detector:
    1. Receives context with cache, site, and previous results
    2. Returns immutable ChangeDetectionResult
    3. Does NOT mutate shared state
    
    Example Implementation:
        class DataChangeDetector:
            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                changed_data = self._find_changed_data_files(ctx.cache)
                affected_pages = self._find_affected_pages(changed_data)
                return ChangeDetectionResult(
                    pages_to_rebuild=affected_pages,
                    data_files_changed=changed_data,
                )
    
    Thread Safety:
        Must be thread-safe. Do not mutate ctx or shared state.
        Return new ChangeDetectionResult instances.
    """
    
    def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
        """
        Detect changes and return result.
        
        Args:
            ctx: Detection context with cache, site, and accumulated results
            
        Returns:
            ChangeDetectionResult with detected changes
        """
        ...
```

### Key Design: Detection Pipeline

```python
# bengal/build/pipeline.py
"""
Composable change detection pipeline.

Detectors are composed in explicit order. Each detector
receives results from previous detectors via context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import ChangeDetector, DetectionContext
    from bengal.build.contracts.results import ChangeDetectionResult

logger = get_logger(__name__)


@dataclass
class DetectionPipeline:
    """
    Ordered sequence of change detectors.
    
    Detectors run in sequence, each receiving accumulated
    results from previous detectors.
    
    Example:
        pipeline = DetectionPipeline([
            ConfigChangeDetector(),      # Must run first
            ContentChangeDetector(),     # Detect changed content
            DataChangeDetector(),        # Detect changed data files
            TemplateChangeDetector(),    # Detect changed templates
            TaxonomyCascadeDetector(),   # Cascade from content changes
        ])
        
        result = pipeline.run(ctx)
    """
    
    detectors: Sequence[ChangeDetector]
    
    def run(self, ctx: DetectionContext) -> ChangeDetectionResult:
        """
        Run all detectors in sequence.
        
        Each detector receives context with accumulated results
        from previous detectors.
        
        Returns:
            Combined ChangeDetectionResult from all detectors
        """
        current_ctx = ctx
        
        for detector in self.detectors:
            detector_name = type(detector).__name__
            
            logger.debug(
                "detector_start",
                detector=detector_name,
                previous_pages=len(current_ctx.previous.pages_to_rebuild),
            )
            
            result = detector.detect(current_ctx)
            
            logger.debug(
                "detector_complete",
                detector=detector_name,
                pages_found=len(result.pages_to_rebuild),
                data_files=len(result.data_files_changed),
                templates=len(result.templates_changed),
            )
            
            # Update context with this detector's results
            current_ctx = current_ctx.with_previous(result)
            
            # Short-circuit if full rebuild triggered
            if result.force_full_rebuild:
                logger.info(
                    "full_rebuild_triggered",
                    detector=detector_name,
                )
                break
        
        return current_ctx.previous


# Standard pipeline configurations

def create_early_pipeline() -> DetectionPipeline:
    """
    Pipeline for early (pre-taxonomy) detection.
    
    Runs before taxonomies are generated.
    """
    from bengal.build.detectors import (
        ConfigChangeDetector,
        ContentChangeDetector,
        DataChangeDetector,
        TemplateChangeDetector,
    )
    
    return DetectionPipeline([
        ConfigChangeDetector(),
        ContentChangeDetector(),
        DataChangeDetector(),
        TemplateChangeDetector(),
    ])


def create_full_pipeline() -> DetectionPipeline:
    """
    Pipeline for full (post-taxonomy) detection.
    
    Runs after taxonomies are generated to handle cascades.
    """
    from bengal.build.detectors import (
        TaxonomyCascadeDetector,
        AutodocChangeDetector,
        VersionChangeDetector,
    )
    
    return DetectionPipeline([
        TaxonomyCascadeDetector(),
        AutodocChangeDetector(),
        VersionChangeDetector(),
    ])
```

---

## Migration Plan

### Phase 1: Create Foundation (Week 1)

**Goal**: Create `bengal/build/` package with contracts.

**Tasks**:
1. Create `bengal/build/__init__.py`
2. Create `bengal/build/contracts/keys.py` with canonical key functions
3. Create `bengal/build/contracts/results.py` with immutable results
4. Create `bengal/build/contracts/protocol.py` with detector protocol
5. Add comprehensive tests for key functions

**Backward Compatible**: No changes to existing code yet.

**Outputs**:
- `bengal/build/contracts/` package
- Tests in `tests/unit/build/contracts/`

### Phase 2: Migrate Provenance System (Week 1-2)

**Goal**: Move provenance system to `bengal/build/`.

**Tasks**:
1. Copy `cache/provenance/` → `build/provenance/`
2. Update provenance to use `CacheKey` from contracts
3. Add re-exports in `cache/provenance/__init__.py` for compatibility
4. Update `orchestration/build/provenance_filter.py` to use new location

**Backward Compatible**: Old imports still work via re-exports.

**Outputs**:
- `bengal/build/provenance/` package
- Deprecation warnings on old imports

### Phase 3: Migrate Detectors (Week 2)

**Goal**: Create protocol-based detectors in `bengal/build/detectors/`.

**Tasks**:
1. Create `bengal/build/detectors/base.py` with base detector class
2. Migrate `orchestration/incremental/file_detector.py` → `build/detectors/content.py`
3. Migrate `orchestration/incremental/data_detector.py` → `build/detectors/data.py`
4. Migrate `orchestration/incremental/template_detector.py` → `build/detectors/template.py`
5. Migrate `orchestration/incremental/taxonomy_detector.py` → `build/detectors/taxonomy.py`
6. Migrate `orchestration/incremental/version_detector.py` → `build/detectors/version.py`
7. Create `bengal/build/pipeline.py` with `DetectionPipeline`

**All new detectors**:
- Implement `ChangeDetector` protocol
- Return `ChangeDetectionResult`
- Use `CacheKey` for all paths

**Backward Compatible**: Old detectors remain as deprecated aliases.

**Outputs**:
- `bengal/build/detectors/` package
- `bengal/build/pipeline.py`
- Tests for each detector

### Phase 4: Migrate Tracking (Week 2-3)

**Goal**: Move dependency tracking to `bengal/build/tracking/`.

**Tasks**:
1. Move `cache/dependency_tracker.py` → `build/tracking/tracker.py`
2. Move `cache/coordinator.py` → `orchestration/build/coordinator.py`
3. Update `DependencyTracker` to use `CacheKey`
4. Add re-exports for compatibility
5. Update all imports in codebase

**Backward Compatible**: Re-exports preserve old import paths.

**Outputs**:
- `bengal/build/tracking/` package
- Updated `orchestration/build/coordinator.py`

### Phase 5: Integration and Cleanup (Week 3-4)

**Goal**: Integrate new system and remove deprecated code.

**Tasks**:
1. Update `orchestration/build/initialization.py` to use `DetectionPipeline`
2. Update `IncrementalOrchestrator` to use new detectors
3. Delete deprecated `orchestration/incremental/filter_engine.py`
4. Delete deprecated detector files after migration
5. Simplify `BuildCache` by removing logic (keep storage)
6. Update documentation

**Breaking Changes** (with deprecation period):
- Old detector imports → emit deprecation warnings → remove in next minor version

**Outputs**:
- Integrated build system
- Cleaned up codebase
- Updated documentation

---

## Dependency Graph (Post-Migration)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY FLOW (POST-MIGRATION)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  bengal/core/                                                                │
│  ├── site.py        ─────────────────┐                                       │
│  ├── page/          ─────────────────┤                                       │
│  └── section/       ─────────────────┤                                       │
│                                      │                                       │
│                                      ▼                                       │
│  bengal/cache/                       │                                       │
│  ├── build_cache/   ◄────────────────┤  (Pure storage)                       │
│  ├── indexes/       ◄────────────────┤                                       │
│  └── compression.py                  │                                       │
│                                      │                                       │
│                                      ▼                                       │
│  bengal/build/                       │                                       │
│  ├── contracts/     ◄────────────────┤  (Domain logic)                       │
│  ├── provenance/    ◄────────────────┤                                       │
│  ├── detectors/     ◄────────────────┤                                       │
│  ├── tracking/      ◄────────────────┤                                       │
│  └── pipeline.py    ◄────────────────┤                                       │
│                                      │                                       │
│                                      ▼                                       │
│  bengal/orchestration/               │                                       │
│  ├── build/         ◄────────────────┘  (Execution coordination)             │
│  └── render/                                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Direction: core → cache → build → orchestration
No reverse dependencies allowed.
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/build/contracts/test_keys.py

def test_content_key_relative():
    """Content key is relative to site root."""
    key = content_key(Path("/site/content/about.md"), Path("/site"))
    assert key == "content/about.md"

def test_content_key_normalizes_backslashes():
    """Windows paths are normalized to forward slashes."""
    key = content_key(Path("content\\docs\\guide.md"), Path("."))
    assert "/" in key
    assert "\\" not in key

def test_data_key_prefix():
    """Data keys have 'data:' prefix."""
    key = data_key(Path("/site/data/team.yaml"), Path("/site"))
    assert key == "data:data/team.yaml"

def test_parse_key_with_prefix():
    """Parse key extracts prefix and path."""
    prefix, path = parse_key(CacheKey("data:data/team.yaml"))
    assert prefix == "data"
    assert path == "data/team.yaml"

def test_parse_key_without_prefix():
    """Parse key handles keys without prefix."""
    prefix, path = parse_key(CacheKey("content/about.md"))
    assert prefix == ""
    assert path == "content/about.md"
```

### Integration Tests

```python
# tests/integration/build/test_pipeline.py

def test_pipeline_accumulates_results():
    """Each detector receives previous results."""
    detector1 = MockDetector(pages={"page1.md"})
    detector2 = MockDetector(pages={"page2.md"})
    
    pipeline = DetectionPipeline([detector1, detector2])
    result = pipeline.run(ctx)
    
    assert len(result.pages_to_rebuild) == 2
    assert "page1.md" in result.pages_to_rebuild
    assert "page2.md" in result.pages_to_rebuild

def test_pipeline_short_circuits_on_full_rebuild():
    """Full rebuild trigger stops pipeline early."""
    detector1 = MockDetector(force_full=True)
    detector2 = MockDetector(pages={"page.md"})
    
    pipeline = DetectionPipeline([detector1, detector2])
    result = pipeline.run(ctx)
    
    assert result.force_full_rebuild
    assert not detector2.was_called

def test_detector_receives_previous_results():
    """Detector context includes previous detector results."""
    detector1 = MockDetector(data_files={"data/team.yaml"})
    detector2 = CapturingDetector()
    
    pipeline = DetectionPipeline([detector1, detector2])
    pipeline.run(ctx)
    
    assert "data/team.yaml" in detector2.received_ctx.previous.data_files_changed
```

### Warm Build Tests

```python
# tests/integration/build/test_incremental.py

def test_data_file_change_triggers_dependent_pages():
    """Changing data file rebuilds pages that use it."""
    # Build site
    build_site(site)
    
    # Modify data file
    modify_file(site.root_path / "data" / "team.yaml")
    
    # Rebuild incrementally
    result = build_site(site, incremental=True)
    
    # Pages using team data should be rebuilt
    assert "content/about.md" in result.pages_rebuilt
    assert "content/docs/index.md" not in result.pages_rebuilt  # Doesn't use team

def test_template_change_triggers_all_users():
    """Changing template rebuilds all pages using it."""
    build_site(site)
    modify_file(site.root_path / "layouts" / "single.html")
    result = build_site(site, incremental=True)
    
    # All pages using single.html should be rebuilt
    for page in result.pages_rebuilt:
        assert get_page_template(page) == "single.html"
```

---

## Risks and Mitigation Plan

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import breakage | High | Medium | Re-export from old locations during migration |
| Performance regression | Low | Medium | Benchmark at each phase; immutability often helps |
| Path edge cases | Medium | High | Comprehensive tests for symlinks, case, Windows |
| Circular imports | Medium | High | Strict dependency direction: core → cache → build → orch |
| Test failures | High | Low | Run full test suite at each phase |
| Cache compatibility | Medium | Medium | Verify with migration tests; bump cache version if needed |

### Migration Compatibility

**Question**: Will existing `.bengal/` cache work after migration?

**Answer**: TBD — requires verification during implementation.

**Plan**:
1. Add migration tests that compare legacy keys vs new `CacheKey` output
2. Treat mismatches as acceptable rebuilds during transition (never skip builds on uncertainty)
3. Bump `BuildCache.VERSION` if incompatibilities are discovered
4. Provide `bengal build --clean` as an escape hatch

---

## Success Criteria

### Phase 1 Complete
- [ ] `bengal/build/contracts/` package exists
- [ ] `CacheKey` type used for all path keys
- [ ] Unit tests for key functions pass

### Phase 2 Complete
- [ ] `bengal/build/provenance/` package exists
- [ ] Old imports via re-exports still work
- [ ] Provenance-based incremental builds work

### Phase 3 Complete
- [ ] All detectors implement `ChangeDetector` protocol
- [ ] `DetectionPipeline` composes detectors
- [ ] Unit tests for each detector pass

### Phase 4 Complete
- [ ] `DependencyTracker` moved to `build/tracking/`
- [ ] `CacheCoordinator` moved to `orchestration/build/`
- [ ] No circular imports

### Phase 5 Complete
- [ ] Deprecated code deleted
- [ ] No path format mismatches in fingerprint lookup
- [ ] Full test suite passes
- [ ] Incremental build performance unchanged or improved

---

## Alternatives Considered

### 1. Merge Everything into `cache/`

**Approach**: Move all incremental build logic into `cache/`.

**Pros**:
- Single location for all caching
- Simple package structure

**Cons**:
- `cache/` becomes orchestration-aware
- 50+ files in one package
- Doesn't solve responsibility confusion

**Rejected**: Makes `cache/` even more bloated.

### 2. Merge Everything into `orchestration/`

**Approach**: Move all incremental build logic into `orchestration/`.

**Pros**:
- Single location for all build logic
- Clear "build happens here"

**Cons**:
- `orchestration/` becomes 100+ files
- Cache storage mixed with build execution
- Still confused responsibilities

**Rejected**: Makes `orchestration/` unmanageable.

### 3. Fix Issues Incrementally Without Restructure

**Approach**: Just fix path format bugs, leave packages as-is.

**Pros**:
- Lower risk
- Faster

**Cons**:
- We've done this 3+ times
- Root cause (unclear responsibilities) remains
- Technical debt continues accumulating

**Rejected**: Doesn't address root cause.

### 4. Wait for Effect-Traced Builds RFC

**Approach**: Defer to rfc-effect-traced-incremental-builds.md implementation.

**Pros**:
- Effect system replaces explicit tracking
- More thorough solution

**Cons**:
- Effect RFC is larger scope (6+ weeks)
- Current bugs block users now
- Effect system still needs clear packages

**Partially Adopted**: Effect RFC can build on this foundation. This RFC creates clear package boundaries that Effect RFC can use.

---

## References

- `plan/rfc-incremental-build-contracts.md` - Contracts design
- `plan/rfc-effect-traced-incremental-builds.md` - Future effect system
- `plan/rfc-cache-invalidation-architecture.md` - Cache coordination
- `plan/rfc-incremental-build-dependency-gaps.md` - Dependency gaps
- `bengal/cache/build_cache/core.py` - Current BuildCache
- `bengal/cache/dependency_tracker.py` - Current DependencyTracker
- `bengal/orchestration/incremental/` - Current detectors

---

## Appendix A: File Inventory

### Files to Create

```
bengal/build/
├── __init__.py
├── contracts/
│   ├── __init__.py
│   ├── keys.py
│   ├── results.py
│   └── protocol.py
├── provenance/
│   ├── __init__.py
│   ├── types.py
│   ├── store.py
│   └── filter.py
├── detectors/
│   ├── __init__.py
│   ├── base.py
│   ├── content.py
│   ├── data.py
│   ├── template.py
│   ├── taxonomy.py
│   ├── autodoc.py
│   └── version.py
├── tracking/
│   ├── __init__.py
│   ├── tracker.py
│   └── invalidator.py
└── pipeline.py
```

### Files to Move

| From | To |
|------|-----|
| `cache/provenance/types.py` | `build/provenance/types.py` |
| `cache/provenance/cache.py` | `build/provenance/store.py` |
| `cache/provenance/filter.py` | `build/provenance/filter.py` |
| `cache/dependency_tracker.py` | `build/tracking/tracker.py` |
| `cache/coordinator.py` | `orchestration/build/coordinator.py` |
| `orchestration/incremental/file_detector.py` | `build/detectors/content.py` |
| `orchestration/incremental/data_detector.py` | `build/detectors/data.py` |
| `orchestration/incremental/template_detector.py` | `build/detectors/template.py` |
| `orchestration/incremental/taxonomy_detector.py` | `build/detectors/taxonomy.py` |
| `orchestration/incremental/version_detector.py` | `build/detectors/version.py` |

### Files to Delete (Phase 5)

| File | Reason |
|------|--------|
| `orchestration/incremental/filter_engine.py` | Deprecated since 0.2.0 |
| `orchestration/incremental/change_detector.py` | Replaced by `build/pipeline.py` |
| `orchestration/incremental/rebuild_filter.py` | Absorbed into detectors |
| `orchestration/incremental/cascade_tracker.py` | Absorbed into taxonomy detector |
| `orchestration/incremental/cleanup.py` | Move to `orchestration/build/` |

---

## Appendix B: Import Migration Examples

### Before

```python
# Old imports
from bengal.build.tracking import DependencyTracker
from bengal.build.provenance import ProvenanceCache, ProvenanceFilter
from bengal.build.pipeline import DetectionPipeline
from bengal.orchestration.incremental.filter_engine import IncrementalFilterEngine
```

### After

```python
# New imports (preferred)
from bengal.build.tracking import DependencyTracker
from bengal.build.provenance import ProvenanceCache, ProvenanceFilter
from bengal.build.pipeline import DetectionPipeline
from bengal.build.detectors import (
    ContentChangeDetector,
    DataChangeDetector,
    TemplateChangeDetector,
)

# Old imports (deprecated, still work via re-exports)
from bengal.build.tracking import DependencyTracker
from bengal.build.provenance import ProvenanceCache
```

---

## Appendix C: Current Path Inconsistencies (Examples)

Verified examples of non-canonical key formats:

| File | Pattern | Issue |
|------|---------|-------|
| `bengal/cache/build_cache/file_tracking.py:131` | `str(file_path)` | No normalization |
| `bengal/cache/build_cache/file_tracking.py:207` | `str(file_path)` | No normalization |
| `bengal/cache/dependency_tracker.py:315-318` | `f"data:{data_file}"` + `Path(dep_key)` | Prefixed key with re-wrapped path |
| `bengal/orchestration/incremental/data_detector.py:119` | `self.cache.is_changed(data_file)` | No prefix |
| `bengal/orchestration/incremental/filter_engine.py:756-763` | `self.cache.is_changed(page.source_path)` | Absolute path |
| `bengal/orchestration/incremental/rebuild_filter.py:125-126` | `self.cache.is_changed(page.source_path)` | Absolute path |
| `bengal/cache/provenance/filter.py:306-311` | `str(page.source_path.relative_to(...))` | Manual relative |

**Note**: This list is illustrative, not exhaustive.

All will use `CacheKey` functions after migration.
