/**
 * REST API catalog navigation interactions (issue #287).
 *
 * One cohesive, lazy-loaded enhancement for the OpenAPI catalog/app shells:
 *   - Client-side FILTER of endpoint cards and schema tiles (no npm, no reload).
 *   - SCROLL-SPY that marks the active section in a left rail as you scroll and
 *     on direct hash navigation.
 *
 * Progressive enhancement: every rail link is a real `href="#id"` and every
 * filter input is a plain `<input type=search>`, so pages work with JS off —
 * this script only layers behavior on top. Copy affordances are handled
 * separately by the global `[data-copy]` delegation in tabs.js; this module
 * adds no copy logic.
 *
 * Activated by `data-bengal="api-catalog"` on a shell that contains:
 *   - `[data-api-filter-input]`  the filter search box (optional)
 *   - `[data-api-filter-item]`   each filterable card/tile
 *   - `[data-api-filter-group]`  a wrapper hidden when all its items are hidden
 *   - `[data-api-filter-empty]`  a no-results node (aria-live)
 *   - `[data-api-rail]`          a nav whose `a[href^="#"]` links drive scroll-spy
 *
 * @see bengal-enhance.js (loader), enhancements/toc.js (scroll-spy pattern)
 */

(function () {
  'use strict';

  // Reuse shared helpers when present; fall back to tiny local versions so the
  // module still works if utils.js has not loaded yet.
  const utils = window.BengalUtils || {};
  const debounce =
    utils.debounce ||
    function (fn, wait) {
      let t;
      return function () {
        const args = arguments;
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), wait);
      };
    };
  const throttleScroll =
    utils.throttleScroll ||
    function (fn) {
      let ticking = false;
      return function () {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
          fn();
          ticking = false;
        });
      };
    };
  const ready =
    utils.ready ||
    function (fn) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
      } else {
        fn();
      }
    };

  const VIEWPORT_OFFSET = 120; // px from top to consider a section "active"
  const ACTIVE_CLASS = 'api-rail__link--active';

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  // ==========================================================================
  // Accessible copy feedback
  // ==========================================================================
  // tabs.js performs the actual clipboard copy for `[data-copy]` and code-sample
  // buttons (and adds the visual `.copied` state). Copy feedback was visual-only,
  // so here we add a screen-reader announcement. Scoped to OpenAPI pages because
  // this module only loads there; the listener is attached once at module load.

  let liveRegion = null;

  function announce(message) {
    if (!liveRegion) {
      liveRegion = document.createElement('div');
      liveRegion.setAttribute('role', 'status');
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.style.cssText =
        'position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0;';
      document.body.appendChild(liveRegion);
    }
    liveRegion.textContent = '';
    // Re-set on the next frame so identical consecutive copies still announce.
    window.requestAnimationFrame(() => {
      liveRegion.textContent = message;
    });
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy], .api-code-samples__copy, .copy-btn');
    if (btn) announce('Copied to clipboard');
  });

  // ==========================================================================
  // Filtering
  // ==========================================================================

  /**
   * Build the lowercased haystack for a filterable item from its text plus any
   * structured data-* attributes (method/path/schema name/type/tags).
   */
  function itemHaystack(item) {
    const attrs = [
      'data-method',
      'data-path',
      'data-schema-name',
      'data-schema-type',
      'data-tags',
    ]
      .map((a) => item.getAttribute(a) || '')
      .join(' ');
    return `${item.textContent} ${attrs}`.toLowerCase().replace(/\s+/g, ' ').trim();
  }

  /**
   * Wire the search input to show/hide items, collapse empty groups, and
   * announce a no-results state. Returns a function that reveals a given
   * element (used to keep deep links working while a filter is active).
   */
  function initFilter(root) {
    const input = root.querySelector('[data-api-filter-input]');
    const items = Array.from(root.querySelectorAll('[data-api-filter-item]'));
    if (!input || !items.length) return null;

    const groups = Array.from(root.querySelectorAll('[data-api-filter-group]'));
    const emptyNode = root.querySelector('[data-api-filter-empty]');
    const haystacks = items.map(itemHaystack);

    function apply() {
      const query = input.value.trim().toLowerCase();
      let visible = 0;
      items.forEach((item, i) => {
        const match = query === '' || haystacks[i].includes(query);
        item.hidden = !match;
        if (match) visible += 1;
      });
      // Collapse any group whose items are now all hidden.
      groups.forEach((group) => {
        const groupItems = group.querySelectorAll('[data-api-filter-item]');
        if (!groupItems.length) return;
        const anyVisible = Array.from(groupItems).some((it) => !it.hidden);
        group.hidden = !anyVisible;
      });
      if (emptyNode) emptyNode.hidden = visible !== 0 || query === '';
    }

    input.addEventListener('input', debounce(apply, 120));

    // Reveal an element that a deep link targets even if it is currently
    // filtered out, so #fragment routing never breaks (clear the filter).
    function reveal(el) {
      if (!el) return;
      const hidden = el.hidden || el.closest('[hidden]');
      if (hidden && input.value) {
        input.value = '';
        apply();
      }
    }
    return reveal;
  }

  // ==========================================================================
  // Scroll-spy
  // ==========================================================================

  function initScrollSpy(root) {
    const rails = Array.from(root.querySelectorAll('[data-api-rail]'));
    if (!rails.length) return null;

    const entries = [];
    rails.forEach((rail) => {
      rail.querySelectorAll('a[href^="#"]').forEach((link) => {
        const id = decodeURIComponent(link.getAttribute('href').slice(1));
        const target = id ? document.getElementById(id) : null;
        if (target) entries.push({ link, target, rail });
      });
    });
    if (!entries.length) return null;

    let activeIndex = -1;

    function update() {
      // PHASE 1: batch reads (avoids layout thrash, mirrors toc.js).
      const tops = entries.map((e) => e.target.getBoundingClientRect().top);
      let index = 0;
      for (let i = tops.length - 1; i >= 0; i--) {
        if (tops[i] <= VIEWPORT_OFFSET) {
          index = i;
          break;
        }
      }
      if (index === activeIndex) return;
      activeIndex = index;

      // PHASE 2: batch writes.
      entries.forEach((e, i) => {
        if (i === index) {
          e.link.classList.add(ACTIVE_CLASS);
          e.link.setAttribute('aria-current', 'location');
        } else {
          e.link.classList.remove(ACTIVE_CLASS);
          e.link.removeAttribute('aria-current');
        }
      });

      // Keep the active rail link visible within its own scroll container.
      const active = entries[index];
      const railRect = active.rail.getBoundingClientRect();
      const linkRect = active.link.getBoundingClientRect();
      if (linkRect.top < railRect.top || linkRect.bottom > railRect.bottom) {
        active.link.scrollIntoView({
          behavior: prefersReducedMotion() ? 'auto' : 'smooth',
          block: 'nearest',
        });
      }
    }

    const onScroll = throttleScroll(update);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', debounce(update, 250), { passive: true });
    window.addEventListener('hashchange', update);
    update();
    return update;
  }

  // ==========================================================================
  // Init / registration
  // ==========================================================================

  function init(root) {
    if (!root || root.getAttribute('data-api-catalog-ready') === 'true') return;
    root.setAttribute('data-api-catalog-ready', 'true');

    const reveal = initFilter(root);
    initScrollSpy(root);

    // A deep link to a filtered-out section must still resolve: on hash nav,
    // clear the filter so the target is visible, then scroll to it.
    if (reveal) {
      const onHash = () => {
        const id = decodeURIComponent(location.hash.slice(1));
        const target = id ? document.getElementById(id) : null;
        if (target) {
          reveal(target);
          target.scrollIntoView({
            behavior: prefersReducedMotion() ? 'auto' : 'smooth',
            block: 'start',
          });
        }
      };
      window.addEventListener('hashchange', onHash);
      // Resolve an initial deep link that points at a (potentially) hidden item.
      if (location.hash) onHash();
    }
  }

  function autoInit() {
    document
      .querySelectorAll('[data-bengal="api-catalog"]')
      .forEach((root) => init(root));
  }

  // Register with the progressive-enhancement loader (primary path).
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('api-catalog', function (el) {
      init(el);
    });
  }

  // Backward-compatible auto-init (idempotent via data-api-catalog-ready).
  ready(autoInit);
  window.addEventListener('contentLoaded', autoInit);
})();
