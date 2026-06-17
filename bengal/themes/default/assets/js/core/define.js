/**
 * Bengal SSG - Custom-element foundation
 *
 * The single enhancement model for the default theme: declarative element
 * enhancements are autonomous custom elements (`<bengal-*>`). The platform's
 * `connectedCallback` auto-initializes each instance exactly when it enters the
 * DOM — including dynamically inserted content — which replaces the old
 * `data-bengal` registry + MutationObserver + deferred-init machinery entirely.
 *
 * Provides:
 *   window.Bengal.define(tag, ctor) — idempotent customElements.define wrapper
 *                                     (no-op on engines without custom elements)
 *   window.Bengal.Base             — HTMLElement base: guarded connectedCallback
 *                                     -> init(), disconnectedCallback -> teardown()
 *
 * Authoring contract (see assets/js/README.md):
 *   window.Bengal.define('bengal-thing', class extends window.Bengal.Base {
 *     init()     { ...element setup, scoped to `this`... }
 *     teardown() { ...remove any window/document listeners added in init()... }
 *   });
 *
 * Document-global behavior (smooth scroll, theme reconcile, code-copy, etc.)
 * is NOT modeled as an element — it lives in its own eager bootstrap module.
 * Heavy third-party assets (Mermaid/KaTeX/Tabulator) keep their separate
 * IntersectionObserver lazy-loader (BENGAL_LAZY_ASSETS / lazy-loaders.js).
 */

(function () {
  'use strict';

  class BengalBase extends HTMLElement {
    connectedCallback() {
      // Guard against re-entrant connects (e.g. the element being moved in the
      // DOM) without a matching disconnect.
      if (this._bengalConnected) return;
      this._bengalConnected = true;
      try {
        this.init();
      } catch (err) {
        // Never throw out of a lifecycle callback — degrade gracefully.
        var u = window.BengalUtils;
        if (u && u.log) u.log('[Bengal] custom-element init error', this.localName, err);
        this.dataset.bengalError = 'true';
      }
    }

    disconnectedCallback() {
      this._bengalConnected = false;
      try {
        if (this.teardown) this.teardown();
      } catch (err) {
        /* swallow teardown errors */
      }
    }

    // Subclasses override these.
    init() {}
    teardown() {}

    /** Read a data-* attribute with a fallback. */
    opt(name, fallback) {
      var v = this.dataset[name];
      return v == null ? fallback : v;
    }

    /**
     * Deterministic per-instance id: tag name + sibling ordinal + suffix.
     * Stable across loads (no random/clock-based seeds), collision-free for
     * repeated sibling instances.
     */
    scopedId(suffix) {
      var siblings = this.parentElement
        ? this.parentElement.querySelectorAll(this.localName)
        : [this];
      var i = Array.prototype.indexOf.call(siblings, this);
      return this.localName + '-' + (i < 0 ? 0 : i) + '-' + suffix;
    }
  }

  function define(tag, ctor) {
    if (!('customElements' in window)) return; // ancient engine: graceful no-op
    if (customElements.get(tag)) return; // idempotent across a bundled duplicate
    customElements.define(tag, ctor);
  }

  window.Bengal = window.Bengal || {};
  window.Bengal.define = define;
  window.Bengal.Base = BengalBase;
})();
