# Plan: Dashboard Deep API Integration

**Status**: Ready  
**RFC**: `plan/drafted/rfc-dashboard-api-integration.md`  
**Created**: 2024-12-22  
**Estimated Effort**: 4 days

---

## Overview

Transform the Bengal dashboard from "shows some stats" to a comprehensive Bengal control panel by surfacing all existing APIs (Site, Page, Section, Asset, BuildStats, HealthReport) and adding minimal middleware for real-time streaming.

### API Readiness Summary

- **95% existing APIs** - Ready to use with dashboard-only changes
- **5% new middleware** - 3 callback additions (~4 hours total)

---

## Phase 1: Site Data Model Integration (1 day)

### 1.1 Rich Site Context Panel

**File**: `bengal/cli/dashboard/screens.py` (LandingScreen)

**Current**: Shows page/section/asset counts  
**Target**: Full site context with theme, baseurl, taxonomies, data files

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 1.1.1 | `screens.py` | Enhance `_get_site_summary()` with draft/published breakdown | `dashboard(landing): add draft vs published page counts` |
| 1.1.2 | `screens.py` | Add asset grouping by file extension (.css, .js, images) | `dashboard(landing): group assets by type with size info` |
| 1.1.3 | `screens.py` | Add taxonomy summary with term counts and page assignments | `dashboard(landing): add taxonomy terms and page counts` |
| 1.1.4 | `screens.py` | Add data files list from `site.data` | `dashboard(landing): show data files from site.data` |
| 1.1.5 | `screens.py` | Show last build time and mode from `site._last_build_stats` | `dashboard(landing): display last build info` |

**Data Sources**:
- `site.pages` → filter by `page.draft` for draft/published
- `site.assets` → group by `asset.suffix`
- `site.taxonomies` → dict of `{taxonomy: {term: [pages]}}`
- `site.data` → dict of data files
- `site.theme`, `site.baseurl`, `site.output_dir`

---

### 1.2 Content Browser Widget

**File**: `bengal/cli/dashboard/widgets/content_browser.py` (NEW)

**Target**: Tree widget to browse pages organized by section hierarchy

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 1.2.1 | `widgets/content_browser.py` | Create `ContentBrowser(Tree)` widget | `dashboard(widgets): add ContentBrowser tree widget` |
| 1.2.2 | `widgets/content_browser.py` | Populate tree from `site.sections` and `section.pages` | `dashboard(widgets): populate ContentBrowser from site sections` |
| 1.2.3 | `widgets/content_browser.py` | Display page metadata (title, date, tags, draft status) | `dashboard(widgets): show page metadata in ContentBrowser` |
| 1.2.4 | `widgets/content_browser.py` | Add filtering by tag and draft status | `dashboard(widgets): add ContentBrowser filtering` |
| 1.2.5 | `widgets/__init__.py` | Export ContentBrowser | `dashboard(widgets): export ContentBrowser` |
| 1.2.6 | `screens.py` | Add ContentBrowser to LandingScreen | `dashboard(landing): integrate ContentBrowser widget` |

**Data Sources**:
- `site.sections` → section hierarchy
- `section.subsections` → child sections
- `section.pages` → pages in section
- `page.title`, `page.date`, `page.tags`, `page.draft`

**Widget Signature**:
```python
class ContentBrowser(Tree):
    def __init__(self, site: Site, filter_tag: str | None = None, show_drafts: bool = True):
        ...
```

---

### 1.3 Asset Explorer Widget

**File**: `bengal/cli/dashboard/widgets/asset_explorer.py` (NEW)

**Target**: Tree widget to browse assets grouped by type with size info

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 1.3.1 | `widgets/asset_explorer.py` | Create `AssetExplorer(Tree)` widget | `dashboard(widgets): add AssetExplorer tree widget` |
| 1.3.2 | `widgets/asset_explorer.py` | Group assets by suffix (.css, .js, .png, etc.) | `dashboard(widgets): group assets by type in AssetExplorer` |
| 1.3.3 | `widgets/asset_explorer.py` | Show file sizes (compute from `Path.stat().st_size`) | `dashboard(widgets): add file sizes to AssetExplorer` |
| 1.3.4 | `widgets/asset_explorer.py` | Calculate total size per type and grand total | `dashboard(widgets): add size totals to AssetExplorer` |
| 1.3.5 | `widgets/__init__.py` | Export AssetExplorer | `dashboard(widgets): export AssetExplorer` |
| 1.3.6 | `screens.py` | Add AssetExplorer to LandingScreen | `dashboard(landing): integrate AssetExplorer widget` |

**Data Sources**:
- `site.assets` → asset list
- `asset.source_path` → file path
- `asset.suffix` → file extension
- `Path(asset.source_path).stat().st_size` → file size

---

## Phase 2: Build Orchestration Integration (1 day)

### 2.1 BuildStats Deep Display

**File**: `bengal/cli/dashboard/screens.py` (BuildScreen)

**Current**: Shows basic phase timing  
**Target**: Display ALL 20+ BuildStats fields

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 2.1.1 | `screens.py` | Display page breakdown (regular, generated, tag, archive, pagination) | `dashboard(build): add page type breakdown` |
| 2.1.2 | `screens.py` | Show phase timing breakdown with percentage bars | `dashboard(build): add phase timing visualization` |
| 2.1.3 | `screens.py` | Display cache performance (hits, misses, time saved) | `dashboard(build): show cache hit/miss stats` |
| 2.1.4 | `screens.py` | Show memory usage (RSS, heap, peak) | `dashboard(build): display memory usage` |
| 2.1.5 | `screens.py` | Show directive usage counts by type | `dashboard(build): show directive usage breakdown` |
| 2.1.6 | `screens.py` | Display warnings and errors by category | `dashboard(build): show warnings and errors` |

**Data Sources** (from `bengal/orchestration/stats/models.py`):
- `stats.total_pages`, `regular_pages`, `generated_pages`
- `stats.tag_pages`, `archive_pages`, `pagination_pages`
- `stats.discovery_time_ms`, `taxonomy_time_ms`, `rendering_time_ms`
- `stats.cache_hits`, `cache_misses`, `time_saved_ms`
- `stats.memory_rss_mb`, `memory_heap_mb`, `memory_peak_mb`
- `stats.total_directives`, `directives_by_type`
- `stats.warnings`, `errors_by_category`

---

### 2.2 Phase Streaming Callbacks (NEW MIDDLEWARE)

**File**: `bengal/orchestration/build/__init__.py`

**Target**: Add optional callbacks to stream build progress to dashboard

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 2.2.1 | `build/__init__.py` | Add `on_phase_start` callback parameter to `build()` | `orchestration(build): add on_phase_start callback` |
| 2.2.2 | `build/__init__.py` | Add `on_phase_complete` callback parameter to `build()` | `orchestration(build): add on_phase_complete callback` |
| 2.2.3 | `build/__init__.py` | Call callbacks at each phase boundary (21 phases) | `orchestration(build): invoke phase callbacks at boundaries` |
| 2.2.4 | `build/options.py` | Add callback fields to `BuildOptions` dataclass | `orchestration(options): add phase callback fields` |

**API Change**:
```python
def build(
    self,
    options: BuildOptions | None = None,
    *,
    # ... existing params ...
    # NEW: Streaming callbacks (optional, None by default)
    on_phase_start: Callable[[str], None] | None = None,
    on_phase_complete: Callable[[str, float, str], None] | None = None,
) -> BuildStats:
```

**Implementation Points** (21 phases):
- Phase 1: Fonts
- Phase 2: Discovery
- Phase 3: Cache metadata
- Phase 4: Config check
- Phase 5: Incremental filter
- Phase 6: Sections
- Phase 7: Taxonomies
- Phase 8: Taxonomy index
- Phase 9: Menus
- Phase 10: Related posts
- Phase 11: Query indexes
- Phase 12: Update pages list
- Phase 13: Assets
- Phase 14: Render
- Phase 15: Update site pages
- Phase 16: Track assets
- Phase 17: Postprocess
- Phase 18: Cache save
- Phase 19: Collect stats
- Phase 20: Health check
- Phase 21: Finalize

---

### 2.3 Dashboard Phase Streaming Integration

**File**: `bengal/cli/dashboard/screens.py` (BuildScreen)

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 2.3.1 | `screens.py` | Create phase callback handlers that update DataTable | `dashboard(build): add phase streaming handlers` |
| 2.3.2 | `screens.py` | Update `_run_build()` to pass callbacks to orchestrator | `dashboard(build): pass phase callbacks to build` |
| 2.3.3 | `screens.py` | Show real-time progress bar based on phase completion | `dashboard(build): update progress bar from phase callbacks` |
| 2.3.4 | `widgets/phase_progress.py` | Create `PhaseProgress` widget for streaming display | `dashboard(widgets): add PhaseProgress streaming widget` |

---

## Phase 3: DevServer Integration (1 day)

### 3.1 File Watcher Event Display

**File**: `bengal/cli/dashboard/screens.py` (ServeScreen)

**Note**: `WatcherRunner` already has `on_changes` callback - just need to wire it up!

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 3.1.1 | `screens.py` | Create file change event handler for ServeScreen | `dashboard(serve): add file change event handler` |
| 3.1.2 | `screens.py` | Display file changes in changes-log with timestamps | `dashboard(serve): show file changes with timestamps` |
| 3.1.3 | `screens.py` | Show event types (created, modified, deleted) with icons | `dashboard(serve): add event type icons` |
| 3.1.4 | `screens.py` | Link file changes to rebuild triggers | `dashboard(serve): connect file changes to rebuild display` |

**Existing API** (`bengal/server/watcher_runner.py`):
```python
class WatcherRunner:
    def __init__(
        self,
        paths: list[Path],
        ignore_filter: IgnoreFilter,
        on_changes: Callable[[set[Path], set[str]], None],  # ← Already exists!
        debounce_ms: int = 300,
    ):
```

---

### 3.2 HTTP Request Logging (NEW MIDDLEWARE)

**File**: `bengal/server/request_handler.py`

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 3.2.1 | `request_handler.py` | Add `RequestLogEntry` dataclass | `server(handler): add RequestLogEntry dataclass` |
| 3.2.2 | `request_handler.py` | Add class-level `request_log` list and `on_request` callback | `server(handler): add request logging infrastructure` |
| 3.2.3 | `request_handler.py` | Log requests in `do_GET()` and `do_HEAD()` | `server(handler): log requests with timing` |
| 3.2.4 | `request_handler.py` | Limit log size to prevent memory growth | `server(handler): bound request log size` |

**New API**:
```python
@dataclass
class RequestLogEntry:
    timestamp: datetime
    method: str
    path: str
    status: int
    duration_ms: float

class BengalRequestHandler:
    request_log: ClassVar[list[RequestLogEntry]] = []
    on_request: ClassVar[Callable[[RequestLogEntry], None] | None] = None
    MAX_LOG_SIZE: ClassVar[int] = 1000
```

---

### 3.3 Dashboard Request Log Integration

**File**: `bengal/cli/dashboard/screens.py` (ServeScreen)

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 3.3.1 | `screens.py` | Create request log handler for ServeScreen | `dashboard(serve): add request log handler` |
| 3.3.2 | `screens.py` | Display requests with method, path, status, duration | `dashboard(serve): show request log with details` |
| 3.3.3 | `screens.py` | Highlight 404s and errors with warning icons | `dashboard(serve): highlight errors in request log` |
| 3.3.4 | `screens.py` | Add "Requests" tab to TabbedContent | `dashboard(serve): add Requests tab` |

---

## Phase 4: Health & Analysis Integration (1 day)

### 4.1 HealthReport Deep Display

**File**: `bengal/cli/dashboard/screens.py` (HealthScreen)

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 4.1.1 | `screens.py` | Parse `HealthReport.results` into categorized tree | `dashboard(health): categorize health results` |
| 4.1.2 | `screens.py` | Display `CheckResult.status` with icons (SUCCESS, WARNING, ERROR) | `dashboard(health): add status icons to health tree` |
| 4.1.3 | `screens.py` | Show `CheckResult.message` and `recommendation` in details panel | `dashboard(health): show recommendations in details` |
| 4.1.4 | `screens.py` | Add file:line references that could open in editor | `dashboard(health): add file references to issues` |
| 4.1.5 | `screens.py` | Calculate health score percentage | `dashboard(health): compute health score percentage` |

**Data Sources** (from `bengal/health/report.py`):
- `HealthReport.results` → list of `CheckResult`
- `CheckResult.status` → SUCCESS, WARNING, ERROR
- `CheckResult.message` → issue description
- `CheckResult.recommendation` → fix suggestion
- `CheckResult.validator` → which validator produced it
- `CheckResult.details` → additional context

---

### 4.2 Taxonomy Explorer Widget

**File**: `bengal/cli/dashboard/widgets/taxonomy_explorer.py` (NEW)

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 4.2.1 | `widgets/taxonomy_explorer.py` | Create `TaxonomyExplorer(Tree)` widget | `dashboard(widgets): add TaxonomyExplorer tree widget` |
| 4.2.2 | `widgets/taxonomy_explorer.py` | Display taxonomy names with term counts | `dashboard(widgets): show taxonomy names with counts` |
| 4.2.3 | `widgets/taxonomy_explorer.py` | Show terms with page counts and horizontal bars | `dashboard(widgets): add term bars to TaxonomyExplorer` |
| 4.2.4 | `widgets/taxonomy_explorer.py` | Expand term to show page list | `dashboard(widgets): expand terms to show pages` |
| 4.2.5 | `widgets/__init__.py` | Export TaxonomyExplorer | `dashboard(widgets): export TaxonomyExplorer` |
| 4.2.6 | `screens.py` | Add TaxonomyExplorer to HealthScreen | `dashboard(health): integrate TaxonomyExplorer widget` |

**Data Sources**:
- `site.taxonomies` → dict of `{taxonomy_name: {term: [pages]}}`
- Term → page list mapping for drill-down

---

### 4.3 Graph Analysis Integration (Future Enhancement)

**File**: `bengal/cli/dashboard/widgets/link_graph.py` (NEW - OPTIONAL)

| Task | File | Description | Commit |
|------|------|-------------|--------|
| 4.3.1 | `widgets/link_graph.py` | Create `LinkGraphSummary` widget | `dashboard(widgets): add LinkGraphSummary widget` |
| 4.3.2 | `widgets/link_graph.py` | Display internal/external link counts | `dashboard(widgets): show link counts` |
| 4.3.3 | `widgets/link_graph.py` | Show orphan pages (no incoming links) | `dashboard(widgets): show orphan pages` |
| 4.3.4 | `widgets/link_graph.py` | Show most linked pages ranking | `dashboard(widgets): show most linked pages` |

**Data Sources** (from `bengal/analysis/graph_analysis.py`):
- `GraphAnalyzer.analyze()` → link analysis
- `page.links` → links from each page

---

## Testing Strategy

### Unit Tests

| Test File | Description |
|-----------|-------------|
| `tests/unit/cli/dashboard/test_content_browser.py` | ContentBrowser widget tests |
| `tests/unit/cli/dashboard/test_asset_explorer.py` | AssetExplorer widget tests |
| `tests/unit/cli/dashboard/test_taxonomy_explorer.py` | TaxonomyExplorer widget tests |
| `tests/unit/cli/dashboard/test_phase_callbacks.py` | Phase callback tests |

### Integration Tests

| Test File | Description |
|-----------|-------------|
| `tests/integration/cli/dashboard/test_site_data_display.py` | Full site data rendering |
| `tests/integration/cli/dashboard/test_build_streaming.py` | Phase streaming integration |
| `tests/integration/cli/dashboard/test_serve_events.py` | File watcher and request log |

---

## Success Criteria

- [ ] All Site properties visible in dashboard (title, theme, baseurl, config)
- [ ] Pages browsable by section, date, tags, draft status
- [ ] Assets browsable by type with size information
- [ ] Build phases stream in real-time (not after completion)
- [ ] Full BuildStats displayed (all 20+ fields)
- [ ] HealthReport properly categorized with recommendations
- [ ] File watcher events visible in serve screen
- [ ] HTTP requests logged in serve screen
- [ ] Taxonomies explorable with page lists
- [ ] No performance regression (<100ms dashboard startup)

---

## Execution Order

**Recommended sequence** (build on existing APIs first):

```
Phase 1 (Site Data) ─────────────┐
  ✅ Uses existing APIs          │
  1.1 Rich Site Context          │
  1.2 ContentBrowser             │
  1.3 AssetExplorer              │
                                 ├──► Phase 2a (BuildStats) ───┐
Phase 4 (Health/Analysis) ───────┘     ✅ Uses existing APIs    │
  ✅ Uses existing APIs                2.1 BuildStats display    │
  4.1 HealthReport display                                       │
  4.2 TaxonomyExplorer                                           │
                                                                 │
                                       Phase 2b + 3 (Middleware) ◄┘
                                         🆕 New core changes
                                         2.2 Phase callbacks
                                         2.3 Dashboard streaming
                                         3.1 File watcher display
                                         3.2 Request logging
                                         3.3 Request log display
```

**Strategy**: Ship dashboard improvements with existing APIs first (Phases 1, 2a, 4), then add streaming features (Phases 2b, 3) as enhancement.

---

## File Summary

### New Files
- `bengal/cli/dashboard/widgets/content_browser.py`
- `bengal/cli/dashboard/widgets/asset_explorer.py`
- `bengal/cli/dashboard/widgets/taxonomy_explorer.py`
- `bengal/cli/dashboard/widgets/phase_progress.py`
- `bengal/cli/dashboard/widgets/link_graph.py` (optional)

### Modified Files
- `bengal/cli/dashboard/screens.py` (major enhancements)
- `bengal/cli/dashboard/widgets/__init__.py` (exports)
- `bengal/orchestration/build/__init__.py` (phase callbacks)
- `bengal/orchestration/build/options.py` (callback fields)
- `bengal/server/request_handler.py` (request logging)

### Test Files
- `tests/unit/cli/dashboard/test_content_browser.py`
- `tests/unit/cli/dashboard/test_asset_explorer.py`
- `tests/unit/cli/dashboard/test_taxonomy_explorer.py`
- `tests/unit/cli/dashboard/test_phase_callbacks.py`
- `tests/integration/cli/dashboard/test_site_data_display.py`
- `tests/integration/cli/dashboard/test_build_streaming.py`
- `tests/integration/cli/dashboard/test_serve_events.py`

---

## Dependencies

### No Core Changes Required (95% of features)
- `Site.*` properties
- `Page.*` properties
- `Section.*` properties
- `Asset.*` properties
- `BuildStats` (all fields)
- `HealthReport`, `CheckResult`
- `GraphAnalyzer.analyze()`
- `WatcherRunner.on_changes` (already exists!)

### New Middleware Required (5% of features)
1. **BuildOrchestrator phase callbacks** (~2 hours)
2. **BengalRequestHandler request logging** (~1 hour)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Large sites slow browsing | Low | Medium | Virtual scrolling, lazy loading (Textual supports this) |
| Complex UI overwhelming | Low | Medium | Progressive disclosure, collapsible sections |
| Core changes break existing behavior | Low | High | Keep callbacks optional with `None` defaults |
