---
title: Performance Benchmarks
nav_title: Benchmarks
description: Measured build times for Bengal across different site sizes and configurations
weight: 15
tags:
- performance
- benchmarks
---

# Performance Benchmarks

Measured build times for Bengal using the benchmark suite in the repository.

---

## Test Methodology

| Parameter | Value |
|-----------|-------|
| **Machine** | Apple M2 MacBook Pro, 16 GB RAM |
| **OS** | macOS Sonoma 14.x |
| **Python** | 3.14.0 (free-threaded build) |
| **Measurement** | pytest-benchmark with statistical analysis |

### Test Content Characteristics

The benchmark suite uses **minimal test pages**:

- Simple Markdown with YAML frontmatter
- No directives (no `:::` blocks, no `{eval-rst}`)
- No syntax highlighting
- No table of contents generation
- Basic theme with navigation and footer

**Important**: Real-world sites with directives, syntax highlighting, and complex templates build slower than these benchmarks suggest. See [What Slows Builds Down](#what-slows-builds-down) for factors that affect your actual build times.

---

## Build Performance by Site Size

Cold build times (no cache) for the benchmark test content.

| Site Size | Build Time | Pages/Second |
|-----------|------------|--------------|
| 100 pages | ~0.4s | ~250 pps |
| 500 pages | ~1.8s | ~280 pps |
| 1,000 pages | ~3.5s | ~285 pps |
| 10,000 pages | ~35s | ~285 pps |

These numbers represent **best-case performance** with minimal content. Your results will vary based on content complexity.

---

## Incremental Build Performance

Time to rebuild when one file changes (warm cache).

| Change Type | Rebuild Time |
|-------------|--------------|
| Single page edit | 35-80 ms |
| Multiple pages (5) | 80-150 ms |
| Config change | Full rebuild |
| No changes | < 100 ms (cache validation) |

Incremental builds provide the largest real-world benefit. Even on large sites, editing a single page rebuilds in under 100 ms.

---

## Memory Usage

Peak RAM during builds with benchmark test content.

| Site Size | Peak Memory | Per-Page Overhead |
|-----------|-------------|-------------------|
| 100 pages | ~80 MB | ~800 KB |
| 1,000 pages | ~200 MB | ~200 KB |
| 10,000 pages | ~800 MB | ~80 KB |

Memory per page decreases at scale due to shared overhead (theme, templates, configuration).

---

## Parallel Processing

Build performance with different worker counts (1,000 pages).

| Workers | Build Time | Speedup |
|---------|------------|---------|
| 1 (serial) | ~9 s | 1.0x |
| 2 | ~5 s | 1.8x |
| 4 | ~3 s | 3.0x |
| 8 | ~2.5 s | 3.6x |

Diminishing returns above 4-8 workers due to I/O bottlenecks and coordination overhead.

---

## Free-Threaded Python Impact

Comparing Python 3.14 with and without the GIL (1,000 pages).

| Configuration | Build Time | Relative |
|---------------|------------|----------|
| Python 3.14 (GIL enabled) | ~3.5 s | 1.0x |
| Python 3.14 (PYTHON_GIL=0) | ~2.0 s | 1.75x |

```bash
# Enable free-threading
PYTHON_GIL=0 bengal build
```

### Kida Template Engine Advantage

Bengal uses [[ext:kida:|Kida]] for template rendering. Under concurrent workloads, Kida significantly outperforms Jinja2:

| Workers | Kida | Jinja2 | Speedup |
|---------|------|--------|---------|
| 1 | 3.31ms | 3.49ms | 1.05x |
| 4 | 1.53ms | 2.05ms | 1.34x |
| 8 | 2.06ms | 3.74ms | **1.81x** |

This advantage comes from [[ext:kida:docs/about/performance|Kida's thread-safe design]] (copy-on-write updates, local render state, GIL independence). Jinja2 shows *negative scaling* at high concurrency due to internal contention.

---

## What Slows Builds Down

Real-world sites build slower than benchmarks. Common factors:

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Syntax highlighting** | +30-50% | Fewer highlighted blocks, simpler languages |
| **Directives** (admonitions, tabs, cards) | +20-40% | Fewer directives = faster builds |
| **Table of contents** | +10-20% | Disable with `toc: false` in frontmatter |
| **Complex Jinja2 templates** | +10-30% | Simplify template logic |
| **Many taxonomies** | +5-15% | Limit to essential taxonomies |
| **Large code blocks** | +10-20% | Syntax highlighting overhead |
| **Related posts calculation** | +5-15% | Scales with page count squared |

### Real-World Example: Bengal Documentation Site

The Bengal documentation site itself (the site you're reading) provides a realistic benchmark:

```text
✓ Built 803 pages in 3.19 s (incremental+parallel) | 252.0 pages/sec  # warm caches
✓ Built 803 pages in 6.49 s (incremental+parallel) | 123.6 pages/sec  # cold caches
```

Even with warm caches, real documentation sites with directive-heavy content show variable performance. The docs use:

- Syntax-highlighted code blocks throughout
- Admonition directives (`:::note`, `:::warning`, etc.)
- Tab containers and card grids
- Table of contents on most pages
- Cross-references and backlinks

### Realistic Expectations

| Site Size | Benchmark (minimal) | Real Docs (directive-heavy) |
|-----------|---------------------|----------------------------|
| 100 pages | ~0.4 s / 250 pps | ~0.8 s / 125 pps |
| 500 pages | ~2 s / 250 pps | ~4 s / 125 pps |
| 800 pages | ~3 s / 265 pps | ~6.5 s / 124 pps |
| 1,000 pages | ~3.5 s / 285 pps | ~8 s / 125 pps |

Your results depend on content complexity. Directive-heavy documentation sites typically see 40-60% of benchmark speeds.

---

## Running Benchmarks

Run the benchmark suite yourself from the repository:

```bash
cd benchmarks

# Install dependencies
pip install -r requirements.txt

# Also install bengal in editable mode from project root
pip install -e ..

# Run all benchmarks
pytest -v

# Run specific benchmark
pytest test_build.py -k "incremental" -v

# Run cold build permutations
pytest test_cold_build_permutations.py -v

# Save and compare results
pytest test_build.py --benchmark-save=baseline
pytest test_build.py --benchmark-compare=baseline
```

### Available Benchmark Suites

| Suite | Purpose |
|-------|---------|
| `test_build.py` | Core build performance, incremental builds, fast mode |
| `test_cold_build_permutations.py` | Compare build modes across site sizes (100-1000 pages) |
| `test_10k_site.py` | Large site performance (10,000 pages), memory usage |
| `test_nav_tree_performance.py` | Navigation tree generation |
| `test_kida_vs_jinja.py` | Template engine concurrent performance comparison |
| `test_github_pages_optimization.py` | Optimal configuration for GitHub Actions (2-core, 7GB) |

---

## Performance Tips

1. **Use incremental builds during development**: `bengal build --incremental`
2. **Enable fast mode**: `bengal build --fast` (quiet output, max speed)
3. **Enable template caching**: Set `cache_templates = true` in config (default)
4. **Use free-threaded Python**: `PYTHON_GIL=0` with Python 3.14+
5. **Minimize directives**: Each directive adds parsing and rendering overhead

---

:::{seealso}
- [Architecture Overview](/docs/reference/architecture/) for how the build pipeline works
- [Configuration Reference](/docs/building/configuration/) for performance-related settings
:::
