# RFC: Modularize virtual_orchestrator.py

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-12  
**Confidence**: 90% 🟢

---

## Problem Statement

`bengal/autodoc/virtual_orchestrator.py` is **~1987 lines** — nearly **5x Bengal's 400-line threshold**.

While the code is well-organized internally, the file size:
- Makes navigation difficult
- Slows IDE performance
- Violates Bengal's own architecture rules
- Bundles unrelated concerns (template env, section creation, page rendering, extraction)

---

## Current Structure Analysis

The file contains **42 methods** that cluster into clear responsibilities:

| Cluster | Methods | Lines | Description |
|---------|---------|-------|-------------|
| **Utils** | 3 | ~100 | Module-level helpers |
| **Result/Context** | 5 | ~90 | `AutodocRunResult`, `_PageContext` |
| **Template Env** | 4 | ~170 | Jinja2 environment setup |
| **Section Builders** | 4 | ~300 | Python/CLI/OpenAPI section creation |
| **Page Builders** | 8 | ~400 | Page creation, rendering, fallbacks |
| **Index Pages** | 3 | ~200 | Section index generation |
| **Extraction** | 3 | ~90 | Python/CLI/OpenAPI extraction wrappers |
| **Core Orchestrator** | 12 | ~350 | Main `generate()` and config handling |

---

## Proposed Package Structure

Convert `virtual_orchestrator.py` into a package:

```
bengal/autodoc/orchestration/
├── __init__.py              # Public API exports (~30 lines)
├── orchestrator.py          # Main VirtualAutodocOrchestrator (~350 lines)
├── result.py                # AutodocRunResult, _PageContext (~90 lines)
├── template_env.py          # Template environment builder (~170 lines)
├── section_builders.py      # Section creation for all doc types (~300 lines)
├── page_builders.py         # Page creation and rendering (~450 lines)
├── index_pages.py           # Section index page generation (~200 lines)
├── extractors.py            # Extraction wrappers (~90 lines)
└── utils.py                 # Shared utilities (~100 lines)
```

**Result**: 9 files averaging ~200 lines each (well under 400-line limit).

---

## Module Breakdown

### 1. `__init__.py` (~30 lines)
```python
"""Autodoc orchestration package."""
from bengal.autodoc.orchestration.orchestrator import VirtualAutodocOrchestrator
from bengal.autodoc.orchestration.result import AutodocRunResult

__all__ = ["VirtualAutodocOrchestrator", "AutodocRunResult"]
```

### 2. `result.py` (~90 lines)
- `AutodocRunResult` dataclass
- `_PageContext` class (lightweight page-like context for templates)

### 3. `utils.py` (~100 lines)
- `_get_template_dir_for_type()`
- `_normalize_autodoc_config()`
- `_format_source_file_for_display()`
- `_slugify()` (moved from orchestrator)

### 4. `template_env.py` (~170 lines)
- `AutodocTemplateEnvironment` class or builder function
- `_create_template_environment()`
- `_get_theme_templates_dir()`
- `_relativize_paths()` (error message helper)

### 5. `section_builders.py` (~300 lines)
- `create_python_sections()`
- `create_cli_sections()`
- `create_openapi_sections()`
- `create_aggregating_parent_sections()`

### 6. `page_builders.py` (~450 lines)
- `create_pages()`
- `find_parent_section()`
- `create_element_page()`
- `get_element_metadata()`
- `render_element()`
- `render_fallback()` and variants

### 7. `index_pages.py` (~200 lines)
- `create_index_pages()`
- `render_section_index()`
- `render_section_index_fallback()`

### 8. `extractors.py` (~90 lines)
- `extract_python()`
- `extract_cli()`
- `extract_openapi()`

### 9. `orchestrator.py` (~350 lines)
- `VirtualAutodocOrchestrator` class with:
  - `__init__`
  - `is_enabled()`
  - `generate()`
  - `generate_from_cache_payload()`
  - `get_cache_payload()`
  - `_check_prefix_overlaps()`
  - `_resolve_output_prefix()`
  - `_derive_openapi_prefix()`

---

## Migration Strategy

### Phase 1: Extract standalone modules (no behavior change)
1. Create `orchestration/` package
2. Move `AutodocRunResult` and `_PageContext` to `result.py`
3. Move utility functions to `utils.py`
4. Update imports in `virtual_orchestrator.py`

### Phase 2: Extract builders
1. Move section builders to `section_builders.py`
2. Move page builders to `page_builders.py`
3. Move index page logic to `index_pages.py`

### Phase 3: Extract template environment
1. Move template env creation to `template_env.py`
2. Possibly create `AutodocTemplateEnvironment` class

### Phase 4: Extract extraction wrappers
1. Move `_extract_*` methods to `extractors.py`

### Phase 5: Finalize orchestrator
1. Slim down `orchestrator.py` to coordination only
2. Delete original `virtual_orchestrator.py`
3. Update external imports

---

## Backward Compatibility

**Public API unchanged**:
```python
# Before
from bengal.autodoc.virtual_orchestrator import VirtualAutodocOrchestrator, AutodocRunResult

# After (both work via __init__.py re-exports)
from bengal.autodoc.orchestration import VirtualAutodocOrchestrator, AutodocRunResult
from bengal.autodoc import VirtualAutodocOrchestrator, AutodocRunResult  # Already works
```

The `bengal/autodoc/__init__.py` already re-exports these, so external code won't break.

---

## Testing Strategy

1. **No new tests needed initially** — existing 17 autodoc test files cover functionality
2. Run full test suite after each phase
3. Add unit tests for newly-exposed module functions if they become part of public API

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Import cycles | Medium | Careful dependency ordering; utils has no internal deps |
| Test regressions | Low | Comprehensive existing test coverage |
| Performance regression | Very Low | No algorithmic changes, just file reorganization |
| Merge conflicts | Medium | Do in single focused PR |

---

## Estimated Effort

| Phase | Files Changed | Time |
|-------|---------------|------|
| Phase 1: Standalone modules | 4 | 30 min |
| Phase 2: Builders | 5 | 45 min |
| Phase 3: Template env | 3 | 20 min |
| Phase 4: Extractors | 3 | 15 min |
| Phase 5: Finalize | 3 | 20 min |
| **Total** | **~9 new files** | **~2.5 hours** |

---

## Decision

**Recommended**: Proceed with modularization.

**Rationale**:
- File is 5x over threshold
- Clear logical boundaries exist
- Existing tests provide safety net
- No behavior changes required
- Improves maintainability significantly

---

## Open Questions

1. Should extracted modules use class methods or standalone functions?
   - **Recommendation**: Functions with explicit `site`/`config` parameters for testability

2. Should `_PageContext` become a public `AutodocPageContext`?
   - **Recommendation**: Keep private for now, only expose if needed externally

3. Should we add a deprecation warning for direct `virtual_orchestrator` imports?
   - **Recommendation**: Not needed — `autodoc/__init__.py` already provides stable API
