# RFC: December Code Hygiene Sprint

**Author**: AI Assistant  
**Date**: 2025-12-01  
**Status**: Ready for Implementation  
**Confidence**: 95% 🟢

---

## Executive Summary

**Context**: Codebase analysis identified several hygiene issues that should be addressed:
- Test configuration causing warnings
- Deprecated code still present
- Minor lint issues
- Flaky tests needing investigation

**Goal**: Clean up technical debt and improve test reliability in a focused sprint.

**Impact**:
- ✅ Cleaner test output (eliminate 99+ warnings per run)
- ✅ Reduced confusion from deprecated commands
- ✅ Improved code quality metrics
- ✅ More reliable CI/CD

**Estimated Effort**: 2-3 hours

---

## 1. Problem Statement

### 1.1 Test Warnings (Fixed ✅)
```
PytestUnknownMarkWarning: Unknown pytest.mark.asyncio
```
- 99+ warnings per test run
- **Status**: Fixed with `asyncio_mode = auto`

### 1.2 Deprecated Code Still Present

Three deprecated items need cleanup:

| Item | Location | Age | Action |
|------|----------|-----|--------|
| `bengal site new` command | `cli/commands/site.py` | Active | Add warning, schedule removal |
| `create_documentation_directives()` | `rendering/plugins/__init__.py:51` | Unknown | Verify usage, deprecate properly |
| `_build_auto_menu_with_dev_bundling()` | `orchestration/menu.py:302` | Unknown | Remove if unused |

### 1.3 Remaining Lint Issues

```
248  E501  line-too-long (style preference)
  2  W293  blank-line-with-whitespace (2 remaining after fix)
  4  SIM114 if-with-same-arms
  3  SIM102 collapsible-if
```

### 1.4 Flaky Integration Tests

| Test | Issue |
|------|-------|
| `test_check_successful_link` | May be async config (now fixed) |
| `test_build_workflows` | Worker crash - needs investigation |
| `test_memory_scaling` | Threshold issue |

---

## 2. Goals & Non-Goals

### Goals

1. **Clean deprecation warnings** - Ensure deprecated code emits warnings
2. **Remove dead code** - Delete truly unused deprecated functions
3. **Fix remaining lint issues** - Clean up whitespace and simplifiable conditionals
4. **Verify test fixes** - Confirm async tests now pass

### Non-Goals

- Not addressing line-too-long (248 instances) - style preference, not bugs
- Not refactoring large files - already functional
- Not implementing new features

---

## 3. Implementation Plan

### Phase 1: Verify Test Fixes (5 min)
- [ ] Run async linkcheck tests to verify `asyncio_mode` fix works

### Phase 2: Deprecation Audit (30 min)
- [ ] Check if `bengal site new` emits deprecation warning
- [ ] Check usage of `create_documentation_directives()`
- [ ] Check usage of `_build_auto_menu_with_dev_bundling()`
- [ ] Add/update deprecation warnings as needed
- [ ] Remove dead code if confirmed unused

### Phase 3: Lint Cleanup (15 min)
- [ ] Fix remaining 2 whitespace issues
- [ ] Fix 4 `if-with-same-arms` (SIM114)
- [ ] Fix 3 `collapsible-if` (SIM102)

### Phase 4: Test Verification (15 min)
- [ ] Run integration tests to verify stability
- [ ] Document any remaining flaky tests

---

## 4. Success Criteria

- [ ] Zero `pytest.mark.asyncio` warnings
- [ ] All deprecated code either removed or emitting warnings
- [ ] Lint issues reduced (target: <250 total)
- [ ] Integration tests passing (or documented as environment-specific)

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Removing code that's still used | Grep for all usages before deletion |
| Breaking existing scripts using deprecated CLI | Keep deprecated command with warning for 1-2 releases |
| Tests still flaky after fixes | Document as known issues with workarounds |

---

## 6. Commits Plan

```bash
# Phase 2
git commit -m "deprecation: add warnings to deprecated code; remove dead functions"

# Phase 3
git commit -m "lint: fix SIM114/SIM102 simplifiable conditionals"

# Phase 4
git commit -m "tests: verify async test configuration working"
```

---

## Decision

**Status**: ✅ Approved for implementation

**Start**: Immediately

