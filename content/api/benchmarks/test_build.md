
---
title: "test_build"
type: "python-module"
source_file: "benchmarks/test_build.py"
line_number: 1
description: "Benchmark suite for Bengal SSG build performance. This suite validates performance claims and tracks improvements over time. All benchmarks use pytest-benchmark for statistical analysis. Benchmark Cat..."
---

# test_build
**Type:** Module
**Source:** [View source](benchmarks/test_build.py#L1)



**Navigation:**
[benchmarks](/api/benchmarks/) ›test_build

Benchmark suite for Bengal SSG build performance.

This suite validates performance claims and tracks improvements over time.
All benchmarks use pytest-benchmark for statistical analysis.

Benchmark Categories:
====================

1. Full Build Performance
   - test_build_performance: Baseline builds for small/large sites
   - test_full_build_baseline: Full build without cache (baseline for comparisons)

2. Fast Mode Benchmarks
   - test_fast_mode_cli_flag: Build with --fast flag (quiet + guaranteed parallel)
   - test_fast_mode_vs_default: Compare fast mode vs default build
   - test_incremental_with_fast_mode: Incremental + fast mode combination

3. Parallel Processing Benchmarks
   - test_parallel_vs_sequential: Parallel vs sequential builds (validates 2-4x speedup)
   - test_sequential_build: Sequential build baseline

4. Incremental Build Benchmarks
   - test_incremental_single_page_change: Single page edit (most common workflow)
   - test_incremental_multi_page_change: Batch edits (5 pages)
   - test_incremental_config_change: Config modification (should trigger full rebuild)
   - test_incremental_no_changes: Cache validation (should be <1s)

5. Memory Optimization Benchmarks
   - test_memory_optimized_build: Streaming build for large sites (--memory-optimized)
   - test_memory_usage_small_site: Memory profiling for small sites
   - test_memory_usage_large_site: Memory profiling for large sites (100 pages)
   - test_incremental_memory_tracking: Memory usage during incremental builds

Expected Performance (Python 3.14):
====================================
- Full build: ~256 pages/sec (Python 3.14), ~373 pps (Python 3.14t)
- Incremental: 15-50x speedup for single-page changes
- Parallel: 2-4x speedup on multi-core systems
- Fast mode: Reduced logging overhead, guaranteed parallel

Recent Optimizations (2025-10-20):
===================================
- Page list caching: 75% reduction in equality checks
- Parallel related posts: 7.5x faster (10K pages: 120s → 16s)
- Parallel taxonomy generation: Automatic for 100+ page sites
- Fast mode: Quiet output + guaranteed parallel processing

## Functions



### `test_build_performance`


```python
def test_build_performance(benchmark, scenario)
```



Benchmark the build process for different scenarios.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `scenario` | - | - | *No description provided.* |









### `temporary_scenario`


```python
def temporary_scenario(tmp_path)
```



Copy a scenario to a temporary location for testing incremental builds.
Cleans up after the test.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path` | - | - | *No description provided.* |









### `test_incremental_single_page_change`


```python
def test_incremental_single_page_change(benchmark, temporary_scenario)
```



Benchmark incremental build after modifying a single page.

This tests the most common developer workflow: edit one page, rebuild.
Expected speedup vs full build: 15-50x (validated at 1K-10K pages).
Recent optimizations (page list caching, parallel related posts) may affect baseline.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |









### `test_incremental_multi_page_change`


```python
def test_incremental_multi_page_change(benchmark, temporary_scenario)
```



Benchmark incremental build after modifying multiple pages (batch edit).

Tests if the system handles multiple changes efficiently.
Expected: Should be faster than full build but slower than single-page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |









### `test_incremental_config_change`


```python
def test_incremental_config_change(benchmark, temporary_scenario)
```



Benchmark behavior when config changes (should trigger full rebuild).

This validates that config change detection works correctly and triggers
a full rebuild when needed.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |









### `test_incremental_no_changes`


```python
def test_incremental_no_changes(benchmark, temporary_scenario)
```



Benchmark rebuild with no changes (cache validation test).

Expected: Very fast, just validates cache. Should be <1 second.
This helps identify cache overhead.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |









### `test_memory_usage_small_site`


```python
def test_memory_usage_small_site(tmp_path)
```



Profile memory usage for small site scenario.

Provides baseline for identifying memory-related bottlenecks.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path` | - | - | *No description provided.* |









### `test_memory_usage_large_site`


```python
def test_memory_usage_large_site(tmp_path)
```



Profile memory usage for large site scenario (100 pages).

Used to identify if scale degradation is memory-related.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path` | - | - | *No description provided.* |









### `test_incremental_memory_tracking`


```python
def test_incremental_memory_tracking(benchmark, temporary_scenario)
```



Benchmark and track memory during incremental builds.

Helps identify if memory accumulates during incremental builds.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |









### `fresh_scenario`


```python
def fresh_scenario(tmp_path)
```



Create a fresh copy of large_site for baseline full build testing.

This fixture creates a NEW copy each time, ensuring we measure
a true full build without any cache.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path` | - | - | *No description provided.* |









### `test_full_build_baseline`


```python
def test_full_build_baseline(benchmark, fresh_scenario)
```



Measure full build performance (no cache, no incremental).

This provides the baseline to compare against incremental builds.
Expected: This should be slower than incremental single-page changes (15-50x).
Recent performance: ~256 pps (Python 3.14), ~373 pps (Python 3.14t free-threading).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario` | - | - | *No description provided.* |









### `fresh_scenario_no_fast`


```python
def fresh_scenario_no_fast(tmp_path)
```



Create a fresh copy of large_site WITHOUT fast_mode for comparison testing.

This allows us to test --fast flag impact by comparing with/without fast mode.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path` | - | - | *No description provided.* |









### `test_fast_mode_cli_flag`


```python
def test_fast_mode_cli_flag(benchmark, fresh_scenario_no_fast)
```



Measure build performance with --fast CLI flag.

Fast mode enables quiet output and guarantees parallel processing.
Expected: Should be similar or slightly faster than default (reduced logging overhead).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario_no_fast` | - | - | *No description provided.* |









### `test_fast_mode_vs_default`


```python
def test_fast_mode_vs_default(benchmark, fresh_scenario_no_fast)
```



Compare fast mode (CLI flag) vs default build mode.

This validates that --fast provides measurable improvement through
reduced logging overhead and guaranteed parallel processing.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario_no_fast` | - | - | *No description provided.* |









### `test_memory_optimized_build`


```python
def test_memory_optimized_build(benchmark, fresh_scenario)
```



Measure build performance with --memory-optimized flag.

Memory-optimized mode uses streaming build for large sites (5K+ pages).
Expected: May be slightly slower than standard build due to batching overhead,
but uses constant memory instead of linear memory scaling.

Note: This is most beneficial for very large sites (10K+ pages).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario` | - | - | *No description provided.* |









### `test_parallel_vs_sequential`


```python
def test_parallel_vs_sequential(benchmark, fresh_scenario_no_fast)
```



Compare parallel vs sequential build performance.

Validates that parallel processing provides 2-4x speedup on multi-core systems.
This tests the core parallel optimization that benefits all builds.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario_no_fast` | - | - | *No description provided.* |









### `test_sequential_build`


```python
def test_sequential_build(benchmark, fresh_scenario_no_fast)
```



Measure sequential (non-parallel) build performance.

Provides baseline for comparing against parallel builds.
Expected: 2-4x slower than parallel on multi-core systems.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario_no_fast` | - | - | *No description provided.* |









### `test_incremental_with_fast_mode`


```python
def test_incremental_with_fast_mode(benchmark, temporary_scenario)
```



Benchmark incremental build with fast mode enabled.

Combines incremental build speedup with fast mode optimizations.
Expected: Should match or slightly improve on standard incremental builds.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `temporary_scenario` | - | - | *No description provided.* |



---
*Generated by Bengal autodoc from `benchmarks/test_build.py`*

