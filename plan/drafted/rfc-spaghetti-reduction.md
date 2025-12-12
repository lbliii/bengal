# RFC: Reduce “spaghetti code” via dependency untangling, hotspot refactors, and core-side-effect cleanup

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-12  
**Confidence**: 87% 🟢  
**Priority**: P2 (Medium)  

---

## Executive summary

This RFC proposes a coordinated effort to reduce Bengal “spaghetti code” by addressing three coupled issues:

1. **Dependency tangles** (import cycles and high coupling)
2. **Complexity hotspots** (large, branch-heavy functions)
3. **Core side effects** (logging and operational behavior inside `bengal/core/`)

The recommended approach is a **phased refactor** that (a) makes imports more acyclic and explicit, (b) breaks a few highest-risk functions into smaller units behind stable APIs, and (c) moves observable side effects out of `bengal/core/` (or formalizes a narrow, explicit exception if we choose to keep structured logging in core).

---

## Problem statement

### Current state (evidence)

#### 1) Dependency tangles / cycles

- The package root re-exports core types by importing them at import-time, which increases coupling pressure and can contribute to cycles:
  - `bengal/__init__.py:10-15`
- `bengal/orchestration/incremental.py` contains an explicit “import here to avoid circular import”:
  - `bengal/orchestration/incremental.py:292-294`

#### 2) Complexity hotspots

Two functions are both large and contain multi-scenario logic:

- Incremental work detection is a long, multi-concern method:
  - `bengal/orchestration/incremental.py:271-630` (`IncrementalOrchestrator.find_work_early`)
- Generated-page context injection handles many special page types and robustness paths:
  - `bengal/rendering/renderer.py:317-603` (`Renderer._add_generated_page_context`)

The renderer complexity is justified by real-world robustness requirements (taxonomy data can be stale, fallbacks needed), and is explicitly tested:
- `tests/unit/rendering/test_renderer_tag_context.py:24-95`

Incremental work detection behavior leading to section rebuild decisions is also explicitly tested:
- `tests/unit/orchestration/test_incremental_orchestrator.py:126-199`

#### 3) Core side effects (logging)

Core’s own package docstring states that core models “do not perform I/O, logging, or side effects”:
- `bengal/core/__init__.py:21-31`

However, core models currently instantiate and emit logs, e.g. `Section`:
- Logger creation: `bengal/core/section.py:32-35`
- Logging inside model behavior: `bengal/core/section.py:445-468`

### Pain points

- **Hard-to-reason-about behavior**: When responsibilities are mixed inside large functions, small changes risk unintended regressions.
- **Hard-to-refactor dependencies**: Import cycles force local imports and widen module knowledge (“everything depends on everything”).
- **Architecture inconsistency**: Core-side effects violate stated constraints and make boundaries unclear (what is safe to import where).

### Impact

- Contributors: slower iteration, higher review burden, more “safety edits” (local imports, broad catches).
- Users: increased risk of incremental build regressions and hard-to-debug failures.

---

## Goals & Non-goals

### Goals

1. **Reduce dependency tangles** by narrowing import-time coupling and removing cycle pressure.
2. **Reduce hotspot complexity** by extracting smaller units with clearer inputs/outputs for the top offenders.
3. **Make core boundaries consistent** by removing core logging/side effects (or explicitly documenting and constraining an exception).
4. **Preserve behavior**: changes should be primarily structural; functional changes must be covered by tests.

### Non-goals

- Rewriting major subsystems (e.g., replacing the incremental build algorithm wholesale).
- Guaranteeing complete absence of cycles across all possible runtime import paths (we focus on the primary `bengal.*` graph).
- Large-scale renaming/relocation of public APIs without a migration plan.

---

## Design options

### Option A: Minimal guardrails + selective refactors (lowest disruption)

**Description**
- Keep module layout mostly intact.
- Add constraints/guardrails (documented boundaries + targeted tests for hotspots).
- Refactor only a small set of functions (incremental work detection and generated context).
- Leave core logging in place, but document it as an intentional exception to the “no side effects” statement.

**Pros**
- Lowest short-term risk.
- Less churn across the codebase.

**Cons**
- Cycles/coupling pressure likely remains.
- Core boundary contradiction remains (docstring vs reality).

### Option B: Phased “untangle + extract” (recommended)

**Description**

Phase the work so each initiative reduces future work:

1. **Dependency untangling**:
   - Reduce import-time coupling from re-exports (e.g., avoid importing heavy modules at package import-time).
   - Replace “import here to avoid circular import” hotspots with shared, lower-level modules where appropriate.
2. **Hotspot refactors**:
   - Extract focused helper components from:
     - `IncrementalOrchestrator.find_work_early` (`bengal/orchestration/incremental.py:271-630`)
     - `Renderer._add_generated_page_context` (`bengal/rendering/renderer.py:317-603`)
   - Keep existing externally-visible behavior; verify by extending existing tests.
3. **Core side-effect cleanup**:
   - Remove logging from core models or route it through an explicit “events/warnings” interface to be emitted by orchestrators.

**Pros**
- Structural improvements compound: fewer cycles makes future refactors cheaper.
- Restores architectural clarity by aligning core behavior with its stated constraints.

**Cons**
- Moderate code churn; requires careful sequencing and test coverage.

### Option C: Big-bang modularization (highest disruption)

**Description**
- Introduce a new explicit “API layer” module (e.g., `bengal/api.py`) and stop re-exporting from package roots, while simultaneously splitting large modules/packages.

**Pros**
- Fastest route to a cleaner import graph (in theory).

**Cons**
- High risk, large diff surface; higher likelihood of downstream breakage.

---

## Recommended approach

Adopt **Option B**.

It is the best fit given:
- We already have evidence of cycle pressure (local import to avoid cycle): `bengal/orchestration/incremental.py:292-294`
- Hotspots are validated by real tests (so we can refactor with guardrails): `tests/unit/orchestration/test_incremental_orchestrator.py:126-199`, `tests/unit/rendering/test_renderer_tag_context.py:24-95`
- Core boundary mismatch is explicit and should be corrected for long-term maintainability: `bengal/core/__init__.py:21-31` vs `bengal/core/section.py:32-35`

---

## Detailed design (proposed)

### 1) Dependency untangling

**Proposal**
- Reduce import-time re-export pressure by making package entrypoints lighter.
  - Current: `bengal/__init__.py` imports `Asset`, `Page`, `Section`, `Site` at import-time (`bengal/__init__.py:10-15`).
- Identify and resolve “local import to avoid circular import” sites by:
  - Extracting shared dataclasses/types into lower-level modules where the dependency direction is stable, or
  - Introducing small adapter modules that depend “downward” (never importing orchestration from core, etc.).

**Acceptance criteria**
- Remove at least one “import here to avoid circular import” by restructuring dependencies without behavior change.
- Reduce fan-out of key modules (baseline established during audit).

### 2) Hotspot refactors

#### 2.1 Incremental work detection

**Proposal**
- Split `find_work_early` into a small set of helpers with single-purpose responsibilities:
  - section-level change detection
  - content file changed detection
  - cascade change handling
  - nav-metadata compare + section rebuild decision
  - template change detection
  - autodoc selective rebuild

**Guardrails**
- Preserve behavior validated by existing tests (nav metadata behavior, section rebuild rules): `tests/unit/orchestration/test_incremental_orchestrator.py:126-199`

#### 2.2 Generated page context injection

**Proposal**
- Split `_add_generated_page_context` by page type, keeping the same external template context keys.
- Explicitly codify the “stale taxonomy” resolution rules already relied upon by tests:
  - `tests/unit/rendering/test_renderer_tag_context.py:24-95`

### 3) Core side-effect cleanup

**Proposal**
- Stop emitting logs from core models (example current logging in `Section.relative_url`): `bengal/core/section.py:445-468`
- Replace with one of:
  - Returning structured diagnostics (warnings list / events) for orchestrators to log, or
  - A lightweight event sink interface injected by orchestrators (core emits events, orchestrators decide whether/how to log).

**Constraint**
- Ensure the design remains compatible with the stated “core models are passive” contract: `bengal/core/__init__.py:21-31`

---

## Testing strategy

- **Unit**:
  - Extend `tests/unit/orchestration/test_incremental_orchestrator.py` to cover refactored helper behavior by assertion on outputs, not internal structure.
  - Extend `tests/unit/rendering/test_renderer_tag_context.py` (or add adjacent tests) to cover each “page type” handler after extraction.
- **Integration**:
  - Ensure full → incremental flow remains correct through the existing regression suite:
    - Cache saved after full build: `tests/integration/test_full_to_incremental_sequence.py:184-220`
  - If we change incremental change detection logic, use (or stabilize) the existing parametrized test (currently skipped as flaky):
    - Skip reason documents current gap: `tests/integration/test_full_to_incremental_sequence.py:53-57`

---

## Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Refactor changes behavior subtly | Med | High | Expand tests around existing behavior before extracting helpers; refactor in small commits |
| Import changes break runtime entrypoints | Med | Med | Keep backwards-compatible import paths; add targeted smoke tests around CLI / importability |
| Removing core logging reduces observability | Low | Med | Introduce explicit diagnostics/events surfaced by orchestrators |

---

## Confidence scoring

**Confidence** is computed as:

```yaml
confidence = Evidence(40) + Consistency(30) + Recency(15) + Tests(15)
```

- **Evidence (40/40)**: Direct source references for each problem area are included (see “References”).
- **Consistency (20/30)**:
  - Source + tests support hotspot behavior and constraints:
    - Incremental behavior: `tests/unit/orchestration/test_incremental_orchestrator.py:126-199`
    - Renderer behavior: `tests/unit/rendering/test_renderer_tag_context.py:24-95`
    - Core constraint vs implementation: `bengal/core/__init__.py:21-31` vs `bengal/core/section.py:32-35`
  - Import-cycle pressure is evidenced by local import patterns, but cycle removal is not yet validated by tests (follow-up plan work).
- **Recency (15/15)**: Hotspot files were modified in the last week (see per-file `git log -n 1 -- <file>` output during RFC drafting).
- **Tests (12/15)**: Strong unit/integration coverage for incremental and renderer behavior, weaker coverage for dependency/cycle constraints and core boundary enforcement.

**Total**: \(40 + 20 + 15 + 12 = 87\)% 🟢

## Implementation plan (high level)

1. **Dependency baseline + first untangle**
   - Reduce import-time coupling around `bengal/__init__.py` and/or core re-exports.
2. **Incremental hotspot extraction**
   - Extract helpers from `IncrementalOrchestrator.find_work_early` with tests as guardrails.
3. **Renderer hotspot extraction**
   - Extract per-page-type handlers from `_add_generated_page_context`, preserving tested behavior.
4. **Core side-effect cleanup**
   - Remove logging from `bengal/core/*` (starting with `Section`) and ensure orchestrators remain the logging boundary.

Follow-up: Convert this RFC into a `plan/drafted/plan-spaghetti-reduction.md` with atomic tasks and commit messages.

---

## Open questions

- [ ] Do we want to keep any structured logging inside core as an explicit exception, or enforce “no logging” strictly (per `bengal/core/__init__.py:21-31`)?
- [ ] Which import surfaces are considered stable public API (so we can avoid accidental breaking changes while reducing re-exports)?

---

## References (evidence)

- `bengal/__init__.py:10-15` — package root imports core types at import-time (re-export behavior).
- `bengal/orchestration/incremental.py:292-294` — local import to avoid circular import.
- `bengal/orchestration/incremental.py:271-630` — `find_work_early` hotspot.
- `tests/unit/orchestration/test_incremental_orchestrator.py:126-199` — incremental nav-metadata behavior tested.
- `bengal/rendering/renderer.py:317-603` — `_add_generated_page_context` hotspot.
- `tests/unit/rendering/test_renderer_tag_context.py:24-95` — robustness rules for tag context tested.
- `bengal/core/__init__.py:21-31` — documented core constraint (“no I/O/logging/side effects”).
- `bengal/core/section.py:32-35` — core model logger creation.
- `bengal/core/section.py:445-468` — core model logging in behavior.
