# RFC: Dashboard Deep API Integration

**Status**: Evaluated  
**Created**: 2024-12-21  
**Plan**: `plan/ready/plan-dashboard-api-integration.md`  
**Author**: AI Assistant  
**Depends On**:
- Terminal UX with Textual (implemented)
- Toad-Inspired Enhancements (in progress)
- Dashboard Content Enrichment RFC (ready)

---

## Summary

The Bengal dashboard infrastructure is complete, but it treats Bengal as a black box. This RFC proposes **deep integration** with Bengal's rich data APIs—making the dashboard a first-class consumer of Site, Page, Section, Asset, BuildStats, HealthReport, and orchestration events.

**Goal**: Transform the dashboard from "shows some stats" to "comprehensive Bengal control panel" that surfaces all the data Bengal already produces.

---

## 🎯 API Readiness Assessment

**95% of required data is available through existing APIs.** Only streaming/real-time features require new middleware.

### ✅ Existing APIs (Ready to Use)

| Feature | API | Status | Effort |
|---------|-----|--------|--------|
| Site context (title, theme, baseurl) | `Site.*` properties | ✅ Ready | Dashboard only |
| Page browsing (title, date, tags, draft) | `Site.pages`, `Page.*` | ✅ Ready | Dashboard only |
| Section hierarchy | `Site.sections`, `Section.subsections` | ✅ Ready | Dashboard only |
| Asset exploration | `Site.assets`, `Asset.suffix` | ✅ Ready | Dashboard only |
| Taxonomy terms & counts | `Site.taxonomies` | ✅ Ready | Dashboard only |
| Build stats (20+ fields) | `BuildStats` from `build()` | ✅ Ready | Dashboard only |
| Health report | `HealthReport.from_site()` | ✅ Ready | Dashboard only |
| Data files | `Site.data` | ✅ Ready | Dashboard only |
| Graph analysis | `GraphAnalyzer.analyze()` | ✅ Ready | Dashboard only |

### 🆕 New Middleware Required (Worth Doing)

| Feature | What's Needed | Why It's Worth It | Effort |
|---------|---------------|-------------------|--------|
| **Phase streaming** | Add callbacks to `BuildOrchestrator.build()` | Real-time build feedback, no more black-box builds | ~2 hours |
| **File change events** | Add event bridge from `WatcherRunner` to dashboard | See what triggered rebuilds, debug file watching | ~1 hour |
| **Request logging** | Add logging to `BengalRequestHandler` | Debug 404s, track request patterns, see live traffic | ~1 hour |

### Implementation Split

```
┌─────────────────────────────────────────────────────────────────┐
│                   IMPLEMENTATION BREAKDOWN                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: Site Data Model (✅ EXISTING APIs)                    │
│    - Site context panel         → Site.*, config                │
│    - Content browser            → Site.pages, Site.sections     │
│    - Asset explorer             → Site.assets                   │
│                                                                  │
│  PHASE 2: Build Integration (⚠️ MIXED)                          │
│    - BuildStats display         → ✅ EXISTING (BuildStats)      │
│    - Phase streaming            → 🆕 NEW MIDDLEWARE NEEDED      │
│                                                                  │
│  PHASE 3: DevServer Integration (🆕 NEW MIDDLEWARE)             │
│    - File watcher events        → 🆕 NEW: Event bridge          │
│    - Request logging            → 🆕 NEW: Handler logging       │
│                                                                  │
│  PHASE 4: Health & Analysis (✅ EXISTING APIs)                  │
│    - HealthReport display       → HealthReport.from_site()      │
│    - Taxonomy explorer          → Site.taxonomies               │
│    - Graph insights             → GraphAnalyzer.analyze()       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

### Current Gap: Shallow Data Integration

The existing RFCs (`rfc-dashboard-content-enrichment`, `rfc-toad-inspired-enhancements`) focus on:
- Displaying BuildStats fields ✅
- Adding Toad-inspired widgets ✅
- Basic health check visualization ✅

**But Bengal has much richer data that's currently untapped**:

| Bengal API | Rich Data Available | Current Dashboard Usage |
|------------|---------------------|-------------------------|
| `Site` | pages, sections, assets, taxonomies, config, theme, data/, menu | ❌ Shows count only |
| `Page` | title, date, url, tags, draft, weight, toc_items, metadata | ❌ Title only |
| `Section` | hierarchy, subsections, index_page, relative_url | ❌ Count only |
| `Asset` | source_path, suffix, grouped by type | ❌ Count only |
| `BuildStats` | 20+ fields including phase timings, cache, memory, directives | ⚠️ Partial |
| `HealthReport` | categorized results with recommendations | ⚠️ Shallow |
| `BuildOrchestrator` | streaming phase events | ❌ Not integrated |
| `DevServer` | file watcher events, request log | ❌ Not integrated |
| `GraphAnalyzer` | link graph, connectivity, knowledge graph | ❌ Not integrated |

### Evidence: What Users Can't See Today

1. **No page browser**: Can't browse pages by date, section, tags, or draft status
2. **No section tree**: Can't navigate content hierarchy
3. **No asset explorer**: Can't see assets grouped by type or size
4. **No taxonomy drill-down**: Can't see which pages have which tags
5. **No build streaming**: Build happens in background, no phase-by-phase feedback
6. **No dev server logs**: Can't see file changes or HTTP requests
7. **No graph insights**: Can't see link structure or orphan pages

---

## Goals

1. **Surface all Bengal data** - Make every data model visible in dashboard
2. **Streaming updates** - Real-time phase progress during builds
3. **Exploratory browsing** - Navigate pages, sections, assets, taxonomies
4. **Actionable insights** - Link to files, show recommendations
5. **Performance visibility** - Full phase timing, memory, cache breakdown

---

## Non-Goals

- New CLI commands (use existing `bengal --dashboard`)
- ~~Changes to core Bengal APIs (consume only)~~ → **Revised**: Minimal, optional callback additions (~4 hours total)
- Heavy visualizations like graphs (defer to separate tool)
- Breaking existing functionality (all new callbacks are optional with `None` defaults)

---

## Proposed Changes

### Phase 1: Site Data Model Integration (1 day)

#### 1.1 Landing Screen: Rich Site Context

**Current**: Shows page/section/asset counts
**Proposed**: Full site context panel

```
┌─ Site Context ─────────────────────────────────────────────┐
│ 🐱 My Documentation Site                                    │
│                                                             │
│ Theme: bengal-docs    Base URL: /docs/                      │
│ Output: public/       Version: v2.1.0                       │
│                                                             │
│ Content:                                                    │
│   📄 142 pages (128 published, 14 draft)                    │
│   📁 23 sections                                            │
│   🎨 47 assets (12 CSS, 8 JS, 27 images)                    │
│                                                             │
│ Taxonomies:                                                 │
│   🏷️ tags: 34 terms (156 page assignments)                  │
│   📂 categories: 8 terms (89 page assignments)              │
│                                                             │
│ Data Files:                                                 │
│   📊 3 data files loaded (authors.yaml, nav.toml, ...)      │
│                                                             │
│ Last Build: 2.3s ago (1.2s, incremental)                    │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `site.title` - Site title
- `site.theme` - Theme name
- `site.baseurl` - Base URL
- `site.output_dir` - Output directory
- `site.pages` - Page list (filter by `draft` property)
- `site.sections` - Section list
- `site.assets` - Asset list (group by `.suffix`)
- `site.taxonomies` - Taxonomy dict with term counts
- `site.data` - Data directory contents
- `site._last_build_stats` - Last build stats

**Implementation**:
```python
# bengal/cli/dashboard/screens.py - LandingScreen

def _get_rich_site_context(self) -> str:
    """Generate comprehensive site context."""
    site = self.site
    if not site:
        return "No site loaded"

    # Page breakdown
    pages = site.pages or []
    drafts = [p for p in pages if getattr(p, "draft", False)]
    published = len(pages) - len(drafts)

    # Asset breakdown by type
    assets = site.assets or []
    by_type = {}
    for asset in assets:
        ext = getattr(asset, "suffix", ".unknown")
        by_type[ext] = by_type.get(ext, 0) + 1
    asset_summary = ", ".join(f"{v} {k}" for k, v in sorted(by_type.items())[:5])

    # Taxonomy summary
    tax_info = []
    for name, terms in (site.taxonomies or {}).items():
        if isinstance(terms, dict):
            page_count = sum(len(v) if isinstance(v, list) else 0 for v in terms.values())
            tax_info.append(f"🏷️ {name}: {len(terms)} terms ({page_count} pages)")

    # Data files
    data_files = list(site.data.keys()) if site.data else []

    return f"""[bold]{site.title or 'Untitled'}[/bold]

Theme: {site.theme or 'default'}    Base URL: {site.baseurl or '/'}
Output: {site.output_dir}/

Content:
  📄 {len(pages)} pages ({published} published, {len(drafts)} draft)
  📁 {len(site.sections or [])} sections
  🎨 {len(assets)} assets ({asset_summary})

{chr(10).join(tax_info) if tax_info else 'No taxonomies configured'}

Data Files: {len(data_files)} loaded
"""
```

---

#### 1.2 Content Browser Widget

**New widget**: Browsable content tree showing pages organized by section

```
┌─ Content Browser ─────────────────────────────────────────┐
│ 📁 docs/                                                   │
│   📄 Introduction                    2024-12-01  #guide    │
│   📄 Getting Started                 2024-12-15  #tutorial │
│   📁 advanced/                                              │
│     📄 Performance Tips              2024-12-10  #perf     │
│     📄 Custom Themes                 2024-12-12  #theme    │
│   📁 api/                                                   │
│     📄 Configuration [draft]         2024-12-20            │
│     📄 CLI Reference                 2024-12-18            │
│ 📁 blog/                                                   │
│   📄 Launch Announcement             2024-11-01  #news     │
└─────────────────────────────────────────────────────────────┘
  [Enter] Open file  [t] Filter by tag  [d] Show drafts only
```

**Data Sources**:
- `site.sections` - Section hierarchy
- `section.pages` - Pages in section
- `section.subsections` - Child sections
- `page.title`, `page.date`, `page.tags`, `page.draft`

**Implementation**: Create new `ContentBrowser` widget extending `Tree`

---

#### 1.3 Asset Explorer Widget

**New widget**: Assets grouped by type with size information

```
┌─ Asset Explorer ───────────────────────────────────────────┐
│ 🎨 47 assets (1.2 MB total)                                │
│                                                             │
│ 📁 CSS (12 files, 245 KB)                                   │
│   ├─ main.css                    128 KB                     │
│   ├─ syntax.css                   45 KB                     │
│   └─ ...                                                    │
│ 📁 JavaScript (8 files, 512 KB)                             │
│   ├─ search.js                   234 KB                     │
│   └─ ...                                                    │
│ 📁 Images (27 files, 467 KB)                                │
│   ├─ logo.svg                     12 KB                     │
│   └─ ...                                                    │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `site.assets` - Asset list
- `asset.source_path` - File path
- `asset.suffix` - File extension
- `Path.stat().st_size` - File size (needs computation)

---

### Phase 2: Build Orchestration Streaming (1 day)

#### 2.1 Real-Time Phase Updates

**Current**: Build runs in background, one "complete" message at end
**Proposed**: Stream phase-by-phase updates as build progresses

```
┌─ Build Progress ───────────────────────────────────────────┐
│ ● Building site...                                          │
│                                                             │
│ ✓ Discovery      120ms    142 pages found                   │
│ ✓ Taxonomies      80ms    34 tags, 8 categories             │
│ ● Rendering      ███████░░░  78% (111/142 pages)            │
│ · Assets         -         waiting...                       │
│ · Postprocess    -         waiting...                       │
│                                                             │
│ Cache: 89/142 hits (63%)  Memory: 128 MB                    │
└─────────────────────────────────────────────────────────────┘
```

**Implementation**: Integrate with `BuildOrchestrator` via callbacks or message passing

```python
# Enhanced build worker with phase callbacks
async def _run_build_with_streaming(self) -> None:
    """Run build with streaming phase updates."""
    from bengal.orchestration.build import BuildOrchestrator

    orchestrator = BuildOrchestrator(self.site)

    # Phase callbacks (if supported) or poll-based updates
    def on_phase_start(phase: str):
        self.call_from_thread(self._update_phase, phase, "running")

    def on_phase_complete(phase: str, time_ms: float, details: str):
        self.call_from_thread(self._update_phase, phase, "complete", time_ms, details)

    # Build with callbacks
    stats = orchestrator.build(
        parallel=True,
        incremental=False,
        on_phase_start=on_phase_start,
        on_phase_complete=on_phase_complete,
    )
```

**Note**: May require adding callback support to `BuildOrchestrator` if not present.

---

#### 2.2 BuildStats Deep Display

**Show ALL BuildStats fields**, not just basics:

```
┌─ Build Statistics ─────────────────────────────────────────┐
│ Total Time: 1.2s (parallel, incremental)                    │
│                                                             │
│ Pages:                                                      │
│   📄 Total: 142 (Regular: 128, Generated: 14)               │
│   📊 Tags: 8, Archives: 3, Pagination: 3                    │
│                                                             │
│ Phase Breakdown:                                            │
│   Discovery:   120ms (10%)  ████                            │
│   Taxonomies:   80ms  (7%)  ███                             │
│   Rendering:  800ms (67%)  ██████████████████████           │
│   Assets:     150ms (13%)  █████                            │
│   Postprocess: 50ms  (4%)  ██                               │
│                                                             │
│ Cache Performance:                                          │
│   Hits: 89 (63%)  Misses: 53 (37%)                          │
│   Time Saved: 2.1s                                          │
│                                                             │
│ Memory:                                                     │
│   RSS: 128 MB  Heap: 96 MB  Peak: 145 MB                    │
│                                                             │
│ Directives Used: 234 total                                  │
│   tabs: 45, admonition: 89, code: 78, include: 22           │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources** (from `orchestration/stats/models.py`):
- `stats.total_pages`, `regular_pages`, `generated_pages`
- `stats.tag_pages`, `archive_pages`, `pagination_pages`
- `stats.discovery_time_ms`, `taxonomy_time_ms`, `rendering_time_ms`, etc.
- `stats.cache_hits`, `cache_misses`, `time_saved_ms`
- `stats.memory_rss_mb`, `memory_heap_mb`, `memory_peak_mb`
- `stats.total_directives`, `directives_by_type`
- `stats.warnings`, `template_errors`, `errors_by_category`

---

### Phase 3: DevServer Integration (1 day)

#### 3.1 File Watcher Event Stream

**Integrate with `DevServer.file_watcher`** to show real-time changes:

```
┌─ File Watcher ─────────────────────────────────────────────┐
│ 👁️ Watching 156 files in 12 directories                    │
│                                                             │
│ Recent Changes:                                             │
│ 14:32:15  ✏️  content/posts/new-feature.md     (modified)   │
│ 14:32:16  🔨 Rebuild triggered (incremental)                │
│ 14:32:17  ✓  Build complete (342ms, 3 pages)                │
│ 14:31:45  ➕ assets/css/new-style.css          (created)    │
│ 14:31:46  🔨 Rebuild triggered (assets only)                │
│ 14:31:47  ✓  Build complete (89ms, assets)                  │
│ 14:30:12  ➖ content/old-page.md               (deleted)    │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `DevServer.watcher_runner` - File watcher component
- `BuildTrigger.trigger_build()` - Build events
- `watchfiles` events from `WatcherRunner`

**Implementation**: Subscribe to watcher events via message passing

---

#### 3.2 HTTP Request Log (Optional Enhancement)

**If dev server tracks requests**, show them:

```
┌─ Request Log ──────────────────────────────────────────────┐
│ 14:32:18  GET /docs/getting-started/  200  12ms             │
│ 14:32:19  GET /assets/css/main.css    200   3ms             │
│ 14:32:19  GET /assets/js/search.js    200   5ms             │
│ 14:32:20  GET /docs/not-found/        404   2ms  ⚠️         │
│ 14:32:22  GET /                        200   8ms             │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `BengalRequestHandler` - Request handling
- `request_logger` - If implemented

**Note**: May require adding request logging to dev server.

---

### Phase 4: Health & Analysis Integration (1 day)

#### 4.1 HealthReport Deep Integration

**Parse full `HealthReport` structure**:

```
┌─ Health Report ────────────────────────────────────────────┐
│ 🏥 Site Health: 94% ███████████████████░░                   │
│                                                             │
│ ✓ 142 pages checked, 47 assets verified                     │
│ ⚠️ 2 issues found (1 error, 1 warning)                      │
│                                                             │
│ Issues by Category:                                         │
│ ├─ 🔗 Links (1 error)                                       │
│ │   └─ ✗ /about → /old-page (404)                           │
│ │       📄 content/about.md:42                              │
│ │       💡 Update link or create redirect                   │
│ │                                                           │
│ ├─ ⚡ Performance (1 warning)                               │
│ │   └─ ⚠️ 3 pages >500KB (may slow load)                    │
│ │       📄 docs/api/reference.md (892KB)                    │
│ │       💡 Consider splitting into smaller pages            │
│ │                                                           │
│ └─ ✓ Assets, Navigation, Config, Taxonomy: All OK           │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `HealthReport.results` - List of `CheckResult`
- `CheckResult.status` - SUCCESS, WARNING, ERROR
- `CheckResult.message`, `recommendation`, `details`
- `CheckResult.validator` - Which validator produced it

---

#### 4.2 Taxonomy Explorer

**Show taxonomy deep-dive**:

```
┌─ Taxonomy Explorer ────────────────────────────────────────┐
│ 🏷️ tags (34 terms)                                         │
│                                                             │
│ ├─ tutorial (12 pages) ████████████                         │
│ │   ├─ Getting Started                                      │
│ │   ├─ First Steps                                          │
│ │   └─ ...                                                  │
│ ├─ guide (8 pages) ████████                                 │
│ ├─ api (6 pages) ██████                                     │
│ ├─ performance (4 pages) ████                               │
│ └─ ...                                                      │
│                                                             │
│ 📂 categories (8 terms)                                     │
│ ├─ Documentation (45 pages)                                 │
│ ├─ Blog (23 pages)                                          │
│ └─ ...                                                      │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `site.taxonomies` - Dict of `{taxonomy_name: {term: [pages]}}`
- Term → page list mapping

---

#### 4.3 GraphAnalyzer Integration (Future Enhancement)

**Surface link graph insights**:

```
┌─ Link Analysis ────────────────────────────────────────────┐
│ 🔗 Link Graph Summary                                       │
│                                                             │
│ Internal Links: 456                                         │
│ External Links: 34                                          │
│ Orphan Pages: 3 (no incoming links)                         │
│   ├─ docs/old/legacy-api.md                                 │
│   ├─ blog/draft-announcement.md                             │
│   └─ hidden/test-page.md                                    │
│                                                             │
│ Most Linked Pages:                                          │
│   1. Getting Started (23 incoming)                          │
│   2. API Reference (18 incoming)                            │
│   3. Configuration (15 incoming)                            │
└─────────────────────────────────────────────────────────────┘
```

**Data Sources**:
- `GraphAnalyzer.analyze()` - Link analysis
- `KnowledgeGraph` - Page relationships
- `page.links` - Links from each page

---

## Implementation Plan

| Phase | Focus | Days | API Status | Key Deliverables |
|-------|-------|------|------------|------------------|
| 1 | Site Data Model | 1 | ✅ **Existing APIs** | Rich site context, content browser, asset explorer |
| 2 | Build Streaming | 1 | ⚠️ **Mixed** | BuildStats display (existing), phase streaming (new) |
| 3 | DevServer Integration | 1 | 🆕 **New Middleware** | File watcher events, request logging |
| 4 | Health & Analysis | 1 | ✅ **Existing APIs** | HealthReport parsing, taxonomy explorer, graph insights |
| **Total** | | **4** | | |

### Recommended Execution Order

```
Phase 1 ──────────┐
(Site Data)       │
✅ Existing APIs  ├──▶  Phase 2a ──────────┐
                  │     (BuildStats)       │
Phase 4 ──────────┘     ✅ Existing APIs   │
(Health/Analysis)                          ├──▶  Phase 2b + 3
✅ Existing APIs                           │     (New Middleware)
                                           │     🆕 Core changes
                                           │
                                           └──▶  Full Dashboard
```

**Strategy**: Ship dashboard improvements with existing APIs first (Phases 1, 2a, 4), then add streaming features (Phases 2b, 3) as enhancement.

---

## New Widgets

| Widget | Purpose | Base Class |
|--------|---------|------------|
| `ContentBrowser` | Navigate pages by section hierarchy | `Tree` |
| `AssetExplorer` | Browse assets by type/size | `Tree` |
| `TaxonomyExplorer` | Drill into taxonomy terms | `Tree` |
| `PhaseProgress` | Streaming build phase display | `Vertical` + `ProgressBar` |
| `FileWatcherLog` | Real-time file change stream | `Log` |
| `HealthTree` | Categorized health issues | `Tree` |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Bengal Dashboard                          │
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   Screens   │────▶│   Widgets   │────▶│   Display   │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│         │                   ▲                               │
│         │                   │                               │
│         ▼                   │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Data Layer (Proposed)                   │    │
│  │                                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │ SiteData │ │ BuildData│ │HealthData│ │WatchData│  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                  │
└──────────────────────────│──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Bengal Core APIs                          │
│                                                             │
│  ┌──────┐ ┌──────┐ ┌────────┐ ┌───────┐ ┌──────────────┐    │
│  │ Site │ │ Page │ │Section │ │ Asset │ │BuildOrchestrator│ │
│  └──────┘ └──────┘ └────────┘ └───────┘ └──────────────┘    │
│                                                             │
│  ┌────────────┐ ┌───────────┐ ┌─────────────┐               │
│  │HealthCheck │ │ DevServer │ │GraphAnalyzer│               │
│  └────────────┘ └───────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cli/dashboard/test_site_data.py

def test_page_draft_filtering():
    """Correctly counts draft vs published pages."""

def test_asset_grouping_by_type():
    """Groups assets by extension correctly."""

def test_taxonomy_term_counting():
    """Counts pages per taxonomy term."""
```

### Integration Tests

```python
# tests/integration/cli/dashboard/test_api_integration.py

async def test_content_browser_reflects_site_structure():
    """Content browser shows actual site sections."""

async def test_build_phases_update_in_realtime():
    """Phase progress updates during build."""
```

---

## Success Criteria

1. ✅ All Site properties visible in dashboard
2. ✅ Pages browsable by section, date, tags, draft status
3. ✅ Assets browsable by type with size
4. ✅ Build phases stream in real-time
5. ✅ Full BuildStats displayed (all 20+ fields)
6. ✅ HealthReport properly categorized
7. ✅ File watcher events visible
8. ✅ Taxonomies explorable with page lists
9. ✅ No performance regression (<100ms dashboard startup)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Large sites slow browsing | Low | Medium | Virtual scrolling, lazy loading (Textual supports this) |
| Complex UI overwhelming | Low | Medium | Progressive disclosure, collapsible sections |
| Core changes break existing behavior | Low | High | Keep callbacks optional with `None` defaults |

### Mitigated Risks (From Analysis)

| Original Risk | Resolution |
|---------------|------------|
| "BuildOrchestrator lacks callbacks" | ✅ **Easy to add** - ~2 hours, callbacks are optional |
| "DevServer not integrated" | ✅ **Easy to add** - ~1 hour per feature |
| "APIs may not expose needed data" | ✅ **Already exposed** - 95% of data available through existing APIs |

---

## Dependencies on Bengal Core

### ✅ No Changes Needed (95% of Features)

These features use existing APIs with zero core changes:

- `Site.*` properties (title, theme, baseurl, config)
- `Site.pages`, `Page.*` (all page metadata)
- `Site.sections`, `Section.*` (hierarchy, subsections)
- `Site.assets`, `Asset.*` (file info)
- `Site.taxonomies` (terms, page assignments)
- `Site.data` (data files)
- `BuildStats` (all 20+ fields already populated)
- `HealthReport`, `CheckResult` (already structured)
- `GraphAnalyzer.analyze()` (link graph)

### 🆕 New Middleware Required (3 Items)

These enable real-time/streaming features and are worth implementing:

#### 1. BuildOrchestrator Phase Callbacks (~2 hours)

**Purpose**: Stream build progress instead of waiting for completion

**Current State**: `BuildOrchestrator.build()` returns `BuildStats` only at the end

**Proposed Changes**:

```python
# bengal/orchestration/build/__init__.py

def build(
    self,
    options: BuildOptions | None = None,
    *,
    # ... existing params ...
    # NEW: Streaming callbacks
    on_phase_start: Callable[[str], None] | None = None,
    on_phase_complete: Callable[[str, float, str], None] | None = None,
) -> BuildStats:
    """
    Args:
        on_phase_start: Called when phase begins (phase_name)
        on_phase_complete: Called when phase ends (phase_name, time_ms, details)
    """
```

**Integration Points**:
- Each `with self.logger.phase("name"):` block calls callbacks
- Or: Create `PhaseReporter` that wraps existing phase calls

**Value**: Users see "Discovery... Taxonomies... Rendering 50%..." instead of blank screen

---

#### 2. File Watcher Event Bridge (~1 hour)

**Purpose**: Show file changes that trigger rebuilds in dashboard

**Current State**: `WatcherRunner` → `BuildTrigger` is internal, dashboard can't see events

**Proposed Changes**:

```python
# bengal/server/watcher_runner.py

class WatcherRunner:
    def __init__(
        self,
        # ... existing params ...
        on_file_change: Callable[[set[Path], set[str]], None] | None = None,
    ):
        """
        Args:
            on_file_change: Called when files change (paths, event_types)
                            event_types: {"created", "modified", "deleted"}
        """
```

**Integration Points**:
- Call callback in `_run_build_trigger` before triggering build
- Or: Use Textual's `Signal` system for decoupled messaging

**Value**: Users see "content/post.md modified → rebuild triggered" instead of just "rebuilding..."

---

#### 3. HTTP Request Logging (~1 hour)

**Purpose**: Show dev server requests in dashboard

**Current State**: `BengalRequestHandler` serves requests but doesn't log them to dashboard

**Proposed Changes**:

```python
# bengal/server/request_handler.py

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

    def do_GET(self):
        start = time.time()
        # ... existing handling ...
        entry = RequestLogEntry(
            timestamp=datetime.now(),
            method="GET",
            path=self.path,
            status=status_code,
            duration_ms=(time.time() - start) * 1000,
        )
        if self.on_request:
            self.on_request(entry)
```

**Value**: Users see live request stream, catch 404s, understand what's being served

---

### Why These Are Worth Doing

| Feature | User Pain Point Solved |
|---------|------------------------|
| Phase streaming | "Build takes 5s and I don't know if it's stuck" |
| File change events | "Something triggered a rebuild but I don't know what" |
| Request logging | "Page isn't loading but I don't know if server is receiving requests" |

**Total effort**: ~4 hours of core changes, enabling a much richer dashboard experience

---

## Relationship to Other RFCs

| RFC | Focus | This RFC |
|-----|-------|----------|
| `rfc-dashboard-content-enrichment` | Display existing stats | **Goes deeper**: Browse pages, sections, assets |
| `rfc-toad-inspired-enhancements` | Toad UI patterns | **Builds on**: Uses widgets to display rich data |
| `rfc-dashboard-api-integration` (this) | Deep API integration | Comprehensive Bengal data access |

**Sequence**: Toad patterns → Content enrichment → **API integration (this)**

---

## References

- [Bengal Site class](../../bengal/core/site/core.py)
- [Bengal Page class](../../bengal/core/page/__init__.py)
- [Bengal Section class](../../bengal/core/section.py)
- [Bengal BuildStats](../../bengal/orchestration/stats/models.py)
- [Bengal HealthReport](../../bengal/health/report.py)
- [Bengal DevServer](../../bengal/server/dev_server.py)
- [Bengal GraphAnalyzer](../../bengal/analysis/graph_analysis.py)
