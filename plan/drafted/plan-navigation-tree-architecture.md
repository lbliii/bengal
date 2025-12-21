# Plan: Navigation Tree Architecture Implementation

**Status**: Ready  
**Scope**: Core navigation model, caching, and theme simplification  
**RFC**: `plan/drafted/rfc-navigation-tree-architecture.md`  
**Confidence**: 92% 🟢

---

## Overview

This plan implements the `NavTree` abstraction to move navigation logic from Jinja templates into a pre-computed, cached Python structure. This improves build performance, simplifies theme development, and provides robust version-switching fallbacks.

**Key Metrics**:
- Current `docs-nav.html`: 161 lines → Target: <60 lines
- Render overhead: ~5ms (estimated) → Target: <1ms (O(1) lookup)
- Cache hit rate target: >99% for same-version pages

---

## Phase 1: Core Navigation Model & Cache

**Goal**: Implement foundational data structures and thread-safe caching.  
**Dependencies**: None

### 1.1 Create NavNode Model

- [ ] **Create `bengal/core/nav_tree.py`**
  - [ ] Implement `NavNode` dataclass with:
    - `__slots__` for memory efficiency (~200 bytes per node)
    - Dict-like access (`__getitem__`, `get()`, `keys()`) for Jinja compatibility
    - Attributes: `id`, `title`, `url`, `icon`, `weight`, `children`, `page`, `section`
    - State flags: `is_index`, `is_current`, `is_in_trail`, `is_expanded`
    - Properties: `has_children`, `depth`
    - Methods: `walk()` (iterator), `find(url)` (lookup)
  - [ ] Follow pattern from existing `NavTreeItem` in `bengal/rendering/template_functions/navigation/models.py:149-211`
- [ ] **Commit**: `core: introduce NavNode dataclass with slots and dict-like access for Jinja templates`

### 1.2 Create NavTree Model

- [ ] **Implement `NavTree` in `bengal/core/nav_tree.py`**
  - [ ] Attributes: `root` (NavNode), `version_id`, `versions`, `current_version`
  - [ ] Cached properties: `flat_nodes`, `urls` (set for O(1) membership)
  - [ ] Methods:
    - `find(url)` → NavNode | None
    - `with_active_trail(page)` → NavTreeContext (immutable overlay)
    - `build(site, version_id)` → NavTree (classmethod)
  - [ ] `build()` must handle:
    - Version-aware section traversal (use existing `pages_for_version()`)
    - `_shared/` content injection into all version trees
    - Logical URL resolution (strip `_versions/` prefixes)
- [ ] **Commit**: `core: add NavTree with version-aware build logic and shared content injection`

### 1.3 Create NavTreeContext (Active Trail Overlay)

- [ ] **Implement `NavTreeContext` in `bengal/core/nav_tree.py`**
  - [ ] Lightweight wrapper preserving cached tree immutability
  - [ ] Cached property: `active_trail_urls` (set of URLs to current page)
  - [ ] Methods: `is_active(node)`, `is_current(node)`
  - [ ] Avoid deep-copying the cached NavTree
- [ ] **Commit**: `core: add NavTreeContext for per-page active trail overlay without cache mutation`

### 1.4 Create NavTreeCache (Thread-Safe)

- [ ] **Implement `NavTreeCache` in `bengal/core/nav_tree.py`**
  - [ ] Class-level cache: `_trees: dict[str | None, NavTree]`
  - [ ] Class-level site reference: `_site: Site | None`
  - [ ] Use `threading.Lock` for thread safety
  - [ ] Lock held only during dict access, NOT during tree building (which is slow)
  - [ ] Methods:
    - `get(site, version_id)` → NavTree (build or return cached)
    - `invalidate(version_id)` → Clear specific version or all
  - [ ] Invalidation triggers:
    - Site object changes (full invalidation)
    - `structural_changed=True` in incremental builds
- [ ] **Commit**: `core: add thread-safe NavTreeCache with site-level invalidation`

### 1.5 Integrate Version URL Logic

- [ ] **Implement `NavTree.get_target_url()` in `bengal/core/nav_tree.py`**
  - [ ] Delegate to existing logic in `bengal/rendering/template_functions/version_url.py:106`
  - [ ] Implement Fallback Cascade:
    1. Exact page match in target version
    2. Section index match
    3. Version root URL
  - [ ] Pre-compute valid URLs at build time for O(1) version dropdown hrefs
- [ ] **Commit**: `core(nav_tree): integrate version-switching fallback cascade from version_url.py`

---

## Phase 2: Template Function Integration

**Goal**: Update rendering layer with backward compatibility.  
**Dependencies**: Phase 1 complete

### 2.1 Update get_nav_tree Function

- [ ] **Update `bengal/rendering/template_functions/navigation/tree.py`**
  - [ ] Refactor `get_nav_tree(page, root_section, mark_active_trail)` to:
    - Delegate to `NavTreeCache.get(site, version_id)`
    - Return `NavTreeContext` (overlay with active trail)
  - [ ] Preserve existing function signature for backward compatibility
  - [ ] Map new `NavNode` attributes to expected template keys:
    - `is_in_active_trail` (existing) ↔ `is_in_trail` (new)
    - Ensure both work for transition period
- [ ] **Commit**: `rendering(nav): refactor get_nav_tree to delegate to NavTreeCache; preserve backward compat`

### 2.2 Deprecate Legacy NavTreeItem

- [ ] **Update `bengal/rendering/template_functions/navigation/models.py`**
  - [ ] Add deprecation warning to `NavTreeItem` docstring:
    ```python
    .. deprecated:: 0.2.0
       Use :class:`bengal.core.nav_tree.NavNode` instead.
       Will be removed in version 2.0.
    ```
  - [ ] Keep class functional for backward compatibility
- [ ] **Commit**: `rendering(nav): deprecate NavTreeItem in favor of core.NavNode; scheduled removal in v2.0`

### 2.3 Integrate with IncrementalOrchestrator

- [ ] **Update `bengal/orchestration/incremental/orchestrator.py`**
  - [ ] Add `NavTreeCache.invalidate()` call when `structural_changed=True`
  - [ ] Structural changes include: new pages, deleted pages, metadata changes (title, weight, icon)
  - [ ] Do NOT invalidate for content-only changes
- [ ] **Commit**: `orchestration(incremental): invalidate NavTreeCache on structural changes`

---

## Phase 3: Theme Optimization

**Goal**: Simplify default theme templates.  
**Dependencies**: Phase 2 complete

### 3.1 Refactor docs-nav.html

- [ ] **Refactor `bengal/themes/default/templates/partials/docs-nav.html`**
  - [ ] Current: 161 lines with version-filtering boilerplate
  - [ ] Target: <60 lines using new NavTree API
  - [ ] Replace:
    ```jinja
    {# OLD: ~40 lines of boilerplate #}
    {% set current_version_id = current_version.id if ... %}
    {% set version_filter = current_version_id if site.versioning_enabled else none %}
    {% set sorted_pages = root_section.pages_for_version(version_filter) %}
    ...
    ```
    With:
    ```jinja
    {# NEW: Single function call #}
    {% set nav = get_nav_tree(page) %}
    ```
  - [ ] Use `nav.root.children` for iteration
  - [ ] Use `item.is_current` and `item.is_in_trail` for styling
  - [ ] Use `item.has_children` and `item.children` for nesting
- [ ] **Commit**: `themes(docs): simplify docs-nav.html from 161 to <60 lines using NavTree API`

### 3.2 Refactor docs-nav-section.html (if exists)

- [ ] **Check for `bengal/themes/default/templates/partials/docs-nav-section.html`**
  - [ ] If exists, update to use NavNode recursive macro
  - [ ] Remove redundant version-filtering logic
- [ ] **Commit**: `themes(docs): simplify docs-nav-section.html using NavNode recursive rendering`

### 3.3 Update Version Selector

- [ ] **Update `bengal/themes/default/templates/partials/version-selector.html`**
  - [ ] Use `nav.get_target_url(page, version)` for dropdown hrefs
  - [ ] Pre-computed URLs eliminate client-side fallback logic
- [ ] **Commit**: `themes(docs): use NavTree.get_target_url for version selector hrefs; eliminate client fallback`

---

## Phase 4: Validation & Testing

**Goal**: Ensure correctness, performance, and thread safety.  
**Dependencies**: Phase 3 complete

### 4.1 Unit Tests

- [ ] **Create `tests/unit/test_nav_tree.py`**
  - [ ] Test `NavNode`:
    - Dict-like access (`node['title']`, `node.get('url')`)
    - `walk()` iteration
    - `find(url)` lookup
    - `has_children` property
  - [ ] Test `NavTree`:
    - `build()` with simple site
    - `build()` with versioned site (multiple versions)
    - `build()` with `_shared/` content appears in all versions
    - `find(url)` returns correct node
    - `flat_nodes` and `urls` cached properties
  - [ ] Test `NavTreeContext`:
    - `is_active(node)` for nodes in trail
    - `is_current(node)` for current page only
    - Immutability (cached tree unchanged)
  - [ ] Test `NavTreeCache`:
    - Cache hit on same version
    - Cache invalidation on site change
    - Thread safety under concurrent access
  - [ ] Test `get_target_url()`:
    - Exact page match scenario
    - Section index fallback scenario
    - Version root fallback scenario
- [ ] **Commit**: `tests(nav): add comprehensive unit tests for NavNode, NavTree, NavTreeCache`

### 4.2 Integration Tests

- [ ] **Create `tests/integration/test_nav_tree_integration.py`**
  - [ ] Use `tests/roots/test-versioned/` site fixture
  - [ ] Verify navigation links resolve correctly across versions
  - [ ] Verify `_shared/` pages appear in all version navigation trees
  - [ ] Verify version switcher URLs are valid (no 404s)
- [ ] **Commit**: `tests(nav): add integration tests for versioned site navigation`

### 4.3 Performance Benchmarks

- [ ] **Add to `benchmarks/test_build.py`** (or create new file)
  - [ ] Benchmark `NavTree.build()` with 100, 500, 1000 pages
  - [ ] Benchmark cache lookup vs cold build
  - [ ] Compare render time before/after (target: <1ms per page)
  - [ ] Document results in commit message
- [ ] **Commit**: `perf(nav): add NavTree benchmarks; verify O(1) cache lookup`

### 4.4 Thread Safety Tests

- [ ] **Add to `tests/unit/test_nav_tree.py`**
  - [ ] Test concurrent `NavTreeCache.get()` calls
  - [ ] Test invalidation during concurrent reads
  - [ ] Use `concurrent.futures.ThreadPoolExecutor` with 8+ workers
- [ ] **Commit**: `tests(nav): add thread safety tests for NavTreeCache concurrent access`

---

## Phase 5: Documentation & Cleanup

**Goal**: Complete the work and document changes.  
**Dependencies**: Phase 4 complete (all tests pass)

### 5.1 Update Architecture Docs

- [ ] **Update `architecture/object-model.md`** (if exists)
  - [ ] Add NavTree to the object model diagram
  - [ ] Document NavTree ↔ Section relationship
- [ ] **Commit**: `docs(architecture): add NavTree to object model documentation`

### 5.2 Update Theme Development Guide

- [ ] **Update theme documentation** (if exists)
  - [ ] Document new `get_nav_tree(page)` API
  - [ ] Provide migration guide from direct Section access
  - [ ] Show before/after template examples
- [ ] **Commit**: `docs(themes): add NavTree migration guide for custom themes`

### 5.3 Changelog Entry

- [ ] **Update `changelog.md`**
  ```markdown
  ## [Unreleased]

  ### Added
  - NavTree: Pre-computed, cached navigation structure for O(1) template access
  - NavNode: Memory-efficient navigation node with dict-like Jinja access
  - NavTreeCache: Thread-safe per-version caching
  - Version-switching fallback cascade integrated into NavTree

  ### Changed
  - `get_nav_tree()` now returns NavTreeContext (backward compatible)
  - `docs-nav.html` simplified from 161 to ~50 lines

  ### Deprecated
  - `NavTreeItem` in favor of `NavNode` (removal in v2.0)
  ```
- [ ] **Commit**: `docs: add NavTree feature to changelog`

### 5.4 Cleanup

- [ ] **Delete planning files**
  - [ ] `rm plan/ready/rfc-navigation-tree-architecture.md` (after moving)
  - [ ] `rm plan/ready/plan-navigation-tree-architecture.md` (after moving)
- [ ] **Commit**: `chore: remove completed NavTree RFC and plan`

---

## Verification Checklist

Before marking complete, verify:

- [ ] `docs-nav.html` < 60 lines
- [ ] All unit tests pass: `pytest tests/unit/test_nav_tree.py -v`
- [ ] All integration tests pass: `pytest tests/integration/test_nav_tree_integration.py -v`
- [ ] Thread safety tests pass
- [ ] Benchmark shows <1ms per page render overhead
- [ ] Existing templates still work (backward compatibility)
- [ ] Versioned site navigation works (`bengal build` on test-versioned)
- [ ] Version switcher produces valid URLs
- [ ] Ruff passes: `ruff check bengal/core/nav_tree.py`
- [ ] Mypy passes: `mypy bengal/core/nav_tree.py`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Template regression | Phase 1 is non-breaking; existing templates work until Phase 3 |
| Cache invalidation bugs | Clear invalidation on `structural_changed`; test with file watcher |
| Thread contention | Lock held only for dict access, not tree building |
| Memory pressure | ~200 bytes per node; 1000 pages ≈ 200KB per version (acceptable) |
| Custom theme breakage | Preserve function signature; deprecation warning before removal |

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | 5 | 4-6 hours |
| Phase 2 | 3 | 2-3 hours |
| Phase 3 | 3 | 2-3 hours |
| Phase 4 | 4 | 3-4 hours |
| Phase 5 | 4 | 1-2 hours |
| **Total** | 19 | **12-18 hours** |

---

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Template simplicity | `docs-nav.html` < 60 lines | Line count |
| Render overhead | < 1ms per page | Benchmark |
| Cache hit rate | > 99% for same-version | Logging |
| Test coverage | > 90% for NavTree | pytest-cov |
| Backward compatibility | All existing templates work | Integration tests |
| Zero 404s on version switch | 100% valid URLs | Navigation audit |
