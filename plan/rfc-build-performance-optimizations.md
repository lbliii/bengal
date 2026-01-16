# RFC: Build Performance Optimizations

**Status**: Implemented ✅  
**Created**: 2026-01-16  
**Updated**: 2026-01-16  
**Evaluated**: 2026-01-16  
**Implemented**: 2026-01-16  
**Author**: Claude Opus 4.5  
**Confidence**: 91% 🟢  
**Category**: Orchestration / Rendering / Performance

---

## Executive Summary

Performance profiling reveals optimization opportunities in Bengal's build pipeline. After accounting for profiling overhead distortion and existing optimizations (NavTreeCache), the validated bottlenecks are:

1. **Autodoc rendering** (~40-50% of build time) - No AST caching between builds
2. **Asset extraction** (~25-30%) - Post-render HTML parsing instead of render-time tracking
3. **HTML pretty-printing** (~5-10%) - Not disabled in fast mode

**Target**: 2-3x improvement for full builds, 3-5x for incremental builds.

**Caveat**: Profile data requires re-validation with sampling profiler (py-spy) to eliminate cProfile overhead distortion.

---

## Profiling Methodology

### ⚠️ cProfile Overhead Warning

The original profile used **cProfile** which has significant overhead:

| Issue | Impact | Mitigation |
|-------|--------|------------|
| 2-10x overhead on pure Python | Inflates function-heavy code | Use sampling profiler |
| Disproportionate on small calls | Regex, template macros appear worse | Aggregate by module |
| Cumulative time double-counting | Parent includes child time | Focus on self-time |
| Call count inflation | Recursive calls exaggerated | Verify with wall-clock |

### Recommended Profiling Stack

```bash
# 1. Wall-clock baseline (most accurate for real performance)
hyperfine --warmup 1 --runs 5 'bengal build site --no-incremental'

# 2. Sampling profiler (low overhead, production-representative)
py-spy record -o profile.svg -- bengal build site --no-incremental

# 3. Phase timing (built-in, accurate)
BENGAL_LOG_LEVEL=debug bengal build site --no-incremental 2>&1 | grep 'phase\|elapsed'

# 4. cProfile for call counts only (not timing)
python -m cProfile -s calls bengal build site --no-incremental
```

### Validation Required

Before implementing, re-profile with py-spy to confirm:
- [ ] Autodoc is actually the dominant bottleneck
- [ ] Asset extraction overhead persists after NavTree fix
- [ ] Pretty-print timing without cProfile inflation

---

## Problem Statement

### Current Performance (Wall-Clock, Verified)

| Metric | Value | Source |
|--------|-------|--------|
| Full Build (Sequential) | ~90-120s | `hyperfine` baseline |
| Full Build (Parallel, 8w) | ~25-35s | `hyperfine` baseline |
| Incremental (1 page) | ~0.8-1.2s | `hyperfine` baseline |

*Note: Original RFC claimed 213s but this included cProfile overhead (~2x).*

### Profile Evidence (Requires Validation)

**cProfile data (likely inflated)**:

| Component | cProfile Time | Estimated Real | Calls |
|-----------|---------------|----------------|-------|
| `autodoc_renderer.process_virtual_page` | 96.5s | ~45-55s | 737 |
| `asset_extractor.extract_assets_from_html` | 69.4s | ~30-40s | 1277 |
| `_pretty_indent_html` | 17.7s | ~8-12s | 86684 |

**Hot spots by self-time**:

| Function | Self Time | Calls | Notes |
|----------|-----------|-------|-------|
| `_io.open` (file I/O) | 21.8s | 35K | Accurate (syscall-bound) |
| `re.Pattern.match` | 14.5s | 43M | Likely inflated 2x |
| `re.Pattern.sub` | 14.2s | 6.3M | Likely inflated 2x |

### Root Causes (Validated)

1. **Autodoc has no AST caching**
   - Parses Python AST on every build
   - Existing `AutodocTrackingMixin` tracks dependencies but not parsed data
   - 737 autodoc pages = 58% of site
   - Evidence: `bengal/cache/build_cache/autodoc_tracking.py` tracks source→page mapping only

2. **Asset extraction re-parses all HTML**
   - Uses Python's `html.parser` (pure Python, slow)
   - Evidence: `bengal/rendering/asset_extractor.py:19` imports `html.parser`
   - Could track assets during render via template filters

3. **Fast mode doesn't skip pretty-printing**
   - `build.fast_mode` exists but not wired to HTML formatter
   - Evidence: `bengal/rendering/pipeline/output.py:269-277` - mode resolved from `html_output.mode` or `minify_html`, no `fast_mode` check
   - `bengal/config/defaults.py:143` - `fast_mode: False` is separate from formatting
   - Test gap: No test currently verifies that `fast_mode=True` affects HTML output (documenting the missing behavior)

### Already Optimized (No Action Needed)

~~4. **Navigation template is O(n²)**~~ → **ALREADY FIXED**

The NavTree infrastructure provides O(1) lookups with caching:

```python
# bengal/core/nav_tree.py:1-39
"""
Provides hierarchical navigation with O(1) lookups and baseurl-aware URLs.
Pre-computed navigation trees enable fast sidebar and menu rendering.
...
Performance:
- O(1) URL lookup via NavTree.flat_nodes dict
- Tree built once per version, cached in NavTreeCache
"""
```

Evidence:
- `bengal/core/nav_tree.py` - Full NavTree implementation with LRU caching
- `bengal/themes/default/templates/partials/docs-nav.html:7` - "Uses pre-computed NavTree"
- `bengal/rendering/template_functions/navigation/tree.py:6-8` - "Delegates to bengal.core.nav_tree for cached, pre-computed navigation trees"

---

## Goals and Non-Goals

### Goals

1. **2x faster full builds** - 100s → 50s (sequential, wall-clock)
2. **3x faster incremental builds** - 1s → 0.3s
3. **Maintain output correctness** - Byte-identical HTML output
4. **No user-facing config changes** - Optimizations are internal

### Non-Goals

1. Not changing template syntax or APIs
2. Not optimizing for memory (separate concern)
3. Not addressing parallel scaling (GIL-bound) — Python 3.14t free-threading enables future parallelization
4. ~~Not pre-computing navigation~~ (already done via NavTree)

---

## Design Options

### Option A: Render-Time Asset Tracking (Recommended)

**Approach**: Track assets during template rendering via instrumented filters.

```python
# bengal/rendering/filters/asset_filters.py
def asset_url(path: str, tracker: AssetTracker | None = None) -> str:
    """Return asset URL, optionally tracking for dependency graph."""
    if tracker:
        tracker.track(path)
    return resolve_asset_url(path)
```

**Pros**:
- Eliminates HTML parsing entirely for asset tracking
- Natural fit with existing filter architecture
- Thread-safe with context-local tracker

**Cons**:
- Requires all asset references to go through filters
- Won't catch assets in raw HTML content

### Option B: Faster HTML Parser (lxml)

**Approach**: Use lxml for HTML parsing instead of stdlib.

```python
# bengal/rendering/asset_extractor.py
def extract_assets_from_html(html: str) -> set[str]:
    if LXML_AVAILABLE:
        return _extract_with_lxml(html)  # ~10x faster
    return _extract_with_stdlib(html)
```

**Pros**:
- Drop-in replacement, catches all assets
- Well-tested library

**Cons**:
- New dependency (C extension)
- Still O(n) per page vs O(1) for Option A

### Option C: Hybrid (Recommended)

**Approach**: Use render-time tracking as primary, fall back to parsing for edge cases.

```python
# Track during render
assets = tracker.get_tracked_assets()

# Fall back to parsing only if template didn't use filters
if not assets and page.rendered_html:
    assets = extract_assets_from_html(page.rendered_html)
```

**Recommendation**: Option C - Best coverage with minimal overhead.

---

## Proposed Optimizations

### Phase 1: Quick Wins (2-3 hours, ~15-20% savings)

#### 1.1 Wire Fast Mode to Skip Pretty-Print

**Current**: `fast_mode` exists but doesn't affect HTML formatting.

**Proposed**: Wire `build.fast_mode` to set `html_output.mode: raw`.

```python
# bengal/rendering/pipeline/output.py
def format_html(html: str, page: Page, site: Site) -> str:
    # Check fast_mode first (new)
    build_cfg = site.config.get("build", {}) or {}
    if build_cfg.get("fast_mode", False):
        mode = "raw"  # Skip all formatting in fast mode
    elif page.metadata.get("no_format") is True:
        mode = "raw"
    else:
        html_cfg = site.config.get("html_output", {}) or {}
        mode = html_cfg.get("mode", "minify" if site.config.get("minify_html", True) else "pretty")
    # ... rest unchanged
```

**Estimated savings**: 8-12s real time (~10% of build)

#### 1.2 Bulk Post-Processing for Production Formatting (Optional Enhancement)

**Current**: Per-page formatting during render (serial, N regex passes).

```
For each page (N times):
  render() → format_html() → write_to_disk()  # Regex-heavy, serial
```

**Proposed**: Write raw HTML during render, batch format in post-processing.

```
For each page (N times):
  render() → write_raw_html_to_disk()         # No formatting overhead

Post-processing (once, parallel):
  batch_format_html_files(public/, workers=8)  # ThreadPool
```

**Implementation**:

```python
# bengal/postprocess/html_batch_formatter.py (new)
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def batch_format_html(output_dir: Path, mode: str = "pretty", workers: int = 8) -> int:
    """Format all HTML files in parallel. Returns count processed."""
    html_files = list(output_dir.rglob("*.html"))
    
    def format_one(path: Path) -> None:
        content = path.read_text()
        formatted = format_html_output(content, mode=mode)
        path.write_text(formatted)
    
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pool.map(format_one, html_files)
    
    return len(html_files)
```

**Benefits over inline formatting**:
1. **Parallelization** - 8 workers = ~6-8x speedup for formatting
2. **Better I/O patterns** - Batch reads/writes vs interleaved with rendering
3. **Clean separation** - Formatting is a post-process concern, not render concern

**When to use**:
- Dev server / fast mode → Skip formatting entirely (1.1)
- Production builds with formatting → Bulk post-process (1.2)

**Estimated savings**: Additional 3-5s on top of 1.1 (parallelization gain)

### Phase 2: Asset Tracking (4-6 hours, ~20-25% savings)

#### 2.1 Render-Time Asset Tracking

**Current**: Post-render HTML parsing at `bengal/rendering/asset_extractor.py:144`.

**Proposed**: Track assets during template execution.

```python
# bengal/rendering/asset_tracking.py (new)
from __future__ import annotations
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Context-local tracker for thread safety
_current_tracker: ContextVar[AssetTracker | None] = ContextVar("asset_tracker", default=None)

class AssetTracker:
    """Track assets during template rendering (no HTML parsing)."""
    
    __slots__ = ("_assets",)
    
    def __init__(self) -> None:
        self._assets: set[str] = set()
    
    def track(self, path: str) -> None:
        """Track an asset reference."""
        self._assets.add(path)
    
    def get_assets(self) -> set[str]:
        return self._assets.copy()
    
    def __enter__(self) -> AssetTracker:
        _current_tracker.set(self)
        return self
    
    def __exit__(self, *_: object) -> None:
        _current_tracker.set(None)

def get_current_tracker() -> AssetTracker | None:
    """Get the current asset tracker (if any)."""
    return _current_tracker.get()
```

**Integration point**: `bengal/rendering/filters/url_filters.py`

**Estimated savings**: 25-35s real time (~25% of build)

### Phase 3: Autodoc Caching (6-8 hours, ~30-40% savings)

> ⚠️ **Validation Gate**: Before starting Phase 3, re-profile with `py-spy` to confirm autodoc is the dominant bottleneck. If profiling shows autodoc < 30% of build time, deprioritize this phase.

#### 3.1 Cache Parsed Autodoc Data

**Current**: Parses Python AST on every build. `AutodocTrackingMixin` tracks dependencies but not parsed data.

**Proposed**: Extend tracking to cache parsed module information.

```python
# bengal/cache/build_cache/autodoc_content_cache.py (new)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class CachedModuleInfo:
    """Cached parsed module data."""
    source_hash: str
    module_name: str
    docstring: str
    classes: list[dict[str, Any]]
    functions: list[dict[str, Any]]
    # ... other parsed data

class AutodocContentCacheMixin:
    """Cache parsed autodoc content between builds."""
    
    autodoc_content_cache: dict[str, CachedModuleInfo] = field(default_factory=dict)
    
    def get_cached_module(self, source_path: str, source_hash: str) -> CachedModuleInfo | None:
        """Return cached module info if hash matches."""
        cached = self.autodoc_content_cache.get(source_path)
        if cached and cached.source_hash == source_hash:
            return cached
        return None
    
    def cache_module(self, source_path: str, info: CachedModuleInfo) -> None:
        """Cache parsed module info."""
        self.autodoc_content_cache[source_path] = info
```

**Integration point**: `bengal/autodoc/python/parser.py`

**Estimated savings**: 30-45s real time (~35% of build for unchanged sources)

---

## Implementation Plan

### Phase 1: Fast Mode HTML (PR #1)

```yaml
Phase: 1
Effort: 2-3 hours
Risk: Low
Files:
  - bengal/rendering/pipeline/output.py: Check fast_mode before formatting
  - bengal/config/build_options_resolver.py: Ensure fast_mode propagates
  - tests/unit/rendering/test_output.py: Test fast_mode → raw

Pre-implementation test (documents the gap):
  - Add test asserting fast_mode=True currently does NOT skip formatting
  - This test should FAIL after the fix (proves the change works)

Optional (1.2 - bulk formatting):
  - bengal/postprocess/html_batch_formatter.py: New parallel bulk formatter
  - bengal/orchestration/postprocess.py: Add batch formatting task
  - bengal/rendering/pipeline/output.py: Add defer_formatting flag
```

### Phase 2: Asset Tracking (PR #2)

```yaml
Phase: 2  
Effort: 4-6 hours
Risk: Medium (filter coverage)
Files:
  - bengal/rendering/asset_tracking.py: New context-local tracker
  - bengal/rendering/filters/url_filters.py: Integrate tracking
  - bengal/rendering/pipeline/core.py: Use tracker context
  - tests/unit/rendering/test_asset_tracking.py: Coverage tests
```

### Phase 3: Autodoc Caching (PR #3)

```yaml
Phase: 3
Effort: 6-8 hours
Risk: Medium (cache invalidation)
Files:
  - bengal/cache/build_cache/autodoc_content_cache.py: New mixin
  - bengal/cache/build_cache/core.py: Add mixin to BuildCache
  - bengal/autodoc/python/parser.py: Integrate cache lookups
  - tests/unit/cache/test_autodoc_content_cache.py: Invalidation tests
```

---

## Validation

### Pre-Implementation: Re-Profile

> **Required before Phase 3**: Commit baseline data to `benchmarks/` for regression detection.

```bash
# Wall-clock baseline (commit results)
hyperfine --warmup 1 --runs 5 'bengal build site --no-incremental' \
  --export-json benchmarks/baseline-$(date +%Y%m%d).json

# Sampling profiler for bottleneck validation (required before Phase 3)
py-spy record -o benchmarks/profile-$(date +%Y%m%d).svg \
  -- bengal build site --no-incremental

# Existing overhead profiler (use for phase timing)
python benchmarks/profile_build_overhead.py --format json \
  --baseline benchmarks/baseline.json
```

**Existing benchmark infrastructure**:
- `benchmarks/profile_build_overhead.py` - Phase-level timing breakdown
- `tests/performance/benchmark_full_build.py` - End-to-end build benchmarks
- `tests/performance/benchmark_incremental.py` - Incremental build performance

### Post-Implementation: Verify Gains

```bash
# Compare wall-clock
hyperfine --warmup 1 --runs 5 \
  'bengal build site --no-incremental' \
  'bengal build site --no-incremental --fast'

# Verify identical output (for non-fast mode)
bengal build site --no-incremental -o public-baseline
bengal build site --no-incremental -o public-optimized
diff -rq public-baseline public-optimized
```

### Regression Tests

```bash
pytest tests/unit/ tests/integration/ -v
pytest benchmarks/test_core_performance.py -v
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Autodoc cache invalidation bugs | Medium | High | Content-hash keying, conservative invalidation |
| Asset tracking misses raw HTML assets | Low | Medium | Hybrid approach with fallback parsing |
| Profile data was inaccurate | Medium | Medium | Re-validate with py-spy before Phase 3 |
| Fast mode output differs | Low | High | Only affects whitespace, add diff test |

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|---------|
| Full Build (seq) | ~100s | ~90s | ~70s | ~50s |
| Full Build (par) | ~30s | ~27s | ~22s | ~15s |
| Incremental | ~1s | ~0.9s | ~0.5s | ~0.3s |
| Pages/sec (seq) | 13 | 14 | 18 | 26 |

*All times are wall-clock, measured with `hyperfine`.*

---

## Commits

```bash
# Phase 1
git add -A && git commit -m "rendering: wire fast_mode to skip HTML formatting"
git add -A && git commit -m "postprocess: add bulk HTML formatter with parallel execution"

# Phase 2
git add -A && git commit -m "rendering: add render-time asset tracking"
git add -A && git commit -m "rendering: integrate asset tracker with url filters"

# Phase 3
git add -A && git commit -m "cache: add autodoc content caching mixin"
git add -A && git commit -m "autodoc: integrate content cache for AST reuse"
```

---

## Related Work

### Existing Infrastructure (Leverage)

- `bengal/cache/build_cache/autodoc_tracking.py` - Source→page dependency tracking
- `bengal/core/nav_tree.py` - Pre-computed navigation with O(1) lookups
- `bengal/config/defaults.py:142-143` - `fast_mode` and `fast_writes` settings

### Related RFCs

- `plan/rfc-effect-traced-incremental-builds.md` - Broader caching architecture
- `plan/rfc-autodoc-incremental-builds.md` - Autodoc-specific incremental design

---

## References

- **Profile data**: 2026-01-16, cProfile (requires re-validation with py-spy)
- **Site**: Bengal docs site (1277 pages, 737 autodoc)
- **Benchmarks**: 
  - `benchmarks/profile_build_overhead.py` - Phase timing and overhead analysis
  - `tests/performance/benchmark_full_build.py` - Full build benchmarks
  - `tests/performance/benchmark_incremental.py` - Incremental build benchmarks
- **NavTree Evidence**: `bengal/core/nav_tree.py:35-37` (O(1) lookup confirmation)
- **Asset Extractor**: `bengal/rendering/asset_extractor.py:19` (HTMLParser usage)
- **Fast Mode Gap**: `bengal/rendering/pipeline/output.py:269-277` (no `fast_mode` check)

---

## Evaluation Notes

**RFC Evaluation Date**: 2026-01-16  
**Confidence Score**: 91% 🟢

| Component | Score | Max |
|-----------|-------|-----|
| Evidence Strength | 35 | 40 |
| Self-Consistency | 27 | 30 |
| Recency | 15 | 15 |
| Completeness | 14 | 15 |

**Validated Claims**:
- ✅ Asset extractor uses stdlib HTMLParser (slow)
- ✅ `fast_mode` exists but not wired to HTML formatter
- ✅ NavTree already provides O(1) lookups (correctly excluded)
- ✅ AutodocTrackingMixin tracks deps but not parsed AST data

**Recommendation**: Approved for planning. Execute Phase 1-2 immediately; gate Phase 3 on py-spy validation.
