# Output Collector: Long-Term Solution & Robust Diagnostics

## Executive Summary

The `output_collector_missing_in_pipeline` warning fires when pipelines render without hot-reload tracking. Multiple code paths can cause this. This document proposes a defense-in-depth fix plus structured diagnostics that communicate the specific failure reason.

---

## 1. Root Cause Analysis

### 1.1 Creation & Intended Flow

```
BuildOrchestrator.build() [__init__.py:384]
  └─ output_collector = BuildOutputCollector(output_dir)
  └─ early_ctx.output_collector = output_collector
  └─ phase_render(..., collector=output_collector)
       └─ ctx = BuildContext(..., output_collector=collector)
       └─ [branch] → StreamingRenderOrchestrator / WaveScheduler / RenderOrchestrator
```

When this flow is followed, `output_collector` is present. The warning indicates a **gap** in propagation.

### 1.2 Identified Gaps (Failure Modes)

| ID | Location | Reason | When |
|----|----------|--------|------|
| **G1** | `streaming.py:218-221` | `orchestrator.process()` called without `build_context` | KnowledgeGraph import fails → fallback drops ctx |
| **G2** | `orchestrator.py:775-782` | `RenderingPipeline` created without `output_collector` param | Rich progress path omits explicit pass |
| **G3** | `__init__.py:1017` | `_phase_render` calls `phase_render` without `collector` | If `_phase_render` ever used (currently dead) |
| **G4** | Any future caller | `process(build_context=ctx)` where `ctx.output_collector` is None | New code paths that create minimal BuildContext |

### 1.3 Why G2 Causes the Warning (Most Likely)

`_render_parallel_with_progress` creates pipelines with only `build_context`. The pipeline falls back to `getattr(build_context, "output_collector", None)`. So if `build_context` has it, we're fine. The warning implies `build_context.output_collector` is None when we reach the orchestrator.

**Hypothesis**: The rich progress path is chosen when `use_rich=True` (not quiet, >5 pages, no Live display). In that path, `build_context` comes from `_process_impl` → `process()` → `phase_render` → `orchestrator.render.process(build_context=ctx)`. So `ctx` should have `output_collector`. Unless `phase_render` is invoked from a path that passes `collector=None`—e.g. a different entry point we haven't found, or `ctx` is being replaced/mutated.

**Alternative**: The snapshot path may bypass `phase_render`'s ctx. When `_render_parallel` receives `build_context` with a snapshot, it calls `_render_with_snapshot`, which uses `WaveScheduler`. But `_render_with_snapshot` gets `build_context` from the same `process()` call. So it should still have `output_collector`.

The most actionable fix is to **close all known gaps** and **add structured diagnostics** so when it happens again, we know why.

---

## 2. Long-Term Solution Architecture

### 2.1 Principles

1. **Single source of truth**: `output_collector` is created once in `BuildOrchestrator.build()` and attached to `early_ctx` and passed as `collector` to `phase_render`.
2. **Explicit propagation**: Every render path that creates pipelines passes `output_collector` explicitly. No reliance on "it might be on build_context."
3. **Fail-fast in dev**: When `dev_mode=True` and we're about to render without `output_collector`, emit a structured diagnostic (not just a generic warning).
4. **Structured reason codes**: Each failure mode has a unique `source` so logs and fixes are traceable.

### 2.2 Diagnostic Schema

```python
# When output_collector is missing in dev mode
{
    "event": "output_collector_missing_in_pipeline",
    "source": str,      # One of: STREAMING_FALLBACK, RICH_PROGRESS_OMITTED, BUILD_CONTEXT_NONE, COLLECTOR_NOT_PROPAGATED, UNKNOWN
    "caller": str,      # e.g. "RenderOrchestrator._render_parallel_with_progress"
    "build_context_present": bool,
    "worker_threads": int,
    "hint": str,        # Human-readable fix suggestion
}
```

### 2.3 Source Enum (Reason Codes)

| Source | Meaning | Fix |
|--------|---------|-----|
| `STREAMING_FALLBACK` | StreamingRenderOrchestrator fell back to process() without build_context | Pass build_context in streaming.py fallback |
| `RICH_PROGRESS_OMITTED` | _render_parallel_with_progress created pipeline without output_collector | Pass output_collector explicitly |
| `BUILD_CONTEXT_NONE` | process() was called with build_context=None | Ensure caller passes build_context |
| `COLLECTOR_NOT_PROPAGATED` | build_context exists but output_collector is None | Fix phase_render caller to pass collector |
| `PHASE_RENDER_NO_COLLECTOR` | _phase_render called phase_render without collector | Add collector to _phase_render |
| `UNKNOWN` | Could not determine source | Add instrumentation |

---

## 3. Implementation Plan

### Phase 1: Close Propagation Gaps (Defense in Depth)

| Gap | File | Change |
|-----|------|--------|
| G1 | `orchestration/streaming.py` | In fallback (lines 218-221), pass `build_context`, `reporter`, `changed_sources` to `orchestrator.process()` |
| G2 | `orchestration/render/orchestrator.py` | In `_render_parallel_with_progress`, extract `output_collector` and pass to `RenderingPipeline` (same pattern as _render_parallel_simple) |
| G3 | `orchestration/build/__init__.py` | In `_phase_render`, pass `collector`, `early_context`, `changed_sources` to `phase_render` (future-proofing) |

### Phase 2: Centralized Diagnostic Helper

Create `bengal/orchestration/render/output_collector_diagnostics.py`:

```python
"""Structured diagnostics for output_collector propagation failures."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

class OutputCollectorSource(Enum):
    STREAMING_FALLBACK = "streaming_fallback"
    RICH_PROGRESS_OMITTED = "rich_progress_omitted"
    BUILD_CONTEXT_NONE = "build_context_none"
    COLLECTOR_NOT_PROPAGATED = "collector_not_propagated"
    PHASE_RENDER_NO_COLLECTOR = "phase_render_no_collector"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class OutputCollectorDiagnostic:
    source: OutputCollectorSource
    caller: str
    build_context_present: bool
    worker_threads: int
    hint: str

    def to_log_context(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "caller": self.caller,
            "build_context_present": self.build_context_present,
            "worker_threads": self.worker_threads,
            "hint": self.hint,
        }

SOURCE_HINTS: dict[OutputCollectorSource, str] = {
    OutputCollectorSource.STREAMING_FALLBACK: (
        "StreamingRenderOrchestrator fallback dropped build_context. "
        "Pass build_context to orchestrator.process() in streaming.py fallback."
    ),
    OutputCollectorSource.RICH_PROGRESS_OMITTED: (
        "_render_parallel_with_progress omits output_collector. "
        "Pass output_collector explicitly to RenderingPipeline."
    ),
    OutputCollectorSource.BUILD_CONTEXT_NONE: (
        "process() called without build_context. "
        "Ensure caller passes build_context from phase_render."
    ),
    OutputCollectorSource.COLLECTOR_NOT_PROPAGATED: (
        "build_context exists but output_collector is None. "
        "Fix phase_render caller to pass collector=output_collector."
    ),
    OutputCollectorSource.PHASE_RENDER_NO_COLLECTOR: (
        "_phase_render calls phase_render without collector. "
        "Add collector param to _phase_render."
    ),
    OutputCollectorSource.UNKNOWN: (
        "Hot reload will fall back to full reload. "
        "Run with BENGAL_LOG_LEVEL=debug for trace."
    ),
}

def diagnose_missing_output_collector(
    *,
    build_context: Any,
    caller: str,
    worker_threads: int,
) -> OutputCollectorDiagnostic:
    """Determine why output_collector is missing and return structured diagnostic."""
    if build_context is None:
        return OutputCollectorDiagnostic(
            source=OutputCollectorSource.BUILD_CONTEXT_NONE,
            caller=caller,
            build_context_present=False,
            worker_threads=worker_threads,
            hint=SOURCE_HINTS[OutputCollectorSource.BUILD_CONTEXT_NONE],
        )
    if getattr(build_context, "output_collector", None) is None:
        return OutputCollectorDiagnostic(
            source=OutputCollectorSource.COLLECTOR_NOT_PROPAGATED,
            caller=caller,
            build_context_present=True,
            worker_threads=worker_threads,
            hint=SOURCE_HINTS[OutputCollectorSource.COLLECTOR_NOT_PROPAGATED],
        )
    return OutputCollectorDiagnostic(
        source=OutputCollectorSource.UNKNOWN,
        caller=caller,
        build_context_present=True,
        worker_threads=worker_threads,
        hint=SOURCE_HINTS[OutputCollectorSource.UNKNOWN],
    )
```

### Phase 3: Caller-Specific Source Detection

In `RenderOrchestrator._render_parallel`, we know the caller. For `_render_parallel_with_progress`, we can pass `source=RICH_PROGRESS_OMITTED` when we detect the gap (before we fix it). After the fix, that path won't warn. For `StreamingRenderOrchestrator` fallback, pass `source=STREAMING_FALLBACK`.

The diagnostic helper can accept an optional `known_source` when the caller knows why (e.g. "I'm the streaming fallback and I didn't pass build_context").

### Phase 4: Integrate into Orchestrator Warning

Replace the current warning block in `_render_parallel`:

```python
# Current (simplified)
if build_context and not getattr(build_context, "output_collector", None):
    if dev_mode:
        logger.warning("output_collector_missing_in_pipeline", ...)

# New
if build_context is None or not getattr(build_context, "output_collector", None):
    if dev_mode:
        diagnostic = diagnose_missing_output_collector(
            build_context=build_context,
            caller="_render_parallel",
            worker_threads=max_workers,
        )
        logger.warning(
            "output_collector_missing_in_pipeline",
            **diagnostic.to_log_context(),
        )
```

### Phase 5: Add Diagnostic to Streaming Fallback

In `streaming.py` fallback, before calling `orchestrator.process()`:

```python
# Before fix: warn that we're about to drop output_collector
if build_context and getattr(build_context, "output_collector", None):
    logger.warning(
        "output_collector_missing_in_pipeline",
        source=OutputCollectorSource.STREAMING_FALLBACK.value,
        caller="StreamingRenderOrchestrator.process",
        hint="Pass build_context to orchestrator.process() in fallback.",
    )
# Then fix: pass build_context
orchestrator.process(
    pages, parallel, quiet, stats,
    progress_manager=progress_manager,
    build_context=build_context,  # ADD
    reporter=reporter,           # ADD
    changed_sources=changed_sources,  # ADD if available
)
```

---

## 4. Files to Modify

| File | Changes |
|------|---------|
| `bengal/orchestration/streaming.py` | Pass build_context, reporter, changed_sources in fallback; add diagnostic if we can't |
| `bengal/orchestration/render/orchestrator.py` | Add output_collector to _render_parallel_with_progress; use diagnose_missing_output_collector |
| `bengal/orchestration/build/__init__.py` | Fix _phase_render to pass collector, early_context, changed_sources |
| `bengal/orchestration/render/output_collector_diagnostics.py` | New module with diagnostic helper |
| `plan/output-collector-propagation-plan.md` | Update with long-term solution reference |

---

## 5. Testing Strategy

1. **Unit test**: `diagnose_missing_output_collector` returns correct source for each case.
2. **Integration test**: Dev server build with each render path (simple, live progress, rich progress, streaming, snapshot) — no warning when gaps are closed.
3. **Regression test**: Intentionally break propagation (e.g. pass None) and assert the warning includes the correct `source`.

---

## 6. Rollout Order

1. Create `output_collector_diagnostics.py` (no behavior change).
2. Fix G2: Add output_collector to _render_parallel_with_progress.
3. Fix G1: Pass build_context in streaming fallback.
4. Fix G3: Update _phase_render (future-proofing).
5. Integrate diagnostic helper into orchestrator warning (replace current block).
6. Add tests.

---

## 7. Success Criteria

- No `output_collector_missing_in_pipeline` warning in normal dev server builds.
- When it does fire (e.g. intentional test or future regression), the log includes `source` and `hint` for actionable debugging.
- All four render paths (simple, live progress, rich progress, streaming) propagate output_collector correctly.

---

## 8. Known Limitations

- **Streaming fallback**: If KnowledgeGraph cannot be imported, StreamingRenderOrchestrator falls back to RenderOrchestrator.process() with full context. Memory optimization is not used for that build; hot reload remains functional.
