# feature/benchmark-suite-enhancements

## Branch Purpose
Follow-up work to the merged "Add Robust Benchmarking Suite" PR. This branch implements critical enhancements needed to:
1. Validate incremental build fixes (currently broken - 1.1x speedup)
2. Identify scale degradation causes (141 pps → 29 pps at scale)
3. Track performance regressions over time
4. Profile and find bottlenecks

## Context
See `plan/active/BENCHMARK_RESULTS_ANALYSIS.md` for the analysis that triggered this work.

## Planned Phases

### Phase 1: Critical Infrastructure (Days 1-3) 🔴
- Incremental build benchmarking (tests single-page, multi-page, asset, config changes)
- Memory profiling (tracemalloc integration)
- Regression detection (pytest-benchmark comparison mode)

### Phase 2: Enhanced Scenarios (Days 4-5) 🟡
- Dynamic scenario generator (1K/5K/10K pages without disk bloat)
- API documentation scenario (Sphinx migration use case)
- Nested section hierarchy scenario

### Phase 3: Profiling Tools (Days 6-7) 🟢
- CPU profiling integration
- Flame graph generation

### Phase 4: Reporting & CI (Days 8-10) 🔵
- HTML benchmark report generator
- GitHub Actions workflow

## Quick Start
See `plan/active/BENCHMARK_SUITE_ENHANCEMENTS.md` for detailed implementation specs.

## Key Deliverables
1. Incremental builds show true speedup (or confirm the bug)
2. Memory usage baseline per scenario size
3. Historical performance tracking with regression detection
4. CPU flame graphs identifying bottlenecks
5. Automated benchmark CI/CD workflow

## Related Issues
- Incremental builds performing full rebuilds (need to validate fix)
- Performance degradation at scale (10K pages = 29 pps)
