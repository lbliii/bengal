
---
title: "test_build"
type: "python-module"
source_file: "../bengal/benchmarks/test_build.py"
line_number: 1
description: "test_build package"
---

# test_build
**Type:** Module
**Source:** [View source](../bengal/benchmarks/test_build.py#L1)



**Navigation:**
[benchmarks](/api/benchmarks/) ›test_build

*No module description provided.*

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
Expected speedup vs full build: 15-50x (or reveals if incremental is broken)


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
Expected: This should be slower than incremental single-page changes (5-50x).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `fresh_scenario` | - | - | *No description provided.* |



---
*Generated by Bengal autodoc from `../bengal/benchmarks/test_build.py`*
