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

:::{warning} Workload label — render-light best case, not the committed baseline
The table below is a **render-light, minimal-content best case** (no taxonomy, no
directives, no syntax highlighting). It is **not** Bengal's committed, reproducible
baseline. The committed baseline (`benchmarks/baselines/`, `blog` archetype with
taxonomy, free-threaded 3.14t, median of 3) measures **~18–20 pages/s end-to-end** —
e.g. 1,000 pages in **56.3 s** (`PYTHON_GIL=0`). Treat the numbers below as an
upper bound for trivial sites, and see [the committed free-threading table](#free-threaded-python-impact)
and `benchmarks/baselines/SPEEDUP.md` for what reproduces.
:::

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

:::{note} No committed memory baseline yet
The figures below are illustrative; there is **no committed peak-RSS baseline**
(`benchmarks/baselines/peak_rss.json` is not yet generated). Treat them as rough
guidance until a measured baseline lands.
:::

| Site Size | Peak Memory | Per-Page Overhead |
|-----------|-------------|-------------------|
| 100 pages | ~80 MB | ~800 KB |
| 1,000 pages | ~200 MB | ~200 KB |
| 10,000 pages | ~800 MB | ~80 KB |

Memory per page decreases at scale due to shared overhead (theme, templates, configuration).

---

## Parallel Processing

Build performance with different worker counts (1,000 pages).

:::{warning} Workload label — render-light, illustrative scaling
These worker-scaling figures are **render-light** (the same minimal-content
workload as the table above) and are **illustrative of the scaling shape**, not
a committed baseline. For Bengal's committed, reproducible parallel/serial
numbers, see [Free-Threaded Python Impact](#free-threaded-python-impact) below
and `benchmarks/baselines/SPEEDUP.md` — e.g. 1,000 pages (`blog` archetype) goes
from **109.2 s** (`PYTHON_GIL=1`) to **56.3 s** (`PYTHON_GIL=0`), a 1.94x
free-threading speedup.
:::

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

:::{note} Committed baseline
The render-light numbers above predate the committed baseline. On the taxonomy-heavy
`blog` archetype (`benchmarks/baselines/gil_speedup.json`, median of 3), free-threading
measures **1.24x at 100 pages and 1.94x at 1,000 pages** (56.3 s with `PYTHON_GIL=0`
vs 109.2 s with the GIL re-enabled). The speedup grows with site size because rendering
— the dominant phase — scales across threads.
:::

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

:::{warning} Workload label — warm-cache, content-specific spot run (not the committed baseline)
The numbers below are a **warm-cache, incremental+parallel spot run** of this
specific docs site on one machine — not a committed, reproducible baseline.
They are *not* comparable to the committed end-to-end baseline of **~18–20
pages/s** (`benchmarks/baselines/`, `blog` archetype with taxonomy, free-threaded
3.14t, median of 3; see [Free-Threaded Python Impact](#free-threaded-python-impact)).
The high pps reflects incremental builds skipping unchanged pages plus a warm
render cache, not raw end-to-end throughput. Treat it as illustrative of
incremental-build behavior on a content-specific site.
:::

The Bengal documentation site itself (the site you're reading) shows how
incremental builds behave on directive-heavy content:

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

:::{warning} Workload label — render-light upper bound vs. committed baseline
The "Benchmark (minimal)" column is the **render-light upper bound** from the
[Build Performance by Site Size](#build-performance-by-site-size) table (no
taxonomy, no directives, no syntax highlighting). It is **not** the committed
end-to-end baseline, which measures **~18–20 pages/s** for the `blog` archetype
with taxonomy (`benchmarks/baselines/`, free-threaded 3.14t, median of 3 —
e.g. 1,000 pages in **56.3 s**). The "Real Docs" column is an illustrative
warm-cache estimate for directive-heavy content; treat both columns as upper
bounds, not the reproducible baseline.
:::

| Site Size | Benchmark (minimal, render-light) | Real Docs (directive-heavy, warm cache) |
|-----------|-----------------------------------|-----------------------------------------|
| 100 pages | ~0.4 s / 250 pps | ~0.8 s / 125 pps |
| 500 pages | ~2 s / 250 pps | ~4 s / 125 pps |
| 800 pages | ~3 s / 265 pps | ~6.5 s / 124 pps |
| 1,000 pages | ~3.5 s / 285 pps | ~8 s / 125 pps |

These are render-light/warm-cache upper bounds, not the committed ~18–20 pages/s
end-to-end baseline. Your results depend on content complexity; directive-heavy
documentation sites typically see 40-60% of these render-light figures.

---

## Running Benchmarks

Run the benchmark suite yourself from the repository:

```bash
cd benchmarks

# Install dependencies
pip install -r requirements.txt

# Also install bengal in editable mode from project root
pip install -e ..

# Run all benchmarks (from project root)
poe benchmark

# Or with pytest directly
pytest benchmarks/ tests/performance/ -v --benchmark-only

# Run specific benchmark
pytest tests/performance/ -k "incremental" -v --benchmark-only

# Save and compare results
poe benchmark-save
poe benchmark-compare
```

### Available Benchmark Suites

| Suite | Purpose |
|-------|---------|
| `benchmark_full_build.py` | Core build performance, phase breakdown |
| `benchmark_incremental.py` | Incremental build speedup |
| `benchmark_ssg_comparison.py` | CSS-Tricks methodology, cross-SSG comparison |
| `benchmark_content_complexity.py` | Directives, code blocks, taxonomy impact |
| `benchmark_phase_breakdown.py` | Total build time by site size (phase breakdown in benchmark_full_build) |
| `benchmark_render.py` | HtmlRenderer performance |
| `benchmark_github_pages_optimization.py` | Optimal configuration for GitHub Actions (2-core, 7GB) |

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
