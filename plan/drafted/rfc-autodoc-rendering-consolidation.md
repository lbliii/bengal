# RFC: Consolidate Autodoc Rendering Paths

**Status**: Evaluated ✅  
**Confidence**: 94% 🟢  
**Author**: AI Assistant  
**Created**: 2025-12-19  
**Evaluated**: 2025-12-19  
**Category**: Architecture / Refactoring

---

## Executive Summary

Bengal's autodoc system currently has **three separate rendering paths** that must all be kept in sync for template context (versioning, menus, etc.). This RFC proposes consolidating to a single rendering path to reduce maintenance burden and prevent bugs like the recent `current_version` undefined error.

**Recommendation**: Remove dead code (Option A) — ~300 lines, 1-2 hours effort, low risk.

---

## Problem Statement

### Current Architecture

Autodoc pages are rendered through three different code paths:

| # | Location | Function | Status |
|---|----------|----------|--------|
| 1 | `bengal/autodoc/orchestration/page_builders.py:303` | `render_element()` | ❌ Dead code (verified) |
| 2 | `bengal/autodoc/orchestration/index_pages.py:98` | `render_section_index()` | ❌ Dead code (verified) |
| 3 | `bengal/rendering/pipeline/core.py:620` | `_render_autodoc_page()` | ✅ Active - only rendering path |

### Evidence of the Problem

When versioning was added, `current_version` and `is_latest_version` had to be added to all three paths. The main rendering path (#3) was initially missed, causing 200+ template render failures:

```
autodoc_template_render_failed error='current_version' is undefined
```

Fixed in commit: `rendering(pipeline): add versioning context to _render_autodoc_page`

### Why Three Paths Exist

Historical evolution:

1. **Original Design**: `render_element()` and `render_section_index()` were intended to render HTML during the autodoc discovery phase.

2. **Deferred Rendering Refactor**: A later refactor introduced "deferred rendering" - autodoc pages are created without HTML during discovery, then rendered by the main pipeline after menus are built. This ensures autodoc pages have full navigation context.

3. **Result**: The original autodoc rendering functions (`render_element`, `render_section_index`) are now effectively dead code. The README documents the new flow:

```
Build Lifecycle (Deferred Rendering):

1. Discovery Phase (Phase 5)
   ├─ Extract DocElements from source (Python, CLI, OpenAPI)
   ├─ Create virtual Page objects with element metadata
   └─ Store DocElement on page (NO HTML rendering yet)

2. Menu Building Phase (Phase 9)
   └─ site.menu populated with navigation

3. Rendering Phase (Phase 14)
   ├─ RenderingPipeline detects autodoc pages (is_autodoc=True)
   ├─ Calls _render_autodoc_page() with FULL template context
   └─ HTML written to output
```

---

## Evidence Analysis

### Call Graph Analysis (Verified)

**`page_builders.render_element()`** — ❌ DEAD CODE:
- Defined at `page_builders.py:303-396`
- Imports from `page_builders` in `orchestrator.py:26-29`:
  ```python
  from bengal.autodoc.orchestration.page_builders import (
      create_pages,
      find_parent_section,
      get_element_metadata,
  )
  ```
- `render_element` is NOT imported anywhere in codebase
- NOT called anywhere in tests (`grep` returns 0 matches)
- Internal helpers (`render_fallback`, `render_fallback_class`, `render_fallback_function`) are only called within `render_element()` itself

**`index_pages.render_section_index()`** — ❌ DEAD CODE:
- Defined at `index_pages.py:98-162`
- Import from `index_pages` in `orchestrator.py:25`:
  ```python
  from bengal.autodoc.orchestration.index_pages import create_index_pages
  ```
- `render_section_index` is NOT imported anywhere in codebase
- NOT called anywhere in tests (`grep` returns 0 matches)
- Internal helper `render_section_index_fallback()` is only called within `render_section_index()` itself

**`_render_autodoc_page()`** — ✅ ACTIVE:
- Defined at `core.py:620-706`
- Called from `_process_virtual_page()` when `page.metadata.get("is_autodoc")` is True
- This is the ONLY path that actually renders autodoc pages
- Has full template context including menus, active states, versioning

### Duplicate Template Context

All three functions must maintain identical template context. Compare:

**`page_builders.py:366-374`**:
```python
render_context = {
    "element": element_data,
    "page": page_context,
    "config": normalized_config,
    "site": site,
    "current_version": None,
    "is_latest_version": True,
}
```

**`index_pages.py:129-137`**:
```python
render_context = {
    "section": section,
    "page": page_context,
    "config": config,
    "site": site,
    "current_version": None,
    "is_latest_version": True,
}
```

**`core.py:668-679`**:
```python
html_content = template.render(
    element=element,
    page=page,
    section=section,
    site=self.site,
    config=self._normalize_config(self.site.config),
    toc_items=getattr(page, "toc_items", []) or [],
    toc=getattr(page, "toc", "") or "",
    current_version=None,
    is_latest_version=True,
)
```

---

## Validation Summary

### Claims Verified ✅

| Claim | Verification Method | Result |
|-------|---------------------|--------|
| `render_element()` not imported | `grep 'from.*page_builders.*import'` | Only `create_pages`, `find_parent_section`, `get_element_metadata` imported |
| `render_element()` not called | `grep 'render_element'` in `bengal/` | Only definition found (line 303) |
| `render_section_index()` not imported | `grep 'from.*index_pages.*import'` | Only `create_index_pages` imported |
| `render_section_index()` not called | `grep 'render_section_index'` in `bengal/` | Only definitions found (lines 98, 162, 165) |
| Fallback functions are internal | `grep 'render_fallback\('` in `bengal/` | Only called within `render_element()` |
| No test references | `grep` in `tests/` | 0 matches for either function |
| README documents deferred rendering | Manual inspection | `bengal/autodoc/README.md:83-103` confirms |

### Confidence Score: 94% 🟢

| Component | Score | Notes |
|-----------|-------|-------|
| Evidence Strength | 40/40 | Direct code matches with file:line references |
| Consistency | 28/30 | All evidence agrees across codebase |
| Recency | 15/15 | Based on current codebase state |
| Test Coverage | 11/15 | No tests reference functions, but no tests explicitly confirming removal is safe |

---

## Options

### Option A: Remove Dead Code (Recommended)

**Action**: Delete `render_element()` and `render_section_index()` since they're never called.

**Pros**:
- Simple, low-risk change
- Eliminates maintenance burden of keeping 3 paths in sync
- Makes architecture clearer

**Cons**:
- None significant

**Effort**: Low (1-2 hours)

### Option B: Consolidate All Rendering into Pipeline

**Action**: Move all autodoc rendering logic into `RenderingPipeline._render_autodoc_page()`. Delete the autodoc orchestration rendering functions.

**Pros**:
- Single source of truth for rendering
- Clear separation: autodoc orchestration handles extraction/structure, pipeline handles rendering

**Cons**:
- Slightly larger diff
- Need to ensure all fallback logic is preserved

**Effort**: Medium (half day)

### Option C: Extract Shared Rendering Module

**Action**: Create `bengal/autodoc/orchestration/rendering.py` that both the pipeline and autodoc orchestration import from.

**Pros**:
- DRY principle for template context building
- Could enable pre-rendering if ever needed again

**Cons**:
- Adds abstraction layer
- More complex than just removing dead code

**Effort**: Medium (half day)

---

## Recommendation

**Implement Option A (Remove Dead Code)** as the immediate fix.

The functions `render_element()` and `render_section_index()` are dead code that adds confusion and maintenance burden. The deferred rendering architecture is correct - autodoc pages should be rendered by the main pipeline where full site context is available.

### Rationale

1. **Code evidence**: Neither function is imported or called anywhere
2. **Architecture intent**: README explicitly documents deferred rendering as the design
3. **Risk mitigation**: Removing unused code can't break anything
4. **Simplicity**: Less code = less to maintain = fewer bugs like the versioning issue

---

## Implementation Plan

### Phase 1: Pre-Removal Verification ✅ (Complete)

Verification already performed during RFC evaluation:

```bash
# Confirm no imports of render_element
grep -r "from.*page_builders.*import" bengal/
# Result: Only create_pages, find_parent_section, get_element_metadata

# Confirm no imports of render_section_index
grep -r "from.*index_pages.*import" bengal/
# Result: Only create_index_pages

# Confirm no test references
grep -r "render_element\|render_section_index" tests/
# Result: 0 matches
```

### Phase 2: Removal (30 min)

**`bengal/autodoc/orchestration/page_builders.py`** — Remove ~140 lines:

| Function | Lines | Notes |
|----------|-------|-------|
| `render_element()` | 303-396 | Main dead function |
| `render_fallback()` | 399-425 | Helper, only called by `render_element()` |
| `render_fallback_class()` | 427-435 | Helper, only called by `render_fallback()` |
| `render_fallback_function()` | 437-444 | Helper, only called by `render_fallback()` |

**`bengal/autodoc/orchestration/index_pages.py`** — Remove ~156 lines:

| Function | Lines | Notes |
|----------|-------|-------|
| `render_section_index()` | 98-162 | Main dead function |
| `render_section_index_fallback()` | 165-254 | Helper, only called by `render_section_index()` |

**Unused imports to remove**:
- Check for orphaned imports after function removal (e.g., `PageContext` if only used in deleted code)

### Phase 3: Documentation (15 min)

1. Update `bengal/autodoc/README.md` Build Lifecycle section to explicitly note:
   > "All autodoc rendering occurs via `RenderingPipeline._render_autodoc_page()` — this is the single rendering path."
2. Add docstring comment in `_render_autodoc_page()`:
   ```python
   """
   Render an autodoc page using the site's template engine.

   NOTE: This is the ONLY rendering path for autodoc pages. The deferred
   rendering architecture ensures full template context (menus, active states,
   versioning) is available. See bengal/autodoc/README.md for details.
   """
   ```

### Phase 4: Post-Removal Verification (15 min)

```bash
# Run full test suite
pytest tests/ -v

# Build site and verify
cd site && bengal build

# Confirm no references remain
grep -r "render_element\|render_section_index" bengal/
# Expected: 0 matches
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Someone is using render_element() externally | Very Low | Low | Search GitHub/PyPI for usage |
| Fallback rendering is needed | Low | Medium | Keep fallback logic in `_render_autodoc_page()` |
| Future need for pre-rendering | Low | Low | Can be re-implemented if needed |

---

## Success Criteria

- [ ] No `render_element()` or `render_section_index()` in codebase
- [ ] All tests pass
- [ ] Site builds successfully with no template errors
- [ ] Reduced lines of code in autodoc orchestration (~300 lines removed)

---

## Alternative Considered: Keep for Testing

One might argue these functions are useful for unit testing autodoc rendering in isolation. However:

1. The functions don't match the actual rendering path (missing template engine setup, menu context, etc.)
2. Tests should test what users experience - the full pipeline
3. Current tests in `test_virtual_page_rendering.py` already test the real path

---

## Appendix: File Locations

### Files to Modify

| File | Lines to Remove | Function(s) | Action |
|------|-----------------|-------------|--------|
| `bengal/autodoc/orchestration/page_builders.py` | 303-444 (~140) | `render_element()`, `render_fallback*()` | Delete |
| `bengal/autodoc/orchestration/index_pages.py` | 98-254 (~156) | `render_section_index*()` | Delete |
| `bengal/rendering/pipeline/core.py` | N/A | `_render_autodoc_page()` | Add comment |
| `bengal/autodoc/README.md` | N/A | Build Lifecycle section | Clarify |

### Suggested Commit Message

```
autodoc: remove dead rendering functions; consolidate to single path

- Delete render_element() + fallback helpers from page_builders.py (~140 lines)
- Delete render_section_index() + fallback from index_pages.py (~156 lines)
- Document _render_autodoc_page() as the single rendering path
- Eliminates sync burden that caused 'current_version' undefined errors

These functions became dead code after the deferred rendering refactor.
All autodoc pages now render via RenderingPipeline._render_autodoc_page().
```

---

## Related

- **Issue**: `'current_version' is undefined` in autodoc templates (200+ failures)
- **Commits**:
  - `autodoc: add versioning context to template env and render calls`
  - `rendering(pipeline): add versioning context to _render_autodoc_page`
- **Architecture**: `bengal/autodoc/README.md:83-103` - Build Lifecycle (Deferred Rendering)
- **Active Rendering Path**: `bengal/rendering/pipeline/core.py:620-706`
