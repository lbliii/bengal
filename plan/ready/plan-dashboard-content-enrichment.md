# Plan: Dashboard Content Enrichment

**Status**: Ready  
**RFC**: [rfc-dashboard-content-enrichment.md](rfc-dashboard-content-enrichment.md)  
**Created**: 2024-12-21  
**Estimated Time**: 3.5 days  
**Confidence**: 88% 🟢

---

## Summary

Convert RFC for dashboard content enrichment into actionable tasks. Enriches Build, Serve, and Health dashboards with real-time stats, meaningful visualizations, and actionable content.

---

## Prerequisites

- [x] Terminal UX with Textual (implemented)
- [x] Dashboard infrastructure complete (`bengal/cli/dashboard/`)
- [x] BuildStats model with all required fields (`orchestration/stats/models.py`)
- [x] Health validators exist (`health/validators/`)

---

## Phase 1: Build Dashboard Enrichment (1 day)

### Task 1.1: Add Build Statistics Panel

**File**: `bengal/cli/dashboard/build.py`

**What**: Add a `Static` widget showing build stats (pages, assets, cache hit rate, memory, mode)

**Implementation**:
1. Add `_get_build_stats_content()` method to generate Rich markup stats
2. Add `Static` widget with id `build-stats` in `compose()`
3. Update stats on `BuildComplete` message

**Data sources** (verified):
- `BuildStats.total_pages` (`orchestration/stats/models.py:50`)
- `BuildStats.total_assets` (`orchestration/stats/models.py:56`)
- `BuildStats.cache_hits/cache_misses` (`orchestration/stats/models.py:82-83`)
- `BuildStats.memory_rss_mb` (`orchestration/stats/models.py:77`)
- `BuildStats.incremental` (`orchestration/stats/models.py:61`)

**Tests**:
- `tests/unit/cli/dashboard/test_build_stats.py`

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/build): add build statistics panel with cache hit rate, memory, and mode indicators"
```

---

### Task 1.2: Add Phase Profiling Table

**File**: `bengal/cli/dashboard/build.py`

**What**: Show time breakdown per phase with percentage bars

**Implementation**:
1. Add columns "%" and visual bar to phase table
2. Calculate percentage from phase times
3. Update `_update_phase_complete()` to include percentage/bar

**Data sources** (verified):
- `BuildStats.discovery_time_ms` (`orchestration/stats/models.py:69`)
- `BuildStats.taxonomy_time_ms` (`orchestration/stats/models.py:70`)
- `BuildStats.rendering_time_ms` (`orchestration/stats/models.py:71`)
- `BuildStats.assets_time_ms` (`orchestration/stats/models.py:72`)
- `BuildStats.postprocess_time_ms` (`orchestration/stats/models.py:73`)

**Tests**:
- `tests/unit/cli/dashboard/test_phase_profiling.py`

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/build): add phase profiling with percentage bars and time breakdown"
```

---

### Task 1.3: Pre-populate Phase Table on Mount

**File**: `bengal/cli/dashboard/build.py`

**What**: Show expected phases with "Waiting..." status before build starts (not empty)

**Implementation**:
1. Already implemented in `on_mount()` (lines 151-165)
2. Update initial status text from "·" to "○" for visual distinction
3. Add "Waiting..." as initial details column value

**Tests**:
- Verify phase table has rows on mount before build starts

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/build): improve phase table pre-population with waiting state indicators"
```

---

## Phase 2: Serve Dashboard Enrichment (1 day)

### Task 2.1: Add Rich Stats Tab Content

**File**: `bengal/cli/dashboard/serve.py`

**What**: Replace placeholder stats table with real server statistics

**Implementation**:
1. Add `_start_time` tracking in `__init__()` (line 129)
2. Add `uptime_str` property for human-readable uptime
3. Update stats table rows with real data:
   - Uptime: calculated from `_start_time`
   - Requests: new counter (optional, via server integration)
   - Rebuilds: already tracked (`rebuild_count`)
   - Avg Build: calculated from `build_history`
   - Watched Files: from site.pages + site.assets counts
   - File breakdown: content/templates/assets

**Tests**:
- `tests/unit/cli/dashboard/test_serve_stats.py`

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/serve): add rich stats tab with uptime, rebuild count, and file watcher breakdown"
```

---

### Task 2.2: Initialize Sparkline with Placeholder Data

**File**: `bengal/cli/dashboard/serve.py`

**What**: Pre-populate sparkline so it's not blank on launch

**Implementation**:
1. Initialize `build_history` with zeros in `__init__()` (line 138 already has `[]`)
2. Change to: `self.build_history: list[float] = [0.0] * 10`
3. Sparkline shows flat line initially, updates with real data on rebuilds

**Evidence**: Current code at line 138: `self.build_history: list[float] = []`

**Tests**:
- Verify sparkline has data on mount

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/serve): initialize sparkline with placeholder data for immediate visual feedback"
```

---

### Task 2.3: Add File Watcher Details to Changes Tab

**File**: `bengal/cli/dashboard/serve.py`

**What**: Show watched file summary at top of Changes tab

**Implementation**:
1. Add `_get_watcher_summary()` method
2. Update Changes tab header with watched file counts
3. Add site.pages count, site.assets count breakdown
4. Update on `WatcherStatus` message

**Tests**:
- Verify file watcher summary displays on Changes tab

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/serve): add file watcher summary to changes tab with content/template/asset breakdown"
```

---

## Phase 3: Health Dashboard Enrichment (1 day)

### Task 3.1: Implement Multi-Category Health Checks

**File**: `bengal/cli/dashboard/health.py`

**What**: Expand tree to show categories for all validator types

**Implementation**:
1. Update `_populate_from_report()` to create category nodes for each validator type
2. Map validators to categories:
   - 🔗 Links: `LinkValidator` (`validators/links.py`)
   - 📄 Output: `OutputValidator` (`validators/output.py`)
   - 🖼️ Assets: `AssetValidator` (`validators/assets.py`)
   - ⚡ Performance: `PerformanceValidator` (`validators/performance.py`)
   - 🧭 Navigation: `NavigationValidator` (`validators/navigation.py`)
   - ⚙️ Config: `ConfigValidatorWrapper` (`validators/config.py`)
3. Show issue count per category in tree node label

**Evidence**: Validators exist at `bengal/health/validators/__init__.py`

**Tests**:
- `tests/unit/cli/dashboard/test_health_categories.py`

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/health): add multi-category health checks with validator-specific grouping"
```

---

### Task 3.2: Enrich Issue Details Panel

**File**: `bengal/cli/dashboard/health.py`

**What**: Extend `_show_issue_details()` to include recommendation from `CheckResult`

**Implementation**:
1. Current implementation at lines 364-387
2. Add `recommendation` field from `CheckResult` if available
3. Add "[Press Enter to open file]" hint
4. Format with Rich markup for better visual hierarchy

**Tests**:
- Verify details panel shows recommendation when available

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/health): enrich issue details panel with recommendations and file open hints"
```

---

### Task 3.3: Add Health Score Summary

**File**: `bengal/cli/dashboard/health.py`

**What**: Show aggregate health score with progress bar

**Implementation**:
1. Add `_calculate_health_score()` method:
   - 100 points base
   - -10 per error
   - -2 per warning
   - Floor at 0
2. Add health score display to summary bar
3. Use `ProgressBar` or ASCII bar to visualize

**Tests**:
- `tests/unit/cli/dashboard/test_health_score.py`

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard/health): add aggregate health score with visual progress bar"
```

---

## Phase 4: Cross-Dashboard Polish (0.5 days)

### Task 4.1: Add Loading States

**Files**: All dashboard files

**What**: Show loading indicator while data loads

**Implementation**:
1. Add `is_loading` reactive property
2. Show "Loading..." message or spinner in panels while loading
3. Update to real content when data available

**Tests**:
- Verify loading state displays during data fetch

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard): add loading states with visual indicators across all dashboards"
```

---

### Task 4.2: Add Empty State Messages

**Files**: All dashboard files

**What**: When no data, show helpful message instead of blank

**Implementation**:
1. Add empty state messages:
   - Build: "No builds yet. Press 'r' to start a build."
   - Serve: "No changes detected. Watching for file changes..."
   - Health: "No issues found. Site is healthy!"
2. Include keyboard hint for next action

**Tests**:
- Verify empty states display with helpful messages

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard): add helpful empty state messages with keyboard hints"
```

---

### Task 4.3: Verify Keyboard Hints in Footer

**Files**: All dashboard files

**What**: Ensure contextual keyboard hints in footer are complete

**Implementation**:
1. Verify all `Binding` entries have `show=True` for important actions
2. Add missing bindings if any
3. Ensure footer displays correctly with all hints

**Tests**:
- Verify footer shows all key bindings

**Commit**:
```bash
git add -A && git commit -m "cli(dashboard): verify and complete keyboard hints in dashboard footers"
```

---

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/unit/cli/dashboard/test_build_stats.py` | Stats panel content |
| `tests/unit/cli/dashboard/test_phase_profiling.py` | Phase percentages |
| `tests/unit/cli/dashboard/test_serve_stats.py` | Server stats |
| `tests/unit/cli/dashboard/test_health_categories.py` | Category grouping |
| `tests/unit/cli/dashboard/test_health_score.py` | Score calculation |

### Integration Tests

| Test File | Coverage |
|-----------|----------|
| `tests/integration/cli/dashboard/test_dashboards.py` | End-to-end dashboard behavior |

### Edge Cases

- [ ] Empty site (0 pages)
- [ ] Large site (>1000 pages)
- [ ] Build errors
- [ ] No health issues
- [ ] All validators with issues

---

## Execution Order

```
Phase 1 (1 day)           Phase 2 (1 day)           Phase 3 (1 day)
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ 1.1 Build Stats     │   │ 2.1 Serve Stats     │   │ 3.1 Health Categories│
│ 1.2 Phase Profiling │   │ 2.2 Sparkline Init  │   │ 3.2 Issue Details   │
│ 1.3 Phase Pre-pop   │   │ 2.3 Watcher Details │   │ 3.3 Health Score    │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
         │                          │                        │
         └──────────────────────────┴────────────────────────┘
                                    │
                          Phase 4 (0.5 days)
                    ┌─────────────────────┐
                    │ 4.1 Loading States  │
                    │ 4.2 Empty States    │
                    │ 4.3 Keyboard Hints  │
                    └─────────────────────┘
```

**Note**: Phases 1 and 2 can be executed in parallel.

---

## Success Criteria

- [ ] ✅ No blank panels on dashboard launch
- [ ] ✅ Useful info visible within 1 second
- [ ] ✅ All stats backed by real data (not placeholder)
- [ ] ✅ Empty states guide users on next action
- [ ] ✅ Existing tests continue to pass
- [ ] ✅ New unit tests for data extraction functions
- [ ] ✅ No measurable performance regression

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead | Low | Medium | Use existing `BuildStats`; no additional `tracemalloc` |
| Data not available | Medium | Low | Graceful fallback to "N/A" |
| Validator interface mismatch | Low | Medium | All validators return `list[CheckResult]` |
| UI clutter | Low | Low | Use progressive disclosure; collapsible panels |

---

## Quick Start

```bash
# Start with Phase 1, Task 1.1
# Open: bengal/cli/dashboard/build.py

# Verify BuildStats fields exist
grep -n "total_pages\|total_assets\|cache_hits\|memory_rss_mb" \
  bengal/orchestration/stats/models.py

# Run existing tests
pytest tests/unit/cli/dashboard/ -v

# Implement Task 1.1...
```
