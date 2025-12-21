# Plan: Architecture Refactoring - Package Consolidation and Code Smell Remediation

**Status**: Ready  
**RFC**: `plan/evaluated/rfc-architecture-refactoring.md`  
**Created**: 2025-12-20  
**Estimated Effort**: 10 weeks (6 sprints)  
**Subsystem**: Core, Rendering, Orchestration, Utils, CLI, Health, Autodoc

---

## Executive Summary

Comprehensive architecture refactoring addressing **package-level structural issues** (oversized packages, grab-bag utils, overlapping validation) and **file-level code smells** (8+ monolithic files >700 lines, 40+ god functions). Strategy: package consolidation first, then file-level refactoring.

**Key Files**:
- `rendering/` → Extract directives (107 → ~70 files)
- `utils/` → Relocate domain code (46 → ~35 files)
- `incremental.py` → Package (1,399 lines → <400 per module)
- `navigation.py` → Package (966 lines → <200 per module)

---

## Sprint 1: Package Consolidation Foundation (Week 1-2)

### Phase 1.0: Baseline & Tooling (New)

**Goal**: Establish performance baseline and dependency visualization.

#### Task 1.0.1: Capture Performance Baseline
**Action**: Run full benchmark suite and archive results.
```bash
python scripts/benchmark.py --output benchmarks/baseline_sprint0.json
```
**Commit**: `benchmarks: capture pre-refactoring baseline`

#### Task 1.0.2: Generate Dependency Graph
**Action**: Use `pydeps` to visualize current state of `rendering/` and `utils/`.
```bash
pydeps bengal/rendering --max-depth 2 -o benchmarks/rendering_pre.svg
pydeps bengal/utils --max-depth 2 -o benchmarks/utils_pre.svg
```
**Commit**: `benchmarks: generate pre-refactoring dependency graphs`

---

### Phase 1.1: Create Directives Package Structure

**Goal**: Extract 39 directive files from `rendering/plugins/directives/` to `bengal/directives/`.

#### Task 1.1.1: Create Package Skeleton

**Files**:
- `bengal/directives/__init__.py` (new)
- `bengal/directives/registry.py` (new)
- `bengal/directives/base.py` (new)

```python
# bengal/directives/__init__.py
"""
Directive system for Bengal templates.

Implements lazy-loading to prevent performance regression.
"""
from bengal.directives.registry import get_directive, register_all

__all__ = ['get_directive', 'register_all']
```

```python
# bengal/directives/registry.py
"""Lazy-loading directive registry."""
from __future__ import annotations
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.directives.base import BaseDirective

_DIRECTIVE_MAP: dict[str, str] = {
    "admonition": "bengal.directives.admonitions",
    "cards": "bengal.directives.cards",
    "tabs": "bengal.directives.tabs",
    "code-block": "bengal.directives.code_blocks",
    "dropdown": "bengal.directives.dropdowns",
    "grid": "bengal.directives.grids",
    "image": "bengal.directives.image",
    "toc": "bengal.directives.toc",
    "youtube": "bengal.directives.youtube",
    # ... add remaining directives
}

_loaded_directives: dict[str, type[BaseDirective]] = {}

def get_directive(name: str) -> type[BaseDirective] | None:
    """Get directive class by name, loading lazily."""
    if name in _loaded_directives:
        return _loaded_directives[name]

    module_path = _DIRECTIVE_MAP.get(name)
    if not module_path:
        return None

    module = importlib.import_module(module_path)
    directive_class = getattr(module, 'directive_class', None)
    if directive_class:
        _loaded_directives[name] = directive_class
    return directive_class

def register_all() -> None:
    """Pre-load all directives (for testing/inspection)."""
    for name in _DIRECTIVE_MAP:
        get_directive(name)
```

**Commit**: `directives: create package skeleton with lazy-loading registry`

---

#### Task 1.1.2: Move Base Directive Classes

**Source**: `bengal/rendering/plugins/directives/base.py` (or equivalent)  
**Target**: `bengal/directives/base.py`

**Action**: Move base classes, update imports.

**Commit**: `directives: move BaseDirective and related base classes`

---

#### Task 1.1.3: Move Simple Directive Files (batch 1)

**Files to move** (alphabetical, first batch):
- `admonitions.py`
- `code_blocks.py`
- `diagrams.py`
- `dropdowns.py`

**Pattern** (repeat for each):
1. Copy to `bengal/directives/`
2. Update internal imports
3. Add re-export in old location with deprecation warning

**Commit**: `directives: move admonitions, code_blocks, diagrams, dropdowns`

---

#### Task 1.1.4: Move Simple Directive Files (batch 2)

**Files to move**:
- `grids.py`
- `image.py`
- `tabs.py`
- `toc.py`
- `youtube.py`

**Commit**: `directives: move grids, image, tabs, toc, youtube`

---

#### Task 1.1.5: Move Remaining Directive Files (batch 3)

**Files to move**: All remaining files except `cards.py` (~20 files)

**Commit**: `directives: move remaining directive implementations`

---

#### Task 1.1.6: Break Up cards.py into Package (1,027 lines)

**Source**: `bengal/rendering/plugins/directives/cards.py`  
**Target**: `bengal/directives/cards/`

**Proposed Structure**:
```
bengal/directives/cards/
├── __init__.py      # Public API, re-exports
├── simple.py        # SimpleCard directive
├── linked.py        # LinkedCard directive
├── grid.py          # CardGrid directive
└── utils.py         # Shared card utilities
```

**Steps**:
1. Analyze `cards.py` to identify logical splits
2. Create package structure
3. Move code to appropriate modules
4. Ensure each module < 300 lines
5. Update imports

**Commit**: `directives(cards): convert 1,027-line module to package with focused modules`

---

#### Task 1.1.7: Update Rendering Plugins to Use New Package

**File**: `bengal/rendering/plugins/__init__.py`

**Changes**:
- Import directives from `bengal.directives` instead of local
- Add deprecation warnings for old import paths

**Commit**: `rendering: update plugins to import from bengal.directives`

---

#### Task 1.1.8: Add Deprecation Redirects

**Files**: `bengal/rendering/plugins/directives/*.py` (old locations)

**Pattern**:
```python
# bengal/rendering/plugins/directives/admonitions.py
import warnings
warnings.warn(
    "Import from bengal.directives.admonitions instead",
    DeprecationWarning,
    stacklevel=2
)
from bengal.directives.admonitions import *
```

**Commit**: `rendering: add deprecation warnings for old directive imports`

---

### Phase 1.2: Relocate Small/Medium Domain Utils

#### Task 1.2.1: Create core/theme Package

**Files**:
- `bengal/core/theme/__init__.py` (new)
- `bengal/core/theme/registry.py` (new, from utils)
- `bengal/core/theme/resolution.py` (new, from utils)

**Source Files**:
- `utils/theme_registry.py` (298 lines)
- `utils/theme_resolution.py` (165 lines)

**Commit**: `core(theme): create package; relocate theme_registry and theme_resolution from utils`

---

#### Task 1.2.2: Relocate Build-Related Utils to Orchestration

**Files to move**:
- `utils/build_badge.py` (119 lines) → `orchestration/badge.py`
- `utils/incremental_constants.py` (55 lines) → `orchestration/constants.py`

**Commit**: `orchestration: relocate build_badge and incremental_constants from utils`

---

#### Task 1.2.3: Relocate page_initializer to Discovery

**Source**: `utils/page_initializer.py` (138 lines)  
**Target**: `discovery/page_factory.py`

**Commit**: `discovery: relocate page_initializer as page_factory from utils`

---

#### Task 1.2.4: Merge sections.py into core/section.py

**Source**: `utils/sections.py` (67 lines)  
**Target**: `core/section.py`

**Action**: Merge utility functions into Section class or as module-level helpers.

**Commit**: `core(section): merge utils/sections.py into section module`

---

#### Task 1.2.5: Add Deprecation Warnings to Relocated Utils

**Files**: All relocated files in `utils/`

**Commit**: `utils: add deprecation warnings for relocated domain modules`

---

#### Task 1.2.6: Update Imports Across Codebase

**Action**: Find and replace all imports of relocated modules.

```bash
# Find all imports to update
grep -r "from bengal.utils.theme_" bengal/
grep -r "from bengal.utils.build_badge" bengal/
grep -r "from bengal.utils.incremental_constants" bengal/
grep -r "from bengal.utils.page_initializer" bengal/
grep -r "from bengal.utils.sections" bengal/
```

**Commit**: `refactor: update imports for relocated utils modules`

---

### Sprint 1 Tests

#### Task 1.T.1: Update Directive Tests

**Files**: `tests/unit/rendering/test_directives*.py` → `tests/unit/directives/`

**Commit**: `tests: update directive tests for new package location`

---

#### Task 1.T.2: Add Lazy Registry Tests

**File**: `tests/unit/directives/test_registry.py` (new)

**Commit**: `tests: add unit tests for directive lazy-loading registry`

---

#### Task 1.T.3: Update Utils Tests

**Files**: Move/update tests for relocated modules.

**Commit**: `tests: update tests for relocated utils modules`

---

### Sprint 1 Exit Criteria

- [ ] `rendering/` file count < 70 (from 107)
- [ ] `bengal/directives/` package created with lazy-loading
- [ ] `cards.py` broken into package with modules < 300 lines each
- [ ] `utils/` theme files relocated to `core/theme/`
- [ ] `utils/` build files relocated to `orchestration/`
- [ ] All deprecation warnings in place
- [ ] All tests pass
- [ ] **Performance within 2% of baseline** (Task 1.0.1)
- [ ] **Dependency graph updated** and verified for no new cycles

---

## Sprint 2: Large Utils Extraction & Foundation Dataclasses (Week 3-4)

### Phase 2.1: Extract Large Utils to Packages

#### Task 2.1.1: Circular Dependency Audit for CLI Output

**Action**: Before moving `cli_output.py`, audit all imports to prevent circular dependencies.

```bash
# Check what imports cli_output
grep -r "from bengal.utils.cli_output" bengal/
grep -r "from bengal.utils import.*cli_output" bengal/

# Check what cli_output imports
head -50 bengal/utils/cli_output.py
```

**Output**: Document dependency graph, identify any cycles.

**Commit**: N/A (audit only)

---

#### Task 2.1.2: Convert cli_output.py to cli/output Package

**Source**: `utils/cli_output.py` (838 lines)  
**Target**: `cli/output/`

**Proposed Structure**:
```
bengal/cli/output/
├── __init__.py      # CLIOutput class, public API
├── formatter.py     # Output formatting logic
├── progress.py      # Progress indicators
├── stats.py         # Build stats display
└── colors.py        # Color/ANSI utilities
```

**Steps**:
1. Create package structure
2. Split by logical concern
3. Ensure each module < 250 lines
4. Update all imports

**Commit**: `cli(output): convert 838-line utils module to focused package`

---

#### Task 2.1.3: Convert build_stats.py to orchestration/stats Package

**Source**: `utils/build_stats.py` (613 lines)  
**Target**: `orchestration/stats/`

**Proposed Structure**:
```
bengal/orchestration/stats/
├── __init__.py      # BuildStats class, public API
├── collector.py     # Stats collection logic
├── reporter.py      # Stats reporting/display
└── serializer.py    # Stats serialization (JSON, etc.)
```

**Commit**: `orchestration(stats): convert 613-line utils module to focused package`

---

#### Task 2.1.4: Relocate live_progress.py to CLI

**Source**: `utils/live_progress.py` (555 lines)  
**Target**: `cli/progress.py`

**Note**: 555 lines is borderline for splitting. Relocate first, consider split later if needed.

**Commit**: `cli: relocate live_progress from utils`

---

#### Task 2.1.5: Relocate build_summary.py to Orchestration

**Source**: `utils/build_summary.py` (433 lines)  
**Target**: `orchestration/summary.py`

**Note**: 433 lines exceeds 400-line threshold. Consider split if natural boundaries exist.

**Commit**: `orchestration: relocate build_summary from utils`

---

### Phase 2.2: Foundation Dataclasses

#### Task 2.2.1: Create BuildOptions Dataclass

**File**: `bengal/orchestration/build/options.py` (new)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.build.profile import BuildProfile

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

**Commit**: `orchestration(build): add BuildOptions dataclass to replace 11-parameter signature`

---

#### Task 2.2.2: Update BuildOrchestrator.build() Signature

**File**: `bengal/orchestration/build/__init__.py`

**Before**:
```python
def build(
    self,
    parallel: bool = True,
    incremental: bool | None = None,
    verbose: bool = False,
    # ... 11 parameters
) -> BuildStats:
```

**After**:
```python
def build(self, options: BuildOptions | None = None) -> BuildStats:
    if options is None:
        options = BuildOptions()
    # ... use options.parallel, options.incremental, etc.
```

**Commit**: `orchestration(build): adopt BuildOptions dataclass in build() method`

---

#### Task 2.2.3: Update All build() Call Sites

**Action**: Find and update all callers of `BuildOrchestrator.build()`.

```bash
grep -r "\.build(" bengal/ --include="*.py" | grep -v test
```

**Commit**: `refactor: update all build() call sites to use BuildOptions`

---

#### Task 2.2.4: Create Navigation Dataclasses

**File**: `bengal/rendering/template_functions/navigation/models.py` (new)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class BreadcrumbItem:
    """Single breadcrumb in navigation trail."""
    title: str
    url: str
    is_current: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        return ["title", "url", "is_current"]

@dataclass(slots=True)
class PaginationItem:
    """Single page in pagination."""
    num: int | None
    url: str | None
    is_current: bool = False
    is_ellipsis: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

@dataclass(slots=True)
class NavTreeItem:
    """Item in navigation tree."""
    title: str
    url: str
    is_current: bool = False
    is_in_active_trail: bool = False
    is_section: bool = False
    depth: int = 0
    children: list[NavTreeItem] = field(default_factory=list)
    has_children: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
```

**Commit**: `rendering(navigation): add typed dataclasses with dict-style compatibility`

---

### Sprint 2 Tests

#### Task 2.T.1: Tests for CLI Output Package

**File**: `tests/unit/cli/test_output.py`

**Commit**: `tests: add unit tests for cli/output package`

---

#### Task 2.T.2: Tests for BuildOptions

**File**: `tests/unit/orchestration/test_build_options.py`

**Commit**: `tests: add unit tests for BuildOptions dataclass`

---

#### Task 2.T.3: Tests for Navigation Dataclasses

**File**: `tests/unit/rendering/test_navigation_models.py`

**Commit**: `tests: add unit tests for navigation dataclasses`

---

### Sprint 2 Exit Criteria

- [ ] `utils/` file count < 35 (from 46)
- [ ] `cli_output.py` converted to `cli/output/` package
- [ ] `build_stats.py` converted to `orchestration/stats/` package
- [ ] `BuildOptions` dataclass created and adopted
- [ ] Navigation dataclasses created with `__slots__`
- [ ] All tests pass

---

## Sprint 3: Validation Consolidation (Week 5)

### Phase 3.1: Audit Validation Overlap

#### Task 3.1.1: Document Validation Overlap

**Action**: Compare health/ and rendering/ validators.

**Files to analyze**:
- `health/validators/links.py`
- `health/validators/rendering.py`
- `rendering/link_validator.py`
- `rendering/validator.py`

**Output**: Document overlap, identify canonical versions.

**Commit**: N/A (audit only)

---

### Phase 3.2: Merge Validators

#### Task 3.2.1: Merge Link Validation

**Action**: Consolidate link validation into `health/validators/links.py`.

**Steps**:
1. Identify unique logic in `rendering/link_validator.py`
2. Merge into `health/validators/links.py`
3. Update `rendering/` to import from `health/`

**Commit**: `health(validators): consolidate link validation from rendering`

---

#### Task 3.2.2: Merge Template Validation

**Action**: Consolidate template validation into `health/validators/templates.py`.

**Steps**:
1. Identify unique logic in `rendering/validator.py`
2. Merge into `health/validators/templates.py`
3. Update `rendering/` to import from `health/`

**Commit**: `health(validators): consolidate template validation from rendering`

---

#### Task 3.2.3: Update Rendering Pipeline

**File**: `bengal/rendering/pipeline/core.py`

**Change**: Delegate to health validators instead of duplicated logic.

```python
from bengal.health.validators import validate_links, validate_templates

def _validate_output(self, page: Page) -> list[ValidationError]:
    return validate_links(page) + validate_templates(page)
```

**Commit**: `rendering(pipeline): delegate validation to health validators`

---

#### Task 3.2.4: Remove Duplicated Validators

**Files to remove** (after updating all references):
- `rendering/link_validator.py`
- `rendering/validator.py`

**Commit**: `rendering: remove duplicated validator modules; use health validators`

---

### Sprint 3 Exit Criteria

- [ ] Single source of truth for link validation
- [ ] Single source of truth for template validation
- [ ] `rendering/` delegates to `health/` for validation
- [ ] No duplicate validation logic
- [ ] All tests pass

---

## Sprint 4: Incremental Package Refactoring (Week 6-7) ⚠️ HIGH RISK

### Phase 4.1: Preparation

#### Task 4.1.1: Audit Incremental Test Coverage

**Action**: Ensure comprehensive test coverage before refactoring.

```bash
pytest tests/unit/test_incremental*.py -v --cov=bengal.orchestration.incremental
```

**Output**: Coverage report, identify gaps.

**Commit**: N/A (audit only)

---

#### Task 4.1.2: Add Missing Incremental Tests

**Files**: `tests/unit/orchestration/test_incremental_*.py`

**Focus**: Cover `find_work_early()` and `find_work()` edge cases.

**Commit**: `tests: add comprehensive incremental build tests before refactoring`

---

### Phase 4.2: Package Structure

#### Task 4.2.1: Create Incremental Package Skeleton

**Files**:
```
bengal/orchestration/incremental/
├── __init__.py              # Public API (IncrementalOrchestrator)
├── change_detector.py       # Unified change detection
├── cache_manager.py         # Cache initialization and persistence
├── rebuild_filter.py        # Pages/assets filtering
├── cascade_tracker.py       # Cascade dependencies
└── cleanup.py               # Deleted file cleanup
```

**Commit**: `orchestration(incremental): create package skeleton`

---

#### Task 4.2.2: Extract CacheManager

**Source**: Cache-related methods from `incremental.py`  
**Target**: `incremental/cache_manager.py`

**Commit**: `orchestration(incremental): extract CacheManager class`

---

#### Task 4.2.3: Extract RebuildFilter

**Source**: Page/asset filtering methods from `incremental.py`  
**Target**: `incremental/rebuild_filter.py`

**Commit**: `orchestration(incremental): extract RebuildFilter class`

---

#### Task 4.2.4: Extract CascadeTracker

**Source**: `_apply_cascade_rebuilds()`, `_apply_nav_frontmatter_section_rebuilds()`, etc.  
**Target**: `incremental/cascade_tracker.py`

**Commit**: `orchestration(incremental): extract CascadeTracker class`

---

#### Task 4.2.5: Extract Cleanup Module

**Source**: Deleted file cleanup logic  
**Target**: `incremental/cleanup.py`

**Commit**: `orchestration(incremental): extract cleanup module`

---

### Phase 4.3: Merge find_work Methods ⚠️ CRITICAL

#### Task 4.3.0: Cache Version Bump (New)
**Action**: Increment `CACHE_VERSION` in `bengal/cache/constants.py` to ensure clean slate for refactored incremental logic.
**Commit**: `cache: bump version for incremental refactor`

#### Task 4.3.1: Implement ChangeDetector with Phase Parameter

**Target**: `incremental/change_detector.py`

**Design**:
```python
class ChangeDetector:
    """Unified change detection for incremental builds."""

    def detect_changes(
        self,
        phase: Literal["early", "full"],
        ...
    ) -> ChangeSet:
        """
        Detect changes requiring rebuilds.

        Args:
            phase: "early" (before taxonomy) or "full" (after taxonomy)
        """
        # Shared logic here
        if phase == "early":
            # Early-specific logic
        else:
            # Full-specific logic
```

**Commit**: `orchestration(incremental): implement unified ChangeDetector with phase parameter`

---

#### Task 4.3.2: Implement Shadow Execution Mode

**File**: `incremental/__init__.py`

**Design**: Run both old and new logic, compare results.

```python
class IncrementalOrchestrator:
    def find_work(self, ...):
        if self.config.use_unified_change_detector:
            new_result = self._change_detector.detect_changes("full", ...)
            if self.config.shadow_mode:
                old_result = self._legacy_find_work(...)
                self._compare_results(old_result, new_result)
            return new_result
        return self._legacy_find_work(...)
```

**Commit**: `orchestration(incremental): add shadow execution mode for validation`

---

#### Task 4.3.3: Add Feature Flag Configuration

**File**: `bengal/config/build.py` (or appropriate config)

```python
use_unified_change_detector: bool = False
shadow_mode: bool = False  # Run both paths and compare
```

**Commit**: `config: add feature flags for unified change detector`

---

### Phase 4.4: Validation Period

#### Task 4.4.1: Run Shadow Mode in CI

**Action**: Enable shadow mode in CI, monitor for discrepancies.

**Duration**: 1 week minimum.

**Commit**: N/A (CI configuration)

---

#### Task 4.4.2: Enable New Detector by Default

**After validation period**: Set `use_unified_change_detector: True`.

**Commit**: `orchestration(incremental): enable unified change detector by default`

---

#### Task 4.4.3: Remove Legacy Code

**After stable period**: Remove `_legacy_find_work()` and shadow mode.

**Commit**: `orchestration(incremental): remove legacy find_work implementations`

---

### Sprint 4 Exit Criteria

- [ ] `IncrementalOrchestrator` < 400 lines
- [ ] `find_work()` and `find_work_early()` merged into `ChangeDetector`
- [ ] Shadow mode validation completed (1+ week)
- [ ] Feature flag enabled by default
- [ ] All incremental build tests pass
- [ ] No regressions in dev server or CI builds

---

## Sprint 5: Navigation & Parser Packages (Week 8-9)

### Phase 5.1: Navigation Package

#### Task 5.1.1: Create Navigation Package Structure

**Source**: `rendering/template_functions/navigation.py` (966 lines)  
**Target**: `rendering/template_functions/navigation/`

```
bengal/rendering/template_functions/navigation/
├── __init__.py      # register() function, re-exports
├── models.py        # Dataclasses (already created in Sprint 2)
├── breadcrumbs.py   # get_breadcrumbs()
├── pagination.py    # get_pagination_items()
├── tree.py          # get_nav_tree()
├── auto_nav.py      # get_auto_nav(), section menu helpers
└── toc.py           # get_toc_grouped(), combine_track_toc_items()
```

**Commit**: `rendering(navigation): create package skeleton`

---

#### Task 5.1.2: Extract Breadcrumbs Module

**Target**: `navigation/breadcrumbs.py`

**Migrate to**: Use `BreadcrumbItem` dataclass.

**Commit**: `rendering(navigation): extract breadcrumbs module with typed returns`

---

#### Task 5.1.3: Extract Pagination Module

**Target**: `navigation/pagination.py`

**Migrate to**: Use `PaginationItem` dataclass.

**Commit**: `rendering(navigation): extract pagination module with typed returns`

---

#### Task 5.1.4: Extract Tree Module

**Target**: `navigation/tree.py`

**Migrate to**: Use `NavTreeItem` dataclass.

**Commit**: `rendering(navigation): extract tree module with typed returns`

---

#### Task 5.1.5: Extract Auto-Nav Module

**Target**: `navigation/auto_nav.py`

**Includes**: `_build_section_menu_item()` and related helpers.

**Commit**: `rendering(navigation): extract auto_nav module`

---

#### Task 5.1.6: Extract TOC Module

**Target**: `navigation/toc.py`

**Commit**: `rendering(navigation): extract toc module`

---

### Phase 5.2: Mistune Parser Package

#### Task 5.2.1: Create Mistune Package Structure

**Source**: `rendering/parsers/mistune.py` (1,075 lines)  
**Target**: `rendering/parsers/mistune/`

```
bengal/rendering/parsers/mistune/
├── __init__.py      # MistuneParser class
├── highlighting.py  # Syntax highlighting plugin
├── toc.py           # TOC extraction and anchor injection
├── cross_refs.py    # Cross-reference support
└── ast.py           # AST parsing and rendering
```

**Commit**: `rendering(mistune): create package skeleton`

---

#### Task 5.2.2: Extract Highlighting Plugin

**Target**: `mistune/highlighting.py`

**Includes**: `_create_syntax_highlighting_plugin()` (175 lines)

**Commit**: `rendering(mistune): extract syntax highlighting plugin`

---

#### Task 5.2.3: Extract TOC Logic

**Target**: `mistune/toc.py`

**Commit**: `rendering(mistune): extract TOC extraction and anchor logic`

---

#### Task 5.2.4: Extract Cross-Reference Support

**Target**: `mistune/cross_refs.py`

**Commit**: `rendering(mistune): extract cross-reference support`

---

#### Task 5.2.5: Extract AST Logic

**Target**: `mistune/ast.py`

**Commit**: `rendering(mistune): extract AST parsing and rendering`

---

### Sprint 5 Exit Criteria

- [ ] Navigation package with modules < 200 lines each
- [ ] Navigation functions return typed dataclasses
- [ ] Mistune package with modules < 300 lines each
- [ ] `MistuneParser` < 400 lines
- [ ] All rendering tests pass

---

## Sprint 6: Remaining Large Files (Week 10)

### Phase 6.1: Python Extractor Package

#### Task 6.1.1: Create Python Extractor Package

**Source**: `autodoc/extractors/python.py` (1,146 lines)  
**Target**: `autodoc/extractors/python/`

```
bengal/autodoc/extractors/python/
├── __init__.py           # PythonExtractor class
├── docstring_parser.py   # Docstring parsing
├── signature_analyzer.py # Function/class signatures
├── hierarchy_builder.py  # Module hierarchy
└── metadata.py           # Metadata extraction
```

**Commits**: One per module extraction.

---

### Phase 6.2: Autodoc Naming Cleanup

#### Task 6.2.1: Audit External Plugin Imports

**Action**: Check if any external plugins import `virtual_orchestrator`.

```bash
# If no external plugins, safe to rename
grep -r "virtual_orchestrator" --include="*.py"
```

**Commit**: N/A (audit only)

---

#### Task 6.2.2: Rename virtual_orchestrator.py

**Source**: `autodoc/virtual_orchestrator.py` (27 lines)  
**Target**: `autodoc/virtual.py`

**Commit**: `autodoc: rename virtual_orchestrator.py to virtual.py for consistency`

---

### Phase 6.3: Final Cleanup & Hardening

#### Task 6.3.1: Remove Old Deprecation Stubs
**Action**: After 1 release cycle, remove deprecation redirects from Sprint 1-2.
**Commit**: `cleanup: remove deprecated import redirects`

#### Task 6.3.2: Update Architecture Documentation (New)
**Action**: Update `architecture/object-model.md` and `architecture/orchestration.md` to reflect new package structure.
**Commit**: `docs(arch): update documentation to match new package structure`

#### Task 6.3.3: Enforce 400-Line Threshold (New)
**Action**: Add `ruff` rule or custom CI script to fail build if any *new* file in `bengal/` exceeds 400 lines (existing large files can be excluded via baseline).
**Commit**: `ci: enforce 400-line threshold gate for new files`

---

### Sprint 6 Exit Criteria

- [ ] All files < 600 lines (soft target: 400)
- [ ] Python extractor package created
- [ ] Autodoc naming consistent
- [ ] All deprecation warnings functional
- [ ] All tests pass
- [ ] **Architecture docs synchronized**
- [ ] **Ruff gate active for 400-line limit**

---

## Sprint 7: Final Cleanup (Week 11) - Part 2

**Status**: Added 2025-12-20 after codebase evaluation  
**Estimated Effort**: 2-3 hours  
**Risk**: LOW

### Context

Post-implementation evaluation identified orphaned files and incomplete cleanup:

| Issue | File | Size | Cause |
|-------|------|------|-------|
| Dead code | `orchestration/incremental.py` | 1,399 lines | Old monolithic file; package supersedes it |
| Empty stub | `rendering/link_validator.py` | 0 bytes | Consolidation incomplete |
| Missing deprecation | Multiple relocated files | — | Deprecation warnings not added |

### Phase 7.1: Delete Dead Code

#### Task 7.1.1: Delete Old incremental.py

**File**: `bengal/orchestration/incremental.py` (1,399 lines)

**Verification**: Confirm all imports use the package:

```bash
# Should return ONLY files in incremental/ directory
grep -r "from bengal.orchestration.incremental" bengal/ --include="*.py" | grep -v "incremental/"
```

**Expected**: No results (all imports use `incremental/` package)

**Action**: Delete file after verification.

**Commit**: `orchestration: delete orphaned incremental.py (superseded by incremental/ package)`

---

#### Task 7.1.2: Delete Empty link_validator.py

**File**: `bengal/rendering/link_validator.py` (0 bytes)

**Action**: Delete empty file.

**Commit**: `rendering: delete empty link_validator.py stub`

---

### Phase 7.2: Verify Package Imports

#### Task 7.2.1: Verify Incremental Package Usage

**Action**: Ensure `IncrementalOrchestrator` is imported from package:

```bash
# Check orchestration/__init__.py exports
grep -A2 "IncrementalOrchestrator" bengal/orchestration/__init__.py

# Verify build/__init__.py uses package
grep "incremental" bengal/orchestration/build/__init__.py
```

**Expected**: All imports reference `bengal.orchestration.incremental` (package, not file)

**Commit**: N/A (verification only)

---

#### Task 7.2.2: Run Full Test Suite

**Action**: Verify deletions don't break anything:

```bash
pytest tests/ -v --tb=short
```

**Gate**: All tests must pass.

**Commit**: N/A (verification only)

---

### Phase 7.3: File Count Reduction

#### Task 7.3.1: Audit Remaining Large Files

**Action**: Identify files still exceeding thresholds:

```bash
wc -l bengal/**/*.py 2>/dev/null | sort -rn | head -15
```

**Current State** (post-Sprint 6):
- `analysis/knowledge_graph.py` (1,222 lines) - Out of scope for this RFC
- `core/section.py` (996 lines) - Out of scope
- `discovery/content_discovery.py` (944 lines) - Out of scope
- `rendering/pipeline/core.py` (925 lines) - Out of scope

**Decision**: These files are outside the original RFC scope. Track in separate RFC if needed.

**Commit**: N/A (audit only)

---

#### Task 7.3.2: Check utils/ File Count

**Action**: Verify utils/ is at target:

```bash
find bengal/utils -name "*.py" | wc -l  # Target: < 35
```

**Current**: 36 files (1 over target)

**Decision**: Acceptable variance. No action needed unless natural opportunity arises.

**Commit**: N/A (audit only)

---

### Phase 7.4: Documentation Sync (from Sprint 6.3)

#### Task 7.4.1: Update Architecture Documentation

**Files**:
- `architecture/object-model.md`
- `architecture/orchestration.md`

**Changes**:
- Add `incremental/` package structure diagram
- Update `IncrementalOrchestrator` description
- Document new module boundaries

**Commit**: `docs(arch): update documentation to match new package structure`

---

#### Task 7.4.2: Update Related Plan Files

**Action**: Mark deprecated plan files:

```bash
# Check for outdated RFCs referencing old structure
grep -l "incremental.py" plan/**/*.md
```

**Commit**: `docs(plan): mark superseded RFCs as archived`

---

### Phase 7.5: CI Enforcement (from Sprint 6.3)

#### Task 7.5.1: Add File Size Lint Rule

**File**: `pyproject.toml`

**Action**: Add custom ruff rule or pre-commit hook:

```toml
# Option 1: Use ruff's PLR0915 (too many statements)
[tool.ruff.lint]
select = ["PLR0915"]

# Option 2: Custom script in CI
# scripts/check_file_size.py
```

**Note**: Ruff doesn't have a direct "lines per file" rule. Consider:
1. Using `wc -l` in CI script
2. Adding baseline for existing large files

**Commit**: `ci: add file size enforcement gate`

---

### Sprint 7 Exit Criteria

- [ ] `bengal/orchestration/incremental.py` deleted
- [ ] `bengal/rendering/link_validator.py` deleted
- [ ] All tests pass after deletions
- [ ] `rendering/` file count verified (target: < 70)
- [ ] `utils/` file count verified (target: < 35)
- [ ] Architecture docs updated
- [ ] No file exceeds 600 lines (excluding baseline exemptions)

---

### Quick Execution Checklist

```bash
# 1. Verify no external imports of old incremental.py
grep -r "from bengal.orchestration.incremental import" bengal/ --include="*.py" | grep -v "incremental/"
# Expected: empty

# 2. Delete dead files
rm bengal/orchestration/incremental.py
rm bengal/rendering/link_validator.py

# 3. Run tests
pytest tests/ -v --tb=short

# 4. Commit
git add -A && git commit -m "cleanup: delete orphaned incremental.py and empty link_validator.py"

# 5. Verify metrics
find bengal/rendering -name "*.py" | wc -l  # Target: < 70
find bengal/utils -name "*.py" | wc -l       # Target: < 35
wc -l bengal/**/*.py | sort -rn | head -10
```

---

## Summary Table

| Sprint | Week | Focus | Key Deliverables |
|--------|------|-------|------------------|
| 1 | 1-2 | Package Consolidation | `directives/` package, utils relocation |
| 2 | 3-4 | Utils Extraction + Dataclasses | `cli/output/`, `orchestration/stats/`, BuildOptions |
| 3 | 5 | Validation Consolidation | Single validator source of truth |
| 4 | 6-7 | Incremental Refactoring ⚠️ | `incremental/` package, ChangeDetector |
| 5 | 8-9 | Navigation + Parser | `navigation/` package, `mistune/` package |
| 6 | 10 | Cleanup | Python extractor, naming fixes |
| **7** | **11** | **Final Cleanup** | **Dead code removal, docs sync, CI gates**

---

## Overall Exit Criteria

### Quantitative

- [ ] `rendering/` has < 70 files (from 107) — **Current: 79** (after Sprint 7: ~77)
- [ ] `utils/` has < 35 files (from 46) — **Current: 36** (1 over, acceptable)
- [ ] No file exceeds 600 lines (soft target: 400) — **Pending Sprint 7** (delete 1,399-line orphan)
- [ ] No function exceeds 100 lines (soft target: 50)
- [ ] No validation logic duplicated — **✅ Done** (`link_validator.py` empty, `validator.py` removed)
- [ ] Test coverage maintained or improved
- [ ] Build performance within 5% of baseline

### Qualitative

- [ ] New developers can find code by domain concept — **✅ Done** (domain packages created)
- [ ] Single source of truth for each concern — **✅ Done** (packages consolidated)
- [ ] Clear package boundaries — **✅ Done**
- [ ] Type hints improve IDE experience

---

## Verification Commands

```bash
# File counts
find bengal/rendering -name "*.py" | wc -l  # Target: < 70
find bengal/utils -name "*.py" | wc -l       # Target: < 35

# Largest files
wc -l bengal/**/*.py | sort -n | tail -20

# Full test suite
pytest tests/ -v --tb=short

# Performance baseline
time bengal build site/

# Lint
ruff check bengal/
```

---

## Rollback Plan

Each sprint is designed to be independently revertable:

```bash
# Revert entire sprint
git log --oneline --since="sprint-start-date"
git revert HEAD~N  # N = commits in sprint
```

For Sprint 4 (high-risk incremental changes):
- Feature flag allows instant rollback without code revert
- Shadow mode catches regressions before default enable

---

## Related

- **RFC**: `plan/evaluated/rfc-architecture-refactoring.md`
- **Deprecated RFCs**: `rfc-code-smell-remediation.md`, `rfc-package-architecture-consolidation.md`
- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc`

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-20 | Added Sprint 7 (Part 2 cleanup) after codebase evaluation | AI |
| 2025-12-20 | Updated exit criteria with current state metrics | AI |
