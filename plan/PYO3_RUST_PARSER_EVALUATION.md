# PyO3 + Rust Markdown Parser Evaluation

**Date:** October 3, 2025  
**Proposal:** Replace python-markdown with comrak (Rust) via PyO3  
**Source:** ChatGPT conversation analysis

---

## Executive Summary

**Viability:** ✅ Technically sound and achievable  
**Performance:** 3-5x speedup expected (3.78s → ~1.0s for quickstart)  
**Complexity:** ⚠️ HIGH - Adds Rust toolchain, PyO3, cross-platform builds  
**Recommendation:** **Defer** - Do configurable extensions first (2 hrs, 26% speedup, zero complexity)

---

## Performance Comparison

| Approach | Build Time | Speedup | Effort | Complexity |
|----------|-----------|---------|--------|------------|
| **Current (python-markdown)** | 3.78s | Baseline | - | Low |
| **+ Configurable Extensions** | ~2.8s | 1.35x | 2 hrs | Low |
| **+ Mistune (Pure Python)** | ~1.2s | 3.15x | 6-8 hrs | Medium |
| **+ PyO3 + Rust** | ~0.8-1.0s | 3.8-4.7x | 12-16 hrs | **High** |

---

## What PyO3 Gives You

### 1. True GIL-Free Parallelism ✅
```python
# Current: 10 workers compete for GIL
# With PyO3: All 10 cores work independently
html = py.allow_threads(|| parse_markdown(bytes))
```

**Impact:** Additional 1.5-2x on top of parser speedup

### 2. Native Parser Speed ✅
- comrak (Rust) is 3-5x faster than python-markdown
- Similar to Mistune, but with GIL release

### 3. Future Optimization Path ✅
Once PyO3 infrastructure exists:
- Syntax highlighting (syntect)
- HTML/CSS/JS minification
- Asset processing
- Image optimization

---

## What It Costs You

### 1. Rust Toolchain Requirement ⚠️

**Developers need:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
pip install maturin
```

**Users need:**
- Pre-built wheels for their platform, OR
- Rust toolchain to build from source

### 2. Cross-Platform Wheel Complexity ⚠️

Must build wheels for:
- `manylinux_2_28_x86_64`
- `manylinux_2_28_aarch64`
- `macosx_10_12_x86_64`
- `macosx_11_0_arm64` (Apple Silicon)
- `win_amd64`
- `win32`

**Solution:** GitHub Actions with `maturin build --release` for each platform

### 3. Feature Parity Work ⚠️

| Feature | python-markdown | comrak | Work Needed |
|---------|----------------|---------|-------------|
| Tables | ✅ | ✅ | None |
| Footnotes | ✅ | ✅ | None |
| Code blocks | ✅ | ✅ | None |
| TOC | ✅ Auto + permalinks | ⚠️ Manual | 2-3 hours |
| Admonitions | ✅ `!!! note` | ❌ | 3-4 hours |
| Def lists | ✅ | ❌ | 2-3 hours |

**Total:** 7-10 hours to reach feature parity

### 4. Learning Curve ⚠️

**New skills required:**
- Rust basics (ownership, borrowing)
- PyO3 API and type conversions
- maturin build system
- Debugging across FFI boundary

---

## Design Pattern Analysis

### The Facade Pattern ✅

```python
# bengal/markdown/__init__.py
def render(text: str, opts: MDOptions) -> str:
    if USE_RUST:
        return _render_rust(text, opts)  # PyO3 + comrak
    else:
        return _render_python(text, opts)  # python-markdown
```

**Assessment:** Excellent design
- Clean separation
- Easy A/B testing
- Environment variable fallback
- Single point of change

### The Options Contract ✅

```python
@dataclass(frozen=True)
class MDOptions:
    gfm: bool = True
    tables: bool = True
    footnotes: bool = True
    # ...
```

**Assessment:** Good, but could be simpler
- Frozen dataclass is right
- Maps well to comrak's options
- Consider: "profiles" (minimal, standard, full) instead of 10 flags

---

## Implementation Estimate

### Phase 1: Basic Integration (4-6 hours)
- [ ] Create `bengal/markdown/` facade
- [ ] Set up `native/fastmd/` Rust crate
- [ ] Implement basic `render_doc()` with comrak
- [ ] Add environment variable switching
- [ ] Basic smoke tests

### Phase 2: Feature Parity (6-8 hours)
- [ ] TOC generation with permalinks
- [ ] Heading ID slugification (match current behavior)
- [ ] Admonition support (`!!! note`)
- [ ] Definition list support
- [ ] Golden tests for all features

### Phase 3: Packaging (2-4 hours)
- [ ] maturin setup in pyproject.toml
- [ ] GitHub Actions for wheel building
- [ ] Test wheels on Linux/macOS/Windows
- [ ] Fallback messaging when Rust unavailable

**Total: 12-18 hours**

---

## Risk Assessment

### High Risk ⚠️

1. **Wheel building fails on CI** - maturin + GitHub Actions can be finicky
2. **Feature differences break existing sites** - comrak output differs from python-markdown
3. **Rust toolchain friction** - Contributors may not want to install Rust
4. **Debug complexity** - Harder to trace bugs across Python↔Rust boundary

### Medium Risk ⚠️

1. **Maintenance burden** - Need to understand Rust to fix bugs
2. **Dependency bloat** - Rust dependencies (comrak, syntect) are large
3. **Platform-specific issues** - Different behavior on ARM vs x86

### Low Risk ✅

1. **Performance regression** - Very unlikely; Rust will be faster
2. **API breakage** - Facade pattern protects consumers

---

## Alternative: Staged Rollout

### Stage 1: Parser Instance Reuse (✅ DONE)
- 15 minutes, 10-15% speedup
- Thread-local parser storage
- **Result: 4.29s → 3.78s**

### Stage 2: Configurable Extensions (RECOMMENDED NEXT)
- 2 hours, 20-30% speedup
- Load only needed extensions per page
- Zero new dependencies
- **Estimated: 3.78s → ~2.8s**

### Stage 3: Evaluate User Needs
- Is 2.8s fast enough?
- Do users care about 2.8s vs 1.0s?
- Are we getting adoption?

### Stage 4: PyO3 + Rust (IF NEEDED)
- Only if performance is proven bottleneck
- Only if project has momentum
- When you have time for 12-18 hour investment

---

## Recommendation: Configurable Extensions First

### Why Not PyO3 Now?

1. **Premature optimization** - Don't know if 2.8s is "good enough"
2. **High complexity cost** - Rust adds significant overhead
3. **Quick wins available** - 26% speedup in 2 hours
4. **Reversible** - Can still do PyO3 later if needed

### What to Do Instead

**Implement Option C from earlier discussion:**

```python
# bengal/rendering/parser.py
class MarkdownParser:
    def __init__(self, extensions=None):
        # Only load specified extensions
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.md = markdown.Markdown(extensions=self.extensions)
```

```toml
# In bengal.toml or frontmatter
[markdown]
extensions = ["tables", "toc", "fenced_code"]  # Minimal set
```

**Benefits:**
- 2 hours of work
- 26% speedup (3.78s → 2.8s)
- Keeps all features
- Zero complexity added
- Learn which extensions users actually need

### When to Revisit PyO3

✅ **Do PyO3 if:**
- 2.8s is still too slow after user testing
- Project gets significant adoption
- You're comfortable with Rust
- You have 2-3 weeks for proper implementation + testing

❌ **Don't do PyO3 if:**
- Just trying to hit a performance number
- No users complaining about speed
- Rust feels uncomfortable
- Distribution complexity is concerning

---

## Conclusion

**The PyO3 proposal is technically excellent**, but:
- It's **over-engineering** for current needs
- It **adds significant complexity** (Rust toolchain, wheels, FFI debugging)
- There are **easier wins available** (configurable extensions)

**Recommended path:**
1. **Now:** Configurable extensions (2 hrs) → 2.8s
2. **Later:** Evaluate if 2.8s is fast enough
3. **If needed:** Consider PyO3 OR pure-Python Mistune (simpler distribution)

The proposal is **viable and well-designed**, but **too complex too soon**.

---

## Implementation Sketch (If You Decide to Do It)

If you do want to proceed with PyO3, here's the minimal path:

### 1. Create Rust Crate
```bash
cd /Users/llane/Documents/github/python/bengal
mkdir -p native/fastmd
cd native/fastmd
cargo init --lib
```

### 2. Add Dependencies
```toml
# native/fastmd/Cargo.toml
[dependencies]
pyo3 = "0.22"
comrak = "0.25"
```

### 3. Implement Basic Parser
See the ChatGPT proposal's `src/lib.rs` - it's a good starting point.

### 4. Python Facade
See the ChatGPT proposal's `bengal/markdown/__init__.py` - solid design.

### 5. Test & Benchmark
```bash
maturin develop
python -c "from bengal.markdown import render; print(render('# Test'))"
```

But again: **recommend deferring this** until configurable extensions prove insufficient.

