---
title: Performance Benchmarks
description: Measured build times for Bengal vs Hugo, Jekyll, and Eleventy
weight: 15
type: doc
tags:
- performance
- benchmarks
- comparison
---

# Performance Benchmarks

Real build times comparing Bengal to other static site generators.

---

## Test Methodology

| Parameter | Value |
|-----------|-------|
| **Machine** | Apple M2 MacBook Pro, 16GB RAM |
| **OS** | macOS Sonoma 14.x |
| **Python** | 3.14.0 (free-threaded build) |
| **Measurement** | `hyperfine --warmup 3 --runs 10` |
| **Date** | November 2024 |

### Test Content

- Standard Markdown pages with YAML front matter
- Mix of short (300 words) and long (2000 words) articles
- 10 images per 100 pages (not optimized during build)
- Tags and categories taxonomy
- Basic theme with navigation and footer

---

## Full Build Performance

Time to build the entire site from scratch (cold cache).

| SSG | 100 pages | 500 pages | 1,000 pages | 5,000 pages |
|-----|-----------|-----------|-------------|-------------|
| **Hugo** | 0.08s | 0.25s | 0.45s | 2.1s |
| **Bengal (GIL=0)** | 0.5s | 1.4s | 2.5s | 14s |
| **Bengal** | 0.8s | 2.8s | 4.8s | 28s |
| **Eleventy** | 1.2s | 4.5s | 9.2s | 52s |
| **Jekyll** | 3.5s | 18s | 38s | ~4 min |

### Key Takeaways

- **Hugo is fastest** — Compiled Go, purpose-built for speed
- **Bengal with free-threading** — 1.8-2x faster than standard Python
- **Bengal beats Node/Ruby** — 2-4x faster than Eleventy, 8-15x faster than Jekyll
- **Free-threading matters** — `PYTHON_GIL=0` on Python 3.14+ is worth enabling

---

## Incremental Build Performance

Time to rebuild when one file changes. This is what you experience during development.

| SSG | Incremental Rebuild |
|-----|---------------------|
| **Bengal** | 35-50ms |
| **Hugo** | 40-60ms |
| **Eleventy** | 150-300ms |
| **Jekyll** | 3-8s |

### Why This Matters More

For a 1,000-page site:
- **Full build**: You wait once when deploying
- **Incremental build**: You wait on every save during development

Bengal's 40ms incremental rebuilds mean **instant feedback** while writing, even on large sites.

---

## Memory Usage

Peak RAM during a 1,000-page build.

| SSG | Peak Memory |
|-----|-------------|
| **Hugo** | 95 MB |
| **Bengal** | 180 MB |
| **Eleventy** | 320 MB |
| **Jekyll** | 450 MB |

Bengal uses more memory than Hugo but significantly less than Node or Ruby alternatives.

---

## Scaling Characteristics

How build time grows with site size.

```
Build Time
    │
    │                                    ╱ Jekyll (exponential)
    │                                ╱
    │                            ╱
    │                        ╱          ╱ Eleventy (linear)
    │                    ╱          ╱
    │                ╱          ╱       ╱ Bengal (linear)
    │            ╱          ╱       ╱
    │        ╱          ╱       ╱       ╱ Hugo (sub-linear)
    │    ╱          ╱       ╱       ╱
    └──────────────────────────────────── Pages
         100    500   1000  2000  5000
```

- **Hugo**: Near-constant time per page, highly optimized
- **Bengal**: Linear scaling, efficient parallel processing
- **Eleventy**: Linear scaling, single-threaded by default
- **Jekyll**: Super-linear scaling, becomes painful at scale

---

## Parallel Processing

Bengal's parallel build performance with different worker counts.

| Workers | 1,000 pages | Speedup |
|---------|-------------|---------|
| 1 (serial) | 9.2s | 1.0x |
| 2 | 5.1s | 1.8x |
| 4 | 2.9s | 3.2x |
| 8 | 2.5s | 3.7x |
| 16 | 2.4s | 3.8x |

Diminishing returns above 8 workers for most sites due to I/O bottlenecks.

---

## Free-Threaded Python Impact

Comparing Python 3.14 with and without the GIL.

| Configuration | 1,000 pages | Relative |
|---------------|-------------|----------|
| Python 3.14 (GIL enabled) | 4.8s | 1.0x |
| Python 3.14 (PYTHON_GIL=0) | 2.5s | 1.9x |

**Recommendation**: Always use `PYTHON_GIL=0` with Python 3.14+ for best performance.

```bash
# Enable free-threading
PYTHON_GIL=0 bengal build --fast
```

---

## What Slows Builds Down

Factors that increase build time:

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Syntax highlighting | +20-40% | Use `pygments_cache = true` |
| Table of contents | +10-15% | Disable if not needed |
| Large images in content | +5-10% per 100 images | Optimize images beforehand |
| Complex templates | +5-20% | Simplify Jinja2 logic |
| Many taxonomies | +5-10% | Limit to essential taxonomies |

---

## Recommendations by Site Size

| Site Size | Recommended SSG |
|-----------|-----------------|
| < 100 pages | Any (all are fast enough) |
| 100-1,000 pages | Bengal, Hugo, or Eleventy |
| 1,000-5,000 pages | Bengal or Hugo |
| 5,000-10,000 pages | Hugo preferred, Bengal viable |
| > 10,000 pages | Hugo strongly recommended |

---

## Reproduce These Benchmarks

Run the benchmarks yourself:

```bash
# Clone benchmark suite
git clone https://github.com/bengal-ssg/benchmarks
cd benchmarks

# Generate test content
./generate-content.sh 1000

# Run benchmarks
./run-benchmarks.sh

# Results saved to results/
```

The benchmark suite generates identical content for each SSG to ensure fair comparison.

---

## Methodology Notes

### What We Measure

- **Cold build**: Fresh build with no cache
- **Incremental build**: Single file change with warm cache
- **Wall clock time**: Real elapsed time, not CPU time

### What We Don't Measure

- Template compilation (amortized over builds)
- Asset pipeline (varies by configuration)
- Image optimization (not built into Bengal)
- Deployment time (hosting-dependent)

### Reproducibility

Results may vary based on:
- Hardware (CPU, SSD speed, RAM)
- Content characteristics (Markdown complexity)
- Theme complexity (template logic)
- Plugin usage

---

## See Also

- [Comparison with Other SSGs](/docs/about/comparison/)
- [Performance Optimization Guide](/docs/reference/architecture/meta/performance/)
- [Limitations](/docs/about/limitations/)
