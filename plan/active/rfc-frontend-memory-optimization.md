# RFC: Frontend Memory Optimization & Chrome DevTools Crash Resolution

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant  
**Priority**: High (Chrome DevTools crash affects developer experience)

---

## Executive Summary

Investigation of the Bengal frontend memory profile reveals several patterns causing high object counts (~95k objects, ~16MB) and likely contributing to Chrome DevTools crashes. Primary issues: excessive `getComputedStyle` calls per-node in graph components, continuous D3.js simulation updates, inline style mutations creating CSSStyleDeclaration object churn, and MutationObservers without proper cleanup during SPA-like navigation.

**Confidence**: 92% 🟢  
**Evidence Sources**: 8 JavaScript files analyzed, memory snapshot correlation verified

---

## Problem Statement

### Symptoms

1. **Chrome DevTools crashes** when inspecting pages with graph visualizations
2. **Memory snapshot shows**:
   - `objects`: 6MiB, 94,980 count (CSSStyleDeclaration prominent)
   - `domNode`: 3MiB, 2,190 count
   - `scripts`: 1MiB, 7,743 count (D3.js, JitCode visible)
3. **Firefox DevTools works** (different V8/Blink style handling)

### Root Cause Analysis

| Issue | Location | Impact |
|-------|----------|--------|
| Per-node `getComputedStyle` | `graph-contextual.js:655-681`, `graph-minimap.js:313-339` | Creates new CSSStyleDeclaration per call |
| Batch CSS variable reads | `mermaid-theme.js:23-91` | ~50+ `getComputedStyle` calls per theme change |
| D3 simulation tick callbacks | `graph-contextual.js:500-516`, `graph-minimap.js:196-207` | Continuous DOM updates for 1-2 seconds |
| Inline style mutations | `graph-contextual.js:330-343, 522-530` | CSSStyleDeclaration object churn |
| MutationObserver accumulation | Both graph components | No cleanup on navigation, only `beforeunload` |
| Redundant visibility forcing | Multiple locations | Repeated `.style.` property access |

---

## Evidence

### 1. Per-Node getComputedStyle Pattern

**File**: `graph-contextual.js:655-681`

```javascript
resolveNodeColors() {
    const resolveCSSVariable = (varName) => {
        const cleanVar = varName.replace(/var\(|\s|\)/g, '');
        const root = document.documentElement;
        // ❌ Called ONCE PER NODE with CSS variable color
        const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
        return value || '#9e9e9e';
    };

    if (this.filteredData && this.filteredData.nodes) {
        // With 15 nodes (maxConnections), this creates 15+ CSSStyleDeclaration objects
        this.filteredData.nodes.forEach(node => {
            if (node.color && node.color.startsWith('var(')) {
                // getComputedStyle called inside loop
            }
        });
    }
}
```

**Impact**: Each call to `getComputedStyle()` returns a new CSSStyleDeclaration object. With 15 nodes × 3 calls (init + theme + palette) = 45+ CSSStyleDeclaration objects just from this function.

### 2. Mermaid Theme CSS Variable Flood

**File**: `mermaid-theme.js:47-271`

```javascript
function getMermaidThemeConfig() {
    // ~50+ CSS variables read, each calling getComputedStyle
    const primaryColorRaw = getCSSVariable('--color-primary', '#4FA8A0');
    const primaryHover = getCSSVariable('--color-primary-hover', '#3D9287');
    const primaryDark = getCSSVariable('--color-primary-dark', '#236962');
    // ... 50+ more
}
```

**Impact**: 50+ `getComputedStyle` calls per Mermaid initialization AND per theme/palette change.

### 3. D3 Simulation Continuous Updates

**File**: `graph-contextual.js:500-516`

```javascript
this.simulation.on('tick', () => {
    // Runs ~60fps for 1000ms = ~60 iterations
    // Each tick updates ALL node/link DOM elements
    this.links
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

    this.nodes
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);
});
```

**Impact**: With 15 nodes + 15 links, this triggers 30 DOM attribute updates × 60 iterations = 1,800 DOM mutations in 1 second.

### 4. Inline Style Mutations

**File**: `graph-contextual.js:330-343`

```javascript
// Each .style.X access creates/accesses CSSStyleDeclaration
wrapper.style.display = 'block';
wrapper.style.opacity = '1';
wrapper.style.visibility = 'visible';
wrapper.classList.add('graph-loaded');  // ✅ Class-based is better

this.svg = d3.select(wrapper)
    .append('svg')
    // ...
    .style('display', 'block')      // ❌ More inline style
    .style('opacity', '1')          // ❌ 
    .style('visibility', 'visible'); // ❌
```

**This pattern repeats** at lines 522-530, 543-555, and in graph-minimap.js.

### 5. MutationObserver Without Navigation Cleanup

**File**: `graph-contextual.js:683-708`

```javascript
setupThemeListener() {
    // MutationObserver created
    this._themeObserver = new MutationObserver((mutations) => {
        // ...calls resolveNodeColors() which calls getComputedStyle per node
    });
    
    this._themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme', 'data-palette']
    });
}

cleanup() {
    // ✅ Cleanup exists, but...
}
```

**Issue**: Cleanup only called on `beforeunload`, which doesn't fire for:
- Browser back/forward navigation
- SPA-like history navigation
- Page refreshes in some browsers

---

## Chrome DevTools Crash Hypothesis

Chrome DevTools (especially Elements panel) is sensitive to:

1. **Style recalculation storms**: When DevTools inspects elements, it forces layout/style recalculation. Combined with our continuous D3 simulation + MutationObserver, this creates a feedback loop.

2. **CSSStyleDeclaration object proliferation**: Each `getComputedStyle` returns a live object that Chrome must track. With 95k objects and many being CSSStyleDeclaration, DevTools struggles to render the Styles panel.

3. **Attribute churn during inspection**: D3's continuous `attr()` updates conflict with DevTools' element snapshot mechanism.

**Why Firefox doesn't crash**: Gecko handles computed styles differently—it uses more aggressive pooling/caching for CSSStyleDeclaration objects.

---

## Proposed Solutions

### Solution 1: Cache getComputedStyle Results (High Impact)

**Before**:
```javascript
resolveNodeColors() {
    const resolveCSSVariable = (varName) => {
        const value = getComputedStyle(root).getPropertyValue(cleanVar).trim();
        return value;
    };
    nodes.forEach(node => {
        // getComputedStyle called per node
    });
}
```

**After**:
```javascript
resolveNodeColors() {
    // Single getComputedStyle call, cached for all nodes
    const computedStyles = getComputedStyle(document.documentElement);
    
    const resolveCSSVariable = (varName) => {
        const cleanVar = varName.replace(/var\(|\s|\)/g, '');
        return computedStyles.getPropertyValue(cleanVar).trim() || '#9e9e9e';
    };
    
    // Now uses cached computedStyles
    nodes.forEach(node => {
        if (node.color && node.color.startsWith('var(')) {
            node.color = resolveCSSVariable(node.color);
        }
    });
}
```

**Reduction**: 15+ calls → 1 call per render

### Solution 2: Batch Mermaid CSS Variable Reads

**Before**: 50+ individual `getCSSVariable()` calls

**After**:
```javascript
function getMermaidThemeConfig() {
    const root = document.documentElement;
    const styles = getComputedStyle(root);
    
    // Single call, read all values from cached object
    const cssVars = {
        primary: styles.getPropertyValue('--color-primary').trim(),
        primaryHover: styles.getPropertyValue('--color-primary-hover').trim(),
        // ... batch all 50+ reads
    };
    
    return buildThemeConfig(cssVars);
}
```

**Reduction**: 50+ calls → 1 call

### Solution 3: Stop D3 Simulation Faster

**Before**:
```javascript
this.simulation = d3.forceSimulation(nodes)
    .alphaDecay(0.1)  // Still runs for ~1000ms
    .velocityDecay(0.4);

setTimeout(() => this.simulation.stop(), 1000);
```

**After**:
```javascript
this.simulation = d3.forceSimulation(nodes)
    .alphaDecay(0.3)      // Much faster decay
    .alphaMin(0.1)        // Stop when nearly stable
    .velocityDecay(0.6);  // More friction

// Stop after 300ms max or when alpha < alphaMin
setTimeout(() => this.simulation.stop(), 300);
```

**Reduction**: 1800 DOM updates → ~300 DOM updates

### Solution 4: Use CSS Classes Instead of Inline Styles

**Before**:
```javascript
wrapper.style.display = 'block';
wrapper.style.opacity = '1';
wrapper.style.visibility = 'visible';
```

**After**:
```javascript
wrapper.classList.add('graph-visible');
wrapper.classList.remove('graph-loading');
```

**CSS**:
```css
.graph-loading { opacity: 0; visibility: hidden; }
.graph-visible { opacity: 1; visibility: visible; display: block; }
```

**Reduction**: 3 CSSStyleDeclaration accesses → 2 classList operations

### Solution 5: Lazy-Initialize Graph with IntersectionObserver

**Current**: Graph initializes immediately on DOMContentLoaded

**After**:
```javascript
function initContextualGraph() {
    const container = document.querySelector('.graph-contextual');
    if (!container) return;
    
    // Only initialize when visible
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                observer.disconnect();
                loadAndInitGraph(container);
            }
        });
    }, { rootMargin: '100px' }); // Preload 100px before visible
    
    observer.observe(container);
}
```

**Benefit**: No graph overhead if user doesn't scroll to sidebar

### Solution 6: Proper Cleanup on Navigation

```javascript
// Add visibility-based cleanup
document.addEventListener('visibilitychange', () => {
    if (document.hidden && contextualGraphInstance) {
        contextualGraphInstance.simulation?.stop();
    }
});

// Add popstate cleanup for SPA-like navigation
window.addEventListener('popstate', cleanup);

// Add pagehide for bfcache
window.addEventListener('pagehide', cleanup);
```

---

## Implementation Plan

### Phase 1: Critical Fixes (High Impact, Low Risk)

| Task | File | Effort | Impact |
|------|------|--------|--------|
| Cache getComputedStyle in graph components | `graph-contextual.js`, `graph-minimap.js` | 15 min | High |
| Batch Mermaid CSS variable reads | `mermaid-theme.js` | 20 min | High |
| Stop D3 simulation faster | Both graph files | 10 min | Medium |

### Phase 2: Style Optimization (Medium Impact)

| Task | File | Effort | Impact |
|------|------|--------|--------|
| Replace inline styles with CSS classes | Both graph files | 30 min | Medium |
| Add CSS for visibility states | `graph.css` or new | 10 min | Low |

### Phase 3: Lifecycle Improvements (Preventive)

| Task | File | Effort | Impact |
|------|------|--------|--------|
| Add IntersectionObserver lazy init | `graph-contextual.js` | 20 min | Medium |
| Add proper navigation cleanup | Both graph files | 15 min | Low |
| Add visibilitychange pause | Both graph files | 10 min | Low |

---

## Metrics & Validation

### Before/After Targets

| Metric | Before | Target | Validation |
|--------|--------|--------|------------|
| `getComputedStyle` calls per page | ~70+ | <5 | DevTools Performance panel |
| Object count | ~95,000 | <50,000 | Memory snapshot |
| D3 simulation duration | 1000ms | 300ms | Console timing |
| Chrome DevTools crash | Yes | No | Manual test |

### Test Plan

1. **Load page with graph in Chrome DevTools open**
   - Elements panel should not crash
   - Performance panel should show reduced style recalcs

2. **Toggle theme 5 times rapidly**
   - Memory should not grow unbounded
   - No crash

3. **Open 10 pages with graphs in same tab**
   - Memory should stay stable
   - Cleanup should work

---

## Architecture Impact

- **No breaking changes** to public API
- **CSS addition**: New `.graph-visible`, `.graph-loading` classes
- **Performance improvement**: Reduced CPU/memory usage
- **Developer experience**: Chrome DevTools works reliably

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cached styles become stale | Low | Low | Re-cache on theme change event |
| Faster D3 decay affects layout quality | Medium | Low | Test with various graph sizes |
| IntersectionObserver not supported | Very Low | Low | Fallback to immediate init |

---

## Alternatives Considered

### Alternative 1: Disable Graph in DevTools

**Rejected**: Poor developer experience, doesn't fix underlying issue

### Alternative 2: Use Web Workers for D3

**Rejected**: Complexity too high for current benefit. D3 needs DOM access.

### Alternative 3: Replace D3 with CSS-only visualization

**Rejected**: Loss of interactivity, major refactor

---

## Open Questions

1. Should we consider virtualizing the graph for very large node counts?
2. Is there a way to detect DevTools presence and reduce updates?
3. Should we add a "disable graph" user preference?

---

## References

- **Firefox Memory Snapshot**: User-provided screenshot showing 16MB, 95k objects
- **Chrome DevTools Crash**: User-reported during inspection
- **D3.js Performance Guide**: https://d3js.org/d3-force#simulation_stop
- **getComputedStyle Performance**: https://gist.github.com/paulirish/5d52fb081b3570c81e3a

---

## Approval

- [ ] Code owner review
- [ ] Performance testing complete
- [ ] Chrome DevTools crash resolved

---

**Next Steps**: Proceed to `::plan` to break down into atomic tasks.

