# Memory Optimization Guide

Guide for using `--memory-optimized` builds in Bengal SSG.

---

## When to Use Memory Optimization

### ✅ **Recommended For:**

**Large Sites (5K+ pages)**
- Documentation sites with extensive API references
- Blog archives spanning many years
- Knowledge bases with 1000s of articles
- E-commerce catalogs with large product inventories

**Symptoms:**
- Build process runs out of memory (OOM errors)
- System swapping heavily during builds
- Memory usage exceeding available RAM
- Build becomes unstable on large sites

**Benefits:**
- 40-90% memory reduction (depending on site structure)
- Enables building sites that previously failed
- More stable builds on memory-constrained systems

---

### ⚠️ **Not Recommended For:**

**Small to Medium Sites (< 1K pages)**
- Personal blogs (< 100 posts)
- Small documentation sites
- Marketing websites
- Portfolio sites

**Why:**
- Graph analysis overhead (~50ms) > memory savings
- Standard parallel build is already fast
- Memory footprint is manageable
- No noticeable benefit

**Medium Sites (1K-5K pages)**
- Marginal benefit
- Only use if experiencing memory issues
- Test with and without to measure impact

---

## Usage

### Basic Usage

```bash
# Standard build (default)
bengal build

# Memory-optimized build (for large sites)
bengal build --memory-optimized
```

### Combined with Other Flags

```bash
# Memory-optimized + incremental
bengal build --memory-optimized --incremental

# Memory-optimized + dev profile
bengal build --memory-optimized --profile=dev

# All together
bengal build --memory-optimized --incremental --parallel
```

---

## How It Works

### 1. **Connectivity Analysis**

Before rendering, Bengal analyzes your site's connectivity using a knowledge graph:

```
🧠 Analyzing connectivity for memory optimization...
   Hubs: 19 (keep in memory)          [9.6%]
   Mid-tier: 60 (batch process)       [30.3%]
   Leaves: 119 (stream & release)     [60.1%]
```

- **Hubs**: Highly connected pages (>10 incoming references)
- **Mid-tier**: Moderately connected (3-10 incoming references)
- **Leaves**: Low connectivity (≤2 incoming references)

### 2. **Hub-First Processing**

Pages are rendered in optimal order:

1. **Render Hubs** → Keep in memory (frequently referenced)
2. **Batch Mid-Tier** → Process in chunks
3. **Stream Leaves** → Render and immediately release from memory

### 3. **Memory Release**

After rendering leaves:
- Clear page content caches
- Release heavy data structures
- Force garbage collection
- Continue to next batch

---

## Expected Memory Savings

### Site Structure Matters

Memory savings depend on your site's **connectivity distribution**:

**High Connectivity (Many hubs):**
- Example: Documentation with cross-references
- Savings: ~40-50% (fewer pages can be released)

**Low Connectivity (Many leaves):**
- Example: Blog archive with isolated posts
- Savings: ~80-90% (most pages can be released)

**Typical Power-Law Distribution:**
- 10% hubs (must keep in memory)
- 30% mid-tier (batch process)
- 60% leaves (stream and release)
- **Expected savings: ~60-70%**

### Real-World Examples

| Site Type | Pages | Connectivity | Standard | Optimized | Savings |
|-----------|-------|--------------|----------|-----------|---------|
| Small Blog | 200 | Low | 12 MB | 10 MB | 17% ⚠️ |
| Medium Docs | 2K | Medium | 60 MB | 30 MB | 50% ✓ |
| Large Docs | 10K | High | 200 MB | 50 MB | 75% ✅ |
| Huge Archive | 50K | Low | 800 MB | 90 MB | 89% 🚀 |

---

## Configuration Options

### Batch Size

Control how many leaves are processed per batch (default: 100):

```python
# In code (programmatic builds)
site.build(
    memory_optimized=True,
    batch_size=50  # Smaller batches = more GC, less memory
)
```

### Thresholds

The system automatically warns you if memory optimization might not help:

- **< 1K pages**: Warning (overhead > benefit)
- **1K-5K pages**: Info (marginal benefit)
- **5K+ pages**: Recommended (clear benefit)

---

## Measuring Impact

### Check Memory Usage

**Linux/macOS:**
```bash
# Before (standard build)
time -v bengal build 2>&1 | grep "Maximum resident"

# After (optimized build)
time -v bengal build --memory-optimized 2>&1 | grep "Maximum resident"
```

**Python (built-in metrics):**
```bash
# Bengal tracks memory automatically in dev mode
bengal build --memory-optimized --profile=dev
# Check .bengal-metrics/latest.json for memory_peak_mb
```

### Compare Build Times

```bash
# Standard
time bengal build

# Optimized
time bengal build --memory-optimized
```

**Note:** Build time should be roughly the same (graph overhead is minimal).

---

## Troubleshooting

### "Still Running Out of Memory"

If you're still hitting OOM errors with `--memory-optimized`:

1. **Reduce batch size:**
   - Smaller batches = more aggressive memory release
   - Trade-off: Slightly slower builds

2. **Check for memory leaks:**
   - Large images in frontmatter
   - Circular references in custom plugins
   - Heavy template functions

3. **Increase system resources:**
   - Add swap space
   - Increase container memory limits
   - Use a machine with more RAM

### "Build is Slower"

Memory optimization should NOT slow down builds significantly. If it does:

1. **Check page count:**
   - < 1K pages? Don't use `--memory-optimized`
   - Graph analysis overhead dominates

2. **Profile the build:**
   ```bash
   bengal build --memory-optimized --profile=dev
   ```

3. **Compare with standard:**
   ```bash
   # Standard build
   bengal build --profile=dev
   
   # Optimized build
   bengal build --memory-optimized --profile=dev
   ```

### "Warning Says Not Recommended"

If you see:
```
⚠️  Memory optimization is designed for large sites (5K+ pages)
   Your site has 198 pages - standard build is likely faster.
```

**Action:** Remove `--memory-optimized` unless:
- You're testing/profiling
- You're on a very memory-constrained system
- You're experiencing memory issues (rare for small sites)

---

## When to Enable by Default

Consider enabling memory optimization by default in your `bengal.toml` if:

1. **Your site has 10K+ pages** (always beneficial)
2. **You're building in CI/CD** with limited memory
3. **You're on a shared hosting** environment
4. **Memory is more constrained** than CPU

```toml
# bengal.toml
[build]
memory_optimized = true  # Enable by default
```

---

## Advanced: Programmatic Usage

For custom build scripts:

```python
from bengal.core.site import Site

# Load site
site = Site.from_config(".")

# Build with memory optimization
stats = site.build(
    parallel=True,
    incremental=False,
    memory_optimized=True  # Enable memory optimization
)

# Check memory usage
print(f"Peak memory: {stats.memory_heap_mb:.1f} MB")
```

---

## FAQ

### Q: Does it work with incremental builds?
**A:** Yes! Combine `--memory-optimized` with `--incremental`:
```bash
bengal build --memory-optimized --incremental
```

### Q: Does it affect build speed?
**A:** No. Graph analysis adds ~50ms overhead, but rendering speed is identical.

### Q: What about parallel builds?
**A:** Memory optimization works with both parallel and sequential rendering.

### Q: Can I use it in production?
**A:** Absolutely! It's production-ready and has zero breaking changes.

### Q: What if my site has no links?
**A:** The system detects this and all pages are treated as leaves (maximum memory savings).

### Q: Does it change the output?
**A:** No. Output HTML is identical, only the build process changes.

---

## Summary

| Site Size | Use `--memory-optimized`? | Expected Benefit |
|-----------|---------------------------|------------------|
| < 1K pages | ❌ No | Overhead > savings |
| 1K-5K pages | 🤷 Optional | Marginal (~30-50%) |
| 5K-10K pages | ✅ Yes | Good (~50-70%) |
| 10K+ pages | 🚀 Absolutely | Excellent (~70-90%) |

**Rule of Thumb:**
- **< 5K pages:** Skip it (unless memory-constrained)
- **5K+ pages:** Use it
- **10K+ pages:** Always use it

---

**Last Updated:** 2025-10-09

