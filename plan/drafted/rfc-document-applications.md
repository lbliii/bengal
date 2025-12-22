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

### Browser Support Matrix

Specific version requirements for Document Application features:

| Feature | Chrome | Firefox | Safari | Edge | Notes |
|---------|--------|---------|--------|------|-------|
| View Transitions API | 111+ | ❌ Not yet | 18+ | 111+ | Falls back to instant navigation |
| Speculation Rules | 109+ | ❌ Not yet | ❌ Not yet | 109+ | Ignored if unsupported |
| `:has()` selector | 105+ | 121+ | 15.4+ | 105+ | 97%+ global support |
| `popover` attribute | 114+ | 125+ | 17+ | 114+ | 93%+ global support |
| `<dialog>` element | 37+ | 98+ | 15.4+ | 79+ | 97%+ global support |
| `@starting-style` | 117+ | ❌ Not yet | 17.4+ | 117+ | Graceful degradation |
| CSS Nesting | 120+ | 117+ | 17.2+ | 120+ | 95%+ global support |

**Target Browser Policy**: Evergreen browsers only. Features degrade gracefully on unsupported browsers.

**Firefox Impact**: ~3% of users. View Transitions and Speculation Rules will not apply, but sites remain fully functional with standard navigation.

---

## Current Theme Assessment

Bengal's default theme is **partially there**. Here's what we're starting with:

| Component | Current Implementation | Status |
|-----------|----------------------|--------|
| Search Modal | ✅ Already using `<dialog>` | Done |
| Tabs | JS class toggling (`tabs.js`, 167 lines) | Needs migration |
| Mobile Nav | Custom JS drawer (`mobile-nav.js`, 285 lines) | Needs migration |
| Theme Dropdown | Custom JS menu | Needs migration |
| TOC Scroll-spy | JS IntersectionObserver | Keep (requires JS) |
| Code Copy | JS clipboard API | Keep (requires JS) |
| Lightbox | JS enhancement | Keep (requires JS) |

**JavaScript savings estimate:** ~450 lines of JS can be replaced with ~50 lines of CSS.

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

## End User Impact

### Quantifiable Benefits

| Metric | Current | Document Application | Impact |
|--------|---------|---------------------|--------|
| Initial JS load | ~25-40 KB | ~10-15 KB | 2-3x faster TTI |
| Navigation feel | Instant cut | Smooth animation | More polished |
| Link click → render | 100-500ms | 10-50ms (prerendered) | Near-instant |
| Back button | Sometimes broken | Always works | Less frustration |
| Shareable URLs | State often lost | State preserved in URL | Actually useful |
| No-JS experience | Partially broken | Fully functional | Accessibility win |
| Mobile battery | More JS = more drain | Less JS = longer battery | Real-world impact |
| Slow connections | Wait for JS | Works immediately | Huge for emerging markets |

### User Experience Difference

```
Current: Click link → white flash → content appears
                     ⎣━━━━ 150-400ms ━━━━⎦

Document Application: Click link → smooth crossfade → content slides in
                                  ⎣━━━ 100ms (but feels seamless) ━━━⎦
```

**The honest downside:** Users won't consciously notice. They'll just think "this site feels nice" without knowing why. That's the goal, but it's hard to market.

---

## Theme Developer Impact

### Who Would Love It

**CSS-first developers** — The majority of theme creators:

> "Finally, I can build interactive components without JavaScript!"  
> "Modern CSS is so powerful, why was I writing JS for tabs?"  
> ":has() is like magic. This is what CSS should have always been."

- Their core skill is CSS — This empowers them
- Simpler debugging — No more "why isn't my event handler firing?"
- Fewer dependencies — No build step, no bundlers
- Modern CSS is beautiful — Container queries, `:has()`, nesting

### Who Would Hate It

**JavaScript-heavy theme developers** — A minority, but vocal:

> "I have to learn new CSS patterns?"  
> "This breaks my existing customizations."  
> "What if I need complex state that CSS can't handle?"

**Realities:**
- Existing theme overrides may break
- Some patterns are genuinely harder (synced tabs across page)
- Learning curve for `:has()`, `@starting-style`, popover

### Theme Migration Compatibility

```css
/* Existing theme customization: */

/* This still works ✓ */
.tabs { background: var(--my-color); }
.tab-nav a { font-family: var(--my-font); }

/* This might break ✗ */
.tab-pane.active { ... }  →  .tab-pane:target { ... }
.tab-nav li.active a { }  →  .tab-nav a[aria-selected="true"] { }
```

**Mitigation:** Keep both CSS files during transition, let themers opt-in.

### The Honest Pitch to Themers

```
"Your CSS skills are now enough to build interactive themes.
 No JavaScript required for 90% of interactivity.
 The 10% that needs JS is smaller, simpler, optional."
```

**The honest catch:**

```
"You need to learn :has(), @starting-style, popover, and dialog.
 These are 2024 CSS features. They're well-supported but new.
 Existing theme overrides may need updates."
```

---

## Styling Limitations — Honest Assessment

### ✅ No Limitations (Same or Better)

**View Transitions:**
```css
/* You have MORE control, not less */
::view-transition-old(main) {
  animation: custom-exit 200ms ease-out;
}
::view-transition-new(main) {
  animation: custom-enter 200ms ease-in;
}

/* Can even do morphing between elements */
.card { view-transition-name: card-1; }
/* Card smoothly morphs between list → detail view */
```

**Dialogs:**
```css
/* Full styling freedom */
dialog {
  background: var(--anything);
  border: none;
  border-radius: var(--whatever);
  box-shadow: var(--as-fancy-as-you-want);
}

dialog::backdrop {
  background: linear-gradient(...);
  backdrop-filter: blur(20px);
  /* Full CSS control */
}
```

**Popovers:**
```css
/* Same freedom as any element */
[popover] {
  background: var(--glass-effect);
  border: 1px solid var(--border);
  animation: pop-in 150ms ease-out;
}
```

### ⚠️ Minor Limitations (Workarounds Exist)

**1. Popover Positioning**

```css
/* Current limitation: No automatic anchor positioning yet */
/* CSS Anchor Positioning API is coming, but not universal */

/* Workaround: Manual positioning */
[popover] {
  position: fixed;
  top: var(--trigger-bottom);
  left: var(--trigger-left);
}

/* Or use a small JS helper for position only */
```

**2. Dialog Open/Close Animation**

```css
/* Requires @starting-style (Chrome 117+, Safari 17.4+) */
dialog {
  opacity: 0;
  transform: scale(0.95);
  transition: opacity 200ms, transform 200ms, display 200ms allow-discrete;
}

dialog[open] {
  opacity: 1;
  transform: scale(1);
}

@starting-style {
  dialog[open] {
    opacity: 0;
    transform: scale(0.95);
  }
}
```

Firefox: Works but no exit animation (snaps closed). ~5% of users.  
**Fallback:** Graceful degradation, still functional.

**3. Tab Indicator Animation**

```css
/* Current: JS can animate the underline sliding between tabs */

/* CSS-only: Underline can't "slide" between tabs */
/* It appears instantly on the new tab */

/* Workaround: Fade transition instead */
.tab-nav a::after {
  opacity: 0;
  transition: opacity 150ms;
}
.tabs:has(#tab1:target) a[href="#tab1"]::after {
  opacity: 1;
}
```

Honestly? The fade looks just as good. Sliding underlines are overrated.

### ❌ Genuine Limitations (Require JS)

**1. Synchronized Tab Groups**

```markdown
<!-- Page has two tab groups, user wants them synced -->
<!-- e.g., "Python" selected in one → "Python" selected in all -->

CSS can't do this. URL has one #fragment.
```

**Solution:** Keep a small enhancement for this specific case:
```javascript
// 15 lines of JS for synced tabs (opt-in)
document.querySelectorAll('[data-sync-group]').forEach(...)
```

**2. Complex Dropdown Positioning**

```
Dropdown needs to:
- Flip when near edge
- Avoid viewport overflow
- Align to trigger precisely

CSS Anchor Positioning solves this but isn't universal yet.
```

**Solution:** Use Floating UI (~3KB) for just this, or accept simpler positioning.

**3. State Persistence Across Pages**

```
User sets dark mode on page A
Page B needs to know about it
```

**Solution:** Already needs JS for localStorage. This doesn't change.

### Will Sites Look Worse?

**No. They can look better.**

```
Current Beautiful Site:
─────────────────────────────────────
• Smooth animations ← (still possible, CSS)
• Rich visual design ← (unchanged)
• Interactive elements ← (now native, equally stylable)
• Consistent feel ← (improved with view transitions)

What you lose: Nothing visible
What you gain: Smoother page transitions, faster feel
```

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

#### CSS Generation Strategy for Tabs

The CSS state machine for tabs requires ID-specific selectors. Two approaches:

**Option A: Generic CSS with Attribute Selectors (Recommended)**

```css
/* Generic rules that work for any tab set */
.tabs .tab-pane { display: none; }
.tabs .tab-pane:first-of-type { display: block; }
.tabs .tab-pane:target { display: block; }
.tabs:has(.tab-pane:target) .tab-pane:first-of-type:not(:target) { display: none; }

/* Active tab styling using general sibling + :target */
.tab-nav a { color: var(--color-text-secondary); }
.tab-nav a:first-of-type { color: var(--color-primary); border-bottom-color: var(--color-primary); }

/* When any tab pane is targeted, find its corresponding nav link */
.tabs:has(.tab-pane:target) .tab-nav a:first-of-type {
  color: var(--color-text-secondary);
  border-bottom-color: transparent;
}

/* Match nav link href to targeted pane */
.tab-nav a[href]:has(~ .tab-content .tab-pane:target[id]) {
  /* This requires the nav link href to match the pane id */
}
```

**Limitation**: CSS cannot directly match `a[href="#foo"]` to `#foo:target` without additional structure.

**Solution**: Use `data-*` attributes for pairing:

```html
<div class="tabs" id="example-tabs">
  <nav class="tab-nav" role="tablist">
    <a href="#example-tabs-py" data-pane="example-tabs-py">Python</a>
    <a href="#example-tabs-js" data-pane="example-tabs-js">JavaScript</a>
  </nav>
  <div class="tab-content">
    <section id="example-tabs-py" class="tab-pane">...</section>
    <section id="example-tabs-js" class="tab-pane">...</section>
  </div>
</div>
```

```css
/* Use :has() with ID matching via adjacent structure */
.tabs:has(#example-tabs-py:target) a[data-pane="example-tabs-py"],
.tabs:has(#example-tabs-js:target) a[data-pane="example-tabs-js"] {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}
```

**Option B: Inline Scoped Styles (Alternative)**

Generate `<style>` block per tab set:

```html
<div class="tabs" id="tabs-a1b2c3">
  <style>
    #tabs-a1b2c3:has(#tabs-a1b2c3-py:target) a[href="#tabs-a1b2c3-py"],
    #tabs-a1b2c3:has(#tabs-a1b2c3-js:target) a[href="#tabs-a1b2c3-js"] {
      color: var(--color-primary);
    }
  </style>
  <!-- tab content -->
</div>
```

**Trade-off**: Increases HTML size but provides precise scoping.

**Recommendation**: Start with Option A (generic CSS) and fall back to Option B for edge cases.

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

## Concrete Before/After Examples

### Example 1: Tabs Component

#### Current Implementation (tabs.js + tabs.css)

```html
<!-- Current Bengal output -->
<div class="tabs">
  <ul class="tab-nav">
    <li class="active"><a href="#" data-tab-target="python-example">Python</a></li>
    <li><a href="#" data-tab-target="javascript-example">JavaScript</a></li>
    <li><a href="#" data-tab-target="go-example">Go</a></li>
  </ul>
  <div class="tab-content">
    <div id="python-example" class="tab-pane active">
      <pre><code>print("Hello")</code></pre>
    </div>
    <div id="javascript-example" class="tab-pane">
      <pre><code>console.log("Hello")</code></pre>
    </div>
    <div id="go-example" class="tab-pane">
      <pre><code>fmt.Println("Hello")</code></pre>
    </div>
  </div>
</div>

<script src="js/enhancements/tabs.js"></script> <!-- 167 lines -->
```

#### Document Application (CSS-only, URL-driven)

```html
<!-- Document Application output -->
<div class="tabs" id="code-example">
  <nav class="tab-nav" role="tablist">
    <a href="#code-example-python" role="tab"
       aria-selected="true" aria-controls="code-example-python">Python</a>
    <a href="#code-example-js" role="tab"
       aria-controls="code-example-js">JavaScript</a>
    <a href="#code-example-go" role="tab"
       aria-controls="code-example-go">Go</a>
  </nav>
  <div class="tab-content">
    <section id="code-example-python" role="tabpanel" class="tab-pane">
      <pre><code>print("Hello")</code></pre>
    </section>
    <section id="code-example-js" role="tabpanel" class="tab-pane">
      <pre><code>console.log("Hello")</code></pre>
    </section>
    <section id="code-example-go" role="tabpanel" class="tab-pane">
      <pre><code>fmt.Println("Hello")</code></pre>
    </section>
  </div>
</div>

<!-- No JavaScript needed -->
```

#### CSS State Machine for Tabs

```css
/* New: tabs-native.css */

/* Default: show first pane */
.tabs .tab-pane {
  display: none;
}
.tabs .tab-pane:first-of-type {
  display: block;
}

/* URL-targeted pane becomes visible */
.tabs .tab-pane:target {
  display: block;
}

/* Hide first pane when another is targeted */
.tabs:has(.tab-pane:target) .tab-pane:first-of-type:not(:target) {
  display: none;
}

/* Active tab styling via :has() */
.tab-nav a {
  color: var(--color-text-tertiary);
  border-bottom: 2px solid transparent;
}

/* First tab active by default */
.tab-nav a:first-of-type {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* When a pane is targeted, style corresponding tab */
.tabs:has(#code-example-python:target) .tab-nav a[href="#code-example-python"],
.tabs:has(#code-example-js:target) .tab-nav a[href="#code-example-js"],
.tabs:has(#code-example-go:target) .tab-nav a[href="#code-example-go"] {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* Remove first-tab styling when another is targeted */
.tabs:has(.tab-pane:target:not(:first-of-type)) .tab-nav a:first-of-type {
  color: var(--color-text-tertiary);
  border-bottom-color: transparent;
}
```

**Benefits:**
- URL shareable: `/docs/example#code-example-js` opens JavaScript tab
- Back button works
- Zero JavaScript
- Works without JS enabled

### Example 2: Theme Dropdown

#### Current Implementation (theme-controls.html + JS)

```html
<!-- Current: Custom JS dropdown -->
<div class="theme-dropdown">
  <button class="theme-dropdown__button" aria-haspopup="true" aria-expanded="false">
    <span class="theme-dropdown__icon">{{ icon("palette") }}</span>
    <span>Appearance</span>
    {{ icon("chevron-down") }}
  </button>
  <ul class="theme-dropdown__menu">
    <li class="separator">Mode</li>
    <li><button data-appearance="system">System</button></li>
    <li><button data-appearance="light">Light</button></li>
    <li><button data-appearance="dark">Dark</button></li>
    <li class="separator">Palette</li>
    <li><button data-palette="snow-lynx">Snow Lynx</button></li>
    <!-- ... more palettes -->
  </ul>
</div>

<script>
// JS handles: open/close, click outside, escape key, aria-expanded
</script>
```

#### Document Application (Popover API)

```html
<!-- Document Application: Native popover -->
<div class="theme-controls">
  <button popovertarget="theme-menu" class="theme-dropdown__button">
    {{ icon("palette", size=24) }}
    <span>Appearance</span>
    {{ icon("chevron-down", size=20) }}
  </button>

  <div id="theme-menu" popover class="theme-dropdown__menu">
    <fieldset>
      <legend class="separator">Mode</legend>
      <label><input type="radio" name="appearance" value="system" checked> System</label>
      <label><input type="radio" name="appearance" value="light"> Light</label>
      <label><input type="radio" name="appearance" value="dark"> Dark</label>
    </fieldset>
    <fieldset>
      <legend class="separator">Palette</legend>
      <label><input type="radio" name="palette" value="snow-lynx"> Snow Lynx</label>
      <label><input type="radio" name="palette" value="brown-bengal"> Brown Bengal</label>
      <!-- ... -->
    </fieldset>
  </div>
</div>

<script>
// Minimal JS: just persist selection to localStorage
document.querySelector('#theme-menu').addEventListener('change', (e) => {
  if (e.target.name === 'appearance') {
    localStorage.setItem('bengal-theme', e.target.value);
    document.documentElement.dataset.theme = e.target.value;
  }
  // ... palette handling
});
</script>
```

**Benefits:**
- Browser handles: open/close, click outside, escape key, focus management
- ~50% less JavaScript
- Native animations available via CSS

### Example 3: Mobile Navigation

#### Current Implementation (mobile-nav.js — 285 lines)

```html
<!-- Current: Custom drawer implementation -->
<button class="mobile-nav-toggle">☰</button>
<div class="mobile-nav-backdrop"></div>
<nav class="mobile-nav">
  <div class="mobile-nav-header">
    <button class="mobile-nav-close">✕</button>
  </div>
  <ul><!-- menu items --></ul>
</nav>

<script>
// Handles: toggle, backdrop click, escape, focus trap, inert, resize
// 285 lines of JavaScript
</script>
```

#### Document Application (Native Dialog)

```html
<!-- Document Application: Dialog as drawer -->
<button class="mobile-nav-toggle" onclick="mobileNav.showModal()">
  {{ icon('list', size=24) }}
</button>

<dialog id="mobile-nav" class="mobile-nav-dialog">
  <form method="dialog" class="mobile-nav-header">
    <span class="logo">{{ site.title }}</span>
    <button value="close" class="mobile-nav-close">
      {{ icon('x', size=16) }}
      <span>Close</span>
    </button>
  </form>

  <nav>
    <ul>
      {% for item in menu %}
      <li><a href="{{ item.href }}">{{ item.name }}</a></li>
      {% endfor %}
    </ul>
  </nav>

  <div class="mobile-nav-footer">
    {% include 'partials/theme-controls.html' %}
  </div>
</dialog>

<script>
// Just the shortcut to get element - browser handles everything else
const mobileNav = document.getElementById('mobile-nav');

// Close on link click (for same-page navigation)
mobileNav.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => mobileNav.close());
});
</script>
```

#### CSS for Dialog-as-Drawer

```css
/* Mobile nav as slide-in drawer */
.mobile-nav-dialog {
  position: fixed;
  inset: 0;
  margin: 0;
  padding: 0;
  width: min(320px, 85vw);
  height: 100%;
  max-height: 100%;
  border: none;
  background: var(--color-bg-primary);
  box-shadow: 4px 0 25px rgba(0, 0, 0, 0.15);

  /* Slide in from left */
  transform: translateX(-100%);
  transition: transform 0.3s ease-out,
              opacity 0.3s ease-out,
              display 0.3s allow-discrete;
}

.mobile-nav-dialog[open] {
  transform: translateX(0);
}

/* Starting state for transition */
@starting-style {
  .mobile-nav-dialog[open] {
    transform: translateX(-100%);
  }
}

.mobile-nav-dialog::backdrop {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  opacity: 0;
  transition: opacity 0.3s;
}

.mobile-nav-dialog[open]::backdrop {
  opacity: 1;
}
```

**Benefits:**
- Browser handles: focus trap, escape key, backdrop click, inert background
- Animated open/close via CSS `@starting-style`
- ~250 fewer lines of JavaScript
- Accessibility handled by browser

### Example 4: View Transitions (New Addition)

Add to `base.html` `<head>`:

```html
<!-- Document Application: View Transitions -->
<meta name="view-transition" content="same-origin">

<style>
  /* Named elements for transitions */
  main { view-transition-name: main-content; }
  .docs-nav { view-transition-name: docs-nav; }
  .toc-sidebar { view-transition-name: toc; }
  .page-hero { view-transition-name: hero; }

  /* Transition animations */
  ::view-transition-old(main-content) {
    animation: fade-slide-out 150ms ease-out;
  }
  ::view-transition-new(main-content) {
    animation: fade-slide-in 150ms ease-in;
  }

  @keyframes fade-slide-out {
    to { opacity: 0; transform: translateY(-10px); }
  }
  @keyframes fade-slide-in {
    from { opacity: 0; transform: translateY(10px); }
  }

  /* Keep nav stable during transition */
  ::view-transition-old(docs-nav),
  ::view-transition-new(docs-nav) {
    animation: none;
  }
</style>
```

**Result:** Every page navigation now animates smoothly—feels like an SPA, is actually multi-page.

### Example 5: Speculation Rules (New Addition)

Add to `base.html` before `</head>`:

```html
<!-- Document Application: Speculation Rules -->
<script type="speculationrules">
{
  "prerender": [
    {
      "where": {
        "and": [
          { "href_matches": "/docs/*" },
          { "not": { "selector_matches": "[data-external]" } }
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

**Result:** Browser prerenders likely destinations. Navigation feels instant.

---

## Visual Comparison

```
CURRENT THEME                          DOCUMENT APPLICATION THEME
─────────────────────────────────────  ─────────────────────────────────────

base.html <head>:                      base.html <head>:
  • Meta tags                            • Meta tags
  • Stylesheets                          • Stylesheets
  • Theme init script                    • Theme init script (smaller)
                                         • <meta view-transition>
                                         • <script type="speculationrules">

JavaScript loaded:                     JavaScript loaded:
  • utils.js                             • utils.js
  • bengal-enhance.js                    • bengal-enhance.js
  • theme.js                             • theme.js (smaller)
  • search.js                            • search.js
  • nav-dropdown.js                      • (removed - popover handles)
  • mobile-nav.js (285 lines)            • (removed - dialog handles)
  • tabs.js (167 lines)                  • (removed - CSS handles)
  • toc.js                               • toc.js
  • interactive.js                       • interactive.js (smaller)
  • ...                                  • ...

Total JS estimate: ~25KB               Total JS estimate: ~12KB

Page transition: Instant cut           Page transition: Smooth animation
Link prefetch: Manual/none             Link prefetch: Automatic
Tab state: Lost on refresh             Tab state: URL preserved
Mobile nav: Custom focus trap          Mobile nav: Native dialog
Theme menu: Custom dropdown            Theme menu: Native popover
```

---

## Implementation Plan

### Phase 1: View Transitions (Foundation) — 1-2 days

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

### Phase 2: Speculation Rules (Performance) — 1 day

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

### Phase 3: Theme Controls Migration — 1 day

**Scope**: Convert theme dropdown to popover API

**Changes:**
1. Update theme-controls.html to use popover
2. Reduce theme.js to just persistence logic
3. Add popover styles

**Files affected:**
- `bengal/themes/default/templates/partials/theme-controls.html`
- `bengal/themes/default/assets/js/core/theme.js`
- `bengal/themes/default/assets/css/components/dropdowns.css`

### Phase 4: Mobile Nav Migration — 2 days

**Scope**: Convert mobile nav to native dialog

**Changes:**
1. Update mobile-nav markup to use `<dialog>`
2. Add CSS drawer animation with `@starting-style`
3. Remove `mobile-nav.js` (keep 20-line replacement)
4. Test focus management

**Files affected:**
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/assets/css/components/navigation.css`
- `bengal/themes/default/assets/js/enhancements/mobile-nav.js` (delete or minimize)

### Phase 5: CSS State Machine Tabs — 4-5 days

**Scope**: Replace JS tabs with CSS state machine

**Why longer estimate**: The `tabs.py` directive (392 lines) has complex HTML extraction logic that must be refactored. Additionally, CSS generation strategy requires careful implementation.

**Changes:**
1. Refactor `TabSetDirective.render()` to output `:target`-compatible HTML
2. Update HTML structure: `data-tab-target` → `href="#id"` fragment links
3. New `tabs-native.css` for CSS state machine (see CSS Generation Strategy)
4. Add `data-pane` attributes for CSS selector pairing
5. Keep JS fallback for complex cases (synced tabs via `data-sync`)
6. Migration script for existing content using old tab syntax
7. Update existing content if needed

**Files affected:**
- `bengal/directives/tabs.py` — Major refactor of `render()` method
- `bengal/themes/default/assets/css/components/tabs.css` — New CSS state machine rules
- `bengal/themes/default/assets/css/components/tabs-native.css` — New file
- `bengal/themes/default/assets/js/enhancements/tabs.js` — Keep minimal version for sync feature
- `scripts/migrate_tabs_syntax.py` — New migration helper

**Breakdown:**
- Day 1-2: Directive HTML output refactoring
- Day 3: CSS state machine implementation
- Day 4: Testing and edge cases (nested tabs, sync groups)
- Day 5: Documentation and migration tooling

### Phase 6: Author-Time Intelligence — 3-5 days

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

## Testing Plan

### Unit Tests

| Component | Test Coverage | Priority |
|-----------|--------------|----------|
| View Transitions meta tag generation | Template output verification | P0 |
| Speculation Rules JSON generation | Schema validation, pattern matching | P0 |
| CSS state machine HTML output | Tab directive renders correct structure | P0 |
| Dialog/Popover HTML attributes | Semantic correctness | P1 |
| Fallback behavior | Feature detection paths | P1 |

**Test files to create:**
- `tests/unit/rendering/test_view_transitions.py`
- `tests/unit/postprocess/test_speculation_rules.py`
- `tests/unit/directives/test_tabs_native.py`
- `tests/unit/themes/test_dialog_components.py`

### Integration Tests

```python
# Example: Verify CSS state machine tabs work end-to-end
def test_tabs_css_state_machine_integration(built_site):
    """Tabs should be URL-addressable and work without JS."""
    page = built_site.get_page("/docs/example/")

    # Verify HTML structure
    assert 'href="#code-example-python"' in page.html
    assert 'role="tabpanel"' in page.html
    assert 'id="code-example-python"' in page.html

    # Verify no JS dependency in critical path
    assert 'data-tab-target=' not in page.html  # Old JS pattern removed
```

### Browser Testing

**Tools**: Playwright for cross-browser testing

```yaml
# .github/workflows/browser-tests.yml
browser-matrix:
  - chromium  # View Transitions, Speculation Rules
  - firefox   # Fallback behavior verification
  - webkit    # Safari approximation
```

**Manual Testing Checklist:**
- [ ] View Transitions: Smooth navigation between pages (Chrome/Edge)
- [ ] Fallback: Standard navigation works (Firefox)
- [ ] Tabs: URL fragment updates, back button works
- [ ] Dialog: Focus trap, Escape key, backdrop click
- [ ] Popover: Opens/closes, dismisses on outside click
- [ ] Mobile nav: Slide animation, focus management
- [ ] No-JS mode: All content accessible with JS disabled

### Accessibility Testing

**Automated**: axe-core integration in CI

```bash
# Run accessibility audit on built site
bengal build && npx @axe-core/cli http://localhost:8000
```

**Manual WCAG 2.1 AA Checklist:**
- [ ] Dialog announces to screen readers
- [ ] Tab navigation follows ARIA authoring practices
- [ ] Focus visible on all interactive elements
- [ ] View transitions respect `prefers-reduced-motion`

### Performance Testing

**Baseline capture before implementation:**

```bash
# Capture current metrics
lighthouse http://localhost:8000 --output=json --output-path=baseline.json
```

**Post-implementation comparison:**
- Time to Interactive (TTI)
- Total Blocking Time (TBT)
- JavaScript bundle size
- Largest Contentful Paint (LCP)

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
| `<dialog>` | Already supported, minimal polyfill if needed |
| `@starting-style` | No animation, snaps open/closed (functional) |

### Rollback Strategy

Each Document Application feature can be disabled independently via configuration:

```yaml
# bengal.yaml - Disable features individually if issues arise
document_application:
  enabled: true

  # Feature flags for rollback
  features:
    view_transitions: false    # Disable if causing visual glitches
    speculation_rules: false   # Disable if bandwidth concerns
    native_tabs: false         # Fall back to JS tabs
    native_dialogs: true       # Keep working features
    native_popovers: false     # Fall back to JS dropdowns
```

**Rollback Procedure:**

1. **Immediate** (config change): Set feature flag to `false`, rebuild
2. **Code rollback**: Each phase is a separate PR, revert specific PR if needed
3. **Full rollback**: Set `document_application.enabled: false` to restore pre-RFC behavior

**Monitoring for Rollback Triggers:**
- User reports of broken navigation
- Significant bounce rate increase
- Accessibility audit failures
- Performance regression (>10% TTI increase)

---

## Success Criteria

### Performance Baselines (Capture Before Implementation)

**Current Bengal Default Theme Metrics** (to be measured):

| Metric | Current Baseline | Target | Method |
|--------|-----------------|--------|--------|
| Total JS Size | ~25-40 KB | < 15 KB | `wc -c public/**/*.js` |
| Time to Interactive | TBD ms | < 1500 ms | Lighthouse |
| Total Blocking Time | TBD ms | < 200 ms | Lighthouse |
| First Contentful Paint | TBD ms | < 1000 ms | Lighthouse |
| Navigation (click→render) | ~150-400 ms | < 100 ms | Manual timing |

**Baseline Capture Command:**
```bash
# Run before starting implementation
bengal build --site site/
cd public && python -m http.server 8000 &
lighthouse http://localhost:8000 --output=json --output-path=metrics/baseline-$(date +%Y%m%d).json
```

### Quantitative

- [ ] Zero framework JavaScript in default output
- [ ] < 15 KB total JavaScript (enhancement layer only) — measured via `wc -c`
- [ ] View transitions enabled on all page navigations
- [ ] Speculation rules generated for 80%+ internal links
- [ ] All interactive patterns work without JavaScript
- [ ] JS reduction: ≥ 40% smaller than baseline

### Qualitative

- [ ] Navigation feels instant (< 100ms perceived)
- [ ] No flash of unstyled content
- [ ] Back button works correctly for all state
- [ ] URLs are shareable with state preserved
- [ ] Screen readers announce transitions appropriately

### Lighthouse Metrics

| Metric | Target | Baseline | Delta |
|--------|--------|----------|-------|
| Performance | 95+ | TBD | Must improve |
| Accessibility | 100 | TBD | Must not regress |
| Best Practices | 100 | TBD | Must not regress |
| SEO | 100 | TBD | Must not regress |

### Validation Gates

Each phase must pass before proceeding:

| Phase | Gate Criteria |
|-------|--------------|
| 1: View Transitions | Lighthouse Performance ≥ baseline |
| 2: Speculation Rules | No broken links in prefetch rules |
| 3: Theme Controls | Manual QA pass, no accessibility regressions |
| 4: Mobile Nav | Focus trap works, screen reader tested |
| 5: CSS Tabs | URL fragments work, back button tested |
| 6: Intelligence | Build time < 2x baseline for large sites |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Browser API changes | Low | Medium | Feature detection, progressive enhancement |
| Safari View Transitions lag | Medium | Low | Graceful degradation, works without |
| Developer unfamiliarity | Medium | Medium | Documentation, examples, migration guides |
| CSS complexity | Low | Low | Generate CSS, developers don't write it |
| Legacy browser users | Low | Low | Define support matrix, basic fallback |
| Theme author resistance | Medium | Medium | Gradual migration, keep both modes |

---

## Open Questions

1. **Should CSS state machines be opt-in or default?**
   - Opt-in: Safer, less surprising
   - Default: Cleaner output, forces the paradigm

   **Recommendation: Opt-in first.** Existing sites should not break on upgrade. After one minor version cycle with opt-in, consider making it the default for new sites only.

   ```yaml
   # v0.2.x: Opt-in
   document_application:
     interactivity:
       tabs: css_state_machine  # Explicit opt-in

   # v0.3.x: Default for new sites, opt-out for existing
   document_application:
     interactivity:
       tabs: css_state_machine  # Default
       # tabs: enhanced  # Opt-out to JS version
   ```

2. **How aggressive should speculation rules be?**
   - Conservative: Minimal bandwidth, slower perceived nav
   - Aggressive: Faster nav, higher bandwidth cost

   **Recommendation: Conservative default with configuration.** Users on metered connections (mobile) should not pay bandwidth costs by default. Power users can increase aggressiveness.

   ```yaml
   speculation:
     prerender:
       eagerness: conservative  # Default: only on hover/focus
       # eagerness: moderate    # On viewport visibility
       # eagerness: eager       # Immediate on page load
   ```

3. **Should we ship a polyfill for `<dialog>` on older browsers?**
   - Yes: Better compatibility
   - No: Smaller bundle, clearer support matrix

   **Recommendation: No polyfill.** `<dialog>` has 97%+ support. The 3% on older browsers get functional but unstyled modals. Cost of polyfill (~5KB) outweighs benefit.

4. **How do we handle JavaScript-required features (clipboard, etc.)?**
   - Inline script: Simple, no module system
   - Enhancement layer: Consistent with current approach

   **Recommendation: Enhancement layer.** Consistency with existing `data-bengal="..."` pattern. Keeps JS organized and allows tree-shaking of unused enhancements.

   ```html
   <!-- Keep existing pattern -->
   <button data-bengal="copy" data-target="#code-block">Copy</button>
   ```

5. **How do we message this to theme authors?**
   - Framing as empowerment vs. requirement
   - Migration guide priority

   **Recommendation: Empowerment framing with clear migration path.**

   - Blog post: "Your CSS Skills Are Now Superpowers"
   - Migration guide: Step-by-step for each component
   - Compatibility mode: Keep both CSS files for transition period
   - Theme author office hours: Live Q&A during transition

---

## Appendix A: The Philosophical Foundation

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

## Appendix B: View Transitions Enable New Beauty

Things you **can't** easily do today, but could with view transitions:

```css
/* Hero image morphs between list and detail */
.post-card img { view-transition-name: hero; }
.post-detail img { view-transition-name: hero; }

/* Result: Image smoothly animates position/size between pages */

/* Code blocks cross-fade nicely */
pre { view-transition-name: code-block; }

/* Navigation stays stable while content transitions */
.sidebar { view-transition-name: sidebar; }
::view-transition-old(sidebar) { animation: none; }
```

This is **impossible** with current multi-page architecture without client-side routing.

---

## References

- [View Transitions API](https://developer.chrome.com/docs/web-platform/view-transitions/)
- [Speculation Rules API](https://developer.chrome.com/docs/web-platform/prerender-pages/)
- [CSS :has() selector](https://developer.mozilla.org/en-US/docs/Web/CSS/:has)
- [Dialog element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog)
- [Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API)
- [CSS @starting-style](https://developer.mozilla.org/en-US/docs/Web/CSS/@starting-style)
- [HTMX Essays](https://htmx.org/essays/)
- [The Rule of Least Power](https://www.w3.org/2001/tag/doc/leastPower.html)

---

## Implementation Timeline Summary

| Phase | Scope | Estimate | Cumulative |
|-------|-------|----------|------------|
| 1 | View Transitions | 1-2 days | 1-2 days |
| 2 | Speculation Rules | 1-2 days | 2-4 days |
| 3 | Theme Controls (Popover) | 1-2 days | 3-6 days |
| 4 | Mobile Nav (Dialog) | 2-3 days | 5-9 days |
| 5 | CSS State Machine Tabs | 4-5 days | 9-14 days |
| 6 | Author-Time Intelligence | 3-5 days | 12-19 days |

**Total Estimated Duration**: 12-19 working days (3-4 weeks)

**Recommended Approach**: Ship Phases 1-2 together as they are low-risk additive features. Phases 3-5 can be released incrementally with feature flags.

---

## Changelog

- **2025-12-22**: Initial draft
- **2025-12-22**: Added current theme assessment, concrete before/after examples, end user impact analysis, theme developer impact, styling limitations assessment, visual comparison
- **2025-12-22**: Added Browser Support Matrix, Testing Plan, Performance Metrics baselines, Rollback Strategy, CSS Generation Strategy for tabs, adjusted Phase 5 timeline, added recommendations to Open Questions
