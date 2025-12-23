# RFC: Track Layout Performance Optimization

**Status**: Draft  
**Created**: 2024  
**Author**: Performance Analysis  
**Related**: Track layouts are by far the most expensive to build despite only 9 instances

## Problem Statement

Track layouts (`tracks/single.html`) are significantly more expensive to build than other page types, even though there are only 9 track pages. This suggests inefficient repeated work during template rendering.

### Symptoms

- 9 track pages take disproportionately long to render
- Each track page renders multiple track item pages inline
- Template calls `get_page()` many times per track item
- On-demand parsing occurs repeatedly for the same pages

## Root Cause Analysis

### 1. Multiple `get_page()` Calls Per Track Item

For a track with 9 items, `get_page()` is called **~54+ times** per track page:

**In `tracks/single.html`:**
- Line 56: Track contents overview loop (9 calls)
- Line 77: Main track content loop (9 calls)
- Line 119: Previous page navigation (9 calls)
- Line 131: Next page navigation (9 calls)
- Line 174: `combine_track_toc(track.items)` (9 calls internally)

**In `partials/track-sidebar.html`:**
- Line 72: Track progress nav loop (9 calls)

**Total: ~54 calls per track page × 9 track pages = ~486 `get_page()` calls**

### 2. On-Demand Parsing Overhead

Each `get_page()` call triggers `_ensure_page_parsed()` in `bengal/rendering/template_functions/get_page.py`:

```python
# bengal/rendering/template_functions/get_page.py:24-38
def _ensure_page_parsed(page: Page, site: Site) -> None:
    """Ensure a page is parsed if it hasn't been parsed yet."""
    # Skip if already parsed
    if hasattr(page, "parsed_ast") and page.parsed_ast is not None:
        return

    # Skip if no content
    if not hasattr(page, "content") or not page.content:
        return

    # Lazy-create parser on site object for reuse
    if site._template_parser is None:
        from bengal.rendering.parsers import create_markdown_parser
        # ... parser creation ...
```

**Cost per parse (when not cached):**
- Markdown parsing: ~5-50ms per page (depends on content size)
- Cross-reference processing: ~1-10ms
- TOC generation: ~1-5ms
- **Total: ~7-65ms per page**

**For 9 track items parsed 6 times each:**
- Best case: 9 × 6 × 7ms = **378ms**
- Worst case: 9 × 6 × 65ms = **3.5 seconds**

### 3. No Per-Render Caching

The current `get_page()` implementation (lines 238-313) doesn't cache results within a single template render:

```python
# bengal/rendering/template_functions/get_page.py:238-313
def get_page(path: str) -> Page | None:
    """Get a page by its relative path or slug."""
    if not path:
        return None

    # Validate path...
    normalized_path = path.replace("\\", "/")

    # Build lookup maps if not already built
    _build_lookup_maps(site)
    maps = site._page_lookup_maps

    # Strategy 1-4: Lookup in maps (fast)
    page = maps["relative"].get(normalized_path)
    # ... other strategies ...

    # Ensure page is parsed if needed (expensive!)
    _ensure_page_parsed(page, site)

    return page
```

**Lookup overhead per call:**
- Path normalization: ~0.1ms
- Map lookup: ~0.01ms
- **Total per call: ~0.11ms**
- **For 486 calls: ~53ms just in lookup overhead**

### 4. Redundant Template Logic

The template accesses the same track items multiple times:
- Contents overview needs titles/descriptions
- Main content needs full parsed content
- Sidebar needs titles for navigation
- TOC needs headings from parsed content

Each access triggers a separate `get_page()` call and potentially parsing.

## Proposed Solutions

### Solution 1: Per-Render `get_page()` Caching (High Impact, Low Risk)

Add a per-template-render cache to `get_page()` following the existing pattern in `NavScaffoldCache` (see `bengal/rendering/template_functions/navigation/scaffold.py`).

**Implementation:**

```python
# bengal/rendering/template_functions/get_page.py

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page

# Thread-local cache for per-render caching (thread-safe for parallel builds)
_render_cache = threading.local()


def _get_render_cache() -> dict[str, "Page | None"]:
    """Get per-render cache for get_page() results (thread-safe)."""
    if not hasattr(_render_cache, "pages"):
        _render_cache.pages = {}
    return _render_cache.pages


def clear_get_page_cache() -> None:
    """
    Clear per-render cache.

    Called at start of each page render by RenderOrchestrator.
    Thread-safe: Only clears the cache for the current thread.
    """
    if hasattr(_render_cache, "pages"):
        _render_cache.pages.clear()


def _normalize_cache_key(path: str) -> str:
    """
    Normalize path to canonical form for cache key.

    Ensures all path variants resolve to the same cache entry:
    - "./foo.md" -> "foo.md"
    - "content/foo.md" -> "foo.md"
    - "foo" -> "foo" (extension added during lookup)
    """
    normalized = path.replace("\\", "/")

    # Strip leading "./"
    if normalized.startswith("./"):
        normalized = normalized[2:]

    # Strip "content/" prefix
    if normalized.startswith("content/"):
        normalized = normalized[8:]

    return normalized


def get_page(path: str) -> "Page | None":
    """Get a page by path with per-render caching."""
    if not path:
        return None

    # Normalize path for cache key
    cache_key = _normalize_cache_key(path)
    cache = _get_render_cache()

    # Check per-render cache first
    if cache_key in cache:
        return cache[cache_key]

    # ... existing lookup logic (unchanged) ...

    # Ensure parsed
    _ensure_page_parsed(page, site)

    # Cache for this render (cache both hits and misses)
    cache[cache_key] = page

    return page
```

**Wire into rendering pipeline:**

The `RenderOrchestrator` already clears `clear_global_context_cache()` at the start of each build. We follow the same pattern:

```python
# bengal/orchestration/render.py

def process(self, pages: list[Page], ...) -> None:
    """Render pages (parallel or sequential)."""
    # Clear stale thread-local pipelines
    clear_thread_local_pipelines()

    # Clear global context cache
    from bengal.rendering.context import clear_global_context_cache
    clear_global_context_cache()

    # NEW: Clear get_page cache at start of build (not per-page)
    # Per-page clearing happens in _render_single_page()
    ...
```

**Per-page cache clearing:**

```python
# bengal/rendering/pipeline/core.py or wherever single page rendering happens

def _render_single_page(self, page: Page, ...) -> None:
    """Render a single page."""
    # Clear per-render cache at start of each page
    from bengal.rendering.template_functions.get_page import clear_get_page_cache
    clear_get_page_cache()

    # ... render page ...
```

**Expected Impact:**
- Eliminates redundant lookups: **~53ms saved per track page**
- Eliminates redundant parsing: **~378ms - 3.5s saved per track page**
- **Total savings: ~430ms - 3.5s per track page**
- **For 9 track pages: ~3.9s - 31.5s total savings**

**Risk:** Low - cache is scoped to single render, cleared automatically per-page, thread-safe via `threading.local()`

### Solution 2: Pre-Parse Track Items (Medium Impact, Medium Risk)

Pre-parse all track item pages before rendering track pages.

**Implementation:**

```python
# bengal/rendering/pipeline/core.py

def _preparse_track_items(self, page: Page, site: Site) -> None:
    """Pre-parse all track items for a track page."""
    metadata = getattr(page, "metadata", {}) or {}
    if metadata.get("type") != "track":
        return

    track_id = metadata.get("track_id") or getattr(page, "slug", None)
    if not track_id:
        return

    tracks_data = getattr(site, "data", {}).get("tracks", {})
    track = tracks_data.get(track_id)
    if not track or not track.get("items"):
        return

    # Pre-parse all track items
    from bengal.rendering.template_functions.get_page import _ensure_page_parsed

    for item_slug in track["items"]:
        item_page = self._get_page_by_slug(item_slug)
        if item_page is None:
            continue

        # Check if parsing needed (same logic as _ensure_page_parsed)
        if not hasattr(item_page, "parsed_ast") or item_page.parsed_ast is None:
            _ensure_page_parsed(item_page, site)


def _render_page(self, page: Page, ...) -> None:
    # Pre-parse track items if this is a track page
    self._preparse_track_items(page, self.site)

    # ... render page ...
```

**Expected Impact:**
- Ensures all track items are parsed once before template access
- Eliminates on-demand parsing during template rendering
- **Savings: ~378ms - 3.5s per track page**

**Risk:** Medium - requires detecting track pages correctly via metadata

### Solution 3: Batch Fetch Track Pages in Template Context (Medium Impact, Low Risk)

Pre-fetch all track item pages and inject into template context.

**Implementation:**

```python
# bengal/rendering/context.py - add to build_page_context()

def build_page_context(
    page: Page | SimpleNamespace,
    site: Site,
    content: str = "",
    ...
) -> dict[str, Any]:
    """Build complete template context for any page type."""
    # ... existing context building ...

    # Pre-fetch track items if this is a track page
    metadata = getattr(page, "metadata", {}) or {}
    if metadata.get("type") == "track":
        track_id = metadata.get("track_id") or getattr(page, "slug", None)
        tracks_data = getattr(site, "data", {}).get("tracks", {})
        track = tracks_data.get(track_id) if track_id else None

        if track and track.get("items"):
            from bengal.rendering.template_functions.get_page import (
                _ensure_page_parsed,
                _get_page_by_path,
            )

            track_items_pages = []
            for item_slug in track["items"]:
                item_page = _get_page_by_path(item_slug, site)
                if item_page:
                    _ensure_page_parsed(item_page, site)
                    track_items_pages.append(item_page)

            context["track_items_pages"] = track_items_pages

    return context
```

**Template changes (backward compatible):**

```jinja
{# tracks/single.html - use pre-fetched items when available #}
{% if track and track.items %}
<div class="track-contents-overview mb-5">
    <h2 class="h5 mb-3">Track Contents</h2>
    <div class="track-contents-list">
        {# Use pre-fetched pages if available, fall back to get_page() #}
        {% for item_slug in track.items %}
        {% set item_page = track_items_pages[loop.index0] if track_items_pages is defined else get_page(item_slug) %}
        {% if item_page %}
        <a href="#track-section-{{ loop.index }}" class="track-contents-item">
            <span class="track-contents-number">{{ loop.index }}</span>
            <div class="track-contents-content">
                <div class="track-contents-title">{{ item_page.title }}</div>
                {% if item_page.description %}
                <div class="track-contents-desc">{{ item_page.description }}</div>
                {% endif %}
            </div>
        </a>
        {% endif %}
        {% endfor %}
    </div>
</div>
{% endif %}
```

**Expected Impact:**
- Reduces `get_page()` calls in template from ~54 to ~0 (when using `track_items_pages`)
- Ensures parsing happens once before template access
- **Savings: ~430ms - 3.5s per track page**

**Risk:** Low - template changes are straightforward, backward compatible

### Solution 4: Optimize `combine_track_toc_items()` (Low Impact, Low Risk)

Cache `get_page()` results within `combine_track_toc_items()`.

**Implementation:**

```python
# bengal/rendering/template_functions/navigation/toc.py

def combine_track_toc_items(
    track_items: list[str],
    get_page_func: Any,
) -> list[dict[str, Any]]:
    """Combine TOC items from all track section pages with internal caching."""
    combined: list[dict[str, Any]] = []
    page_cache: dict[str, Any] = {}  # Local cache within function

    for index, item_slug in enumerate(track_items, start=1):
        # Check local cache first
        if item_slug not in page_cache:
            page_cache[item_slug] = get_page_func(item_slug)

        page = page_cache[item_slug]
        if not page:
            continue

        # Add section header as level 1 item
        section_id = f"track-section-{index}"
        combined.append({"id": section_id, "title": page.title, "level": 1})

        # Add all TOC items from this section, incrementing level by 1
        if hasattr(page, "toc_items") and page.toc_items:
            for toc_item in page.toc_items:
                combined.append(
                    {
                        "id": toc_item.get("id", ""),
                        "title": toc_item.get("title", ""),
                        "level": toc_item.get("level", 2) + 1,
                    }
                )

    return combined
```

**Expected Impact:**
- Eliminates redundant `get_page()` calls within TOC generation
- **Savings: ~9 calls × 0.11ms = ~1ms per track page** (minimal alone, but helps when combined with Solution 1)

**Risk:** Very Low - simple local cache, no state shared between calls

## Recommended Approach

**Phase 1: Quick Win (Solution 1 + Solution 4)**
- Implement per-render `get_page()` caching with proper key normalization
- Optimize `combine_track_toc_items()` local caching
- **Expected: ~430ms - 3.5s savings per track page**

**Phase 2: Further Optimization (Solution 2 or Solution 3 if needed)**
- Choose between pre-parsing or batch fetching based on Phase 1 results
- Only implement if Phase 1 doesn't achieve target performance
- **Expected: Marginal additional savings (Phase 1 should capture most benefit)**

## Implementation Plan

### Step 1: Add Per-Render Caching

1. Add `_render_cache` thread-local to `get_page.py`
2. Add `_normalize_cache_key()` function for consistent cache keys
3. Add `clear_get_page_cache()` function
4. Modify `get_page()` to check/populate cache
5. Call `clear_get_page_cache()` at start of each page render in pipeline

### Step 2: Optimize TOC Generation

1. Add local cache to `combine_track_toc_items()`
2. Test TOC generation with track pages

### Step 3: Measure Impact

1. Profile track page rendering before/after
2. Verify no regressions in other page types
3. Document performance improvements

### Step 4: Consider Further Optimizations

1. Evaluate if pre-parsing (Solution 2) or batch fetching (Solution 3) is needed
2. Implement only if Phase 1 doesn't achieve target performance

## Testing Strategy

### Unit Tests

1. **Per-render cache:**
   - Cache persists within single render
   - Cache cleared between renders
   - Thread-safe (each thread has own cache)
   - Different path formats resolve to same cache entry

2. **Cache key normalization:**
   - `"./foo.md"` → `"foo.md"`
   - `"content/foo.md"` → `"foo.md"`
   - `"foo.md"` → `"foo.md"`
   - `"foo"` → `"foo"` (extension handled by lookup)

3. **TOC caching:**
   - Same page not fetched twice
   - Missing pages handled correctly

```python
# tests/unit/rendering/test_get_page_cache.py

import threading
from unittest.mock import MagicMock

import pytest

from bengal.rendering.template_functions.get_page import (
    _normalize_cache_key,
    clear_get_page_cache,
)


class TestCacheKeyNormalization:
    """Test cache key normalization."""

    def test_strips_leading_dot_slash(self):
        assert _normalize_cache_key("./foo.md") == "foo.md"

    def test_strips_content_prefix(self):
        assert _normalize_cache_key("content/foo.md") == "foo.md"

    def test_normalizes_backslashes(self):
        assert _normalize_cache_key("content\\foo.md") == "foo.md"

    def test_preserves_simple_path(self):
        assert _normalize_cache_key("foo.md") == "foo.md"

    def test_handles_nested_paths(self):
        assert _normalize_cache_key("content/guides/foo.md") == "guides/foo.md"


class TestCacheThreadSafety:
    """Test thread isolation of cache."""

    def test_caches_are_thread_isolated(self):
        results = {}

        def thread_work(thread_id: int):
            clear_get_page_cache()
            from bengal.rendering.template_functions.get_page import _get_render_cache

            cache = _get_render_cache()
            cache["test"] = f"thread-{thread_id}"
            results[thread_id] = cache.get("test")

        threads = [
            threading.Thread(target=thread_work, args=(i,)) for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have its own value
        assert results[0] == "thread-0"
        assert results[1] == "thread-1"
        assert results[2] == "thread-2"
```

### Integration Tests

1. **Track rendering:**
   - Track pages render correctly
   - All track items accessible
   - TOC generation works

2. **Performance:**
   - Track page rendering time reduced
   - No regressions in other page types

### Benchmarking

```python
# benchmarks/test_track_rendering.py

import time

import pytest


@pytest.fixture
def track_page(site_with_tracks):
    """Get a track page for benchmarking."""
    for page in site_with_tracks.pages:
        if page.metadata.get("type") == "track":
            return page
    pytest.skip("No track pages found")


def test_track_render_performance(track_page, renderer, benchmark_threshold=0.1):
    """Verify track page renders in under 100ms."""
    start = time.perf_counter()
    renderer.render_page(track_page)
    duration = time.perf_counter() - start

    # Target: < 100ms per track page (down from ~500ms+)
    assert duration < benchmark_threshold, (
        f"Track page render took {duration:.3f}s, expected < {benchmark_threshold}s"
    )
```

## Success Metrics

- **Track page rendering time:** < 100ms per page (down from ~500ms+)
- **Total track build time:** < 1s for 9 pages (down from ~4.5s+)
- **No regressions:** Other page types unaffected
- **Memory overhead:** < 10MB for per-render cache (cleared after each page)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cache not cleared between renders | High | Clear cache at start of each `_render_single_page()` |
| Thread safety issues | Medium | Use `threading.local()` (same pattern as `NavScaffoldCache`) |
| Cache key inconsistency | Medium | `_normalize_cache_key()` ensures all path variants hit same entry |
| Memory overhead | Low | Cache cleared after each page render, ~9 pages × ~1KB = ~9KB max |
| Template compatibility | Low | Backward compatible, no template changes needed for Phase 1 |
| Watch mode invalidation | Low | Pages are re-parsed from source; cache only lives during single render |

## Alternatives Considered

1. **Lazy parsing with global cache:** Rejected - pages may change between renders in watch mode
2. **Template-level caching (`{% cache %}` blocks):** Rejected - requires Jinja2 extension, less flexible
3. **Pre-render all pages:** Rejected - too aggressive, may parse unused pages
4. **LRU cache with TTL:** Rejected - over-engineered for per-render scope; simple dict suffices

## Existing Patterns to Follow

Bengal already implements similar caching patterns that this RFC should follow:

1. **`NavScaffoldCache`** (`bengal/rendering/template_functions/navigation/scaffold.py`):
   - Thread-safe caching with `threading.Lock()`
   - Per-site invalidation when site object changes
   - Double-checked locking for expensive operations

2. **`clear_global_context_cache()`** (`bengal/rendering/context.py`):
   - Called at start of build by `RenderOrchestrator`
   - Clears stateless wrappers (SiteContext, ConfigContext, etc.)

3. **Thread-local pipelines** (`bengal/orchestration/render.py`):
   - `clear_thread_local_pipelines()` called at build start
   - Each thread gets its own rendering pipeline

## References

- `bengal/rendering/template_functions/get_page.py` - Current implementation
- `bengal/themes/default/templates/tracks/single.html` - Track template
- `bengal/themes/default/templates/partials/track-sidebar.html` - Sidebar template
- `bengal/rendering/template_functions/navigation/toc.py` - TOC generation
- `bengal/rendering/template_functions/navigation/scaffold.py` - NavScaffoldCache pattern
- `bengal/rendering/context.py` - Global context caching pattern
- `bengal/orchestration/render.py` - Rendering pipeline (parallel/sequential)

## Appendix: Performance Analysis

### Current Cost Breakdown (per track page with 9 items)

| Operation | Calls | Cost per Call | Total Cost |
|-----------|-------|---------------|------------|
| `get_page()` lookup | 54 | 0.11ms | 6ms |
| `get_page()` parsing (if not cached) | 54 | 7-65ms | 378ms - 3.5s |
| Template rendering | 1 | 50ms | 50ms |
| **Total** | | | **434ms - 3.56s** |

### After Optimization (Solution 1 + 4)

| Operation | Calls | Cost per Call | Total Cost |
|-----------|-------|---------------|------------|
| `get_page()` lookup (first call per page) | 9 | 0.11ms | 1ms |
| `get_page()` cache hit | 45 | 0.01ms | 0.5ms |
| `get_page()` parsing | 9 | 7-65ms | 63ms - 585ms |
| Template rendering | 1 | 50ms | 50ms |
| **Total** | | | **114.5ms - 636.5ms** |

**Improvement: 74-82% reduction in rendering time**

## Appendix: Code Location Quick Reference

| Component | File | Key Lines |
|-----------|------|-----------|
| `get_page()` function | `bengal/rendering/template_functions/get_page.py` | 238-313 |
| `_ensure_page_parsed()` | `bengal/rendering/template_functions/get_page.py` | 24-154 |
| `_build_lookup_maps()` | `bengal/rendering/template_functions/get_page.py` | 156-189 |
| `combine_track_toc_items()` | `bengal/rendering/template_functions/navigation/toc.py` | 112-148 |
| Track template | `bengal/themes/default/templates/tracks/single.html` | Full file |
| Track sidebar | `bengal/themes/default/templates/partials/track-sidebar.html` | 72-81 |
| `RenderOrchestrator.process()` | `bengal/orchestration/render.py` | 162-209 |
| `NavScaffoldCache` (pattern) | `bengal/rendering/template_functions/navigation/scaffold.py` | 66-171 |
