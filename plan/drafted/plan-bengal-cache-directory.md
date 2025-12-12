# Plan: Centralize `.bengal/` Cache Directory

**RFC**: `rfc-bengal-cache-directory.md`  
**Status**: Ready  
**Estimated Effort**: 5-7 hours  
**Confidence**: 88% 🟢

---

## Executive Summary

Implement the `BengalPaths` class to centralize all `.bengal/` directory path access, then migrate 34 source call sites and ~54 test files to use it.

---

## Phase 1a: Create `BengalPaths` Class + Unit Tests

**Goal**: Single source of truth for all `.bengal` paths  
**Effort**: 1 hour  
**Dependencies**: None

### Task 1.1: Create `bengal/cache/paths.py`

Create the `BengalPaths` class with all path properties.

**File**: `bengal/cache/paths.py` (new)

```python
"""
Single source of truth for Bengal state directory paths.

The .bengal directory stores all project-specific state:
- Build caches for incremental builds
- Query indexes for fast lookups
- Template bytecode cache
- Logs, metrics, and profiles
- Runtime state (PID files, etc.)
"""
from __future__ import annotations

from pathlib import Path


# Single source of truth
STATE_DIR_NAME = ".bengal"


class BengalPaths:
    """Accessor for all .bengal directory paths."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / STATE_DIR_NAME

    # Properties for all subdirectories and files...
```

**Commit**: `cache: add BengalPaths class as single source of truth for .bengal directory paths`

---

### Task 1.2: Add unit tests for `BengalPaths`

**File**: `tests/unit/cache/test_bengal_paths.py` (new)

Tests to include:
- `test_state_dir_under_root()` - Verify `.bengal` is under root
- `test_all_paths_under_state_dir()` - All paths start with `.bengal`
- `test_ensure_dirs_creates_directories()` - Directory creation works
- `test_paths_are_path_objects()` - Type safety verification
- `test_build_cache_path()` - Specific path verification
- `test_legacy_path_compatibility()` - Current file names match

**Commit**: `tests: add unit tests for BengalPaths class`

---

### Task 1.3: Export from `bengal/cache/__init__.py`

Add exports for `BengalPaths` and `STATE_DIR_NAME`.

**File**: `bengal/cache/__init__.py`

```python
from bengal.cache.paths import BengalPaths, STATE_DIR_NAME

__all__ = [
    # ... existing exports ...
    "BengalPaths",
    "STATE_DIR_NAME",
]
```

**Commit**: `cache: export BengalPaths and STATE_DIR_NAME from cache module`

---

## Phase 1b: Migrate Source Call Sites (34 files)

**Goal**: Replace all hardcoded `.bengal` paths with `BengalPaths`  
**Effort**: 1-2 hours  
**Dependencies**: Phase 1a

### Task 1.4: Add `site.paths` property

**File**: `bengal/core/site/core.py`

```python
from functools import cached_property
from bengal.cache.paths import BengalPaths

@cached_property
def paths(self) -> BengalPaths:
    """Access to .bengal directory paths."""
    return BengalPaths(self.root_path)
```

**Commit**: `core(site): add paths property for centralized .bengal access`

---

### Task 1.5: Migrate orchestration files (8 call sites)

**Files**:
- `orchestration/incremental.py` (2 sites) → `self.site.paths.state_dir`, `self.site.paths.build_cache`
- `orchestration/build/__init__.py` (1 site) → `self.site.paths.build_cache`
- `orchestration/build/initialization.py` (3 sites) → `paths.page_cache`, `paths.build_cache`
- `orchestration/build/rendering.py` (1 site) → `paths.asset_cache`
- `orchestration/build/content.py` (1 site) → `paths.taxonomy_cache`

**Pattern**:
```python
# Before
cache_dir = self.site.root_path / ".bengal"
cache_path = cache_dir / "cache.json"

# After
cache_path = self.site.paths.build_cache
```

**Commit**: `orchestration: migrate .bengal paths to BengalPaths`

---

### Task 1.6: Migrate orchestration secondary files (4 call sites)

**Files**:
- `orchestration/taxonomy.py` (2 sites) → `paths.taxonomy_cache`
- `orchestration/asset.py` (1 site) → `paths.js_bundle_dir`

**Commit**: `orchestration: migrate remaining .bengal paths to BengalPaths`

---

### Task 1.7: Migrate cache module (1 call site)

**File**: `cache/utils.py` (1 site) → Use `STATE_DIR_NAME` constant

**Commit**: `cache: use STATE_DIR_NAME constant in utils`

---

### Task 1.8: Migrate CLI commands (12 call sites)

**Files**:
- `cli/commands/clean.py` (3 sites) → `site.paths.state_dir`
- `cli/commands/debug.py` (3 sites) → `site.paths.build_cache`
- `cli/commands/validate.py` (3 sites) → `site.paths.build_cache`
- `cli/commands/explain.py` (1 site) → `site.paths.build_cache`
- `cli/commands/sources.py` (3 sites) → `paths.content_dir`

**Commit**: `cli: migrate .bengal paths in commands to BengalPaths`

---

### Task 1.9: Migrate CLI helpers (1 call site)

**File**: `cli/helpers/site_loader.py` (1 site) → Use `STATE_DIR_NAME` for detection

**Commit**: `cli: use STATE_DIR_NAME in site_loader detection`

---

### Task 1.10: Migrate utils files (6 call sites)

**Files**:
- `utils/paths.py` (4 sites) → `paths.profiles_dir`, `paths.logs_dir`, `paths.templates_dir`
- `utils/swizzle.py` (1 site) → `paths.swizzle_registry`
- `utils/url_strategy.py` (1 site) → `paths.state_dir / "generated"`

**Commit**: `utils: migrate .bengal paths to BengalPaths`

---

### Task 1.11: Migrate performance utils (2 call sites)

**Files**:
- `utils/performance_collector.py` (1 site) → `paths.metrics_dir`
- `utils/performance_report.py` (1 site) → `paths.metrics_dir`

**Commit**: `utils: migrate performance metrics paths to BengalPaths`

---

### Task 1.12: Migrate remaining files (6 call sites)

**Files**:
- `debug/delta_analyzer.py` (1 site) → `paths.build_history`
- `server/pid_manager.py` (1 site) → `paths.server_pid`
- `content_layer/manager.py` (1 site) → `paths.content_dir`
- `assets/pipeline.py` (1 site) → `paths.temp_dir / "pipeline_out"`
- `analysis/graph_visualizer.py` (1 site) → `paths.state_dir / "asset-manifest.json"`
- `health/validators/cache.py` (1 site) → `paths.build_cache`

**Commit**: `core: migrate remaining .bengal paths to BengalPaths`

---

### Task 1.13: Update server ignore patterns

**File**: `server/build_handler.py` - Update ignore pattern references

**Commit**: `server: use STATE_DIR_NAME in ignore patterns`

---

## Phase 1c: Update Test Files (~54 files)

**Goal**: Update test files to use `BengalPaths` or `STATE_DIR_NAME`  
**Effort**: 1-2 hours  
**Dependencies**: Phase 1b

### Task 1.14: Update unit tests (cache)

**Files** (~25 matches):
- `tests/unit/cache/test_build_cache.py`
- `tests/unit/cache/test_cache_corruption.py`
- `tests/unit/cache/test_compression.py`
- `tests/unit/cache/test_taxonomy_index.py`
- `tests/unit/cache/test_page_discovery_cache.py`
- `tests/unit/cache/test_asset_dependency_map.py`
- `tests/unit/cache/test_cacheable_properties.py`

**Strategy**: Import `BengalPaths` or `STATE_DIR_NAME` as needed

**Commit**: `tests(cache): migrate .bengal paths to BengalPaths`

---

### Task 1.15: Update unit tests (utils)

**Files** (~50 matches):
- `tests/unit/utils/test_paths.py`
- `tests/unit/utils/test_paths_properties.py`
- `tests/unit/utils/test_swizzle.py`
- `tests/unit/utils/test_url_strategy.py`
- `tests/unit/utils/test_url_strategy_properties.py`
- `tests/unit/utils/test_file_lock.py`
- `tests/unit/utils/test_page_initializer.py`

**Commit**: `tests(utils): migrate .bengal paths to BengalPaths`

---

### Task 1.16: Update unit tests (other)

**Files**:
- `tests/unit/orchestration/test_incremental_orchestrator.py`
- `tests/unit/orchestration/test_cache_migration.py`
- `tests/unit/orchestration/test_section_orchestrator.py`
- `tests/unit/orchestration/build/test_initialization.py`
- `tests/unit/health/validators/test_cache.py`
- `tests/unit/cli/test_clean_command.py`
- `tests/unit/server/test_dev_server_baseurl.py`
- `tests/unit/theme/test_swizzle.py`
- `tests/unit/autodoc/test_models_common.py`
- `tests/unit/autodoc/test_typed_metadata_access.py`
- `tests/unit/assets/test_assets_pipeline.py`

**Commit**: `tests(unit): migrate remaining .bengal paths to BengalPaths`

---

### Task 1.17: Update integration tests

**Files** (~40 matches):
- `tests/integration/test_phase2b_cache_integration.py`
- `tests/integration/test_phase2c_lazy_loading.py`
- `tests/integration/test_phase2c2_incremental_tags.py`
- `tests/integration/test_full_to_incremental_sequence.py`
- `tests/integration/test_infrastructure_prototype.py`
- `tests/integration/test_incremental_output_formats.py`
- `tests/integration/test_baseurl_builds.py`
- `tests/integration/test_documentation_builds.py`
- `tests/integration/test_cli_output_integration.py`
- `tests/integration/test_cascade_integration.py`
- `tests/integration/test_resource_cleanup.py`
- `tests/integration/test_assets_manifest.py`
- `tests/integration/stateful/test_build_workflows.py`
- `tests/integration/stateful/helpers.py`

**Commit**: `tests(integration): migrate .bengal paths to BengalPaths`

---

### Task 1.18: Update performance tests

**Files** (~30 matches):
- `tests/performance/benchmark_*.py` files
- `tests/performance/profile_utils.py`
- `tests/performance/test_jinja2_bytecode_cache.py`
- `tests/performance/README.md`
- `tests/performance/PROFILING_GUIDE.md`
- `tests/performance/PROFILING_QUICK_START.md`

**Commit**: `tests(performance): migrate .bengal paths to BengalPaths`

---

### Task 1.19: Update test utilities and markers

**Files**:
- `tests/_testing/markers.py`
- `tests/_testing/README.md`
- `tests/roots/README.md`
- `tests/README.md`

**Commit**: `tests: update test utilities and documentation with STATE_DIR_NAME`

---

## Phase 2: Relocate Template Cache

**Goal**: Move template cache from `output/.bengal-cache/templates` to `.bengal/templates`  
**Effort**: 1 hour  
**Dependencies**: Phase 1

### Task 2.1: Update template engine environment

**File**: `rendering/template_engine/environment.py`

```python
# Before
cache_dir = site.output_dir / ".bengal-cache" / "templates"

# After
cache_dir = site.paths.templates_dir
```

**Commit**: `rendering: relocate template bytecode cache to .bengal/templates`

---

### Task 2.2: Update `utils/paths.py` template cache functions

**File**: `utils/paths.py`

Update `get_template_cache_dir()` and related functions.

**Commit**: `utils: update template cache path functions for new location`

---

### Task 2.3: Add migration for old template cache location

**File**: `bengal/cache/paths.py` or `orchestration/build/initialization.py`

```python
def migrate_template_cache(paths: BengalPaths, output_dir: Path) -> None:
    """Migrate template cache from old location if exists."""
    old_cache = output_dir / ".bengal-cache" / "templates"
    if old_cache.exists() and not paths.templates_dir.exists():
        shutil.move(str(old_cache), str(paths.templates_dir))
    # Clean up old parent dir if empty
    old_parent = output_dir / ".bengal-cache"
    if old_parent.exists() and not any(old_parent.iterdir()):
        old_parent.rmdir()
```

**Commit**: `cache: add migration helper for legacy template cache location`

---

### Task 2.4: Update tests for new template cache location

Update any tests that verify template cache location.

**Commit**: `tests: update template cache location tests`

---

## Phase 3: Documentation

**Goal**: Document the `.bengal/` directory structure  
**Effort**: 1 hour  
**Dependencies**: Phase 2

### Task 3.1: Update QUICKSTART.md

Add section explaining `.bengal/` directory.

**Commit**: `docs: document .bengal directory in QUICKSTART.md`

---

### Task 3.2: Add `.bengal/README.md` generator

**File**: `bengal/cache/readme_generator.py` (new)

Auto-generate `.bengal/README.md` on first build explaining structure.

**Commit**: `cache: add README generator for .bengal directory`

---

### Task 3.3: Update architecture documentation

Add section on state management to architecture docs.

**Commit**: `docs: add state management section to architecture docs`

---

### Task 3.4: Update `.gitignore` templates

Ensure `.bengal/` is in default `.gitignore`.

**Commit**: `cli(new): ensure .bengal in default .gitignore template`

---

## Verification Checklist

After completing all tasks:

- [ ] `grep -r '\.bengal"' bengal/` returns only `STATE_DIR_NAME` definition
- [ ] `grep -r '\.bengal"' tests/` returns only intentional legacy tests
- [ ] All unit tests pass: `pytest tests/unit/`
- [ ] All integration tests pass: `pytest tests/integration/`
- [ ] Template cache is created at `.bengal/templates/` not `output/.bengal-cache/templates`
- [ ] `site.paths` is accessible and works correctly
- [ ] Legacy caches are read correctly (backwards compatibility)

---

## Pre-drafted Commits (Summary)

| Task | Commit Message |
|------|----------------|
| 1.1 | `cache: add BengalPaths class as single source of truth for .bengal directory paths` |
| 1.2 | `tests: add unit tests for BengalPaths class` |
| 1.3 | `cache: export BengalPaths and STATE_DIR_NAME from cache module` |
| 1.4 | `core(site): add paths property for centralized .bengal access` |
| 1.5 | `orchestration: migrate .bengal paths to BengalPaths` |
| 1.6 | `orchestration: migrate remaining .bengal paths to BengalPaths` |
| 1.7 | `cache: use STATE_DIR_NAME constant in utils` |
| 1.8 | `cli: migrate .bengal paths in commands to BengalPaths` |
| 1.9 | `cli: use STATE_DIR_NAME in site_loader detection` |
| 1.10 | `utils: migrate .bengal paths to BengalPaths` |
| 1.11 | `utils: migrate performance metrics paths to BengalPaths` |
| 1.12 | `core: migrate remaining .bengal paths to BengalPaths` |
| 1.13 | `server: use STATE_DIR_NAME in ignore patterns` |
| 1.14 | `tests(cache): migrate .bengal paths to BengalPaths` |
| 1.15 | `tests(utils): migrate .bengal paths to BengalPaths` |
| 1.16 | `tests(unit): migrate remaining .bengal paths to BengalPaths` |
| 1.17 | `tests(integration): migrate .bengal paths to BengalPaths` |
| 1.18 | `tests(performance): migrate .bengal paths to BengalPaths` |
| 1.19 | `tests: update test utilities and documentation with STATE_DIR_NAME` |
| 2.1 | `rendering: relocate template bytecode cache to .bengal/templates` |
| 2.2 | `utils: update template cache path functions for new location` |
| 2.3 | `cache: add migration helper for legacy template cache location` |
| 2.4 | `tests: update template cache location tests` |
| 3.1 | `docs: document .bengal directory in QUICKSTART.md` |
| 3.2 | `cache: add README generator for .bengal directory` |
| 3.3 | `docs: add state management section to architecture docs` |
| 3.4 | `cli(new): ensure .bengal in default .gitignore template` |

---

## Rollback Plan

If issues arise during implementation:

1. **Phase 1 issues**: Keep `BengalPaths` but retain raw `.bengal` strings as fallback
2. **Phase 2 issues**: Keep template cache at old location, update `BengalPaths.templates_dir` to point there
3. **Full rollback**: Revert all commits, codebase continues to work with hardcoded strings

---

## Future Work (Out of Scope)

- **Phase 4**: Reorganize directory structure (cache/, state/, etc.)
- **Phase 5**: Add optional compression for large caches
- **Configuration**: Add `state_dir` config option for custom location
