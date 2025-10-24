# RFC: Dev Server Link Checker Overlay

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2025-10-24  
**Updated**: 2025-10-24

---

## Summary

Add an optional, on-demand link checking overlay to the development server that allows developers to quickly identify and fix broken links during local development without impacting hot reload performance.

## Motivation

### Problem

Broken links are a common issue in documentation sites that often go unnoticed until deployment:

1. **Current workflow is disconnected**: Developers must run `bengal health linkcheck` separately from `bengal site serve`, switching between terminal and browser
2. **Context switching overhead**: Finding broken links requires reading terminal output, then manually locating the source file
3. **Delayed feedback**: Link issues discovered late in development or after deployment
4. **CI-only validation**: Teams often only catch link issues in CI, requiring fix → commit → push → wait cycles

### Goals

1. **Zero performance impact on hot reload**: Link checking must not slow down the development feedback loop
2. **In-context feedback**: Show broken links directly in the browser where developers are working
3. **On-demand execution**: Developer controls when to check links (not automatic)
4. **Actionable information**: Display broken links with source file references for quick fixes
5. **Dev-only feature**: No impact on production builds or final output

### Non-Goals

1. **Real-time link checking**: Not checking links on every file save (too slow)
2. **External link checking in dev**: Only internal links (external checks can take 30+ seconds)
3. **Auto-fix functionality**: Just detection and reporting, not automated fixes
4. **Production mode**: This is strictly a development tool

---

## Current State

### Existing Link Checker (`bengal health linkcheck`)

```bash
$ bengal health linkcheck
✨ Loaded 292 pages
✨ Site built successfully
Checking links (internal: True, external: False)...
✨ JSON report saved to linkcheck-report.json
```

**Strengths:**
- Works standalone and in CI
- Comprehensive checking (internal + external)
- JSON output for tooling integration
- ~1.2 seconds for internal links (Bengal site: 292 pages, 1,300+ links)

**Weaknesses for dev workflow:**
- Separate command from dev server
- Terminal-only output (not in-context)
- Requires manual file lookup after finding issues
- No live feedback loop

### Existing Dev Server

**Current architecture:**
```
bengal/server/
├── dev_server.py       # Flask app + file watcher
├── request_handler.py  # HTTP request handling
├── build_handler.py    # Rebuild coordination
└── utils.py           # WebSocket, reload coordination
```

**Hot reload flow:**
```
File change → BuildHandler → Site.build() → WebSocket → Browser reload
                                                    ↓
                                               ~0.5-1s (fast!)
```

**Dev-only features already present:**
- WebSocket connection for hot reload
- Dev toolbar injection (via base template check)
- `dev_server=True` config flag
- Error overlay for build failures

---

## Proposed Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Dev Mode)                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Floating Dev Toolbar                                │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ 🔗 Links: 5 broken ⟳ Check Links [×]          │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ Broken Links Overlay (expandable)              │ │  │
│  │  │  • /blog/ - Page not found                     │ │  │
│  │  │    → Found in: index.html                      │ │  │
│  │  │  • /tags/ - Page not found                     │ │  │
│  │  │    → Found in: 404.html                        │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ↑                                     │
│                        │ fetch('/bengal-dev/linkcheck')     │
│                        ↓                                     │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────┐
│  Dev Server (Python)   ↓                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  New Endpoint: /bengal-dev/linkcheck                 │  │
│  │  ├─ Check if cached (< 30s old) → Return cache      │  │
│  │  ├─ Run LinkCheckOrchestrator (internal only)       │  │
│  │  └─ Cache results + return JSON                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### User Flow

**Scenario 1: Initial page load**
1. Developer runs `bengal site serve`
2. Server starts, runs initial linkcheck in background
3. Browser opens to `http://localhost:5173`
4. Dev toolbar shows: "🔗 Links: 5 broken" (badge only, collapsed)
5. Developer clicks badge → overlay expands with details

**Scenario 2: Developer makes changes**
1. Developer edits content, saves file
2. Hot reload happens (~0.5s, no linkcheck)
3. Developer sees changes immediately
4. Developer clicks "⟳ Check Links" when ready
5. Button shows spinner, request to `/bengal-dev/linkcheck`
6. Results update in ~1-2s, overlay refreshes

**Scenario 3: Dismissing overlay**
1. Developer clicks [×] to dismiss
2. Badge remains visible: "🔗 5 broken"
3. LocalStorage remembers dismissal (per-session)
4. Click badge to re-open overlay

---

## Implementation Plan

### Phase 1: Backend API Endpoint

**File: `bengal/server/dev_server.py`**

```python
# Add to DevServer class
@app.route('/bengal-dev/linkcheck')
def dev_linkcheck():
    """
    Run link checker and return results (dev mode only).

    Returns JSON with broken links (internal only, cached 30s).
    """
    if not app.config.get('dev_mode'):
        return jsonify({'error': 'Dev mode only'}), 403

    # Check cache (30 second TTL)
    cache_key = 'linkcheck_results'
    cached = app.config.get(cache_key)
    if cached and time.time() - cached['timestamp'] < 30:
        return jsonify(cached['data'])

    # Run internal link check only (fast: ~1-2s)
    from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator
    orchestrator = LinkCheckOrchestrator(
        site,
        check_internal=True,
        check_external=False,  # External too slow for dev
        config={}
    )

    results, summary = orchestrator.check_all_links()

    # Format for frontend
    broken = [
        {
            'url': r.url,
            'reason': r.reason,
            'first_ref': r.first_ref,
            'ref_count': r.ref_count,
        }
        for r in results if r.status == 'broken'
    ][:50]  # Limit to top 50

    response_data = {
        'summary': {
            'total': summary.total_checked,
            'ok': summary.ok,
            'broken': summary.broken,
            'duration_ms': summary.duration_ms,
        },
        'broken_links': broken,
        'timestamp': time.time(),
    }

    # Cache results
    app.config[cache_key] = {
        'data': response_data,
        'timestamp': time.time()
    }

    return jsonify(response_data)
```

**Initial check on server start:**

```python
# In DevServer.__init__() or after initial build
def _run_initial_linkcheck(self):
    """Run linkcheck after initial build (background thread)."""
    import threading

    def check_links():
        # Wait for initial build to complete
        time.sleep(2)
        # Pre-warm cache by calling endpoint
        try:
            with app.test_client() as client:
                client.get('/bengal-dev/linkcheck')
        except Exception as e:
            logger.debug("initial_linkcheck_failed", error=str(e))

    thread = threading.Thread(target=check_links, daemon=True)
    thread.start()
```

### Phase 2: Frontend Overlay

**File: `bengal/themes/default/assets/js/dev-linkcheck.js`**

```javascript
/**
 * Dev-only link checker overlay
 *
 * Features:
 * - Floating badge with broken link count
 * - Expandable overlay with details
 * - On-demand refresh
 * - LocalStorage for dismissal state
 */

class DevLinkChecker {
  constructor() {
    this.overlayVisible = !localStorage.getItem('bengal-linkcheck-dismissed');
    this.lastCheck = null;
    this.init();
  }

  async init() {
    this.createUI();
    await this.fetchResults();
  }

  createUI() {
    // Create floating toolbar
    const toolbar = document.createElement('div');
    toolbar.id = 'bengal-dev-linkcheck';
    toolbar.className = 'bengal-dev-toolbar';
    toolbar.innerHTML = `
      <div class="bengal-linkcheck-badge">
        🔗 <span id="bengal-link-count">-</span>
        <button id="bengal-linkcheck-refresh" title="Refresh">⟳</button>
        <button id="bengal-linkcheck-toggle">▼</button>
      </div>
      <div class="bengal-linkcheck-overlay" style="display: none;">
        <div class="bengal-linkcheck-header">
          <h3>Broken Links</h3>
          <button id="bengal-linkcheck-close">×</button>
        </div>
        <div id="bengal-linkcheck-content">Loading...</div>
      </div>
    `;
    document.body.appendChild(toolbar);

    // Event listeners
    document.getElementById('bengal-linkcheck-refresh').addEventListener('click', () => this.refresh());
    document.getElementById('bengal-linkcheck-toggle').addEventListener('click', () => this.toggle());
    document.getElementById('bengal-linkcheck-close').addEventListener('click', () => this.dismiss());
  }

  async fetchResults(forceRefresh = false) {
    const url = '/bengal-dev/linkcheck' + (forceRefresh ? '?refresh=1' : '');

    try {
      const response = await fetch(url);
      const data = await response.json();
      this.lastCheck = data;
      this.updateUI(data);
    } catch (error) {
      console.error('Link check failed:', error);
    }
  }

  updateUI(data) {
    const count = data.summary.broken;
    document.getElementById('bengal-link-count').textContent =
      count > 0 ? `${count} broken` : '✓';

    const content = document.getElementById('bengal-linkcheck-content');

    if (count === 0) {
      content.innerHTML = '<p class="success">✓ All links working!</p>';
    } else {
      const list = data.broken_links.map(link => `
        <div class="broken-link">
          <div class="broken-link-url">${link.url}</div>
          <div class="broken-link-reason">${link.reason}</div>
          <div class="broken-link-ref">Found in: ${link.first_ref}</div>
        </div>
      `).join('');

      content.innerHTML = `
        <div class="broken-link-summary">
          Found ${count} broken link${count > 1 ? 's' : ''}
        </div>
        ${list}
      `;
    }
  }

  async refresh() {
    const btn = document.getElementById('bengal-linkcheck-refresh');
    btn.textContent = '⟳';
    btn.classList.add('spinning');

    await this.fetchResults(true);

    btn.classList.remove('spinning');
  }

  toggle() {
    const overlay = document.querySelector('.bengal-linkcheck-overlay');
    const btn = document.getElementById('bengal-linkcheck-toggle');

    if (overlay.style.display === 'none') {
      overlay.style.display = 'block';
      btn.textContent = '▲';
      localStorage.removeItem('bengal-linkcheck-dismissed');
    } else {
      overlay.style.display = 'none';
      btn.textContent = '▼';
    }
  }

  dismiss() {
    document.querySelector('.bengal-linkcheck-overlay').style.display = 'none';
    document.getElementById('bengal-linkcheck-toggle').textContent = '▼';
    localStorage.setItem('bengal-linkcheck-dismissed', 'true');
  }
}

// Initialize on dev mode only
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  new DevLinkChecker();
}
```

**File: `bengal/themes/default/assets/css/dev-linkcheck.css`**

```css
/* Dev-only link checker overlay */
.bengal-dev-toolbar {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 10000;
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 14px;
}

.bengal-linkcheck-badge {
  background: #2563eb;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  cursor: pointer;
}

.bengal-linkcheck-badge button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.bengal-linkcheck-badge button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.bengal-linkcheck-badge button.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.bengal-linkcheck-overlay {
  position: absolute;
  bottom: 50px;
  right: 0;
  width: 400px;
  max-height: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.bengal-linkcheck-header {
  background: #1e293b;
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bengal-linkcheck-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.bengal-linkcheck-header button {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

#bengal-linkcheck-content {
  padding: 16px;
  max-height: 420px;
  overflow-y: auto;
}

.broken-link {
  padding: 12px;
  margin-bottom: 12px;
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  border-radius: 4px;
}

.broken-link-url {
  font-weight: 600;
  color: #dc2626;
  margin-bottom: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

.broken-link-reason {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 4px;
}

.broken-link-ref {
  color: #94a3b8;
  font-size: 12px;
  font-style: italic;
}

.broken-link-summary {
  background: #fee2e2;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  color: #991b1b;
  font-weight: 500;
}

.success {
  color: #16a34a;
  font-weight: 500;
  text-align: center;
  padding: 20px;
}
```

### Phase 3: Theme Integration

**File: `bengal/themes/default/templates/base.html`**

```jinja2
{% if site.config.get('dev_server') %}
  {# Dev-only link checker overlay #}
  <link rel="stylesheet" href="{{ 'css/dev-linkcheck.css' | asset_url }}">
  <script src="{{ 'js/dev-linkcheck.js' | asset_url }}" defer></script>
{% endif %}
```

---

## Performance Analysis

### Measurements (Bengal site: 292 pages, 1,300+ links)

| Operation | Time | Impact |
|-----------|------|--------|
| Hot reload (current) | 0.5s | None (baseline) |
| Internal link check | 1.2s | Not on hot reload |
| External link check | 30-60s | Disabled in dev |
| API endpoint (cached) | 5ms | Negligible |
| API endpoint (fresh) | 1.2s | Only on-demand |

### Performance Guarantees

1. **Zero impact on hot reload**: Link checking never blocks file watch → rebuild → reload cycle
2. **Cached responses**: 30-second TTL prevents redundant checks
3. **Internal links only**: External checks too slow for dev experience
4. **Async initial check**: Background thread after server start
5. **Limited results**: Top 50 broken links (prevent huge payloads)

### Worst Case Scenarios

**Large site (1,000 pages, 5,000 links):**
- Initial check: ~5-8 seconds (background, doesn't block)
- On-demand check: ~5-8 seconds (with spinner, user-triggered)
- Cache hit: <10ms

**Still acceptable** because it's on-demand and shows progress feedback.

---

## Alternatives Considered

### Alternative 1: Auto-check on Every Rebuild

**Pros:**
- Always up-to-date results
- No manual action needed

**Cons:**
- ❌ 3x slowdown on hot reload (0.5s → 1.7s)
- ❌ Breaks fast feedback loop
- ❌ Annoying for rapid iterations

**Verdict:** Rejected - performance impact unacceptable

### Alternative 2: Incremental Link Checking

**Concept:** Only check links in changed files + pages linking to them

**Pros:**
- Fast (~100ms for 5-10 links)
- Could run on every rebuild

**Cons:**
- ❌ Complex implementation (dependency tracking)
- ❌ Might miss cascading issues
- ❌ Still ~2x slower than no checking

**Verdict:** Interesting for future, but over-engineered for v1

### Alternative 3: WebSocket Live Updates

**Concept:** Server pushes linkcheck results via WebSocket

**Pros:**
- No polling needed
- Real-time updates

**Cons:**
- ❌ Overkill for occasional checks
- ❌ Complexity for minimal benefit
- ❌ WebSocket already used for hot reload

**Verdict:** Rejected - REST endpoint simpler and sufficient

### Alternative 4: CLI Terminal Output Only

**Current state** - no browser integration

**Pros:**
- Simple, already works
- No code changes needed

**Cons:**
- ❌ Context switching (terminal ↔ browser)
- ❌ No in-context feedback
- ❌ Manual file lookup

**Verdict:** Rejected - doesn't solve the UX problem

---

## Open Questions

1. **Should we show warnings (e.g., external link slow response)?**
   - **Proposal**: No, keep it simple - only broken links
   - Warnings can be verbose, overlay should be actionable only

2. **Should we provide "Copy to clipboard" for broken link list?**
   - **Proposal**: Yes, add button to copy markdown list of broken links
   - Useful for filing issues or commit messages

3. **Should we link directly to source files in editor?**
   - **Proposal**: Future enhancement - `vscode://file/path/to/file.md`
   - Requires editor protocol support, defer to v2

4. **Should we persist overlay state across page navigations?**
   - **Proposal**: No, overlay resets on navigation (new page, new context)
   - LocalStorage only persists dismissal state

5. **Should we support external link checking in dev?**
   - **Proposal**: Optional toggle, default OFF (too slow)
   - Advanced users can enable if needed

---

## Migration & Rollout

### Backwards Compatibility

- ✅ No breaking changes
- ✅ Opt-in via dev server (no config needed)
- ✅ Production builds unchanged
- ✅ Works with existing `bengal health linkcheck` CLI

### Feature Flag

```toml
# bengal.toml (optional config)
[dev_server]
enable_linkcheck_overlay = true  # Default: true
linkcheck_cache_ttl = 30         # Seconds, default: 30
linkcheck_max_results = 50       # Limit results, default: 50
```

### Testing Strategy

1. **Unit tests**: API endpoint returns correct JSON format
2. **Integration tests**: Full dev server with linkcheck overlay
3. **Manual testing**: Test on Bengal docs site (292 pages)
4. **Performance tests**: Verify no hot reload regression

### Documentation

- Add to `docs/dev-server.md`: "Link Checker Overlay" section
- Add to `docs/health.md`: Note about dev mode integration
- Screenshot/GIF of overlay in action
- Troubleshooting section for common issues

---

## Success Metrics

**Goal: Improve developer experience without sacrificing performance**

### Quantitative

- ✅ Hot reload speed: <1s (unchanged)
- ✅ Linkcheck on-demand: <2s for internal links
- ✅ API response (cached): <50ms
- ✅ Zero production build impact

### Qualitative

- ✅ Developers discover broken links during dev, not in CI
- ✅ No terminal → browser → terminal context switching
- ✅ In-context feedback (see issue in same window)
- ✅ Optional/dismissible (not intrusive)

---

## Future Enhancements

### v1.1: Enhanced Click Actions

- Click broken link → highlight in source (if file viewer available)
- Click source file → open in editor (protocol handlers)
- Copy broken link list as markdown

### v1.2: Incremental Link Checking

- Track link dependencies
- Only check changed pages + referencing pages
- Enable auto-check on rebuild (if fast enough <200ms)

### v1.3: Link Health Insights

- Trend over time (broken links chart)
- Most common failure reasons
- Suggest fixes (e.g., typos, renamed pages)

### v2.0: Multi-Site Link Validation

- Check cross-project references (intersphinx-style)
- Validate external links periodically (background job)
- Integration with deployment previews

---

## References

- [Link Checker Implementation](../../bengal/health/linkcheck/)
- [Dev Server Architecture](../../bengal/server/)
- [Hot Reload System](../../bengal/server/utils.py)
- [Theme Dev Toolbar](../../bengal/themes/default/templates/base.html)

---

## Appendix: Example API Response

```json
{
  "summary": {
    "total": 1362,
    "ok": 1347,
    "broken": 15,
    "duration_ms": 1192.4
  },
  "broken_links": [
    {
      "url": "/bengal/blog/",
      "reason": "Page not found",
      "first_ref": "404.html",
      "ref_count": 2
    },
    {
      "url": "/bengal/tags/",
      "reason": "Page not found",
      "first_ref": "404.html",
      "ref_count": 1
    }
  ],
  "timestamp": 1729728000.0
}
```

---

## Approval & Next Steps

**Approval Checklist:**
- [ ] Technical design approved
- [ ] Performance benchmarks acceptable
- [ ] UX mockup reviewed
- [ ] Security considerations addressed (dev-only, no sensitive data)
- [ ] Documentation plan agreed

**Implementation Timeline:**
- Phase 1 (Backend): 2-3 hours
- Phase 2 (Frontend): 3-4 hours
- Phase 3 (Integration): 1 hour
- Testing & Polish: 2-3 hours
- **Total: ~8-10 hours**

**Priority:** Medium (nice-to-have developer experience improvement)
