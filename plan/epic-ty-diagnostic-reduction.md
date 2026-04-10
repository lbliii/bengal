# Epic: ty Diagnostic Reduction — From 2,654 to Error-Promotion Ready

**Status**: Draft
**Created**: 2026-04-10
**Target**: 0.4.0
**Estimated Effort**: 24-36h
**Dependencies**: None (ty already adopted, RFC implemented)
**Source**: `uv run ty check` analysis (2026-04-10), `plan/rfc-ty-type-checker-adoption.md`

---

## Why This Matters

Bengal has 2,654 ty diagnostics — nearly 4x the ~715 reported in PR #203 three weeks ago. The three highest-volume rules (`invalid-argument-type`, `unresolved-attribute`, `invalid-assignment`) are stuck at `warn` level, meaning real type bugs can ship to main undetected. The pyproject.toml comments are stale (claim 257/333/65 but reality is 957/704/329), giving a false sense of progress.

**Consequences:**

1. **Type bugs reach main** — warn-level rules don't block CI, so actual type errors in new code go unnoticed
2. **Signal-to-noise collapse** — 2,654 warnings means developers ignore ty output entirely
3. **Free-threading risk** — incorrect types in concurrent code can cause subtle data races that type checking should catch
4. **Stale comments erode trust** — pyproject.toml claims 257 `invalid-argument-type` violations; the real number is 957
5. **Compound growth** — without enforcement, every PR adds new violations faster than they're fixed

**The fix:** Systematically reduce diagnostics by fixing hot functions first (one Protocol fix can eliminate 50+ downstream warnings), then promote rules from `warn` to `error` as counts reach zero for source code.

### Evidence Table

| Source | Finding | Proposal Impact |
|--------|---------|-----------------|
| `uv run ty check` | 2,654 total diagnostics (was ~715 at PR #203) | FIXES — targets reduction to <200 source diagnostics |
| Diagnostic distribution | 1,405 source, 1,870 tests, 95 stdlib | FIXES — source-first strategy, tests follow |
| Hot function clustering | `add_page` = 69 hits, `__init__` = 117, `register` = 36 | FIXES — Sprint 1 targets these multipliers |
| Module concentration | rendering (387), orchestration (210), core (175) = 55% | FIXES — Sprint 2-4 attack by module |
| Config staleness | Comments say 257/333/65, reality 957/704/329 | FIXES — Sprint 0 updates comments, Sprint 5 promotes to error |
| 354 `invalid-key` errors | TypedDict/dict literal type inference gaps | MITIGATES — may require ty upstream fixes or suppression |

### Invariants

These must remain true throughout or we stop and reassess:

1. **Full test suite passes**: `pytest tests/ -x -q` green after every sprint — type annotation changes must not alter runtime behavior
2. **No `# type: ignore` carpet-bombing**: Suppress individual diagnostics only with specific rule codes and a comment explaining why (ty false positive, dynamic pattern, etc.)
3. **Diagnostic count monotonically decreases per rule**: Each sprint's target rule count must be <= the previous sprint's count; if a sprint increases a count, the change is reverted and investigated

---

## Target Architecture

**Before (current):**
```
[tool.ty.rules]
invalid-argument-type = "warn"    # 957 violations
unresolved-attribute = "warn"     # 704 violations
invalid-assignment = "warn"       # 329 violations
# ... all warn, none enforced
```

**After (target):**
```
[tool.ty.rules]
invalid-argument-type = "error"   # 0 source violations (tests may retain some)
unresolved-attribute = "error"    # 0 source violations
invalid-assignment = "error"      # 0 source violations
invalid-return-type = "error"     # 0 source violations
# ... promoted rules block CI on new violations
```

**Approach:** Fix source code first (1,405 diagnostics across `bengal/`), promote to error with per-file ignores for tests where needed. This prevents regression in production code while allowing gradual test cleanup.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| 0 | Triage & classify all 2,654 diagnostics | 2h | Low | Yes (updated comments + triage doc) |
| 1 | Fix hot functions — eliminate multiplier diagnostics | 6h | Medium | Yes (largest single drop) |
| 2 | rendering module (387 diagnostics) | 6h | Medium | Yes |
| 3 | core + orchestration modules (385 diagnostics) | 6h | Medium | Yes |
| 4 | Remaining source modules (458 diagnostics) | 4h | Low | Yes |
| 5 | Promote rules to error, update config | 2h | Low | Yes (enforcement gate) |

---

## Sprint 0: Triage & Classify

**Goal**: Understand every diagnostic category and decide: fix, suppress (with reason), or report upstream to ty.

### Task 0.1 — Generate full diagnostic inventory

Run `uv run ty check` and produce a breakdown by: rule × module × specific message. Identify which diagnostics are genuine type bugs vs ty false positives vs dynamic patterns.

**Acceptance**:
- Triage table exists in this plan (or linked doc) with fix/suppress/upstream for each cluster
- pyproject.toml comments updated to reflect actual counts

### Task 0.2 — Identify ty false positives

Sample 10-15 diagnostics from each major rule. For each, determine: is this a real type error, a missing annotation, or a ty bug?

**Files**: `pyproject.toml` (update stale comments)
**Acceptance**: `grep '257 violations\|333 violations\|65 violations' pyproject.toml` returns zero hits

### Task 0.3 — Classify `invalid-key` errors (354)

These are error-level but numerous. Determine if they're TypedDict inference gaps (ty limitation) or genuine dict-typing issues.

**Acceptance**: Written classification with recommended action per cluster

---

## Sprint 1: Fix Hot Functions (Multiplier Elimination)

**Goal**: Fix the type signatures of functions that cause the most downstream diagnostics. One fix here eliminates 10-70 warnings elsewhere.

### Task 1.1 — Fix `add_page` signature (69 diagnostics)

The `add_page(self, page: PageLike)` signature in `bengal/core/section/queries.py` triggers 69 `invalid-argument-type` warnings because callers pass `Page` objects that ty doesn't recognize as `PageLike`.

**Files**: `bengal/core/section/queries.py`, `bengal/protocols/core.py`
**Acceptance**: `uv run ty check 2>&1 | grep 'add_page' | wc -l` drops by >= 60

### Task 1.2 — Fix `__init__` argument patterns (117 diagnostics)

Various `__init__` methods receive arguments ty can't resolve. Likely caused by Protocol/dataclass interaction or missing type narrowing.

**Files**: Multiple — identify top 5 classes by `__init__` diagnostic count
**Acceptance**: `uv run ty check 2>&1 | grep '__init__.*is incorrect' | wc -l` drops by >= 80

### Task 1.3 — Fix `register` function (36 diagnostics)

Plugin/template function registration has overly broad or incorrect parameter types.

**Files**: `bengal/plugins/registry.py`, `bengal/rendering/template_functions/`
**Acceptance**: `uv run ty check 2>&1 | grep 'register.*is incorrect' | wc -l` drops by >= 30

### Task 1.4 — Fix `_resolve_fingerprinted` (27 diagnostics)

Asset resolution function type signature mismatch.

**Files**: `bengal/rendering/assets.py`
**Acceptance**: `uv run ty check 2>&1 | grep '_resolve_fingerprinted' | wc -l` drops by >= 20

### Task 1.5 — Fix `append`/`extend` on typed collections (47 diagnostics)

List operations where the element type doesn't match the declared collection type. Likely a `list[PageLike]` vs `list[Page]` variance issue.

**Acceptance**: `uv run ty check 2>&1 | grep -E 'append|extend.*is incorrect' | wc -l` drops by >= 35

**Sprint 1 gate**: Total diagnostic count drops below 2,200 (from 2,654)

---

## Sprint 2: rendering Module (387 diagnostics)

**Goal**: Clean up the largest source module. Focus on pipeline/core.py (49), renderer.py (44), template_functions/ (82 combined), and assets.py (27).

### Task 2.1 — Fix pipeline/core.py (49 diagnostics)

The rendering pipeline core has the most diagnostics of any single source file. Likely Protocol conformance and snapshot type issues.

**Files**: `bengal/rendering/pipeline/core.py`
**Acceptance**: `uv run ty check 2>&1 | grep 'rendering/pipeline/core.py' | wc -l` < 10

### Task 2.2 — Fix renderer.py (44 diagnostics)

**Files**: `bengal/rendering/renderer.py`
**Acceptance**: `uv run ty check 2>&1 | grep 'rendering/renderer.py' | wc -l` < 10

### Task 2.3 — Fix template_functions/ (82 diagnostics combined)

`get_page.py` (38), `autodoc.py` (25), `openapi.py` (20), `memo.py` (19).

**Files**: `bengal/rendering/template_functions/`
**Acceptance**: `uv run ty check 2>&1 | grep 'template_functions/' | wc -l` < 20

### Task 2.4 — Fix remaining rendering/ files

**Acceptance**: `uv run ty check 2>&1 | grep 'bengal/rendering/' | grep -c '^\s*-->'` < 50

**Sprint 2 gate**: Total source diagnostics for `bengal/rendering/` < 50 (from 387)

---

## Sprint 3: core + orchestration Modules (385 diagnostics)

**Goal**: Fix the two next-largest modules.

### Task 3.1 — Fix core/section/queries.py (69 diagnostics)

Most diagnostics are `add_page` related (may be resolved by Sprint 1). Remaining issues likely involve query return types and Protocol conformance.

**Files**: `bengal/core/section/queries.py`
**Acceptance**: `uv run ty check 2>&1 | grep 'core/section/queries.py' | wc -l` < 5

### Task 3.2 — Fix core/site/__init__.py (22 diagnostics)

**Files**: `bengal/core/site/__init__.py`
**Acceptance**: `uv run ty check 2>&1 | grep 'core/site/__init__.py' | wc -l` < 5

### Task 3.3 — Fix orchestration/ (210 diagnostics)

Key files: `taxonomy.py` (19), `stats/display.py` (20), `utils/parallel.py` (19), `build/content.py` (14), `streaming.py` (13), `section.py` (12).

**Files**: `bengal/orchestration/`
**Acceptance**: `uv run ty check 2>&1 | grep 'bengal/orchestration/' | grep -c '^\s*-->'` < 30

**Sprint 3 gate**: Total source diagnostics for `bengal/core/` + `bengal/orchestration/` < 40 (from 385)

---

## Sprint 4: Remaining Source Modules (458 diagnostics)

**Goal**: Clean up cache (74), postprocess (69), cli (60), parsing (53), health (43), server (37), effects (37), snapshots (34), and smaller modules.

### Task 4.1 — Fix cache/ (74 diagnostics)

Key files: `generated_page_cache.py` (21), `build_cache/file_tracking.py` (13).

**Files**: `bengal/cache/`
**Acceptance**: `uv run ty check 2>&1 | grep 'bengal/cache/' | grep -c '^\s*-->'` < 10

### Task 4.2 — Fix postprocess/ + cli/ (129 diagnostics)

**Files**: `bengal/postprocess/`, `bengal/cli/`
**Acceptance**: Combined count < 15

### Task 4.3 — Fix remaining modules (255 diagnostics)

parsing, health, server, effects, snapshots, analysis, content, utils, errors, debug, autodoc, content_types, collections, config.

**Acceptance**: `uv run ty check 2>&1 | grep '^bengal/' | grep -v tests | grep -c '^\s*-->'` < 30 total for all remaining

**Sprint 4 gate**: Total source diagnostics across all `bengal/` modules < 100

---

## Sprint 5: Promote Rules to Error

**Goal**: Change the three high-volume rules from `warn` to `error` in pyproject.toml so CI blocks new type violations.

### Task 5.1 — Promote `invalid-argument-type` to error

If source count is 0, promote to error. If residual suppressions exist, add per-file `# ty: ignore[invalid-argument-type]` with justification comments.

**Files**: `pyproject.toml`
**Acceptance**: `grep 'invalid-argument-type = "error"' pyproject.toml` returns a hit; `uv run ty check 2>&1 | grep error | wc -l` shows no new errors from this rule in `bengal/`

### Task 5.2 — Promote `unresolved-attribute` to error

Same approach.

**Acceptance**: `grep 'unresolved-attribute = "error"' pyproject.toml` returns a hit

### Task 5.3 — Promote `invalid-assignment` to error

Same approach.

**Acceptance**: `grep 'invalid-assignment = "error"' pyproject.toml` returns a hit

### Task 5.4 — Evaluate remaining warn-level rules for promotion

Review `invalid-return-type` (65), `not-subscriptable` (37), `call-non-callable` (29), `unresolved-import` (29) for promotion readiness.

**Acceptance**: Each rule either promoted to error or has a documented reason to remain at warn with a target sprint for future promotion

**Sprint 5 gate**: At least 3 rules promoted from warn to error; `uv run ty check` exits clean (no errors) on `bengal/`

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fixing types changes runtime behavior (e.g., removing `Any` narrows dispatch) | Medium | High | Invariant 1: full test suite after every sprint; review each fix for behavioral change |
| ty false positives require widespread suppression | Medium | Medium | Sprint 0 triage identifies these upfront; report upstream to Astral with reproducers |
| Hot function fixes cascade into test failures | Medium | Medium | Sprint 1 runs full test suite after each task; revert if > 5 test failures per fix |
| `invalid-key` errors are ty limitations, not fixable | Medium | Low | Classify in Sprint 0; suppress with `# ty: ignore[invalid-key]` if confirmed upstream bug |
| Diagnostic count re-grows between sprints | Low | Medium | Invariant 3 + promote to error ASAP to prevent regression |
| Protocol changes break plugin API | Low | High | No changes to `bengal/protocols/` public signatures without deprecation path |

---

## Success Metrics

| Metric | Current | After Sprint 1 | After Sprint 3 | After Sprint 5 |
|--------|---------|----------------|----------------|----------------|
| Total diagnostics | 2,654 | < 2,200 | < 1,500 | < 800 |
| Source diagnostics (`bengal/`) | 1,405 | < 1,000 | < 200 | < 100 |
| Rules at error level | 6 | 6 | 6 | 9+ |
| Stale config comments | 3 | 0 | 0 | 0 |
| `rendering/` diagnostics | 387 | 387 | < 50 | < 50 |

---

## Relationship to Existing Work

- **`rfc-ty-type-checker-adoption.md`** — prerequisite, already implemented — this epic is the "Phase 2: Fix Type Errors" that RFC deferred
- **`epic-stale-code-refresh.md`** — parallel — that effort reduced diagnostics from 837 → 715; this continues the trajectory
- **`rfc-protocol-driven-typing.md`** — informing — Protocol definitions in `bengal/protocols/` are the root cause of many `invalid-argument-type` diagnostics; this epic may refine those Protocols
- **PR #203** (`837 → 715`) — predecessor — established the pattern of diagnostic reduction PRs

---

## Changelog

- 2026-04-10: Draft created from fresh `uv run ty check` analysis (2,654 diagnostics)
