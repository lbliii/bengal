# Plan: Code Smell Remediation - Monolithic Modules and God Functions

**Status**: Draft  
**Created**: 2025-01-27  
**RFC**: `plan/drafted/rfc-code-smell-remediation.md`  
**Confidence**: 91% 🟢  
**Estimated Effort**: ~72 hours across 4 sprints

---

## Summary

Refactor 8+ monolithic files (>700 lines) into focused packages, eliminate 40+ god functions (>50 lines), and introduce typed dataclasses to replace primitive dictionaries. Improves maintainability, testability, and adherence to Bengal's 400-line architectural threshold.

**Current State** (refreshed 2025-01-27):
- `orchestration/incremental.py`: 1,399 lines (3.5x threshold)
- `analysis/knowledge_graph.py`: 1,222 lines (3.1x threshold)
- `autodoc/extractors/python.py`: 1,146 lines (2.9x threshold)
- `rendering/parsers/mistune.py`: 1,075 lines (2.7x threshold)
- Plus 5 more files >700 lines

**Target State**:
- No file >600 lines (soft target: 400)
- No function >100 lines (soft target: 50)
- Typed dataclasses replace dict returns
- Clear package boundaries

---

## Phase 1: Foundation (Sprint 1) — ~9 hours

**Goal**: Create foundational dataclasses and update call sites. Low risk, high value for type safety.

### 1.1 Create `BuildOptions` Dataclass

**File**: `bengal/orchestration/build/options.py` (new)  
**Effort**: 2h

**What**:
- Create `BuildOptions` dataclass to replace 11-parameter `build()` signature
- Use `field(default_factory=set)` for mutable defaults
- Add docstrings for each field

**Implementation**:
```python
from dataclasses import dataclass, field
from pathlib import Path
from bengal.config.profile import BuildProfile

@dataclass
class BuildOptions:
    """Configuration options for site builds."""
    parallel: bool = True
    incremental: bool | None = None
    verbose: bool = False
    quiet: bool = False
    profile: BuildProfile | None = None
    memory_optimized: bool = False
    strict: bool = False
    full_output: bool = False
    profile_templates: bool = False
    changed_sources: set[Path] = field(default_factory=set)
    nav_changed_sources: set[Path] = field(default_factory=set)
    structural_changed: bool = False
```

**Integration Point**:
- Import in `bengal/orchestration/build/__init__.py`
- Update `BuildOrchestrator.build()` signature to accept `options: BuildOptions | None = None`
- Maintain backward compatibility: if `options is None`, create from kwargs

**Verification**:
- [ ] All existing call sites work without changes (backward compatible)
- [ ] New call sites can use `BuildOptions` dataclass
- [ ] Type hints work correctly
- [ ] All tests pass

**Commit**: `orchestration(build): introduce BuildOptions dataclass to replace 11-parameter build() signature`

---

### 1.2 Create Navigation Dataclasses

**File**: `bengal/rendering/template_functions/navigation/models.py` (new)  
**Effort**: 3h

**What**:
- Create `BreadcrumbItem`, `PaginationItem`, `NavTreeItem` dataclasses
- Implement `__getitem__` for dict compatibility (backward compatibility)
- Add `keys()` method for dict conversion support

**Implementation**:
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class BreadcrumbItem:
    """Single breadcrumb in navigation trail."""
    title: str
    url: str
    is_current: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Support dict(item) conversion."""
        return ["title", "url", "is_current"]

@dataclass  
class PaginationItem:
    """Single page in pagination."""
    num: int | None
    url: str | None
    is_current: bool = False
    is_ellipsis: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

@dataclass
class NavTreeItem:
    """Item in navigation tree."""
    title: str
    url: str
    is_current: bool = False
    is_in_active_trail: bool = False
    is_section: bool = False
    depth: int = 0
    children: list["NavTreeItem"] = field(default_factory=list)
    has_children: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
```

**Integration Point**:
- Import in `bengal/rendering/template_functions/navigation.py`
- Update return types: `list[BreadcrumbItem]` instead of `list[dict[str, Any]]`
- Keep dict compatibility via `__getitem__` (zero template changes required)

**Verification**:
- [ ] Existing templates work without changes (dict compatibility)
- [ ] Type hints improve IDE autocompletion
- [ ] All navigation tests pass
- [ ] Can migrate templates to dot notation (`item.title`) gradually

**Commit**: `rendering(navigation): add typed dataclasses (BreadcrumbItem, PaginationItem, NavTreeItem) with dict compatibility for backward compatibility`

---

### 1.3 Update Call Sites for `BuildOptions`

**Files**:
- `bengal/orchestration/build/__init__.py`
- `bengal/cli/commands/build.py`
- `bengal/server/build_trigger.py`
- Any other call sites

**Effort**: 4h

**What**:
- Update `BuildOrchestrator.build()` to accept `BuildOptions | None`
- Convert kwargs to `BuildOptions` if `options is None` (backward compatibility)
- Update CLI command to construct `BuildOptions` from click arguments
- Update dev server to use `BuildOptions`

**Implementation**:
```python
# bengal/orchestration/build/__init__.py
def build(
    self,
    options: BuildOptions | None = None,
    # Backward compatibility kwargs
    parallel: bool = True,
    incremental: bool | None = None,
    # ... other kwargs ...
) -> BuildStats:
    """Execute full build pipeline."""
    # Convert kwargs to BuildOptions if options not provided
    if options is None:
        options = BuildOptions(
            parallel=parallel,
            incremental=incremental,
            # ... map all kwargs ...
        )

    # Use options.* throughout method
```

**Integration Points**:
- `BuildOrchestrator.build()` signature
- CLI command argument parsing
- Dev server build triggers

**Verification**:
- [ ] All existing call sites work (backward compatible)
- [ ] New call sites can use `BuildOptions` directly
- [ ] No API changes visible to users
- [ ] All tests pass

**Commit**: `orchestration(build): update build() call sites to use BuildOptions; maintain backward compatibility with kwargs`

---

**Phase 1 Exit Criteria**:
- [ ] `BuildOptions` dataclass created and tested
- [ ] Navigation dataclasses created with dict compatibility
- [ ] All call sites updated (backward compatible)
- [ ] All tests pass
- [ ] No API changes visible to users

---

## Phase 2: Incremental Package (Sprint 2) — ~18 hours

**Goal**: Convert `orchestration/incremental.py` (1,399 lines) into focused package. HIGH RISK due to critical incremental build logic.

### 2.1 Create Package Structure

**Files**:
- `bengal/orchestration/incremental/__init__.py` (new)
- `bengal/orchestration/incremental/change_detector.py` (new)
- `bengal/orchestration/incremental/cache_manager.py` (new)
- `bengal/orchestration/incremental/rebuild_filter.py` (new)
- `bengal/orchestration/incremental/cascade_tracker.py` (new)
- `bengal/orchestration/incremental/cleanup.py` (new)

**Effort**: 1h

**What**:
- Create package directory structure
- Move `IncrementalOrchestrator` to `__init__.py` (initially, will refactor)
- Set up imports and public API

**Implementation**:
```python
# bengal/orchestration/incremental/__init__.py
"""Incremental build orchestration package."""

from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator

__all__ = ["IncrementalOrchestrator"]
```

**Verification**:
- [ ] Package imports work
- [ ] Existing imports (`from bengal.orchestration.incremental import IncrementalOrchestrator`) still work
- [ ] No test failures

**Commit**: `orchestration(incremental): create package structure for incremental build logic`

---

### 2.2 Extract `ChangeDetector` Class

**File**: `bengal/orchestration/incremental/change_detector.py` (new)  
**Effort**: 4h

**What**:
- Extract unified change detection logic from `find_work_early()` and `find_work()`
- Create `ChangeDetector` class with `detect()` method
- Accept `phase` parameter: `"early"` (before taxonomy) or `"late"` (after taxonomy)

**Implementation**:
```python
from dataclasses import dataclass
from pathlib import Path
from bengal.cache.build_cache import BuildCache
from bengal.cache.dependency_tracker import DependencyTracker
from bengal.core.site import Site
from bengal.core.page import Page
from bengal.core.asset import Asset

@dataclass
class ChangeDetectionResult:
    """Result of change detection."""
    pages_to_rebuild: set[Path]
    assets_to_process: list[Asset]
    change_summary: ChangeSummary

class ChangeDetector:
    """Unified change detection for incremental builds."""

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker,
    ):
        self.site = site
        self.cache = cache
        self.tracker = tracker

    def detect(
        self,
        phase: str = "early",  # "early" or "late"
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> ChangeDetectionResult:
        """
        Detect changes requiring rebuild.

        Args:
            phase: "early" (before taxonomy) or "late" (after taxonomy)
            verbose: Collect detailed change information
            forced_changed_sources: Explicitly changed sources
            nav_changed_sources: Navigation-affected sources
        """
        # Unified logic for both phases
        # Phase-specific differences handled via conditional logic
        pass
```

**Integration Point**:
- `IncrementalOrchestrator.find_work_early()` delegates to `ChangeDetector.detect(phase="early")`
- `IncrementalOrchestrator.find_work()` delegates to `ChangeDetector.detect(phase="late")`

**Verification**:
- [ ] `ChangeDetector` extracts shared logic correctly
- [ ] Both `find_work_early()` and `find_work()` produce same results via `ChangeDetector`
- [ ] All incremental build tests pass

**Commit**: `orchestration(incremental): extract ChangeDetector class for unified change detection logic`

---

### 2.3 Merge `find_work()` and `find_work_early()` ⚠️ HIGH RISK

**File**: `bengal/orchestration/incremental/change_detector.py`  
**Effort**: 6h

**What**:
- Merge duplicate logic from `find_work_early()` (254 lines) and `find_work()` (176 lines)
- Use `phase` parameter to handle differences
- Eliminate ~200+ lines of duplication

**Risk Mitigation** (CRITICAL):

1. **Pre-requisite**: Audit test coverage
   - Location: `tests/unit/test_incremental.py`
   - Verify tests cover both pre-taxonomy and post-taxonomy phases
   - Add missing tests if needed

2. **Feature flag**: Introduce `use_unified_change_detector: bool = False`
   - Old code path (`find_work_early()` / `find_work()`) remains default
   - New code path (`ChangeDetector.detect()`) opt-in via config
   - Allows parallel validation

3. **Parallel execution**: Run both paths, compare results
   - Log discrepancies
   - 1-week validation period before switching default

4. **Rollback plan**: Git revert to last known-good if issues arise

**Implementation**:
```python
def detect(
    self,
    phase: str = "early",
    verbose: bool = False,
    forced_changed_sources: set[Path] | None = None,
    nav_changed_sources: set[Path] | None = None,
) -> ChangeDetectionResult:
    """Unified change detection."""
    # Shared logic (70% of both methods)
    pages_to_rebuild: set[Path] = set()
    assets_to_process: list[Asset] = []
    change_summary = ChangeSummary()

    # Phase-specific differences
    if phase == "early":
        # Pre-taxonomy logic (from find_work_early)
        # Skip generated pages
    else:
        # Post-taxonomy logic (from find_work)
        # Include generated pages based on affected tags

    return ChangeDetectionResult(
        pages_to_rebuild=pages_to_rebuild,
        assets_to_process=assets_to_process,
        change_summary=change_summary,
    )
```

**Integration Point**:
- `IncrementalOrchestrator.find_work_early()` → `ChangeDetector.detect(phase="early")`
- `IncrementalOrchestrator.find_work()` → `ChangeDetector.detect(phase="late")`
- Feature flag controls which path is used

**Verification**:
- [ ] Feature flag works correctly
- [ ] Old path produces identical results (regression test)
- [ ] New path produces identical results (validation)
- [ ] All incremental build tests pass
- [ ] Performance within 5% of baseline

**Commit**: `orchestration(incremental): merge find_work() and find_work_early() into unified ChangeDetector; add feature flag for safe rollout`

---

### 2.4 Extract `CascadeTracker` Class

**File**: `bengal/orchestration/incremental/cascade_tracker.py` (new)  
**Effort**: 3h

**What**:
- Extract cascade rebuild logic: `_apply_cascade_rebuilds()`, `_apply_nav_frontmatter_section_rebuilds()`, `_apply_adjacent_navigation_rebuilds()`, `_apply_shared_content_cascade()`
- Create `CascadeTracker` class to encapsulate cascade logic

**Implementation**:
```python
class CascadeTracker:
    """Tracks and applies cascade rebuilds."""

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker,
    ):
        self.site = site
        self.cache = cache
        self.tracker = tracker

    def apply_cascade_rebuilds(
        self,
        pages_to_rebuild: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """Apply section cascade rebuilds."""
        # Extract from _apply_cascade_rebuilds()
        pass

    def apply_nav_frontmatter_rebuilds(
        self,
        pages_to_rebuild: set[Path],
        all_changed: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> None:
        """Apply navigation frontmatter section rebuilds."""
        # Extract from _apply_nav_frontmatter_section_rebuilds()
        pass

    def apply_adjacent_navigation_rebuilds(
        self,
        pages_to_rebuild: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """Apply adjacent navigation rebuilds."""
        # Extract from _apply_adjacent_navigation_rebuilds()
        pass

    def apply_shared_content_cascade(
        self,
        pages_to_rebuild: set[Path],
        forced_changed: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> None:
        """Apply shared content cascade (versioned docs)."""
        # Extract from _apply_shared_content_cascade()
        pass
```

**Integration Point**:
- `ChangeDetector` uses `CascadeTracker` for cascade logic
- Methods extracted from `IncrementalOrchestrator`

**Verification**:
- [ ] Cascade logic works identically
- [ ] All cascade-related tests pass
- [ ] Code is more testable (isolated cascade logic)

**Commit**: `orchestration(incremental): extract CascadeTracker class for cascade rebuild logic`

---

### 2.5 Update Imports and Tests

**Files**:
- All files importing `IncrementalOrchestrator`
- `tests/unit/test_incremental.py`
- `tests/integration/test_incremental_*.py`

**Effort**: 4h

**What**:
- Update imports to use new package structure
- Update tests to use new classes (`ChangeDetector`, `CascadeTracker`)
- Ensure all tests pass

**Verification**:
- [ ] All imports updated
- [ ] All tests pass
- [ ] No regressions

**Commit**: `orchestration(incremental): update imports and tests for new package structure`

---

**Phase 2 Exit Criteria**:
- [ ] `IncrementalOrchestrator` < 400 lines (currently 1,399)
- [ ] `find_work()` and `find_work_early()` merged into `ChangeDetector`
- [ ] Cascade logic extracted to `CascadeTracker`
- [ ] All incremental build tests pass
- [ ] Feature flag validated (1-week parallel execution)
- [ ] Performance within 5% of baseline

---

## Phase 3: Navigation Package (Sprint 3) — ~15 hours

**Goal**: Convert `rendering/template_functions/navigation.py` (966 lines) into focused package with typed dataclasses.

### 3.1 Create Package Structure

**Files**:
- `bengal/rendering/template_functions/navigation/__init__.py` (new)
- `bengal/rendering/template_functions/navigation/breadcrumbs.py` (new)
- `bengal/rendering/template_functions/navigation/pagination.py` (new)
- `bengal/rendering/template_functions/navigation/tree.py` (new)
- `bengal/rendering/template_functions/navigation/auto_nav.py` (new)
- `bengal/rendering/template_functions/navigation/toc.py` (new)
- `bengal/rendering/template_functions/navigation/models.py` (already created in Phase 1)

**Effort**: 1h

**What**:
- Create package directory structure
- Move `register()` function to `__init__.py`
- Set up imports and public API

**Implementation**:
```python
# bengal/rendering/template_functions/navigation/__init__.py
"""Navigation template functions package."""

from bengal.rendering.template_functions.navigation.breadcrumbs import get_breadcrumbs
from bengal.rendering.template_functions.navigation.pagination import get_pagination_items
from bengal.rendering.template_functions.navigation.tree import get_nav_tree
from bengal.rendering.template_functions.navigation.auto_nav import get_auto_nav
from bengal.rendering.template_functions.navigation.toc import get_toc_grouped, combine_track_toc_items

def register(env: "JinjaEnvironment") -> None:
    """Register all navigation template functions."""
    env.globals["get_breadcrumbs"] = get_breadcrumbs
    env.globals["get_pagination_items"] = get_pagination_items
    env.globals["get_nav_tree"] = get_nav_tree
    env.globals["get_auto_nav"] = get_auto_nav
    env.globals["get_toc_grouped"] = get_toc_grouped
    env.globals["combine_track_toc_items"] = combine_track_toc_items

__all__ = ["register"]
```

**Verification**:
- [ ] Package imports work
- [ ] `register()` function works
- [ ] Existing templates still work

**Commit**: `rendering(navigation): create package structure for navigation template functions`

---

### 3.2 Split into Focused Modules

**Files**: Split `navigation.py` into:
- `breadcrumbs.py`: `get_breadcrumbs()` function
- `pagination.py`: `get_pagination_items()` function
- `tree.py`: `get_nav_tree()` function
- `auto_nav.py`: `get_auto_nav()` + `_build_section_menu_item()` helper
- `toc.py`: `get_toc_grouped()`, `combine_track_toc_items()`

**Effort**: 4h

**What**:
- Move each function to its own module
- Extract shared helpers appropriately
- Update imports

**Verification**:
- [ ] Each module < 200 lines
- [ ] All functions work identically
- [ ] All tests pass

**Commit**: `rendering(navigation): split navigation.py into focused modules (breadcrumbs, pagination, tree, auto_nav, toc)`

---

### 3.3 Migrate to Typed Dataclasses

**Files**: All navigation modules  
**Effort**: 6h

**What**:
- Update return types to use dataclasses (`BreadcrumbItem`, `PaginationItem`, `NavTreeItem`)
- Replace dict construction with dataclass instantiation
- Ensure `__getitem__` compatibility works

**Implementation**:
```python
# bengal/rendering/template_functions/navigation/breadcrumbs.py
from bengal.rendering.template_functions.navigation.models import BreadcrumbItem

def get_breadcrumbs(page: Page) -> list[BreadcrumbItem]:
    """Get breadcrumb items for a page."""
    items: list[BreadcrumbItem] = []
    # ... logic ...
    items.append(BreadcrumbItem(title=title, url=url, is_current=True))
    return items
```

**Verification**:
- [ ] Return types use dataclasses
- [ ] Dict compatibility works (`item["title"]` still works)
- [ ] Dot notation works (`item.title` works)
- [ ] All templates work without changes
- [ ] All tests pass

**Commit**: `rendering(navigation): migrate navigation functions to return typed dataclasses; maintain dict compatibility`

---

### 3.4 Update Template Usage (Optional)

**Files**: Theme templates (if migrating to dot notation)  
**Effort**: 4h (optional, can be deferred)

**What**:
- Update templates to use dot notation (`item.title` instead of `item["title"]`)
- Can be done gradually, not required for Phase 3

**Verification**:
- [ ] Templates work with dot notation
- [ ] Dict notation still works (backward compatible)

**Commit**: `themes: update navigation templates to use dot notation for dataclass access (optional migration)`

---

**Phase 3 Exit Criteria**:
- [ ] Navigation package < 200 lines per module
- [ ] All functions return typed dataclasses
- [ ] Templates still work (dict compatibility)
- [ ] All tests pass

---

## Phase 4: Parser Package (Sprint 4) — ~16 hours

**Goal**: Convert `rendering/parsers/mistune.py` (1,075 lines) into focused package.

### 4.1 Create Package Structure

**Files**:
- `bengal/rendering/parsers/mistune/__init__.py` (new)
- `bengal/rendering/parsers/mistune/highlighting.py` (new)
- `bengal/rendering/parsers/mistune/toc.py` (new)
- `bengal/rendering/parsers/mistune/cross_refs.py` (new)
- `bengal/rendering/parsers/mistune/ast.py` (new)

**Effort**: 1h

**What**:
- Create package directory structure
- Move `MistuneParser` class to `__init__.py` (initially)
- Set up imports

**Verification**:
- [ ] Package imports work
- [ ] Existing imports still work
- [ ] No test failures

**Commit**: `rendering(parsers): create mistune package structure`

---

### 4.2 Extract Highlighting Plugin

**File**: `bengal/rendering/parsers/mistune/highlighting.py` (new)  
**Effort**: 4h

**What**:
- Extract `_create_syntax_highlighting_plugin()` (175 lines) to separate module
- Create `SyntaxHighlightingPlugin` class
- Update `MistuneParser` to use extracted plugin

**Verification**:
- [ ] Highlighting works identically
- [ ] All parsing tests pass

**Commit**: `rendering(parsers): extract syntax highlighting plugin to mistune/highlighting.py`

---

### 4.3 Extract TOC Logic

**File**: `bengal/rendering/parsers/mistune/toc.py` (new)  
**Effort**: 4h

**What**:
- Extract TOC extraction and anchor injection logic
- Create `TOCExtractor` class
- Update `MistuneParser` to use extracted TOC logic

**Verification**:
- [ ] TOC extraction works identically
- [ ] Anchor injection works correctly
- [ ] All parsing tests pass

**Commit**: `rendering(parsers): extract TOC logic to mistune/toc.py`

---

### 4.4 Extract Cross-Reference Support

**File**: `bengal/rendering/parsers/mistune/cross_refs.py` (new)  
**Effort**: 3h

**What**:
- Extract cross-reference support logic
- Create `CrossReferenceHandler` class
- Update `MistuneParser` to use extracted handler

**Verification**:
- [ ] Cross-references work identically
- [ ] All parsing tests pass

**Commit**: `rendering(parsers): extract cross-reference support to mistune/cross_refs.py`

---

### 4.5 Update Tests

**Files**: `tests/unit/test_mistune*.py`, `tests/integration/test_parsing*.py`  
**Effort**: 4h

**What**:
- Update tests to use new package structure
- Ensure all tests pass

**Verification**:
- [ ] All tests pass
- [ ] No regressions

**Commit**: `rendering(parsers): update tests for mistune package structure`

---

**Phase 4 Exit Criteria**:
- [ ] `MistuneParser` < 400 lines (currently 1,075)
- [ ] Highlighting, TOC, cross-refs extracted to separate modules
- [ ] All parsing tests pass

---

## Success Criteria

### Quantitative
- [ ] No file in `bengal/` exceeds 600 lines (soft target: 400)
- [ ] No function exceeds 100 lines (soft target: 50)
- [ ] Test coverage maintained or improved
- [ ] Build performance within 5% of baseline

### Qualitative
- [ ] New developers can understand module structure faster
- [ ] Changes to one concern don't require touching unrelated code
- [ ] Type hints improve IDE experience for template function returns

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking incremental builds during refactor | Medium | High | Feature flag (`use_unified_change_detector`), parallel execution validation period, rollback plan |
| Template breakage from navigation changes | Low | Medium | Dataclasses implement `__getitem__` for dict compatibility; gradual migration path |
| Performance regression | Low | Medium | Benchmark before/after each sprint |
| Increased import complexity | Medium | Low | Clear public API in `__init__.py`, re-export key classes |
| Test coverage gaps during merge | Medium | Medium | Audit existing incremental tests before Sprint 2; require 100% coverage for ChangeDetector |

---

## Related

- **RFC**: `plan/drafted/rfc-code-smell-remediation.md`
- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc` - 400-line threshold
- **Existing Patterns**: `bengal/core/page/` - Mixin-based package structure
