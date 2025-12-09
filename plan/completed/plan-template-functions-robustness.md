# 📋 Implementation Plan: Template Functions Robustness

**Source RFC**: `plan/active/rfc-template-functions-robustness.md`  
**Created**: 2025-12-09  
**Status**: Ready for Implementation

---

## Executive Summary

Fix the broken `truncatewords_html` function, add performance caching to `resolve_pages`, improve observability for silent failures, and add comprehensive unit tests. Option A (Minimal Fixes) selected for high ROI with low risk.

### Plan Details

- **Total Tasks**: 14
- **Estimated Time**: 3-4 hours
- **Complexity**: Moderate
- **Confidence Gates**: Implementation ≥90%

---

## Phase 1: Critical Fix — TF-1 (3 tasks)

### Rendering Changes (`bengal/rendering/template_functions/`)

#### Task 1.1: Implement HTML-preserving `truncatewords_html`

- **Files**: `bengal/rendering/template_functions/strings.py`
- **Action**: 
  - Replace `truncatewords_html` implementation (lines 88-119)
  - Add tag-aware truncation with open tag tracking
  - Include complete HTML5 void elements set
  - Close unclosed tags at truncation point
- **Dependencies**: None
- **Status**: pending
- **Commit**: `rendering(strings): fix truncatewords_html to preserve HTML structure and close tags`

#### Task 1.2: Update `truncatewords_html` docstring and comments

- **Files**: `bengal/rendering/template_functions/strings.py`
- **Action**:
  - Update docstring to accurately describe behavior
  - Remove misleading comment at line 116-117 ("Simple implementation")
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `rendering(strings): update truncatewords_html docstring to match implementation`

### Tests (`tests/unit/rendering/`)

#### Task 1.3: Add unit tests for `truncatewords_html`

- **Files**: `tests/unit/rendering/test_template_functions_strings.py` (new)
- **Action**:
  - Create test file with `TestTruncateWordsHtml` class
  - Test: preserves simple tags
  - Test: closes unclosed tags
  - Test: handles void elements (br, img, etc.)
  - Test: short content unchanged
  - Test: empty input
  - Test: nested tags
- **Dependencies**: Task 1.1
- **Status**: pending
- **Commit**: `tests(rendering): add truncatewords_html unit tests for HTML preservation`

---

## Phase 2: Performance — TF-2 (4 tasks)

### Core Changes (`bengal/core/`)

#### Task 2.1: Add page path map cache to Site

- **Files**: `bengal/core/site.py`
- **Action**:
  - Add `_page_path_map: dict[str, Page] | None = None`
  - Add `_page_path_map_version: int = -1`
  - Add `get_page_path_map()` method with version-based invalidation
  - Add `invalidate_page_caches()` method for explicit clearing
- **Dependencies**: None
- **Status**: pending
- **Commit**: `core(site): add cached page path map with version-based invalidation`

### Rendering Changes (`bengal/rendering/template_functions/`)

#### Task 2.2: Update `resolve_pages` to use cached map

- **Files**: `bengal/rendering/template_functions/collections.py`
- **Action**:
  - Replace inline `page_map` construction (line 558-559)
  - Use `site.get_page_path_map()` instead
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `rendering(collections): use cached page path map in resolve_pages for O(1) lookups`

### Tests (`tests/unit/`)

#### Task 2.3: Add unit tests for page path map caching

- **Files**: `tests/unit/test_site.py`
- **Action**:
  - Test: `get_page_path_map()` returns consistent map
  - Test: Cache invalidates when page count changes
  - Test: `invalidate_page_caches()` clears cache
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `tests(core): add unit tests for Site page path map caching`

#### Task 2.4: Add unit tests for `resolve_pages` with caching

- **Files**: `tests/unit/rendering/test_template_functions_collections.py` (new)
- **Action**:
  - Test: resolves paths to pages correctly
  - Test: handles missing paths gracefully
  - Test: returns empty list for empty input
- **Dependencies**: Task 2.2
- **Status**: pending
- **Commit**: `tests(rendering): add resolve_pages unit tests`

---

## Phase 3: Observability — TF-3 (2 tasks)

### Rendering Changes (`bengal/rendering/template_functions/`)

#### Task 3.1: Add warning log for `replace_regex` invalid pattern

- **Files**: `bengal/rendering/template_functions/strings.py`
- **Action**:
  - In `replace_regex` exception handler (line 328-330)
  - Add `logger.warning()` call with pattern and error details
  - Log level: WARNING (developer error, should be visible)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `rendering(strings): add warning log for invalid regex patterns in replace_regex`

#### Task 3.2: Add debug log for `sort_by` failures

- **Files**: `bengal/rendering/template_functions/collections.py`
- **Action**:
  - In `sort_by` exception handler (line 242-244)
  - Add `logger.debug()` call with key and error details
  - Log level: DEBUG (expected edge case, not developer error)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `rendering(collections): add debug log for sort_by failures`

---

## Phase 4: Test Coverage — TF-4 (3 tasks)

### Tests (`tests/unit/rendering/`)

#### Task 4.1: Add comprehensive string function tests

- **Files**: `tests/unit/rendering/test_template_functions_strings.py`
- **Action**: Add test classes for remaining functions:
  - `TestTruncateWords` (3 tests)
  - `TestSlugify` (4 tests)
  - `TestReplaceRegex` (4 tests)
  - `TestMarkdownify` (3 tests)
  - `TestStripHtml` (3 tests)
  - `TestReadingTime` (4 tests)
  - `TestExcerpt` (3 tests)
  - `TestFirstSentence` (3 tests)
  - `TestPluralize` (4 tests)
  - `TestDictGet` (3 tests)
- **Dependencies**: Task 1.3
- **Status**: pending
- **Commit**: `tests(rendering): add comprehensive unit tests for string template functions`

#### Task 4.2: Add comprehensive collection function tests

- **Files**: `tests/unit/rendering/test_template_functions_collections.py`
- **Action**: Add test classes:
  - `TestSortBy` (4 tests)
  - `TestWhere` (2 tests)
  - `TestLimit` (2 tests)
  - `TestOffset` (2 tests)
  - `TestGroupBy` (2 tests)
- **Dependencies**: Task 2.4
- **Status**: pending
- **Commit**: `tests(rendering): add comprehensive unit tests for collection template functions`

#### Task 4.3: Run test coverage and verify ≥90%

- **Files**: N/A (verification task)
- **Action**:
  - Run `pytest --cov=bengal/rendering/template_functions tests/unit/rendering/`
  - Verify coverage ≥90% for `strings.py` and `collections.py`
  - Add missing tests if needed
- **Dependencies**: Tasks 4.1, 4.2
- **Status**: pending
- **Commit**: N/A (verification only)

---

## Phase 5: Feature Gap — TF-9 (2 tasks)

### Rendering Changes (`bengal/rendering/template_functions/`)

#### Task 5.1: Expose `filesize` filter

- **Files**: `bengal/rendering/template_functions/strings.py`
- **Action**:
  - Import `humanize_bytes` from `bengal.utils.text`
  - Add `filesize` function wrapper
  - Register in `env.filters` dict
  - Update module docstring count
- **Dependencies**: None
- **Status**: pending
- **Commit**: `rendering(strings): expose filesize filter wrapping humanize_bytes`

#### Task 5.2: Add unit tests for `filesize` filter

- **Files**: `tests/unit/rendering/test_template_functions_strings.py`
- **Action**:
  - Test: formats bytes correctly (KB, MB, GB)
  - Test: handles zero
  - Test: handles large values
- **Dependencies**: Tasks 4.1, 5.1
- **Status**: pending
- **Commit**: `tests(rendering): add filesize filter unit tests`

---

## Validation Checklist

### Before Starting
- [ ] RFC approved (92% confidence ✅)
- [ ] No blocking changes in related files

### After Each Phase
- [ ] Lint passes: `ruff check bengal/rendering/template_functions/`
- [ ] Type check passes: `mypy bengal/rendering/template_functions/`

### Final Validation
- [ ] All unit tests pass: `pytest tests/unit/rendering/test_template_functions_*.py -v`
- [ ] Coverage ≥90%: `pytest --cov --cov-report=term-missing`
- [ ] No regressions in existing tests: `pytest tests/`
- [ ] Manual verification: `{{ "<p>Hello <strong>world</strong></p>" | truncatewords_html(1) }}` → `<p>Hello...</p>`

---

## 📊 Task Summary

| Area | Tasks | Estimated Time |
|------|-------|----------------|
| Core | 1 | 15 min |
| Rendering | 5 | 60 min |
| Tests | 6 | 90 min |
| Validation | 2 | 15 min |
| **Total** | **14** | **~3 hours** |

---

## Task Dependencies Graph

```
Phase 1 (Critical Fix):
  1.1 truncatewords_html impl ──┬──► 1.2 docstring update
                                └──► 1.3 tests

Phase 2 (Performance):
  2.1 Site cache ──┬──► 2.2 resolve_pages update ──► 2.4 resolve_pages tests
                   └──► 2.3 Site cache tests

Phase 3 (Observability):
  3.1 replace_regex log ◄── independent
  3.2 sort_by log ◄── independent

Phase 4 (Test Coverage):
  1.3 ──► 4.1 string tests ──┬
  2.4 ──► 4.2 collection tests ──┼──► 4.3 coverage check
                              └──┘

Phase 5 (Feature Gap):
  5.1 filesize filter ──► 5.2 filesize tests
```

---

## 📋 Next Steps

1. [ ] Review plan for completeness
2. [ ] Begin Phase 1 with `::implement`
3. [ ] Track progress in this document (update task statuses)
4. [ ] Final validation with `::validate`

---

## Commit Sequence (Pre-drafted)

```bash
# Phase 1: Critical Fix
git add -A && git commit -m "rendering(strings): fix truncatewords_html to preserve HTML structure and close tags"
git add -A && git commit -m "rendering(strings): update truncatewords_html docstring to match implementation"
git add -A && git commit -m "tests(rendering): add truncatewords_html unit tests for HTML preservation"

# Phase 2: Performance
git add -A && git commit -m "core(site): add cached page path map with version-based invalidation"
git add -A && git commit -m "rendering(collections): use cached page path map in resolve_pages for O(1) lookups"
git add -A && git commit -m "tests(core): add unit tests for Site page path map caching"
git add -A && git commit -m "tests(rendering): add resolve_pages unit tests"

# Phase 3: Observability
git add -A && git commit -m "rendering(strings): add warning log for invalid regex patterns in replace_regex"
git add -A && git commit -m "rendering(collections): add debug log for sort_by failures"

# Phase 4: Test Coverage
git add -A && git commit -m "tests(rendering): add comprehensive unit tests for string template functions"
git add -A && git commit -m "tests(rendering): add comprehensive unit tests for collection template functions"

# Phase 5: Feature Gap
git add -A && git commit -m "rendering(strings): expose filesize filter wrapping humanize_bytes"
git add -A && git commit -m "tests(rendering): add filesize filter unit tests"
```

