---
title: Performance
description: Benchmarks, optimization strategies, and performance characteristics
weight: 10
category: meta
tags:
- meta
- performance
- benchmarks
- optimization
- speed
- python-3.14
- incremental-builds
keywords:
- performance
- benchmarks
- optimization
- speed
- Python 3.14
- incremental builds
- parallel
---

# Performance

This page is a pointer to the benchmark suite and the main performance-critical subsystems.

## Benchmarks

- Benchmark suite: `benchmarks/`
- Entry points:
  - `benchmarks/test_build.py`
  - `benchmarks/test_cold_build_permutations.py`
  - `benchmarks/test_nav_tree_performance.py`

## Hot paths (where build time goes)

- **Markdown parsing + transforms**: `bengal/rendering/parsers/`, `bengal/rendering/pipeline/`
- **Template rendering**: `bengal/rendering/template_engine/`
- **Incremental build + caching**: `bengal/cache/`, `bengal/orchestration/`

## Related architecture pages

- [[docs/reference/architecture/rendering/rendering|Rendering Pipeline]]
- [[docs/reference/architecture/core/cache|Cache]]
- [[docs/reference/architecture/core/orchestration|Orchestration]]
