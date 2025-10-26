# Implementation Plan: Stable Section References

**Based on**: RFC: Stable State Management for Incremental Builds  
**Created**: 2025-10-26  
**Status**: Active  
**Estimated Time**: 5 days  
**Complexity**: Moderate

---

## Executive Summary

Implement path-based section references to eliminate object identity fragmentation in incremental builds. Replace direct `Section` object references with path storage + lazy lookup via O(1) registry. Fixes wrong URLs, lost cascade metadata, and broken navigation in dev server.

### Plan Details
- **Total Tasks**: 23 tasks across 4 phases
- **Estimated Time**: 5 days (40 hours)
- **Complexity**: Moderate (~300 lines across 8 files)
- **Confidence Gates**: Implementation ≥90%, Performance < 1% regression

---

## Phase 1: Foundation (Days 1-2, 7 tasks)

### Core: Site Registry Infrastructure

#### Task 1.1: Add section registry to Site
- **ID**: `core-site-registry`
- **Files**: `bengal/core/site.py`
- **Action**:
  - Add `_section_registry: dict[Path, Section]` field
  - Implement `_normalize_section_path()` method (relative to content/, resolve symlinks, lowercase on case-insensitive FS)
  - Implement `get_section_by_path()` method (O(1) lookup with normalization)
  - Implement `register_sections()` method (builds registry with metrics logging)
  - Implement `_register_section_recursive()` helper
- **Dependencies**: None
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add bengal/core/site.py && git commit -m "core(site): add path-based section registry with O(1) lookup

Adds section registry infrastructure for stable references across rebuilds:
- _section_registry: dict mapping normalized paths to Section objects
- _normalize_section_path(): cross-platform path normalization
- get_section_by_path(): O(1) lookup by path
- register_sections(): builds registry with debug metrics

Part of path-based reference system to eliminate object identity brittleness."
```

---

#### Task 1.2: Convert Page._section to property with path storage
- **ID**: `core-page-section-property`
- **Files**: `bengal/core/page/__init__.py`
- **Action**:
  - **CRITICAL**: Remove `_section: Section | None` dataclass field (line 102)
  - Add `_section_path: Path | None` field
  - Add `_missing_section_warnings: dict[str, int]` field for counter-gated warnings
  - Implement `_section` property getter (lazy lookup via `site.get_section_by_path()`)
  - Implement `_section` setter (stores path, not object)
  - Add counter-gated warning logic for missing sections (warn first 3, summary, then silent)
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~50
- **Commit**:
```bash
git add bengal/core/page/__init__.py && git commit -m "core(page): convert _section to path-based property with lazy lookup

Replace direct Section object reference with path-based lookup:
- Remove _section dataclass field (prevents setter bypass)
- Add _section_path storage field
- Implement _section property (lazy lookup via site registry)
- Implement _section setter (stores path from Section.path)
- Add counter-gated warnings for missing sections (log spam prevention)

Section references now survive object recreation across rebuilds."
```

---

#### Task 1.3: Convert PageProxy._section to property with path storage
- **ID**: `core-proxy-section-property`
- **Files**: `bengal/core/page/proxy.py`
- **Action**:
  - Add `_section_path: Path | None` field to `__init__`
  - Implement `_section` property getter (delegate to loaded page if loaded, else lookup via path)
  - Implement `_section` setter (stores path)
  - Update `_ensure_loaded()` to transfer `_section_path` instead of object reference
- **Dependencies**: Task 1.2
- **Status**: pending
- **Lines**: ~40
- **Commit**:
```bash
git add bengal/core/page/proxy.py && git commit -m "core(proxy): convert PageProxy._section to path-based property

Match Page interface with path-based section references:
- Add _section_path storage field
- Implement _section property (lookup via site registry)
- Update _ensure_loaded to transfer path, not object

PageProxy references now stable across incremental rebuilds."
```

---

### Orchestration: Registry Integration

#### Task 1.4: Wire register_sections() into content orchestrator
- **ID**: `orch-register-sections`
- **Files**: `bengal/orchestration/content.py`
- **Action**:
  - Add `site.register_sections()` call in `discover_and_setup()`
  - **Critical placement**: AFTER `discover_content()`, BEFORE `_setup_page_references()`
  - Add comment documenting build ordering invariant
  - Import `time` for registry timing
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~15
- **Commit**:
```bash
git add bengal/orchestration/content.py && git commit -m "orchestration(content): register sections after discovery for path-based lookups

Add site.register_sections() call in build ordering invariant:
1. discover_content()       → Creates Page/Section objects
2. register_sections()      → Builds path→section registry (NEW)
3. setup_page_references()  → Sets page._section via property setter
4. apply_cascades()         → Lookups resolve via registry
5. generate_urls()          → Uses correct section hierarchy

Ensures section references remain valid when objects recreated."
```

---

### Discovery: Path-Based Cache Comparison

#### Task 1.5: Update cache validation to compare paths, not objects
- **ID**: `disc-cache-path-compare`
- **Files**: `bengal/discovery/content_discovery.py`
- **Action**:
  - Update `_cache_is_valid()` method (if it exists)
  - Change section comparison from object identity to path comparison
  - Compare `cached._section_path` vs `page._section.path` (with None handling)
- **Dependencies**: Task 1.3
- **Status**: pending
- **Lines**: ~10
- **Commit**:
```bash
git add bengal/discovery/content_discovery.py && git commit -m "discovery: compare section paths in cache validation, not object identity

Update _cache_is_valid to compare section paths instead of object identity:
- cached._section_path vs current page._section.path
- Handles None sections correctly
- Works with path-based reference system

Prevents false cache invalidation from object recreation."
```

---

### Tests: Unit Tests for Core Infrastructure

#### Task 1.6: Add unit tests for section registry
- **ID**: `test-section-registry`
- **Files**: `tests/unit/test_site_section_registry.py` (new file)
- **Action**:
  - `test_register_sections_builds_registry()` - Verify registry built correctly
  - `test_get_section_by_path_normalized()` - Path normalization works
  - `test_get_section_by_path_case_insensitive()` - macOS/Windows case handling
  - `test_get_section_by_path_symlinks()` - Symlink resolution
  - `test_registry_recursive_subsections()` - Nested sections registered
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~150
- **Commit**:
```bash
git add tests/unit/test_site_section_registry.py && git commit -m "tests(core): add unit tests for section registry infrastructure

Test coverage for site.register_sections() and path-based lookups:
- Registry build with metrics
- Path normalization (relative, symlinks, case)
- O(1) lookup performance
- Recursive subsection registration"
```

---

#### Task 1.7: Add unit tests for Page/PageProxy path-based references
- **ID**: `test-page-section-property`
- **Files**: `tests/unit/test_page_section_references.py` (new file)
- **Action**:
  - `test_section_reference_survives_recreation()` - Object recreation works
  - `test_page_url_stable_across_rebuilds()` - URLs correct after rebuild
  - `test_proxy_url_without_forcing_load()` - Proxy doesn't trigger load
  - `test_section_setter_stores_path()` - Setter behavior correct
  - `test_missing_section_counter_gated_warnings()` - Warning logic works
- **Dependencies**: Tasks 1.2, 1.3
- **Status**: pending
- **Lines**: ~200
- **Commit**:
```bash
git add tests/unit/test_page_section_references.py && git commit -m "tests(core): add unit tests for path-based page section references

Comprehensive test coverage for Page/PageProxy._section property:
- Section references survive object recreation
- URLs stable across rebuilds
- Proxy doesn't force load on section access
- Counter-gated warnings prevent log spam
- Setter stores path correctly"
```

---

## Phase 2: Integration & Validation (Days 3-4, 10 tasks)

### Integration Tests

#### Task 2.1: Test dev server stability with _index.md edits
- **ID**: `test-dev-server-cascade`
- **Files**: `tests/integration/test_incremental_section_stability.py` (new file)
- **Action**:
  - `test_live_server_section_changes()` - Basic dev server workflow
  - `test_dev_server_index_edit_preserves_cascades()` - Cascade updates correctly
  - `test_dev_server_create_delete_files()` - File operations work
  - Simulate full dev server workflow (build, edit, rebuild, verify)
- **Dependencies**: Tasks 1.1-1.5
- **Status**: pending
- **Lines**: ~150
- **Commit**:
```bash
git add tests/integration/test_incremental_section_stability.py && git commit -m "tests(integration): add dev server section stability tests

Integration tests for live server with section changes:
- Edit _index.md preserves cascades and URLs
- Create/delete files maintain correct structure
- Incremental rebuilds use correct section relationships

Validates fix for user-reported issues."
```

---

#### Task 2.2: Test section rename/move fallback behavior
- **ID**: `test-section-rename`
- **Files**: `tests/integration/test_incremental_section_stability.py`
- **Action**:
  - `test_section_rename_treated_as_delete_create()` - Fallback URL works
  - `test_section_move_triggers_full_rebuild()` - Build handler detects move
  - Verify graceful degradation when sections deleted/moved
- **Dependencies**: Task 2.1
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add tests/integration/test_incremental_section_stability.py && git commit -m "tests(integration): add section rename/move fallback tests

Test graceful degradation for structural changes:
- Renamed sections trigger fallback URLs (slug-based)
- Moved sections detected by build handler
- Pages remain accessible with fallback URLs

Validates design decision for treating renames as delete+create."
```

---

### Performance Validation

#### Task 2.3: Add performance benchmarks for registry lookups
- **ID**: `test-registry-performance`
- **Files**: `tests/performance/benchmark_section_lookup.py` (new file)
- **Action**:
  - `test_registry_lookup_performance()` - < 1µs per lookup for 10K sections
  - `test_registry_build_time()` - < 10ms for 10K sections
  - `test_registry_memory_bounded()` - < 50MB for 10K sections
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~120
- **Commit**:
```bash
git add tests/performance/benchmark_section_lookup.py && git commit -m "tests(perf): add section registry performance benchmarks

Microbenchmarks for path-based lookup system:
- Lookup time < 1µs for 10K sections
- Registry build < 10ms for 10K sections
- Memory usage < 50MB for 10K sections

Validates O(1) performance characteristics."
```

---

#### Task 2.4: Add full build performance regression test
- **ID**: `test-build-regression`
- **Files**: `tests/performance/benchmark_section_lookup.py`
- **Action**:
  - `test_full_build_performance_regression()` - 253+ pps (< 1% regression from 256 pps)
  - `test_incremental_build_speedup_maintained()` - 15-50x speedup preserved
  - Run on 1000-page test site
- **Dependencies**: Tasks 1.1-1.5
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add tests/performance/benchmark_section_lookup.py && git commit -m "tests(perf): add build performance regression tests

Validate path-based references maintain performance:
- Full build: 253+ pps (< 1% regression)
- Incremental: 15-50x speedup maintained

Ensures fix doesn't impact build times."
```

---

### Large Site Testing

#### Task 2.5: Test 10K page site with path-based references
- **ID**: `test-large-site`
- **Files**: `tests/integration/test_incremental_section_stability.py`
- **Action**:
  - `test_large_site_registry_memory_bounded()` - Memory growth bounded
  - `test_large_site_all_urls_correct()` - All page URLs correct
  - Generate 10K pages across 1K sections
  - Verify full build + incremental rebuild
- **Dependencies**: Task 2.1
- **Status**: pending
- **Lines**: ~100
- **Commit**:
```bash
git add tests/integration/test_incremental_section_stability.py && git commit -m "tests(integration): add 10K page site stability test

Large-scale validation:
- 10K pages across 1K sections
- Memory bounded (< 50MB for registry)
- All URLs correct after full/incremental builds

Validates production readiness at scale."
```

---

### Cross-Platform Testing

#### Task 2.6: Test path normalization on case-insensitive filesystems
- **ID**: `test-path-normalization`
- **Files**: `tests/unit/test_site_section_registry.py`
- **Action**:
  - `test_path_normalization_cross_platform()` - Case handling by platform
  - `test_symlink_resolution()` - Symlinks resolved correctly
  - Platform-specific test skipping (Linux vs macOS/Windows)
- **Dependencies**: Task 1.6
- **Status**: pending
- **Lines**: ~60
- **Commit**:
```bash
git add tests/unit/test_site_section_registry.py && git commit -m "tests(core): add cross-platform path normalization tests

Platform-specific validation:
- macOS/Windows: case-insensitive lookups work
- Linux: case-sensitive lookups work
- Symlinks resolved correctly on all platforms

Validates cross-platform correctness."
```

---

### Feature Flag Implementation

#### Task 2.7: Add stable_section_references config flag
- **ID**: `config-feature-flag`
- **Files**: `bengal/core/site.py`, `bengal/utils/config_schema.py`
- **Action**:
  - Add `build.stable_section_references` to config schema (default: true)
  - Add conditional logic in `Site.get_section_by_path()` to check flag
  - Add fallback to direct object references if flag disabled
  - Document flag in config schema
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~30
- **Commit**:
```bash
git add bengal/core/site.py bengal/utils/config_schema.py && git commit -m "core(config): add stable_section_references feature flag

Add rollback safety for path-based references:
- build.stable_section_references: true (default)
- Conditional logic in get_section_by_path()
- Falls back to direct refs if disabled

Enables rollback if critical issues discovered post-release."
```

---

### Linting & Type Checking

#### Task 2.8: Fix linter errors from new code
- **ID**: `lint-fixes`
- **Files**: All modified files
- **Action**:
  - Run `ruff check bengal/` and fix issues
  - Run `mypy bengal/` and fix type errors
  - Ensure all new code passes linting
- **Dependencies**: Tasks 1.1-1.7
- **Status**: pending
- **Commit**:
```bash
git add -A && git commit -m "chore: fix linter and type errors in path-based reference implementation"
```

---

### Validation Gate: Phase 2 Complete

#### Task 2.9: Run full test suite
- **ID**: `validate-phase-2`
- **Files**: N/A (validation task)
- **Action**:
  - Run `pytest tests/unit/` - All pass
  - Run `pytest tests/integration/` - All pass
  - Run `pytest tests/performance/` - Within thresholds
  - Verify no regressions
- **Dependencies**: Tasks 2.1-2.8
- **Status**: pending
- **Command**:
```bash
pytest tests/ -v --tb=short
```

---

#### Task 2.10: Verify dev server works with real site
- **ID**: `validate-dev-server`
- **Files**: N/A (manual validation)
- **Action**:
  - Start dev server: `cd site && bengal site serve`
  - Edit `content/getting-started/_index.md` (change cascade)
  - Verify URLs correct: `http://localhost:5173/getting-started/writer-quickstart/`
  - Verify sidebar appears (cascade applied)
  - Create new file, verify it appears correctly
  - Delete file, verify it disappears
- **Dependencies**: Task 2.9
- **Status**: pending
- **Command**:
```bash
cd /Users/llane/Documents/github/python/bengal/site
bengal site serve
# Then test manually
```

---

## Phase 3: Documentation (Day 5, 5 tasks)

### Architecture Documentation

#### Task 3.1: Document path-based references in architecture
- **ID**: `docs-architecture`
- **Files**: `architecture/object-model.md` (new or update existing)
- **Action**:
  - Document path-based reference design
  - Explain section registry
  - Show lookup flow diagram (ASCII art)
  - Document build ordering invariant
  - Add examples
- **Dependencies**: Task 2.10
- **Status**: pending
- **Lines**: ~200
- **Commit**:
```bash
git add architecture/object-model.md && git commit -m "docs(architecture): document path-based section reference system

Add comprehensive documentation for stable references:
- Section registry design and O(1) lookups
- Page/PageProxy property-based interface
- Build ordering invariant
- Lookup flow diagram
- Migration notes from object refs

Provides architectural context for maintainers."
```

---

### Plugin Author Documentation

#### Task 3.2: Add plugin author contract to CONTRIBUTING.md
- **ID**: `docs-plugin-contract`
- **Files**: `CONTRIBUTING.md`
- **Action**:
  - Add "Working with Page-Section References" section
  - Document DO/DON'T for plugin authors
  - Show code examples (good vs bad)
  - Note performance characteristics (< 1µs lookup)
- **Dependencies**: Task 3.1
- **Status**: pending
- **Lines**: ~100
- **Commit**:
```bash
git add CONTRIBUTING.md && git commit -m "docs(contrib): add plugin author contract for page-section references

Document best practices for plugins using page._section:
- DO: Use as property, compare by path
- DON'T: Store objects across builds, compare with 'is'
- Examples of correct usage
- Performance notes (O(1) lookups)

Prevents plugins from breaking with path-based system."
```

---

### Changelog Update

#### Task 3.3: Add changelog entry for v0.2.0
- **ID**: `docs-changelog`
- **Files**: `changelog.md`
- **Action**:
  - Add entry under "## Unreleased" or "## [0.2.0] - 2025-XX-XX"
  - Document fix for dev server URL issues
  - Note breaking change (internal only)
  - Document feature flag
- **Dependencies**: Task 3.2
- **Status**: pending
- **Lines**: ~30
- **Commit**:
```bash
git add changelog.md && git commit -m "docs(changelog): add entry for stable section references fix

Changelog for v0.2.0:
- Fixed: Dev server URL issues with _index.md edits
- Fixed: Lost cascade metadata in incremental builds
- Added: Path-based section references (internal change)
- Added: build.stable_section_references config flag

User-facing improvements to live server reliability."
```

---

### Code Comments & Docstrings

#### Task 3.4: Add docstrings to all new methods
- **ID**: `docs-docstrings`
- **Files**: All modified files
- **Action**:
  - Ensure all new methods have docstrings
  - Add type hints where missing
  - Document critical invariants in comments
  - Add examples in docstrings where helpful
- **Dependencies**: Tasks 1.1-1.5
- **Status**: pending
- **Commit**:
```bash
git add -A && git commit -m "docs: add comprehensive docstrings to path-based reference implementation

Improve code documentation:
- Docstrings for all new methods
- Type hints complete
- Critical invariants documented
- Examples in complex methods

Enhances maintainability."
```

---

### Migration Guide (if needed)

#### Task 3.5: Create migration guide for plugin authors
- **ID**: `docs-migration`
- **Files**: `docs/migration/v0.2.0-section-references.md` (new, if needed)
- **Action**:
  - Only needed if plugins exist that access `_section` directly
  - Document breaking changes
  - Provide migration examples
  - List affected APIs
- **Dependencies**: Task 3.2
- **Status**: pending (optional)
- **Commit**:
```bash
git add docs/migration/v0.2.0-section-references.md && git commit -m "docs(migration): add v0.2.0 section reference migration guide

Plugin migration from object refs to path-based lookups:
- Breaking changes (internal only)
- Code examples for migration
- Testing recommendations

Helps plugin authors update to v0.2.0."
```

---

## Phase 4: Final Validation & Ship (Day 5, 1 task)

### Final Validation Gate

#### Task 4.1: Complete pre-merge checklist
- **ID**: `validate-final`
- **Files**: N/A (validation task)
- **Action**:
  - [ ] All unit tests pass
  - [ ] All integration tests pass
  - [ ] All performance tests within thresholds (< 1% regression)
  - [ ] Linter passes (no errors)
  - [ ] Type checker passes (mypy)
  - [ ] Dev server works with real site (manual test)
  - [ ] Documentation complete
  - [ ] Changelog updated
  - [ ] Feature flag works (test rollback)
  - [ ] Cross-platform tests pass (if applicable)
  - [ ] Confidence ≥ 90%
- **Dependencies**: All previous tasks
- **Status**: pending
- **Command**:
```bash
# Run full validation suite
pytest tests/ -v
ruff check bengal/
mypy bengal/
# Manual dev server test
cd site && bengal site serve
```

---

## 📊 Task Summary

| Phase | Area | Tasks | Lines | Status |
|-------|------|-------|-------|--------|
| 1. Foundation | Core | 3 | ~170 | pending |
| 1. Foundation | Orchestration | 1 | ~15 | pending |
| 1. Foundation | Discovery | 1 | ~10 | pending |
| 1. Foundation | Tests | 2 | ~350 | pending |
| 2. Integration | Tests | 5 | ~590 | pending |
| 2. Integration | Config | 1 | ~30 | pending |
| 2. Integration | Validation | 3 | - | pending |
| 3. Documentation | Docs | 5 | ~330 | pending |
| 4. Final | Validation | 1 | - | pending |
| **Total** | | **23** | **~1495** | **0% complete** |

---

## 🎯 Critical Path

**Must complete in order**:
1. Task 1.1 (Site registry) → Task 1.2 (Page property) → Task 1.3 (Proxy property)
2. Task 1.4 (Orchestration wiring)
3. Task 1.5 (Cache validation)
4. Tasks 1.6-1.7 (Unit tests)
5. All Phase 2 tasks (can parallelize tests)
6. All Phase 3 tasks (documentation)
7. Task 4.1 (Final validation)

**Can parallelize**:
- Tasks 2.1-2.6 (different test files)
- Tasks 3.1-3.5 (documentation)

---

## 📋 Quality Gates

### Phase 1 Gate (Foundation Complete)
- ✅ All unit tests pass
- ✅ Linter passes
- ✅ Core infrastructure working

### Phase 2 Gate (Integration Complete)
- ✅ All integration tests pass
- ✅ Performance < 1% regression
- ✅ Dev server works manually
- ✅ Confidence ≥ 90%

### Phase 3 Gate (Documentation Complete)
- ✅ Architecture documented
- ✅ Plugin contract documented
- ✅ Changelog updated

### Phase 4 Gate (Ready to Merge)
- ✅ All tests pass
- ✅ All documentation complete
- ✅ Feature flag tested
- ✅ Manual validation successful
- ✅ No regressions

---

## 🚀 Next Steps

**To begin implementation**:
```bash
# 1. Start with Task 1.1
::implement Task 1.1

# Or start the entire Phase 1
::implement Phase 1
```

**To track progress**:
- Update task statuses in this document as you complete them
- Run validation gates at end of each phase
- Document any issues or deviations in this file

**Alternative workflows**:
- Review plan first, adjust task breakdown if needed
- Run `::validate` on RFC again if confidence concerns
- Prototype Task 1.1-1.3 first to validate approach

---

## 📌 Notes

**Implementation Tips**:
1. **Start with tests**: Write tests for Task 1.1 before implementing (TDD)
2. **Incremental commits**: Commit after each task (atomic commits)
3. **Verify as you go**: Run tests after each task
4. **Don't skip Phase 2**: Integration tests catch edge cases

**Risk Mitigation**:
- Feature flag allows rollback if issues found
- Comprehensive test coverage reduces regression risk
- Manual dev server validation catches UX issues
- Performance tests ensure no speed regression

**Success Criteria**:
- Dev server works flawlessly for create/modify/delete operations
- URLs always correct (no more `/page/` instead of `/section/page/`)
- Cascade metadata preserved across rebuilds
- Performance within 1% of baseline (253+ pps)
- No user-facing changes required

---

**Status**: Ready to implement  
**Recommended Next Command**: `::implement Task 1.1` (start with site registry)
