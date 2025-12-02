# RFC: Render Performance Optimization

**Status**: Implemented  
**Created**: 2025-12-02  
**Author**: AI Assistant  
**Priority**: High  
**Est. Impact**: ~8 second reduction in render-blocking time

---

## Executive Summary

Lighthouse reports **8,060 ms** of render-blocking requests for the Bengal documentation site. This RFC proposes changes to eliminate render-blocking resources through deferred script loading, lazy library loading, and font optimization.

**Key Changes**:
1. Add `defer` attribute to all scripts
2. Lazy-load heavy libraries (Mermaid, D3, Tabulator) only when needed
3. Preload critical fonts
4. Inline critical theme initialization

---

## Problem Statement

### Current State

The `base.html` template loads **25+ scripts synchronously** in the critical path:
- All scripts block parsing until downloaded and executed
- Heavy libraries load on every page even when unused:
  - **Mermaid.js**: 932.5 KiB (7,680 ms)
  - **D3.js**: 92.0 KiB (3,260 ms)
  - **Tabulator**: 99.3 KiB (2,750 ms)
- Font CSS blocks rendering (160 ms)
- Total render-blocking: **~8,060 ms**

### Evidence

From Lighthouse audit:

```
Render blocking requests Est savings of 8,060 ms

Top offenders:
- mermaid.min.js (cdn.jsdelivr.net): 932.5 KiB, 7,680 ms
- tabulator.min.71b17795.js: 99.3 KiB, 2,750 ms  
- d3.v7.min.js (d3js.org): 92.0 KiB, 3,260 ms
- style.6a083c0f.css: 67.3 KiB, 2,750 ms
- 20+ local JS files: ~40 KiB total, ~6,000 ms combined
```

---

## Proposed Solution

### 1. Defer All Local Scripts

**Change**: Add `defer` to all local scripts in `base.html`.

```html
{# Before #}
<script src="{{ asset_url('js/utils.js') }}"></script>

{# After #}
<script defer src="{{ asset_url('js/utils.js') }}"></script>
```

**Why it works**:
- `defer` downloads script in parallel without blocking HTML parsing
- Scripts execute in order after DOM is ready
- All Bengal scripts already use `DOMContentLoaded` or `ready()` patterns

**Affected scripts** (all local scripts):
- `js/utils.js`, `js/theme-toggle.js`, `js/mobile-nav.js`
- `js/tabs.js`, `js/toc.js`, `js/action-bar.js`, `js/main.js`
- `js/interactive.js`, `js/copy-link.js`, `js/lightbox.js`
- `js/search.js`, `js/search-page.js`, `js/search-modal.js`
- `js/mermaid-toolbar.js`, `js/mermaid-theme.js`
- `js/session-path-tracker.js`, `js/graph-minimap.js`, `js/graph-contextual.js`

**Exception**: `js/theme-init.js` must remain synchronous (prevents FOUC).

### 2. Lazy-Load Heavy Libraries

**Change**: Only load Mermaid, D3, and Tabulator when their features are used on the page.

#### 2a. Mermaid.js (932 KiB → 0 KiB on most pages)

**Strategy**: Detect `.mermaid` blocks and load dynamically.

```html
{# In base.html - Remove synchronous load #}
{# DELETE: <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script> #}

{# Add conditional loading block #}
{% if page.has_mermaid is defined and page.has_mermaid %}
<script>
  (function() {
    // Only load if .mermaid elements exist
    if (!document.querySelector('.mermaid')) return;

    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
    script.onload = function() {
      // Trigger mermaid-theme.js initialization
      if (window.BengalMermaidTheme) {
        window.BengalMermaidTheme.initializeMermaid();
      }
    };
    document.head.appendChild(script);
  })();
</script>
{% endif %}
```

**Better approach**: Add frontmatter detection during build:

```python
# In bengal/rendering/markdown_parser.py
# Detect mermaid blocks and set page.has_mermaid = True
```

#### 2b. D3.js (92 KiB → 0 KiB on most pages)

**Strategy**: Only load when graph containers exist.

```html
{# In base.html - Remove synchronous load #}
{# DELETE: <script src="https://d3js.org/d3.v7.min.js"></script> #}

{# Add conditional loading #}
<script>
  (function() {
    // Only load D3 if graph elements exist
    if (!document.querySelector('.graph-minimap, .graph-contextual, [data-graph]')) return;

    var script = document.createElement('script');
    script.src = 'https://d3js.org/d3.v7.min.js';
    script.onload = function() {
      // Initialize graphs after D3 loads
      window.dispatchEvent(new Event('d3:ready'));
    };
    document.head.appendChild(script);
  })();
</script>
```

Update `graph-minimap.js` and `graph-contextual.js` to wait for `d3:ready` event.

#### 2c. Tabulator (99 KiB → 0 KiB on most pages)

**Strategy**: Only load when data tables exist.

```html
{# In base.html - Remove synchronous loads #}
{# DELETE: <script src="{{ asset_url('js/tabulator.min.js') }}"></script> #}
{# DELETE: <script src="{{ asset_url('js/data-table.js') }}"></script> #}

{# Add conditional loading #}
<script>
  (function() {
    if (!document.querySelector('.bengal-data-table-wrapper')) return;

    var script = document.createElement('script');
    script.src = '{{ asset_url("js/tabulator.min.js") }}';
    script.onload = function() {
      // Load data-table.js after Tabulator
      var dataTableScript = document.createElement('script');
      dataTableScript.src = '{{ asset_url("js/data-table.js") }}';
      document.head.appendChild(dataTableScript);
    };
    document.head.appendChild(script);
  })();
</script>
```

### 3. Font Optimization

**Change**: Preload critical fonts and use `font-display: swap`.

```html
{# In base.html head section #}
{% if site.config.get('fonts') %}
{# Preload critical fonts #}
<link rel="preload" href="{{ asset_url('fonts/outfit-700.woff2') }}" as="font" type="font/woff2" crossorigin>
{# Load font CSS with optional rendering #}
<link rel="stylesheet" href="{{ asset_url('fonts.css') }}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{{ asset_url('fonts.css') }}"></noscript>
{% endif %}
```

**Also verify** `fonts.css` includes:
```css
@font-face {
  font-display: swap; /* Prevent FOIT (Flash of Invisible Text) */
}
```

### 4. Inline Critical Theme Init

The `theme-init.js` script prevents flash of unstyled content but blocks rendering.

**Change**: Inline the critical theme detection code.

```html
{# In base.html - Replace external script with inline #}
{# DELETE: <script src="{{ asset_url('js/theme-init.js') }}"></script> #}

<script>
  // Critical: Apply theme before first paint to prevent FOUC
  (function() {
    var stored = localStorage.getItem('bengal-theme');
    var preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var theme = stored || window.BENGAL_THEME_DEFAULTS?.appearance || preferred;
    document.documentElement.setAttribute('data-theme', theme);

    var palette = localStorage.getItem('bengal-palette') || window.BENGAL_THEME_DEFAULTS?.palette || 'default';
    document.documentElement.setAttribute('data-palette', palette);
  })();
</script>
```

---

## Implementation Plan

### Phase 1: Defer Scripts (Low Risk, High Impact)

**Files Changed**: `bengal/themes/default/templates/base.html`

```diff
- <script src="{{ asset_url('js/utils.js') }}"></script>
+ <script defer src="{{ asset_url('js/utils.js') }}"></script>
```

**Estimated Savings**: ~3,000 ms (parallel downloading)

### Phase 2: Lazy-Load Libraries (Medium Risk, Highest Impact)

**Files Changed**:
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/assets/js/graph-minimap.js`
- `bengal/themes/default/assets/js/graph-contextual.js`
- `bengal/themes/default/assets/js/mermaid-theme.js`
- `bengal/themes/default/assets/js/data-table.js`

**Estimated Savings**: ~5,000 ms on pages without diagrams/tables/graphs

### Phase 3: Font Optimization (Low Risk, Medium Impact)

**Files Changed**:
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/assets/fonts.css` (verify `font-display: swap`)

**Estimated Savings**: ~160 ms (non-blocking font load)

### Phase 4: Inline Critical CSS (Optional, Higher Complexity)

Inline above-the-fold CSS to eliminate the 2,750 ms CSS blocking time.

**Requires**: Build-time critical CSS extraction (tools like Critical or Critters).

**Deferred**: Consider for future optimization.

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Defer scripts | Low | All scripts already wait for DOM ready |
| Lazy-load libraries | Medium | Add error handling, test pages with/without features |
| Font preloading | Low | Fallback to normal load via noscript |
| Inline theme init | Low | Same code, different delivery |

---

## Testing Strategy

1. **Lighthouse Before/After**: Run on staging to verify savings
2. **Visual Regression**: Check no FOUC or layout shifts
3. **Feature Testing**: Verify diagrams/graphs/tables still work
4. **Network Throttling**: Test on 3G to confirm improvement

---

## Metrics

**Current State** (from Lighthouse):
- First Contentful Paint: Delayed by ~8s of blocking resources
- Largest Contentful Paint: Delayed by critical path chains
- Total Blocking Time: High due to script evaluation

**Target State**:
- Eliminate all render-blocking JS except theme-init inline
- Load heavy libraries only when needed (~1 MB saved on most pages)
- Font loading non-blocking

---

## Alternatives Considered

### 1. Bundle All Scripts

**Rejected**: Would still load unused code (Mermaid/D3) on every page.

### 2. HTTP/2 Server Push

**Rejected**: Not available on GitHub Pages hosting.

### 3. Service Worker Caching

**Considered for Future**: Could cache heavy libraries after first visit.

---

## Related Work

- [rfc-search-experience-v2.md](rfc-search-experience-v2.md) - Search index lazy loading (already implemented)
- GitHub Pages cache limitations (10 minute TTL) - out of scope

---

## Implementation Notes

**Implemented**: 2025-12-02

### Changes Made

1. **`base.html`** - Template updates:
   - Added `defer` to all local scripts
   - Inlined `theme-init.js` for faster FOUC prevention
   - Added font preloading (`<link rel="preload">`)
   - Made fonts.css non-blocking with preload pattern
   - Created lazy-loaders for Mermaid, D3, and Tabulator

2. **`graph-minimap.js`** - Added `d3:ready` event listener for lazy D3

3. **`graph-contextual.js`** - Added `d3:ready` event listener for lazy D3

### Files Changed

- `bengal/themes/default/templates/base.html` (+132/-48 lines)
- `bengal/themes/default/assets/js/graph-minimap.js` (+5 lines)
- `bengal/themes/default/assets/js/graph-contextual.js` (+3 lines)

---

## Approval

- [x] Implementation complete
- [ ] Performance testing completed
- [ ] No visual regressions
