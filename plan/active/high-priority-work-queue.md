# High Priority Work Queue

**Date**: 2025-12-01  
**Status**: Active  
**Source**: Codebase analysis

---

## Executive Summary

Analysis found **1 critical bug** (fixed), **test configuration issues**, **deprecation cleanup needed**, and **remaining large files**.

---

## 🔴 Priority 1: Critical (Fixed)

### ✅ Undefined `page` Variable in Parallel Rendering
**Location**: `bengal/orchestration/render.py:316, 443`  
**Status**: ✅ **FIXED** - Committed `69d9cd3b`

**Issue**: In `as_completed()` loop, `page` variable was undefined - would crash on any render error.

**Fix**: Changed `futures = [...]` to `future_to_page = {...}` dict mapping.

---

## 🟠 Priority 2: Test Infrastructure

### 2.1 Async Test Configuration Missing
**Location**: `pytest.ini`, `tests/integration/test_linkcheck.py`

**Issue**: `@pytest.mark.asyncio` not recognized (99 warnings per test run)

**Root Cause**: Missing `asyncio_mode = auto` in pytest.ini or pytest-asyncio not configured

**Fix**:
```ini
# Add to pytest.ini
asyncio_mode = auto
```

Or register marker:
```ini
markers =
    asyncio: Async tests
```

**Impact**: All async linkcheck tests may not run properly

---

### 2.2 Flaky Integration Tests (Investigate)

| Test | Failure Mode |
|------|--------------|
| `test_check_successful_link` | Possibly network/async config |
| `test_build_workflows` | Worker crash (timeout/resource) |
| `test_memory_scaling` | Performance threshold |
| `test_pages_have_proper_html_structure` | Error (not failure) |

**Recommendation**: Run tests outside sandbox to verify if failures are environment-specific.

---

## 🟡 Priority 3: Code Quality

### 3.1 Deprecation Cleanup
Remove deprecated code after ensuring no usage:

| Deprecated | Location | Replacement |
|------------|----------|-------------|
| `bengal site new` command | `cli/commands/site.py:26` | `bengal new site` |
| `create_documentation_directives()` | `rendering/plugins/__init__.py:51` | `create_documentation_directives()` |
| `_build_auto_menu_with_dev_bundling()` | `orchestration/menu.py:302` | Use current method |

**Task**: 
- [ ] Add deprecation warnings if not present
- [ ] Remove deprecated code after 1-2 releases
- [ ] Update any documentation referencing old commands

---

### 3.2 Large Files (>800 lines)

Already modularized files with delegation patterns:
- `knowledge_graph.py` (912) → delegates to `GraphAnalyzer`, `GraphReporter`
- `output_formats/` → already a package

Files that could benefit from modularization (optional):

| File | Lines | Potential Split |
|------|-------|-----------------|
| `core/site.py` | 1,015 | Deferred - core data model |
| `template_functions/navigation.py` | 847 | Extract helpers |
| `autodoc/extractors/python.py` | 837 | Split by concern |
| `orchestration/taxonomy.py` | 828 | Extract taxonomy types |
| `utils/cli_output.py` | 827 | Extract formatters |
| `cache/build_cache.py` | 820 | Extract serialization |

**Recommendation**: Low priority - these are cohesive modules. Only split if maintainability issues arise.

---

### 3.3 Lint Issues

```
248  E501  line-too-long
 36  W293  blank-line-with-whitespace
  4  SIM114 if-with-same-arms
  3  SIM102 collapsible-if
```

**Fix**: `ruff check bengal/ --fix` (safe fixes)

---

## 🟢 Priority 4: Documentation/Polish

### 4.1 Marimo Directive TODO
**Location**: `bengal/rendering/plugins/directives/marimo.py:140, 167`

```python
# TODO: Implement caching
# TODO: Store in cache
```

**Status**: Feature incomplete - caching not implemented for Marimo notebooks

---

### 4.2 Init Command TODOs
**Location**: `bengal/cli/commands/init.py:125, 165`

Template placeholders - these are intentional user-facing comments, not code TODOs.

---

## Action Plan

### Immediate (Today)
1. [x] Fix undefined `page` variable ✅
2. [ ] Fix pytest-asyncio configuration
3. [ ] Run `ruff check --fix` for safe lint fixes

### This Week
4. [ ] Investigate test failures outside sandbox
5. [ ] Add deprecation warnings to old commands
6. [ ] Clean up whitespace lint issues

### Future (Backlog)
7. [ ] Consider `site.py` modularization (if needed)
8. [ ] Implement Marimo caching (feature request)
9. [ ] Full deprecation removal (next major version)

---

## Verification Commands

```bash
# Check for undefined names
ruff check bengal/ --select=F821

# Run async tests
pytest tests/integration/test_linkcheck.py -v

# Check lint status
ruff check bengal/ --statistics

# Run all tests (outside sandbox)
pytest tests/ -x -v
```

