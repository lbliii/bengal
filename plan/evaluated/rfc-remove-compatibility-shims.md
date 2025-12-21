# RFC: Remove Unused Compatibility Shims and Wrapper Code

**Status**: Evaluated
**Created**: 2025-01-27
**Author**: AI Assistant
**Confidence**: 90% 🟢
**Category**: Code Quality / Technical Debt

---

## Executive Summary

Codebase analysis identified **3 unused compatibility shims** that add maintenance overhead without providing value. All imports have migrated to canonical paths, making these shims obsolete. This RFC proposes removing them to reduce cognitive load and eliminate dead code.

**Impact**: Low risk, high value cleanup. Removes 3 files (~60 lines) of unused code.

---

## Problem Statement

### Current State

Bengal maintains several compatibility shims from past refactorings:

1. **`bengal/core/build_context.py`** - Re-exports `BuildContext` from `bengal.utils.build_context`
2. **`bengal/autodoc/extractors/python.py`** - File-level shim with deprecation warnings for `PythonExtractor`
3. **`discover_components()` function** - Standalone wrapper around `ComponentPreviewServer.discover_components()`

### Evidence: Unused Imports

**1. BuildContext shim** (`bengal/core/build_context.py`):

```python
# bengal/core/build_context.py:13
from bengal.utils.build_context import BuildContext  # noqa: F401
```

**Usage analysis**:

- ✅ **38 imports** use canonical path: `from bengal.utils.build_context import BuildContext`
- ❌ **0 imports** use old path: `from bengal.core.build_context import BuildContext`

**Evidence**: `grep -r "from bengal.core.build_context"` returns zero matches.

---

**2. PythonExtractor file shim** (`bengal/autodoc/extractors/python.py`):

```python
# bengal/autodoc/extractors/python.py:19-27
from bengal.autodoc.extractors.python import PythonExtractor

warnings.warn(
    "Importing PythonExtractor from bengal.autodoc.extractors.python (file) is deprecated...",
    DeprecationWarning,
    stacklevel=2,
)
```

**Usage analysis**:

- ✅ **All imports** use package path: `from bengal.autodoc.extractors.python import PythonExtractor`
- Package structure: `python/__init__.py` → `python/extractor.py` (canonical)
- ❌ **File `python.py`** is never imported (Python resolves `python` to `python/__init__.py`)

**Evidence**: All 10 imports resolve to `python/__init__.py`, not `python.py`:

- `bengal/autodoc/__init__.py:18`
- `bengal/autodoc/extractors/__init__.py:10`
- `bengal/autodoc/orchestration/extractors.py:27`
- All test files use package import

---

**3. discover_components() wrapper** (`bengal/server/component_preview.py:393-395`):

```python
# Backwards-compatible function export for tests
def discover_components(site: Site) -> list[dict[str, Any]]:
    """Discover components using a temporary server instance (compat shim)."""
    return ComponentPreviewServer(site).discover_components()
```

**Usage analysis**:

- ✅ Used in **1 test**: `tests/unit/server/test_component_preview.py:168-170`
- ❌ No production code uses this wrapper
- ✅ Can be refactored to use class method directly

---

### Pain Points

1. **Cognitive Load**: Developers see deprecation warnings and compatibility shims, creating confusion about canonical paths
2. **Maintenance Overhead**: Dead code requires maintenance (imports, docstrings, deprecation warnings)
3. **False Signals**: Deprecation warnings suggest migration needed, but migration is already complete
4. **Code Clutter**: Unnecessary files in package structure

### Impact

- **Low Risk**: No production code depends on these shims
- **High Value**: Cleaner codebase, reduced confusion, eliminated dead code
- **Affected**: Developers reading/understanding codebase structure

---

## Goals & Non-Goals

### Goals

1. **Remove unused compatibility shims** - Delete files that are no longer imported
2. **Refactor test usage** - Update test to use canonical API directly
3. **Eliminate deprecation warnings** - Remove false-positive deprecation signals
4. **Reduce cognitive load** - Cleaner package structure

### Non-Goals

1. **Not removing legitimate wrappers** - Keep wrappers that add value:
   - `TemplatePageWrapper`, `TemplateSectionWrapper`, `TemplateSiteWrapper` (add baseurl logic)
   - `LiveProgressReporterAdapter` (adapts protocol interfaces)
   - `ProfiledTemplate` (adds profiling instrumentation)
   - Template function `*_wrapper` closures (provide site closure for Jinja2)
   - Legacy directive compatibility (`GridDirective`, `GridItemCardDirective`) - user-facing backward compatibility

2. **Not changing public APIs** - Only removing unused code paths

3. **Not breaking existing functionality** - All current imports use canonical paths

---

## Design Options

### Option A: Remove All Shims Immediately

**Description**: Delete all 3 shims in one commit, refactor test.

**Pros**:

- ✅ Cleanest outcome
- ✅ Single atomic change
- ✅ No migration period needed

**Cons**:

- ⚠️ Requires test refactor (low risk)

**Recommended**: ✅ **Option A** - All evidence shows shims are unused. No migration period needed.

### Option B: Keep Shims with Deprecation Warnings

**Description**: Keep shims but add stronger deprecation warnings.

**Pros**:

- ✅ Zero risk of breaking anything

**Cons**:

- ❌ Maintains dead code
- ❌ Continues false-positive deprecation warnings
- ❌ Adds cognitive load

**Not Recommended**: Dead code should be removed, not maintained.

---

## Detailed Design

### File Removals

**1. Delete `bengal/core/build_context.py`**:

- **Reason**: Zero imports use this path
- **Impact**: None (no code depends on it)
- **Verification**: `grep -r "from bengal.core.build_context"` returns empty

**2. Delete `bengal/autodoc/extractors/python.py`**:

- **Reason**: Python resolves `python` import to `python/__init__.py`, not `python.py`
- **Impact**: None (all imports resolve to package)
- **Verification**: All imports use package path, file is never loaded

**3. Remove `discover_components()` function** from `bengal/server/component_preview.py:393-395`:

- **Reason**: Only used in 1 test, can use class method directly
- **Impact**: Requires test refactor
- **Verification**: Single test usage identified

### Test Refactoring

**File**: `tests/unit/server/test_component_preview.py:168-170`

**Before**:

```python
from bengal.server.component_preview import discover_components

components = discover_components(site)
```

**After**:

```python
from bengal.server.component_preview import ComponentPreviewServer

components = ComponentPreviewServer(site).discover_components()
```

**Impact**: Minimal - same functionality, clearer API usage.

---

## Architecture Impact

### Affected Subsystems

| Subsystem | Impact | Notes |
|-----------|--------|-------|
| **Core** | ✅ None | Removing unused file |
| **Autodoc** | ✅ None | Removing unused file |
| **Server** | ✅ None | Removing unused wrapper function |
| **Tests** | 🟡 Minor | One test needs refactor |

### Import Path Changes

**No changes required** - All imports already use canonical paths:

- ✅ `from bengal.utils.build_context import BuildContext` (38 usages)
- ✅ `from bengal.autodoc.extractors.python import PythonExtractor` (10 usages)
- ✅ `ComponentPreviewServer(site).discover_components()` (direct usage)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Hidden import dependency** | Low | Medium | Run full test suite before/after removal |
| **Test refactor breaks test** | Low | Low | Test is straightforward, verify behavior unchanged |
| **Python import resolution confusion** | Low | Low | Verify with `python -c "import bengal.autodoc.extractors.python; print(__file__)"` |

### Verification Steps

1. **Pre-removal**:

   ```bash
   # Verify no imports use old paths
   grep -r "from bengal.core.build_context" bengal/ tests/
   grep -r "from bengal.autodoc.extractors.python import" bengal/ tests/ | grep -v "__pycache__"

   # Verify Python import resolution
   python -c "from bengal.autodoc.extractors.python import PythonExtractor; import bengal.autodoc.extractors.python; print(bengal.autodoc.extractors.python.__file__)"
   # Should print: .../python/__init__.py (not python.py)
   ```

2. **Post-removal**:

   ```bash
   # Run full test suite
   pytest tests/ -v

   # Verify imports still work
   python -c "from bengal.utils.build_context import BuildContext; print('OK')"
   python -c "from bengal.autodoc.extractors.python import PythonExtractor; print('OK')"
   ```

---

## Implementation Plan

### Phase 1: Verification (5 min)

1. Run verification commands above
2. Confirm zero imports use old paths
3. Confirm Python resolves to package, not file

### Phase 2: Removal (10 min)

1. **Delete `bengal/core/build_context.py`**
2. **Delete `bengal/autodoc/extractors/python.py`**
3. **Remove `discover_components()` function** from `bengal/server/component_preview.py:393-395`
4. **Update test** `tests/unit/server/test_component_preview.py:168-170`:

   ```python
   # Change from:
   from bengal.server.component_preview import discover_components
   components = discover_components(site)

   # To:
   from bengal.server.component_preview import ComponentPreviewServer
   components = ComponentPreviewServer(site).discover_components()
   ```

### Phase 3: Validation (5 min)

1. Run test suite: `pytest tests/unit/server/test_component_preview.py -v`
2. Run full test suite: `pytest tests/ -v`
3. Verify imports work: `python -c "from bengal.utils.build_context import BuildContext; from bengal.autodoc.extractors.python import PythonExtractor; print('OK')"`

### Phase 4: Commit

```bash
git add -A && git commit -m "core: remove unused BuildContext compatibility shim; autodoc: remove unused PythonExtractor file shim; server: remove discover_components() wrapper and refactor test to use class method directly"
```

**Estimated Time**: 20 minutes total

---

## Open Questions

- [ ] **Q1**: Should we check git history to confirm when migration completed?
  - **Answer**: Not necessary - current state shows zero usage
- [ ] **Q2**: Are there any external packages that might import these shims?
  - **Answer**: Unlikely, but verification commands will catch this
- [ ] **Q3**: Should we add a deprecation period before removal?
  - **Answer**: No - shims are already unused, no migration needed

---

## Confidence Scoring

**Overall Confidence**: 90% 🟢

### Component Scores

| Component | Score | Reasoning |
|-----------|-------|-----------|
| **Evidence** | 38/40 | ✅ Complete import analysis, zero usage found |
| **Consistency** | 28/30 | ✅ All imports use canonical paths consistently |
| **Recency** | 15/15 | ✅ Analysis performed today, codebase current |
| **Tests** | 9/15 | 🟡 Single test needs refactor, but straightforward |

### Confidence Breakdown

- **BuildContext shim**: 100% confidence - zero imports found
- **PythonExtractor shim**: 100% confidence - Python resolves to package, file never loaded
- **discover_components() wrapper**: 90% confidence - single test usage, straightforward refactor

---

## Success Criteria

✅ **Removal Complete**:

- [ ] `bengal/core/build_context.py` deleted
- [ ] `bengal/autodoc/extractors/python.py` deleted
- [ ] `discover_components()` function removed from `component_preview.py`
- [ ] Test refactored to use `ComponentPreviewServer` directly

✅ **Verification Complete**:

- [ ] All tests pass
- [ ] Imports still work (canonical paths)
- [ ] No deprecation warnings in codebase
- [ ] Zero references to removed files

✅ **Documentation**:

- [ ] Changelog entry added (if applicable)
- [ ] Commit message follows Bengal standards

---

## Related

- **Architecture**: `architecture/file-organization.md` - Package structure guidelines
- **Code Quality**: `plan/evaluated/rfc-code-smell-remediation.md` - Related code smell analysis
- **Philosophy**: `site/content/docs/about/philosophy.md` - "Delete deprecated code when it's time"
