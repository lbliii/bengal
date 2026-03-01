# Output Collector: Tech Debt Remediation Plan

## Executive Summary

This plan addresses technical debt identified during the output_collector propagation fixes (G1–G4). Items are ordered by impact and effort; higher-priority items reduce risk and improve maintainability.

**Related**: `plan/output-collector-long-term-solution.md`, `bengal/orchestration/render/output_collector_diagnostics.py`

---

## 1. Dead Code: `_phase_render`

### Problem

`_phase_render` in `build/__init__.py` is never called. The main build flow invokes `rendering.phase_render` directly at line 645. The method appears to be leftover from a phase-by-phase execution interface.

### Options

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| **A. Remove** | Low | Medium | Remove `_phase_render` and any phase mixin that only delegates to it. Verify no external callers (grep, deprecation search). |
| **B. Wire up** | Medium | Low | If phase-by-phase execution is a desired feature, add a caller (e.g. dashboard, CLI `--phase`) that invokes `_phase_render` with `collector`, `early_context`, `changed_sources`. |
| **C. Deprecate** | Low | Low | Add deprecation warning, document as legacy. Remove in next major. |

### Recommended Path

**Option A** unless phase-by-phase execution is on the roadmap. Steps:

1. Grep for `_phase_render` and `phase_render` callers across bengal + dependents.
2. If no callers: delete `_phase_render` method.
3. If phase mixin exists solely for this: remove or simplify mixin.
4. Add a brief note in changelog: "Removed unused _phase_render."

---

## 2. Unit Tests for Diagnostics Module

### Problem

`output_collector_diagnostics` has no tests. `diagnose_missing_output_collector()` and `OutputCollectorDiagnostic.to_log_context()` are easy to regress.

### Scope

- `tests/unit/orchestration/render/test_output_collector_diagnostics.py`

### Test Cases

| Test | Input | Expected |
|------|-------|----------|
| `test_known_source_returns_that_source` | `known_source=STREAMING_FALLBACK` | Diagnostic with `source=streaming_fallback`, matching hint |
| `test_build_context_none` | `build_context=None` | `source=build_context_none` |
| `test_collector_not_propagated` | `build_context` with `output_collector=None` | `source=collector_not_propagated` |
| `test_unknown_when_context_has_collector` | `build_context` with `output_collector=<obj>` | `source=unknown` (edge case; caller shouldn't call when collector present) |
| `test_to_log_context_keys` | Any diagnostic | Dict has `source`, `caller`, `build_context_present`, `worker_threads`, `hint` |
| `test_all_source_hints_exist` | Each `OutputCollectorSource` | `SOURCE_HINTS[source]` is non-empty string |

### Effort

~1–2 hours. No mocks needed; pure function.

---

## 3. Diagnostic Heuristic Improvements

### Problem

`diagnose_missing_output_collector()` cannot distinguish:

- `RICH_PROGRESS_OMITTED` (G2) — pipeline created without explicit pass
- `COLLECTOR_NOT_PROPAGATED` (G4) — build_context exists but collector is None

Both present as "build_context exists but output_collector is None." The function only knows `caller`, not which render path (Rich vs simple) was taken.

### Options

| Option | Approach | Effort |
|--------|----------|--------|
| **A. Caller passes `known_source`** | When the caller knows the reason (e.g. streaming fallback), pass `known_source=OutputCollectorSource.STREAMING_FALLBACK`. | Low |
| **B. Add `render_path` param** | Caller passes `render_path="rich_progress" | "simple" | "streaming_fallback"`. Diagnostic uses it to refine source. | Medium |
| **C. Stack inspection** | Use `inspect.stack()` to detect if we're inside `_render_parallel_with_progress`. Fragile, not recommended. | High (and brittle) |

### Recommended Path

**Option A** for known cases; keep current heuristic for unknown.

1. In `streaming.py` fallback, before calling `orchestrator.process()`, we could log with `known_source=STREAMING_FALLBACK` if we ever hit that path and still see the warning. (We fixed G1, so this path should now pass build_context.)
2. In `_render_parallel`, we don't know if we're in the Rich path or simple path at the point of the warning. The warning fires when `output_collector is None`; by then we've already lost the path info.
3. **Pragmatic fix**: Add optional `render_path: str | None = None` to `diagnose_missing_output_collector()`. If `render_path == "rich_progress"` and `build_context` exists but collector is None → use `RICH_PROGRESS_OMITTED`. Otherwise keep current logic. Update `_render_parallel` to pass `render_path` when we're in the Rich progress branch (requires threading a flag through).

**Defer** if G1/G2 fixes eliminate the warning in practice. Revisit only if new failure modes appear.

---

## 4. BuildContext Schema Hardening

### Problem

Code uses `getattr(build_context, "output_collector", None)` in many places. `BuildContext` does not formally declare these attributes, making propagation bugs easy to introduce and hard to catch with types.

### Options

| Option | Approach | Effort |
|--------|----------|--------|
| **A. Dataclass / typed attrs** | Add `output_collector: OutputCollector | None = None` to BuildContext. All access becomes `ctx.output_collector`. | Medium |
| **B. Protocol** | Define `BuildContextProtocol` with `output_collector`, `reporter`, etc. BuildContext implements it. | Medium |
| **C. Validation at construction** | In dev mode, validate that render-related BuildContext instances have `output_collector` when expected. | Low |

### Recommended Path

**Option A** as part of a broader BuildContext cleanup (see `rfc-global-build-state-dependencies.md` if it exists).

1. Audit `BuildContext` definition and all `getattr(build_context, "output_collector", None)` call sites.
2. Add `output_collector: OutputCollector | None = None` (and `reporter`, `progress_manager` if not already present) as explicit attributes.
3. Replace `getattr(..., "output_collector", None)` with `build_context.output_collector`.
4. Run mypy/ty to catch missing propagation.

**Scope**: Can be done incrementally. Start with `output_collector` only.

---

## 5. Dual output_collector Inputs (Pipeline API)

### Problem

`RenderingPipeline` accepts both `build_context` (which may carry `output_collector`) and `output_collector` as a separate parameter. Redundancy increases cognitive load and risk of inconsistency.

### Options

| Option | Approach | Effort |
|--------|----------|--------|
| **A. Single source** | Pipeline derives `output_collector` from `build_context.output_collector` when `build_context` is present. Remove explicit param. | Medium |
| **B. Explicit only** | Require `output_collector` as explicit param when needed. `build_context` is optional for other data. | Low |
| **C. Keep both (current)** | Document that explicit `output_collector` overrides `build_context.output_collector` when both provided. Defense-in-depth. | None |

### Recommended Path

**Option C** for now. The dual input was intentional for defense-in-depth. Document the precedence:

```python
# RenderingPipeline.__init__ docstring:
# output_collector: Explicit collector for hot reload. When build_context is also
#   provided, this overrides build_context.output_collector. Pass explicitly
#   in worker threads to avoid propagation gaps.
```

Add a one-line comment at the pipeline constructor. **Defer** refactor until BuildContext schema is hardened (item 4).

---

## 6. Import in Warning Path

### Problem

The orchestrator imports `diagnose_missing_output_collector` inside the `if output_collector is None and dev_mode` block. Avoids circular imports but adds import overhead on every warning.

### Fix

1. Try top-level import: `from bengal.orchestration.render.output_collector_diagnostics import diagnose_missing_output_collector`
2. If circular import occurs: keep lazy import but add a brief comment explaining why.
3. Verify no circular dependency: orchestrator → output_collector_diagnostics (diagnostics does not import orchestrator).

### Effort

~15 minutes.

---

## 7. Streaming Fallback Documentation

### Problem

When KnowledgeGraph import fails, the code falls back to standard rendering and warns. There is no retry or alternative; the memory-optimized path is abandoned. Acceptable behavior but undocumented.

### Fix

1. In `streaming.py`, add a module-level docstring or inline comment at the fallback block:

   ```python
   # Fallback: KnowledgeGraph unavailable (e.g. optional dep not installed).
   # Memory optimization is disabled; standard render is used. Hot reload
   # is preserved by passing build_context. See plan/output-collector-long-term-solution.md.
   ```

2. In `plan/output-collector-long-term-solution.md` or this plan, add a "Known Limitations" section:

   - **Streaming fallback**: If KnowledgeGraph cannot be imported, StreamingRenderOrchestrator falls back to RenderOrchestrator.process() with full context. Memory optimization is not used for that build.

### Effort

~10 minutes.

---

## 8. Implementation Order

| Phase | Items | Rationale |
|-------|-------|-----------|
| **1** | 2 (tests), 6 (import) | Low effort, immediate value. Tests protect future changes. |
| **2** | 1 (dead code) | Reduces confusion, small diff. |
| **3** | 7 (docs) | Quick win, no code behavior change. |
| **4** | 3 (heuristic) | Defer unless warnings persist. |
| **5** | 4 (BuildContext) | Larger refactor; coordinate with rfc-global-build-state-dependencies or similar. |
| **6** | 5 (pipeline API) | Defer until item 4 is done. |

---

## 9. Acceptance Criteria

- [ ] `_phase_render` removed or wired up with tests
- [ ] `test_output_collector_diagnostics.py` exists with ≥6 test cases
- [ ] Diagnostic import is top-level (or documented if lazy)
- [ ] Streaming fallback behavior documented in code and plan
- [ ] (Optional) BuildContext has explicit `output_collector` attribute
- [ ] (Optional) Pipeline constructor documents output_collector precedence

---

## 10. Known Limitations

- **Streaming fallback**: If KnowledgeGraph cannot be imported (e.g. optional dep not installed), StreamingRenderOrchestrator falls back to RenderOrchestrator.process() with full context. Memory optimization is not used for that build. Hot reload is preserved by passing build_context. See `bengal/orchestration/streaming.py` lines 208–231.

---

## 11. References

- `plan/output-collector-long-term-solution.md` — Root cause analysis, diagnostic schema
- `bengal/orchestration/render/output_collector_diagnostics.py` — Diagnostic implementation
- `bengal/orchestration/build/__init__.py` — `_phase_render`, main build flow
- `bengal/orchestration/streaming.py` — Streaming fallback path
