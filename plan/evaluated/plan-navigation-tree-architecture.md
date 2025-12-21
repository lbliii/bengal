# Plan: Navigation Tree Architecture Implementation

**Status**: Ready  
**Scope**: Core navigation model, caching, and theme simplification  
**RFC**: `plan/drafted/rfc-navigation-tree-architecture.md`  
**Confidence**: 92% 🟢

## Overview

This plan implements the `NavTree` abstraction to move navigation logic from Jinja templates into a pre-computed, cached Python structure. This improves build performance, simplifies theme development, and provides robust version-switching fallbacks.

## Phase 1: Core Navigation Model & Cache

**Goal**: Implement the foundational data structures and thread-safe caching.

- [ ] **Create `bengal/core/nav_tree.py`**
  - [ ] Implement `NavNode` with `__slots__` and dict-like access for Jinja.
  - [ ] Implement `NavTree` with `build()` logic (Section traversal, `_shared/` content).
  - [ ] Implement `NavTreeContext` for lightweight active trail marking.
  - [ ] Implement `NavTreeCache` with `threading.Lock` and site-level invalidation.
  - [ ] Implement `NavTree.get_target_url()` for version-switching fallback cascade.
- [ ] **Commit**: `core: introduce NavNode and NavTree models for version-aware navigation`
- [ ] **Commit**: `core: add thread-safe NavTreeCache with site-level invalidation`

## Phase 2: Template Function Integration

**Goal**: Update the rendering layer to use the new models while maintaining backward compatibility.

- [ ] **Update `bengal/rendering/template_functions/navigation/tree.py`**
  - [ ] Refactor `get_nav_tree(page)` to delegate to `NavTreeCache`.
  - [ ] Ensure `NavNode` attributes match expected keys in existing templates (`title`, `url`, `is_current`, `is_in_active_trail`).
- [ ] **Update `bengal/rendering/template_functions/navigation/models.py`**
  - [ ] Mark `NavTreeItem` as deprecated.
- [ ] **Commit**: `rendering(nav): adopt NavTreeCache in get_nav_tree; maintain backward compatibility`
- [ ] **Commit**: `rendering(nav): deprecate legacy NavTreeItem in favor of core.NavNode`

## Phase 3: Theme Optimization

**Goal**: Simplify the default theme templates and reduce logic boilerplate.

- [ ] **Refactor `site/themes/default/layouts/partials/docs-nav.html`** (or relevant path)
  - [ ] Remove ~100 lines of version-filtering and traversal logic.
  - [ ] Use `get_nav_tree(page)` and iterate over `nav.root.children`.
- [ ] **Commit**: `themes(docs): simplify navigation template using new NavTree API; reduce boilerplate`

## Phase 4: Validation & Testing

**Goal**: Ensure correctness, performance, and thread safety.

- [ ] **Add Unit Tests** (`tests/unit/test_nav_tree.py`)
  - [ ] Test `NavTree.build()` with `_shared/` content.
  - [ ] Test `NavTreeCache` concurrency and invalidation.
  - [ ] Test `get_target_url()` fallback logic (Cascade).
- [ ] **Add Integration Tests**
  - [ ] Verify `test-versioned` site navigation links.
- [ ] **Commit**: `tests(nav): add unit and integration tests for version-aware navigation`

## Cleanup

- [ ] Delete RFC and Plan files after implementation.
- [ ] Add entry to `changelog.md`.
