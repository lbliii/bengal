/**
 * Bengal SSG - Documentation Navigation Scaffold Enhancement
 *
 * Applies active/trail state to statically-rendered nav scaffolds.
 * This enables cached nav HTML with per-page active state applied client-side.
 *
 * Phase 2 of docs-nav rendering optimization:
 * - Scaffold HTML is rendered once per scope (static, no active classes)
 * - This JS reads data attributes and applies active state
 * - Expands sections in the active trail
 *
 * Data Attributes (on nav element):
 * - data-current-path: URL of the current page (e.g., "/docs/getting-started/")
 * - data-active-trail: JSON array of URLs in the trail (current to root)
 *
 * Data Attributes (on nav items):
 * - data-nav-path: URL this item represents
 *
 * Classes Applied:
 * - .active: Current page link
 * - .is-in-trail: Items in path from current page to root
 * - .is-expanded (on group items): Sections in the trail
 * - aria-current="page": Semantic current page marker
 * - aria-expanded="true": Expanded sections
 */

(function() {
  'use strict';

  /**
   * Apply active state to a scaffold navigation element.
   *
   * @param {HTMLElement} nav - The nav element with data-bengal="docs-nav-scaffold"
   */
  function applyActiveState(nav) {
    // Parse data attributes
    const currentPath = nav.dataset.currentPath;
    let activeTrail = [];

    try {
      activeTrail = JSON.parse(nav.dataset.activeTrail || '[]');
    } catch (e) {
      console.error('[Bengal] Invalid active trail JSON:', e);
      return;
    }

    if (!currentPath) {
      return;
    }

    // Convert trail to Set for O(1) lookups
    const trailSet = new Set(activeTrail);

    // Find all elements with data-nav-path
    const navItems = nav.querySelectorAll('[data-nav-path]');

    navItems.forEach(item => {
      const itemPath = item.dataset.navPath;
      if (!itemPath) return;

      const isInTrail = trailSet.has(itemPath);
      const isCurrent = itemPath === currentPath;

      // Apply classes based on state
      if (isCurrent) {
        item.classList.add('active');
        item.setAttribute('aria-current', 'page');

        // If this is a link inside a group, mark the group
        const parentGroup = item.closest('.docs-nav-group');
        if (parentGroup) {
          parentGroup.classList.add('is-in-trail');
        }
      }

      if (isInTrail) {
        // Mark the item as in trail
        if (item.classList.contains('docs-nav-group')) {
          item.classList.add('is-in-trail');
        } else if (item.classList.contains('docs-nav-group-title') ||
                   item.classList.contains('docs-nav-group-link')) {
          // Mark parent group
          const parentGroup = item.closest('.docs-nav-group');
          if (parentGroup) {
            parentGroup.classList.add('is-in-trail');
          }
        }
      }
    });

    // Expand sections in the active trail
    expandActiveTrail(nav, trailSet);

    // Scroll active item into view (after expansion)
    scrollActiveIntoView(nav);
  }

  /**
   * Expand all sections that are in the active trail.
   *
   * @param {HTMLElement} nav - The nav element
   * @param {Set<string>} trailSet - Set of URLs in the active trail
   */
  function expandActiveTrail(nav, trailSet) {
    // Find all expandable groups in the trail
    const groups = nav.querySelectorAll('.docs-nav-group[data-nav-path]');

    groups.forEach(group => {
      const groupPath = group.dataset.navPath;
      if (!groupPath || !trailSet.has(groupPath)) return;

      // Find the toggle button
      const toggle = group.querySelector(':scope > .docs-nav-group-toggle-wrapper > .docs-nav-group-toggle');
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'true');
      }

      // Find the items container
      const items = group.querySelector(':scope > .docs-nav-group-items');
      if (items) {
        items.classList.add('is-expanded');
        items.classList.add('expanded');
      }
    });

    // Also expand root groups (depth 0) by default
    const rootGroups = nav.querySelectorAll('.docs-nav-group--root > .docs-nav-group-items');
    rootGroups.forEach(items => {
      items.classList.add('is-expanded');
      items.classList.add('expanded');
    });
  }

  /**
   * Scroll the active item into view within the nav container.
   *
   * @param {HTMLElement} nav - The nav element
   */
  function scrollActiveIntoView(nav) {
    // Small delay to allow CSS transitions
    requestAnimationFrame(() => {
      const activeItem = nav.querySelector('[aria-current="page"]');
      if (activeItem) {
        // Use scrollIntoView with block: 'nearest' to avoid jarring jumps
        activeItem.scrollIntoView({
          behavior: 'instant',
          block: 'nearest',
          inline: 'nearest'
        });
      }
    });
  }

  /**
   * Setup toggle handlers for expandable sections.
   *
   * @param {HTMLElement} nav - The nav element
   */
  function setupToggleHandlers(nav) {
    const toggles = nav.querySelectorAll('.docs-nav-group-toggle');

    toggles.forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        e.preventDefault();

        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', !isExpanded);

        const controlsId = toggle.getAttribute('aria-controls');
        if (controlsId) {
          const content = document.getElementById(controlsId);
          if (content) {
            content.classList.toggle('expanded', !isExpanded);
            content.classList.toggle('is-expanded', !isExpanded);
          }
        }
      });
    });
  }

  /**
   * Initialize scaffold navigation.
   */
  function init() {
    // Find all scaffold nav elements
    const scaffoldNavs = document.querySelectorAll('[data-bengal="docs-nav-scaffold"]');

    scaffoldNavs.forEach(nav => {
      applyActiveState(nav);
      setupToggleHandlers(nav);
    });

    if (scaffoldNavs.length > 0) {
      // Use BengalUtils.log if available
      if (window.BengalUtils && window.BengalUtils.log) {
        window.BengalUtils.log('Scaffold navigation initialized');
      }
    }
  }

  // Register with Bengal enhancement system
  if (window.Bengal && window.Bengal.enhance) {
    window.Bengal.enhance.register('docs-nav-scaffold', function(el, options) {
      applyActiveState(el);
      setupToggleHandlers(el);
    });
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export for manual initialization
  window.BengalDocsNavScaffold = {
    init: init,
    applyActiveState: applyActiveState
  };

})();
