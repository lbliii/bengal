---
title: "Parallel Processing for Maximum Speed"
date: 2025-10-03
template: doc.html
tags: ["performance", "configuration", "advanced"]
categories: ["Documentation", "Performance"]
type: "guide"
description: "Maximize build speed with Bengal's parallel processing across multiple CPU cores"
author: "Bengal Documentation Team"
---

# Parallel Processing

Bengal uses parallel processing to maximize build speed on multi-core systems, providing 2-4x speedup for medium to large sites.

## Quick Start

```toml
[build]
parallel = true           # Enable parallel processing (default: true)
max_workers = 4          # Number of worker threads (default: auto-detect)
```

That's it! Bengal automatically parallelizes all intensive operations.

## What Runs in Parallel?

### 1. Page Rendering

All pages render concurrently using Python's `ThreadPoolExecutor`:

```
Page 1 ─┐
Page 2 ─┼─→ Thread Pool ─→ Rendered HTML
Page 3 ─┤
Page N ─┘
```

**Performance**: Near-linear scaling up to CPU core count.

### 2. Asset Processing

Images, CSS, and JavaScript files process in parallel:

```
image1.jpg ─┐
style.css  ─┼─→ Asset Pipeline ─→ Optimized Assets
script.js  ─┤
image2.png ─┘
```

**Smart Threshold**: Only parallelizes when ≥5 assets (avoids thread overhead).

### 3. Post-Processing

Sitemap, RSS, and link validation run concurrently:

```
Sitemap ────┐
RSS Feed ───┼─→ Concurrent ─→ Complete
Link Check ─┘
```

**Performance**: 2x speedup for post-processing tasks.

## Performance Benchmarks

Real-world results from Bengal's performance tests:

### Asset Processing

| Assets | Sequential | Parallel | Speedup |
|--------|-----------|----------|---------|
| 10 assets | 0.089s | 0.089s | 1.0x (threshold) |
| 50 assets | 0.445s | 0.148s | **3.01x** |
| 100 assets | 0.890s | 0.211s | **4.21x** |

### Post-Processing

| Task | Sequential | Parallel | Speedup |
|------|-----------|----------|---------|
| Sitemap + RSS + Links | 0.243s | 0.121s | **2.01x** |

### Full Site Builds

| Site Size | Sequential | Parallel | Speedup |
|-----------|-----------|----------|---------|
| 10 pages | 0.324s | 0.289s | 1.1x |
| 50 pages | 1.234s | 0.789s | 1.6x |
| 100 pages | 2.456s | 1.658s | 1.5x |

**Note**: Speedup varies based on CPU cores and content complexity.

## How It Works

### Thread Pool Architecture

Bengal uses Python's `concurrent.futures.ThreadPoolExecutor`:

```python
# Simplified example
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(render_page, page) for page in pages]
    results = [future.result() for future in futures]
```

### Smart Thresholds

Bengal avoids thread overhead for tiny workloads:

| Operation | Threshold | Reasoning |
|-----------|-----------|-----------|
| Page rendering | Always parallel | Pages are I/O bound |
| Asset processing | ≥5 assets | Thread startup cost |
| Post-processing | ≥2 tasks | Natural parallelism |

### Thread Safety

All parallel operations are thread-safe:

✅ **File Operations**: Thread-safe read/write locks  
✅ **Template Rendering**: Thread-local Jinja2 environments  
✅ **Error Collection**: Synchronized error lists  
✅ **Cache Updates**: Atomic cache operations

## Configuration

### Enable/Disable

```toml
[build]
# Enable parallel processing (default)
parallel = true

# Disable for debugging or single-core systems
parallel = false
```

### Worker Count

```toml
[build]
# Auto-detect CPU cores (default)
max_workers = 0

# Explicit worker count
max_workers = 4

# Maximum workers (uses all cores)
max_workers = -1
```

**Recommendation**: Use auto-detect (0) for best results.

### CPU Core Detection

Bengal automatically detects your CPU configuration:

```bash
# Bengal will use optimal worker count
bengal build --parallel
```

Detection considers:
- Physical CPU cores
- Hyperthreading/SMT
- System load
- Available memory

## When to Use Parallel Processing

### ✅ Use Parallel For:

**Development Builds**
```bash
bengal build --parallel
# Fast iteration during development
```

**Production Builds**
```bash
bengal build --parallel
# Maximum speed for deployment
```

**Large Sites**
- 50+ pages
- 20+ assets
- Complex templates

**Multi-Core Systems**
- 4+ CPU cores
- Server environments
- Modern laptops

### ❌ Consider Sequential For:

**Debugging Template Issues**
```bash
bengal build --no-parallel
# Easier to trace errors
```

**Single-Core Environments**
- Minimal benefit
- May add overhead

**Very Small Sites**
- <10 pages
- <5 assets
- Minimal processing

**CI/CD with Limited Resources**
```bash
bengal build --parallel --max-workers=2
# Avoid overwhelming CI runners
```

## Combining with Incremental Builds

Maximum speed comes from combining parallel and incremental builds:

```bash
# Ultimate development speed
bengal build --incremental --parallel
```

**Results**:
- Incremental: Only rebuild changed files (18-42x)
- Parallel: Process multiple files concurrently (2-4x)
- **Combined**: Near-instant rebuilds for large sites

Example for a 100-page site with 1 file changed:
```
Full build: 1.688s
Incremental only: 0.047s (36x faster)
Incremental + Parallel: 0.015s (112x faster!)
```

## Best Practices

### Development Workflow

```bash
# Start dev server with parallel + incremental (default)
bengal serve

# Or explicit build
bengal build --incremental --parallel --verbose
```

### Production Deployment

```bash
# Clean build with maximum parallelism
bengal clean
bengal build --parallel --max-workers=-1
```

### CI/CD Pipeline

```toml
# .github/workflows/deploy.yml
[build]
parallel = true
max_workers = 2  # Conservative for CI runners
```

Or override via CLI:
```bash
bengal build --parallel --max-workers=2
```

## Troubleshooting

### Problem: Build errors with parallel enabled

**Symptom**: Random errors or inconsistent output

**Solution**: Try sequential build to isolate issue
```bash
bengal build --no-parallel --verbose
```

If sequential build works, report as a thread-safety bug.

### Problem: No speedup observed

**Possible causes**:
1. **Site too small** - <10 pages may not benefit
2. **Single-core system** - Check CPU with `lscpu` or `sysctl -n hw.ncpu`
3. **I/O bottleneck** - Slow disk may limit gains
4. **Template complexity** - CPU-bound templates benefit more

**Solution**: Profile with verbose mode
```bash
bengal build --parallel --verbose --profile
```

### Problem: High memory usage

**Symptom**: Build crashes or system slows down

**Solution**: Reduce worker count
```toml
[build]
max_workers = 2  # Lower than CPU count
```

### Problem: Inconsistent output

**Symptom**: Different results between parallel and sequential

**Solution**: Report as a bug! Output should be identical.

## Technical Deep Dive

### GIL Considerations

Python's Global Interpreter Lock (GIL) limits CPU parallelism, but Bengal benefits because:

1. **I/O Bound Operations**: File reads/writes release GIL
2. **Template Rendering**: Jinja2 operations release GIL
3. **Markdown Parsing**: Native C extensions release GIL

Result: Near-linear scaling despite GIL.

### Memory Usage

Parallel processing increases memory usage:

| Workers | Memory Multiplier |
|---------|------------------|
| 1 (sequential) | 1.0x (baseline) |
| 2 workers | 1.3x |
| 4 workers | 1.6x |
| 8 workers | 2.0x |

For very large sites (1000+ pages), monitor memory usage.

### Task Scheduling

Bengal uses work-stealing for optimal load balancing:

```
Worker 1: [Page 1] [Page 2] [Page 3] ...
Worker 2: [Page 4] [Page 5] [Page 6] ...
Worker 3: [Page 7] [Page 8] [Page 9] ...
Worker 4: [Page 10] ...
          ↓ (steal work)
          [Page 11]
```

Fast-completing workers steal tasks from busy workers.

## Advanced Configuration

### Custom Thread Pool

For advanced users, customize thread pool behavior:

```python
# Future feature - custom thread pool configuration
[build.parallel]
executor = "thread"  # or "process" for CPU-bound work
max_workers = 4
thread_name_prefix = "Bengal-Worker"
```

### Profiling Parallel Performance

```bash
# Enable detailed profiling (future feature)
bengal build --parallel --profile --verbose
```

Expected output:
```
⚡ Parallel Processing Stats:
Workers: 4
Tasks: 100 pages, 50 assets, 3 post-process
Duration: 1.234s
Per-worker: 0.308s average
Speedup: 3.2x vs sequential
```

## Comparison with Other SSGs

| SSG | Parallel Support | Configuration | Performance |
|-----|-----------------|---------------|-------------|
| Bengal | ✅ Full | Automatic | 2-4x speedup |
| Hugo | ✅ Native Go | Automatic | Very fast |
| Jekyll | ❌ No | N/A | Slow |
| Gatsby | ✅ Full | Automatic | Fast |
| Eleventy | ⚠️ Limited | Manual | Moderate |

## Learn More

- [Incremental Builds](/docs/incremental-builds/) - Combine for maximum speed
- [Performance Optimization](/guides/performance-optimization/) - Additional tips
- [Configuration Reference](/docs/configuration-reference/) - All build options

## Feedback

Questions or issues with parallel processing? [Open an issue](https://github.com/bengal-ssg/bengal/issues).

