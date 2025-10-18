# What is "Blazing Fast" for Python?

## TL;DR

**For Python SSGs**: 200-300 pages/sec would be genuinely impressive  
**Bengal's current**: ~100-120 pages/sec is **competitive, not exceptional**

---

## Python SSG Performance Landscape

### Current State (2025)

| SSG | Language | Pages/sec | Notes |
|-----|----------|-----------|-------|
| **Hugo** | Go | ~1000+ | The gold standard, compiled |
| **Zola** | Rust | ~800 | Compiled, very fast |
| **Eleventy** | Node.js | ~200 | JavaScript runtime advantage |
| **Pelican** | Python | ~80-100 | Pure Python, similar to Bengal |
| **Bengal** | Python | ~100-120 | **Current performance** |
| **Jekyll** | Ruby | ~50 | Single-threaded, older design |
| **Sphinx** | Python | ~30-50 | Not optimized for speed (docs-focused) |

### What Would Be "Blazing Fast" for Python?

**Target: 200-300 pages/sec** would be genuinely exceptional

**Why this target?**
- 2-3x faster than current Python SSGs
- Approaching JavaScript runtime speeds (Eleventy)
- Still 3-5x slower than compiled languages (acceptable Python tax)
- Would require significant engineering effort

---

## How to Achieve 200-300 pps in Python

### 1. ✅ What Bengal Already Does (100-120 pps)

**Already Optimized**:
- ✅ Parallel processing (joblib)
- ✅ Incremental builds with caching
- ✅ Fast Markdown parser (mistune)
- ✅ Jinja2 template caching
- ✅ Page subset caching (just added)

**Current Bottlenecks**:
- 🐍 Python interpreter overhead (~40% of time)
- 📝 Markdown parsing (~40% of time)
- 💾 File I/O (~10% of time)
- 🔍 Object creation/manipulation (~10% of time)

---

### 2. ⚠️ What Could Get to 150-180 pps (Medium Effort)

**Async I/O Throughout** (~20-30% faster I/O)
```python
import asyncio
import aiofiles

async def read_pages_async(pages):
    tasks = [aiofiles.open(p.source_path).read() for p in pages]
    return await asyncio.gather(*tasks)
```
**Effort**: 1-2 weeks (refactor entire pipeline)  
**Impact**: +10-15 pps

**C Extension for Markdown** (if available)
```python
# Use markdown-it-c or similar
import markdown_it_c  # Hypothetical

# Would need to maintain AST extraction
```
**Effort**: 2-3 weeks (integration + testing)  
**Impact**: +20-30 pps (if AST extraction works)

**Object Pooling / Reduced Allocations**
```python
# Reuse Page objects instead of creating new ones
page_pool = PagePool(size=1000)
page = page_pool.acquire()
# ... use page
page_pool.release(page)
```
**Effort**: 1-2 weeks  
**Impact**: +5-10 pps

**Combined Impact**: ~150-180 pps (1.5x improvement)

---

### 3. 🔥 What Could Get to 200-300 pps (High Effort)

**Cython Critical Paths** (compile hot paths)
```python
# cython: boundscheck=False, wraparound=False
cdef class FastPage:
    cdef public str title
    cdef public str content
    # ... compile to C
```
**Effort**: 1-2 months (learn Cython, port critical code)  
**Impact**: +30-50 pps (2-3x faster for compiled sections)

**PyPy Runtime** (JIT compilation)
```bash
# Run Bengal with PyPy instead of CPython
pypy3 -m bengal build
```
**Effort**: 1-2 weeks (compatibility testing)  
**Impact**: +40-60 pps (2-5x faster for pure Python code)  
**Risk**: May not support all dependencies

**Memory-Mapped I/O + Zero-Copy Parsing**
```python
import mmap

def parse_mmap(path):
    with open(path, 'r+b') as f:
        mm = mmap.mmap(f.fileno(), 0)
        # Parse directly from memory-mapped region
        return parse_markdown_from_bytes(mm)
```
**Effort**: 2-3 weeks  
**Impact**: +10-20 pps (especially for large files)

**Rust Extensions for Critical Paths** (PyO3)
```rust
// bengal-core/src/lib.rs
use pyo3::prelude::*;

#[pyfunction]
fn parse_markdown_fast(content: &str) -> PyResult<String> {
    // Rust-powered parsing
    Ok(parsed_html)
}
```
**Effort**: 2-3 months (learn Rust + PyO3, rewrite core)  
**Impact**: +50-100 pps (compiled speed for hot paths)

**Combined Impact**: ~200-300 pps (2-3x improvement)

---

## Real-World Examples

### Pelican (Python SSG)

**Performance**: ~80-100 pps  
**Similar to Bengal**, uses:
- Jinja2 templates
- Python Markdown parser
- Basic caching

**Not considered "blazing fast"** - it's standard Python performance.

---

### Nikola (Python SSG)

**Performance**: ~100-150 pps  
**Slightly faster** due to:
- doit task engine (incremental builds)
- Plugin architecture (optional features)
- More aggressive caching

**Still not "blazing fast"** - good but not exceptional.

---

### MkDocs (Python)

**Performance**: ~50-80 pps  
**Slower** because:
- Theme complexity
- Live reload overhead
- Less optimization focus

**Trade-off**: Better DX (developer experience) over raw speed.

---

## The Honest Assessment

### Bengal Today: ~100-120 pps

**Rating**: ⭐⭐⭐ **Competitive**
- ✅ Better than Pelican (~80-100 pps)
- ✅ On par with Nikola (~100-150 pps)
- ✅ Much better than Sphinx (~30-50 pps)
- ❌ Not exceptional for Python
- ❌ Not "blazing fast"

**Verdict**: **"Fast enough for Python"** or **"Competitive Python performance"**

---

### What Would Be "Blazing Fast"? 200-300 pps

**Rating**: ⭐⭐⭐⭐⭐ **Exceptional**
- ✅ 2-3x faster than typical Python SSGs
- ✅ Approaching JavaScript runtime speeds
- ✅ Best-in-class for Python
- ✅ Could legitimately claim "blazing fast **for Python**"

**How to get there**:
1. Cython for hot paths (1-2 months)
2. PyPy runtime support (1-2 weeks)
3. Async I/O throughout (1-2 weeks)
4. Rust extensions (optional, 2-3 months)

**Total effort**: 3-6 months of dedicated performance engineering

---

## Recommended Marketing Language

### ❌ Don't Say (Without Data)

- "Blazing fast" (unqualified)
- "Faster than Hugo" (it's not)
- "Sub-second builds" (depends on scale)
- "Handles any site size" (memory-bound at 10K+)

---

### ✅ Do Say (With Data)

**Current State (100-120 pps)**:

> **"Competitive Python performance"**  
> Bengal builds at ~100-120 pages/sec, on par with Pelican and Nikola.  
> Not the fastest (Hugo: ~1000 pps), but **fast enough for Python** and  
> most documentation sites (10K pages in ~100 seconds).

**If You Reach 200-300 pps**:

> **"Blazing fast for Python"**  
> Bengal achieves 200-300 pages/sec through Cython compilation and  
> aggressive optimization, making it **the fastest Python SSG** available.  
> Approaches JavaScript runtime speeds while maintaining Python's DX.

**Honest Hybrid**:

> **"Fast enough, Python native"**  
> Bengal won't beat Hugo (Go), but builds 10K pages in ~100 seconds with  
> 15-50x faster incremental rebuilds. Optimized for **Python developers**  
> who value debuggability and AST-based autodoc over raw speed.

---

## The Bottom Line

### Current Bengal: 100-120 pps

**Is this "blazing fast"?**
- ❌ No, not objectively
- ❌ No, not even for Python
- ✅ Yes, "competitive" or "fast enough"
- ✅ Yes, "well-optimized Python"

### Target for "Blazing Fast" Label: 200-300 pps

**Effort Required**:
- 3-6 months dedicated performance work
- Cython/PyPy/Rust integration
- Async I/O refactor
- Significant testing

**Is It Worth It?**
- ⚠️ Depends on your goals
- ⚠️ Bengal's strength is **AST autodoc**, not speed
- ⚠️ Users choose Python for DX, not performance
- ⚠️ Hugo already exists for speed

---

## My Recommendation

### Don't Chase "Blazing Fast"

**Instead, own your niche**:

1. ✅ **"Best Python SSG for API docs"**
   - AST-based autodoc without imports
   - No stubs, no runtime required
   - This is genuinely unique

2. ✅ **"Fast enough for most sites"**
   - 10K pages in ~100 seconds
   - 15-50x faster incremental builds
   - Good enough for 99% of use cases

3. ✅ **"Python-native with great DX"**
   - pip install, virtual envs
   - Debuggable Python stacktraces
   - Familiar ecosystem

4. ✅ **"Honest about limitations"**
   - Won't beat compiled SSGs
   - 10K pages max recommended
   - Python overhead accepted

---

## Conclusion

**"Blazing fast" for Python means 200-300 pps**.

Bengal's **100-120 pps is competitive, not exceptional**.

**Better positioning**:
- "Fast enough Python SSG" ✅
- "Best Python SSG for API docs" ✅
- "Python-native with great DX" ✅

**Avoid**:
- "Blazing fast" (without qualifier) ❌
- Speed comparisons with Hugo ❌
- Unvalidated performance claims ❌

**The real selling point isn't speed—it's AST-based autodoc + Python ecosystem.**
