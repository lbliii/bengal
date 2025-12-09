# 📋 Implementation Plan: Directive System v2

**RFC**: `plan/active/rfc-directive-system-v2.md`  
**Branch**: `refactor/directives`  
**Created**: 2025-12-09  
**Status**: Ready for Implementation

---

## Executive Summary

Implement the Directive System v2 to eliminate fence-depth cascade pain and catch invalid nesting at parse time. This involves creating a new foundation (base class, typed options, contracts), adding named closure syntax parsing, and migrating existing directives incrementally.

**Estimated Time**: 3-4 days  
**Complexity**: Complex (foundational change with incremental migration)  
**Confidence Gates**: Foundation ≥90%, Migration ≥85%

---

## Plan Details

- **Total Tasks**: 28 tasks across 4 phases
- **Critical Path**: Phase 1 Foundation → Phase 2.1 Parser → Phase 2.2 Migration
- **Risk**: Parser changes must be backward compatible

---

## Phase 1: Foundation (8 tasks)

Create the new infrastructure files without changing any existing code.

### Rendering Infrastructure (`bengal/rendering/plugins/directives/`)

#### Task 1.1: Create DirectiveToken dataclass ✅
- **Files**: `bengal/rendering/plugins/directives/tokens.py`
- **Action**:
  - Create `DirectiveToken` dataclass with `type`, `attrs`, `children`
  - Add `to_dict()` for mistune compatibility
  - Add `from_dict()` for testing
- **Dependencies**: None
- **Status**: completed
- **Commit**: `rendering(directives): add DirectiveToken dataclass for typed AST tokens`

#### Task 1.2: Create DirectiveOptions base class ✅
- **Files**: `bengal/rendering/plugins/directives/options.py`
- **Action**:
  - Create `DirectiveOptions` base dataclass with `from_raw()` parser
  - Add type coercion logic (str→bool, str→int, str→list)
  - Add `_field_aliases` and `_allowed_values` class vars
  - Create `StyledOptions` preset (css_class field)
  - Create `ContainerOptions` preset (columns, gap, style)
- **Dependencies**: None
- **Status**: completed
- **Commit**: `rendering(directives): add DirectiveOptions base class with type coercion`

#### Task 1.3: Create shared utilities module ✅
- **Files**: `bengal/rendering/plugins/directives/utils.py`
- **Action**:
  - Extract `escape_html()` function
  - Add `build_class_string()` function
  - Add `bool_attr()` function
  - Add `data_attrs()` function
- **Dependencies**: None
- **Status**: completed
- **Commit**: `rendering(directives): extract shared utilities to utils.py`

#### Task 1.4: Create DirectiveContract system ✅
- **Files**: `bengal/rendering/plugins/directives/contracts.py`
- **Action**:
  - Create `DirectiveContract` frozen dataclass
  - Create `ContractViolation` dataclass
  - Create `ContractValidator` with `validate_parent()` and `validate_children()`
  - Define preset contracts: `STEPS_CONTRACT`, `STEP_CONTRACT`, `TAB_SET_CONTRACT`, `TAB_ITEM_CONTRACT`, `CARDS_CONTRACT`, `CARD_CONTRACT`
- **Dependencies**: None
- **Status**: completed
- **Commit**: `rendering(directives): add DirectiveContract system for nesting validation`

#### Task 1.5: Create BengalDirective base class ✅
- **Files**: `bengal/rendering/plugins/directives/base.py`
- **Action**:
  - Create `BengalDirective` extending `DirectivePlugin`
  - Add class attrs: `NAMES`, `TOKEN_TYPE`, `OPTIONS_CLASS`, `CONTRACT`
  - Implement `parse()` template method with contract validation
  - Add abstract `parse_directive()` and `render()` methods
  - Add utility methods: `escape_html()`, `build_class_string()`, `bool_attr()`
  - Add `_get_parent_directive_type()` and `_get_source_location()` helpers
- **Dependencies**: Task 1.1, 1.2, 1.3, 1.4
- **Status**: completed
- **Commit**: `rendering(directives): add BengalDirective base class with contract validation`

#### Task 1.6: Update directives package exports ✅
- **Files**: `bengal/rendering/plugins/directives/__init__.py`
- **Action**:
  - Export new classes: `BengalDirective`, `DirectiveToken`, `DirectiveOptions`, `DirectiveContract`
  - Export preset options: `StyledOptions`, `ContainerOptions`
  - Export utilities: `escape_html`, `build_class_string`, `bool_attr`, `data_attrs`
  - Keep all existing exports
- **Dependencies**: Task 1.1-1.5
- **Status**: completed
- **Commit**: `rendering(directives): export new foundation classes from __init__.py`

---

### Tests (`tests/unit/rendering/`)

#### Task 1.7: Add foundation unit tests ✅
- **Files**: `tests/unit/rendering/directives/test_foundation.py`
- **Action**:
  - Test `DirectiveToken.to_dict()` and `from_dict()`
  - Test `DirectiveOptions.from_raw()` type coercion (bool, int, list)
  - Test `DirectiveOptions._allowed_values` validation
  - Test `DirectiveOptions._field_aliases` mapping
  - Test utility functions
- **Dependencies**: Task 1.1-1.3
- **Status**: completed
- **Commit**: `tests(directives): add unit tests for foundation classes`

#### Task 1.8: Add contract validation tests ✅
- **Files**: `tests/unit/rendering/directives/test_contracts.py`
- **Action**:
  - Test `ContractValidator.validate_parent()` - valid and invalid cases
  - Test `ContractValidator.validate_children()` - required, min, max, allowed
  - Test `ContractViolation.to_log_dict()` format
  - Test preset contracts (STEPS, TABS, CARDS)
- **Dependencies**: Task 1.4
- **Status**: completed
- **Commit**: `tests(directives): add unit tests for DirectiveContract validation`

---

## Phase 2: Implementation (12 tasks)

### 2.1 Named Closure Parser

#### Task 2.1: Extend FencedDirective for named closers
- **Files**: `bengal/rendering/plugins/directives/fenced.py`
- **Action**:
  - Add regex pattern for `:::{/name}` named closer
  - Modify parsing to match named closer to opener
  - Ensure standard `:::` counting still works
  - Named closer takes precedence over depth counting when matched
- **Dependencies**: Phase 1 complete
- **Status**: pending
- **Commit**: `rendering(directives): add named closure syntax :::{/name} to FencedDirective`

#### Task 2.2: Add named closure parser tests
- **Files**: `tests/unit/rendering/directives/test_named_closers.py`
- **Action**:
  - Test basic named closer: `:::{note}...:::{/note}`
  - Test nested named closers: tabs with tab-items
  - Test mixed syntax: named outer, standard inner
  - Test backward compatibility: standard fences still work
  - Test mismatched names produce error/warning
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `tests(directives): add unit tests for named closure syntax`

---

### 2.2 Pilot Migration (Simple Directives)

#### Task 2.3: Migrate DropdownDirective (pilot) ✅
- **Files**: `bengal/rendering/plugins/directives/dropdown.py`
- **Action**:
  - Create `DropdownOptions` dataclass with `open: bool`, `css_class: str`
  - Convert `DropdownDirective` to extend `BengalDirective`
  - Move `render_dropdown` into class as `render()` method
  - Verify all existing tests pass
- **Dependencies**: Task 1.5
- **Status**: completed
- **Commit**: `rendering(directives): migrate DropdownDirective to BengalDirective base class`

#### Task 2.4: Migrate ContainerDirective ✅
- **Files**: `bengal/rendering/plugins/directives/container.py`
- **Action**:
  - Create `ContainerOptions` dataclass with css_class field
  - Convert to `BengalDirective`
  - Integrate render method
- **Dependencies**: Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate ContainerDirective to BengalDirective base class`

#### Task 2.5: Migrate RubricDirective ✅
- **Files**: `bengal/rendering/plugins/directives/rubric.py`
- **Action**: Convert to `BengalDirective` pattern with `RubricOptions`
- **Dependencies**: Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate RubricDirective to BengalDirective base class`

#### Task 2.6: Migrate ButtonDirective ✅
- **Files**: `bengal/rendering/plugins/directives/button.py`
- **Action**: Convert to `BengalDirective` pattern with `ButtonOptions`
- **Dependencies**: Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate ButtonDirective to BengalDirective base class`

#### Task 2.7: Migrate BadgeDirective ✅
- **Files**: `bengal/rendering/plugins/directives/badge.py`
- **Action**: Convert to `BengalDirective` pattern with `BadgeOptions`
- **Dependencies**: Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate BadgeDirective to BengalDirective base class`

---

### 2.3 Container Directives (with Contracts)

#### Task 2.8: Migrate StepsDirective with contracts ✅
- **Files**: `bengal/rendering/plugins/directives/steps.py`
- **Action**:
  - Create `StepsOptions` and `StepOptions` dataclasses
  - Convert `StepsDirective` with `CONTRACT = STEPS_CONTRACT`
  - Convert `StepDirective` with `CONTRACT = STEP_CONTRACT`
  - Validate parent-child relationship at parse time
  - Integrate render methods into classes
- **Dependencies**: Task 1.4, Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate StepsDirective with DirectiveContract validation`

#### Task 2.9: Migrate TabsDirective with contracts ✅
- **Files**: `bengal/rendering/plugins/directives/tabs.py`
- **Action**:
  - Create `TabSetOptions`, `TabItemOptions` dataclasses
  - Convert `TabSetDirective` with `CONTRACT = TAB_SET_CONTRACT`
  - Convert `TabItemDirective` with `CONTRACT = TAB_ITEM_CONTRACT`
  - Handle `TabsDirective` (legacy) compatibility
- **Dependencies**: Task 1.4, Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate TabsDirective with DirectiveContract validation`

#### Task 2.10: Migrate CardsDirective with contracts ✅
- **Files**: `bengal/rendering/plugins/directives/cards.py`
- **Action**:
  - Create `CardsOptions`, `CardOptions`, `ChildCardsOptions` dataclasses
  - Convert `CardsDirective`, `CardDirective`, `ChildCardsDirective` to `BengalDirective`
  - Keep `GridDirective`, `GridItemCardDirective` as legacy compatibility shims
  - Add contracts for parent-child validation
- **Dependencies**: Task 1.4, Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate CardsDirective family to BengalDirective base class with typed options`

---

### 2.4 Remaining Directives

#### Task 2.11: Migrate AdmonitionDirective ✅
- **Files**: `bengal/rendering/plugins/directives/admonitions.py`
- **Action**:
  - Create `AdmonitionOptions` dataclass
  - Convert to `BengalDirective`
  - Handle 10 directive names with single TOKEN_TYPE pattern
  - Override `parse()` to capture admon_type before calling parent
- **Dependencies**: Task 2.3
- **Status**: completed
- **Commit**: `rendering(directives): migrate AdmonitionDirective to BengalDirective with multi-name registration`

#### Task 2.12: Migrate remaining directives (batch) ✅
- **Files Migrated**:
  - `checklist.py` - ChecklistDirective
  - `icon.py` - IconDirective (with invalid size fallback)
  - `code_tabs.py` - CodeTabsDirective
  - `navigation.py` - BreadcrumbsDirective, SiblingsDirective, PrevNextDirective, RelatedDirective
- **Files NOT Migrated** (complex path/security/stateful handling):
  - `include.py` - Complex path resolution and security checks
  - `literalinclude.py` - Complex path resolution and security checks
  - `glossary.py` - Deferred data loading pattern
  - `data_table.py` - Data file loading and config
  - `list_table.py` - Custom row parsing logic
  - `marimo.py` - Stateful execution and caching
- **Dependencies**: Task 2.11
- **Status**: completed
- **Commit**: `rendering(directives): migrate Checklist, Icon, CodeTabs, Navigation directives to BengalDirective base class`

---

## Phase 3: Validation (5 tasks) ✅

### Test Suite

#### Task 3.1: Update existing directive tests ✅
- **Files**: Existing tests verified
- **Action**:
  - Verified all existing tests still pass (979 tests)
  - Contract validation warnings properly emitted
  - Named closer syntax deferred to Phase 4 (optional feature)
- **Dependencies**: Phase 2 complete
- **Status**: completed
- **Result**: 979 tests pass, 1 skipped

#### Task 3.2: Add integration tests for nesting validation ✅
- **Files**: `tests/integration/test_directive_nesting.py`
- **Action**:
  - Test orphaned `step` produces warning and still renders
  - Test orphaned `tab-item` produces warning and still renders  
  - Test valid nesting produces correct HTML structure
  - Test cards/card soft validation
- **Dependencies**: Task 2.8, Task 2.9
- **Status**: completed
- **Commit**: `tests(directives): add integration tests for directive nesting validation; fix linting`

---

### Linting and Health

#### Task 3.3: Run linter and fix issues ✅
- **Files**: All modified files
- **Action**:
  - Run `ruff check bengal/rendering/plugins/directives/ --fix`
  - Run `ruff format bengal/rendering/plugins/directives/`
  - 4 files reformatted
- **Dependencies**: Phase 2 complete
- **Status**: completed
- **Result**: Linting clean except pre-existing line-length issues in validator.py

#### Task 3.4: Update health validators ✅
- **Files**: `bengal/health/validators/directives/constants.py`
- **Action**:
  - Added import for ADMONITION_TYPES, CODE_BLOCK_DIRECTIVES from rendering package
  - Single source of truth pattern maintained
  - Health checks now properly import type constants
- **Dependencies**: Phase 2 complete
- **Status**: completed
- **Commit**: `health(validators): fix ADMONITION_TYPES import from rendering package (single source of truth)`

#### Task 3.5: Run full test suite ✅
- **Files**: None (command only)
- **Action**:
  - `pytest tests/unit/rendering/` - 979 passed, 1 skipped
  - `pytest tests/integration/test_directive_nesting.py` - 11 passed
- **Dependencies**: Task 3.1-3.4
- **Status**: completed
- **Result**: All tests passing

---

## Phase 4: Polish (3 tasks) ✅

### Documentation

#### Task 4.1: Update rendering architecture docs ✅
- **Files**: `bengal/rendering/plugins/directives/README.md`
- **Action**:
  - Documented `BengalDirective` base class pattern with examples
  - Documented `DirectiveContract` system with validation rules
  - Added migration guide from legacy to new directives
  - Documented all available directives with quick reference table
- **Dependencies**: Phase 3 complete
- **Status**: completed
- **Commit**: `docs(directives): add README with architecture overview and migration guide`

#### Task 4.2: Update directive README ✅
- **Files**: `bengal/rendering/plugins/directives/README.md`
- **Action**:
  - Documented all 19+ directives with descriptions
  - Added options documentation and examples
  - Created file structure reference
- **Dependencies**: Task 4.1
- **Status**: completed (combined with 4.1)

#### Task 4.3: Update changelog ✅
- **Files**: `changelog.md`
- **Action**:
  - Added comprehensive entry for directive system v2
  - Documented new features: typed tokens, options, contracts
  - Noted 19 migrated directives and 90+ new tests
  - No breaking changes (backward compatible)
- **Dependencies**: Phase 4 tasks complete
- **Status**: completed
- **Commit**: `docs: update changelog for directive system v2`

---

## 📊 Task Summary

| Area | Tasks | Status |
|------|-------|--------|
| Foundation | 6 | ✅ completed |
| Tests (Foundation) | 2 | ✅ completed |
| Parser | 2 | ⏸️ deferred (named closers optional) |
| Migration (Simple) | 5 | ✅ completed |
| Migration (Container) | 3 | ✅ completed |
| Migration (Remaining) | 2 | ✅ completed |
| Validation | 5 | ✅ completed |
| Documentation | 3 | ✅ completed |
| **Total** | **28** | **26 completed, 2 deferred** |

---

## Dependency Graph

```
Phase 1: Foundation (parallel)
├── Task 1.1: tokens.py ────────────────┐
├── Task 1.2: options.py ───────────────┤
├── Task 1.3: utils.py ─────────────────┼──▶ Task 1.5: base.py ──▶ Task 1.6: __init__.py
├── Task 1.4: contracts.py ─────────────┘
├── Task 1.7: test_foundation.py (after 1.1-1.3)
└── Task 1.8: test_contracts.py (after 1.4)

Phase 2: Implementation
├── Task 2.1: fenced.py (named closers) ──▶ Task 2.2: tests
└── Task 2.3: dropdown.py (pilot) ──▶ Task 2.4-2.7 (simple)
                                   ──▶ Task 2.8-2.10 (container)
                                   ──▶ Task 2.11-2.12 (remaining)

Phase 3: Validation (sequential)
Task 3.1 ──▶ Task 3.2 ──▶ Task 3.3 ──▶ Task 3.4 ──▶ Task 3.5

Phase 4: Polish (sequential)
Task 4.1 ──▶ Task 4.2 ──▶ Task 4.3
```

---

## 📋 Next Steps

1. [ ] Review plan for completeness
2. [ ] Begin Phase 1 with `::implement Task 1.1`
3. [ ] Track progress by updating task statuses in this document
4. [ ] After Phase 1, validate with `pytest tests/unit/rendering/directives/`

---

## Validation Checklist

**Phase 1 Complete When**:
- [ ] All foundation files created
- [ ] All unit tests pass
- [ ] Exports updated in `__init__.py`

**Phase 2 Complete When**:
- [ ] Named closure syntax works
- [ ] All 24 directives migrated
- [ ] Contract validation produces warnings for invalid nesting
- [ ] Existing functionality unchanged

**Phase 3 Complete When**:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Linter passes
- [ ] Health validators pass

**Phase 4 Complete When**:
- [ ] Architecture docs updated
- [ ] README created
- [ ] Changelog updated

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Parser breaks existing content | Test backward compatibility first in Task 2.2 |
| Migration breaks directive output | Pilot with DropdownDirective (Task 2.3) before others |
| Contract warnings too noisy | Make warnings opt-in via config flag initially |
| Performance regression | Benchmark before/after Phase 2 |

---

**Ready to begin**: Run `::implement Task 1.1` to start
