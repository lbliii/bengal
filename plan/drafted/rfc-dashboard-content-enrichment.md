# RFC: Dashboard Content Enrichment

**Status**: Draft  
**Created**: 2024-12-21  
**Depends On**: Terminal UX with Textual (implemented)  
**Estimated Time**: 3-5 days

---

## Summary

The Textual dashboard infrastructure is complete, but panels are sparse and low-information. This RFC proposes enriching dashboard content with real-time stats, meaningful visualizations, and actionable information to make the dashboards genuinely useful.

---

## Problem Statement

Current dashboard state:

| Dashboard | Issue |
|-----------|-------|
| **Build** | Phase table works, but no build profiling or cache stats |
| **Serve** | Sparkline empty until rebuilds; Stats tab is placeholder |
| **Health** | Shows demo mode; needs richer issue categorization |
| **All** | Large empty spaces; panels lack actionable content |

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

---

## Proposed Changes

### Phase 1: Build Dashboard Enrichment (1 day)

#### 1.1 Add Build Statistics Panel

Replace empty space with real stats:

```
┌─ Build Statistics ─────────────────┐
│ Pages:      142  │  Cache Hits: 89%│
│ Assets:      47  │  Memory: 128 MB │
│ Templates:   12  │  Threads: 4     │
│ Last Build: 1.2s │  Incremental: ✓ │
└────────────────────────────────────┘
```

**Source data**:
- `site.pages` count
- `site.assets` count  
- `BuildOrchestrator.stats` (if available)
- `sys.getsizeof` / `tracemalloc` for memory
- Cache hit rate from `BuildCache`

#### 1.2 Add Phase Profiling

Show time breakdown per phase:

```
Phase          Time    %  
─────────────────────────────
Discovery      120ms   10%  ████
Taxonomies      80ms    7%  ███
Rendering      800ms   67%  ██████████████████████████
Assets         150ms   13%  █████
Postprocess     50ms    4%  ██
```

#### 1.3 Pre-populate Phase Table

Show expected phases before build starts (not empty):

```
Status  Phase        Time    Details
─────────────────────────────────────
·       Discovery    -       Waiting...
·       Taxonomies   -       Waiting...
·       Rendering    -       Waiting...
```

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

#### 2.2 Sparkline with Initial Data

Pre-populate sparkline with zeros so it's not blank:

```python
# Initialize with placeholder data
self.build_history = [0] * 10  # Shows a flat line initially
```

Update with real build times as they occur.

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

---

### Phase 3: Health Dashboard Enrichment (1 day)

#### 3.1 Multi-Category Health Checks

Expand beyond just links:

```
Health Report
├─ 🔗 Links (2 issues)
│  ├─ ⛔ /about → 404 (broken)
│  └─ ⚠️ /old-page → 301 (redirect)
├─ 📝 Frontmatter (1 issue)  
│  └─ ⚠️ Missing 'date' in 3 posts
├─ 🖼️ Images (0 issues)
│  └─ ✓ All 47 images valid
├─ ⚡ Performance (1 issue)
│  └─ ⚠️ 2 pages >500KB
└─ 📄 Content (0 issues)
   └─ ✓ No orphan pages
```

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

#### 3.3 Summary Statistics

Show aggregate health score:

```
Site Health: 94% ██████████████████░░
  142 pages checked
  47 images verified
  2 issues found (1 error, 1 warning)
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

Add contextual hints in footer:

```
[r] Rebuild  [o] Open Browser  [c] Clear  [?] Help  [q] Quit
```

---

## Implementation Plan

| Phase | Tasks | Days |
|-------|-------|------|
| 1 | Build stats, profiling, phase pre-pop | 1 |
| 2 | Serve stats, sparkline init, watcher | 1 |
| 3 | Health categories, details, score | 1 |
| 4 | Loading states, empty states, hints | 0.5 |
| **Total** | | **3.5** |

---

## Data Sources

### Build Dashboard
- `site.pages` - Page count
- `site.assets` - Asset count
- `BuildCache.stats()` - Cache hit rate
- `BuildOrchestrator.phase_times` - Phase profiling
- `tracemalloc` - Memory usage

### Serve Dashboard
- `time.time()` - Uptime calculation
- `build_history: list[float]` - Build times
- `watchfiles` stats - Watched file count
- Request counter (if server exposes it)

### Health Dashboard
- `LinkCheckOrchestrator` - Link validation
- `FrontmatterValidator` - Frontmatter checks
- `ImageValidator` - Image validation
- `PerformanceValidator` - Page size checks

---

## Migration

No breaking changes. All enhancements are additive.

Existing functionality:
- `--dashboard` flags continue to work
- Keyboard shortcuts unchanged
- CSS styling preserved

---

## Testing

- Unit tests for data extraction functions
- Manual testing of each panel with real sites
- Edge cases: empty sites, large sites, error states

---

## Success Criteria

1. ✅ No blank panels on dashboard launch
2. ✅ Useful info visible within 1 second
3. ✅ All stats backed by real data
4. ✅ Empty states guide users on next action
5. ✅ Existing tests continue to pass

---

## Risks

| Risk | Mitigation |
|------|------------|
| Performance overhead | Lazy-load stats; cache values |
| Data not available | Graceful fallback to "N/A" |
| Validator coupling | Abstract through interfaces |

---

## Alternatives Considered

1. **Defer indefinitely** - Ship as-is, enhance later
   - Rejected: Dashboards feel incomplete

2. **Add more widgets** - New panels, modes
   - Rejected: Infrastructure is fine, needs content

3. **Rich integration** - Use Rich panels alongside Textual
   - Rejected: Stick with pure Textual for consistency

---

## References

- [Terminal UX RFC](rfc-terminal-ux-style-guide.md) - Design system
- [Terminal UX Plan](plan-terminal-ux-textual.md) - Infrastructure plan
- [Textual docs](https://textual.textualize.io/) - Widget reference
