# RFC: Document Applications — A Post-Framework Paradigm

**Status**: Draft  
**Created**: 2025-12-22  
**Author**: Human + AI  
**Priority**: Strategic (Long-term vision)

---

## Executive Summary

This RFC proposes a fundamental shift in how Bengal approaches web output. Rather than generating "static sites that need JavaScript frameworks for interactivity," Bengal will generate **Document Applications**—semantic HTML documents that leverage modern browser capabilities for interactivity, state management, and navigation without framework runtimes.

The core thesis: **The browser is already a powerful application runtime. We've been ignoring it.**

**Key principles:**
- Documents as the unit of composition (not components)
- HTML/CSS as the runtime (not JavaScript frameworks)
- Author-time intelligence (not build-time compilation complexity)
- Browser-native capabilities (not framework abstractions)
- Progressive enhancement (not hydration)

---

## Problem Statement

### The Current Web Development Paradigm

Modern web development assumes complexity:

```
Typical "modern" documentation site:
────────────────────────────────────────────────────────────
Dependencies:     400+ npm packages
Bundle size:      200-500 KB JavaScript
Build time:       30-120 seconds
Concepts:         Components, hooks, state, hydration, SSR
Failure modes:    Hydration mismatch, bundle errors, version conflicts
────────────────────────────────────────────────────────────
```

This complexity exists because the dominant paradigm treats:
- JavaScript as the application runtime
- HTML as an implementation detail
- The browser as a rendering target, not a platform

### The Cost of Framework Complexity

| Problem | Impact |
|---------|--------|
| Bundle size | Slower initial load, mobile penalty |
| Hydration | Flash of unstyled content, interactivity delay |
| Build tooling | Configuration overhead, dependency management |
| Mental model | useState, useEffect, virtual DOM, reconciliation |
| Accessibility | Frameworks often break native browser behavior |
| Resilience | Sites break without JavaScript |

### What Browsers Can Do Now

Modern browsers (2024+) provide capabilities that eliminate the need for frameworks:

| Capability | Replaces | Support |
|------------|----------|---------|
| View Transitions API | React Router, page transitions | Chrome, Safari |
| Speculation Rules | Prefetch libraries | Chrome |
| `<dialog>` element | Modal libraries | All modern |
| `popover` attribute | Tooltip/dropdown libraries | All modern |
| `:has()` selector | JavaScript parent selection | All modern |
| `@container` queries | JavaScript resize observers | All modern |
| CSS nesting | Preprocessors | All modern |
| `<details>` element | Accordion libraries | All browsers |
| Form `method="dialog"` | Custom form handlers | All modern |
| Scroll-driven animations | JavaScript scroll handlers | Chrome, Safari |

---

## Goals

1. **Generate Document Applications** — Output that uses browser-native capabilities for interactivity
2. **Zero framework runtime** — No React, Vue, or framework code shipped to users
3. **Works without JavaScript** — Core functionality via HTML/CSS, JS enhances
4. **Instant navigation** — View transitions + speculation rules for SPA-like feel
5. **Author-time intelligence** — Complex analysis at build time, simple output at runtime
6. **Scales to complex sites** — The paradigm works for 10 pages or 10,000 pages

## Non-Goals

- Replacing JavaScript entirely (some interactivity requires JS)
- Building a component framework (explicitly rejected)
- Supporting legacy browsers (target evergreen browsers)
- Real-time collaborative features (different problem space)

---

## Design

### The Document Application Model

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    DOCUMENT APPLICATION                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  SEMANTIC HTML                       │   │
│  │  • Native elements (<dialog>, <details>, popover)   │   │
│  │  • ARIA roles and attributes                         │   │
│  │  • Meaningful structure                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 CSS STATE MACHINES                   │   │
│  │  • :has() for parent-based state                     │   │
│  │  • :target for URL-driven state                      │   │
│  │  • @container for component-scoped responsive        │   │
│  │  • View transitions for navigation                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ENHANCEMENT LAYER (Optional)            │   │
│  │  • Progressive enhancement for complex features      │   │
│  │  • No framework, vanilla JS                          │   │
│  │  • Declarative via data-* attributes                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Core Primitives

#### 1. View Transitions (Navigation)

**What**: Browser-native animated page transitions
**Replaces**: React Router, client-side routing, page transition libraries

```html
<!-- Bengal generates automatically -->
<meta name="view-transition" content="same-origin">

<style>
/* Fade transition for main content */
::view-transition-old(main-content) {
  animation: fade-out 150ms ease-out;
}
::view-transition-new(main-content) {
  animation: fade-in 150ms ease-in;
}

/* Slide transition for navigation */
::view-transition-old(nav) {
  animation: slide-out 200ms ease-out;
}
::view-transition-new(nav) {
  animation: slide-in 200ms ease-in;
}
</style>

<main style="view-transition-name: main-content">
  <!-- Content -->
</main>
```

**Configuration:**
```yaml
# bengal.yaml
view_transitions:
  enabled: true
  default_animation: crossfade  # crossfade | slide | none
  per_element:
    main: crossfade
    nav: persist
    toc: slide
```

#### 2. Speculation Rules (Prefetching)

**What**: Declarative hints for browser prefetching
**Replaces**: Prefetch libraries, preload hacks, custom link handlers

```html
<!-- Bengal generates based on content graph analysis -->
<script type="speculationrules">
{
  "prerender": [
    {
      "where": {
        "and": [
          { "href_matches": "/docs/*" },
          { "not": { "selector_matches": ".external" } }
        ]
      },
      "eagerness": "moderate"
    }
  ],
  "prefetch": [
    {
      "where": { "href_matches": "/*" },
      "eagerness": "conservative"
    }
  ]
}
</script>
```

**Configuration:**
```yaml
# bengal.yaml
speculation:
  enabled: true
  prerender:
    - pattern: "/docs/*"
      eagerness: moderate
  prefetch:
    - pattern: "/*"
      eagerness: conservative
  # Bengal can auto-generate based on:
  # - Link frequency analysis
  # - Navigation patterns
  # - Content relationships
  auto_generate: true
```

#### 3. CSS State Machines (Interactivity)

**What**: CSS-only state management using modern selectors
**Replaces**: useState, UI state libraries, toggle scripts

**Tabs via :target:**
```html
<!-- URL-driven tabs: /page#tab2 activates second tab -->
<nav role="tablist" class="tabs">
  <a href="#overview" role="tab">Overview</a>
  <a href="#api" role="tab">API</a>
  <a href="#examples" role="tab">Examples</a>
</nav>

<section id="overview" role="tabpanel" class="tab-panel">
  Overview content...
</section>
<section id="api" role="tabpanel" class="tab-panel">
  API content...
</section>
<section id="examples" role="tabpanel" class="tab-panel">
  Examples content...
</section>

<style>
/* Only show targeted panel, or first if none targeted */
.tab-panel { display: none; }
.tab-panel:target { display: block; }
.tab-panel:first-of-type:not(:has(~ .tab-panel:target)) { display: block; }

/* Style active tab */
.tabs a[href^="#"]:has(+ .tab-panel:target),
.tabs a:first-of-type:not(:has(~ a + .tab-panel:target)) {
  border-bottom: 2px solid var(--color-primary);
}
</style>
```

**Accordion via :has():**
```html
<div class="accordion">
  <details name="faq">
    <summary>Question 1</summary>
    <p>Answer 1...</p>
  </details>
  <details name="faq">
    <summary>Question 2</summary>
    <p>Answer 2...</p>
  </details>
</div>

<style>
/* Native accordion behavior, exclusive via name attribute */
details[name="faq"] summary {
  cursor: pointer;
  padding: 1rem;
}
details[name="faq"][open] summary {
  background: var(--color-surface-hover);
}
</style>
```

**Dark mode via :has():**
```html
<html>
  <body>
    <!-- Toggle anywhere in page -->
    <input type="checkbox" id="dark-mode" hidden>
    <label for="dark-mode">Toggle dark mode</label>

    <!-- Content -->
  </body>
</html>

<style>
html:has(#dark-mode:checked) {
  color-scheme: dark;
  --color-bg: #1a1a1a;
  --color-text: #e0e0e0;
}
</style>
```

#### 4. Native Dialogs (Modals)

**What**: `<dialog>` element for modal content
**Replaces**: Modal libraries, focus trap libraries, overlay management

```html
<dialog id="search-modal">
  <form method="dialog">
    <header>
      <h2>Search</h2>
      <button formmethod="dialog" value="cancel">✕</button>
    </header>
    <input type="search" name="q" autofocus>
    <menu>
      <button value="search">Search</button>
    </menu>
  </form>
</dialog>

<button onclick="document.getElementById('search-modal').showModal()">
  Search (⌘K)
</button>

<style>
dialog::backdrop {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}
dialog {
  border: none;
  border-radius: 8px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
</style>
```

**Features browser provides automatically:**
- Focus trapping
- Escape key closes
- Backdrop click closes (with small JS)
- Returns focus to trigger element
- Prevents background scroll
- Proper ARIA semantics

#### 5. Popover API (Tooltips, Dropdowns)

**What**: `popover` attribute for non-modal overlays
**Replaces**: Tooltip libraries, dropdown menus, floating UI

```html
<!-- Tooltip -->
<button popovertarget="tooltip-1">Hover me</button>
<div id="tooltip-1" popover>
  Helpful information here
</div>

<!-- Dropdown menu -->
<button popovertarget="menu" popovertargetaction="toggle">
  Options ▾
</button>
<nav id="menu" popover>
  <a href="/settings">Settings</a>
  <a href="/profile">Profile</a>
  <a href="/logout">Logout</a>
</nav>

<style>
[popover] {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>
```

### Author-Time Intelligence

Rather than complex build-time transformations, Bengal provides intelligence during authoring that results in simple output:

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTHOR-TIME INTELLIGENCE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Content Analysis:                                          │
│  • "This section has 4 code examples in different langs"    │
│    → Generate CSS-state tabs, URL-addressable               │
│                                                             │
│  • "These 3 pages are related via shared taxonomy"          │
│    → Generate speculation rules for prefetch                │
│                                                             │
│  • "This is the 3rd level of navigation"                    │
│    → Generate details/summary accordion                     │
│                                                             │
│  • "This content is referenced from 5 other pages"          │
│    → Pre-compute backlinks, inline in HTML                  │
│                                                             │
│  Link Analysis:                                             │
│  • "80% of users go from /intro to /quickstart"             │
│    → Prerender /quickstart aggressively                     │
│                                                             │
│  • "This external link is broken"                           │
│    → Error at build time, not runtime                       │
│                                                             │
│  Accessibility Analysis:                                    │
│  • "This content has no heading structure"                  │
│    → Warning with fix suggestion                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Configuration Schema

```yaml
# bengal.yaml - Document Application configuration

document_application:
  # Master switch
  enabled: true

  # Navigation experience
  navigation:
    view_transitions: true
    transition_style: crossfade  # crossfade | slide | morph | none
    speculation_rules: auto      # auto | manual | disabled
    scroll_restoration: true

  # Interactive patterns
  interactivity:
    tabs: css_state_machine      # css_state_machine | enhanced | classic
    accordions: native_details   # native_details | enhanced | classic
    modals: native_dialog        # native_dialog | enhanced
    tooltips: popover            # popover | enhanced | title_attr
    code_copy: enhanced          # Requires JS for clipboard

  # State management
  state:
    url_driven: true             # Use URL fragments/params for state
    form_actions: true           # Use forms for mutations
    local_storage: false         # Avoid client-side persistence

  # Fallback behavior
  fallback:
    no_js: graceful              # graceful | reduced | error
    legacy_browsers: basic       # basic | unsupported
```

---

## Implementation Plan

### Phase 1: View Transitions (Foundation)

**Scope**: Add View Transitions API support to Bengal's output

**Changes:**
1. Add view transition meta tag to base template
2. Add CSS for transition animations
3. Add `view-transition-name` to key elements (main, nav, toc)
4. Configuration options for transition styles

**Files affected:**
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/assets/css/base/transitions.css`
- `bengal/config/defaults.py`

**Output example:**
```html
<meta name="view-transition" content="same-origin">
<style>
  @view-transition { navigation: auto; }
  main { view-transition-name: main-content; }
</style>
```

### Phase 2: Speculation Rules (Performance)

**Scope**: Generate speculation rules based on content graph

**Changes:**
1. Analyze link patterns during build
2. Generate speculation rules JSON
3. Inject into page head
4. Configuration for prefetch aggressiveness

**Files affected:**
- `bengal/postprocess/speculation.py` (new)
- `bengal/analysis/link_patterns.py` (new)
- `bengal/themes/default/templates/base.html`

**Output example:**
```html
<script type="speculationrules">
{
  "prerender": [{ "where": { "href_matches": "/docs/*" }, "eagerness": "moderate" }],
  "prefetch": [{ "where": { "href_matches": "/*" }, "eagerness": "conservative" }]
}
</script>
```

### Phase 3: CSS State Machines (Interactivity)

**Scope**: Replace JavaScript-dependent patterns with CSS

**Changes:**
1. Refactor tab directive to use :target/:has()
2. Refactor accordion to use native details
3. Generate CSS state machine styles
4. Ensure URL-addressable state

**Files affected:**
- `bengal/directives/tabs.py`
- `bengal/themes/default/assets/css/components/_tabs.css`
- `bengal/themes/default/assets/css/components/_accordion.css`

**Before:**
```html
<div class="tabs" data-bengal="tabs">
  <button data-tab="1">Tab 1</button>
  ...
</div>
<script>/* Tab switching logic */</script>
```

**After:**
```html
<nav role="tablist" class="tabs">
  <a href="#tab1" role="tab">Tab 1</a>
  ...
</nav>
<section id="tab1" role="tabpanel">...</section>
<style>/* CSS state machine */</style>
<!-- No JavaScript required -->
```

### Phase 4: Native Dialogs (Modals)

**Scope**: Use `<dialog>` for all modal content

**Changes:**
1. Refactor search modal to use `<dialog>`
2. Add dialog styles to theme
3. Minimal JS for keyboard shortcut (Cmd+K)
4. Ensure focus management works

**Files affected:**
- `bengal/themes/default/templates/partials/search-modal.html`
- `bengal/themes/default/assets/css/components/_dialog.css`
- `bengal/themes/default/assets/js/enhancements/search.js`

### Phase 5: Popover Integration (Tooltips)

**Scope**: Use popover attribute for tooltips and dropdowns

**Changes:**
1. Add popover support to tooltip directive
2. Refactor mobile nav to use popover
3. Add popover styles
4. Graceful fallback for older browsers

**Files affected:**
- `bengal/directives/tooltip.py` (new)
- `bengal/themes/default/templates/partials/mobile-nav.html`
- `bengal/themes/default/assets/css/components/_popover.css`

### Phase 6: Author-Time Intelligence

**Scope**: Enhance build-time analysis for smarter output

**Changes:**
1. Link pattern analysis for speculation rules
2. Content relationship inference for prefetch hints
3. Accessibility analysis warnings
4. Navigation pattern suggestions

**Files affected:**
- `bengal/analysis/content_intelligence.py` (new)
- `bengal/health/validators/accessibility.py` (new)
- `bengal/postprocess/speculation.py`

---

## Migration Strategy

### For Existing Bengal Sites

**Phase 1-2 (View Transitions + Speculation):**
- Opt-in via configuration
- No breaking changes
- Additive enhancement

**Phase 3-5 (CSS State Machines + Native Elements):**
- Existing directives continue to work
- New `mode: native` option for directives
- Gradual migration path

**Configuration for gradual adoption:**
```yaml
document_application:
  enabled: true

  # Migrate incrementally
  interactivity:
    tabs: enhanced           # Keep current JS-enhanced tabs
    accordions: native_details  # Switch to native
    modals: native_dialog    # Switch to native
```

### Fallback Behavior

For browsers without full support:

| Feature | Fallback |
|---------|----------|
| View Transitions | Standard navigation (no animation) |
| Speculation Rules | Ignored (no prefetch, still works) |
| `:has()` | JavaScript enhancement layer |
| `popover` | JavaScript enhancement layer |
| `<dialog>` | Polyfill or enhanced fallback |

---

## Success Criteria

### Quantitative

- [ ] Zero framework JavaScript in default output
- [ ] < 10 KB total JavaScript (enhancement layer only)
- [ ] View transitions enabled on all page navigations
- [ ] Speculation rules generated for 80%+ internal links
- [ ] All interactive patterns work without JavaScript

### Qualitative

- [ ] Navigation feels instant (< 100ms perceived)
- [ ] No flash of unstyled content
- [ ] Back button works correctly for all state
- [ ] URLs are shareable with state preserved
- [ ] Screen readers announce transitions appropriately

### Lighthouse Metrics

- [ ] Performance: 95+
- [ ] Accessibility: 100
- [ ] Best Practices: 100
- [ ] SEO: 100

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Browser API changes | Low | Medium | Feature detection, progressive enhancement |
| Safari View Transitions lag | Medium | Low | Graceful degradation, works without |
| Developer unfamiliarity | Medium | Medium | Documentation, examples, migration guides |
| CSS complexity | Low | Low | Generate CSS, developers don't write it |
| Legacy browser users | Low | Low | Define support matrix, basic fallback |

---

## Open Questions

1. **Should CSS state machines be opt-in or default?**
   - Opt-in: Safer, less surprising
   - Default: Cleaner output, forces the paradigm

2. **How aggressive should speculation rules be?**
   - Conservative: Minimal bandwidth, slower perceived nav
   - Aggressive: Faster nav, higher bandwidth cost

3. **Should we ship a polyfill for `<dialog>` on older browsers?**
   - Yes: Better compatibility
   - No: Smaller bundle, clearer support matrix

4. **How do we handle JavaScript-required features (clipboard, etc.)?**
   - Inline script: Simple, no module system
   - Enhancement layer: Consistent with current approach

---

## Appendix: The Philosophical Foundation

### Why "Document Applications"?

The web was built on documents. HTML is a document format. The browser is a document viewer that became an application platform. Somewhere along the way, we forgot that documents are powerful.

A Document Application is:
- **A document first** — Semantic HTML that means something
- **An application second** — Behavior added via platform capabilities
- **Framework-free** — The browser provides the runtime
- **Progressively enhanced** — Works without JavaScript, better with it
- **URL-driven** — State lives in the URL, not in memory
- **Server-rendered** — Intelligence at build time, simplicity at runtime

### The Bengal Advantage

Bengal is uniquely positioned to pioneer Document Applications because:

1. **Python heritage**: Not tied to JavaScript ecosystem assumptions
2. **Documentation focus**: Content-heavy sites benefit most
3. **Build-time intelligence**: Already analyzes content graph
4. **Validation culture**: Can enforce Document Application patterns
5. **Progressive enhancement**: Already the philosophy

### The Future We're Building

```
Today:                              Tomorrow:
─────────────────────────────────   ─────────────────────────────────
npm install (400 packages)          pip install bengal
webpack.config.js                   bengal.yaml
React.useState()                    URL state
Bundle optimization                 Nothing to bundle
Hydration debugging                 Nothing to hydrate
"Why is this re-rendering?"         HTML doesn't re-render
Framework upgrade treadmill         Browser improves for free
─────────────────────────────────   ─────────────────────────────────
```

---

## References

- [View Transitions API](https://developer.chrome.com/docs/web-platform/view-transitions/)
- [Speculation Rules API](https://developer.chrome.com/docs/web-platform/prerender-pages/)
- [CSS :has() selector](https://developer.mozilla.org/en-US/docs/Web/CSS/:has)
- [Dialog element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog)
- [Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API)
- [HTMX Essays](https://htmx.org/essays/)
- [The Rule of Least Power](https://www.w3.org/2001/tag/doc/leastPower.html)

---

## Changelog

- **2025-12-22**: Initial draft
