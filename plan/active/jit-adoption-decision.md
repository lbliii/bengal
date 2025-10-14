# JIT Adoption Decision: Manual Opt-In

**Question:** Should `PYTHON_JIT=1` be enabled automatically in `--fast` mode?

**Answer:** ❌ No - Keep it as manual opt-in documentation only

---

## Bengal's Current Philosophy

Looking at existing defaults:

```python
@click.option("--parallel/--no-parallel", default=True, ...)  # ON by default
@click.option("--watch/--no-watch", default=True, ...)         # ON by default  
@click.option("--fast/--no-fast", default=None, ...)           # Opt-in only
```

**Pattern:**
- ✅ **Stable, proven optimizations** → Default ON (parallel rendering)
- ✅ **Convenience features** → Default ON (watch, auto-port)
- ⚠️ **Experimental features** → Opt-in only (--fast mode)

---

## Why JIT Should Stay Manual

### 1. **Experimental Status**
```
Python docs: "This feature is EXPERIMENTAL and may be removed"
```
- Still under development
- May have subtle bugs
- Could break in future Python versions
- Not production-ready

### 2. **Version Requirements**
- Only works in Python 3.13.4+
- Doesn't work in 3.13.0, 3.13.1, 3.13.2, 3.13.3
- Checking version adds complexity
- Risk of silent failures if unavailable

### 3. **Not Universally Beneficial**
- 5-10% speedup (modest)
- Startup overhead hurts small sites
- Best for compute-heavy workloads only
- I/O-bound tasks see minimal benefit

### 4. **Debugging Complexity**
- JIT-compiled code harder to profile
- Different behavior than interpreted
- Makes bug reports harder to reproduce
- Could mask performance issues in development

### 5. **Different from `PYTHON_GIL=0`**
- `PYTHON_GIL=0` suppresses warnings (cosmetic)
- `PYTHON_JIT=1` changes execution (behavioral)
- GIL flag is safe, JIT flag is experimental
- Different risk profiles

---

## Comparison: Parallel vs JIT

| Feature | Parallel Rendering | JIT Compiler |
|---------|-------------------|--------------|
| **Status** | Stable since Python 3.2 | Experimental (3.13.4+) |
| **Impact** | 1.8x faster (180% speedup) | 1.05-1.10x faster (5-10%) |
| **Risk** | None (battle-tested) | Unknown (experimental) |
| **Overhead** | Minimal | Warmup cost |
| **Default?** | ✅ YES | ❌ NO |

---

## Recommended Approach

### 1. Document, Don't Automate
Update `INSTALL_FREE_THREADED.md`:

```markdown
## Optional: Enable JIT Compiler (Experimental)

Python 3.13.4+ includes an experimental JIT for 5-10% faster builds:

```bash
# One-time test
PYTHON_JIT=1 bengal build --fast

# Make permanent (add to ~/.zshrc or ~/.bashrc)
export PYTHON_JIT=1
```

**Note:** This is EXPERIMENTAL. Only use if:
- You have Python 3.13.4 or later
- You're comfortable with experimental features
- You want maximum speed and accept potential bugs
```

### 2. Add to README Under "Performance Tips"

```markdown
## Performance Tips

For fastest builds:

1. **Use Python 3.14t** (free-threaded, 1.8x faster)
   ```bash
   PYTHON_GIL=0 bengal build --fast
   ```

2. **Enable JIT (experimental, 5-10% faster)**
   ```bash
   export PYTHON_JIT=1  # Python 3.13.4+ only
   ```

3. **Use incremental builds**
   ```bash
   bengal build --incremental
   ```
```

### 3. Update `CHANGELOG.md`

```markdown
### Documentation

- **Python 3.13 JIT Support**: Documented how to enable experimental JIT
  compiler for 5-10% faster builds on Python 3.13.4+. See INSTALL_FREE_THREADED.md.
```

---

## User Experience

**Power user workflow:**
```bash
# Add to shell config for maximum speed
echo 'export PYTHON_JIT=1' >> ~/.zshrc
echo 'export PYTHON_GIL=0' >> ~/.zshrc
source ~/.zshrc

# Now just use --fast
bengal build --fast
```

**Beginner workflow:**
```bash
# Just use fast mode - works everywhere
bengal build --fast

# Read docs to learn about JIT if interested
```

---

## Decision Matrix

| Scenario | Should JIT be automatic? |
|----------|-------------------------|
| Small site (< 100 pages) | ❌ NO (startup overhead > benefit) |
| Large site (10K pages) | ❌ NO (modest 5-10% gain, experimental) |
| Production builds | ❌ NO (experimental = risky) |
| Development builds | ❌ NO (different behavior = confusing) |
| Power users | ⚠️ MAYBE (via docs/guide) |

**Conclusion:** ❌ No automatic JIT in any scenario

---

## Implementation Plan

✅ **Do:**
1. Document JIT in `INSTALL_FREE_THREADED.md` (experimental section)
2. Add to `README.md` performance tips (as optional advanced tip)
3. Update `CHANGELOG.md` to mention documentation
4. Add caveat about Python 3.13.4+ requirement

❌ **Don't:**
1. Set `PYTHON_JIT=1` in code
2. Check for JIT support in build orchestrator
3. Make JIT part of `--fast` mode behavior
4. Recommend JIT as default anywhere

---

## Final Answer

**JIT should be documented as an optional advanced optimization for power users,
but NOT enabled automatically in any scenario (including --fast mode).**

**Reason:** Experimental features require explicit user opt-in. Bengal's `--fast`
mode is already experimental enough (free-threading); adding JIT would compound
risk without significant benefit (5-10% vs 180% from parallelism).
