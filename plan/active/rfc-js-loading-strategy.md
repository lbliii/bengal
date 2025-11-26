# RFC: JavaScript Loading Strategy for Heavy Dependencies

**Status**: Draft  
**Author**: AI Assistant  
**Date**: 2025-01-XX  
**Related**: Graph minimap implementation, performance optimization

---

## Problem

Currently, all JavaScript loads in `base.html`, including heavy dependencies like:
- **D3.js** (~200KB minified) - Only needed for graph visualizations
- **Mermaid.js** (~400KB) - Only needed for diagrams
- **Tabulator.js** (~150KB) - Only needed for data tables

This means:
- Every page loads ~750KB+ of JS even if unused
- Slower initial page load
- Wasted bandwidth
- Poor performance on slow connections

## Current Approach

```html
<!-- base.html - loads on EVERY page -->
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="{{ asset_url('js/graph-minimap.js') }}"></script>
<script src="{{ asset_url('js/graph-contextual.js') }}"></script>
```

**Issues:**
- D3.js loads even on pages without graphs
- No lazy loading for heavy dependencies
- Components check for containers but scripts already loaded

## Proposed Solution

### Pattern 1: Conditional Script Loading (Recommended)

Load scripts only when containers exist, using dynamic script injection:

```html
<!-- base.html -->
<script>
(function() {
  // Check for graph containers before loading D3.js
  if (document.querySelector('.graph-minimap, .graph-contextual')) {
    const d3Script = document.createElement('script');
    d3Script.src = 'https://d3js.org/d3.v7.min.js';
    d3Script.onload = function() {
      // Load graph components after D3 is ready
      const components = [
        '{{ asset_url("js/graph-minimap.js") }}',
        '{{ asset_url("js/graph-contextual.js") }}'
      ];
      components.forEach(src => {
        const script = document.createElement('script');
        script.src = src;
        document.head.appendChild(script);
      });
    };
    document.head.appendChild(d3Script);
  }
})();
</script>
```

**Pros:**
- Only loads when needed
- Follows existing pattern (search preloading)
- No template changes needed
- Works with auto-initialization

**Cons:**
- Slightly more complex
- Requires DOM check before scripts load

### Pattern 2: Template-Level Conditional Includes

Use template conditionals to include scripts only on pages that need them:

```html
<!-- base.html -->
{% if page.metadata.get('has_graph') or (toc_items and page.metadata.get('type') == 'doc') %}
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="{{ asset_url('js/graph-contextual.js') }}"></script>
{% endif %}

{% if page.url.endswith('/search/') %}
<script src="{{ asset_url('js/graph-minimap.js') }}"></script>
{% endif %}
```

**Pros:**
- Simple and explicit
- No runtime checks
- Clear intent

**Cons:**
- Requires metadata/frontmatter changes
- Less flexible
- Template coupling

### Pattern 3: Lazy Loading on Intent (Like Search)

Load on user interaction or when container becomes visible:

```html
<!-- base.html -->
<script>
(function() {
  const graphContainers = document.querySelectorAll('.graph-minimap, .graph-contextual');
  if (graphContainers.length === 0) return;

  function loadGraphScripts() {
    if (window.d3) return; // Already loaded

    const d3Script = document.createElement('script');
    d3Script.src = 'https://d3js.org/d3.v7.min.js';
    d3Script.onload = function() {
      // Load components...
    };
    document.head.appendChild(d3Script);
  }

  // Load when container becomes visible (Intersection Observer)
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        loadGraphScripts();
        observer.disconnect();
      }
    });
  });

  graphContainers.forEach(container => observer.observe(container));
})();
</script>
```

**Pros:**
- Loads only when user scrolls to graph
- Best performance
- Progressive enhancement

**Cons:**
- Slight delay before graph renders
- More complex implementation

## Comparison with Other SSGs

### Hugo
- Uses front matter to conditionally include scripts
- Template-level conditionals (`{{ if .Params.js }}`)
- Hugo Pipes for bundling/minification

### Next.js / MDX
- Code splitting by default
- Dynamic imports (`import()`)
- Route-based chunking

### Jekyll
- Plugin-based loading
- Conditional includes in templates
- No built-in lazy loading

## Recommendation

**Use Pattern 1 (Conditional Script Loading)** because:

1. **Matches existing patterns**: Similar to search preloading
2. **Zero template changes**: Works with current implementation
3. **Performance**: Only loads when needed
4. **Simple**: Single check, dynamic loading
5. **Backward compatible**: Falls back gracefully

## Implementation Plan

1. **Phase 1**: Implement conditional loading for D3.js + graph components
2. **Phase 2**: Apply same pattern to Mermaid.js (if not already conditional)
3. **Phase 3**: Consider Tabulator.js (data tables)
4. **Phase 4**: Document pattern for theme developers

## Example Implementation

```html
<!-- base.html -->
{# Heavy dependencies - load conditionally #}
<script>
(function() {
  'use strict';

  // Graph visualizations
  if (document.querySelector('.graph-minimap, .graph-contextual')) {
    const d3Script = document.createElement('script');
    d3Script.src = 'https://d3js.org/d3.v7.min.js';
    d3Script.async = true;
    d3Script.onload = function() {
      // Load graph components after D3
      ['{{ asset_url("js/graph-minimap.js") }}',
       '{{ asset_url("js/graph-contextual.js") }}'].forEach(src => {
        const s = document.createElement('script');
        s.src = src;
        s.async = true;
        document.head.appendChild(s);
      });
    };
    document.head.appendChild(d3Script);
  }

  // Mermaid diagrams (if not already conditional)
  if (document.querySelector('.mermaid')) {
    // Mermaid already loads conditionally via CDN
    // But could add similar pattern here
  }
})();
</script>
```

## Performance Impact

**Before:**
- Every page: ~750KB JS (D3 + Mermaid + Tabulator)
- Initial load: Slower
- Unused code: Wasted

**After:**
- Pages with graphs: ~200KB (D3 + components)
- Pages without: 0KB (saved ~200KB)
- Pages with diagrams: ~400KB (Mermaid)
- **Estimated savings: 20-30% faster initial load**

## Questions

1. Should we apply this to Mermaid.js too? (Currently loads on all pages)
2. Should we add a config option to force-load all scripts? (For debugging)
3. Should we use Intersection Observer for even lazier loading?
4. Should we bundle graph components with D3.js? (Single file)

## References

- [Hugo JavaScript Loading](https://gohugo.io/hugo-pipes/js/)
- [Web.dev: Reduce JavaScript Payloads](https://web.dev/reduce-javascript-payloads-with-code-splitting/)
- Bengal's search preloading pattern (`base.html` lines 417-453)
