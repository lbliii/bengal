# Sprint 0: ty Diagnostic Triage

**Status**: Complete
**Date**: 2026-04-10
**Archived**: 2026-04-20 — triage feeds `plan/complete/epic-ty-diagnostic-reduction.md`. Diagnostic floor now ~2207 (verified 2026-04-20).
**Total diagnostics at start**: 2,654
**Epic**: `plan/complete/epic-ty-diagnostic-reduction.md`

---

## Diagnostic Inventory

### Source Code — 724 diagnostics across `bengal/`

| Rule | Count | Classification | Action |
|------|-------|---------------|--------|
| `unresolved-attribute` | 340 | ~60% PageLike protocol gaps, ~25% Optional access, ~15% dynamic attrs | **Fix**: expand PageLike protocol or narrow types at call sites |
| `invalid-argument-type` | 197 | ~80% Page→PageLike covariance, ~20% genuine mismatches | **Fix**: widen function signatures or use Protocol covariance |
| `invalid-assignment` | 74 | ~50% list variance (list[Page] → list[PageLike]), ~30% read-only protocol attrs, ~20% mixed | **Fix**: use Sequence[PageLike] for read-only, widen for mutable |
| `invalid-return-type` | 56 | Real type mismatches — return types too narrow | **Fix**: correct return annotations |
| `call-non-callable` | 21 | hasattr guard patterns ty can't narrow | **Suppress**: `# ty: ignore[call-non-callable]` with comment |
| `unresolved-import` | 13 | Deleted/moved modules (directives.cache, incremental.block_detector) | **Fix**: update or remove stale imports |
| `invalid-type-arguments` | 11 | DirectiveOptions subclass not assignable to TypeVar bound | **Fix**: adjust TypeVar bound or use covariant |
| `invalid-method-override` | 10 | Liskov violations in CLI widgets + cascade view | **Fix**: align method signatures |
| `not-subscriptable` | 2 | AssetCacheEntry missing __getitem__ | **Fix**: add protocol method or use dict |

### Test Code — 1,835 diagnostics

| Rule | Count | Classification | Action |
|------|-------|---------------|--------|
| `invalid-argument-type` | 760 | Page objects passed where PageLike expected — same root cause as source | **Fix**: cascade from source fixes |
| `invalid-key` | 354 | ASTNode union subscript — ty can't narrow `result[0]["url"]` to LinkNode | **Suppress**: per-test `# ty: ignore[invalid-key]` or cast |
| `unresolved-attribute` | 364 | Same PageLike protocol gaps + test mock attributes | **Fix**: cascade from source + fix mocks |
| `invalid-assignment` | 255 | list[PageLike \| Page] → list[PageLike] variance | **Fix**: cascade from source fixes |
| `unsupported-operator` | 54 | `in` operator on Optional fields without None check | **Fix**: add None guards in tests |
| `not-subscriptable` | 35 | object/None subscript after mock returns | **Fix**: type test fixtures |
| `missing-argument` | 29 | API changed, tests not updated | **Fix**: update test call signatures |
| `unknown-argument` | 19 | Same — kwargs renamed | **Fix**: update test call signatures |

### stdlib/stubs — 95 diagnostics

All in `builtins.pyi` and `unittest/mock.pyi`. These are ty's own type stub issues — not fixable by us.

**Action**: Ignore. These will resolve as ty matures.

---

## Root Cause Analysis

### Root Cause 1: PageLike Protocol Too Narrow (est. ~500 diagnostics)

The `PageLike` protocol in `bengal/protocols/core.py` does NOT declare `_source`, `_section`, or several other attributes that source code routinely accesses. Additionally, `Page` implements `PageLike` but ty doesn't recognize the structural subtyping because:

- Private attributes (`_source`, `_section`) are accessed on `PageLike`-typed variables
- Functions accept `PageLike` but callers pass `Page` — ty sees `Page` as not structurally matching in all cases

**Fix strategy**: Either (a) add missing attributes to `PageLike` protocol, or (b) accept `Page` directly where the protocol abstraction isn't needed, or (c) use type narrowing with `isinstance`.

**Estimated impact**: Fixing this root cause eliminates ~35 `unresolved-attribute` + ~69 `add_page` invalid-argument-type + cascading test diagnostics ≈ 500 total.

**Actual result**: ~300 eliminated. ty's structural matching limitation prevents full resolution.

### Root Cause 2: List Invariance (est. ~370 diagnostics)

`list[Page]` is not assignable to `list[PageLike]` because lists are invariant in Python's type system. This triggers:
- 90 instances of `list[PageLike | Page]` → `list[PageLike]` assignment
- 36 `append` argument errors
- ~255 test diagnostics

**Fix strategy**: Use `Sequence[PageLike]` (covariant) for read-only parameters, keep `list[Page]` for mutable contexts.

**Actual result**: ~200 eliminated. Remaining cases are where ty can't match Page to PageLike structurally even through Sequence.

### Root Cause 3: ASTNode Union Subscript (est. ~354 diagnostics)

Tests index into `list[ASTNode]` results and access `["url"]` — but `ASTNode` is a union of 16 TypedDicts, and only `LinkNode` has `"url"`. ty correctly flags that subscripting with `"url"` is invalid for the other 15 types.

**Fix strategy**: Either (a) cast `result[0]` to `LinkNode` in tests, or (b) use type narrowing (`assert result[0]["type"] == "link"`), or (c) suppress with `# ty: ignore[invalid-key]`.

**Actual result**: ~100 eliminated via type narrowing in test assertions.

### Root Cause 4: Optional Access Without Guards (est. ~150 diagnostics)

Code accesses attributes on `Optional[X]` values without None checks. ty correctly flags `.attribute` access on `X | None`.

**Fix strategy**: Add None guards or assert-not-None where the value is known to be non-None.

### Root Cause 5: hasattr/Dynamic Dispatch (est. ~50 diagnostics)

Patterns like `if hasattr(obj, "method"): obj.method()` — ty can't narrow the type from `hasattr`. Also affects Protocol objects used dynamically.

**Fix strategy**: Use `isinstance` checks with Protocol, or suppress with targeted `# ty: ignore`.

**Actual result**: Unfixable — ty limitation. 507 `unresolved-attribute` diagnostics remain.

---

## Classification Summary

| Classification | Diagnostic Count | Action | Result |
|---------------|-----------------|--------|--------|
| **Fix in source** — real type improvements | ~724 source | Sprint 1-4 | ~250 fixed, ~474 are ty limitations |
| **Fix cascading to tests** — same root causes | ~1,100 tests | Resolves with source fixes | Partial — ty structural matching blocks full cascade |
| **Suppress in tests** — ASTNode union subscript | ~354 tests | Cast or `# ty: ignore` | ~100 fixed via type narrowing |
| **Suppress** — ty limitations (hasattr, stubs) | ~145 | Targeted `# ty: ignore` with reason | Not pursued — too many to suppress cleanly |
| **Ignore** — stdlib stubs | ~95 | ty upstream | Ignored |
| **Fix in tests** — stale call signatures | ~48 tests | Update tests | Not addressed |

**Bottom line**: The triage correctly identified the root causes. The gap between estimated and actual impact was caused by ty's structural protocol matching limitation — even when we fix the types correctly, ty often can't verify the fix.

---

## Revised Sprint 1 Priorities

Based on triage, Sprint 1 should focus on these high-multiplier fixes:

1. **PageLike protocol expansion** — add missing attributes or retype functions to accept `Page` directly (~500 diagnostics)
2. **List invariance** — `list[PageLike]` → `Sequence[PageLike]` for read-only params (~370 diagnostics)
3. **ASTNode test narrowing** — add `assert node["type"] == "link"` before `node["url"]` access (~354 diagnostics)

These three changes should drop total diagnostics from 2,654 to ~1,400.

**Actual result**: Dropped to 2,023 after Sprint 1. The gap was caused by ty's inability to structurally match Page to PageLike in many inference contexts.
