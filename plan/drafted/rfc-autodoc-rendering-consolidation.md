# RFC: Consolidate Autodoc Rendering Paths

**Status**: Draft
**Author**: AI Assistant
**Created**: 2025-12-19
**Category**: Architecture / Refactoring

---

## Executive Summary

Bengal's autodoc system currently has **three separate rendering paths** that must all be kept in sync for template context (versioning, menus, etc.). This RFC proposes consolidating to a single rendering path to reduce maintenance burden and prevent bugs like the recent `current_version` undefined error.

---

## Problem Statement

### Current Architecture

Autodoc pages are rendered through three different code paths:

| # | Location | Function | When Called |
|---|----------|----------|-------------|
| 1 | `bengal/autodoc/orchestration/page_builders.py` | `render_element()` | Never used in current flow (dead code?) |
| 2 | `bengal/autodoc/orchestration/index_pages.py` | `render_section_index()` | Never used in current flow (dead code?) |
| 3 | `bengal/rendering/pipeline/core.py` | `_render_autodoc_page()` | **Main path** - renders all autodoc pages |

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

### Call Graph Analysis

**`page_builders.render_element()`**:
- Defined at line 303
- NOT imported by `orchestrator.py` (only `create_pages`, `find_parent_section`, `get_element_metadata` are imported)
- NOT called anywhere in the codebase
- **Verdict**: Dead code

**`index_pages.render_section_index()`**:
- Defined at line 98
- `create_index_pages()` is imported and used, but `render_section_index()` is NOT
- NOT called anywhere in the codebase
- **Verdict**: Dead code

**`_render_autodoc_page()`**:
- Called from `_process_virtual_page()` when `page.metadata.get("is_autodoc")` is True
- This is the ONLY path that actually renders autodoc pages
- **Verdict**: Active code path

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

### Phase 1: Verification (30 min)

1. Add test that confirms `render_element()` and `render_section_index()` are not called during a full site build
2. Grep entire codebase for any remaining references

### Phase 2: Removal (30 min)

1. Delete `render_element()` function (lines 303-396 in `page_builders.py`)
2. Delete `render_fallback()`, `render_fallback_class()`, `render_fallback_function()` (lines 399-444)
3. Delete `render_section_index()` function (lines 98-162 in `index_pages.py`)
4. Delete `render_section_index_fallback()` function (lines 165-254)
5. Remove unused imports

### Phase 3: Documentation (15 min)

1. Update `bengal/autodoc/README.md` to clarify the single rendering path
2. Add code comment in `_render_autodoc_page()` explaining it's the only rendering path

### Phase 4: Verification (15 min)

1. Run full test suite
2. Build site/ and verify no regressions

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

| File | Lines | Function |
|------|-------|----------|
| `bengal/autodoc/orchestration/page_builders.py` | 303-444 | `render_element()` + fallbacks |
| `bengal/autodoc/orchestration/index_pages.py` | 98-254 | `render_section_index()` + fallback |
| `bengal/rendering/pipeline/core.py` | 620-703 | `_render_autodoc_page()` (keep) |

---

## Related

- **Issue**: `'current_version' is undefined` in autodoc templates
- **Commits**:
  - `autodoc: add versioning context to template env and render calls`
  - `rendering(pipeline): add versioning context to _render_autodoc_page`
- **Architecture**: `bengal/autodoc/README.md` - Build Lifecycle section
