# RFC: Incremental Build Contracts

## Status: Evaluated — Paths Need Update
## Created: 2026-01-14
## Updated: 2026-02-14
## Confidence: 88% 🟢

> **Path note (2026-02-14)**: `dependency_tracker.py` was removed (replaced by EffectTracer). `file_tracking` lives at `bengal/cache/build_cache/file_tracking.py`. Detectors live in `bengal/orchestration/incremental/` (EffectBasedDetector). Update references before implementing.

---

## Summary

**Problem**: Bengal's incremental build system has grown organically to include 7+ detectors, 4+ cache layers, and 3+ phases—but the contracts between them are implicit. Path formats vary (`str(path)`, `Path`, relative, absolute), results are mutable sets, and phase ordering is encoded in string literals. This leads to subtle bugs that are hard to diagnose.

**Evidence**: The current debugging session revealed that content fingerprints are stored with one path format but looked up with another, causing false "changed" detection. Similar issues have appeared with data file tracking, taxonomy cascades, and template dependencies.

**Solution**: Introduce explicit contracts via:
1. **Canonical path keys** - Single `cache_key()` function used everywhere
2. **Immutable result dataclasses** - `ChangeDetectionResult` replaces mutable sets
3. **Detector protocol** - Composable `ChangeDetector` interface
4. **Phase state machine** - Explicit `BuildPhase` enum with typed transitions

**Estimated Effort**: 2-3 weeks (phased implementation)

---

## Goals and Non-Goals

### Goals

1. **Eliminate path format mismatches** - All cache lookups use identical key format
2. **Enable detector composition** - Uniform protocol allows swapping/testing detectors independently
3. **Improve debuggability** - Rebuild reasons tracked per-page for better diagnostics
4. **Thread-safe change detection** - Immutable results enable safe parallel execution
5. **Type-safe phase transitions** - Compiler catches phase ordering errors

### Non-Goals

1. **Changing cache serialization format** - Existing `.bengal_cache/` structure remains compatible
2. **Modifying build phase order** - INIT → DISCOVERY → DETECTION → TAXONOMY → RENDER order unchanged
3. **Adding new detectors** - Scope limited to contracting existing detectors
4. **Optimizing cache performance** - Focus is correctness, not speed (though immutability may help)
5. **Changing user-facing behavior** - Output should be identical; only internal contracts change

---

## Problem Statement

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INCREMENTAL BUILD FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ FileDetector │    │ DataDetector │    │ TaxDetector  │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         ▼                   ▼                   ▼                            │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │              pages_to_rebuild: set[Path]  (MUTABLE)          │           │
│  │              change_summary: ChangeSummary (MUTABLE)         │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                              │
│  Path Formats Used:                                                          │
│  • str(path)              - cache/build_cache/file_tracking.py            │
│  • str(file_path)         - cache/build_cache/file_tracking.py            │
│  • str(data_file)         - (dependency_tracker removed; see EffectTracer)  │
│  • f"data:{data_file}"    - (legacy; dependency_tracker removed)          │
│  • page.source_path       - sometimes absolute, sometimes relative          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Problems

#### 1. Path Format Chaos

```python
# cache/build_cache/file_tracking.py - stores fingerprints with str(file_path)
file_key = str(file_path)  # Could be absolute or relative
self.file_fingerprints[file_key] = {...}

# (Legacy: dependency_tracker removed; EffectTracer/provenance used now)
# data_detector / effect_detector - looks up; verify path format consistency
if self.cache.is_changed(data_file):  # str(data_file) - no prefix
    ...
```

**Result**: Fingerprint stored as `/abs/path/data/team.yaml`, looked up as `data:data/team.yaml`. Miss.

#### 2. Implicit Phase Ordering

```python
# change_detector.py:129
def detect_changes(
    self,
    phase: Literal["early", "full"],  # String literal!
    ...
):
    if phase == "full":
        self._taxonomy_detector.check_taxonomy_changes(...)  # Only in "full"
```

**Problem**: Nothing prevents calling detectors in wrong order. No type safety.

#### 3. Mutable Shared State

```python
# Multiple detectors mutate the same set
pages_to_rebuild: set[Path] = set()

self._file_detector.check_pages(..., pages_to_rebuild=pages_to_rebuild)
self._data_detector.check_data_files(..., pages_to_rebuild=pages_to_rebuild)
self._taxonomy_detector.check_metadata_cascades(..., pages_to_rebuild=pages_to_rebuild)
```

**Problem**: Race conditions in parallel mode. Hard to trace which detector added which page.

#### 4. No Detector Contract

Each detector has a different signature:

```python
# FileChangeDetector.check_pages
def check_pages(self, *, pages_to_check, changed_sections, all_changed, 
                pages_to_rebuild, change_summary, verbose) -> None

# DataFileDetector.check_data_files
def check_data_files(self, *, pages_to_rebuild, change_summary, verbose) -> int

# TaxonomyChangeDetector.check_taxonomy_changes
def check_taxonomy_changes(self, *, pages_to_rebuild, change_summary, verbose) -> None
```

**Problem**: Can't compose. Can't test uniformly. Can't swap implementations.

---

## Proposed Solution

### Phase 1: Canonical Path Keys (Week 1)

**Goal**: Single source of truth for all cache keys.

```python
# bengal/cache/keys.py (NEW FILE)
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
        
        content_key(Path("./content/about.md"), Path("."))
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
    """
    Canonical key for template files.
    
    Relative to templates directory.
    
    Examples:
        template_key(Path("/site/templates/base.html"), Path("/site/templates"))
        → "base.html"
    """
    try:
        rel = path.resolve().relative_to(templates_dir.resolve())
        return CacheKey(str(rel).replace("\\", "/"))
    except ValueError:
        return CacheKey(str(path.resolve()).replace("\\", "/"))


def asset_key(path: Path, assets_dir: Path) -> CacheKey:
    """
    Canonical key for asset files.
    
    Relative to assets directory.
    """
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

**Migration**: Grep for all `str(path)`, `str(file_path)`, `str(source_path)` in cache code and replace with appropriate `*_key()` function.

### Phase 2: Immutable Result Dataclasses (Week 1-2)

**Goal**: Replace mutable sets with immutable, typed results.

```python
# bengal/orchestration/incremental/results.py (NEW FILE)
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
    from bengal.cache.keys import CacheKey


class RebuildReasonCode(Enum):
    """Why a page needs rebuilding."""
    
    CONTENT_CHANGED = auto()
    DATA_FILE_CHANGED = auto()
    TEMPLATE_CHANGED = auto()
    TAXONOMY_CASCADE = auto()
    ASSET_FINGERPRINT_CHANGED = auto()
    CONFIG_CHANGED = auto()
    OUTPUT_MISSING = auto()
    FORCED = auto()


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
        >>> file_result = file_detector.detect(ctx)
        >>> data_result = data_detector.detect(ctx)
        >>> combined = file_result.merge(data_result)
    """
    
    # Pages that need rebuilding
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

### Phase 3: Detector Protocol (Week 2)

**Goal**: Uniform interface for all change detectors.

```python
# bengal/orchestration/incremental/protocol.py (NEW FILE)
"""
Change detector protocol.

All detectors implement this interface, enabling:
- Uniform testing
- Composable pipelines
- Swappable implementations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.orchestration.incremental.results import ChangeDetectionResult
    from bengal.orchestration.incremental.context import DetectionContext


@runtime_checkable
class ChangeDetector(Protocol):
    """
    Protocol for change detection components.
    
    Each detector:
    1. Receives context with cache, site, and previous results
    2. Returns immutable ChangeDetectionResult
    3. Does NOT mutate shared state
    
    Example Implementation:
        class DataFileDetector:
            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                changed_data = self._find_changed_data_files(ctx.cache)
                affected_pages = self._find_affected_pages(changed_data)
                return ChangeDetectionResult(
                    pages_to_rebuild=affected_pages,
                    data_files_changed=changed_data,
                )
    """
    
    def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
        """
        Detect changes and return result.
        
        Args:
            ctx: Detection context with cache, site, and accumulated results
            
        Returns:
            ChangeDetectionResult with detected changes
            
        Thread Safety:
            Must be thread-safe. Do not mutate ctx or shared state.
            Return new ChangeDetectionResult instances.
        """
        ...


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
    
    def with_previous(self, result: ChangeDetectionResult) -> DetectionContext:
        """Create new context with updated previous results."""
        return DetectionContext(
            cache=self.cache,
            site=self.site,
            previous=self.previous.merge(result),
            verbose=self.verbose,
            forced_changed=self.forced_changed,
        )
```

### Phase 4: Composable Pipeline (Week 2-3)

**Goal**: Explicit, ordered detector composition.

```python
# bengal/orchestration/incremental/pipeline.py (NEW FILE)
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
    from bengal.orchestration.incremental.protocol import ChangeDetector, DetectionContext
    from bengal.orchestration.incremental.results import ChangeDetectionResult

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
            ContentFileDetector(),       # Detect changed content
            DataFileDetector(),          # Detect changed data files
            TemplateDetector(),          # Detect changed templates
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
    
    def run_parallel(self, ctx: DetectionContext) -> ChangeDetectionResult:
        """
        Run independent detectors in parallel.
        
        Only safe for detectors that don't depend on each other's results.
        Use run() for detectors with cascade dependencies.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results: list[ChangeDetectionResult] = []
        
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(d.detect, ctx): type(d).__name__
                for d in self.detectors
            }
            
            for future in as_completed(futures):
                detector_name = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "detector_failed",
                        detector=detector_name,
                        error=str(e),
                    )
                    raise
        
        # Merge all results
        combined = ChangeDetectionResult.empty()
        for result in results:
            combined = combined.merge(result)
        
        return combined


# Standard pipeline configurations
def create_early_pipeline() -> DetectionPipeline:
    """Pipeline for early (pre-taxonomy) detection."""
    from bengal.orchestration.incremental.detectors import (
        ConfigChangeDetector,
        ContentFileDetector,
        DataFileDetector,
        TemplateDetector,
    )
    
    return DetectionPipeline([
        ConfigChangeDetector(),
        ContentFileDetector(),
        DataFileDetector(),
        TemplateDetector(),
    ])


def create_full_pipeline() -> DetectionPipeline:
    """Pipeline for full (post-taxonomy) detection."""
    from bengal.orchestration.incremental.detectors import (
        TaxonomyCascadeDetector,
        AutodocDetector,
    )
    
    return DetectionPipeline([
        TaxonomyCascadeDetector(),
        AutodocDetector(),
    ])
```

### Phase 5: Build Phase State Machine (Week 3)

**Goal**: Type-safe phase transitions.

```python
# bengal/orchestration/build/phases.py (NEW FILE)
"""
Build phase state machine.

Explicit phases with typed transitions prevent:
- Calling detectors in wrong order
- Skipping required phases
- Running phases multiple times
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from bengal.orchestration.incremental.results import ChangeDetectionResult

T = TypeVar("T")


class BuildPhase(Enum):
    """Build phases in order."""
    
    INIT = auto()
    DISCOVERY = auto()
    EARLY_DETECTION = auto()
    TAXONOMY = auto()
    FULL_DETECTION = auto()
    RENDER = auto()
    POSTPROCESS = auto()
    COMPLETE = auto()


@dataclass(frozen=True)
class PhaseState(Generic[T]):
    """
    Type-safe phase state.
    
    The generic parameter T represents the data available
    at this phase. Transitions produce new states with
    updated data.
    """
    
    phase: BuildPhase
    data: T
    
    def __post_init__(self) -> None:
        """Validate phase transitions."""
        # Could add validation here
        pass


# Phase-specific state types
@dataclass(frozen=True)
class InitState:
    """State after initialization."""
    cache_loaded: bool
    config_hash: str


@dataclass(frozen=True)
class DiscoveryState:
    """State after content discovery."""
    pages_discovered: int
    assets_discovered: int
    sections_discovered: int


@dataclass(frozen=True)
class EarlyDetectionState:
    """State after early change detection."""
    changes: ChangeDetectionResult


@dataclass(frozen=True)
class TaxonomyState:
    """State after taxonomy resolution."""
    tags_resolved: int
    categories_resolved: int


@dataclass(frozen=True)
class FullDetectionState:
    """State after full change detection."""
    changes: ChangeDetectionResult
    pages_to_build: int


@dataclass(frozen=True)
class RenderState:
    """State after rendering."""
    pages_rendered: int
    errors: list[str]


@dataclass(frozen=True)
class CompleteState:
    """Final build state."""
    success: bool
    stats: dict


# Type-safe transitions
def init_to_discovery(
    state: PhaseState[InitState],
    discovery_result: DiscoveryState,
) -> PhaseState[DiscoveryState]:
    """Transition from INIT to DISCOVERY."""
    assert state.phase == BuildPhase.INIT
    return PhaseState(BuildPhase.DISCOVERY, discovery_result)


def discovery_to_early_detection(
    state: PhaseState[DiscoveryState],
    changes: ChangeDetectionResult,
) -> PhaseState[EarlyDetectionState]:
    """Transition from DISCOVERY to EARLY_DETECTION."""
    assert state.phase == BuildPhase.DISCOVERY
    return PhaseState(BuildPhase.EARLY_DETECTION, EarlyDetectionState(changes))


# ... etc for other transitions
```

---

## Migration Strategy

### Week 1: Foundation

1. **Add `bengal/cache/keys.py`** with canonical key functions
2. **Add tests** for key functions (edge cases: symlinks, Windows paths)
3. **Grep and replace** `str(path)` patterns in:
   - `bengal/cache/build_cache/file_tracking.py`
   - `bengal/cache/dependency_tracker.py`
   - `bengal/orchestration/incremental/data_detector.py`

### Week 2: Results

1. **Add `bengal/orchestration/incremental/results.py`**
2. **Add `bengal/orchestration/incremental/protocol.py`**
3. **Refactor `FileChangeDetector`** to return `ChangeDetectionResult`
4. **Add adapter** to convert old results to new format (gradual migration)

### Week 3: Pipeline

1. **Add `bengal/orchestration/incremental/pipeline.py`**
2. **Refactor remaining detectors** to implement protocol
3. **Replace `ChangeDetector.detect_changes()`** with pipeline
4. **Add phase state machine** (optional, can be deferred)

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cache/test_keys.py
def test_content_key_relative():
    key = content_key(Path("/site/content/about.md"), Path("/site"))
    assert key == "content/about.md"

def test_content_key_absolute_external():
    key = content_key(Path("/external/file.md"), Path("/site"))
    assert key == "/external/file.md"

def test_data_key_prefix():
    key = data_key(Path("/site/data/team.yaml"), Path("/site"))
    assert key == "data:data/team.yaml"

def test_parse_key_with_prefix():
    prefix, path = parse_key(CacheKey("data:data/team.yaml"))
    assert prefix == "data"
    assert path == "data/team.yaml"
```

### Integration Tests

```python
# tests/integration/incremental/test_pipeline.py
def test_pipeline_accumulates_results():
    """Each detector receives previous results."""
    detector1 = MockDetector(pages={"page1.md"})
    detector2 = MockDetector(pages={"page2.md"})
    
    pipeline = DetectionPipeline([detector1, detector2])
    result = pipeline.run(ctx)
    
    assert result.pages_to_rebuild == {"page1.md", "page2.md"}

def test_pipeline_short_circuits_on_full_rebuild():
    """Full rebuild trigger stops pipeline early."""
    detector1 = MockDetector(force_full=True)
    detector2 = MockDetector(pages={"page.md"})  # Should not run
    
    pipeline = DetectionPipeline([detector1, detector2])
    result = pipeline.run(ctx)
    
    assert result.force_full_rebuild
    assert not detector2.was_called
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Performance regression from immutable copies | Medium | Low | Use `frozenset` (O(1) union), profile hot paths |
| Breaking existing tests | High | Medium | Add adapter layer, migrate incrementally |
| Protocol too restrictive | Low | Medium | Protocol is minimal, implementations can vary |
| Path edge cases (symlinks, case) | Medium | High | Comprehensive tests, `.resolve()` normalization |
| Cache format incompatibility | Low | Medium | Key format change is internal; see Migration Compatibility |

---

## Migration Compatibility

### Cache Format Backward Compatibility

**Question**: Will existing `.bengal_cache/` data work after migration?

**Answer**: Yes, with graceful degradation during transition:

1. **Phase 1 (Keys)**: New `CacheKey` format uses same string representation as most existing keys. The `content_key()` function produces identical output to current `str(path.relative_to(root))` patterns.

2. **Key Mismatches**: During migration, some lookups may miss due to format differences. This causes unnecessary rebuilds (safe) not incorrect skips (unsafe). After full migration, all lookups align.

3. **Cache Version Check**: Add optional version marker to cache metadata:

```python
# bengal/cache/build_cache/core.py
CACHE_VERSION = "2.0"  # Bump on contract migration

def load_cache(cache_path: Path) -> BuildCache:
    meta = load_cache_metadata(cache_path)
    if meta.get("version") != CACHE_VERSION:
        logger.info("cache_version_mismatch", 
                    expected=CACHE_VERSION, 
                    found=meta.get("version"),
                    action="full_rebuild_recommended")
    ...
```

4. **Escape Hatch**: If cache becomes unusable, `bengal build --clean` already clears and rebuilds.

### Test Verification

Add migration test to verify compatibility:

```python
# tests/integration/test_cache_migration.py
def test_old_cache_format_triggers_rebuild():
    """Old cache keys should cause cache miss (safe), not incorrect hit."""
    # Simulate old format: absolute path as key
    old_key = str(Path("/abs/path/content/about.md"))
    
    # New format: relative, normalized
    new_key = content_key(Path("/abs/path/content/about.md"), Path("/abs/path"))
    
    assert new_key == "content/about.md"
    assert old_key != new_key  # Mismatch → cache miss → rebuild (safe)
```

---

## Success Criteria

### Phase 1 (Week 1)
- [ ] All cache key generation uses `keys.py` functions
- [ ] Zero path format mismatches in fingerprint lookup
- [ ] Existing tests pass

### Phase 2 (Week 2)
- [ ] All detectors return `ChangeDetectionResult`
- [ ] Results are immutable (verified by `frozen=True`)
- [ ] Rebuild reasons tracked for every page

### Phase 3 (Week 3)
- [ ] All detectors implement `ChangeDetector` protocol
- [ ] Pipeline composition working
- [ ] Incremental build tests pass

---

## Alternatives Considered

### 1. Wrapper Class with Path Normalization (Viable Alternative)

**Approach**: Create a `CachePath` wrapper class that normalizes paths on construction:

```python
@dataclass(frozen=True, slots=True)
class CachePath:
    """Path wrapper that normalizes on construction."""
    _normalized: str
    
    def __init__(self, path: Path | str, root: Path):
        normalized = str(Path(path).resolve().relative_to(root.resolve()))
        object.__setattr__(self, "_normalized", normalized.replace("\\", "/"))
    
    def __str__(self) -> str:
        return self._normalized
    
    def __hash__(self) -> int:
        return hash(self._normalized)
```

**Pros**:
- Single class handles all path types
- Normalization happens automatically at construction
- Can be adopted incrementally (pass `CachePath` where `Path` accepted)

**Cons**:
- Requires `root` parameter everywhere, increasing coupling
- Doesn't distinguish content/data/template paths semantically
- Harder to debug which path type caused an issue
- Still need to update all callsites

**Why Not Chosen**: The proposed `content_key()`, `data_key()`, etc. functions provide semantic clarity about what type of path is being keyed. A generic `CachePath` loses this signal. However, this alternative could work if we decide semantic distinction isn't needed.

### 2. Fix Path Issues Incrementally

**Approach**: Just fix the immediate bugs without architectural change.

**Rejected because**: We've done this 3+ times already. Each fix introduces new edge cases. The root cause is lack of contracts, not the specific bugs.

### 3. Use Absolute Paths Everywhere

**Approach**: Always use `path.resolve()` for all keys.

**Rejected because**: 
- Cache portability (CI artifacts built on different machines)
- Verbose keys make debugging harder
- Doesn't solve the interface problem (mutable sets, different signatures)

### 4. Full Rewrite

**Approach**: Start fresh with new incremental build system.

**Rejected because**: Too risky. Existing system correctly handles 95% of cases. Contracts formalize what works; a rewrite would re-introduce bugs we've already fixed.

---

## References

- `plan/rfc-cache-invalidation-architecture.md` - Related cache coordination
- `plan/rfc-incremental-build-dependency-gaps.md` - Gaps this addresses
- `bengal/cache/build_cache/file_tracking.py` - Current fingerprint implementation
- `bengal/orchestration/incremental/` - Current detector implementations

---

## Appendix: Current Path Inconsistencies

Found via grep for `str(path)`, `str(file_path)`, etc:

| File | Line | Pattern | Issue |
|------|------|---------|-------|
| `file_tracking.py` | 131 | `str(file_path)` | No normalization |
| `file_tracking.py` | 207 | `str(file_path)` | No normalization |
| `dependency_tracker.py` | 316 | `f"data:{data_file}"` | Prefixed |
| `dependency_tracker.py` | 318 | `Path(dep_key)` | Re-wrapping string |
| `data_detector.py` | 119 | `self.cache.is_changed(data_file)` | No prefix |
| `filter_engine.py` | 756 | `self.cache.is_changed(page.source_path)` | Absolute path |
| `rebuild_filter.py` | 125 | `self.cache.is_changed(page.source_path)` | Absolute path |

Total: 15+ inconsistent patterns across 8 files.
