# Plan: Dashboard Deep API Integration

**Status**: Draft  
**Created**: 2024-12-21  
**RFC**: [rfc-dashboard-api-integration.md](rfc-dashboard-api-integration.md)  
**Estimated Duration**: 4 days

---

## Executive Summary

Transform the Bengal dashboard from "shows some stats" to "comprehensive Bengal control panel" by integrating with all existing Bengal APIs (Site, Page, Section, Asset, BuildStats, HealthReport) and adding minimal middleware for streaming features.

**Strategy**: Ship dashboard improvements with existing APIs first (Phases 1, 2a, 4), then add streaming features (Phases 2b, 3) as enhancement.

---

## Prerequisites

- [ ] Terminal UX with Textual (implemented ✅)
- [ ] Toad-Inspired Enhancements (in progress)
- [ ] Dashboard Content Enrichment RFC (ready)

---

## Phase 1: Site Data Model Integration (Existing APIs)

**Goal**: Surface all Site data (pages, sections, assets, taxonomies) in browsable widgets  
**Effort**: 1 day  
**API Status**: ✅ All existing APIs—dashboard changes only

### Task 1.1: Rich Site Context Panel

**What**: Enhance landing screen with comprehensive site context  
**Where**: `bengal/cli/dashboard/screens.py` (LandingScreen)

**Changes**:
- [ ] Add `_get_rich_site_context()` method to LandingScreen
- [ ] Display: site title, theme, baseurl, output_dir
- [ ] Show page breakdown (published vs draft)
- [ ] Show asset breakdown by type (CSS, JS, images)
- [ ] Show taxonomy summary (term counts, page assignments)
- [ ] Show data files loaded
- [ ] Show last build time

**Data Sources**:
- `site.title`, `site.theme`, `site.baseurl`, `site.output_dir`
- `site.pages` → filter by `draft` property
- `site.assets` → group by `.suffix`
- `site.taxonomies` → term counts
- `site.data` → data file keys
- `site._last_build_stats` or stored stats

**Commit**: `cli(dashboard): add rich site context panel with page/asset/taxonomy breakdown`

---

### Task 1.2: Content Browser Widget

**What**: New widget for browsing pages by section hierarchy  
**Where**: New file `bengal/cli/dashboard/widgets/content_browser.py`

**Changes**:
- [ ] Create `ContentBrowser` widget extending Textual `Tree`
- [ ] Build tree from `site.sections` and `section.subsections`
- [ ] Display pages with: title, date, tags, draft status
- [ ] Add filtering: by tag, drafts only, date range
- [ ] Add keyboard bindings: Enter to open file, `t` filter by tag, `d` drafts only

**Data Sources**:
- `site.sections` → section hierarchy
- `section.pages` → pages in section
- `section.subsections` → child sections
- `page.title`, `page.date`, `page.tags`, `page.draft`

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_content_browser.py`
  - Test tree building from sections
  - Test draft filtering
  - Test tag filtering

**Commit**: `cli(dashboard): add ContentBrowser widget for section-based page navigation`

---

### Task 1.3: Asset Explorer Widget

**What**: New widget for browsing assets grouped by type with sizes  
**Where**: New file `bengal/cli/dashboard/widgets/asset_explorer.py`

**Changes**:
- [ ] Create `AssetExplorer` widget extending Textual `Tree`
- [ ] Group assets by extension (CSS, JS, images, etc.)
- [ ] Show file sizes (compute from `Path.stat().st_size`)
- [ ] Show total size per type and overall
- [ ] Add keyboard bindings: Enter to reveal in finder/open

**Data Sources**:
- `site.assets` → asset list
- `asset.source_path` → file path for size
- `asset.suffix` → extension for grouping

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_asset_explorer.py`
  - Test asset grouping by type
  - Test size calculation
  - Test empty asset list handling

**Commit**: `cli(dashboard): add AssetExplorer widget with type grouping and size display`

---

### Task 1.4: Integrate Widgets into Screens

**What**: Add new widgets to appropriate dashboard screens  
**Where**: `bengal/cli/dashboard/screens.py`

**Changes**:
- [ ] Add ContentBrowser to content-focused screen or new tab
- [ ] Add AssetExplorer to build/assets screen or new tab
- [ ] Wire up navigation between widgets
- [ ] Add CSS styling in `bengal.tcss`

**Commit**: `cli(dashboard): integrate ContentBrowser and AssetExplorer into dashboard screens`

---

## Phase 2a: BuildStats Deep Display (Existing APIs)

**Goal**: Display ALL 20+ BuildStats fields with visualizations  
**Effort**: 0.5 day  
**API Status**: ✅ Existing APIs—dashboard changes only

### Task 2.1: Full BuildStats Display

**What**: Show complete build statistics with all fields  
**Where**: `bengal/cli/dashboard/build.py`

**Changes**:
- [ ] Display page breakdown: total, regular, generated, tag pages, archive pages, pagination pages
- [ ] Display phase timing with visual bar chart:
  - discovery_time_ms, taxonomy_time_ms, rendering_time_ms, assets_time_ms, postprocess_time_ms
- [ ] Display cache performance: hits, misses, time_saved_ms
- [ ] Display memory: rss_mb, heap_mb, peak_mb
- [ ] Display directives: total_directives, directives_by_type
- [ ] Display errors: warnings, template_errors, errors_by_category

**Data Sources** (from `orchestration/stats/models.py`):
- `stats.total_pages`, `regular_pages`, `generated_pages`
- `stats.tag_pages`, `archive_pages`, `pagination_pages`
- `stats.discovery_time_ms`, `taxonomy_time_ms`, etc.
- `stats.cache_hits`, `cache_misses`, `time_saved_ms`
- `stats.memory_rss_mb`, `memory_heap_mb`, `memory_peak_mb`
- `stats.total_directives`, `directives_by_type`

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_build_stats_display.py`
  - Test all field rendering
  - Test phase bar chart calculations
  - Test cache percentage formatting

**Commit**: `cli(dashboard): display full BuildStats with phase timing, cache, memory, and directives`

---

## Phase 4: Health & Analysis Integration (Existing APIs)

**Goal**: Parse full HealthReport structure and add taxonomy/graph exploration  
**Effort**: 1 day  
**API Status**: ✅ Existing APIs—dashboard changes only

> **Note**: Phase 4 before Phases 2b/3 because it uses existing APIs

### Task 4.1: HealthReport Deep Integration

**What**: Parse and display full HealthReport structure with categories  
**Where**: `bengal/cli/dashboard/health.py`

**Changes**:
- [ ] Parse `HealthReport.results` list of `CheckResult`
- [ ] Group issues by category (Links, Performance, Assets, Navigation, Config, Taxonomy)
- [ ] Display status: SUCCESS, WARNING, ERROR with icons
- [ ] Show recommendations from `CheckResult.recommendation`
- [ ] Add expandable details from `CheckResult.details`
- [ ] Show file locations for issues
- [ ] Create `HealthTree` widget extending `Tree` for hierarchical display

**Data Sources**:
- `HealthReport.results` → list of `CheckResult`
- `CheckResult.status` → SUCCESS, WARNING, ERROR
- `CheckResult.message`, `recommendation`, `details`
- `CheckResult.validator` → source validator

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_health_tree.py`
  - Test issue categorization
  - Test status icon mapping
  - Test empty report handling

**Commit**: `cli(dashboard): add HealthTree widget with categorized issues and recommendations`

---

### Task 4.2: Taxonomy Explorer Widget

**What**: New widget for exploring taxonomies with term drill-down  
**Where**: New file `bengal/cli/dashboard/widgets/taxonomy_explorer.py`

**Changes**:
- [ ] Create `TaxonomyExplorer` widget extending `Tree`
- [ ] Display all taxonomies (tags, categories, etc.)
- [ ] Show term counts with visual bars
- [ ] Expand terms to show page list
- [ ] Add keyboard navigation to pages

**Data Sources**:
- `site.taxonomies` → dict of `{taxonomy_name: {term: [pages]}}`
- Term → page list mapping

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_taxonomy_explorer.py`
  - Test taxonomy tree building
  - Test page list under terms
  - Test empty taxonomies

**Commit**: `cli(dashboard): add TaxonomyExplorer widget with term drill-down and page lists`

---

### Task 4.3: GraphAnalyzer Integration

**What**: Surface link graph insights from GraphAnalyzer  
**Where**: New section in health or new tab

**Changes**:
- [ ] Call `GraphAnalyzer.analyze()` on site
- [ ] Display internal/external link counts
- [ ] Identify and list orphan pages (no incoming links)
- [ ] Show most-linked pages (top 5-10)
- [ ] Show basic graph statistics

**Data Sources**:
- `GraphAnalyzer.analyze()` → link analysis results
- Orphan pages detection
- Incoming link counts per page

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_graph_insights.py`
  - Test orphan page detection
  - Test link counting
  - Test empty graph handling

**Commit**: `cli(dashboard): add graph insights panel showing orphans and most-linked pages`

---

## Phase 2b: Build Phase Streaming (New Middleware)

**Goal**: Stream build phases in real-time instead of waiting for completion  
**Effort**: 0.5 day  
**API Status**: 🆕 Requires core changes (~2 hours)

### Task 2.2: Add Phase Callbacks to BuildOrchestrator

**What**: Add optional callbacks for phase start/complete  
**Where**: `bengal/orchestration/build/__init__.py`

**Changes**:
- [ ] Add `on_phase_start: Callable[[str], None] | None = None` parameter
- [ ] Add `on_phase_complete: Callable[[str, float, str], None] | None = None` parameter
- [ ] Call callbacks within each `with self.logger.phase("name"):` block
- [ ] Ensure callbacks are optional (None default) for backward compatibility

**Signature**:
```python
def build(
    self,
    options: BuildOptions | None = None,
    *,
    on_phase_start: Callable[[str], None] | None = None,
    on_phase_complete: Callable[[str, float, str], None] | None = None,
) -> BuildStats:
```

**Tests**:
- [ ] `tests/unit/orchestration/test_build_callbacks.py`
  - Test callbacks are called for each phase
  - Test None callbacks don't break build
  - Test callback arguments (phase name, time, details)

**Commit**: `orchestration(build): add optional phase callbacks for streaming progress`

---

### Task 2.3: PhaseProgress Widget

**What**: New widget showing streaming build progress  
**Where**: New file `bengal/cli/dashboard/widgets/phase_progress.py`

**Changes**:
- [ ] Create `PhaseProgress` widget with phase list
- [ ] Show phase status: pending (·), running (●), complete (✓)
- [ ] Display phase timing and details
- [ ] Show progress bar for rendering phase (pages rendered/total)
- [ ] Update in real-time via Textual `worker`

**Integration**:
- [ ] Update build worker in `build.py` to use phase callbacks
- [ ] Pass callbacks to `BuildOrchestrator.build()`
- [ ] Use `call_from_thread` for safe Textual updates

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_phase_progress.py`
  - Test phase status transitions
  - Test timing display
  - Test progress bar accuracy

**Commit**: `cli(dashboard): add PhaseProgress widget with real-time build streaming`

---

## Phase 3: DevServer Integration (New Middleware)

**Goal**: Show file watcher events and HTTP requests in dashboard  
**Effort**: 1 day  
**API Status**: 🆕 Requires core changes (~2 hours)

### Task 3.1: Add File Change Callback to WatcherRunner

**What**: Add callback for file change events  
**Where**: `bengal/server/watcher_runner.py`

**Changes**:
- [ ] Add `on_file_change: Callable[[set[Path], set[str]], None] | None = None` parameter
- [ ] Call callback in `_run_build_trigger` with paths and event types
- [ ] Event types: `{"created", "modified", "deleted"}`
- [ ] Ensure callback is optional for backward compatibility

**Signature**:
```python
class WatcherRunner:
    def __init__(
        self,
        # ... existing params ...
        on_file_change: Callable[[set[Path], set[str]], None] | None = None,
    ):
```

**Tests**:
- [ ] `tests/unit/server/test_watcher_callbacks.py`
  - Test callback called on file change
  - Test event types passed correctly
  - Test None callback doesn't break watcher

**Commit**: `server(watcher): add optional file change callback for dashboard integration`

---

### Task 3.2: FileWatcherLog Widget

**What**: New widget showing file change stream  
**Where**: New file `bengal/cli/dashboard/widgets/file_watcher_log.py`

**Changes**:
- [ ] Create `FileWatcherLog` widget extending `Log`
- [ ] Display: timestamp, event icon (✏️ modified, ➕ created, ➖ deleted), file path
- [ ] Show rebuild trigger messages
- [ ] Show build completion with time
- [ ] Keep last N entries (configurable, default 50)

**Integration**:
- [ ] Wire up callback from WatcherRunner to widget
- [ ] Handle threading safely with Textual

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_file_watcher_log.py`
  - Test event formatting
  - Test log rotation (max entries)
  - Test empty log display

**Commit**: `cli(dashboard): add FileWatcherLog widget with real-time file change stream`

---

### Task 3.3: Add Request Logging to Handler

**What**: Add HTTP request logging capability  
**Where**: `bengal/server/request_handler.py`

**Changes**:
- [ ] Create `RequestLogEntry` dataclass (timestamp, method, path, status, duration_ms)
- [ ] Add class-level `on_request: Callable[[RequestLogEntry], None] | None = None`
- [ ] Call callback in `do_GET` with timing
- [ ] Keep optional request_log list for history (optional)

**Dataclass**:
```python
@dataclass
class RequestLogEntry:
    timestamp: datetime
    method: str
    path: str
    status: int
    duration_ms: float
```

**Tests**:
- [ ] `tests/unit/server/test_request_logging.py`
  - Test log entry creation
  - Test callback invocation
  - Test timing accuracy

**Commit**: `server(handler): add request logging with callback for dashboard`

---

### Task 3.4: RequestLog Widget

**What**: New widget showing HTTP request stream  
**Where**: New file `bengal/cli/dashboard/widgets/request_log.py`

**Changes**:
- [ ] Create `RequestLog` widget extending `Log`
- [ ] Display: timestamp, method, path, status code, duration
- [ ] Highlight 404s and errors with ⚠️
- [ ] Keep last N entries (configurable, default 100)

**Integration**:
- [ ] Wire up callback from BengalRequestHandler
- [ ] Handle threading safely

**Tests**:
- [ ] `tests/unit/cli/dashboard/test_request_log.py`
  - Test request formatting
  - Test error highlighting
  - Test log rotation

**Commit**: `cli(dashboard): add RequestLog widget with live HTTP request stream`

---

## Phase 5: Integration & Polish

**Goal**: Integrate all widgets, add navigation, polish UX  
**Effort**: 0.5 day

### Task 5.1: Screen Organization

**What**: Organize widgets into logical screens/tabs  
**Where**: `bengal/cli/dashboard/screens.py`, `bengal.tcss`

**Changes**:
- [ ] Add new tabs/screens for:
  - Content (ContentBrowser, TaxonomyExplorer)
  - Build (PhaseProgress, BuildStats)
  - Server (FileWatcherLog, RequestLog)
  - Health (HealthTree, GraphInsights)
- [ ] Update navigation between screens
- [ ] Add keyboard shortcuts for screen switching
- [ ] Polish CSS styling

**Commit**: `cli(dashboard): organize widgets into logical screens with improved navigation`

---

### Task 5.2: Performance Optimization

**What**: Ensure dashboard remains fast with large sites  
**Where**: All new widgets

**Changes**:
- [ ] Add virtual scrolling for large lists (Textual supports this)
- [ ] Add lazy loading for content trees
- [ ] Test with 1000+ page site
- [ ] Profile and optimize if needed

**Commit**: `cli(dashboard): optimize widget performance for large sites`

---

### Task 5.3: Documentation

**What**: Update dashboard documentation  
**Where**: `site/docs/dashboard.md` or similar

**Changes**:
- [ ] Document new widgets and features
- [ ] Add keyboard shortcuts reference
- [ ] Add screenshots

**Commit**: `docs(dashboard): document API integration features and widgets`

---

## Task Summary

| Phase | Tasks | Effort | API Status |
|-------|-------|--------|------------|
| 1: Site Data | 4 tasks | 1 day | ✅ Existing |
| 2a: BuildStats | 1 task | 0.5 day | ✅ Existing |
| 4: Health & Analysis | 3 tasks | 1 day | ✅ Existing |
| 2b: Build Streaming | 2 tasks | 0.5 day | 🆕 Core changes |
| 3: DevServer | 4 tasks | 1 day | 🆕 Core changes |
| 5: Integration | 3 tasks | 0.5 day | Dashboard only |
| **Total** | **17 tasks** | **4.5 days** | |

---

## Recommended Execution Order

```
Week 1:
├── Phase 1: Site Data Model (1 day)
│   ├── Task 1.1: Rich Site Context
│   ├── Task 1.2: ContentBrowser
│   ├── Task 1.3: AssetExplorer
│   └── Task 1.4: Integrate into Screens
│
├── Phase 2a: BuildStats Display (0.5 day)
│   └── Task 2.1: Full BuildStats
│
└── Phase 4: Health & Analysis (1 day)
    ├── Task 4.1: HealthTree
    ├── Task 4.2: TaxonomyExplorer
    └── Task 4.3: GraphInsights

Week 2:
├── Phase 2b: Build Streaming (0.5 day)
│   ├── Task 2.2: Core Callbacks
│   └── Task 2.3: PhaseProgress Widget
│
├── Phase 3: DevServer (1 day)
│   ├── Task 3.1: File Change Callback
│   ├── Task 3.2: FileWatcherLog
│   ├── Task 3.3: Request Logging
│   └── Task 3.4: RequestLog Widget
│
└── Phase 5: Integration & Polish (0.5 day)
    ├── Task 5.1: Screen Organization
    ├── Task 5.2: Performance
    └── Task 5.3: Documentation
```

---

## New Files Created

```
bengal/cli/dashboard/widgets/
├── content_browser.py    # Task 1.2
├── asset_explorer.py     # Task 1.3
├── taxonomy_explorer.py  # Task 4.2
├── phase_progress.py     # Task 2.3
├── file_watcher_log.py   # Task 3.2
└── request_log.py        # Task 3.4

bengal/server/
├── request_handler.py    # Modified: Task 3.3 (RequestLogEntry)

tests/unit/cli/dashboard/
├── test_content_browser.py
├── test_asset_explorer.py
├── test_build_stats_display.py
├── test_health_tree.py
├── test_taxonomy_explorer.py
├── test_graph_insights.py
├── test_phase_progress.py
├── test_file_watcher_log.py
└── test_request_log.py

tests/unit/server/
├── test_watcher_callbacks.py
└── test_request_logging.py

tests/unit/orchestration/
└── test_build_callbacks.py
```

---

## Success Criteria

- [ ] All Site properties visible in dashboard
- [ ] Pages browsable by section, date, tags, draft status
- [ ] Assets browsable by type with sizes
- [ ] Build phases stream in real-time
- [ ] Full BuildStats displayed (all 20+ fields)
- [ ] HealthReport properly categorized with recommendations
- [ ] File watcher events visible
- [ ] HTTP requests logged with timing
- [ ] Taxonomies explorable with page lists
- [ ] Graph insights show orphans and most-linked
- [ ] No performance regression (<100ms dashboard startup)
- [ ] All new widgets have unit tests

---

## Commit Summary

| Task | Commit Message |
|------|----------------|
| 1.1 | `cli(dashboard): add rich site context panel with page/asset/taxonomy breakdown` |
| 1.2 | `cli(dashboard): add ContentBrowser widget for section-based page navigation` |
| 1.3 | `cli(dashboard): add AssetExplorer widget with type grouping and size display` |
| 1.4 | `cli(dashboard): integrate ContentBrowser and AssetExplorer into dashboard screens` |
| 2.1 | `cli(dashboard): display full BuildStats with phase timing, cache, memory, and directives` |
| 2.2 | `orchestration(build): add optional phase callbacks for streaming progress` |
| 2.3 | `cli(dashboard): add PhaseProgress widget with real-time build streaming` |
| 3.1 | `server(watcher): add optional file change callback for dashboard integration` |
| 3.2 | `cli(dashboard): add FileWatcherLog widget with real-time file change stream` |
| 3.3 | `server(handler): add request logging with callback for dashboard` |
| 3.4 | `cli(dashboard): add RequestLog widget with live HTTP request stream` |
| 4.1 | `cli(dashboard): add HealthTree widget with categorized issues and recommendations` |
| 4.2 | `cli(dashboard): add TaxonomyExplorer widget with term drill-down and page lists` |
| 4.3 | `cli(dashboard): add graph insights panel showing orphans and most-linked pages` |
| 5.1 | `cli(dashboard): organize widgets into logical screens with improved navigation` |
| 5.2 | `cli(dashboard): optimize widget performance for large sites` |
| 5.3 | `docs(dashboard): document API integration features and widgets` |
