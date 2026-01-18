# RFC: Aggressive Cleanup - Site Mixin Elimination and Detector Consolidation

**Status**: Evaluated
**Created**: 2026-01-18
**Author**: AI Assistant
**Parent RFC**: rfc-snapshot-enabled-v2-opportunities.md
**Confidence**: 100% 🟢 (Evaluated)

---

## Executive Summary

This RFC completes the architectural transformation started in the Snapshot-Enabled v2 RFC by:

1. **Eliminating all 6 Site mixins** → Inline into Site or extract to services
2. **Consolidating legacy detector classes into 1** → Replace old pipeline with `EffectBasedDetector`
3. **Removing ~2,900 lines of legacy code** → Cleaner, more maintainable codebase

**Target**: Zero mixins, zero old detectors, pure functions + immutable data.

---

## Goals

1. **Eliminate mixin complexity** — Reduce `Site.__mro__` from 8 classes to 2 (Site, object)
2. **Unify change detection** — Replace legacy detector classes with `EffectBasedDetector`
3. **Leverage existing services** — Use DataService/QueryService from Phase 3
4. **Improve testability** — Site becomes a simple dataclass; services accept explicit dependencies
5. **Delete dead code** — Remove ~2,900 lines of superseded implementation

## Non-Goals

1. **API changes** — `Site.from_config()` continues to work (via re-export)
2. **New features** — This is cleanup only, no new capabilities
3. **Performance optimization** — Focus is code reduction, not speed (though simplification may help)
4. **Service redesign** — We use existing DataService/QueryService as-is
5. **Test coverage increase** — Maintain existing coverage, don't expand scope

---

## Problem Statement

### Current State (Verified)

**Evidence**:

- `bengal/core/site/core.py:79-87` - Site inherits 6 mixins
- `bengal/build/detectors/__init__.py:7-23` - 8 detector classes exported
- `bengal/build/pipeline.py:66-100` - detector pipeline composition
- `bengal/orchestration/incremental/orchestrator.py:25-29` - pipeline used in orchestrator


The Site class uses 6 mixins with **actual** line counts:

```
┌─────────────────────────────────────────────────────────────────┐
│ Site (bengal/core/site/core.py)                                 │
├─────────────────────────────────────────────────────────────────┤
│ Inherits from:                                                  │
│   ├── SitePropertiesMixin    (800 lines) - config accessors     │
│   ├── PageCachesMixin        (204 lines) - page list caching    │
│   ├── SiteFactoriesMixin     (157 lines) - from_config()        │
│   ├── ContentDiscoveryMixin  (388 lines) - discover_content()   │
│   ├── DataLoadingMixin       (173 lines) - load data/           │
│   └── SectionRegistryMixin   (132 lines) - section lookup       │
├─────────────────────────────────────────────────────────────────┤
│ Total: 1,854 lines across 6 mixin files                         │
└─────────────────────────────────────────────────────────────────┘
```
Line counts verified in Appendix C.

The incremental build system uses 8 detector files with **actual** line counts:

```
bengal/build/detectors/
├── __init__.py                (24 lines)  - exports
├── base.py                    (53 lines)  - BaseDetector
├── autodoc.py                (137 lines)  - AutodocChangeDetector
├── cascade.py                (165 lines)  - NavigationDependencyDetector
├── content.py                 (95 lines)  - ContentChangeDetector
├── data.py                    (83 lines)  - DataChangeDetector
├── taxonomy.py               (153 lines)  - TaxonomyCascadeDetector
├── template.py               (155 lines)  - TemplateChangeDetector
└── version.py                 (86 lines)  - VersionChangeDetector
─────────────────────────────────────────────────────────────────
Total: 951 lines across 9 files (excluding __pycache__)
```
Line counts verified in Appendix C.

### Problems

1. **Mixin Complexity**: Multiple inheritance makes code hard to trace. `Site.__mro__` has 8 classes.

2. **Hidden Dependencies**: Mixins assume attributes exist on host class without explicit contracts.

3. **Testing Friction**: Can't test mixins in isolation—need full Site instance.

4. **Detector Sprawl**: 8 detector files with overlapping responsibilities. Each must understand cache format, key encoding, and detection patterns.

5. **Duplicate Logic**: Each detector reimplements hash comparison, key building, and result merging.

6. **No Unified View**: `EffectTracer` from Phase 3 provides single dependency graph, but old detectors don't use it.

### Import Dependency Analysis

Files importing from old detectors (migration scope):

```bash
# Source files (must update)
bengal/orchestration/incremental/orchestrator.py  # Uses create_early_pipeline
bengal/build/pipeline.py                          # Aggregates detectors
bengal/build/detectors/__init__.py                # Re-exports

# Detector internal imports (will be deleted)
bengal/build/detectors/template.py
bengal/build/detectors/data.py
bengal/build/detectors/autodoc.py
bengal/build/detectors/cascade.py
bengal/build/detectors/taxonomy.py
bengal/build/detectors/content.py
bengal/build/detectors/version.py

# Test files (must migrate or delete)
tests/unit/build/detectors/test_data.py
tests/unit/build/detectors/test_taxonomy.py
tests/unit/build/detectors/test_template.py
tests/unit/build/detectors/test_cascade.py
tests/unit/build/detectors/test_version.py
tests/unit/build/detectors/test_autodoc.py
tests/unit/build/detectors/test_content.py
tests/unit/build/detectors/test_base.py
```

**Total**: 19 files reference old detectors (8 tests, 8 detector internals, 3 orchestration)

---

## Design Options

### Option A: Inline + Service Extraction (Recommended)

**Approach**: 
- Inline simple mixins (properties, caches) directly into Site
- Extract complex mixins to standalone services
- Wire existing EffectBasedDetector, delete old detectors

**Pros**:
- Leverages Phase 3 services (DataService, QueryService)
- EffectBasedDetector already exists and tested
- Clear separation: Site = data, Services = operations

**Cons**:
- Site file grows larger (~1,800 lines after inlining properties)
- Must update import sites

### Option B: Full Service Extraction

**Approach**: 
- Extract ALL mixin functionality to services (including properties)
- Site becomes minimal container with only fields
- All accessors via `SiteService.get_title(site)`

**Pros**:
- Site is maximally simple (~200 lines)
- All logic in testable services

**Cons**:
- Breaking API change: `site.title` → `SiteService.get_title(site)`
- More verbose template access
- **Rejected**: Violates Non-Goal of API stability

### Option C: Composition over Inheritance

**Approach**:
- Keep mixin logic but inject as composed objects
- `Site.properties = SiteProperties(config)`
- `Site.caches = PageCaches(pages)`

**Pros**:
- Explicit dependencies
- Testable in isolation

**Cons**:
- Still multiple objects to coordinate
- Breaking API: `site.title` → `site.properties.title`
- **Rejected**: Violates Non-Goal of API stability

### Decision: Option A

Option A maintains API compatibility while achieving cleanup goals. Properties accessed as `site.title` continue to work, just implemented inline rather than via mixin.

---

## Solution

### Phase 1: Inline Site Mixins (Zero Mixins)

Mixins become either:
- **Inlined** into Site dataclass (simple properties)
- **Extracted** to service functions (complex operations)

#### 1.1 SitePropertiesMixin → Inline Properties

Properties like `title`, `baseurl`, `author` are simple config accessors. Inline them directly:

```python
# Before: Mixin with 800 lines
class SitePropertiesMixin:
    @property
    def title(self) -> str | None:
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "title", None)
        return self.config.get("site", {}).get("title") or self.config.get("title")

# After: Inline in Site (same code, no mixin)
@dataclass
class Site:
    @property
    def title(self) -> str | None:
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "title", None)
        return self.config.get("site", {}).get("title") or self.config.get("title")
```

**Files affected:**
- `bengal/core/site/core.py` - Inline all properties
- `bengal/core/site/properties.py` - Delete

#### 1.2 PageCachesMixin → Inline Cached Properties

Page caching is tightly coupled to Site's `pages` list. Inline it:

```python
@dataclass
class Site:
    # Cache fields (already in Site)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    
    @property
    def regular_pages(self) -> list[Page]:
        if self._regular_pages_cache is not None:
            return self._regular_pages_cache
        self._regular_pages_cache = [p for p in self.pages if not p.metadata.get("_generated")]
        return self._regular_pages_cache
```

**Files affected:**
- `bengal/core/site/core.py` - Inline cache properties
- `bengal/core/site/page_caches.py` - Delete

#### 1.3 SiteFactoriesMixin → Module-Level Functions

Factory methods become standalone functions:

```python
# bengal/core/site/factories.py → Keep as module with functions

def from_config(root_path: Path) -> Site:
    """Create Site from bengal.toml configuration."""
    from bengal.config import UnifiedConfigLoader
    loader = UnifiedConfigLoader()
    config = loader.load(root_path)
    return Site(root_path=root_path, config=config)

def for_testing(
    root_path: Path | None = None,
    pages: list[Page] | None = None,
    **overrides: Any,
) -> Site:
    """Create Site for unit testing with minimal setup."""
    ...
```

Usage unchanged via re-export:
```python
# Works before AND after (via __init__.py re-export)
site = Site.from_config(path)

# Also works after
from bengal.core.site import from_config
site = from_config(path)
```

**Files affected:**
- `bengal/core/site/factories.py` - Convert class methods to functions
- `bengal/core/site/core.py` - Remove mixin inheritance
- `bengal/core/site/__init__.py` - Re-export `from_config`, `for_testing` AND attach to Site class

#### 1.4 ContentDiscoveryMixin → ContentDiscoveryService

Content discovery has I/O and complex logic—extract to service:

```python
# bengal/services/content_discovery.py

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.asset import Asset

@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Result of content discovery."""
    pages: tuple[Page, ...]
    sections: tuple[Section, ...]
    assets: tuple[Asset, ...]

def discover_content(
    root_path: Path,
    content_dir: Path,
    config: dict,
) -> DiscoveryResult:
    """
    Discover pages and sections from content directory.
    
    Pure function: reads filesystem, returns immutable result.
    
    Args:
        root_path: Site root path
        content_dir: Content directory (usually root_path / "content")
        config: Site configuration dict
        
    Returns:
        DiscoveryResult with discovered pages, sections, and assets
    """
    # Implementation moved from ContentDiscoveryMixin
    ...

def discover_assets(
    root_path: Path,
    assets_dirs: list[Path],
    config: dict,
) -> tuple[Asset, ...]:
    """
    Discover assets from asset directories.
    
    Args:
        root_path: Site root path
        assets_dirs: List of asset directories to scan
        config: Site configuration dict
        
    Returns:
        Tuple of discovered Asset objects
    """
    ...
```

**Files affected:**
- `bengal/services/content_discovery.py` - New service (388 lines moved)
- `bengal/core/site/discovery.py` - Delete
- `bengal/orchestration/content.py` - Use service

#### 1.5 DataLoadingMixin → Use Existing DataService

Already extracted in Phase 3! Just remove the mixin:

```python
# Already exists: bengal/services/data.py (287 lines)
@dataclass(frozen=True, slots=True)
class DataService:
    root_path: Path
    snapshot: DataSnapshot
    
    @classmethod
    def from_root(cls, root_path: Path) -> DataService:
        """Create service by loading data from root_path/data/."""
        snapshot = load_data_directory(root_path)
        return cls(root_path=root_path, snapshot=snapshot)
```

**Files affected:**
- `bengal/core/site/data.py` - Delete (173 lines)
- `bengal/core/site/core.py` - Use `DataService.from_root()`

#### 1.6 SectionRegistryMixin → Use Existing QueryService

Already extracted in Phase 3! Just remove the mixin:

```python
# Already exists: bengal/services/query.py (269 lines)
@dataclass(frozen=True, slots=True)
class QueryService:
    snapshot: SiteSnapshot
    _sections_by_url: dict[str, SectionSnapshot]
    _sections_by_path: dict[Path, SectionSnapshot]
    
    def get_section(self, url: str) -> SectionSnapshot | None:
        """Get section by URL (O(1))."""
        return self._sections_by_url.get(url)
```

**Files affected:**
- `bengal/core/site/section_registry.py` - Delete (132 lines)
- `bengal/core/site/core.py` - Remove mixin, use `QueryService` for lookups

### Phase 2: Consolidate Detectors (1 Unified Detector)

Replace legacy detector classes with `EffectBasedDetector`.

#### 2.1 Current State

`EffectBasedDetector` exists at `bengal/orchestration/incremental/effect_detector.py` (217 lines) but is **not yet wired** into the build pipeline. The orchestrator still uses:

```python
# bengal/orchestration/incremental/orchestrator.py (current)
from bengal.build.pipeline import create_early_pipeline, create_full_pipeline
```

**Evidence**:

- `bengal/orchestration/incremental/effect_detector.py:1-46` - EffectBasedDetector exists
- `bengal/orchestration/incremental/orchestrator.py:25-29` - pipeline imports


#### 2.2 Wire EffectBasedDetector into IncrementalOrchestrator

```python
# bengal/orchestration/incremental/orchestrator.py (after)

from bengal.orchestration.incremental.effect_detector import (
    EffectBasedDetector,
    create_detector_from_build,
)

class IncrementalOrchestrator:
    def __init__(self, site: Site) -> None:
        self.site = site
        self._detector: EffectBasedDetector | None = None
    
    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        self.cache, self.tracker = self._cache_manager.initialize(enabled)
        # Create unified detector from tracer
        self._detector = create_detector_from_build(self.site)
        return self.cache, self.tracker
    
    def find_work_early(
        self,
        forced_changed_sources: set[Path] | None = None,
        **kwargs,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        if self._detector is None:
            raise BengalError("Detector not initialized")
        
        changed_pages = self._detector.detect_changes(
            forced_changed_sources or set(),
        )
        
        pages_to_build = [
            self.site.page_by_source_path.get(p)
            for p in changed_pages
            if p in self.site.page_by_source_path
        ]
        
        return pages_to_build, [], ChangeSummary(...)
```

**Files affected:**
- `bengal/orchestration/incremental/orchestrator.py` - Use EffectBasedDetector
- `bengal/build/pipeline.py` - Delete (no longer needed)

#### 2.3 Delete Old Detectors

Once `EffectBasedDetector` is wired up and tests pass:

```bash
# Files to delete (951 lines total)
bengal/build/detectors/__init__.py      # 24 lines
bengal/build/detectors/autodoc.py       # 137 lines
bengal/build/detectors/base.py          # 53 lines
bengal/build/detectors/cascade.py       # 165 lines
bengal/build/detectors/content.py       # 95 lines
bengal/build/detectors/data.py          # 83 lines
bengal/build/detectors/taxonomy.py      # 153 lines
bengal/build/detectors/template.py      # 155 lines
bengal/build/detectors/version.py       # 86 lines
bengal/build/pipeline.py                # 101 lines (aggregator)
```

Keep only:
```bash
bengal/build/
├── __init__.py
├── contracts/          # Keep - protocol definitions
│   ├── __init__.py
│   ├── keys.py
│   ├── protocol.py
│   └── results.py
├── provenance/         # Keep - effect provenance
│   └── ...
└── tracking/           # Keep - dependency tracking
    └── ...
```

---

## Migration Strategy

### Approach: Direct Replacement (No Shims)

Per project directive: "we do not want shims or wrappers and do not care about backwards compatibility. we care about clean code."

Each phase:
1. Implement new pattern
2. Update all call sites
3. Delete old code
4. Run tests
5. Commit

### Phase Order

```
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1A: Inline Simple Mixins                                      │
│   SitePropertiesMixin → inline properties (800 lines)               │
│   PageCachesMixin → inline cached properties (204 lines)            │
│   Effort: 2-3 hours                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 1B: Extract Complex Mixins                                    │
│   SiteFactoriesMixin → module functions (157 lines)                 │
│   DataLoadingMixin → delete, use DataService (173 lines)            │
│   SectionRegistryMixin → delete, use QueryService (132 lines)       │
│   ContentDiscoveryMixin → ContentDiscoveryService (388 lines)       │
│   Effort: 4-5 hours                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 2A: Wire EffectBasedDetector                                  │
│   Replace pipeline usage in IncrementalOrchestrator                 │
│   Add parity tests (see Testing Strategy)                           │
│   Effort: 4-5 hours                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 2B: Delete Legacy Detectors                                   │
│   Remove bengal/build/detectors/ (951 lines)                        │
│   Remove bengal/build/pipeline.py (101 lines)                       │
│   Migrate/delete 8 test files                                       │
│   Effort: 2-3 hours                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 3: Final Cleanup                                              │
│   Remove mixin files (1,854 lines)                                  │
│   Update __init__.py exports                                        │
│   Effort: 1 hour                                                    │
└─────────────────────────────────────────────────────────────────────┘

Total Estimated Effort: 13-17 hours
```

---

## Architecture Impact

### Core/Orchestration Separation
- `Site` currently inherits multiple mixins in `bengal/core/site/core.py`, coupling passive model data with operational behaviors (discovery, data loading).
- This RFC moves I/O-heavy behaviors into services/orchestration layers, aligning with existing service patterns.

**Evidence**:

- `bengal/core/site/core.py:79-87` - Site mixins embedded in core model
- `bengal/services/data.py:54-83` - DataService is a frozen service with explicit dependencies
- `bengal/services/query.py:26-116` - QueryService is a frozen service with explicit dependencies
- `bengal/orchestration/incremental/effect_detector.py:1-46` - EffectBasedDetector in orchestration layer


### Detector Count Clarification
- Legacy incremental detection currently exposes 8 detector classes via `bengal/build/detectors/__init__.py`.
- `EffectBasedDetector` docstring references “13 detector classes,” likely referring to a broader legacy set; reconcile terminology during implementation.

**Evidence**:

- `bengal/build/detectors/__init__.py:7-23` - 8 detector classes exported
- `bengal/orchestration/incremental/effect_detector.py:1-12` - docstring mentions 13 detector classes


---

## Success Criteria

### Quantitative

| Metric | Before | After |
|--------|--------|-------|
| Site mixins | 6 | 0 |
| Site.__mro__ depth | 8 classes | 2 classes |
| Detector classes (legacy) | 8 | 0 (use EffectBasedDetector) |
| Lines in bengal/build/detectors/ | 951 | 0 |
| Lines in bengal/core/site/*.py | 1,854 | ~1,600 (inline in core.py) |
| Total lines deleted | - | ~2,900 |

### Qualitative

- [ ] `Site` is a simple dataclass with inline properties
- [ ] All factory methods are module-level functions (re-exported on Site)
- [ ] `IncrementalOrchestrator` uses `EffectBasedDetector` exclusively
- [ ] No imports from `bengal.build.detectors.*` anywhere
- [ ] All tests pass
- [ ] `Site.from_config()` continues to work (API compatibility)

---

## Testing Strategy

### Detector Parity Tests (Phase 2A - CRITICAL)

Before deleting old detectors, verify `EffectBasedDetector` produces equivalent results:

```python
# tests/unit/orchestration/incremental/test_effect_detector_parity.py

import pytest
from bengal.build.pipeline import create_early_pipeline
from bengal.orchestration.incremental.effect_detector import (
    EffectBasedDetector,
    create_detector_from_build,
)

class TestEffectDetectorParity:
    """Verify EffectBasedDetector matches old detector behavior."""
    
    @pytest.fixture
    def site_with_changes(self, tmp_path):
        """Create site with known changes for testing."""
        ...
    
    def test_content_change_detection_parity(self, site_with_changes):
        """Content changes detected same as old ContentChangeDetector."""
        # Old pipeline
        old_pipeline = create_early_pipeline(site_with_changes)
        old_result = old_pipeline.detect(changed_paths)
        
        # New detector
        new_detector = create_detector_from_build(site_with_changes)
        new_result = new_detector.detect_changes(changed_paths)
        
        assert new_result == old_result.pages_to_rebuild
    
    def test_template_change_detection_parity(self, site_with_changes):
        """Template changes cascade correctly."""
        ...
    
    def test_taxonomy_cascade_parity(self, site_with_changes):
        """Taxonomy changes invalidate tag pages."""
        ...
    
    def test_data_file_detection_parity(self, site_with_changes):
        """Data file changes detected."""
        ...
```

### Test Migration Strategy

| Old Test File | Action | New Location |
|---------------|--------|--------------|
| `test_base.py` | Delete | N/A (base class removed) |
| `test_content.py` | Migrate | `test_effect_detector_parity.py` |
| `test_template.py` | Migrate | `test_effect_detector_parity.py` |
| `test_cascade.py` | Migrate | `test_effect_detector_parity.py` |
| `test_taxonomy.py` | Migrate | `test_effect_detector_parity.py` |
| `test_data.py` | Migrate | `test_effect_detector_parity.py` |
| `test_version.py` | Migrate | `test_effect_detector_parity.py` |
| `test_autodoc.py` | Migrate | `test_effect_detector_parity.py` |

### Unit Tests

- Test inlined properties still work
- Test factory functions create valid Site
- Test ContentDiscoveryService matches old discovery behavior

### Integration Tests

- Full build with new Site structure
- Incremental build with EffectBasedDetector
- Dev server with new detection system

### Regression Tests

- Run existing test suite (should all pass)
- Manual smoke test of bengal CLI commands

---

## Risks and Mitigations

### Risk 1: Breaking Call Sites

**Likelihood**: Medium  
**Impact**: High

**Mitigation**: Grep-driven migration. Search for all usages before deletion:

```bash
# Find all mixin method usages
rg "site\.discover_content|site\.discover_assets" --type py
rg "Site\.from_config|Site\.for_testing" --type py
rg "site\.get_section_by_path|site\.get_section_by_url" --type py

# Find all detector imports (19 files identified)
rg "from bengal\.build\.detectors" --type py
```

### Risk 2: EffectBasedDetector Missing Edge Cases

**Likelihood**: Medium  
**Impact**: High (incorrect incremental builds)

**Mitigation**: 
1. Parity tests before migration (see Testing Strategy)
2. Run full test suite with both old and new detectors
3. Shadow mode: run both in parallel, compare results

### Risk 3: Test Failures

**Likelihood**: Low  
**Impact**: Medium

**Mitigation**: Run full test suite after each file deletion:

```bash
# After each phase
uv run pytest tests/ -x --tb=short
```

### Risk 4: Performance Regression

**Likelihood**: Low  
**Impact**: Medium

**Mitigation**: Benchmark critical paths before/after:

```bash
# Before cleanup
hyperfine 'bengal build --incremental' --warmup 2

# After each phase, compare
hyperfine 'bengal build --incremental' --warmup 2
```

---

## Rollout Plan

1. **Merge Phase 1A** - Inline simple mixins (low risk)
2. **Merge Phase 1B** - Extract complex mixins (medium risk)
3. **Merge Phase 2A** - Wire EffectBasedDetector with parity tests (medium risk)
4. **Merge Phase 2B** - Delete old detectors (low risk - tests prove parity)
5. **Merge Phase 3** - Delete mixin files (low risk - just cleanup)

Each merge is atomic and independently testable.

---

## Appendix A: Files to Delete

```
# Mixin files (after inlining/extraction)
bengal/core/site/properties.py          (800 lines)
bengal/core/site/page_caches.py         (204 lines)
bengal/core/site/factories.py           (157 lines) - class removed, functions kept
bengal/core/site/discovery.py           (388 lines)
bengal/core/site/data.py                (173 lines)
bengal/core/site/section_registry.py    (132 lines)
─────────────────────────────────────────────────────
Subtotal: 1,854 lines

# Detector files (after EffectBasedDetector wired)
bengal/build/detectors/__init__.py      (24 lines)
bengal/build/detectors/autodoc.py       (137 lines)
bengal/build/detectors/base.py          (53 lines)
bengal/build/detectors/cascade.py       (165 lines)
bengal/build/detectors/content.py       (95 lines)
bengal/build/detectors/data.py          (83 lines)
bengal/build/detectors/taxonomy.py      (153 lines)
bengal/build/detectors/template.py      (155 lines)
bengal/build/detectors/version.py       (86 lines)
bengal/build/pipeline.py                (101 lines)
─────────────────────────────────────────────────────
Subtotal: 1,052 lines

Total: 2,906 lines deleted
```

## Appendix B: Test Files to Migrate

```
tests/unit/build/detectors/
├── test_base.py       → Delete (base class removed)
├── test_content.py    → Migrate to test_effect_detector_parity.py
├── test_template.py   → Migrate to test_effect_detector_parity.py
├── test_cascade.py    → Migrate to test_effect_detector_parity.py
├── test_taxonomy.py   → Migrate to test_effect_detector_parity.py
├── test_data.py       → Migrate to test_effect_detector_parity.py
├── test_version.py    → Migrate to test_effect_detector_parity.py
└── test_autodoc.py    → Migrate to test_effect_detector_parity.py
```

---

## Appendix C: Line Count Verification

Line counts verified via `wc -l` on 2026-01-18:

```bash
wc -l \
  bengal/core/site/properties.py \
  bengal/core/site/page_caches.py \
  bengal/core/site/factories.py \
  bengal/core/site/discovery.py \
  bengal/core/site/data.py \
  bengal/core/site/section_registry.py \
  bengal/build/detectors/__init__.py \
  bengal/build/detectors/base.py \
  bengal/build/detectors/autodoc.py \
  bengal/build/detectors/cascade.py \
  bengal/build/detectors/content.py \
  bengal/build/detectors/data.py \
  bengal/build/detectors/taxonomy.py \
  bengal/build/detectors/template.py \
  bengal/build/detectors/version.py \
  bengal/build/pipeline.py
```

Output:

```text
     800 bengal/core/site/properties.py
     204 bengal/core/site/page_caches.py
     157 bengal/core/site/factories.py
     388 bengal/core/site/discovery.py
     173 bengal/core/site/data.py
     132 bengal/core/site/section_registry.py
      24 bengal/build/detectors/__init__.py
      53 bengal/build/detectors/base.py
     137 bengal/build/detectors/autodoc.py
     165 bengal/build/detectors/cascade.py
      95 bengal/build/detectors/content.py
      83 bengal/build/detectors/data.py
     153 bengal/build/detectors/taxonomy.py
     155 bengal/build/detectors/template.py
      86 bengal/build/detectors/version.py
     101 bengal/build/pipeline.py
    2906 total
```

---

## Related Documents

- `plan/rfc-snapshot-enabled-v2-opportunities.md` - Parent RFC
- `bengal/effects/effect.py` - Effect dataclass
- `bengal/effects/tracer.py` - EffectTracer
- `bengal/orchestration/incremental/effect_detector.py` - EffectBasedDetector
- `bengal/services/` - Extracted services (ThemeService, QueryService, DataService)
