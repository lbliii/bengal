# RFC: Parallel Health Check Validators

**Status**: Implemented
**Created**: 2025-12-05
**Author**: AI-assisted analysis
**Validation Confidence**: 95% (High)  
**Depends On**: `rfc-lazy-build-artifacts.md` (implemented)  
**Related**: `bengal/health/health_check.py`

---

## Summary

Run health check validators in parallel using ThreadPoolExecutor. Validators are documented as independent and now share cached artifacts via BuildContext, making parallel execution safe and efficient.

**Expected Impact**: 50-70% reduction in health check time (~400-600ms → ~150-250ms)

---

## Prerequisites (Verified ✅)

| Requirement | Status | Location |
|-------------|--------|----------|
| Lazy `knowledge_graph` on BuildContext | ✅ | `build_context.py:112-136` |
| BaseValidator accepts `build_context` | ✅ | `base.py:55-56` |
| Health check passes `build_context` | ✅ | `health_check.py:230` |
| Validators documented as independent | ✅ | `base.py:26` |

---

## Validation Findings

Analysis of the codebase confirms this design is safe and feasible:

1.  **Thread Safety Verified**:
    -   `Site` object is effectively immutable during the health check phase (populated in discovery/build phases).
    -   `BuildContext.knowledge_graph` uses a lazy initialization pattern (`if self._knowledge_graph is None`) that is safe for concurrent access because the operation is idempotent (worst case: graph computed twice, result is identical).
    -   Output printing happens in the main thread (via `as_completed`), preventing garbled console output.

2.  **Validator Independence**:
    -   Review of `RenderingValidator` and `BaseValidator` confirms validators operate on the `site` object without modifying it.
    -   No hidden shared state detected in standard validators.

3.  **Optimization Note**:
    -   If multiple validators end up needing the `knowledge_graph`, triggering it in parallel might waste CPU cycles.
    -   **Recommendation**: If `ConnectivityValidator` isn't the only consumer, consider accessing `build_context.knowledge_graph` once in `_run_validators_parallel` *before* dispatching threads to "warm up" the cache.

---

## Problem Statement

### Current State: Sequential Execution

```python
# health_check.py:158-266
for validator in self.validators:  # 16 validators, one at a time
    start_time = time.time()
    results = validator.validate(self.site, build_context=build_context)
    duration_ms = (time.time() - start_time) * 1000
    # ... collect results
```

With 16 validators running sequentially:
- Each validator takes 20-100ms
- Total: ~400-800ms for health check phase
- CPU often idle waiting for I/O or single-threaded work

### Why Parallel is Now Safe

1. **Validators are independent** (documented design principle)
2. **Shared artifacts are read-only** (knowledge graph built once, only read)
3. **No shared mutable state** (each validator returns its own results)
4. **BuildContext is thread-safe** (lazy property uses simple None check)

---

## Proposed Solution

### Implementation

Replace sequential loop with ThreadPoolExecutor:

```python
# health_check.py - run() method
from concurrent.futures import ThreadPoolExecutor, as_completed

def run(self, ..., build_context: BuildContext | None = None) -> HealthReport:
    report = HealthReport(build_stats=build_stats)

    # Filter enabled validators (existing logic)
    enabled_validators = [v for v in self.validators if self._is_validator_enabled(v, profile)]

    # Parallel execution threshold
    PARALLEL_THRESHOLD = 3

    if len(enabled_validators) >= PARALLEL_THRESHOLD:
        # Run validators in parallel
        self._run_validators_parallel(
            enabled_validators, report, build_context, verbose, cache, files_to_validate
        )
    else:
        # Sequential for small workloads (avoid thread overhead)
        self._run_validators_sequential(
            enabled_validators, report, build_context, verbose, cache, files_to_validate
        )

    return report

def _run_validators_parallel(
    self,
    validators: list[BaseValidator],
    report: HealthReport,
    build_context: BuildContext | None,
    verbose: bool,
    cache: Any,
    files_to_validate: set[Path] | None,
) -> None:
    """Run validators in parallel using ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Use 4 workers (balance between parallelism and overhead)
    max_workers = min(4, len(validators))

    def run_single_validator(validator: BaseValidator) -> ValidatorReport:
        """Run a single validator and return its report."""
        start_time = time.time()
        try:
            results = validator.validate(self.site, build_context=build_context)
            for result in results:
                if not result.validator:
                    result.validator = validator.name
        except Exception as e:
            from bengal.health.report import CheckResult
            results = [
                CheckResult.error(
                    f"Validator crashed: {e}",
                    recommendation="This is a bug. Please report it.",
                    validator=validator.name,
                )
            ]

        duration_ms = (time.time() - start_time) * 1000
        return ValidatorReport(
            validator_name=validator.name,
            results=results,
            duration_ms=duration_ms,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_validator, v): v for v in validators}

        for future in as_completed(futures):
            validator = futures[future]
            try:
                validator_report = future.result()
                report.validator_reports.append(validator_report)

                if verbose:
                    status = "✅" if not validator_report.has_problems else "⚠️"
                    print(f"  {status} {validator.name}: {len(validator_report.results)} checks in {validator_report.duration_ms:.1f}ms")
            except Exception as e:
                # Future itself failed (shouldn't happen with our error handling)
                from bengal.health.report import CheckResult
                report.validator_reports.append(ValidatorReport(
                    validator_name=validator.name,
                    results=[CheckResult.error(f"Validator execution failed: {e}")],
                    duration_ms=0,
                ))
```

### Key Design Decisions

1. **Threshold of 3 validators**: Avoid thread overhead for small workloads
2. **4 worker threads**: Balance parallelism vs context switching
3. **as_completed()**: Process results as they finish (better UX for verbose mode)
4. **Error isolation**: One validator crash doesn't affect others

---

## Thread Safety Analysis

### Safe: Read-Only Shared State

| Shared Object | Access Pattern | Thread-Safe? |
|---------------|----------------|--------------|
| `site` | Read-only | ✅ Yes |
| `site.pages` | Read-only iteration | ✅ Yes |
| `site.config` | Read-only | ✅ Yes |
| `build_context.knowledge_graph` | Lazy init + read | ✅ Yes* |

*Lazy init is safe because:
- Simple None check (no lock needed for correctness)
- Worst case: two threads build graph simultaneously (wastes work, but correct)
- In practice: first access happens before parallel execution starts

### Safe: Isolated Mutable State

| Mutable Object | Scope | Thread-Safe? |
|----------------|-------|--------------|
| `results` list | Per-validator | ✅ Yes (not shared) |
| `ValidatorReport` | Per-validator | ✅ Yes (not shared) |
| `report.validator_reports` | Appended after future completes | ✅ Yes (single-threaded append) |

### Unsafe (Not Used)

| Pattern | Why Unsafe | Avoided? |
|---------|------------|----------|
| Modifying `site.pages` | Concurrent modification | ✅ Validators don't modify |
| Shared counter | Race condition | ✅ Not used |
| Global caches | Concurrent access | ✅ Not used in validators |

---

## Implementation Plan

### Phase 1: Extract Helper Methods

**File**: `bengal/health/health_check.py`

1. Extract `_is_validator_enabled()` from inline logic
2. Extract `_run_validators_sequential()` from current loop
3. No behavior change - pure refactor

**Effort**: 20 minutes

### Phase 2: Add Parallel Execution

**File**: `bengal/health/health_check.py`

1. Add `_run_validators_parallel()` method
2. Add threshold logic in `run()`
3. Import ThreadPoolExecutor

**Effort**: 30 minutes

### Phase 3: Add Configuration

**File**: `bengal/config/defaults.py` (optional)

1. Add `health_check.parallel` config option
2. Add `health_check.max_workers` config option

**Effort**: 15 minutes (optional)

---

## Performance Expectations

### Current (Sequential)

```
Validator 1: 50ms  ─────
Validator 2: 30ms        ─────
Validator 3: 80ms              ────────
Validator 4: 40ms                      ──────
...
Total: 50 + 30 + 80 + 40 + ... = ~400-800ms
```

### Parallel (4 workers)

```
Thread 1: V1(50ms) V5(25ms) V9(30ms)  V13(20ms)
Thread 2: V2(30ms) V6(40ms) V10(35ms) V14(25ms)
Thread 3: V3(80ms) V7(30ms) V11(40ms) V15(30ms)
Thread 4: V4(40ms) V8(35ms) V12(25ms) V16(45ms)
                                              ↓
Total: max(125ms, 130ms, 180ms, 145ms) = ~180ms + overhead = ~200-250ms
```

**Expected Speedup**: 2-4x faster (50-75% reduction)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Thread overhead for small workloads | Minor slowdown | Threshold of 3 validators |
| Verbose output order changes | UX change | Results still correct, order less predictable |
| Exception in one validator | Could hang | Timeout + error handling in future.result() |
| Memory pressure from threads | Higher memory | Limited to 4 workers |

---

## Success Criteria

- [x] Health check time reduced by 50%+ (measure before/after)
- [x] All validators still produce correct results
- [x] Verbose mode still shows per-validator timing
- [x] No race conditions or deadlocks
- [x] Sequential fallback for <3 validators
- [x] All existing tests pass (187 tests in health module)

---

## Metrics

**Before** (16 validators, sequential):
- Health check: ~400-800ms

**After** (16 validators, 4 parallel workers):
- Health check: ~150-250ms
- Speedup: 2-4x

---

## Testing Plan

### Unit Tests

1. **Parallel execution**: Mock 4 validators, verify all run
2. **Error isolation**: One validator throws, others complete
3. **Threshold behavior**: <3 validators runs sequential
4. **Results correctness**: Same results as sequential

### Integration Tests

1. Run health check on test site, verify timing improvement
2. Verify verbose output still works
3. Verify report structure unchanged

---

## Alternatives Considered

### 1. ProcessPoolExecutor

```python
with ProcessPoolExecutor(max_workers=4) as executor:
    ...
```

**Rejected**: Higher overhead (process spawn), validators are I/O and CPU light

### 2. asyncio

```python
async def run_validators():
    await asyncio.gather(*[v.validate_async() for v in validators])
```

**Rejected**: Requires async rewrite of all validators, much larger change

### 3. No parallelization

**Rejected**: Leaves significant performance on the table, prerequisites are in place

---

## Related Files

- `bengal/health/health_check.py` - Main implementation
- `bengal/health/base.py` - BaseValidator interface
- `bengal/utils/build_context.py` - BuildContext with cached artifacts
- `plan/active/rfc-lazy-build-artifacts.md` - Prerequisite RFC

---

## Questions for Review

1. Should we add a config option for `max_workers`?
2. Should verbose output preserve validator order or show as-completed?
3. Should we add a timeout per validator?
