# RFC: Directive Package Test Maturity

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/directives/`  
**Confidence**: 95% 🟢 (metrics verified via find/grep/wc across source and test files)  
**Priority**: P2 (Medium) — Infrastructure layer needs focused unit testing  
**Estimated Effort**: 1.5-2 days (single dev)

---

## Executive Summary

The `bengal/directives/` package has **47 source files** with **strong directive behavior coverage** but **weak infrastructure unit testing**. Directive rendering is well-tested through integration and rendering test files, but the foundation classes (`base.py`, `factory.py`, `options.py`, `validator.py`) lack focused unit tests.

**Current state**:
- **20+ directive test files** across `tests/unit/rendering/`, `tests/unit/directives/`, and `tests/integration/`
- **~9,500+ LOC** of directive-related tests
- **Strong coverage**: admonitions (16+ tests), dropdown (10+ tests), gallery (11 tests), media (185+ tests), badges (22+ tests)
- **Weak coverage**: infrastructure layer (base, factory, options) — tested only indirectly

**True gaps**:
- `base.py` (568 LOC) — foundation class, no direct unit tests
- `factory.py` (~100 LOC) — instantiation logic, no unit tests
- `options.py` (433 LOC) — option parsing, partial coverage via `test_foundation.py`
- `validator.py` (644 LOC) — validation logic, tested only via health validators
- **2 TODO comments** in `marimo.py` (caching feature incomplete)

**Recommendation**: Create infrastructure unit tests for `base.py`, `factory.py`, and `options.py`, then address type safety improvements.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Coverage Analysis](#coverage-analysis)
4. [Gap Analysis](#gap-analysis)
5. [Incomplete Implementations](#incomplete-implementations)
6. [Type Safety Analysis](#type-safety-analysis)
7. [Proposed Test Plan](#proposed-test-plan)
8. [Implementation Phases](#implementation-phases)
9. [Success Criteria](#success-criteria)
10. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

Directives are a **core user-facing feature** of Bengal. The directive infrastructure (`base.py`, `factory.py`, `options.py`) provides:
- Automatic registration via `NAMES` and `TOKEN_TYPE`
- Typed option parsing via `OPTIONS_CLASS`
- Contract-based nesting validation via `CONTRACT`
- Error context creation for debugging

Without infrastructure unit tests:
- **Regressions in option parsing** go undetected
- **Registration edge cases** are undiscovered
- **Error handling paths** are untested
- **Refactoring is risky** — no safety net for foundation changes

### Current Coverage Summary

| Location | Test Files | LOC | Focus |
|----------|------------|-----|-------|
| `tests/unit/rendering/test_*directive*.py` | 15 | ~5,968 | Directive behavior |
| `tests/unit/rendering/directives/` | 5 | ~2,200 | Media, foundation, contracts |
| `tests/unit/directives/` | 4 | ~1,116 | Tabs, tokens, priority |
| `tests/integration/test_*directive*.py` | 3 | ~500 | Nesting, gallery |
| **Total** | **27** | **~9,784** | — |

**Directive behavior is well-tested. Infrastructure is not.**

---

## Current State Evidence

### Existing Test Files

**`tests/unit/rendering/directives/`** (5 files, ~2,200 LOC):

| Test File | What It Tests | LOC |
|-----------|---------------|-----|
| `test_media_directives.py` | YouTube, Vimeo, Gist, CodePen, Figure, Audio, etc. | 1,217 |
| `test_foundation.py` | DirectiveToken, DirectiveOptions, utilities | 462 |
| `test_named_closers.py` | Named fence closers | ~250 |
| `test_contracts.py` | Nesting validation contracts | ~200 |

**`tests/unit/rendering/test_*.py`** — Directive Behavior (15 files, ~5,968 LOC):

| Test File | Directive(s) Covered | LOC |
|-----------|----------------------|-----|
| `test_cards_directive.py` | cards, card | ~913 |
| `test_literalinclude_directive.py` | literalinclude | ~527 |
| `test_mistune_parser.py` | admonitions, dropdown, tabs | ~720 |
| `test_myst_syntax.py` | admonitions, dropdown, tabs | ~802 |
| `test_navigation_directives.py` | breadcrumbs, prev-next, siblings | ~400 |
| `test_steps_directive.py` | steps, step | ~300 |
| `test_glossary_directive.py` | glossary, term | ~250 |
| `test_badges.py` | badge | ~171 |
| `test_marimo_directive.py` | marimo | ~200 |
| `test_include_directive.py` | include | ~200 |
| `test_checklist_directive.py` | checklist | ~150 |
| `test_data_table_directive.py` | data-table | ~150 |
| `test_button_directive.py` | button | ~150 |
| `test_icon_directive.py` | icon | ~150 |
| `test_target_directive.py` | target | ~100 |

**`tests/unit/directives/`** (4 files, ~1,116 LOC):

| Test File | What It Tests | LOC |
|-----------|---------------|-----|
| `test_code_tabs.py` | Code tabs directive | ~400 |
| `test_tabs_native.py` | Native tabs rendering | ~300 |
| `test_tokens.py` | Token processing | ~250 |
| `test_priority.py` | Directive priority ordering | ~166 |

**`tests/integration/`** — Directive Integration:

| Test File | What It Tests | LOC |
|-----------|---------------|-----|
| `test_directive_nesting.py` | Nested directive rendering | ~150 |
| `test_gallery.py` | Gallery directive end-to-end | ~178 |

### Source Files (47 total)

**Evidence**: `find bengal/directives -name "*.py" | wc -l` → 47

**By lines of code** (top 15):

| File | Lines | Has Tests |
|------|-------|-----------|
| `embed.py` | 1,188 | ✅ `test_media_directives.py` |
| `video.py` | 908 | ✅ `test_media_directives.py` |
| `code_tabs.py` | 814 | ✅ `test_code_tabs.py` |
| `validator.py` | 644 | ⚠️ Indirect via health validators |
| `base.py` | 567 | ❌ No direct unit tests |
| `navigation.py` | 508 | ✅ `test_navigation_directives.py` |
| `tabs.py` | 504 | ✅ `test_tabs_native.py` |
| `figure.py` | 471 | ✅ `test_media_directives.py` |
| `glossary.py` | 467 | ✅ `test_glossary_directive.py` |
| `steps.py` | 453 | ✅ `test_steps_directive.py` |
| `data_table.py` | 435 | ✅ `test_data_table_directive.py` |
| `options.py` | 433 | ⚠️ Partial via `test_foundation.py` |
| `literalinclude.py` | 430 | ✅ `test_literalinclude_directive.py` |
| `contracts.py` | 408 | ✅ `test_contracts.py` |
| `versioning.py` | 397 | ✅ `test_versioning.py` |

---

## Coverage Analysis

### Directives WITH Comprehensive Tests

| Directive | Test Coverage | Assessment |
|-----------|--------------|------------|
| cards/card | `test_cards_directive.py` (913 LOC) | 🟢 Excellent |
| literalinclude | `test_literalinclude_directive.py` (527 LOC) | 🟢 Excellent |
| video/embed/figure/audio | `test_media_directives.py` (1,217 LOC) | 🟢 Excellent |
| navigation | `test_navigation_directives.py` (400 LOC) | 🟢 Good |
| steps | `test_steps_directive.py` (300 LOC) | 🟢 Good |
| glossary/term | `test_glossary_directive.py` (250 LOC) | 🟢 Good |
| code_tabs | `test_code_tabs.py` (400 LOC) | 🟢 Good |
| tabs | `test_tabs_native.py` (300 LOC) | 🟢 Good |
| admonitions | 16+ tests in `test_mistune_parser.py`, `test_myst_syntax.py` | 🟢 Good |
| dropdown | 10+ tests in `test_mistune_parser.py`, `test_myst_syntax.py` | 🟢 Good |
| badge | `test_badges.py` (171 LOC) | 🟢 Good |
| gallery | `test_gallery.py` (178 LOC) | 🟡 Moderate |
| checklist | `test_checklist_directive.py` | 🟡 Moderate |
| icon | `test_icon_directive.py` | 🟡 Moderate |
| button | `test_button_directive.py` | 🟡 Moderate |
| target | `test_target_directive.py` | 🟡 Moderate |
| versioning | `test_versioning.py` (3 tests) | 🟡 Moderate |

### Infrastructure WITHOUT Direct Unit Tests

| File | Lines | Current Coverage | Priority |
|------|-------|------------------|----------|
| `base.py` | 567 | ❌ None — tested only through subclasses | 🔴 P1 |
| `factory.py` | ~100 | ❌ None — tested indirectly | 🔴 P1 |
| `options.py` | 433 | ⚠️ Partial — `test_foundation.py` covers ~40% | 🟡 P2 |
| `validator.py` | 644 | ⚠️ Indirect — via `test_directive_validator.py` | 🟡 P2 |

---

## Gap Analysis

### Tier 1: Critical (Foundation, Zero Direct Tests)

#### `base.py` — NO DIRECT UNIT TESTS ❌

**Usage**: Foundation for all 40+ directives.

**Source**: `bengal/directives/base.py` (567 lines)

**What needs testing**:
- `parse_directive()` — argument/option/content extraction
- `_parse_children()` — nested content parsing
- `render()` — template method dispatch
- Option validation hooks
- Error context creation (`_create_error_context()`)
- Default value handling
- Plugin registration mechanics

#### `factory.py` — NO UNIT TESTS ❌

**Usage**: Directive instantiation and lookup.

**Source**: `bengal/directives/factory.py` (~100 lines)

**What needs testing**:
- Directive lookup by name
- Instantiation with options
- Missing directive handling
- Alias resolution

### Tier 2: Partial Coverage

#### `options.py` — PARTIAL COVERAGE ⚠️

**Current tests**: `test_foundation.py` covers `DirectiveOptions`, `StyledOptions`, `ContainerOptions`, `TitledOptions`

**Gaps**:
- Boolean option parsing edge cases
- Integer/float option parsing
- List option parsing (comma-separated values)
- Required option validation
- Unknown option handling

#### `validator.py` — INDIRECT COVERAGE ⚠️

**Current tests**: `test_directive_validator.py`, `test_directive_validator_fences.py` in health validators

**Gaps**:
- Unit tests for validation logic in isolation
- Edge cases in fence detection
- Error message formatting

---

## Incomplete Implementations

### `marimo.py` — Caching TODO

**Location**: `bengal/directives/marimo.py:142, 169`

```python
# TODO: Implement caching
# if use_cache and label:
#     cached = self._get_from_cache(label, code)
#     if cached:
#         return cached

# TODO: Store in cache
```

**Impact**: Performance — without caching, Marimo cells re-execute on every build.

**Resolution**: Document as "Planned Feature" in docstring until implementation prioritized.

---

## Type Safety Analysis

### `# type: ignore` Distribution (43 total)

**Evidence**: `grep -r "type: ignore" bengal/directives --include="*.py" | wc -l` → 43

| Type | Count | Reason | Action |
|------|-------|--------|--------|
| `# type: ignore[override]` | 40 | Method signature narrowing (intentional) | ✅ Keep — valid pattern |
| `# type: ignore[attr-defined]` | 3 | State attribute access in `include.py` | 🔧 Fix — add proper typing |

**The `# type: ignore[override]` Pattern**:

This is **intentional** and **correct**. Python's type system doesn't support covariant parameter types, so subclasses narrowing `BaseOptions` to specific options require this suppression.

### `: Any` Distribution (~98 total)

**Hotspots for TypedDict improvement**:

| File | Count | Recommendation |
|------|-------|----------------|
| `cards/utils.py` | 6 | Add `CardData` TypedDict |
| `glossary.py` | 6 | Add `GlossaryTerm` TypedDict |
| `steps.py` | 6 | Add `StepItem` TypedDict |

**Target**: Reduce from ~98 to ~70 by adding 3-4 TypedDicts.

---

## Proposed Test Plan

### Test Architecture

```
tests/unit/directives/
├── __init__.py
├── conftest.py                  # Shared fixtures (existing)
├── test_code_tabs.py            # ✅ Existing
├── test_priority.py             # ✅ Existing
├── test_tabs_native.py          # ✅ Existing
├── test_tokens.py               # ✅ Existing
│
└── infrastructure/              # NEW
    ├── __init__.py
    ├── conftest.py              # Infrastructure-specific fixtures
    ├── test_base.py             # Base directive class
    ├── test_factory.py          # Directive instantiation
    └── test_options_parsing.py  # Option parsing edge cases
```

### Test Patterns

#### Pattern 1: Base Class Method Test

```python
"""Tests for BengalDirective base class."""
import pytest
from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions


class TestBengalDirectiveOptionParsing:
    """Test option parsing in base directive."""

    def test_boolean_option_true_string(self) -> None:
        """Boolean options parse 'true' string correctly."""
        raw = {"open": "true"}
        result = DirectiveOptions.from_raw(raw)
        # Verify boolean conversion

    def test_boolean_option_empty_means_true(self) -> None:
        """Empty boolean option value means True (flag-style)."""
        raw = {"open": ""}
        result = DirectiveOptions.from_raw(raw)
        # Verify empty = True for flags

    def test_missing_required_option_raises(self) -> None:
        """Missing required option raises descriptive error."""
        with pytest.raises(ValueError, match="required"):
            # Test validation
            pass
```

#### Pattern 2: Factory Test

```python
"""Tests for directive factory."""
import pytest
from bengal.directives.factory import get_directive, DirectiveNotFoundError


class TestDirectiveFactory:
    """Test directive lookup and instantiation."""

    def test_lookup_by_primary_name(self) -> None:
        """Directive found by primary name."""
        directive = get_directive("note")
        assert directive is not None

    def test_lookup_by_alias(self) -> None:
        """Directive found by alias name."""
        directive = get_directive("details")  # alias for dropdown
        assert directive is not None

    def test_unknown_directive_raises(self) -> None:
        """Unknown directive name raises clear error."""
        with pytest.raises(DirectiveNotFoundError, match="unknown_directive"):
            get_directive("unknown_directive")
```

---

## Implementation Phases

### Phase 1: Infrastructure Unit Tests (1 day)

**Goal**: Direct unit test coverage for foundation classes.

| Test File | Source File | Est. Tests |
|-----------|-------------|------------|
| `test_base.py` | `base.py` | ~25-30 |
| `test_factory.py` | `factory.py` | ~10-15 |
| `test_options_parsing.py` | `options.py` | ~20-25 |

**Focus areas**:
- Option parsing: booleans, integers, lists, defaults
- Error handling: missing required, invalid values
- Registration: name lookup, alias resolution
- Child parsing: nested content extraction

**Expected outcome**: 60+ new unit tests, infrastructure layer directly tested

### Phase 2: Validator Unit Tests (0.5 day)

**Goal**: Isolated unit tests for validation logic.

| Test File | Source File | Est. Tests |
|-----------|-------------|------------|
| `test_validator_unit.py` | `validator.py` | ~15-20 |

**Focus areas**:
- Fence detection edge cases
- Error message formatting
- Validation rule logic

### Phase 3: Type Safety (0.5 day)

| Task | File(s) | Effort |
|------|---------|--------|
| Fix `[attr-defined]` ignores | `include.py` | 30min |
| Add `StepItem` TypedDict | `steps.py` | 30min |
| Add `GlossaryTerm` TypedDict | `glossary.py` | 30min |
| Document marimo caching as planned | `marimo.py` | 15min |

---

## Success Criteria

### Phase 1 Complete When:

- [ ] `tests/unit/directives/infrastructure/` directory created
- [ ] `test_base.py` with 25+ tests
- [ ] `test_factory.py` with 10+ tests
- [ ] `test_options_parsing.py` with 20+ tests
- [ ] All new tests pass

### Phase 2 Complete When:

- [ ] `test_validator_unit.py` created with 15+ tests
- [ ] Validation edge cases covered
- [ ] All tests pass

### Phase 3 Complete When:

- [ ] `# type: ignore[attr-defined]` reduced to 0
- [ ] 2+ TypedDicts added
- [ ] Marimo TODO documented in docstring

### Final Metrics:

| Metric | Before | After |
|--------|--------|-------|
| Infrastructure test files | 0 | 4 |
| New unit tests | 0 | 75+ |
| `# type: ignore[attr-defined]` | 3 | 0 |
| TODO comments | 2 | 0 (documented) |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests reveal bugs in base.py | Medium | Low | Fix bugs — that's the point |
| Mistune API changes | Low | Medium | Pin version, test API surface |
| Base class refactoring needed | Low | Medium | Tests enable safe refactoring |

---

## Dependencies

### On Other RFCs

- **rfc-type-refinement-sweep.md**: Type improvements should align with broader type refinement effort

### On External Packages

- **Mistune**: Directive parsing relies on Mistune's plugin API
- **pytest**: Test infrastructure

---

## References

- `bengal/directives/` — Source directory (47 files, ~16,000 LOC)
- `tests/unit/directives/` — Current tests (4 files, ~1,116 LOC)
- `tests/unit/rendering/directives/` — Behavior tests (5 files, ~2,200 LOC)
- `tests/unit/rendering/test_*directive*.py` — More behavior tests (15 files, ~5,968 LOC)
