# RFC: Test Suite Signal and Collection Hardening

**Status**: Draft  
**Created**: 2025-12-21  
**Author**: AI Assistant  
**Priority**: P1 (High)  
**Scope**: Test infrastructure + integration test signal

---

## Executive Summary

Bengal’s test suite is large and well-instrumented, but there are a few sharp edges that reduce test signal and increase maintenance cost:

1. Some integration tests **silently skip** unless `site/public` already exists.
2. `pytest` collection currently relies on a **global filter hook** to avoid collecting non-test `test_*` functions in production code (Jinja template predicates).
3. `pytest.ini` sets `norecursedirs`, which can **override defaults** and trigger third-party plugin warnings (Hypothesis).

This RFC proposes a phased hardening plan that preserves current behavior while improving determinism, CI signal, and long-term maintainability.

---

## Problem Statement

### 1) Silent skips reduce CI signal

Some integration tests assert properties of the built documentation site by reading files under `site/public`. When `site/public` is missing, they `pytest.skip()` with instructions to run `bengal build` manually.

This makes the tests non-deterministic across environments and can result in CI runs that appear “green” while silently skipping meaningful assertions.

**Evidence**:
- `tests/integration/test_autodoc_html_generation.py:21-27` (skips if `site/public` does not exist)
- `tests/integration/test_autodoc_nav_integration.py:13-22` (skips if `site/public` does not exist)

### 2) Pytest collection depends on global filtering

There are non-pytest functions named `test_*` in production code (`bengal/rendering/template_tests.py`). These are Jinja2 predicate functions registered into the template environment. They are not intended to be collected by pytest.

The test suite currently prevents their collection by filtering collected items to only those under the `tests/` directory.

This works, but it is a global hook and can hide other accidental collection problems outside `tests/`.

**Evidence**:
- Jinja predicate functions named `test_*`: `bengal/rendering/template_tests.py:30-46`, `bengal/rendering/template_tests.py:50-120`
- Global filtering hook: `tests/conftest.py:103-136`

### 3) `norecursedirs` can override defaults

`pytest.ini` explicitly sets `norecursedirs`. This replaces (not extends) pytest defaults, which can interact poorly with third-party plugins that expect default ignores to remain present.

**Evidence**:
- `pytest.ini:7` (`norecursedirs = bengal .git .tox dist build *.egg`)

---

## Goals

1. **Deterministic signal**: Tests should not silently skip critical checks because a manual precondition was not met.
2. **Safer collection**: Reduce reliance on global collection filtering by removing the root cause (`test_*` in production code).
3. **Stable config**: Avoid surprising plugin interactions due to overriding pytest default ignore behavior.
4. **Low-risk rollout**: Land changes in small, bisectable steps.

## Non-Goals

- Increasing test coverage broadly (see `plan/drafted/rfc-test-coverage-gaps.md`).
- Rewriting the test platform in `tests/_testing/`.
- Changing user-facing product behavior.

---

## Design Options

### Option A: Keep current behavior (Not Recommended)

Pros:
- No work.

Cons:
- Silent skips remain, reducing CI value.
- Global collection filtering remains a footgun.

### Option B: Targeted hardening (Recommended)

Pros:
- Improves determinism and signal without broad refactors.
- Removes root cause of collection hook dependency.
- Preserves overall test ergonomics.

Cons:
- Requires small set of changes across tests + rendering utilities.

### Option C: Aggressive restructuring of tests/

Pros:
- Could further simplify long-term structure.

Cons:
- High churn; not necessary for the immediate problems.

---

## Recommended Approach: Targeted Hardening (Phased)

### Phase 1: Make built-site assertions self-contained or explicitly manual

For tests that assert properties of a built documentation site, choose one of:

1. **Self-contained**: Build a site within the test using existing test infrastructure (preferred when feasible).
2. **Explicitly manual**: Move the test to `tests/manual/` and remove it from CI signal if it is inherently “works on developer machine” validation.

**Current state evidence**:
- `tests/integration/test_autodoc_html_generation.py:21-27`
- `tests/integration/test_autodoc_nav_integration.py:13-22`

**Success criteria**:
- No integration tests in `tests/integration/` require `site/public` to exist before tests start.

### Phase 2: Rename Jinja template predicate functions away from `test_*`

Rename predicate functions in `bengal/rendering/template_tests.py` to avoid pytest discovery confusion:

- `test_draft` → `is_draft`
- `test_featured` → `is_featured`
- `test_match` → `matches`
- `test_outdated` → `is_outdated`
- `test_section` → `is_section`
- `test_translated` → `is_translated`

Update `register()` accordingly.

**Evidence**:
- Current registrations refer to `test_*`: `bengal/rendering/template_tests.py:30-46`
- Functions are named `test_*`: `bengal/rendering/template_tests.py:50-120`
- Tests currently guard against collection: `tests/conftest.py:103-136`

**Success criteria**:
- No `def test_*` functions exist outside `tests/` in the `bengal/` package (excluding intentionally documented examples).

### Phase 3: Revisit global collection filtering and narrow it if possible

After Phase 2, reassess whether `tests/conftest.py:pytest_collection_modifyitems` still needs to filter by path, or whether it can be narrowed to only xdist grouping concerns.

**Evidence**:
- Current hook handles both filtering and xdist grouping: `tests/conftest.py:103-136`

**Success criteria**:
- Collection hook does not need to drop items from outside `tests/` to avoid false positives caused by project code naming.

### Phase 4: Adjust `pytest.ini` ignore patterns to avoid replacing defaults

Change `pytest.ini` configuration to avoid unintended behavior from overriding `norecursedirs` defaults.

**Evidence**:
- `pytest.ini:7`

**Success criteria**:
- No plugin warnings attributable to ignore-configuration conflicts during collection.

---

## Risks and Mitigations

- **Risk: Breaking template behavior by renaming tests**
  - Mitigation: Keep the Jinja key names (`"draft"`, `"featured"`, etc.) stable; only rename Python function objects. Evidence: keys are defined in `bengal/rendering/template_tests.py:38-46`.

- **Risk: Hardening built-site tests increases runtime**
  - Mitigation: Prefer small test roots and reuse existing test fixtures; keep heavy builds marked `slow` or `performance`. Evidence: `tests/performance/__init__.py:1-4`, `pytest.ini:13`.

- **Risk: Removing collection filtering reveals new accidental collection**
  - Mitigation: Do Phase 2 before narrowing Phase 3. Keep changes bisectable.

---

## Success Criteria

- [ ] No `tests/integration/` tests require a pre-built `site/public`.
- [ ] No `def test_*` functions exist in production code for non-pytest semantics (e.g., Jinja predicates).
- [ ] Pytest collection hook no longer needs broad path-based filtering to remain correct.
- [ ] Collection runs without plugin warnings related to ignore configuration.

---

## Validation Summary (Evidence)

Key claims in this RFC are grounded in current code:

- Built-site integration tests skip if `site/public` missing:
  - `tests/integration/test_autodoc_html_generation.py:21-27`
  - `tests/integration/test_autodoc_nav_integration.py:13-22`
- Production code defines `test_*` functions for Jinja predicates:
  - `bengal/rendering/template_tests.py:50-120`
- Global collection filtering exists to avoid collecting those functions:
  - `tests/conftest.py:103-136`
- `pytest.ini` overrides `norecursedirs`:
  - `pytest.ini:7`

---

## Confidence Breakdown

This RFC is primarily an internal test/infra hardening proposal.

- Evidence Strength: 40/40 (claims referenced with file:line)
- Consistency: 30/30 (no conflicting sources identified)
- Recency: 15/15 (evidence from current tree)
- Tests: 10/15 (proposal is about tests; concrete follow-up changes required)

**Total**: 95% 🟢
