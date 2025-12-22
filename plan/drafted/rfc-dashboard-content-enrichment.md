# RFC: Dashboard Content Enrichment

**Status**: Draft → Evaluated  
**Created**: 2024-12-21  
**Updated**: 2024-12-21  
**Depends On**: Terminal UX with Textual (implemented)  
**Estimated Time**: 3.5 days  
**Confidence**: 88% 🟢

---

## Summary

The Textual dashboard infrastructure is complete, but panels are sparse and low-information. This RFC proposes enriching dashboard content with real-time stats, meaningful visualizations, and actionable information to make the dashboards genuinely useful.

---

## Problem Statement

Current dashboard state:

| Dashboard | Issue | Evidence |
|-----------|-------|----------|
| **Build** | Phase table works, but no build profiling or cache stats | `build.py:139-142` |
| **Serve** | Sparkline empty until rebuilds; Stats tab is placeholder | `serve.py:167-168`, `screens.py:140` |
| **Health** | Shows demo mode; needs richer issue categorization | `health.py:189-201` |
| **All** | Large empty spaces; panels lack actionable content | Visual inspection |

Users see mostly empty panels on first launch, which makes the dashboards feel unfinished.

---

## Goals

1. **Immediate value** - Show useful info even when idle
2. **Progressive detail** - More info appears as activity happens
3. **Actionable insights** - Help users understand what to do next
4. **Performance visibility** - Surface build times, cache hits, memory

---

## Non-Goals

- Major UI redesign (infrastructure is solid)
- Adding new widgets or screens
- Changing keyboard shortcuts
- Breaking existing functionality
- Complex memory profiling (adds overhead)

---

## Proposed Changes

### Phase 1: Build Dashboard Enrichment (1 day)

#### 1.1 Add Build Statistics Panel

Replace empty space with real stats using Textual `Static` widget with Rich markup:

```
┌─ Build Statistics ─────────────────┐
│ Pages:      142  │  Cache Hits: 89%│
│ Assets:      47  │  Memory: 128 MB │
│ Templates:   12  │  Threads: 4     │
│ Last Build: 1.2s │  Incremental: ✓ │
└────────────────────────────────────┘
```

**Implementation**:

```python
# bengal/cli/dashboard/build.py

def _get_build_stats_panel(self) -> str:
    """Generate build stats panel content."""
    stats = self.stats or {}

    # Cache hit rate calculation
    hits = stats.get("cache_hits", 0)
    misses = stats.get("cache_misses", 0)
    total = hits + misses
    hit_rate = f"{(hits / total * 100):.0f}%" if total > 0 else "N/A"

    # Memory from BuildStats (already tracked, no tracemalloc overhead)
    memory_mb = stats.get("memory_rss_mb", 0)

    return f"""[bold]Pages:[/] {stats.get('total_pages', 0):>6}  │  [bold]Cache:[/] {hit_rate}
[bold]Assets:[/] {stats.get('total_assets', 0):>5}  │  [bold]Memory:[/] {memory_mb:.0f} MB
[bold]Sections:[/] {stats.get('total_sections', 0):>3}  │  [bold]Mode:[/] {'Incremental' if stats.get('incremental') else 'Full'}"""
```

**Source data** (all verified to exist):
- `BuildStats.total_pages` - `orchestration/stats/models.py:50`
- `BuildStats.total_assets` - `orchestration/stats/models.py:56`
- `BuildStats.cache_hits` / `cache_misses` - `orchestration/stats/models.py:82-83`
- `BuildStats.memory_rss_mb` - `orchestration/stats/models.py:77` (uses `psutil`, not `tracemalloc`)

#### 1.2 Add Phase Profiling

Show time breakdown per phase using `DataTable`:

```
Phase          Time    %  
─────────────────────────────
Discovery      120ms   10%  ████
Taxonomies      80ms    7%  ███
Rendering      800ms   67%  ██████████████████████████
Assets         150ms   13%  █████
Postprocess     50ms    4%  ██
```

**Source data** (verified):
- `BuildStats.discovery_time_ms` - `orchestration/stats/models.py:69`
- `BuildStats.taxonomy_time_ms` - `orchestration/stats/models.py:70`
- `BuildStats.rendering_time_ms` - `orchestration/stats/models.py:71`
- `BuildStats.assets_time_ms` - `orchestration/stats/models.py:72`
- `BuildStats.postprocess_time_ms` - `orchestration/stats/models.py:73`

#### 1.3 Pre-populate Phase Table

Show expected phases before build starts (not empty):

```
Status  Phase        Time    Details
─────────────────────────────────────
·       Discovery    -       Waiting...
·       Taxonomies   -       Waiting...
·       Rendering    -       Waiting...
·       Assets       -       Waiting...
·       Postprocess  -       Waiting...
```

**Implementation**: Extend existing `on_mount()` in `build.py` to pre-populate rows.

---

### Phase 2: Serve Dashboard Enrichment (1 day)

#### 2.1 Rich Stats Tab Content

Replace placeholder with real server stats:

```
┌─ Server Statistics ────────────────┐
│ Uptime:        5m 32s              │
│ Requests:      47                  │
│ Rebuilds:      3                   │
│ Avg Build:     342ms               │
│                                    │
│ Watched Files: 156                 │
│ Content:       89 (.md)            │
│ Templates:     23 (.html)          │
│ Assets:        44 (css/js/img)     │
└────────────────────────────────────┘
```

**Implementation** - Add uptime tracking:

```python
# bengal/cli/dashboard/serve.py

def __init__(self, ...):
    super().__init__()
    self._start_time = time.time()  # NEW: Track server start
    # ... existing init

@property
def uptime_str(self) -> str:
    """Format uptime as human-readable string."""
    elapsed = time.time() - self._start_time
    minutes, seconds = divmod(int(elapsed), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
```

#### 2.2 Sparkline with Initial Data

Pre-populate sparkline with zeros so it's not blank:

```python
# Initialize with placeholder data in __init__
self.build_history: list[float] = [0.0] * 10  # Shows a flat line initially

# In compose()
yield Sparkline(self.build_history, id="build-sparkline")
```

Update with real build times as they occur via message handlers.

#### 2.3 File Watcher Details

Show what's being watched in Changes tab:

```
✓ Watching 156 files in 12 directories
  content/  (89 files)
  layouts/  (23 files)
  assets/   (44 files)

─── Recent Changes ──────────────────
→ 10:42:15  content/posts/new.md (modified)
→ 10:42:16  Rebuilt in 342ms (142 pages)
```

**Source data**: Use `site.pages`, `site.assets` counts; `watchfiles` doesn't expose file counts directly, so track via discovery.

---

### Phase 3: Health Dashboard Enrichment (1 day)

#### 3.1 Multi-Category Health Checks

Expand beyond just links using **existing validators**:

```
Health Report
├─ 🔗 Links (2 issues)
│  ├─ ⛔ /about → 404 (broken)
│  └─ ⚠️ /old-page → 301 (redirect)
├─ 📄 Output (1 issue)  
│  └─ ⚠️ 2 pages >500KB
├─ 🖼️ Assets (0 issues)
│  └─ ✓ All 47 assets valid
├─ ⚡ Performance (1 issue)
│  └─ ⚠️ Build slower than expected
└─ 🧭 Navigation (0 issues)
   └─ ✓ All pages have proper nav
```

**Source data** (verified validators from `health/validators/__init__.py`):

| Category | Validator | Module |
|----------|-----------|--------|
| Links | `LinkValidator` | `validators/links.py` |
| Output | `OutputValidator` | `validators/output.py` (page sizes) |
| Assets | `AssetValidator` | `validators/assets.py` |
| Performance | `PerformanceValidator` | `validators/performance.py` |
| Navigation | `NavigationValidator` | `validators/navigation.py` |
| Config | `ConfigValidatorWrapper` | `validators/config.py` |

**Note**: RFC previously mentioned `FrontmatterValidator` and `ImageValidator` which don't exist. Use actual validators above.

#### 3.2 Issue Details Panel

When selecting an issue, show rich details:

```
┌─ Issue Details ────────────────────┐
│ Type:     Broken Link              │
│ Severity: Error                    │
│ Source:   content/about.md:42      │
│ Target:   /old-page                │
│ Status:   404 Not Found            │
│                                    │
│ Suggestion:                        │
│ Update link or create redirect     │
│                                    │
│ [Press Enter to open file]         │
└────────────────────────────────────┘
```

**Implementation**: Already partially exists in `health.py:364-387`. Extend `_show_issue_details()` to include `recommendation` from `CheckResult`.

#### 3.3 Summary Statistics

Show aggregate health score:

```
Site Health: 94% ██████████████████░░
  142 pages checked
  47 assets verified
  2 issues found (1 error, 1 warning)
```

**Implementation**:

```python
def _calculate_health_score(self) -> int:
    """Calculate health score 0-100."""
    if not self.issues:
        return 100

    error_weight = 10  # Errors cost 10 points each
    warning_weight = 2  # Warnings cost 2 points each

    errors = sum(1 for i in self.issues if i.severity == "error")
    warnings = sum(1 for i in self.issues if i.severity == "warning")

    penalty = (errors * error_weight) + (warnings * warning_weight)
    return max(0, 100 - penalty)
```

---

### Phase 4: Cross-Dashboard Polish (0.5 days)

#### 4.1 Loading States

Show activity indicators while data loads:

```
┌─ Build Statistics ─────────────────┐
│         Loading...                 │
│         ████████░░░░ 60%           │
└────────────────────────────────────┘
```

**Implementation**: Use Textual's `LoadingIndicator` widget or custom `Static` with spinner.

#### 4.2 Empty State Messages

When no data, show helpful message instead of blank:

```
┌─ Build History ────────────────────┐
│                                    │
│  No builds yet.                    │
│  Press 'r' to start a build.       │
│                                    │
└────────────────────────────────────┘
```

#### 4.3 Keyboard Hints

Add contextual hints in footer (already using Textual's `Footer` with `Binding`):

```
[r] Rebuild  [o] Open Browser  [c] Clear  [?] Help  [q] Quit
```

---

## Implementation Plan

| Phase | Tasks | Days | Dependencies |
|-------|-------|------|--------------|
| 1 | Build stats, profiling, phase pre-pop | 1 | None |
| 2 | Serve stats, sparkline init, watcher | 1 | None |
| 3 | Health categories, details, score | 1 | Validator interfaces |
| 4 | Loading states, empty states, hints | 0.5 | Phases 1-3 |
| **Total** | | **3.5** | |

**Phases 1-2 can run in parallel.**

---

## Data Sources

### Build Dashboard

| Data | Source | Location |
|------|--------|----------|
| Page count | `BuildStats.total_pages` | `orchestration/stats/models.py:50` |
| Asset count | `BuildStats.total_assets` | `orchestration/stats/models.py:56` |
| Cache hit rate | `BuildStats.cache_hits` / `cache_misses` | `orchestration/stats/models.py:82-83` |
| Phase times | `BuildStats.*_time_ms` | `orchestration/stats/models.py:69-74` |
| Memory usage | `BuildStats.memory_rss_mb` | `orchestration/stats/models.py:77` |

### Serve Dashboard

| Data | Source | Location |
|------|--------|----------|
| Uptime | `time.time() - self._start_time` | NEW (trivial) |
| Build times | `build_history: list[float]` | Already tracked |
| Watched files | `site.pages` + `site.assets` counts | Existing |
| Rebuild count | `self.rebuild_count` | Already reactive |

### Health Dashboard

| Data | Source | Location |
|------|--------|----------|
| Link issues | `LinkValidator` | `validators/links.py` |
| Output/size issues | `OutputValidator` | `validators/output.py` |
| Asset issues | `AssetValidator` | `validators/assets.py` |
| Performance issues | `PerformanceValidator` | `validators/performance.py` |
| Navigation issues | `NavigationValidator` | `validators/navigation.py` |

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cli/dashboard/test_build_stats.py

def test_cache_hit_rate_calculation():
    """Cache hit rate calculates correctly."""
    stats = {"cache_hits": 89, "cache_misses": 11}
    assert calculate_cache_hit_rate(stats) == 89.0

def test_cache_hit_rate_no_data():
    """Returns N/A when no cache data."""
    assert calculate_cache_hit_rate({}) == "N/A"

def test_phase_percentage():
    """Phase percentages sum to 100%."""
    phases = extract_phase_percentages(stats)
    assert sum(phases.values()) == pytest.approx(100.0)
```

```python
# tests/unit/cli/dashboard/test_health_score.py

def test_health_score_no_issues():
    """Perfect score with no issues."""
    assert calculate_health_score([]) == 100

def test_health_score_with_errors():
    """Errors reduce score significantly."""
    issues = [HealthIssue(severity="error", ...)]
    assert calculate_health_score(issues) == 90  # 100 - 10

def test_health_score_floor():
    """Score never goes below 0."""
    issues = [HealthIssue(severity="error", ...) for _ in range(20)]
    assert calculate_health_score(issues) == 0
```

### Integration Tests

```python
# tests/integration/cli/dashboard/test_dashboards.py

def test_build_dashboard_shows_stats(test_site):
    """Build dashboard displays real stats after build."""
    async with BengalBuildDashboard(site=test_site).run_test() as pilot:
        # Trigger build
        await pilot.press("r")
        await pilot.pause()

        # Verify stats panel has content
        stats = pilot.app.query_one("#build-stats", Static)
        assert "Pages:" in stats.renderable
        assert "Cache:" in stats.renderable

def test_health_dashboard_categories(test_site_with_issues):
    """Health dashboard shows categorized issues."""
    async with BengalHealthDashboard(site=test_site_with_issues).run_test() as pilot:
        tree = pilot.app.query_one("#health-tree", Tree)
        # Verify categories exist
        assert any("Links" in str(node.label) for node in tree.root.children)
```

### Edge Case Tests

```python
def test_empty_site():
    """Dashboards handle empty sites gracefully."""

def test_large_site():
    """Dashboards remain responsive with 10k+ pages."""

def test_error_during_build():
    """Dashboard shows error state, not crash."""
```

---

## Migration

No breaking changes. All enhancements are additive.

Existing functionality:
- `--dashboard` flags continue to work
- Keyboard shortcuts unchanged
- CSS styling preserved

---

## Success Criteria

1. ✅ No blank panels on dashboard launch
2. ✅ Useful info visible within 1 second
3. ✅ All stats backed by real data (not placeholder)
4. ✅ Empty states guide users on next action
5. ✅ Existing tests continue to pass
6. ✅ New unit tests for data extraction functions
7. ✅ No measurable performance regression

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead | Low | Medium | Use existing `BuildStats`; no additional `tracemalloc` |
| Data not available | Medium | Low | Graceful fallback to "N/A" |
| Validator interface mismatch | Low | Medium | All validators return `list[CheckResult]` |
| UI clutter | Low | Low | Use progressive disclosure; collapsible panels |

---

## Alternatives Considered

1. **Defer indefinitely** - Ship as-is, enhance later
   - Rejected: Dashboards feel incomplete

2. **Add more widgets** - New panels, modes
   - Rejected: Infrastructure is fine, needs content

3. **Rich integration** - Use Rich panels alongside Textual
   - Rejected: Stick with pure Textual for consistency

4. **Use tracemalloc for memory** - More accurate heap tracking
   - Rejected: Adds ~5-10% overhead; `psutil.rss` is sufficient and already tracked

---

## Textual Widgets Used

| Widget | Usage | Reference |
|--------|-------|-----------|
| `Static` | Stats panels, labels | [Textual Static](https://textual.textualize.io/reference/#widgets-static) |
| `DataTable` | Phase timing, stats tables | [Textual DataTable](https://textual.textualize.io/reference/#widgets-datatable) |
| `Sparkline` | Build history | [Textual Sparkline](https://textual.textualize.io/reference/#widgets-sparkline) |
| `Tree` | Health issue hierarchy | [Textual Tree](https://textual.textualize.io/reference/#widgets-tree) |
| `ProgressBar` | Loading states | [Textual ProgressBar](https://textual.textualize.io/reference/#widgets-progressbar) |
| `TabbedContent` | Stats/Changes/Errors | [Textual TabbedContent](https://textual.textualize.io/reference/#widgets-tabbedcontent) |
| `Log` | File changes, errors | [Textual Log](https://textual.textualize.io/reference/#widgets-log) |
| `Footer` | Keyboard hints | [Textual Footer](https://textual.textualize.io/reference/#widgets-footer) |

---

## References

- [Terminal UX RFC](rfc-terminal-ux-style-guide.md) - Design system
- [Terminal UX Plan](plan-terminal-ux-textual.md) - Infrastructure plan
- [Textual Reference](https://textual.textualize.io/reference/) - Widget reference
- [BuildStats model](../../bengal/orchestration/stats/models.py) - Build statistics
- [Health validators](../../bengal/health/validators/__init__.py) - Available validators
