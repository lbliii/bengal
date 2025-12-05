# RFC: Systematic Observability Improvements

**Status**: Draft  
**Created**: 2025-06-05  
**Author**: AI Assistant  
**Related**: `plan/implemented/rfc-build-integrated-validation.md`

---

## Summary

Add systematic observability across Bengal's build pipeline to enable rapid diagnosis of performance issues, cache effectiveness, and processing bottlenecks. This RFC proposes standardized stats collection, structured logging, and CLI output improvements.

---

## Problem Statement

### The Debugging Experience Today

When the DirectiveValidator was taking 7+ seconds, we had to:

1. **Manually add debug prints** to trace execution flow
2. **Guess at bottlenecks** without timing data
3. **Add counters** to discover 450/450 pages were being skipped
4. **Check multiple files** to verify cache was being passed correctly

This took ~30 minutes of manual debugging that could have been seconds with proper observability.

### Evidence: What We Couldn't See

```
# What the CLI showed:
✓ Health check 7619ms
   🐌 Slowest: Directives: 7554ms

# What we NEEDED to see:
✓ Health check 7619ms
   🐌 Slowest: Directives: 7554ms
   📊 Directives: processed=0/776 | skipped=[autodoc=450] | cache=0/0 (0%) | timings=[analyze=64ms, rendering=7554ms]
                  ^^^^^^^^^^^       ^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^
                  PROBLEM 1         PROBLEM 2               PROBLEM 3
```

### Current Observability Gaps

| Component | Logging | Timing | Cache Stats | Skip Counts | Sub-timings |
|-----------|---------|--------|-------------|-------------|-------------|
| `BengalLogger` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `HealthCheck` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `DirectiveValidator` | ✅ NEW | ✅ NEW | ✅ NEW | ✅ NEW | ✅ NEW |
| `LinkValidator` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `OutputValidator` | ❌ | ❌ | N/A | ❌ | ❌ |
| `ContentDiscovery` | Partial | ❌ | ❌ | ❌ | ❌ |
| `AssetPipeline` | Partial | Partial | ❌ | ❌ | ❌ |
| `RenderOrchestrator` | Partial | ✅ | ❌ | ❌ | ❌ |
| `BuildCache` | ❌ | ❌ | Partial (Counts only) | N/A | ❌ |

---

## Proposed Solution

### 1. Standardized Stats Protocol

Create a `Stats` protocol that components can implement. This will integrate with the existing `BuildStats` (bengal/utils/build_stats.py) which currently tracks global metrics but lacks granular component-level visibility:

```python
# bengal/utils/observability.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

@runtime_checkable
class HasStats(Protocol):
    """Protocol for components that expose observability stats."""
    last_stats: "ComponentStats | None"

@dataclass
class ComponentStats:
    """Base stats for any component."""

    # Counts
    items_total: int = 0
    items_processed: int = 0
    items_skipped: dict[str, int] = field(default_factory=dict)

    # Cache effectiveness
    cache_hits: int = 0
    cache_misses: int = 0

    # Timing breakdown
    sub_timings: dict[str, float] = field(default_factory=dict)

    # Custom metrics (component-specific)
    metrics: dict[str, int | float | str] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        """Skip rate as percentage (0-100)."""
        if self.items_total == 0:
            return 0.0
        skipped = sum(self.items_skipped.values())
        return (skipped / self.items_total * 100)

    def format_summary(self, name: str = "") -> str:
        """Format for CLI output."""
        parts = []

        # Processing stats
        if self.items_total > 0:
            parts.append(f"processed={self.items_processed}/{self.items_total}")

        # Skip breakdown
        if self.items_skipped:
            skip_str = ", ".join(f"{k}={v}" for k, v in self.items_skipped.items())
            parts.append(f"skipped=[{skip_str}]")

        # Cache stats
        if self.cache_hits or self.cache_misses:
            parts.append(f"cache={self.cache_hits}/{self.cache_hits + self.cache_misses} ({self.cache_hit_rate:.0f}%)")

        # Sub-timings
        if self.sub_timings:
            timing_str = ", ".join(f"{k}={v:.0f}ms" for k, v in self.sub_timings.items())
            parts.append(f"timings=[{timing_str}]")

        # Custom metrics
        if self.metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in self.metrics.items())
            parts.append(f"metrics=[{metrics_str}]")

        prefix = f"{name}: " if name else ""
        return prefix + " | ".join(parts)

    def to_log_context(self) -> dict[str, int | float | str]:
        """Convert to flat dict for structured logging."""
        ctx = {
            "items_total": self.items_total,
            "items_processed": self.items_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "skip_rate": self.skip_rate,
        }

        # Flatten sub-timings
        for k, v in self.sub_timings.items():
            ctx[f"timing_{k}_ms"] = v

        # Flatten skip reasons
        for k, v in self.items_skipped.items():
            ctx[f"skipped_{k}"] = v

        # Flatten metrics
        for k, v in self.metrics.items():
            ctx[f"metric_{k}"] = v

        return ctx
```

### 2. Component-Specific Implementations

#### 2.1 Health Validators

Already implemented for `DirectiveValidator`. Extend to others:

```python
# LinkValidator
class LinkValidator(BaseValidator):
    last_stats: ComponentStats | None = None

    def validate(self, site, build_context=None):
        stats = ComponentStats(items_total=len(site.pages))

        for page in site.pages:
            if not page.links:
                stats.items_skipped["no_links"] += 1
                continue
            stats.items_processed += 1

            # Track cache
            for link in page.links:
                if self._link_cache.get(link):
                    stats.cache_hits += 1
                else:
                    stats.cache_misses += 1

        self.last_stats = stats
        return results

# OutputValidator
class OutputValidator(BaseValidator):
    last_stats: ComponentStats | None = None

    def validate(self, site, build_context=None):
        stats = ComponentStats()
        stats.items_total = len(list(site.output_dir.rglob("*.html")))

        for html_file in site.output_dir.rglob("*.html"):
            stats.items_processed += 1
            # Check file...

        self.last_stats = stats
        return results
```

#### 2.2 Content Discovery

```python
class ContentDiscovery:
    last_stats: ComponentStats | None = None

    def discover(self, ...):
        stats = ComponentStats()
        t0 = time.time()

        # Count files
        all_files = list(content_dir.rglob("*.md"))
        stats.items_total = len(all_files)

        for file_path in all_files:
            t_file = time.time()

            if self._should_skip(file_path):
                stats.items_skipped["filtered"] += 1
                continue

            stats.items_processed += 1

            # Track cache
            if build_context and build_context.get_content(file_path):
                stats.cache_hits += 1
            else:
                stats.cache_misses += 1

        stats.sub_timings["total"] = (time.time() - t0) * 1000
        self.last_stats = stats

        logger.debug("discovery_complete", **stats.to_log_context())
```

#### 2.3 Build Cache

```python
class BuildCache:
    last_stats: ComponentStats | None = None

    def load(self):
        stats = ComponentStats()
        t0 = time.time()

        if self._cache_path.exists():
            stats.metrics["file_size_kb"] = self._cache_path.stat().st_size / 1024
            # Load...
            stats.items_processed = len(self._data)
        else:
            stats.items_skipped["no_cache"] = 1

        stats.sub_timings["load"] = (time.time() - t0) * 1000
        self.last_stats = stats

        logger.debug("cache_loaded", **stats.to_log_context())

    def save(self):
        stats = ComponentStats()
        t0 = time.time()

        # Save...
        stats.items_processed = len(self._data)
        stats.metrics["file_size_kb"] = self._cache_path.stat().st_size / 1024
        stats.sub_timings["save"] = (time.time() - t0) * 1000

        self.last_stats = stats
        logger.debug("cache_saved", **stats.to_log_context())
```

#### 2.4 Asset Pipeline

```python
class AssetOrchestrator:
    last_stats: ComponentStats | None = None

    def process(self, ...):
        stats = ComponentStats()

        assets = list(self._discover_assets())
        stats.items_total = len(assets)

        for asset in assets:
            if self._is_cached(asset):
                stats.cache_hits += 1
                stats.items_skipped["cached"] += 1
                continue

            stats.cache_misses += 1
            stats.items_processed += 1

            # Process asset...

        stats.metrics["css_bundles"] = self._css_bundle_count
        stats.metrics["js_bundles"] = self._js_bundle_count

        self.last_stats = stats
```

### 3. CLI Output Improvements

#### 3.1 Slow Operation Diagnostics

When any phase exceeds threshold, show stats:

```python
# bengal/orchestration/build/finalization.py

def _show_phase_stats(phase_name: str, duration_ms: float, component: HasStats | None):
    """Show stats for slow phases."""
    SLOW_THRESHOLD_MS = 1000

    if duration_ms > SLOW_THRESHOLD_MS and component and component.last_stats:
        cli.info(f"   📊 {phase_name}: {component.last_stats.format_summary()}")
```

#### 3.2 Verbose Mode Enhancement

In verbose mode, always show stats:

```python
if verbose:
    for phase, component in phases_with_stats:
        if component.last_stats:
            cli.info(f"   📊 {phase}: {component.last_stats.format_summary()}")
```

#### 3.3 Build Summary Stats

At end of build, show aggregate stats:

```
📊 Build Statistics:
   ├─ Discovery: 450 pages (12ms, 100% cache hit)
   ├─ Rendering: 450 pages (1.2s, 380 pages/sec)
   ├─ Assets: 110 files (250ms, 45 cached)
   └─ Health: 3 validators (880ms)
       ├─ Directives: 115 checked, 433 skipped (autodoc)
       ├─ Links: 2,340 checked, 100% cache hit
       └─ Output: 450 files verified
```

### 4. Structured Logging Integration

All stats automatically log at DEBUG level:

```python
# When component completes
logger.debug(
    f"{component_name}_complete",
    **stats.to_log_context()
)

# Output in .bengal/build.log:
{"timestamp": "...", "event": "directive_validator_complete",
 "items_total": 776, "items_processed": 115, "skipped_autodoc": 433,
 "cache_hits": 115, "cache_misses": 0, "timing_analyze_ms": 64,
 "timing_rendering_ms": 800}
```

### 5. Metrics Export (Optional)

For CI/CD integration:

```python
# bengal/utils/metrics.py

def export_build_metrics(stats: BuildStats, output_path: Path):
    """Export metrics for CI/CD dashboards."""
    metrics = {
        "build_duration_ms": stats.total_time_ms,
        "pages_rendered": stats.pages_rendered,
        "cache_hit_rate": stats.cache_hit_rate,
        "health_check_duration_ms": stats.health_check_time_ms,
        # Component-specific
        "discovery_cache_hits": stats.discovery_stats.cache_hits,
        "directive_validator_cache_hits": stats.directive_stats.cache_hits,
        # ...
    }

    output_path.write_text(json.dumps(metrics, indent=2))
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1-2 hours)

1. Create `bengal/utils/observability.py` with `ComponentStats` and `HasStats`
2. Update `ValidatorStats` to inherit from `ComponentStats`
3. Add stats collection to `ValidatorReport`

### Phase 2: Health Validators (2-3 hours)

1. Add stats to `LinkValidator`
2. Add stats to `OutputValidator`
3. Add stats to remaining validators (Config, Navigation, etc.)
4. Update CLI output in `finalization.py`

### Phase 3: Discovery & Rendering (2-3 hours)

1. Add stats to `ContentDiscovery`
2. Add stats to `AssetOrchestrator`
3. Add stats to `RenderOrchestrator`
4. Update build phases to collect and display stats

### Phase 4: Cache Layer (1-2 hours)

1. Add stats to `BuildCache` (update `get_stats()` to return `ComponentStats`)
2. Add stats to `CacheStore`
3. Track compression stats
4. Log cache effectiveness

### Phase 5: CLI & Export (1-2 hours)

1. Add build summary stats display
2. Add `--metrics` flag to export JSON
3. Update verbose mode output
4. Add `.bengal/metrics.json` for CI

---

## Success Criteria

1. **Any slow phase immediately shows diagnostic stats** in CLI
2. **Cache effectiveness visible** without code changes
3. **Skip reasons enumerated** for debugging
4. **Sub-timings available** for bottleneck identification
5. **Structured logs** contain all stats for post-hoc analysis
6. **CI can track metrics** over time via JSON export

---

## Alternatives Considered

### 1. OpenTelemetry Integration

**Pros**: Industry standard, rich tooling  
**Cons**: Heavy dependency, overkill for SSG  
**Decision**: Defer until needed; current approach is lighter

### 2. Prometheus Metrics

**Pros**: Time-series, alerting  
**Cons**: Requires external infrastructure  
**Decision**: Add optional export format, not native integration

### 3. Per-File Logging

**Pros**: Maximum granularity  
**Cons**: Log file size explosion, noise  
**Decision**: Aggregate stats with DEBUG-level file details

---

## Testing Strategy

1. **Unit tests**: Verify `ComponentStats` formatting and calculations
2. **Integration tests**: Verify stats are collected during builds
3. **CLI tests**: Verify output format in verbose/slow modes
4. **Performance tests**: Ensure stats collection < 1% overhead

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stats collection overhead | Build slowdown | Lazy collection, skip in quiet mode |
| Log file size growth | Disk usage | Aggregate stats, not per-item |
| Breaking changes to ValidatorReport | Test failures | Backward-compatible optional field |

---

## References

- `bengal/health/report.py:ValidatorStats` - Current implementation
- `bengal/health/validators/directives/__init__.py` - Example usage
- `bengal/utils/logger.py` - Structured logging system
- `plan/implemented/rfc-build-integrated-validation.md` - Related optimization

---

## Appendix: Example Debug Session (Future State)

```bash
$ bengal build --verbose

✓ Discovery 95ms
   📊 Discovery: processed=450/453 | skipped=[draft=3] | cache=450/450 (100%)

✓ Assets 250ms
   📊 Assets: processed=45/110 | skipped=[cached=65] | timings=[css=180ms, copy=70ms]

✓ Rendering 1.2s
   📊 Rendering: processed=450/450 | timings=[template=800ms, markdown=400ms] | metrics=[pages_per_sec=375]

✓ Health check 880ms
   📊 Directives: processed=115/776 | skipped=[no_path=228, autodoc=433] | cache=115/115 (100%)
   📊 Links: processed=450/450 | cache=2340/2400 (98%)
   📊 Output: processed=450/450

📊 Build Complete: 2.4s total
   Cache effectiveness: 98% hit rate
   Throughput: 187 pages/sec
```

When something goes wrong:

```bash
$ bengal build

✓ Health check 7619ms
   🐌 Slowest: Directives: 7554ms
   📊 Directives: processed=0/776 | skipped=[autodoc=776] | cache=0/0 (0%) | timings=[analyze=64ms, rendering=7490ms]
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                  IMMEDIATELY VISIBLE: All pages skipped, no cache, rendering is bottleneck
```
