# Test Coverage and Logging Gaps - Swizzle & Component Preview

**Date**: October 11, 2025
**Status**: Analysis complete, gaps identified

## Summary

**Swizzle Feature**: ⚠️ Partial coverage (basic tests exist, logging minimal)
**Component Preview**: ❌ No test coverage, minimal logging

## 1. Swizzle Feature - Test Coverage

### Existing Tests ✅
Location: `tests/unit/theme/test_swizzle.py` (4 tests)

1. ✅ `test_swizzle_copy_and_registry` - Basic copy and registry creation
2. ✅ `test_swizzle_update_skips_when_local_changed` - Update with local changes
3. ✅ `test_swizzle_update_overwrites_when_local_unchanged` - Update without local changes
4. ✅ `test_swizzle_cli_invocation` - CLI command invocation

### Missing Tests ❌

#### Error Handling Tests
- ❌ Template not found in theme
- ❌ Invalid template path (path traversal)
- ❌ Permission denied writing to templates/
- ❌ Corrupted registry JSON
- ❌ Invalid checksum in registry
- ❌ File encoding errors (non-UTF-8)

#### Edge Case Tests
- ❌ Swizzle same template twice (should replace)
- ❌ Swizzle with no theme configured
- ❌ Swizzle with missing theme directory
- ❌ Update with missing local file
- ❌ Update with missing upstream file (fallback to theme resolution)
- ❌ List with empty registry
- ❌ List with corrupted records

#### Integration Tests
- ❌ Swizzle across theme inheritance chain
- ❌ Swizzle with bundled theme vs local theme
- ❌ Update with theme migration (theme changed)
- ❌ CLI swizzle-list output format
- ❌ CLI swizzle-update summary output

#### Checksum Tests
- ❌ Checksum mismatch detection
- ❌ Binary file handling (should fail gracefully)
- ❌ Large file checksumming

### Test Coverage Estimate
- **Current**: ~40% (happy paths only)
- **Target**: 85%+ (with error handling and edge cases)

## 2. Swizzle Feature - Logging

### Existing Logging ✅
- ✅ `logger.info("swizzle_copied")` - Successful copy
- ✅ `logger.warning("swizzle_resolve_failed")` - Template resolution failure

### Missing Logging ❌
- ❌ Swizzle start (what template, what theme)
- ❌ Update start (how many records to check)
- ❌ Update skip reasons (local changed, missing upstream)
- ❌ Update success per file
- ❌ Registry load/save operations
- ❌ Checksum computation
- ❌ File I/O errors (read/write)
- ❌ Permission errors
- ❌ List operation (how many swizzled files)
- ❌ Re-swizzle detection (overwriting existing)

### Logging Severity Issues
- ⚠️ Silent failures in `list()` (line 85: bare `except Exception`)
- ⚠️ Silent failures in `_load_registry()` (line 162: bare `except Exception`)
- ⚠️ No error context when FileNotFoundError raised (line 56)

## 3. Component Preview - Test Coverage

### Existing Tests ❌
**NONE** - Zero test coverage

### Required Tests (Priority Order)

#### Unit Tests - `test_component_preview.py`
1. ❌ `test_discover_components_empty` - No manifests found
2. ❌ `test_discover_components_single` - Single component with variants
3. ❌ `test_discover_components_multiple` - Multiple components
4. ❌ `test_discover_components_theme_override` - Child theme overrides parent
5. ❌ `test_discover_components_invalid_yaml` - Malformed YAML handling
6. ❌ `test_discover_components_missing_template` - Manifest without template key
7. ❌ `test_render_component_basic` - Render with context
8. ❌ `test_render_component_css_fingerprinting` - CSS URL resolution (our bug fix!)
9. ❌ `test_render_component_page_to_article_alias` - Context aliasing
10. ❌ `test_list_page_empty` - Gallery with no components
11. ❌ `test_list_page_with_components` - Gallery with components
12. ❌ `test_view_page_not_found` - Component doesn't exist
13. ❌ `test_view_page_single_variant` - Render specific variant
14. ❌ `test_view_page_all_variants` - Render all variants
15. ❌ `test_component_manifest_dirs_theme_chain` - Theme inheritance

#### Integration Tests - `test_component_preview_server.py`
1. ❌ `test_component_preview_endpoint` - HTTP GET /__bengal_components__/
2. ❌ `test_component_view_endpoint` - HTTP GET /__bengal_components__/view?c=card
3. ❌ `test_component_variant_endpoint` - HTTP GET with variant parameter
4. ❌ `test_component_preview_live_reload` - LiveReload injection
5. ❌ `test_component_preview_404` - Invalid component ID

### Test Coverage Estimate
- **Current**: 0%
- **Target**: 80%+ (core functionality covered)

## 4. Component Preview - Logging

### Existing Logging ✅
- ✅ `logger.warning("component_manifest_load_failed")` - YAML load error

### Missing Logging ❌

#### Discovery Phase
- ❌ Discovery start (how many dirs to scan)
- ❌ Manifests found per directory
- ❌ Duplicate component IDs (which one wins)
- ❌ Missing template field in manifest
- ❌ Invalid variant structure
- ❌ Discovery summary (total components, total variants)

#### Rendering Phase
- ❌ Component render start
- ❌ Template resolution (which template used)
- ❌ Context aliasing (page → article)
- ❌ Asset URL resolution (CSS fingerprinting)
- ❌ Render errors (template syntax, missing variables)
- ❌ Render success (duration, size)

#### Server Phase
- ❌ Component preview request (path, query params)
- ❌ Gallery page generation
- ❌ View page generation
- ❌ 404 for missing components
- ❌ Performance metrics (discovery time, render time)

### Logging Severity Issues
- ⚠️ Silent template resolution failure (no logging in `_component_manifest_dirs`)
- ⚠️ No error logging in `render_component` (template errors)
- ⚠️ No logging for HTTP request handling in `request_handler.py`

## 5. Integration with Existing Test Infrastructure

### Test Fixtures Needed
```python
# tests/fixtures/component_previews/
- manifests/
  - card.yaml
  - button.yaml
  - invalid.yaml
- templates/partials/
  - card.html
  - button.html
```

### Pytest Fixtures
```python
@pytest.fixture
def component_site(tmp_path):
    """Site with component manifests for testing"""

@pytest.fixture
def swizzle_site(tmp_path):
    """Site with theme templates for swizzle testing"""
```

## 6. Logging Best Practices to Apply

### Structured Logging Format
```python
# Good
logger.info("swizzle_start",
           template=template_path,
           theme=theme_name,
           source=str(source_path))

# Bad (current)
logger.info(f"Swizzling {template_path}")
```

### Consistent Event Names
- Use snake_case: `component_discovered`, not `componentDiscovered`
- Use past tense for completed actions: `swizzle_copied`, not `swizzle_copy`
- Use present continuous for ongoing: `discovering_components`

### Context Fields to Include
- **What**: Action being performed
- **Where**: File paths, component IDs
- **Who**: Theme name, component name
- **How**: Method, source
- **Result**: Success/failure, counts, duration

## 7. Priority Implementation Plan

### Phase 1: Critical Gaps (1-2 hours)
1. ✅ Add logging to swizzle.py (all operations)
2. ✅ Add logging to component_preview.py (discovery & render)
3. ✅ Create test_component_preview.py with 10 core tests
4. ✅ Add error handling tests for swizzle

### Phase 2: Comprehensive Coverage (2-3 hours)
1. Add integration tests for component preview server
2. Add edge case tests for swizzle
3. Add performance/stress tests
4. Add test fixtures and helper utilities

### Phase 3: Polish (1 hour)
1. Add test documentation
2. Update CONTRIBUTING.md with test guidelines
3. Add CI coverage reporting
4. Document logging format in ARCHITECTURE.md

## 8. Specific Code Issues to Fix

### Swizzle Silent Failures
```python
# Line 85: bengal/utils/swizzle.py
except Exception:
    continue  # SILENT FAILURE!

# Should be:
except Exception as e:
    logger.error("swizzle_record_invalid", record=rec, error=str(e))
    continue
```

### Component Preview Error Handling
```python
# Line 97-111: bengal/server/component_preview.py
def view_page(self, comp_id: str, variant_id: Optional[str]) -> str:
    comps = {c.get("id"): c for c in self.discover_components()}
    comp = comps.get(comp_id)
    if not comp:
        return f"<h1>Not found</h1><p>Component '{comp_id}' not found.</p>"
    # NO LOGGING of 404!

# Should log:
if not comp:
    logger.warning("component_not_found",
                  component_id=comp_id,
                  available=list(comps.keys()))
    return f"<h1>Not found</h1>..."
```

### Request Handler Logging
```python
# bengal/server/request_handler.py line 92-99
except Exception as e:
    logger.error("component_preview_failed",
                error=str(e),
                error_type=type(e).__name__)
    # Good error logging exists!
    # But missing: path, query params, user context
```

## 9. Coverage Metrics Goals

### Before
```
swizzle.py          40%  (basic paths only)
component_preview.py  0%  (no tests)
```

### After Phase 1
```
swizzle.py          75%  (+ error handling, edge cases)
component_preview.py 60%  (core functionality)
```

### After Phase 2
```
swizzle.py          90%  (comprehensive)
component_preview.py 85%  (integration tests)
```

## 10. Test Automation

### Run Tests
```bash
# Run swizzle tests
pytest tests/unit/theme/test_swizzle.py -v

# Run component preview tests (after creation)
pytest tests/unit/server/test_component_preview.py -v

# Run with coverage
pytest --cov=bengal.utils.swizzle --cov=bengal.server.component_preview --cov-report=html
```

### CI Integration
```yaml
# Add to .github/workflows/test.yml
- name: Test Swizzle & Component Preview
  run: |
    pytest tests/unit/theme/test_swizzle.py --cov
    pytest tests/unit/server/test_component_preview.py --cov
```

## Conclusion

**Swizzle**: Needs better logging and error handling tests
**Component Preview**: Needs everything (tests + logging)

Both features are production-ready in terms of functionality, but need better observability and reliability through comprehensive testing and logging.
