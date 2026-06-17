# Bengal Enhancement Modules

This directory contains progressive enhancement modules for the Bengal theme.
Declarative, element-scoped enhancements are **autonomous custom elements**
(`<bengal-*>`) built on `core/define.js`; they layer JavaScript on top of
already-working HTML.

## Philosophy

"Layered enhancement — HTML that works, CSS that delights, JS that elevates"

All enhancements follow progressive-enhancement principles:
- HTML is functional without JavaScript.
- Enhancements add interactivity when JS is available.
- Graceful degradation on errors (a failed `init()` never throws; the element
  just stays un-enhanced).

## The model: one custom element per enhancement

There is no central registry and no `data-bengal` attribute. An enhancement is a
custom element whose `connectedCallback` initializes it the moment it enters the
DOM — including content inserted after load — and whose `disconnectedCallback`
tears down any window/document listeners it added. The template wraps the
server-rendered markup in the element:

```html
<bengal-toc>
  <div class="toc-sidebar"> ... server-rendered TOC ... </div>
</bengal-toc>
```

```javascript
// enhancements/my-feature.js
(function () {
  'use strict';

  function initFeature(root) {
    // root is the <bengal-my-feature> element; scope queries to it.
    root.querySelectorAll('[data-thing]').forEach(/* ... */);
  }

  function teardownFeature(root) {
    // Remove any window/document listeners added in initFeature.
  }

  if (window.Bengal && window.Bengal.define) {
    window.Bengal.define('bengal-my-feature', class extends window.Bengal.Base {
      init() { initFeature(this); }
      teardown() { teardownFeature(this); }
    });
  }
})();
```

`window.Bengal.Base` (from `core/define.js`) guards `connectedCallback` against
re-entrancy, swallows init errors (degrade gracefully), and exposes `opt(name,
fallback)` and `scopedId(suffix)` helpers. `window.Bengal.define(tag, ctor)` is
an idempotent `customElements.define` wrapper that no-ops on engines without
custom elements.

Add the module's `<script defer>` to `base.html`'s site-scripts block (after
`core/define.js`) and the bundle order in `bengal/assets/js_bundler.py`.

## Custom elements in this theme

| Element | Module | Wraps |
|---------|--------|-------|
| `<bengal-toc>` | `toc.js` | the `.toc-sidebar` (scroll-spy + collapsible groups) |
| `<bengal-docs-nav>` | `interactive.js` | the docs `<nav>` (scroll-spy + active trail) |
| `<bengal-track-nav>` | `tracks.js` | the learning-track sidebar `<nav>` |
| `<bengal-api-catalog>` | `api-catalog.js` | the REST catalog/explorer shell |

Document-global behavior (smooth scroll, code-copy, external-link decoration,
keyboard detection) is **not** an element — it lives in eager bootstrap modules
(`main.js`, `core/theme.js`, `copy-link.js`, …). Content-decorator modules that
scan parser-emitted nodes (`tabs.js`, `lightbox.js`, `holo.js`) also self-init
eagerly. Heavy third-party assets (Mermaid / KaTeX / Tabulator) load lazily via
the separate `BENGAL_LAZY_ASSETS` / `lazy-loaders.js` IntersectionObserver path.

## Determinism

Any element id generated at runtime must be deterministic (derive it from a
sibling ordinal or a content hash via `Base.scopedId()`) — never `Math.random`
or a clock, so build output stays byte-stable.

## See Also

- [core/define.js](../core/define.js) — the custom-element foundation
- [../README.md](../README.md) — the theme JavaScript overview
