# 📋 Implementation Plan: Robust Template Error Collection

## Executive Summary

Implement reliable template error collection during site builds. The RFC proposes a hybrid approach: proactive validation (opt-in) + enhanced render-time capture (default). This plan breaks down the implementation into 12 atomic tasks across 3 phases.

## Plan Details

- **Total Tasks**: 12
- **Estimated Time**: 3-4 days
- **Complexity**: Moderate
- **Confidence Gates**: RFC ≥85%, Implementation ≥90%
- **RFC**: `plan/active/rfc-template-error-collection.md`

---

## Phase 1: Foundation (5 tasks)

### Rendering Changes (`bengal/rendering/`)

#### Task 1.1: Add `validate_templates()` method to TemplateEngine

- **Files**: `bengal/rendering/template_engine/core.py`
- **Action**:
  - Add new method `validate_templates(include_patterns: list[str] | None = None) -> list[TemplateRenderError]`
  - Iterate through all template directories in `self.template_dirs`
  - For each `.html` file, call `self.env.get_template()` wrapped in try/except
  - Catch `TemplateSyntaxError` and convert to `TemplateRenderError`
  - Return list of all errors found
- **Dependencies**: None
- **Status**: pending
- **Commit**: `rendering(template_engine): add validate_templates() method for proactive syntax checking`

#### Task 1.2: Expose template directories from TemplateEngine

- **Files**: `bengal/rendering/template_engine/core.py`
- **Action**:
  - Store `template_dirs` from environment creation as instance attribute
  - Add property `template_dirs: list[Path]` for access by validate_templates
  - Ensure the list reflects the actual Jinja2 FileSystemLoader search paths
- **Dependencies**: None (can be done in parallel with 1.1)
- **Status**: pending
- **Commit**: `rendering(template_engine): expose template_dirs as instance property`

#### Task 1.3: Add error categorization properties to BuildStats

- **Files**: `bengal/utils/build_stats.py`
- **Action**:
  - Add `@property syntax_errors` - filter template_errors where error_type == "syntax"
  - Add `@property not_found_errors` - filter template_errors where error_type == "not_found"
  - Keep existing `template_errors` list unchanged for backward compatibility
- **Dependencies**: None (can be done in parallel)
- **Status**: pending
- **Commit**: `utils(build_stats): add syntax_errors and not_found_errors properties`

---

### Tests (`tests/unit/`)

#### Task 1.4: Add unit tests for validate_templates()

- **Files**: `tests/unit/rendering/test_template_validation.py` (new file)
- **Action**:
  - Test `validate_templates()` with valid templates returns empty list
  - Test `validate_templates()` with broken template returns TemplateRenderError
  - Test `validate_templates()` with include_patterns filters correctly
  - Test multiple broken templates returns all errors
- **Dependencies**: Task 1.1, Task 1.2
- **Status**: pending
- **Commit**: `tests(rendering): add unit tests for TemplateEngine.validate_templates()`

#### Task 1.5: Add unit tests for BuildStats categorization

- **Files**: `tests/unit/utils/test_build_stats.py` (extend existing)
- **Action**:
  - Test `syntax_errors` property filters correctly
  - Test `not_found_errors` property filters correctly
  - Test empty list when no errors
- **Dependencies**: Task 1.3
- **Status**: pending
- **Commit**: `tests(utils): add tests for BuildStats error categorization`

---

## Phase 2: Build Integration (4 tasks)

### Orchestration Changes (`bengal/orchestration/`)

#### Task 2.1: Add template validation phase to BuildOrchestrator

- **Files**: `bengal/orchestration/build.py`
- **Action**:
  - Add optional template validation phase after TemplateEngine initialization
  - Read `validate_templates` config option (default: False)
  - If enabled, call `template_engine.validate_templates()`
  - Collect errors to `build_stats.template_errors`
  - In strict mode with errors, fail build early with clear message
  - In normal mode, log warnings and continue
- **Dependencies**: Task 1.1, Task 1.2
- **Status**: pending
- **Commit**: `orchestration(build): add optional template validation phase`

#### Task 2.2: Add `validate_templates` config option

- **Files**: `bengal/config/defaults.py` or relevant config module
- **Action**:
  - Add `validate_templates: bool = False` to build config schema
  - Document in config comments
  - Ensure config merging preserves this option
- **Dependencies**: None
- **Status**: pending
- **Commit**: `config: add validate_templates build option (default: false)`

---

### Tests (`tests/integration/`)

#### Task 2.3: Re-enable and fix integration tests

- **Files**: `tests/integration/test_template_error_collection.py`
- **Action**:
  - Remove `pytestmark = pytest.mark.skip(...)` at module level
  - Update tests to use `validate_templates = True` config
  - Verify `test_build_collects_template_errors` passes
  - Verify `test_build_collects_multiple_errors` passes
  - Verify `test_error_has_rich_information` passes
  - Add test for strict mode behavior
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `tests(integration): re-enable template error collection tests`

#### Task 2.4: Add integration test for default behavior (no validation)

- **Files**: `tests/integration/test_template_error_collection.py`
- **Action**:
  - Add test that verifies default behavior unchanged
  - Test that `validate_templates = false` (default) doesn't run validation phase
  - Test that render-time errors are still collected
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `tests(integration): add regression test for default template behavior`

---

## Phase 3: Polish (3 tasks)

### Rendering Changes (`bengal/rendering/`)

#### Task 3.1: Improve template error messages

- **Files**: `bengal/rendering/errors.py`
- **Action**:
  - Enhance error message to include template search path
  - Add suggestion for common issues (missing endif, unclosed tags)
  - Ensure line numbers are accurate from Jinja2 error
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `rendering(errors): improve template error messages with search path and suggestions`

---

### Documentation

#### Task 3.2: Update configuration reference

- **Files**: `site/content/docs/reference/configuration.md` (or equivalent)
- **Action**:
  - Document `[build] validate_templates` option
  - Explain when to enable (development, CI)
  - Describe interaction with `strict_mode`
- **Dependencies**: Task 2.2
- **Status**: pending
- **Commit**: `docs: document validate_templates config option`

#### Task 3.3: Add troubleshooting guide for template errors

- **Files**: `site/content/docs/troubleshooting/template-errors.md` (new)
- **Action**:
  - Common template syntax errors and fixes
  - How to enable proactive validation
  - Understanding error output
  - How template fallback works
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `docs: add template error troubleshooting guide`

---

## 📊 Task Summary

| Area | Tasks | Status |
|------|-------|--------|
| Rendering | 3 | pending |
| Orchestration | 1 | pending |
| Config | 1 | pending |
| Utils | 1 | pending |
| Unit Tests | 2 | pending |
| Integration Tests | 2 | pending |
| Documentation | 2 | pending |
| **Total** | **12** | **pending** |

---

## Validation Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass (including re-enabled ones)
- [ ] Linter passes (no new errors)
- [ ] Existing build behavior unchanged when `validate_templates = false`
- [ ] Strict mode correctly fails on template errors
- [ ] Error messages include file path and line number

---

## Confidence Gates

| Gate | Threshold | Check |
|------|-----------|-------|
| RFC confidence | ≥85% | ✅ 85% |
| Unit test coverage | ≥90% | Verify after Phase 1 |
| Integration tests | All pass | Verify after Phase 2 |
| No regressions | 0 failures | Verify after each phase |

---

## 📋 Next Steps

- [ ] Begin Phase 1 with Task 1.1 (validate_templates method)
- [ ] Tasks 1.1, 1.2, 1.3 can run in parallel
- [ ] Phase 1 tests (1.4, 1.5) require their dependencies
- [ ] Phase 2 depends on Phase 1 completion
- [ ] Phase 3 can start after Phase 2 core tasks (2.1, 2.2)

---

## Pre-Drafted Commits (for reference)

```bash
# Phase 1
git commit -m "rendering(template_engine): add validate_templates() method for proactive syntax checking"
git commit -m "rendering(template_engine): expose template_dirs as instance property"
git commit -m "utils(build_stats): add syntax_errors and not_found_errors properties"
git commit -m "tests(rendering): add unit tests for TemplateEngine.validate_templates()"
git commit -m "tests(utils): add tests for BuildStats error categorization"

# Phase 2
git commit -m "orchestration(build): add optional template validation phase"
git commit -m "config: add validate_templates build option (default: false)"
git commit -m "tests(integration): re-enable template error collection tests"
git commit -m "tests(integration): add regression test for default template behavior"

# Phase 3
git commit -m "rendering(errors): improve template error messages with search path and suggestions"
git commit -m "docs: document validate_templates config option"
git commit -m "docs: add template error troubleshooting guide"
```
