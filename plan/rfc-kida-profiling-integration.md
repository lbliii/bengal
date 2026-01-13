# RFC: Kida Profiling Integration

**Status**: Draft  
**Created**: 2026-01-13  
**Updated**: 2026-01-13  
**Depends on**: Kida `rfc-contextvar-patterns` (✅ Implemented)  
**Target**: Bengal 0.2.x  
**Priority**: P2 (DX improvement, build insights)

---

## Executive Summary

Kida 0.1.x now includes `RenderAccumulator` for opt-in template profiling. Bengal can integrate this to provide:

| Feature | Value | Effort |
|---------|-------|--------|
| **Build performance reports** | Identify slow templates | Low |
| **Dev server overlay** | Real-time render metrics | Medium |
| **Block cache effectiveness** | Cache hit/miss visibility | Low |

**Total Estimated Effort**: 4-6 hours

---

## Motivation

### Current State

Bengal renders templates without visibility into performance:

```python
# rendering/pipeline/core.py (current)
for page in pages:
    html = template.render(page=page, site=site)
    # No idea which blocks/includes are slow
```

**Problems**:
1. No way to identify slow templates during builds
2. Block cache effectiveness is invisible
3. Dev experience lacks performance feedback

### After Kida RenderContext Implementation

Kida now provides:
- `RenderContext`: Clean per-render state via ContextVar
- `RenderAccumulator`: Opt-in profiling with zero overhead when disabled
- `profiled_render()`: Context manager for collecting metrics

---

## Pattern 1: Build Performance Reports

### Problem

Large sites (1000+ pages) can have slow builds. Users don't know which templates are the bottleneck.

### Solution

Collect render metrics during build and report summary:

```python
# bengal/rendering/pipeline/profiling.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


@dataclass
class BuildMetrics:
    """Accumulated metrics across all page renders."""
    
    # Per-template timings
    template_times: dict[str, list[float]] = field(default_factory=dict)
    
    # Block timings (aggregated across templates)
    block_times: dict[str, list[float]] = field(default_factory=dict)
    
    # Include counts
    include_counts: dict[str, int] = field(default_factory=dict)
    
    # Cache stats
    cache_hits: int = 0
    cache_misses: int = 0
    
    def record_page(self, page: Page, metrics: dict) -> None:
        """Record metrics from a single page render."""
        template_name = page.template or "default"
        
        # Track template time
        if template_name not in self.template_times:
            self.template_times[template_name] = []
        self.template_times[template_name].append(metrics["total_ms"])
        
        # Track block times
        for block_name, block_data in metrics.get("blocks", {}).items():
            if block_name not in self.block_times:
                self.block_times[block_name] = []
            self.block_times[block_name].append(block_data["ms"])
        
        # Track includes
        for include_name, count in metrics.get("includes", {}).items():
            self.include_counts[include_name] = (
                self.include_counts.get(include_name, 0) + count
            )
    
    def summary(self) -> dict:
        """Generate build performance summary."""
        def stats(times: list[float]) -> dict:
            if not times:
                return {"count": 0, "avg_ms": 0, "total_ms": 0}
            return {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 2),
                "total_ms": round(sum(times), 2),
                "max_ms": round(max(times), 2),
            }
        
        return {
            "templates": {
                name: stats(times) 
                for name, times in sorted(
                    self.template_times.items(),
                    key=lambda x: sum(x[1]),
                    reverse=True,
                )[:10]  # Top 10 slowest
            },
            "blocks": {
                name: stats(times)
                for name, times in sorted(
                    self.block_times.items(),
                    key=lambda x: sum(x[1]),
                    reverse=True,
                )[:10]  # Top 10 slowest
            },
            "includes": dict(
                sorted(
                    self.include_counts.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]  # Top 10 most included
            ),
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": (
                    round(self.cache_hits / (self.cache_hits + self.cache_misses) * 100, 1)
                    if (self.cache_hits + self.cache_misses) > 0
                    else 0
                ),
            },
        }
```

### Integration with Render Pipeline

```python
# bengal/rendering/pipeline/core.py
from kida.render_accumulator import profiled_render

from bengal.rendering.pipeline.profiling import BuildMetrics


def render_pages(
    pages: list[Page],
    env: Environment,
    *,
    profile: bool = False,
) -> list[RenderedPage]:
    """Render all pages, optionally collecting metrics."""
    
    build_metrics = BuildMetrics() if profile else None
    results = []
    
    for page in pages:
        template = env.get_template(page.template or "default.html")
        
        if profile:
            with profiled_render() as metrics:
                html = template.render(page=page, site=site)
            build_metrics.record_page(page, metrics.summary())
        else:
            html = template.render(page=page, site=site)
        
        results.append(RenderedPage(page, html))
    
    if profile:
        _report_build_metrics(build_metrics)
    
    return results


def _report_build_metrics(metrics: BuildMetrics) -> None:
    """Print build performance summary."""
    summary = metrics.summary()
    
    print("\n📊 Build Performance Report")
    print("=" * 50)
    
    print("\n🐢 Slowest Templates:")
    for name, stats in list(summary["templates"].items())[:5]:
        print(f"  {name}: {stats['avg_ms']:.1f}ms avg × {stats['count']} = {stats['total_ms']:.1f}ms")
    
    print("\n🧱 Slowest Blocks:")
    for name, stats in list(summary["blocks"].items())[:5]:
        print(f"  {name}: {stats['avg_ms']:.1f}ms avg × {stats['count']} = {stats['total_ms']:.1f}ms")
    
    print("\n📦 Most Included:")
    for name, count in list(summary["includes"].items())[:5]:
        print(f"  {name}: {count} times")
    
    cache = summary["cache"]
    print(f"\n💾 Block Cache: {cache['hit_rate']}% hit rate ({cache['hits']} hits, {cache['misses']} misses)")
```

### CLI Integration

```python
# bengal/cli/build.py
@click.command()
@click.option("--profile", is_flag=True, help="Show template performance report")
def build(profile: bool):
    """Build the site."""
    site = Site.from_config()
    site.build(profile=profile)
```

**Usage**:

```bash
$ bengal build --profile

Building site...
✅ Built 847 pages in 12.3s

📊 Build Performance Report
==================================================

🐢 Slowest Templates:
  layouts/post.html: 8.2ms avg × 523 = 4288.6ms
  layouts/list.html: 12.4ms avg × 45 = 558.0ms
  layouts/home.html: 45.2ms avg × 1 = 45.2ms

🧱 Slowest Blocks:
  content: 5.1ms avg × 847 = 4319.7ms
  sidebar: 2.3ms avg × 847 = 1948.1ms
  nav: 0.8ms avg × 847 = 677.6ms

📦 Most Included:
  partials/post-meta.html: 1046 times
  partials/pagination.html: 45 times
  partials/breadcrumbs.html: 523 times

💾 Block Cache: 94.2% hit rate (12705 hits, 792 misses)
```

---

## Pattern 2: Dev Server Performance Overlay

### Problem

During development, slow templates cause frustrating page loads. No visibility into what's slow.

### Solution

Inject performance overlay in dev mode:

```python
# bengal/server/middleware.py
from kida.render_accumulator import profiled_render


def render_with_overlay(template, context: dict, dev_mode: bool) -> str:
    """Render template, injecting dev overlay if enabled."""
    if not dev_mode:
        return template.render(**context)
    
    with profiled_render() as metrics:
        html = template.render(**context)
    
    summary = metrics.summary()
    overlay = _build_overlay_html(summary)
    
    # Inject before </body>
    if "</body>" in html:
        html = html.replace("</body>", f"{overlay}</body>")
    
    return html


def _build_overlay_html(summary: dict) -> str:
    """Build dev overlay HTML."""
    total = summary["total_ms"]
    blocks = summary.get("blocks", {})
    includes = summary.get("includes", {})
    
    block_rows = "".join(
        f'<div class="bengal-metric"><span>{name}</span><span>{data["ms"]:.1f}ms</span></div>'
        for name, data in list(blocks.items())[:5]
    )
    
    include_rows = "".join(
        f'<div class="bengal-metric"><span>{name}</span><span>×{count}</span></div>'
        for name, count in list(includes.items())[:3]
    )
    
    return f'''
<div id="bengal-devtools" style="
    position: fixed; bottom: 10px; right: 10px;
    background: #1a1a2e; color: #eee; padding: 12px 16px;
    border-radius: 8px; font-family: monospace; font-size: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 99999;
    max-width: 280px;
">
    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
        <span style="color: #64ffda;">⚡ Render</span>
        <span style="font-weight: bold;">{total:.1f}ms</span>
    </div>
    {f'<div style="border-top: 1px solid #333; padding-top: 8px; margin-top: 8px;"><div style="color: #888; margin-bottom: 4px;">Blocks</div>{block_rows}</div>' if block_rows else ''}
    {f'<div style="border-top: 1px solid #333; padding-top: 8px; margin-top: 8px;"><div style="color: #888; margin-bottom: 4px;">Includes</div>{include_rows}</div>' if include_rows else ''}
    <div style="color: #666; font-size: 10px; margin-top: 8px;">bengal dev</div>
</div>
<style>
.bengal-metric {{ display: flex; justify-content: space-between; padding: 2px 0; }}
.bengal-metric span:first-child {{ color: #aaa; }}
</style>
'''
```

### Server Integration

```python
# bengal/server/core.py
class DevServer:
    def __init__(self, site: Site, *, show_overlay: bool = True):
        self.site = site
        self.show_overlay = show_overlay
    
    def render_page(self, path: str) -> str:
        page = self.site.get_page(path)
        template = self.site.env.get_template(page.template)
        
        return render_with_overlay(
            template,
            {"page": page, "site": self.site.context},
            dev_mode=self.show_overlay,
        )
```

---

## Pattern 3: Block Cache Effectiveness Reporting

### Problem

Bengal's block cache (`_cached_blocks`) is invisible. Users don't know if it's working.

### Solution

Track cache stats via `RenderContext.cache_stats`:

```python
# bengal/rendering/cache.py
def render_with_cache_tracking(
    template,
    page: Page,
    site: SiteContext,
    cached_blocks: dict[str, str],
) -> tuple[str, dict[str, int]]:
    """Render with block cache and return cache stats."""
    
    cache_stats = {"hits": 0, "misses": 0}
    
    html = template.render(
        page=page,
        site=site,
        _cached_blocks=cached_blocks,
        _cached_stats=cache_stats,  # Kida tracks hits/misses
    )
    
    return html, cache_stats
```

### Build Summary Integration

```python
# After build completes
total_hits = sum(page_stats["hits"] for page_stats in all_stats)
total_misses = sum(page_stats["misses"] for page_stats in all_stats)

if total_hits + total_misses > 0:
    hit_rate = total_hits / (total_hits + total_misses) * 100
    print(f"Block cache: {hit_rate:.1f}% hit rate ({total_hits:,} hits)")
    
    if hit_rate < 80:
        print("⚠️  Low cache hit rate. Consider caching more site-scoped blocks.")
```

---

## Implementation Plan

### Phase 1: Build Reports (2-3 hours)

1. Create `bengal/rendering/pipeline/profiling.py`
2. Add `--profile` flag to `bengal build`
3. Integrate with render pipeline
4. Add summary output

**Files Modified**:
- `bengal/rendering/pipeline/profiling.py` (new)
- `bengal/rendering/pipeline/core.py`
- `bengal/cli/build.py`

### Phase 2: Dev Server Overlay (2-3 hours)

1. Create overlay middleware
2. Add `--no-overlay` flag to `bengal serve`
3. Style overlay for minimal footprint

**Files Modified**:
- `bengal/server/middleware.py` (new)
- `bengal/server/core.py`
- `bengal/cli/serve.py`

### Phase 3: Cache Stats (1 hour)

1. Pass `_cached_stats` to template.render()
2. Aggregate in BuildMetrics
3. Report in build summary

**Files Modified**:
- `bengal/rendering/pipeline/core.py`
- `bengal/rendering/pipeline/profiling.py`

---

## Test Strategy

### Unit Tests

```python
# tests/test_profiling.py
def test_build_metrics_records_page():
    metrics = BuildMetrics()
    metrics.record_page(page, {
        "total_ms": 10.5,
        "blocks": {"content": {"ms": 8.0}},
        "includes": {"partials/nav.html": 2},
    })
    
    summary = metrics.summary()
    assert "layouts/default.html" in summary["templates"]
    assert summary["templates"]["layouts/default.html"]["avg_ms"] == 10.5


def test_profiled_render_integration():
    """Verify Kida profiled_render works in Bengal context."""
    from kida.render_accumulator import profiled_render
    
    env = create_test_env()
    template = env.get_template("test.html")
    
    with profiled_render() as metrics:
        html = template.render(page=test_page)
    
    summary = metrics.summary()
    assert "total_ms" in summary
    assert summary["total_ms"] >= 0
```

### Integration Tests

```python
def test_build_with_profile_flag(tmp_site):
    """Build with --profile produces performance report."""
    result = runner.invoke(build, ["--profile"])
    
    assert result.exit_code == 0
    assert "Build Performance Report" in result.output
    assert "Slowest Templates" in result.output
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Build report overhead | <5% build time increase |
| Dev overlay render overhead | <10ms additional |
| Cache hit rate visibility | 100% (always shown) |
| User adoption | Report shown on `--profile` |

---

## Future Opportunities

1. **HTML report export**: `bengal build --profile --report=perf.html`
2. **Threshold warnings**: Warn if any template >50ms
3. **Historical tracking**: Compare builds over time
4. **IDE integration**: Show metrics in Cursor/VSCode

---

## References

- Kida `plan/rfc-contextvar-patterns.md` (✅ Implemented)
- Kida `render_accumulator.py` — profiling API
- Bengal `plan/rfc-contextvar-downstream-patterns.md` — related patterns
