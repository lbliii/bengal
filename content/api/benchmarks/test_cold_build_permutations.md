
---
title: "test_cold_build_permutations"
type: "python-module"
source_file: "benchmarks/test_cold_build_permutations.py"
line_number: 1
description: "Comprehensive cold build permutation benchmarks. Compares all build mode combinations across multiple site sizes (100, 500, 1000 pages). Tests cold builds (no cache) to measure true build performance...."
---

# test_cold_build_permutations
**Type:** Module
**Source:** [View source](benchmarks/test_cold_build_permutations.py#L1)



**Navigation:**
[benchmarks](/api/benchmarks/) ›test_cold_build_permutations

Comprehensive cold build permutation benchmarks.

Compares all build mode combinations across multiple site sizes (100, 500, 1000 pages).
Tests cold builds (no cache) to measure true build performance.

Build Modes Tested:
===================
1. Standard (default parallel)
2. Fast mode (--fast)
3. Memory-optimized (--memory-optimized)
4. Sequential (--no-parallel)
5. Fast + Memory-optimized (--fast --memory-optimized)

Site Sizes:
===========
- 100 pages: Small-medium site
- 500 pages: Medium-large site
- 1000 pages: Large site

Expected Insights:
==================
- Fast mode impact (logging overhead reduction)
- Memory-optimized tradeoffs (speed vs memory)
- Parallel vs sequential speedup (2-4x expected)
- Scaling characteristics across site sizes

## Functions



### `generate_test_site`


```python
def generate_test_site(num_pages: int, tmp_path: Path) -> Path
```



Generate a test site with specified number of pages.

Creates realistic content with tags, frontmatter, and markdown content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `num_pages` | `int` | - | *No description provided.* |
| `tmp_path` | `Path` | - | *No description provided.* |







**Returns**


`Path`




### `site_100_pages`


```python
def site_100_pages(tmp_path_factory)
```



Generate 100-page test site.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path_factory` | - | - | *No description provided.* |









### `site_500_pages`


```python
def site_500_pages(tmp_path_factory)
```



Generate 500-page test site.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path_factory` | - | - | *No description provided.* |









### `site_1000_pages`


```python
def site_1000_pages(tmp_path_factory)
```



Generate 1000-page test site.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tmp_path_factory` | - | - | *No description provided.* |









### `test_standard_build`


```python
def test_standard_build(benchmark, request, site_fixture, page_count)
```



Standard build (default parallel, no flags).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `request` | - | - | *No description provided.* |
| `site_fixture` | - | - | *No description provided.* |
| `page_count` | - | - | *No description provided.* |









### `test_fast_mode`


```python
def test_fast_mode(benchmark, request, site_fixture, page_count)
```



Fast mode build (--fast: quiet output + guaranteed parallel).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `request` | - | - | *No description provided.* |
| `site_fixture` | - | - | *No description provided.* |
| `page_count` | - | - | *No description provided.* |









### `test_memory_optimized`


```python
def test_memory_optimized(benchmark, request, site_fixture, page_count)
```



Memory-optimized build (--memory-optimized: streaming for large sites).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `request` | - | - | *No description provided.* |
| `site_fixture` | - | - | *No description provided.* |
| `page_count` | - | - | *No description provided.* |









### `test_sequential_build`


```python
def test_sequential_build(benchmark, request, site_fixture, page_count)
```



Sequential build (--no-parallel: baseline for parallel speedup).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `request` | - | - | *No description provided.* |
| `site_fixture` | - | - | *No description provided.* |
| `page_count` | - | - | *No description provided.* |









### `test_fast_memory_optimized`


```python
def test_fast_memory_optimized(benchmark, request, site_fixture, page_count)
```



Fast mode + Memory-optimized (--fast --memory-optimized: for large sites).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `benchmark` | - | - | *No description provided.* |
| `request` | - | - | *No description provided.* |
| `site_fixture` | - | - | *No description provided.* |
| `page_count` | - | - | *No description provided.* |



---
*Generated by Bengal autodoc from `benchmarks/test_cold_build_permutations.py`*

