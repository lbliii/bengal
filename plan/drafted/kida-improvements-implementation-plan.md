# Kida Improvements Implementation Plan

**Status**: Draft  
**Created**: 2025-12-26  
**Source**: `plan/drafted/kida-evaluation-report.md`  
**Priority**: P1 (High) — Performance & Hardening  
**Estimated Effort**: ~66 hours (2-3 weeks part-time)  
**Confidence**: 85% 🟢

---

## Executive Summary

This plan implements **17 actionable improvements** identified in the Kida evaluation report, organized into 4 phases:

| Phase | Focus | Items | Effort | Risk | Impact |
|-------|-------|-------|--------|------|--------|
| **Phase 1** | Quick Wins | 4 | ~6 hours | Low | Immediate 5-10% speedup |
| **Phase 2** | Performance | 3 | ~12 hours | Medium | 15-25% rendering speedup |
| **Phase 3** | Hardening | 3 | ~9 hours | Low | Improved reliability |
| **Phase 4** | Advanced | 7 | ~39 hours | Medium | Code quality, maintainability |
| **Total** | | **17** | **~66 hours** | **Mixed** | **10-25% overall speedup** |

**Success Criteria**:
- ✅ All performance benchmarks meet claimed thresholds (p < 0.05)
- ✅ All existing tests pass (backward compatibility)
- ✅ Security fixes prevent DoS (include recursion, token limit)
- ✅ Code consolidation eliminates duplication

---

## Phase 1: Quick Wins (Low Risk, High Value)

**Goal**: Implement safe, low-risk optimizations with immediate impact.  
**Timeline**: 1-2 days  
**Risk**: Low  
**Dependencies**: None (all items can be parallelized)

### Task 1.1: Enable Filter Inlining by Default

**Reference**: Evaluation Report §1.4  
**Effort**: 1 hour  
**Risk**: Low  
**Impact**: 5-10% speedup for filter-heavy templates

**Changes**:
- `bengal/rendering/kida/optimizer/__init__.py:59` — Change `filter_inlining: bool = False` → `True`
- `bengal/rendering/kida/optimizer/filter_inliner.py` — Expand `_INLINABLE_FILTERS` dict

**Implementation Steps**:
1. Update `OptimizationConfig.filter_inlining` default to `True`
2. Add documentation comment explaining override behavior
3. Expand `_INLINABLE_FILTERS` with additional string methods:
   - `swapcase`, `casefold`, `isdigit`, `isalpha`
4. Add test verifying filter override still works when inlining enabled
5. Run benchmark validation (see evaluation report §1.4)

**Acceptance Criteria**:
- [ ] `filter_inlining=True` by default
- [ ] Expanded `_INLINABLE_FILTERS` includes new methods
- [ ] Test: User override of built-in filter still works
- [ ] Benchmark: ≥5% speedup for filter-heavy templates (p < 0.05)

**Files**:
- `bengal/rendering/kida/optimizer/__init__.py`
- `bengal/rendering/kida/optimizer/filter_inliner.py`
- `tests/rendering/kida/test_filter_inlining.py` (new)

---

### Task 1.2: Cache Regex Patterns in Filters

**Reference**: Evaluation Report §1.5  
**Effort**: 2 hours  
**Risk**: Very Low  
**Impact**: 10-20% speedup for templates using regex filters

**Changes**:
- `bengal/rendering/kida/environment/filters.py` — Move regex compilation to module level

**Implementation Steps**:
1. Identify all filters with inline regex compilation:
   - `_filter_striptags` — `re.sub(r"<[^>]*>", ...)`
   - Any others found during code review
2. Create module-level compiled patterns:
   ```python
   import re
   _STRIPTAGS_RE = re.compile(r"<[^>]*>")
   ```
3. Update filter functions to use compiled patterns
4. Remove `import re` from inside functions
5. Add test verifying behavior unchanged
6. Run benchmark validation (see evaluation report §1.5)

**Acceptance Criteria**:
- [ ] All regex patterns compiled at module level
- [ ] No `import re` inside filter functions
- [ ] Test: Filter behavior identical to before
- [ ] Benchmark: ≥10% speedup for affected filters (p < 0.05)

**Files**:
- `bengal/rendering/kida/environment/filters.py`
- `tests/rendering/kida/test_filter_performance.py` (new)

---

### Task 1.3: Move Lazy Imports to Module Level

**Reference**: Evaluation Report §1.6  
**Effort**: 1 hour  
**Risk**: Very Low  
**Impact**: Eliminates ~0.5ms overhead on first filter use

**Changes**:
- `bengal/rendering/kida/environment/filters.py` — Move stdlib imports to module level

**Implementation Steps**:
1. Identify filters with runtime imports:
   - `_filter_tojson` — `import json`
   - `_filter_filesizeformat` — may have imports
   - Any others found during code review
2. Move stdlib imports to module level:
   ```python
   import json
   import textwrap
   from itertools import groupby
   from urllib.parse import quote
   from pprint import pformat
   ```
3. Remove `import` statements from inside functions
4. Add test verifying no import errors

**Acceptance Criteria**:
- [ ] All stdlib imports at module level
- [ ] No runtime imports in filter functions
- [ ] Test: All filters import successfully
- [ ] No import errors in test suite

**Files**:
- `bengal/rendering/kida/environment/filters.py`
- `tests/rendering/kida/test_filters.py` (existing)

---

### Task 1.4: Add Include Recursion Limit

**Reference**: Evaluation Report §3.2  
**Effort**: 2 hours  
**Risk**: Low  
**Impact**: Prevents DoS from circular includes

**Changes**:
- `bengal/rendering/kida/template.py:278-298` — Add depth tracking

**Implementation Steps**:
1. Add `_include_depth` tracking to `_include()` function
2. Check depth before including template:
   ```python
   depth = context.get("_include_depth", 0)
   if depth > 50:
       raise TemplateRuntimeError(...)
   ```
3. Increment depth in context passed to included template
4. Add test for circular include detection
5. Add test for legitimate deep includes (50 levels)
6. Document limit in error message

**Acceptance Criteria**:
- [ ] Include depth tracked in context
- [ ] Error raised when depth > 50
- [ ] Test: Circular include detected and raises error
- [ ] Test: Legitimate deep includes work (up to limit)
- [ ] Error message includes suggestion for circular includes

**Files**:
- `bengal/rendering/kida/template.py`
- `tests/rendering/kida/test_template_includes.py` (new or extend)

---

## Phase 2: Performance Optimizations (Medium Risk)

**Goal**: Implement performance optimizations with benchmark validation.  
**Timeline**: 3-5 days  
**Risk**: Medium  
**Dependencies**: None (can parallelize)

### Task 2.1: Optimize Lexer `_advance()` Hot Path

**Reference**: Evaluation Report §1.1  
**Effort**: 4 hours  
**Risk**: Medium (column tracking complexity)  
**Impact**: 15-20% lexer speedup

**Changes**:
- `bengal/rendering/kida/lexer.py:664-673` — Batch advance with `count()`

**Implementation Steps**:
1. Replace character-by-character loop with batch processing:
   ```python
   def _advance(self, count: int) -> None:
       end_pos = min(self._pos + count, len(self._source))
       chunk = self._source[self._pos:end_pos]
       newlines = chunk.count("\n")
       if newlines:
           self._lineno += newlines
           last_nl = chunk.rfind("\n")
           self._col_offset = len(chunk) - last_nl - 1
       else:
           self._col_offset += len(chunk)
       self._pos = end_pos
   ```
2. Add comprehensive edge case tests:
   - Empty source
   - Single character
   - Multiple newlines in chunk
   - No newlines in chunk
   - Chunk ends at newline
3. Run benchmark validation (see evaluation report §1.1)
4. Verify column tracking accuracy matches original

**Acceptance Criteria**:
- [ ] Batch processing implemented
- [ ] Column tracking accurate (all tests pass)
- [ ] Test: Edge cases handled correctly
- [ ] Benchmark: ≥15% speedup for templates with long DATA nodes (p < 0.05)

**Files**:
- `bengal/rendering/kida/lexer.py`
- `tests/rendering/kida/test_lexer.py` (extend)
- `benchmarks/test_kida_lexer_performance.py` (new)

---

### Task 2.2: Consolidate Escape Functions

**Reference**: Evaluation Report §1.2  
**Effort**: 6 hours  
**Risk**: Medium (autoescape behavior)  
**Impact**: 2-3x speedup for explicit `| escape` filter

**Changes**:
- Create `bengal/rendering/kida/utils/html.py` (new)
- Refactor `bengal/rendering/kida/template.py:803-824`
- Refactor `bengal/rendering/kida/environment/filters.py:93-110`

**Implementation Steps**:
1. Create `utils/html.py` module with optimized escaping:
   ```python
   _ESCAPE_TABLE = str.maketrans({...})
   _ESCAPE_CHECK = re.compile(r'[&<>"\']')

   def html_escape(value: Any) -> str:
       """O(n) single-pass HTML escaping (returns str)."""
       ...

   def html_escape_filter(value: Any) -> Markup:
       """HTML escape returning Markup (for filter use)."""
       ...
   ```
2. Update `template._escape()` to use `html_escape()` (returns `str`)
3. Update `_filter_escape()` to use `html_escape_filter()` (returns `Markup`)
4. Remove duplicate implementations
5. Add comprehensive autoescape integration tests:
   - Verify Markup objects not double-escaped
   - Verify autoescape context respected
   - Verify filter escape returns Markup
6. Run benchmark validation (see evaluation report §1.2)

**Acceptance Criteria**:
- [ ] `utils/html.py` created with optimized functions
- [ ] Both `template._escape()` and `_filter_escape()` use shared implementation
- [ ] Test: Autoescape behavior unchanged
- [ ] Test: Markup objects handled correctly
- [ ] Benchmark: ≥2x speedup for explicit escape filter (p < 0.05)

**Files**:
- `bengal/rendering/kida/utils/html.py` (new)
- `bengal/rendering/kida/template.py`
- `bengal/rendering/kida/environment/filters.py`
- `tests/rendering/kida/test_html_utils.py` (new)
- `tests/rendering/kida/test_autoescape.py` (extend)
- `benchmarks/test_kida_filter_performance.py` (new)

---

### Task 2.3: Add Token Limit

**Reference**: Evaluation Report §3.4  
**Effort**: 2 hours  
**Risk**: Low  
**Impact**: Prevents DoS from malformed templates

**Changes**:
- `bengal/rendering/kida/lexer.py` — Add token count check

**Implementation Steps**:
1. Add `MAX_TOKENS = 100_000` constant (configurable)
2. Add token counter in `tokenize()` method
3. Check limit before yielding each token:
   ```python
   token_count += 1
   if token_count > MAX_TOKENS:
       raise LexerError(...)
   ```
4. Add test for token limit enforcement
5. Add test with legitimate large template (just under limit)
6. Document limit in error message

**Acceptance Criteria**:
- [ ] Token limit enforced in lexer
- [ ] Error raised when limit exceeded
- [ ] Test: Malformed template with excessive tokens raises error
- [ ] Test: Legitimate large template works (under limit)
- [ ] Error message includes suggestion to split template

**Files**:
- `bengal/rendering/kida/lexer.py`
- `tests/rendering/kida/test_lexer.py` (extend)

---

## Phase 3: Hardening & Code Quality (Low Risk)

**Goal**: Improve reliability and code maintainability.  
**Timeline**: 2-3 days  
**Risk**: Low  
**Dependencies**: Task 2.2 (HTML utils consolidation)

### Task 3.1: Improve Exception Handling

**Reference**: Evaluation Report §3.1  
**Effort**: 2 hours  
**Risk**: Low  
**Impact**: Better error visibility, debugging

**Changes**:
- `bengal/rendering/kida/analysis/analyzer.py:236` — Add logging, specific exceptions

**Implementation Steps**:
1. Add logging import:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
2. Replace broad `except Exception: pass` with specific handling:
   ```python
   except (AttributeError, TypeError) as e:
       logger.debug(f"Skipping node analysis: {type(node).__name__}: {e}")
   except Exception as e:
       logger.warning(f"Unexpected error analyzing {type(node).__name__}: {e}")
   ```
3. Add test verifying logging works
4. Add test with invalid AST node to verify handling

**Acceptance Criteria**:
- [ ] Specific exception types caught
- [ ] Debug logging for expected exceptions
- [ ] Warning logging for unexpected exceptions
- [ ] Test: Logging works correctly
- [ ] No silent failures

**Files**:
- `bengal/rendering/kida/analysis/analyzer.py`
- `tests/rendering/kida/test_analysis.py` (extend)

---

### Task 3.2: Enhance Filter Error Messages

**Reference**: Evaluation Report §3.3  
**Effort**: 3 hours  
**Risk**: Low  
**Impact**: Better developer experience

**Changes**:
- `bengal/rendering/kida/environment/filters.py` — Add strict mode parameter

**Implementation Steps**:
1. Identify filters with silent failure modes:
   - `_filter_int` — returns default on error
   - Any others found during code review
2. Add optional `strict: bool = False` parameter
3. In strict mode, raise `TemplateRuntimeError` with helpful message:
   ```python
   if strict:
       raise TemplateRuntimeError(
           f"Cannot convert {type(value).__name__} to int: {value!r}",
           suggestion="Use | default(0) | int for optional conversion",
       )
   ```
4. Keep default behavior unchanged (backward compatible)
5. Add test for strict mode
6. Document strict mode in filter docs

**Acceptance Criteria**:
- [ ] Strict mode parameter added to affected filters
- [ ] Default behavior unchanged (backward compatible)
- [ ] Test: Strict mode raises helpful errors
- [ ] Test: Default mode maintains silent fallback
- [ ] Documentation updated

**Files**:
- `bengal/rendering/kida/environment/filters.py`
- `tests/rendering/kida/test_filters.py` (extend)

---

### Task 3.3: Consolidate HTML Utilities

**Reference**: Evaluation Report §4.1  
**Effort**: 4 hours  
**Risk**: Low  
**Impact**: Code deduplication, maintainability

**Changes**:
- Extend `bengal/rendering/kida/utils/html.py` (from Task 2.2)
- Refactor `_filter_striptags`, `_filter_xmlattr`, `_filter_spaceless`

**Implementation Steps**:
1. Add remaining HTML utilities to `utils/html.py`:
   - `strip_tags()` — using pre-compiled regex (from Task 1.2)
   - `spaceless()` — remove whitespace between tags
   - `xmlattr()` — convert dict to XML attributes
2. Update filter functions to use utilities:
   - `_filter_striptags` → `strip_tags()`
   - `_filter_xmlattr` → `xmlattr()`
   - `_filter_spaceless` → `spaceless()`
3. Remove duplicate implementations
4. Add tests for all HTML utility functions
5. Verify filter behavior unchanged

**Acceptance Criteria**:
- [ ] All HTML utilities in `utils/html.py`
- [ ] Filters use shared utilities (no duplication)
- [ ] Test: All HTML functions work correctly
- [ ] Test: Filter behavior unchanged
- [ ] No code duplication

**Files**:
- `bengal/rendering/kida/utils/html.py` (extend from Task 2.2)
- `bengal/rendering/kida/environment/filters.py`
- `tests/rendering/kida/test_html_utils.py` (extend)

---

## Phase 4: Advanced Optimizations (Higher Risk)

**Goal**: Implement architectural optimizations requiring careful design.  
**Timeline**: 4-6 days  
**Risk**: Medium  
**Dependencies**: None (can parallelize)

### Task 4.1: Pre-allocate StringBuilder Buffer ✅ COMPLETED

**Reference**: Evaluation Report §1.3  
**Effort**: 8 hours (actual: ~8 hours)  
**Risk**: Medium (memory, dynamic content)  
**Impact**: 5-10% rendering speedup

**Status**: ✅ Completed 2024-12-26

**Implementation Summary**:
1. Added `PRE_ALLOC_THRESHOLD = 100` and `PRE_ALLOC_HEADROOM = 1.2` constants
2. Added `_use_prealloc` and `_buffer_size` computed properties for strategy selection
3. Created AST generation helpers: `_make_prealloc_buffer_init()`, `_make_prealloc_append_func()`,
   `_make_prealloc_join()`, `_make_dynamic_buffer_init()`, `_make_dynamic_join()`
4. Modified `_make_render_function()` to dispatch based on estimated output count
5. The `_append` abstraction allows statement compilation to work unchanged with both strategies
6. Block functions intentionally use dynamic buffers (smaller scope, less benefit)

**Key Design Decisions**:
- Pre-allocation uses indexed assignment (`buf[_idx] = val`) with overflow fallback
- Overflow protection: If `_idx >= _buf_len`, falls back to `buf.append(val)`
- Final join uses conditional slice: `''.join(buf[:_idx] if _idx < _buf_len else buf)`
- 20% headroom (`PRE_ALLOC_HEADROOM = 1.2`) handles minor estimation variance

**Acceptance Criteria**:
- [x] Buffer size estimation passed to compiler (`estimated_output_count` param)
- [x] Pre-allocation generated for large templates (≥100 outputs)
- [x] Fallback to dynamic growth for small/uncertain templates (<100 outputs)
- [x] Test: Pre-allocation works correctly (24 tests in `test_buffer_preallocation.py`)
- [x] Test: Fallback works for dynamic content (overflow tests pass)
- [x] Benchmark: Baseline established (12 benchmarks in `test_kida_buffer_performance.py`)

**Files Modified/Created**:
- `bengal/rendering/kida/compiler/core.py` — Added pre-allocation logic
- `tests/rendering/kida/test_buffer_preallocation.py` — New (24 tests)
- `benchmarks/test_kida_buffer_performance.py` — New (12 benchmarks)

---

### Task 4.2: Expand Dead Code Elimination

**Reference**: Evaluation Report §2.1  
**Effort**: 6 hours  
**Risk**: Medium (incorrect elimination)  
**Impact**: 5-15% smaller compiled templates

**Changes**:
- `bengal/rendering/kida/optimizer/dead_code_eliminator.py` — Extend elimination logic

**Implementation Steps**:
1. Extend `_eliminate_if()` to handle `{% if true %}...{% elif x %}...{% end %}`:
   - Return body contents directly, eliminate elif/else
2. Add elimination for empty blocks: `{% block empty %}{% end %}`
3. Add elimination for empty for loops: `{% for x in [] %}...{% end %}`
4. Add elimination for match with only default case
5. Add comprehensive tests for each elimination case
6. Verify no incorrect eliminations (conservative approach)

**Acceptance Criteria**:
- [ ] `{% if true %}` eliminates elif/else branches
- [ ] Empty blocks eliminated
- [ ] Empty for loops eliminated
- [ ] Match with only default eliminated
- [ ] Test: All elimination cases work correctly
- [ ] Test: No incorrect eliminations

**Files**:
- `bengal/rendering/kida/optimizer/dead_code_eliminator.py`
- `tests/rendering/kida/test_dead_code_elimination.py` (extend)

---

### Task 4.3: AST Node Memory Optimization

**Reference**: Evaluation Report §2.2  
**Effort**: 4 hours  
**Risk**: Medium (breaking change)  
**Impact**: Reduced memory per AST node (~20 bytes per dict)

**Changes**:
- `bengal/rendering/kida/nodes.py` — Change default factories to `None`

**Implementation Steps**:
1. Identify nodes with excessive default factories:
   - `FuncCall.kwargs` — `field(default_factory=dict)`
   - Any others found during code review
2. Change to `None` defaults with property accessor:
   ```python
   _kwargs: dict[str, Expr] | None = None

   @property
   def kwargs(self) -> dict[str, Expr]:
       return self._kwargs or {}
   ```
3. Update all AST traversal code to use property (not private field)
4. Add tests verifying AST traversal still works
5. Verify memory reduction (optional: memory profiling)

**Acceptance Criteria**:
- [ ] Default factories changed to `None`
- [ ] Property accessors maintain API compatibility
- [ ] Test: AST traversal works correctly
- [ ] Test: All node types accessible via properties
- [ ] No breaking changes to public API

**Files**:
- `bengal/rendering/kida/nodes.py`
- `tests/rendering/kida/test_nodes.py` (extend)
- `tests/rendering/kida/test_ast_traversal.py` (extend)

---

### Task 4.4: Extract AST Traversal Utilities

**Reference**: Evaluation Report §4.2  
**Effort**: 8 hours  
**Risk**: Medium (refactoring)  
**Impact**: Code deduplication, maintainability

**Changes**:
- Create `bengal/rendering/kida/utils/ast_visitor.py` (new)
- Refactor 4 optimizers to use utilities

**Implementation Steps**:
1. Create `utils/ast_visitor.py` with `transform_children()` utility:
   ```python
   def transform_children(
       node: T,
       transform: Callable[[Any], Any],
       fields: tuple[str, ...] = ("body", "else_", "empty", "elif_"),
   ) -> T:
       """Transform children of a container node."""
       ...
   ```
2. Identify optimizers with duplicated traversal logic:
   - `ConstantFolder._fold_container`
   - `DeadCodeEliminator._eliminate_container`
   - `FilterInliner._inline_container`
   - `DataCoalescer` (similar pattern)
3. Refactor each optimizer to use `transform_children()`
4. Add tests verifying optimizer behavior unchanged
5. Verify no performance regression

**Acceptance Criteria**:
- [ ] `utils/ast_visitor.py` created with `transform_children()`
- [ ] 4 optimizers refactored to use utility
- [ ] Test: Optimizer behavior unchanged
- [ ] Test: No performance regression
- [ ] Code duplication eliminated

**Files**:
- `bengal/rendering/kida/utils/ast_visitor.py` (new)
- `bengal/rendering/kida/optimizer/constant_folder.py`
- `bengal/rendering/kida/optimizer/dead_code_eliminator.py`
- `bengal/rendering/kida/optimizer/filter_inliner.py`
- `bengal/rendering/kida/optimizer/data_coalescer.py`
- `tests/rendering/kida/test_optimizers.py` (extend)

---

### Task 4.5: Pre-compute Template Metadata

**Reference**: Evaluation Report §2.4  
**Effort**: 4 hours  
**Risk**: Low  
**Impact**: Faster first access to `block_metadata()`, `depends_on()`

**Changes**:
- `bengal/rendering/kida/template.py:958-971` — Pre-compute during compilation
- `bengal/rendering/kida/environment.py` — Pass metadata to Template

**Implementation Steps**:
1. In `Environment._compile()`, when `preserve_ast=True`:
   - Run `BlockAnalyzer` during compilation
   - Pass `precomputed_metadata` to `Template` constructor
2. Update `Template` to accept `precomputed_metadata` parameter
3. Use precomputed metadata if available, otherwise compute on demand
4. Add test verifying metadata correctness
5. Add test verifying faster first access

**Acceptance Criteria**:
- [ ] Metadata pre-computed during compilation
- [ ] Template uses precomputed metadata if available
- [ ] Test: Metadata correctness verified
- [ ] Test: First access faster (optional benchmark)
- [ ] Backward compatible (fallback to on-demand computation)

**Files**:
- `bengal/rendering/kida/template.py`
- `bengal/rendering/kida/environment.py`
- `tests/rendering/kida/test_template.py` (extend)

---

### Task 4.6: Consolidate Error Formatting

**Reference**: Evaluation Report §4.3  
**Effort**: 6 hours  
**Risk**: Low  
**Impact**: Code deduplication, consistent error messages

**Changes**:
- Create `bengal/rendering/kida/utils/errors.py` (new)
- Refactor 4 error classes to use utilities

**Implementation Steps**:
1. Create `utils/errors.py` with formatting utilities:
   ```python
   def format_source_context(
       source: str | None,
       lineno: int,
       col_offset: int,
       context_lines: int = 1,
   ) -> str:
       """Format source context with line numbers and caret."""
       ...

   def format_suggestion(suggestion: str | None) -> str:
       """Format suggestion section."""
       ...
   ```
2. Identify error classes with duplicated formatting:
   - `LexerError._format_message`
   - `TemplateSyntaxError._format_message`
   - `TemplateRuntimeError._format_message`
   - `UndefinedError._format_message`
3. Refactor each error class to use utilities
4. Add tests verifying error messages unchanged
5. Verify formatting consistency

**Acceptance Criteria**:
- [ ] `utils/errors.py` created with formatting utilities
- [ ] 4 error classes refactored to use utilities
- [ ] Test: Error messages unchanged
- [ ] Test: Formatting consistent across error types
- [ ] Code duplication eliminated

**Files**:
- `bengal/rendering/kida/utils/errors.py` (new)
- `bengal/rendering/kida/errors/lexer_error.py`
- `bengal/rendering/kida/errors/template_syntax_error.py`
- `bengal/rendering/kida/errors/template_runtime_error.py`
- `bengal/rendering/kida/errors/undefined_error.py`
- `tests/rendering/kida/test_errors.py` (extend)

---

### Task 4.7: Add Bytecode Cache Cleanup

**Reference**: Evaluation Report §2.3  
**Effort**: 3 hours  
**Risk**: Low  
**Impact**: Prevents disk bloat

**Changes**:
- `bengal/rendering/kida/bytecode_cache.py` — Add cleanup method

**Implementation Steps**:
1. Add `cleanup(max_age_days: int = 30)` method:
   ```python
   def cleanup(self, max_age_days: int = 30) -> int:
       """Remove orphaned cache files older than max_age_days."""
       threshold = time.time() - (max_age_days * 86400)
       count = 0
       for path in self._dir.glob("__kida_*.pyc"):
           if path.stat().st_mtime < threshold:
               path.unlink(missing_ok=True)
               count += 1
       return count
   ```
2. Add test for cleanup logic
3. Add test verifying active cache files not deleted
4. Document cleanup method

**Acceptance Criteria**:
- [ ] `cleanup()` method implemented
- [ ] Orphaned cache files removed based on age
- [ ] Test: Cleanup removes old files
- [ ] Test: Active cache files preserved
- [ ] Documentation added

**Files**:
- `bengal/rendering/kida/bytecode_cache.py`
- `tests/rendering/kida/test_bytecode_cache.py` (extend)

---

## Testing Strategy

### For Each Task

**Unit Tests**:
- Test optimization logic in isolation
- Verify edge cases (empty inputs, None values, etc.)
- Test error handling

**Integration Tests**:
- Test with real templates
- Verify output matches expected result
- Test with various template structures

**Performance Benchmarks** (for performance tasks):
- Run benchmark suite (see evaluation report §5.4)
- Validate speedup claims meet thresholds
- Compare against baseline (current implementation)
- Statistical significance: p < 0.05

**Regression Tests**:
- Run full test suite
- Verify no existing tests break
- Test backward compatibility

### Benchmark Execution

**Prerequisites**:
- Python 3.11+
- `pytest-benchmark` installed
- Warm system (minimize background tasks)

**Execution**:
```bash
# Run all performance benchmarks
pytest benchmarks/test_kida_lexer_performance.py -v
pytest benchmarks/test_kida_filter_performance.py -v
pytest benchmarks/test_kida_buffer_performance.py -v
pytest benchmarks/test_kida_filter_inlining.py -v
pytest benchmarks/test_kida_regex_caching.py -v

# Run with benchmark output
pytest benchmarks/ --benchmark-only --benchmark-json=results.json
```

**Validation Criteria**:
- **Iterations**: Run 10 iterations, use median value
- **Baseline**: Compare against current implementation (before optimization)
- **Success Threshold**:
  - Lexer `_advance()`: ≥15% improvement (p < 0.05)
  - Escape filter: ≥2x improvement (p < 0.05)
  - Filter inlining: ≥5% improvement (p < 0.05)
  - Buffer pre-allocation: ≥5% improvement (p < 0.05)
  - Regex caching: ≥10% improvement (p < 0.05)

---

## Risk Mitigation

### Critical Risks

**1. Escape Consolidation (Task 2.2)**:
- **Risk**: Autoescape behavior change
- **Mitigation**: Preserve Markup return type, extensive integration tests
- **Validation**: Test with Markup objects, verify no double-escaping

**2. Filter Inlining (Task 1.1)**:
- **Risk**: Breaks user filter overrides
- **Mitigation**: Document override behavior, provide opt-out, detect overrides
- **Validation**: Test filter override still works when inlining enabled

**3. Buffer Pre-allocation (Task 4.1)**:
- **Risk**: Memory waste for small templates
- **Mitigation**: Only pre-allocate if estimation > 100 items, fallback to dynamic
- **Validation**: Memory profiling, test with dynamic content

**4. Lexer Optimization (Task 2.1)**:
- **Risk**: Off-by-one in column tracking
- **Mitigation**: Comprehensive test cases for edge cases
- **Validation**: Test column tracking accuracy matches original

---

## Success Criteria

### Performance
- [ ] Lexer `_advance()` shows ≥15% speedup (benchmark validated, p < 0.05)
- [ ] Escape filter shows ≥2x speedup (benchmark validated, p < 0.05)
- [ ] Filter inlining shows ≥5% speedup (benchmark validated, p < 0.05)
- [ ] Buffer pre-allocation shows ≥5% speedup (benchmark validated, p < 0.05)
- [ ] Regex caching shows ≥10% speedup for affected filters (benchmark validated)

### Reliability
- [ ] Include recursion limit prevents DoS (tested with circular includes)
- [ ] Token limit prevents DoS (tested with malformed templates)
- [ ] Exception handling logs unexpected errors (tested with invalid AST nodes)
- [ ] All existing tests pass (full test suite)

### Code Quality
- [ ] HTML utilities consolidated (no duplication)
- [ ] AST traversal utilities extracted (4 optimizers refactored)
- [ ] Error formatting consolidated (4 error classes refactored)
- [ ] No code duplication (verified via code review)

### Backward Compatibility
- [ ] All existing templates render identically
- [ ] API surface unchanged
- [ ] Configuration opt-in works correctly

---

## Timeline & Milestones

### Week 1: Quick Wins & Performance
- **Day 1-2**: Phase 1 (Quick Wins) — 4 tasks, ~6 hours
- **Day 3-5**: Phase 2 (Performance) — 3 tasks, ~12 hours
- **Milestone**: 10-25% performance improvement validated

### Week 2: Hardening & Advanced (Part 1)
- **Day 1-3**: Phase 3 (Hardening) — 3 tasks, ~9 hours
- **Day 4-5**: Phase 4 (Advanced) — Tasks 4.1-4.3, ~18 hours
- **Milestone**: Reliability improvements complete, code quality improved

### Week 3: Advanced (Part 2)
- **Day 1-3**: Phase 4 (Advanced) — Tasks 4.4-4.7, ~21 hours
- **Day 4-5**: Final testing, documentation, cleanup
- **Milestone**: All improvements complete, full test suite passes

---

## Dependencies & Parallelization

### Dependency Graph
```
1.2 (Escape) ──┐
               ├──> 4.1 (HTML Utils)
1.5 (Regex) ───┘

1.4 (Inlining) ──> Independent

3.2 (Recursion) ──> Independent (Security fix)

1.1 (Lexer) ──> Independent
1.3 (Buffer) ──> Independent
```

### Can Parallelize
- **Phase 1**: All 4 tasks (1.1, 1.4, 1.5, 1.6, 3.2) — no dependencies
- **Phase 2**: All 3 tasks (2.1, 2.2, 2.3) — no dependencies
- **Phase 3**: Tasks 3.1, 3.3 — independent (3.2 depends on 2.2)
- **Phase 4**: All 7 tasks — no dependencies between them

### Must Complete First
- **Task 2.2** (Escape consolidation) → **Task 3.3** (HTML utils) — same code, consolidate together

---

## Rollback Strategy

If an optimization causes issues:

1. **Disable via Config**: Set optimization flag to `False` in `OptimizationConfig`
2. **Version Pin**: Pin to previous version if needed
3. **Report Issue**: File issue with reproduction case

**Example Rollback**:
```python
from bengal.rendering.kida import Environment, OptimizationConfig

# Disable problematic optimization
config = OptimizationConfig(filter_inlining=False)
env = Environment(optimization_config=config)
```

---

## Appendix: File Reference

| Category | File | Line(s) | Task |
|----------|------|---------|------|
| Lexer | `bengal/rendering/kida/lexer.py` | 664-673 | 2.1, 2.3 |
| Template | `bengal/rendering/kida/template.py` | 803-824, 278-298 | 2.2, 1.4 |
| Filters | `bengal/rendering/kida/environment/filters.py` | 93-110, 542-546 | 1.2, 1.5, 1.6, 2.2, 3.2 |
| Optimizer | `bengal/rendering/kida/optimizer/__init__.py` | 59 | 1.1 |
| Compiler | `bengal/rendering/kida/compiler/core.py` | 376-380 | 4.1 |
| Analyzer | `bengal/rendering/kida/analysis/analyzer.py` | 236 | 3.1 |
| Cache | `bengal/rendering/kida/bytecode_cache.py` | all | 4.7 |
| Nodes | `bengal/rendering/kida/nodes.py` | all | 4.3 |

---

## Next Steps

1. **Review Plan**: Review this plan for completeness and accuracy
2. **Prioritize**: Confirm phase ordering and task priorities
3. **Assign**: Assign tasks to developers (if team)
4. **Start Phase 1**: Begin with Task 1.1 (Filter Inlining) — lowest risk, high impact
5. **Track Progress**: Update task status as work progresses

---

**Status**: Ready for implementation  
**Last Updated**: 2025-12-26
