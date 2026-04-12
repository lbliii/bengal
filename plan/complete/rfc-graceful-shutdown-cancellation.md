# RFC: Graceful Shutdown with Build Cancellation

**Status**: Implemented (Phase 2)  
**Created**: 2025-03-07  
**Goal**: Replace `os._exit()` workaround with proper cooperative cancellation for S-tier Ctrl+C UX.

---

## Problem

When the user presses Ctrl+C during `bengal serve` (especially during the initial or validation build), the current `os._exit()` approach:

- **Works** but bypasses Python shutdown entirely
- **Avoids** the root cause: `ThreadPoolExecutor` atexit handlers fail during interrupt
- **Risks** unflushed stdout/stderr in edge cases

The root cause: **initial and validation builds run in-process** via `site.build()`, which uses `ThreadPoolExecutor` in 5+ places. When SIGINT arrives, our signal handler runs, but Python's shutdown sequence then tries to join those executor threads and fails with `KeyboardInterrupt`.

---

## Architecture Summary

### Build Execution Paths

| Path | Entry Point | Executor | Process |
|------|-------------|----------|---------|
| Initial build (build-first) | `dev_server.py` L296 | `site.build()` → ThreadPoolExecutor (provenance, postprocess, autodoc) | **Main** |
| Validation build (serve-first) | `dev_server.py` L426 | `site.build()` → same | **Main** |
| Hot reload | `BuildTrigger` → `BuildExecutor` | ProcessPoolExecutor (default) or ThreadPoolExecutor (3.14t) | **Subprocess** or Main |

### ThreadPoolExecutor Usage (in-process build)

| Module | Location | Purpose |
|--------|----------|---------|
| `orchestration/build/provenance_filter.py` | L908 | `record_build_for_pages` (parallel provenance) |
| `build/provenance/filter.py` | L211 | Provenance filter (similar) |
| `orchestration/postprocess.py` | L301 | Parallel postprocessing |
| `autodoc/extractors/python/extractor.py` | L434 | Extract Python API docs |
| `snapshots/scheduler.py` | L251 | Snapshot scheduling |

### Key Constraint: Python 3.14t

On free-threaded Python (3.14t), `BuildExecutor` uses `ThreadPoolExecutor` instead of `ProcessPoolExecutor`. So even hot reload builds run in-process. The subprocess isolation strategy only helps when `BENGAL_BUILD_EXECUTOR=process`.

---

## Solution Options

### Option A: Process Isolation for Initial/Validation Builds (Medium Effort)

**Idea**: Run initial and validation builds through `BuildExecutor` with `ProcessPoolExecutor` forced.

**Changes**:
1. Add `BuildExecutor` to dev server startup (already exists for hot reload via BuildTrigger)
2. For initial build: submit `BuildRequest` to executor, block on result
3. For validation build: same
4. Force `BENGAL_BUILD_EXECUTOR=process` for dev server (or accept that 3.14t users keep `os._exit`)

**Pros**: Main process never has build ThreadPoolExecutors; `sys.exit(0)` works cleanly  
**Cons**: 3.14t default (ThreadPoolExecutor) still has the problem; process spawn overhead for cold start

---

### Option B: Cooperative Cancellation (High Effort, S-Tier)

**Idea**: Plumb a cancellation token through the build pipeline; check it in executor loops; shutdown executors with `cancel_futures=True` on SIGINT.

**Components**:

1. **Cancellation token** (e.g. `threading.Event` or `contextvars.ContextVar`)
   - Set by ResourceManager signal handler before cleanup
   - Checked by build phases before/during work

2. **BuildContext / BuildOptions** extension
   - Add `cancelled: threading.Event | None` (optional, for dev server builds)
   - Pass through `BuildOrchestrator` → phases → executor loops

3. **Executor loop pattern** (each of 5 sites):
   ```python
   for future in as_completed(futures):
       if cancelled and cancelled.is_set():
           executor.shutdown(wait=False, cancel_futures=True)
           raise BuildCancelled()
       future.result()
   ```

4. **ResourceManager** flow:
   - On first SIGINT: set `cancelled` event, call `cleanup()`, then `sys.exit(0)`
   - Build (if running) sees cancellation, exits loop, executor shuts down cleanly
   - No `os._exit`; normal Python shutdown runs

**Pros**: Proper solution; works on all Python versions; no process overhead  
**Cons**: Significant refactoring; every executor loop must be updated; `BuildCancelled` handling

---

### Option C: Hybrid – Process for Initial, Keep os._exit for 3.14t (Low Effort)

**Idea**: Use `BuildExecutor` with `ProcessPoolExecutor` for initial/validation when possible. On 3.14t (ThreadPoolExecutor), keep `os._exit()` but add flush.

**Changes**:
1. Route initial + validation builds through BuildExecutor
2. Set `BENGAL_BUILD_EXECUTOR=process` in dev server env (override auto-detection)
3. Fallback: if ThreadPoolExecutor (user override), keep current `os._exit` + add `sys.stdout.flush()` before exit

**Pros**: Fixes common case (non-free-threaded); minimal code change  
**Cons**: 3.14t users still get os._exit; two code paths

---

## Recommended Plan: Phased Approach

### Phase 1: Quick Win (1–2 hours)

- Add `sys.stdout.flush()` and `sys.stderr.flush()` before `os._exit()` in ResourceManager
- Ensures shutdown messages are visible
- Keeps current behavior, improves robustness

### Phase 2: Process Isolation for Dev Server Builds (1–2 days)

1. **Unify build entry**: Create `_run_build_via_executor()` in dev_server that:
   - Builds `BuildRequest` from `BuildOptions` + site root
   - Submits to `BuildExecutor` (shared with BuildTrigger)
   - Blocks on result, displays stats

2. **Replace direct `site.build()` calls**:
   - Initial build (build-first): use `_run_build_via_executor()`
   - Validation build: use `_run_build_via_executor()`

3. **Force process executor for dev server**:
   - In `DevServer.__init__` or before first build: `os.environ["BENGAL_BUILD_EXECUTOR"] = "process"`
   - Ensures build runs in subprocess; main process stays clean

4. **Revert to `sys.exit()`** in ResourceManager (remove `os._exit`)
   - Main process no longer has build ThreadPoolExecutors
   - Normal shutdown works

### Phase 3: Cancellation Support (Future, Optional)

- Add `BuildContext.cancelled: threading.Event | None`
- Plumb through `BuildOptions` → `BuildInput` → `BuildContext`
- Update 5 executor loops to check and `shutdown(cancel_futures=True)`
- Enables graceful cancellation for `bengal build` (CLI) as well
- Useful for CI timeouts, long builds

---

## Implementation Checklist (Phase 2)

- [x] Add `_run_build_via_executor()` to DevServer (creates executor on demand)
- [x] Implement `_run_build_via_executor(build_opts, description)` returning `MinimalStats`
- [x] Replace `self.site.build(build_opts)` with `_run_build_via_executor()` in:
  - [x] Build-first path (initial build)
  - [x] Validation build path (serve-first)
- [x] Set `BENGAL_BUILD_EXECUTOR=process` for dev server process (before first build)
- [x] Revert ResourceManager: `os._exit` → `sys.exit`
- [x] Update tests for new flow
- [x] Manual test: Ctrl+C during initial build, validation build, hot reload

---

## Files to Modify (Phase 2)

| File | Change |
|------|--------|
| `bengal/server/dev_server.py` | Add BuildExecutor, `_run_build_via_executor`, replace `site.build` calls |
| `bengal/server/resource_manager.py` | Revert `os._exit` → `sys.exit` |
| `bengal/server/build_executor.py` | Ensure `BuildRequest` supports full build (no changed_paths = full) |
| `tests/unit/server/test_resource_manager.py` | Revert mock from `os._exit` to `sys.exit` |

---

## Success Criteria

- Ctrl+C during any build phase shows: "Shutting down gracefully...", "Server stopped", then clean exit
- No "Exception ignored on threading shutdown" traceback
- No "Aborted!" from Click
- `bengal serve` startup time unchanged (process spawn is one-time)
- All existing tests pass
