# RFC: Modularize IncrementalOrchestrator

**Status**: Draft  
**Created**: 2025-12-11  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Scope**: `bengal/orchestration/incremental.py` → `bengal/orchestration/incremental/`

---

## Summary

Convert the monolithic `incremental.py` (1,190 lines) into a modular package with focused, single-responsibility modules. This improves testability, readability, and maintainability while preserving the existing public API.

---

## Problem Statement

The current `IncrementalOrchestrator` class handles too many concerns in a single file:

1. **Cache initialization and migration** (~70 lines)
2. **Configuration change detection** (~50 lines)
3. **Section-level change detection** (~60 lines)
4. **Work finding (early and legacy versions)** (~500 lines)
5. **Cascade dependency resolution** (~80 lines)
6. **Navigation dependency resolution** (~70 lines)
7. **Autodoc dependency handling** (~60 lines)
8. **Template change detection** (~40 lines)
9. **File cleanup operations** (~100 lines)
10. **Cache persistence** (~60 lines)
11. **Test bridge methods** (~100 lines)

**Symptoms**:
- `find_work_early()` is 340 lines with mixed concerns
- Difficult to test individual behaviors in isolation
- Hard to understand the full change detection flow
- Tight coupling between unrelated operations

---

## Proposed Solution

### Directory Structure

```
bengal/orchestration/incremental/
├── __init__.py              # Public API (IncrementalOrchestrator)
├── orchestrator.py          # Main orchestrator class (composition root)
├── cache_manager.py         # Cache initialization, migration, persistence
├── change_detection.py      # Section/file change detection logic
├── work_finder.py           # find_work_early(), find_work() logic
├── dependency_resolver.py   # Cascade, navigation, autodoc dependencies
└── cleanup.py               # Deleted file cleanup operations
```

### Module Responsibilities

#### `__init__.py` - Public API
```python
"""
Incremental build orchestration for Bengal SSG.

Public API:
    IncrementalOrchestrator: Main orchestrator for incremental builds
"""
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator

__all__ = ["IncrementalOrchestrator"]
```

#### `orchestrator.py` - Composition Root (~150 lines)
The main class that composes the specialized modules:

```python
class IncrementalOrchestrator:
    """Orchestrates incremental build logic for efficient rebuilds."""

    def __init__(self, site: Site):
        self.site = site
        self._cache_manager = CacheManager(site)
        self._change_detector = ChangeDetector(site)
        self._work_finder = WorkFinder(site)
        self._dependency_resolver = DependencyResolver(site)
        self._cleanup = CleanupManager(site)

    # Delegate to specialized modules
    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        return self._cache_manager.initialize(enabled)

    def find_work_early(self, ...) -> tuple[list[Page], list[Asset], ChangeSummary]:
        # Compose the modules
        changed_sections = self._change_detector.get_changed_sections()
        pages_to_rebuild = self._work_finder.find_changed_pages(changed_sections, ...)
        pages_to_rebuild = self._dependency_resolver.expand_dependencies(pages_to_rebuild)
        assets_to_process = self._work_finder.find_changed_assets()
        return pages_to_rebuild, assets_to_process, summary
```

#### `cache_manager.py` - Cache Operations (~120 lines)
```python
class CacheManager:
    """Manages cache initialization, migration, and persistence."""

    def __init__(self, site: Site):
        self.site = site
        self.cache: BuildCache | None = None
        self.tracker: DependencyTracker | None = None

    def initialize(self, enabled: bool) -> tuple[BuildCache, DependencyTracker]:
        """Initialize cache and dependency tracker."""
        ...

    def check_config_changed(self) -> bool:
        """Check if configuration changed (requires full rebuild)."""
        ...

    def save(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """Persist cache state after build."""
        ...

    def get_theme_templates_dir(self) -> Path | None:
        """Get templates directory for current theme."""
        ...
```

#### `change_detection.py` - Change Detection (~100 lines)
```python
class ChangeDetector:
    """Detects changed files and sections."""

    def __init__(self, site: Site):
        self.site = site

    def get_changed_sections(
        self,
        cache: BuildCache,
        sections: list[Section] | None = None
    ) -> set[Section]:
        """Identify sections with changed files (section-level optimization)."""
        ...

    def filter_pages_to_check(
        self,
        pages: list[Page],
        changed_sections: set[Section] | None,
        forced_paths: set[Path]
    ) -> list[Page]:
        """Filter pages to only those in changed sections."""
        ...
```

#### `work_finder.py` - Work Discovery (~200 lines)
```python
class WorkFinder:
    """Finds pages and assets that need rebuilding."""

    def __init__(self, site: Site):
        self.site = site

    def find_changed_pages(
        self,
        cache: BuildCache,
        tracker: DependencyTracker,
        pages_to_check: list[Page],
        forced_changed: set[Path],
        nav_changed: set[Path],
        verbose: bool = False
    ) -> tuple[set[Path], ChangeSummary]:
        """Find pages that need rebuilding based on file changes."""
        ...

    def find_changed_assets(
        self,
        cache: BuildCache,
        forced_changed: set[Path],
        verbose: bool = False
    ) -> list[Asset]:
        """Find assets that need processing."""
        ...

    def find_template_affected_pages(
        self,
        cache: BuildCache,
        theme_templates_dir: Path | None,
        verbose: bool = False
    ) -> tuple[set[Path], list[Path]]:
        """Find pages affected by template changes."""
        ...

    def find_autodoc_pages_to_rebuild(
        self,
        cache: BuildCache,
        verbose: bool = False
    ) -> set[str]:
        """Find autodoc pages affected by source file changes."""
        ...
```

#### `dependency_resolver.py` - Dependency Expansion (~180 lines)
```python
class DependencyResolver:
    """Resolves and expands dependencies for changed pages."""

    def __init__(self, site: Site):
        self.site = site

    def expand_cascade_dependencies(
        self,
        pages_to_rebuild: set[Path],
        verbose: bool = False
    ) -> tuple[set[Path], dict[str, list[str]]]:
        """Expand pages affected by cascade metadata changes."""
        ...

    def expand_navigation_dependencies(
        self,
        pages_to_rebuild: set[Path],
        verbose: bool = False
    ) -> tuple[set[Path], dict[str, list[str]]]:
        """Expand pages with prev/next links to modified pages."""
        ...

    def expand_section_nav_dependencies(
        self,
        cache: BuildCache,
        forced_changed: set[Path],
        nav_changed: set[Path],
        pages_to_rebuild: set[Path],
        verbose: bool = False
    ) -> tuple[set[Path], int]:
        """Expand section pages when nav-affecting frontmatter changes."""
        ...

    def _find_cascade_affected_pages(self, index_page: Page) -> set[Path]:
        """Find all pages affected by a cascade change."""
        ...
```

#### `cleanup.py` - Cleanup Operations (~100 lines)
```python
class CleanupManager:
    """Cleans up deleted source files and their outputs."""

    def __init__(self, site: Site):
        self.site = site

    def cleanup_deleted_files(self, cache: BuildCache) -> int:
        """Clean up output files for deleted source files."""
        ...

    def cleanup_deleted_autodoc_sources(self, cache: BuildCache) -> None:
        """Clean up autodoc pages when source files are deleted."""
        ...
```

---

## Migration Strategy

### Phase 1: Extract Modules (No API Changes)

1. Create `bengal/orchestration/incremental/` directory
2. Move existing code to new modules with minimal changes
3. Keep `IncrementalOrchestrator` as facade that delegates to modules
4. Old import `from bengal.orchestration.incremental import IncrementalOrchestrator` continues to work

### Phase 2: Update Tests

1. Add unit tests for individual modules
2. Existing integration tests should pass unchanged
3. Test each module in isolation

### Phase 3: Cleanup

1. Remove any dead code exposed by modularization
2. Improve docstrings for new module boundaries
3. Update architecture documentation

---

## Backward Compatibility

**Preserved**:
- `from bengal.orchestration.incremental import IncrementalOrchestrator`
- All public methods on `IncrementalOrchestrator`
- `ChangeSummary` dataclass import

**Internal only** (not breaking):
- New internal module structure
- New helper classes (`CacheManager`, `ChangeDetector`, etc.)

---

## Testing Strategy

| Module | Test Focus |
|--------|------------|
| `cache_manager.py` | Cache load/save, migration, config validation |
| `change_detection.py` | Section filtering, mtime comparison |
| `work_finder.py` | Page/asset change detection, template detection |
| `dependency_resolver.py` | Cascade/nav expansion, section nav |
| `cleanup.py` | Deleted file removal, autodoc cleanup |
| `orchestrator.py` | Integration of all modules |

---

## Alternatives Considered

### Alternative 1: Keep Single File
**Rejected**: 1,190 lines with 340-line methods is too large for maintainability.

### Alternative 2: Split Into Two Files
**Rejected**: Doesn't address the multiple distinct responsibilities.

### Alternative 3: Functional Decomposition (No Classes)
**Rejected**: Classes provide better encapsulation and state management for cache/tracker references.

---

## Implementation Checklist

- [ ] Create `bengal/orchestration/incremental/` directory
- [ ] Create `__init__.py` with public API
- [ ] Extract `CacheManager` to `cache_manager.py`
- [ ] Extract `ChangeDetector` to `change_detection.py`
- [ ] Extract `WorkFinder` to `work_finder.py`
- [ ] Extract `DependencyResolver` to `dependency_resolver.py`
- [ ] Extract `CleanupManager` to `cleanup.py`
- [ ] Create `orchestrator.py` as composition root
- [ ] Update imports in consuming modules
- [ ] Add unit tests for new modules
- [ ] Verify existing tests pass
- [ ] Update architecture documentation

---

## Success Criteria

1. ✅ All existing tests pass
2. ✅ Each module under 200 lines
3. ✅ `find_work_early` logic is readable and testable
4. ✅ New unit tests for each module
5. ✅ No breaking changes to public API
