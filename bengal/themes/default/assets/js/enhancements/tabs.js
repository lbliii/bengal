/**
 * Bengal Enhancement: Tabs Component
 *
 * Provides tabbed content functionality:
 * - Event delegation (works with dynamic content)
 * - ID-based targeting (more robust than index-based)
 * - Handles nested tabs correctly
 * - Accessible keyboard navigation
 *
 * @requires utils.js (optional, for logging)
 * @requires bengal-enhance.js (for enhancement registration)
 */

(function() {
  'use strict';

  // ============================================================
  // Dependencies
  // ============================================================

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  // CSS classes
  const CLASS_ACTIVE = 'active';
  const SELECTOR_TABS = '.tabs, .code-tabs';
  const SELECTOR_NAV_LINK = '.tab-nav a';
  const SELECTOR_NAV_ITEM = '.tab-nav li';
  const SELECTOR_PANE = '.tab-pane';

  /**
   * Handle click events on tab links
   */
  document.addEventListener('click', (e) => {
    const link = e.target.closest(SELECTOR_NAV_LINK);
    if (!link) return;

    // Find the container
    const container = link.closest(SELECTOR_TABS);
    if (!container) return;

    // Prevent default anchor behavior
    e.preventDefault();

    // Get target ID
    const targetId = link.getAttribute('data-tab-target');
    if (!targetId) return;

    switchTab(container, link, targetId);
  });

  /**
   * Switch tab
   * @param {HTMLElement} container - The tabs container
   * @param {HTMLElement} activeLink - The clicked link
   * @param {string} targetId - ID of the target pane
   */
  function switchTab(container, activeLink, targetId) {
    // 1. Deactivate all nav items in THIS container
    const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
      item.closest(SELECTOR_TABS) === container
    );
    navItems.forEach(item => item.classList.remove(CLASS_ACTIVE));

    // 2. Activate clicked nav item
    const activeItem = activeLink.closest('li');
    if (activeItem) activeItem.classList.add(CLASS_ACTIVE);

    // 3. Hide all panes in THIS container
    const panes = Array.from(container.querySelectorAll(SELECTOR_PANE)).filter(pane =>
      pane.closest(SELECTOR_TABS) === container
    );
    panes.forEach(pane => pane.classList.remove(CLASS_ACTIVE));

    // 4. Show target pane
    // We search globally or within container?
    // IDs are global, but usually inside container.
    // Search within container is safer for nested contexts if IDs aren't unique (they should be).
    const targetPane = document.getElementById(targetId);
    if (targetPane) {
      targetPane.classList.add(CLASS_ACTIVE);

      // Dispatch event
      const event = new CustomEvent('tabSwitched', {
        detail: { container, link: activeLink, pane: targetPane }
      });
      container.dispatchEvent(event);
    }
  }

  /**
   * Initialize state (if needed)
   * Ensure at least one tab is active if HTML didn't set it
   */
  function initTabs() {
    const containers = document.querySelectorAll(SELECTOR_TABS);
    containers.forEach(container => {
      const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
        item.closest(SELECTOR_TABS) === container
      );
      const panes = Array.from(container.querySelectorAll(SELECTOR_PANE)).filter(pane =>
        pane.closest(SELECTOR_TABS) === container
      );

      // If no active item, activate first
      if (navItems.length > 0 && !navItems.some(item => item.classList.contains(CLASS_ACTIVE))) {
        navItems[0].classList.add(CLASS_ACTIVE);
        // Find corresponding link to get target
        const link = navItems[0].querySelector('a');
        if (link) {
          const targetId = link.getAttribute('data-tab-target');
          if (targetId) {
            const pane = document.getElementById(targetId);
            if (pane) pane.classList.add(CLASS_ACTIVE);
          }
        }
      }
    });
  }

  // ============================================================
  // Auto-initialize
  // ============================================================

  // Initialize on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initTabs();
      log('[BengalTabs] Initialized');
    });
  } else {
    initTabs();
    log('[BengalTabs] Initialized');
  }

  // Register with progressive enhancement system if available
  // This allows data-bengal="tabs" elements to work with
  // the new enhancement loader while maintaining backward compatibility
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('tabs', function(container, options) {
      // The existing event delegation handles all tabs globally,
      // but this registers the enhancement for consistency.
      // For data-bengal="tabs", we add explicit initialization.
      const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
        item.closest(SELECTOR_TABS) === container || item.closest('[data-bengal="tabs"]') === container
      );
      const panes = Array.from(container.querySelectorAll(SELECTOR_PANE)).filter(pane =>
        pane.closest(SELECTOR_TABS) === container || pane.closest('[data-bengal="tabs"]') === container
      );

      // Initialize first tab if none active
      if (navItems.length > 0 && !navItems.some(item => item.classList.contains(CLASS_ACTIVE))) {
        navItems[0].classList.add(CLASS_ACTIVE);
        const link = navItems[0].querySelector('a');
        if (link) {
          const targetId = link.getAttribute('data-tab-target');
          if (targetId) {
            const pane = document.getElementById(targetId);
            if (pane) pane.classList.add(CLASS_ACTIVE);
          }
        }
      }
    }, { override: true });
  }

})();
