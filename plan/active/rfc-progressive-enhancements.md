# RFC: Progressive Enhancements Architecture

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant  
**Priority**: Medium  
**Confidence**: 88% 🟢  
**Est. Impact**: Formalized enhancement pattern, conditional script loading, reduced JS per page

---

## Executive Summary

This RFC proposes formalizing Bengal's existing progressive enhancement patterns into a unified **Progressive Enhancements Architecture**. Unlike Islands Architecture (which solves React's hydration problem), this pattern plays to Bengal's vanilla JS strengths: HTML that works without JavaScript, progressively enhanced when JS is available.

**Key Changes**:
1. Unified `data-bengal` attribute for declaring enhancements
2. Central enhancement registry with auto-discovery
3. Conditional script loading for ALL enhancements (not just heavy libs)
4. Formalized pattern documentation

**Philosophy**: "Layered enhancement — HTML that works, CSS that delights, JS that elevates"

---

## Problem Statement

### Current State (Already Good)

Bengal's theme already follows progressive enhancement principles:

```javascript
// lazy-loaders.js - Conditional loading for heavy libs
function loadTabulator() {
    if (!document.querySelector('.bengal-data-table-wrapper')) return;
    // Only loads when needed ✅
}

// tabs.js - Event delegation
document.addEventListener('click', (e) => {
    const link = e.target.closest(SELECTOR_NAV_LINK);
    // Works with dynamic content ✅
});

// toc.js - Data attributes for config
const tocItems = document.querySelectorAll('[data-toc-item]');
// Declarative configuration ✅
```

**Evidence**:
- `bengal/themes/default/assets/js/lazy-loaders.js` - conditional loading
- `bengal/themes/default/assets/js/toc.js` - data attribute pattern
- `bengal/themes/default/assets/js/tabs.js` - event delegation

### Pain Points

1. **Inconsistent Patterns**: Some use classes (`.tabs`, `.theme-toggle`), others use data attributes (`data-toc-item`, `data-tab-target`).

2. **Core Scripts Load Everywhere**: While heavy libs are lazy-loaded, core scripts still load on every page:
   ```html
   <!-- base.html - ALL pages load ALL core scripts -->
   <script defer src="{{ asset_url('js/tabs.js') }}"></script>
   <script defer src="{{ asset_url('js/toc.js') }}"></script>
   <script defer src="{{ asset_url('js/mobile-nav.js') }}"></script>
   <!-- ... even pages without tabs, TOC, or mobile users -->
   ```

3. **No Central Registry**: Each script self-initializes. No way to:
   - List available enhancements
   - Programmatically trigger enhancement
   - Debug what's enhanced

4. **Implicit Conventions**: Pattern exists but isn't documented or enforced.

### Metrics

Current script loading on a simple page (no tabs, no TOC):

| Script | Size | Needed? |
|--------|------|---------|
| utils.js | 3KB | Yes (dependency) |
| theme-toggle.js | 4KB | Yes |
| mobile-nav.js | 3KB | Only on mobile |
| tabs.js | 2KB | **No** |
| toc.js | 8KB | **No** |
| interactive.js | 4KB | Partial |
| **Total loaded** | **~35KB** | **~15KB needed** |

**Potential reduction**: ~50% on pages without tabs/TOC

---

## Goals & Non-Goals

### Goals

1. **G1**: Unify enhancement declaration with `data-bengal` attribute
2. **G2**: Extend conditional loading to ALL enhancements (not just heavy libs)
3. **G3**: Create central enhancement registry
4. **G4**: Maintain backward compatibility with existing patterns
5. **G5**: Document and formalize the pattern
6. **G6**: Keep HTML functional without JavaScript (true progressive enhancement)

### Non-Goals

- **NG1**: Custom elements / Web Components (unnecessary complexity)
- **NG2**: Framework adoption (stay vanilla JS)
- **NG3**: Breaking existing themes (backward compatible)
- **NG4**: Islands Architecture (solves different problem)
- **NG5**: Build-time bundling (keep runtime simplicity)

---

## Architecture Impact

**Affected Subsystems**:

- **Themes** (`bengal/themes/`): Moderate impact
  - Update templates to use `data-bengal` attributes
  - Reorganize JS into `enhancements/` directory
  - Update `base.html` script loading

- **Rendering** (`bengal/rendering/`): Minor impact
  - Template functions for enhancement declaration

- **CLI** (`bengal/cli/`): Minor impact
  - `bengal enhancements list` command

**New Components**:
- `bengal/themes/default/assets/js/bengal-enhance.js` (~1.5KB loader)
- `bengal/themes/default/assets/js/enhancements/` directory

---

## Design

### 1. Unified Data Attribute Pattern

**Before** (inconsistent):
```html
<!-- Class-based -->
<button class="theme-toggle">Toggle</button>
<div class="tabs">...</div>

<!-- Data attribute (various) -->
<nav data-toc-item="#intro">...</nav>
<a data-tab-target="tab-1">...</a>
```

**After** (unified):
```html
<!-- All use data-bengal for enhancement declaration -->
<button data-bengal="theme-toggle">Toggle</button>

<div data-bengal="tabs">
  <a data-tab-target="tab-1">Tab 1</a>
  ...
</div>

<nav data-bengal="toc" data-toc-spy="true">
  <a data-toc-item="#intro">Introduction</a>
  ...
</nav>

<!-- Configuration via additional data attributes -->
<a href="/search" data-bengal="search-modal" data-hotkey="k">Search</a>
```

**Key principle**: `data-bengal` declares WHAT enhancement, other `data-*` attributes configure HOW.

### 2. Enhancement Loader (~1.5KB)

```javascript
// bengal-enhance.js - The enhancement loader
(function() {
  'use strict';

  const REGISTRY = {};
  const ENHANCED = new WeakSet();
  const DEBUG = (window.Bengal && window.Bengal.debug) || false;

  function log(...args) {
    if (DEBUG) console.log('[Bengal]', ...args);
  }

  /**
   * Register an enhancement
   * @param {string} name - Enhancement name (matches data-bengal value)
   * @param {Function} init - Initialization function (element, options) => void
   * @param {Object} [options] - Registration options
   */
  function register(name, init, options = {}) {
    if (REGISTRY[name] && !options.override) {
      log(`Enhancement "${name}" already registered`);
      return;
    }
    REGISTRY[name] = { init, options };
    log(`Registered enhancement: ${name}`);
  }

  /**
   * Enhance a single element
   */
  function enhanceElement(el) {
    if (ENHANCED.has(el)) return;

    const name = el.dataset.bengal;
    if (!name) return;

    const enhancement = REGISTRY[name];
    if (!enhancement) {
      // Try to lazy-load the enhancement
      loadEnhancement(name).then(() => {
        if (REGISTRY[name]) {
          applyEnhancement(el, REGISTRY[name]);
        } else {
          log(`Unknown enhancement: ${name}`);
        }
      });
      return;
    }

    applyEnhancement(el, enhancement);
  }

  /**
   * Apply an enhancement to an element
   */
  function applyEnhancement(el, enhancement) {
    if (ENHANCED.has(el)) return;

    try {
      // Extract options from data attributes
      const options = extractOptions(el);
      enhancement.init(el, options);
      ENHANCED.add(el);
      el.setAttribute('data-enhanced', 'true');
      log(`Enhanced: ${el.dataset.bengal}`, el);
    } catch (err) {
      console.error(`[Bengal] Enhancement error (${el.dataset.bengal}):`, err);
      el.setAttribute('data-enhance-error', 'true');
    }
  }

  /**
   * Extract options from data attributes
   */
  function extractOptions(el) {
    const options = {};
    for (const [key, value] of Object.entries(el.dataset)) {
      if (key !== 'bengal' && key !== 'enhanced') {
        // Convert data-some-option to someOption
        options[key] = parseValue(value);
      }
    }
    return options;
  }

  /**
   * Parse data attribute value (handle booleans, numbers, JSON)
   */
  function parseValue(value) {
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (value === '') return true; // data-something with no value
    if (!isNaN(value) && value !== '') return Number(value);
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  /**
   * Lazy-load an enhancement script
   */
  async function loadEnhancement(name) {
    const baseUrl = window.BENGAL_ENHANCE_URL || '/assets/js/enhancements';
    const url = `${baseUrl}/${name}.js`;

    try {
      await import(url);
      log(`Loaded enhancement: ${name}`);
    } catch (err) {
      // Fallback to script tag for browsers without dynamic import
      return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = resolve;
        script.onerror = () => {
          log(`Failed to load enhancement: ${name}`);
          resolve(); // Don't reject - graceful degradation
        };
        document.head.appendChild(script);
      });
    }
  }

  /**
   * Scan and enhance all elements with data-bengal
   */
  function enhanceAll(root = document) {
    const elements = root.querySelectorAll('[data-bengal]:not([data-enhanced])');
    elements.forEach(enhanceElement);
  }

  /**
   * Initialize the enhancement system
   */
  function init() {
    // Enhance existing elements
    enhanceAll();

    // Watch for dynamic content (optional, configurable)
    if (window.Bengal && window.Bengal.watchDom !== false) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              if (node.dataset && node.dataset.bengal) {
                enhanceElement(node);
              }
              enhanceAll(node);
            }
          });
        });
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }

    log('Enhancement system initialized');
  }

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export API
  window.Bengal = window.Bengal || {};
  window.Bengal.enhance = {
    register,
    enhanceAll,
    enhanceElement,
    list: () => Object.keys(REGISTRY),
    get: (name) => REGISTRY[name],
    isEnhanced: (el) => ENHANCED.has(el)
  };

})();
```

### 3. Enhancement Module Pattern

```javascript
// enhancements/theme-toggle.js
(function() {
  'use strict';

  Bengal.enhance.register('theme-toggle', function(el, options) {
    const defaultTheme = options.default || 'system';

    // Get existing BengalTheme API or create inline
    const toggleTheme = window.BengalTheme
      ? window.BengalTheme.toggle
      : function() {
          const current = document.documentElement.dataset.theme;
          const next = current === 'dark' ? 'light' : 'dark';
          document.documentElement.dataset.theme = next;
          localStorage.setItem('bengal-theme', next);
        };

    el.addEventListener('click', (e) => {
      e.preventDefault();
      toggleTheme();
    });

    // Update aria-pressed on theme change
    window.addEventListener('themechange', () => {
      el.setAttribute('aria-pressed',
        document.documentElement.dataset.theme === 'dark');
    });
  });

})();
```

```javascript
// enhancements/tabs.js
(function() {
  'use strict';

  Bengal.enhance.register('tabs', function(container, options) {
    const navLinks = container.querySelectorAll('[data-tab-target]');
    const panes = container.querySelectorAll('.tab-pane');

    function switchTab(targetId) {
      // Deactivate all
      navLinks.forEach(link => {
        link.closest('li')?.classList.remove('active');
      });
      panes.forEach(pane => pane.classList.remove('active'));

      // Activate target
      const activeLink = container.querySelector(`[data-tab-target="${targetId}"]`);
      activeLink?.closest('li')?.classList.add('active');
      document.getElementById(targetId)?.classList.add('active');
    }

    // Event delegation within container
    container.addEventListener('click', (e) => {
      const link = e.target.closest('[data-tab-target]');
      if (!link) return;
      e.preventDefault();
      switchTab(link.dataset.tabTarget);
    });

    // Initialize first tab if none active
    if (!container.querySelector('.tab-pane.active')) {
      const firstTarget = navLinks[0]?.dataset.tabTarget;
      if (firstTarget) switchTab(firstTarget);
    }
  });

})();
```

```javascript
// enhancements/toc.js
(function() {
  'use strict';

  Bengal.enhance.register('toc', function(nav, options) {
    const spy = options.spy !== false; // Default true
    const items = nav.querySelectorAll('[data-toc-item]');

    if (!items.length) return;

    // Build heading map
    const headings = Array.from(items).map(link => {
      const id = link.dataset.tocItem.replace(/^#/, '');
      return {
        link,
        element: document.getElementById(id),
        id
      };
    }).filter(h => h.element);

    if (!headings.length) return;

    // Smooth scroll on click
    items.forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const id = link.dataset.tocItem.replace(/^#/, '');
        const target = document.getElementById(id);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.replaceState(null, '', '#' + id);
        }
      });
    });

    // Scroll spy
    if (spy && window.BengalUtils) {
      const { throttleScroll } = window.BengalUtils;
      let currentActive = null;

      function updateActive() {
        const scrollTop = window.scrollY + 120;

        let active = headings[0];
        for (const heading of headings) {
          if (heading.element.offsetTop <= scrollTop) {
            active = heading;
          } else {
            break;
          }
        }

        if (active !== currentActive) {
          currentActive?.link.classList.remove('active');
          active.link.classList.add('active');
          currentActive = active;
        }
      }

      window.addEventListener('scroll', throttleScroll(updateActive), { passive: true });
      updateActive();
    }
  });

})();
```

### 4. Template Integration

```html
<!-- base.html - Simplified script loading -->
<head>
  <!-- Critical: Theme init (inline, prevents FOUC) -->
  <script>/* existing inline theme init */</script>

  <!-- Enhancement loader - small, always load -->
  <script defer src="{{ asset_url('js/bengal-enhance.js') }}"></script>

  <!-- Utils - dependency for complex enhancements -->
  <script defer src="{{ asset_url('js/utils.js') }}"></script>

  <!-- Preload critical enhancements (configured in bengal.toml) -->
  {% for name in site.config.enhancements.preload %}
  <link rel="modulepreload" href="{{ asset_url('js/enhancements/' ~ name ~ '.js') }}">
  {% endfor %}
</head>

<body>
  <!-- Enhancements auto-discovered via data-bengal -->

  <button data-bengal="theme-toggle">Toggle Theme</button>

  <nav data-bengal="mobile-nav">...</nav>

  {% if page.toc %}
  <aside data-bengal="toc" data-spy="true">
    {% for item in page.toc %}
    <a data-toc-item="#{{ item.id }}">{{ item.title }}</a>
    {% endfor %}
  </aside>
  {% endif %}

  <!-- No need to load tabs.js if page has no tabs! -->
  {% if page.has_tabs %}
  <div data-bengal="tabs">...</div>
  {% endif %}
</body>
```

### 5. Configuration

```toml
# bengal.toml

[enhancements]
# Base URL for enhancement scripts
base_url = "/assets/js/enhancements"

# Preload these enhancements (always available, no lazy-load delay)
preload = ["theme-toggle", "mobile-nav"]

# Watch DOM for dynamic content (MutationObserver)
watch_dom = true

# Debug mode (logs enhancement activity)
debug = false
```

### 6. Backward Compatibility

Existing scripts continue to work unchanged. Migration is opt-in:

**Phase 1**: Add `bengal-enhance.js` alongside existing scripts  
**Phase 2**: Convert enhancements one-by-one to new pattern  
**Phase 3**: Remove old scripts as enhancements are migrated  
**Phase 4**: Update templates to use `data-bengal` attributes

```javascript
// Backward compatibility: existing scripts can register themselves
// theme-toggle.js (existing, modified)
(function() {
  'use strict';

  // ... existing code ...

  // Register with new system if available
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('theme-toggle', function(el, options) {
      el.addEventListener('click', toggleTheme);
    }, { override: true });
  }

  // ... existing self-initialization continues to work ...
})();
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Progressive Enhancements Flow                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Build Time (Python/Jinja)                      │  │
│  │                                                                   │  │
│  │  1. Templates render HTML with data-bengal attributes             │  │
│  │  2. Conditional: only include enhancement markup when needed      │  │
│  │  3. Copy enhancement scripts to output                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Output HTML                                    │  │
│  │                                                                   │  │
│  │  <html>                                                           │  │
│  │    <head>                                                         │  │
│  │      <script src="bengal-enhance.js" defer></script> <!-- 1.5KB -->│  │
│  │    </head>                                                        │  │
│  │    <body>                                                         │  │
│  │      <!-- HTML works without JS! -->                              │  │
│  │      <a href="/settings" data-bengal="theme-toggle">Theme</a>     │  │
│  │      <nav data-bengal="toc">...</nav>                             │  │
│  │      <main>Static content</main>                                  │  │
│  │    </body>                                                        │  │
│  │  </html>                                                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Runtime (Browser)                              │  │
│  │                                                                   │  │
│  │  1. HTML renders immediately (functional without JS)              │  │
│  │  2. bengal-enhance.js runs (tiny, deferred)                       │  │
│  │  3. Scans for [data-bengal] attributes                            │  │
│  │  4. For each unique enhancement:                                  │  │
│  │     - Check registry (preloaded?)                                 │  │
│  │     - If not: lazy-load /assets/js/enhancements/{name}.js         │  │
│  │  5. Apply enhancement to element                                  │  │
│  │  6. Mark element [data-enhanced="true"]                           │  │
│  │  7. MutationObserver watches for dynamic content                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Enhancement Loading Strategies:

  PRELOADED (theme-toggle, mobile-nav):
    Script bundled → Register immediately → Enhance on DOMContentLoaded

  LAZY-LOADED (tabs, toc, search-modal):
    DOMContentLoaded → Scan [data-bengal] → Dynamic import → Register → Enhance

  CONDITIONAL (from template):
    {% if page.has_tabs %}<div data-bengal="tabs">{% endif %}
    → Only included in HTML when needed
    → Only loaded when element exists
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `bengal-enhance.js` loader
- [ ] Create `enhancements/` directory structure
- [ ] Add configuration support in `bengal.toml`
- [ ] Unit tests for loader

### Phase 2: Migrate Core Enhancements (Week 1-2)

- [ ] Convert `theme-toggle.js` → `enhancements/theme-toggle.js`
- [ ] Convert `mobile-nav.js` → `enhancements/mobile-nav.js`
- [ ] Convert `tabs.js` → `enhancements/tabs.js`
- [ ] Convert `toc.js` → `enhancements/toc.js`
- [ ] Maintain backward compatibility

### Phase 3: Template Updates (Week 2)

- [ ] Update `base.html` to use new script loading
- [ ] Add `data-bengal` attributes to existing elements
- [ ] Update partials (theme-controls, mobile-nav, etc.)
- [ ] Test backward compatibility

### Phase 4: Documentation (Week 2-3)

- [ ] Document enhancement pattern
- [ ] Document creating custom enhancements
- [ ] Document configuration options
- [ ] Add examples

### Phase 5: CLI Integration (Week 3)

- [ ] `bengal enhancements list` command
- [ ] Enhancement scaffolding (`bengal enhance new <name>`)

---

## Comparison: Progressive Enhancements vs Islands

| Aspect | Islands | Progressive Enhancements |
|--------|---------|-------------------------|
| **Custom elements** | Required (`<bengal-island>`) | Not needed (standard HTML) |
| **Works without JS** | Fallback content only | **Native behavior** |
| **Template changes** | Wrap in island tags | Add data attributes |
| **Learning curve** | New concept | Standard web patterns |
| **Bundle size** | ~2KB loader | **~1.5KB loader** |
| **Framework support** | Designed for React/Vue | **Vanilla JS native** |
| **Problem solved** | Hydration tax | Script loading |

**Bengal should use Progressive Enhancements because**:
1. No hydration tax to solve (already vanilla JS)
2. HTML already works without JS (progressive enhancement is the default)
3. Simpler mental model (data attributes, not custom elements)
4. Plays to existing strengths

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Unified pattern | Some flexibility in naming |
| Conditional loading | Slight lazy-load delay |
| Clear documentation | Learning curve for contributors |
| Smaller per-page JS | More files to manage |

### Risks

#### Risk 1: Migration Complexity

**Description**: Existing themes may break during migration

- **Likelihood**: Low (backward compatible)
- **Impact**: Medium
- **Mitigation**:
  - Phased migration
  - Dual-mode: old scripts + new enhancements coexist
  - Clear migration guide

#### Risk 2: Lazy-Load Latency

**Description**: Non-preloaded enhancements have delay

- **Likelihood**: Medium
- **Impact**: Low (progressive enhancement = works anyway)
- **Mitigation**:
  - Preload critical enhancements
  - Use `modulepreload` hints
  - Keep enhancement scripts small

#### Risk 3: MutationObserver Performance

**Description**: Watching DOM for dynamic content has overhead

- **Likelihood**: Low
- **Impact**: Low
- **Mitigation**:
  - Make it configurable (`watch_dom = false`)
  - Only watch `childList`, not attributes
  - Debounce if needed

---

## Future Considerations

1. **Enhancement Dependencies**: Allow enhancements to declare dependencies on other enhancements
2. **Enhancement Options Schema**: Validate options at registration time
3. **Server-Side Hints**: Generate `<link rel="modulepreload">` based on page content
4. **Dev Tools**: Browser extension to visualize enhancements
5. **Enhancement Versioning**: Support multiple versions for gradual upgrades

---

## Related Work

- [Stimulus.js](https://stimulus.hotwired.dev/) - Controller pattern (similar philosophy)
- [Alpine.js](https://alpinejs.dev/) - Attribute-driven behavior
- [Enhance](https://enhance.dev/) - Web component progressive enhancement
- [Petite Vue](https://github.com/vuejs/petite-vue) - Minimal Vue for progressive enhancement
- **Bengal's existing `lazy-loaders.js`** - Foundation for this pattern

---

## Success Criteria

1. **Pattern Documented**: Clear documentation of enhancement pattern
2. **Backward Compatible**: Existing themes continue to work
3. **Reduced JS**: 30-50% reduction in JS loaded on simple pages
4. **Developer Experience**: Easy to create new enhancements
5. **Performance**: No regression in page load times

---

## Approval

- [ ] RFC reviewed
- [ ] Enhancement API approved
- [ ] Migration plan approved
- [ ] Implementation plan approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] Current state analyzed (builds on existing patterns)
- [x] Recommended approach justified
- [x] Architecture impact documented
- [x] Risks identified with mitigations
- [x] Implementation phases defined
- [x] Code examples provided
- [x] Comparison with alternatives (Islands)
- [x] Confidence ≥ 85% (88%)


