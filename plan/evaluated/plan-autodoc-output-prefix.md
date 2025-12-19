# Plan: Separate Output Paths for Autodoc Types

**RFC**: `rfc-autodoc-output-prefix.md`  
**Status**: Draft  
**Created**: 2025-12-11  
**Estimated Time**: 3-4 hours

---

## Summary

Implement configurable `output_prefix` options for Python, OpenAPI, and CLI autodoc types. This enables each documentation type to occupy distinct URL namespaces, resolving navigation conflicts when multiple autodoc types are enabled simultaneously.

---

## Prerequisites

- [ ] RFC reviewed and approved (Confidence: 88%)
- [ ] No blocking issues in Open Questions

---

## Tasks

### Phase 1: Configuration

#### Task 1.1: Add `output_prefix` defaults to config.py

- **Files**: `bengal/autodoc/config.py`
- **Action**: Add `output_prefix` key to each autodoc type's default config
- **Details**:
  ```python
  "python": {
      "output_prefix": "api/python",  # NEW
      ...
  },
  "openapi": {
      "output_prefix": "",  # NEW - empty = auto-derive
      ...
  },
  "cli": {
      "output_prefix": "cli",  # NEW (was implicit)
      ...
  },
  ```
- **Commit**: `autodoc(config): add output_prefix defaults for python, openapi, cli`

---

### Phase 2: Prefix Resolution

#### Task 2.1: Add `_slugify()` helper method

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Add private method to convert text to URL-friendly slugs
- **Details**:
  - Strip common suffixes (api, reference, documentation)
  - Convert to lowercase, replace non-alphanum with hyphens
  - Return "rest" as fallback for empty results
- **Commit**: `autodoc: add _slugify() helper for URL-friendly slug generation`

#### Task 2.2: Add `_derive_openapi_prefix()` method

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Add method to derive prefix from OpenAPI spec title
- **Details**:
  - Load spec file (if exists)
  - Extract `info.title`
  - Slugify and prepend `api/`
  - Fallback to `api/rest` if unavailable
- **Depends on**: Task 2.1
- **Commit**: `autodoc: add _derive_openapi_prefix() for auto-detection from spec title`

#### Task 2.3: Add `_resolve_output_prefix()` method

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Add central method to resolve output prefix for any doc type
- **Details**:
  - Check explicit config value first
  - For openapi: call `_derive_openapi_prefix()`
  - For python: return `api/python`
  - For cli: return `cli`
- **Depends on**: Task 2.2
- **Commit**: `autodoc: add _resolve_output_prefix() for unified prefix resolution`

---

### Phase 3: Section Creation Updates

#### Task 3.1: Update `_create_python_sections()` to use prefix

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Modify Python section creation to use resolved prefix
- **Details**:
  - Call `_resolve_output_prefix("python")` at start
  - Create root section at prefix path (not hardcoded "api")
  - Update subsection paths to use prefix
  - Update section dict keys to include prefix
- **Depends on**: Task 2.3
- **Commit**: `autodoc(python): use configurable output_prefix for section creation`

#### Task 3.2: Update `_create_openapi_sections()` to use prefix

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Modify OpenAPI section creation to use resolved prefix
- **Details**:
  - Call `_resolve_output_prefix("openapi")` at start
  - **Remove** existing section reuse logic (lines 754-770)
  - Always create new section at prefix path
  - Update subsection paths (schemas, tags, endpoints)
- **Depends on**: Task 2.3
- **Commit**: `autodoc(openapi): use configurable output_prefix; remove section reuse`

#### Task 3.3: Update `_create_cli_sections()` to use prefix

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Modify CLI section creation to use resolved prefix
- **Details**:
  - Call `_resolve_output_prefix("cli")` at start
  - Use prefix instead of hardcoded "cli"
- **Depends on**: Task 2.3
- **Commit**: `autodoc(cli): use configurable output_prefix for section creation`

---

### Phase 4: Path Generation Updates

#### Task 4.1: Update `_get_element_metadata()` to use prefix

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Modify URL path generation to include resolved prefix
- **Details**:
  - Call `_resolve_output_prefix(doc_type)` for each type
  - Update URL path construction for:
    - Python modules: `{prefix}/{module_path}`
    - CLI commands: `{prefix}/{cmd_path}`
    - OpenAPI overview: `{prefix}/overview`
    - OpenAPI schemas: `{prefix}/schemas/{name}`
    - OpenAPI endpoints: `{prefix}/endpoints/{method}-{path}`
- **Depends on**: Task 2.3
- **Commit**: `autodoc: update _get_element_metadata() to use resolved prefix in URLs`

---

### Phase 5: Overlap Detection

#### Task 5.1: Add prefix overlap warning

- **Files**: `bengal/autodoc/virtual_orchestrator.py`
- **Action**: Emit warning when Python and OpenAPI share same prefix
- **Details**:
  - After resolving prefixes for both types
  - Check if prefixes overlap (e.g., both start with "api/")
  - Log warning: "Python and OpenAPI autodoc share prefix 'api/'. Consider distinct output_prefix values."
- **Depends on**: Task 2.3
- **Commit**: `autodoc: add warning for overlapping output_prefix values`

---

### Phase 6: Unit Tests

#### Task 6.1: Add tests for `_slugify()`

- **Files**: `tests/unit/autodoc/test_virtual_orchestrator.py`
- **Action**: Add comprehensive edge case tests for slugification
- **Details**:
  - Empty/whitespace → "rest"
  - Suffix stripping (API, Reference, Documentation)
  - Special characters
  - Long titles
  - Unicode handling
- **Depends on**: Task 2.1
- **Commit**: `tests(autodoc): add unit tests for _slugify() edge cases`

#### Task 6.2: Add tests for `_derive_openapi_prefix()`

- **Files**: `tests/unit/autodoc/test_virtual_orchestrator.py`
- **Action**: Add tests for OpenAPI prefix auto-derivation
- **Details**:
  - Spec with title → `api/{slug}`
  - Missing spec file → `api/rest`
  - Missing title → `api/rest`
  - Invalid YAML → `api/rest`
- **Depends on**: Task 2.2
- **Commit**: `tests(autodoc): add unit tests for _derive_openapi_prefix()`

#### Task 6.3: Add tests for `_resolve_output_prefix()`

- **Files**: `tests/unit/autodoc/test_virtual_orchestrator.py`
- **Action**: Add tests for prefix resolution logic
- **Details**:
  - Explicit config → use as-is
  - Empty config → default for type
  - OpenAPI auto-derive
  - Python/CLI static defaults
- **Depends on**: Task 2.3
- **Commit**: `tests(autodoc): add unit tests for _resolve_output_prefix()`

---

### Phase 7: Integration Tests

#### Task 7.1: Add test for separate section trees

- **Files**: `tests/integration/autodoc/test_output_prefix.py` (new)
- **Action**: Verify Python and OpenAPI create distinct nav sections
- **Details**:
  - Build site with both autodocs enabled
  - Verify `/api/python/` section exists
  - Verify `/api/{slug}/` section exists
  - Verify sections are distinct objects
- **Depends on**: Phase 4
- **Commit**: `tests(autodoc): add integration test for separate section trees`

#### Task 7.2: Add test for backwards compatibility

- **Files**: `tests/integration/autodoc/test_output_prefix.py`
- **Action**: Verify single-type configs work unchanged
- **Details**:
  - Python-only with `output_prefix: "api"` → same URLs as before
  - OpenAPI-only with `output_prefix: "api"` → same URLs as before
- **Depends on**: Phase 4
- **Commit**: `tests(autodoc): add backwards compatibility test for output_prefix`

---

### Phase 8: Documentation

#### Task 8.1: Update autodoc README

- **Files**: `bengal/autodoc/README.md` (if exists) or inline docs
- **Action**: Document `output_prefix` configuration option
- **Details**:
  - Add to config reference table
  - Include examples for customization
  - Document auto-derivation behavior for OpenAPI
- **Depends on**: Phase 4
- **Commit**: `docs(autodoc): document output_prefix configuration option`

#### Task 8.2: Update site config example

- **Files**: `site/config/_default/autodoc.yaml`
- **Action**: Add `output_prefix` examples to Bengal's own config
- **Details**:
  - Show commented examples
  - Demonstrate auto-derive for OpenAPI
- **Depends on**: Phase 4
- **Commit**: `docs(site): add output_prefix examples to autodoc.yaml`

---

## Validation Checklist

### Phase 9: Final Validation

- [ ] All unit tests pass: `pytest tests/unit/autodoc/`
- [ ] All integration tests pass: `pytest tests/integration/autodoc/`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Linter passes: `ruff check bengal/autodoc/`
- [ ] Type checker passes: `mypy bengal/autodoc/`
- [ ] Dogfood: Bengal's own site builds correctly with both autodocs

---

## Task Summary

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| 1. Configuration | 1 task | 10 min |
| 2. Prefix Resolution | 3 tasks | 30 min |
| 3. Section Creation | 3 tasks | 45 min |
| 4. Path Generation | 1 task | 20 min |
| 5. Overlap Detection | 1 task | 10 min |
| 6. Unit Tests | 3 tasks | 30 min |
| 7. Integration Tests | 2 tasks | 30 min |
| 8. Documentation | 2 tasks | 15 min |
| 9. Validation | - | 20 min |
| **Total** | **16 tasks** | **~3.5 hours** |

---

## Changelog Entry

```markdown
### Added
- **Autodoc**: Configurable `output_prefix` for Python, OpenAPI, and CLI documentation
  - Python defaults to `/api/python/`
  - OpenAPI auto-derives from spec title (e.g., `/api/commerce/`)
  - CLI remains at `/cli/`
- **Autodoc**: Warning when multiple autodoc types share overlapping prefixes

### Changed
- **Autodoc (OpenAPI)**: No longer reuses existing API section from Python autodoc; creates separate section tree

### Migration
- Existing sites using both Python and OpenAPI autodoc will see URL changes
- To preserve existing URLs: set `output_prefix: "api"` for both types
```

---

## Rollback Plan

If issues are discovered post-implementation:

1. Revert commits in reverse order
2. All changes are isolated to `bengal/autodoc/` and tests
3. No database migrations or external dependencies

---

## Dependencies

- **External**: None (uses stdlib `re`, existing `yaml` dependency)
- **Internal**: `bengal/core/section.py` (unchanged, just used)

---

## Open Items

- [ ] Decide: Should we emit deprecation warning for shared `/api/` prefix? (RFC says yes)
- [ ] Decide: Add `output_prefix` to CLI help output?
