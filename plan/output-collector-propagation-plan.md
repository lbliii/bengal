# Output Collector Propagation — Analysis & Plan

## Problem

`output_collector_missing_in_pipeline` warning fires repeatedly during dev server builds. The warning indicates `RenderingPipeline` was created with `build_context` present but no `output_collector`, degrading hot reload (fallback to full reload instead of CSS-only).

## Call Graph: Where Pipelines Are Created

| Caller | build_context | output_collector | Status |
|--------|---------------|------------------|--------|
| **ReactiveContentHandler** | `None` | Explicit (creates own) | ✓ OK |
| **WaveScheduler** (from phase_render) | `ctx` | Explicit `collector` | ✓ OK |
| **WaveScheduler** (from RenderOrchestrator) | `build_context` | From `build_context.output_collector` | ⚠️ Gap |
| **RenderOrchestrator** (_render_parallel_simple) | `build_context` | From `build_context.output_collector` | ⚠️ Gap |
| **RenderOrchestrator** (_render_parallel_with_live_progress) | `build_context` | From `build_context.output_collector` | ⚠️ Gap |
| **StreamingRenderOrchestrator** fallback | `None` | N/A | ✓ No warning |

## Build Flow: Where output_collector Originates

```
BuildOrchestrator.build()
  └─ output_collector = BuildOutputCollector(...)     # Line 384, always created
  └─ early_ctx.output_collector = output_collector    # Line 643
  └─ phase_render(..., collector=output_collector)
       └─ ctx = BuildContext(..., output_collector=collector)  # Lines 477, 515
       ├─ [memory_optimized] StreamingRenderOrchestrator.process(build_context=ctx)
       ├─ [snapshot + parallel] WaveScheduler(..., output_collector=collector)
       └─ [fallback] orchestrator.render.process(build_context=ctx)
```

**Conclusion**: `ctx` is always built with `output_collector=collector`. All render paths receive this `ctx`.

## Identified Gaps

### 1. RenderOrchestrator._render_with_snapshot

When `process()` is called with `build_context` that has a snapshot, it creates `WaveScheduler` **without** passing `output_collector`:

```python
# orchestrator.py:446-453
scheduler = WaveScheduler(
    snapshot=snapshot,
    site=self.site,
    ...
    build_context=build_context,
    max_workers=max_workers,
    # output_collector NOT passed — relies on build_context.output_collector
)
```

`WaveScheduler` falls back to `getattr(build_context, "output_collector", None)`. When `phase_render` calls this path, `build_context` is `ctx` which has `output_collector`. So this should work — **unless** `process()` is ever called from elsewhere with a `build_context` that lacks `output_collector`.

### 2. RenderOrchestrator Pipeline Creation

Both `_render_parallel_simple` and `_render_parallel_with_live_progress` create pipelines with `build_context` but no explicit `output_collector`. The pipeline uses:

```python
self._output_collector = output_collector or (
    getattr(build_context, "output_collector", None) if build_context else None
)
```

So the pipeline gets it from `build_context.output_collector`. When `build_context` is `ctx` from `phase_render`, it should be set.

### 3. Hypothesis: Why the Warning Fires

Possible causes:

- **A)** A code path passes `build_context` without `output_collector` (not yet found in main flow).
- **B)** Tests or alternate entry points create pipelines with mock/minimal `BuildContext`.
- **C)** `BuildContext` is a dataclass; in some edge case the attribute is missing or overwritten.
- **D)** The warning is overly broad — it fires when `build_context` exists but collector is legitimately optional (e.g. production build where hot reload is irrelevant).

## Proposed Plan

### Phase 1: Harden Propagation (Defense in Depth)

**Goal**: Ensure `output_collector` is passed explicitly wherever we have it, so we don't rely solely on `build_context.output_collector`.

| Location | Change |
|----------|--------|
| `RenderOrchestrator._render_with_snapshot` | Pass `output_collector=getattr(build_context, "output_collector", None)` to `WaveScheduler` |
| `RenderOrchestrator._render_parallel_simple` | Already passes explicitly (from prior fix) |
| `RenderOrchestrator._render_parallel_with_live_progress` | Already passes explicitly (from prior fix) |

### Phase 2: Conditional Warning

**Goal**: Only warn when the missing collector actually matters (dev server / hot reload).

```python
# In RenderingPipeline.__init__
if build_context and not self._output_collector:
    # Only warn when hot reload would benefit (dev server)
    site = getattr(build_context, "site", None)
    dev_mode = getattr(site, "dev_mode", False) if site else False
    if dev_mode:
        logger.warning(
            "output_collector_missing_in_pipeline",
            has_build_context=True,
            hint="Hot reload will fall back to full reload",
        )
    else:
        logger.debug(
            "output_collector_missing_in_pipeline",
            has_build_context=True,
        )
```

### Phase 3: Add Assertion in Build Flow (Optional)

**Goal**: Fail fast if we ever create a render context without `output_collector` when it should be present.

In `phase_render`, before passing `ctx` to any renderer:

```python
if not ctx.output_collector and getattr(orchestrator.site, "dev_mode", False):
    raise AssertionError(
        "output_collector must be set on BuildContext for dev server hot reload"
    )
```

This would surface any future regression immediately.

### Phase 4: Instrumentation (Debugging)

**Goal**: If the warning persists, add temporary logging to identify the exact caller.

```python
if build_context and not self._output_collector:
    import traceback
    logger.debug(
        "output_collector_missing_trace",
        has_build_context=True,
        trace=traceback.format_stack()[-10:],
    )
```

Run with `BENGAL_LOG_LEVEL=debug` to capture the trace, then remove once root cause is found.

## Recommended Implementation Order

1. **Phase 1** — Fix `_render_with_snapshot` to pass `output_collector` explicitly.
2. **Phase 2** — Make the warning conditional on `dev_mode`.
3. **Phase 3** — Add assertion only if Phase 1+2 don't resolve the issue.
4. **Phase 4** — Use only if the warning continues after Phase 1–2.

## Files to Modify

| File | Changes |
|------|---------|
| `bengal/orchestration/render/orchestrator.py` | Pass `output_collector` in `_render_with_snapshot` |
| `bengal/rendering/pipeline/core.py` | Conditional warning (Phase 2) |
| `bengal/orchestration/build/rendering.py` | Optional assertion (Phase 3) |

## Revert Previous Band-Aid

The prior fix downgraded the warning to `logger.debug`. If we implement Phase 2 (conditional warning), we can restore `logger.warning` for the dev_mode case and keep `logger.debug` for production. The explicit `output_collector` passing in RenderOrchestrator (from the earlier fix) should remain as defense in depth.
