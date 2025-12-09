# RFC: Instant Dev Server Rebuilds

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 75% 🟡

---

## Executive Summary

Achieve sub-100ms page rebuilds during development by implementing streaming HTML delivery, surgical cache invalidation, and speculative pre-rendering. The goal: update the browser before the developer's eyes leave the editor.

---

## Problem Statement

### Current State

Bengal's dev server rebuilds pages when files change. While incremental builds help, the full cycle is:

```
File save → Detect change → Invalidate cache → Parse → Render → Respond → Browser refresh
```

**Evidence**:
- `bengal/server/dev_server.py`: File watcher triggers full page rebuild
- `bengal/orchestration/render_orchestrator.py`: Renders complete HTML before response

### Pain Points

1. **Latency**: Even with caching, rebuilds take 200-500ms for complex pages
2. **Full page**: Entire HTML regenerated even for small content changes
3. **Blocking**: Browser waits for complete response before any render
4. **Context switch**: Developer loses flow waiting for preview

### User Impact

Every 500ms delay compounds. A developer making 100 saves/hour loses 50 seconds to waiting—enough to break concentration and slow iteration.

---

## Goals & Non-Goals

**Goals**:
- Sub-100ms perceived rebuild time for content-only changes
- Streaming HTML delivery (browser starts rendering immediately)
- Surgical invalidation (only re-render what changed)
- Zero-config for users (just works)

**Non-Goals**:
- Production build optimization (different problem)
- Full re-architecture of rendering pipeline (incremental improvement)
- Browser-side JavaScript frameworks (keep it simple)

---

## Architecture Impact

**Affected Subsystems**:
- **Server** (`bengal/server/`): Streaming response, WebSocket for hot reload
- **Cache** (`bengal/cache/`): Fine-grained invalidation, partial page caching
- **Rendering** (`bengal/rendering/`): Chunked output, template segmentation
- **Orchestration** (`bengal/orchestration/`): Speculative pre-rendering

---

## Design Options

### Option A: Streaming HTML with Chunked Encoding (Recommended)

**Concept**: Send HTML in chunks as it's generated. Browser starts rendering immediately.

**How it works**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Request   │────▶│   Server    │────▶│   Browser   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ 1. Send <head> immediately  │ ◀─ 10ms
            │ 2. Send nav/sidebar (cached)│ ◀─ 20ms
            │ 3. Render content (async)   │
            │ 4. Stream content chunks    │ ◀─ 50-200ms
            │ 5. Send footer/scripts      │ ◀─ 10ms
            └─────────────────────────────┘
```

**Implementation**:
```python
# bengal/server/streaming.py
async def stream_page(page: Page, response: StreamingResponse):
    # Immediately send shell (cached)
    yield render_shell_head(page)
    yield render_navigation(site)  # Likely unchanged, cached
    
    # Open content container
    yield '<main class="content">'
    
    # Stream content as it renders
    async for chunk in render_content_streaming(page):
        yield chunk
    
    yield '</main>'
    yield render_footer()
    yield render_scripts()
```

**Pros**:
- First paint in <50ms
- Works with existing templates (with modifications)
- Progressive enhancement

**Cons**:
- Template restructuring needed (segment into streamable chunks)
- Error handling more complex (can't change headers mid-stream)

---

### Option B: WebSocket-Based Hot Module Replacement

**Concept**: Keep persistent WebSocket connection. On change, send only the diff.

**How it works**:
```
┌─────────────┐     WebSocket     ┌─────────────┐
│   Browser   │◀─────────────────▶│   Server    │
└─────────────┘                   └─────────────┘
       │                                │
       │  1. Initial full page          │
       │◀───────────────────────────────│
       │                                │
       │  2. File changes               │
       │                                │
       │  3. Send DOM patch             │
       │◀───────────────────────────────│
       │  { replace: "#content",        │
       │    html: "<p>New text</p>" }   │
       │                                │
       │  4. Apply patch (JS)           │
       ▼                                ▼
```

**Implementation**:
```python
# bengal/server/hot_reload.py
class HotReloadServer:
    async def on_file_change(self, path: Path):
        page = self.site.get_page(path)
        
        # Render only the changed section
        if change_type == "content_only":
            new_html = render_content_only(page)
            patch = {"selector": ".page-content", "html": new_html}
        elif change_type == "frontmatter":
            new_html = render_full_page(page)
            patch = {"selector": "body", "html": new_html}
        
        await self.broadcast({"type": "patch", "data": patch})
```

**Browser-side JS**:
```javascript
// Injected by dev server
const ws = new WebSocket('ws://localhost:8000/_bengal/ws');
ws.onmessage = (event) => {
    const { type, data } = JSON.parse(event.data);
    if (type === 'patch') {
        document.querySelector(data.selector).innerHTML = data.html;
    }
};
```

**Pros**:
- True instant updates (no full page reload)
- Can preserve scroll position, form state
- Minimal data transfer

**Cons**:
- Requires JavaScript in dev mode
- More complex diffing logic
- State synchronization challenges

---

### Option C: Speculative Pre-Rendering

**Concept**: Pre-render pages the developer is likely to edit next.

**How it works**:
```
Developer edits: docs/guide.md

System predicts next edits:
├─ docs/guide.md (current - always hot)
├─ docs/tutorial.md (sibling - likely)
├─ docs/_index.md (parent - likely)
└─ templates/doc.html (template - possible)

Pre-render these in background, cache results.
```

**Implementation**:
```python
# bengal/server/speculative.py
class SpeculativeRenderer:
    def __init__(self):
        self.hot_pages: dict[str, RenderedPage] = {}
        self.access_history: list[str] = []
    
    def predict_next_edits(self, current: Page) -> list[Page]:
        """Predict pages likely to be edited next."""
        candidates = []
        
        # Siblings
        candidates.extend(current.section.pages[:5])
        
        # Recently accessed
        candidates.extend(self.get_recent_pages(5))
        
        # Linked pages
        candidates.extend(current.outgoing_links[:3])
        
        return candidates
    
    async def warm_cache(self, pages: list[Page]):
        """Pre-render predicted pages in background."""
        async with TaskGroup() as tg:
            for page in pages:
                tg.create_task(self.render_and_cache(page))
```

**Pros**:
- Zero perceived latency for predicted pages
- Works transparently
- Utilizes idle time

**Cons**:
- Prediction accuracy varies
- Memory overhead for cached renders
- CPU usage during "idle" time

---

## Recommended Approach: Hybrid

Combine all three options:

1. **Streaming HTML** for initial page loads (Option A)
2. **WebSocket HMR** for incremental updates (Option B)
3. **Speculative pre-rendering** for predicted edits (Option C)

```
┌─────────────────────────────────────────────────────────────┐
│                     Dev Server Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Watcher    │───▶│  Invalidator │───▶│  Predictor   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ WebSocket    │    │   Cache      │    │  Pre-render  │  │
│  │ Broadcaster  │    │   Manager    │    │   Queue      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             ▼                              │
│                    ┌──────────────┐                        │
│                    │  Streaming   │                        │
│                    │  Response    │                        │
│                    └──────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Surgical Cache Invalidation (1-2 weeks)

**Goal**: Only invalidate what actually changed.

```python
# bengal/cache/invalidation.py
class SurgicalInvalidator:
    def invalidate(self, path: Path, change_type: ChangeType) -> set[str]:
        """Return minimal set of cache keys to invalidate."""
        
        if change_type == ChangeType.CONTENT_BODY:
            # Only content changed, not frontmatter
            return {f"content:{path}"}
        
        elif change_type == ChangeType.FRONTMATTER:
            # Frontmatter changed, may affect navigation
            page = self.site.get_page(path)
            keys = {f"page:{path}", f"content:{path}"}
            if "title" in changed_fields:
                keys.add(f"nav:{page.section.path}")
            return keys
        
        elif change_type == ChangeType.TEMPLATE:
            # Template changed, all pages using it
            return {f"page:{p.path}" for p in self.get_pages_using(path)}
```

### Phase 2: Streaming Response (2-3 weeks)

**Goal**: Send HTML chunks as they're ready.

- Restructure base template into streamable segments
- Implement chunked transfer encoding
- Add `render_streaming()` method to render orchestrator

### Phase 3: WebSocket Hot Reload (2-3 weeks)

**Goal**: Push updates without page reload.

- Add WebSocket endpoint to dev server
- Implement DOM diffing and patching
- Inject hot reload client script in dev mode

### Phase 4: Speculative Pre-rendering (1-2 weeks)

**Goal**: Pre-render likely next edits.

- Build prediction model based on file proximity and access patterns
- Background render queue with priority
- Memory-bounded LRU cache for pre-rendered pages

---

## Performance Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Content-only change | 300-500ms | <100ms | Surgical invalidation + streaming |
| Frontmatter change | 400-600ms | <150ms | Partial re-render + HMR |
| Template change | 1-2s | <500ms | Speculative + streaming |
| First contentful paint | 400ms | <50ms | Streaming HTML |
| Time to interactive | 600ms | <100ms | HMR (no reload) |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Template restructuring breaks existing themes | High | Medium | Provide migration guide, maintain backward compat |
| WebSocket complexity increases bugs | Medium | Medium | Extensive testing, fallback to full reload |
| Prediction misses waste CPU | Low | Low | Bounded pre-render queue, adaptive prediction |
| Streaming errors hard to debug | Medium | Medium | Detailed error logging, graceful degradation |

---

## Open Questions

1. **How to handle errors mid-stream?**
   - Option: Error boundary component, client-side error overlay

2. **Should HMR be opt-in or opt-out?**
   - Recommendation: Opt-out (enabled by default in dev)

3. **Memory budget for speculative cache?**
   - Proposal: 100MB default, configurable

4. **How to handle CSS/JS changes?**
   - Full page reload for now, CSS HMR as future enhancement

---

## Success Criteria

- [ ] Content changes reflect in browser in <100ms
- [ ] First paint occurs in <50ms after request
- [ ] Developer can disable HMR if needed
- [ ] No regressions in production build quality
- [ ] Memory usage stays bounded in long dev sessions

---

## References

- [Streaming SSR in React 18](https://react.dev/reference/react-dom/server/renderToPipeableStream)
- [Vite HMR](https://vitejs.dev/guide/features.html#hot-module-replacement)
- [HTTP Chunked Transfer Encoding](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding)
- [LiveReload Protocol](http://livereload.com/api/protocol/)

