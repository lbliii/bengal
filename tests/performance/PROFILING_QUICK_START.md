# Profiling Quick Start 🔥

Fast guide to profiling Bengal SSG. The profiling system is **production-ready** and **world-class**.

## 30-Second Start

```bash
# 1. Profile your site
python tests/performance/profile_site.py examples/showcase

# 2. View results (requires snakeviz)
pip install snakeviz
python tests/performance/flamegraph.py examples/showcase/.bengal/profiles/build_profile.stats
```

Done! The flame graph shows bottlenecks visually (wide bars = slow).

## Common Tasks

### Find Bottleneck
```bash
python tests/performance/profile_site.py examples/showcase
python tests/performance/flamegraph.py examples/showcase/.bengal/profiles/build_profile.stats
# → Opens browser, look for wide bars
```

### Compare Before/After
```bash
# Before
python tests/performance/profile_site.py examples/showcase
cp examples/showcase/.bengal/profiles/build_profile.stats baseline.stats

# Make changes...

# After
python tests/performance/profile_site.py examples/showcase
python tests/performance/analyze_profile.py \
    examples/showcase/.bengal/profiles/build_profile.stats \
    --compare baseline.stats
```

### CI/CD Regression Detection
```bash
python tests/performance/analyze_profile.py current.stats \
    --compare baseline.stats \
    --fail-on-regression 15
# → Fails if any function regresses >15%
```

## Available Tools

| Tool | Purpose | Time to Learn |
|------|---------|---------------|
| `flamegraph.py` | Visual profiling | 1 minute |
| `analyze_profile.py` | Text analysis + comparison | 2 minutes |
| `profile_site.py` | Profile any site | 1 minute |
| `profile_utils.py` | Programmatic profiling | 5 minutes |

## Installation

```bash
# Optional (but highly recommended for visualization)
pip install snakeviz
```

## Full Docs

- **[PROFILING_GUIDE.md](PROFILING_GUIDE.md)** - Complete guide with examples
- **[README.md](README.md)** - Performance benchmarks + profiling section

## Why This Matters

**Before:**
- No idea what's slow
- Guessing at optimizations
- No regression detection
- Text-only pstats output (500+ lines)

**After:**
- Visual flame graphs show bottlenecks in seconds
- Data-driven optimization
- Automated regression detection in CI
- Beautiful, actionable reports

## Example Output

### Flame Graph (snakeviz)
```
Opens browser with interactive visualization:
├── Wide bars = functions taking most time
├── Tall stacks = deep call chains
└── Click to zoom, hover for details
```

### Regression Detection
```
⚠️  PERFORMANCE REGRESSIONS (slower):
Function                          Change      Current    Baseline
mistune.py::parse                +15.3%     2.345s     2.034s
pipeline.py::process_page        +8.7%      1.234s     1.135s

✅ PERFORMANCE IMPROVEMENTS (faster):
Function                          Change      Current    Baseline
cache.py::is_changed             -23.1%     0.123s     0.160s
```

## Comparison with Other SSGs

| Feature | Bengal | Hugo | Jekyll | Eleventy |
|---------|--------|------|--------|----------|
| Flame graphs | ✅ 3 tools | ❌ | ❌ | ❌ |
| Regression detection | ✅ | ❌ | ❌ | ❌ |
| CI/CD integration | ✅ | ❌ | ❌ | ❌ |
| Visual profiling | ✅ | ❌ | ❌ | ❌ |
| Comparison tool | ✅ | ❌ | ❌ | ❌ |

**Bengal has the most advanced profiling system of any SSG.**

## Next Steps

1. **Try it now**: `python tests/performance/profile_site.py examples/showcase`
2. **Read full guide**: [PROFILING_GUIDE.md](PROFILING_GUIDE.md)
3. **Add to CI**: See [README.md#ci-integration](README.md#ci-integration)

---

**TL;DR:** Run `profile_site.py`, then `flamegraph.py`. You'll find bottlenecks in seconds.
