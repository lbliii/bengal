/**
 * Bengal Enhancement: Tabs
 *
 * Provides accessible tab navigation with event delegation.
 * Registers with Bengal.enhance for data-bengal="tabs" elements.
 *
 * Usage:
 *   <div data-bengal="tabs">
 *     <ul class="tab-nav">
 *       <li><a data-tab-target="tab-1">Tab 1</a></li>
 *       <li><a data-tab-target="tab-2">Tab 2</a></li>
 *     </ul>
 *     <div id="tab-1" class="tab-pane active">Content 1</div>
 *     <div id="tab-2" class="tab-pane">Content 2</div>
 *   </div>
 *
 * Options:
 *   - defaultTab: ID of tab to activate by default
 *
 * @requires bengal-enhance.js
 */

(function() {
  'use strict';

  // Ensure enhancement system is available
  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded - tabs enhancement cannot register');
    return;
  }

  const CLASS_ACTIVE = 'active';
  const SELECTOR_NAV_LINK = '[data-tab-target]';
  const SELECTOR_NAV_ITEM = '.tab-nav li';
  const SELECTOR_PANE = '.tab-pane';

  // Register the enhancement
  Bengal.enhance.register('tabs', function(container, options) {
    const navLinks = container.querySelectorAll(SELECTOR_NAV_LINK);
    const panes = Array.from(container.querySelectorAll(SELECTOR_PANE)).filter(pane =>
      pane.closest('[data-bengal="tabs"]') === container
    );

    if (!navLinks.length || !panes.length) {
      return; // Nothing to enhance
    }

    /**
     * Switch to a specific tab
     * @param {string} targetId - ID of the target pane
     */
    function switchTab(targetId) {
      // Get nav items scoped to this container
      const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
        item.closest('[data-bengal="tabs"]') === container
      );

      // Deactivate all nav items
      navItems.forEach(item => item.classList.remove(CLASS_ACTIVE));

      // Deactivate all panes
      panes.forEach(pane => pane.classList.remove(CLASS_ACTIVE));

      // Activate target
      const activeLink = container.querySelector(`[data-tab-target="${targetId}"]`);
      if (activeLink) {
        const activeItem = activeLink.closest('li');
        if (activeItem) {
          activeItem.classList.add(CLASS_ACTIVE);
        }
      }

      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add(CLASS_ACTIVE);

        // Dispatch event for external listeners
        container.dispatchEvent(new CustomEvent('tabSwitched', {
          detail: { container, link: activeLink, pane: targetPane, targetId }
        }));
      }
    }

    // Event delegation for tab clicks
    container.addEventListener('click', (e) => {
      const link = e.target.closest(SELECTOR_NAV_LINK);
      if (!link) return;

      // Make sure click is within our container
      if (link.closest('[data-bengal="tabs"]') !== container) return;

      e.preventDefault();
      const targetId = link.dataset.tabTarget;
      if (targetId) {
        switchTab(targetId);
      }
    });

    // Keyboard navigation
    container.addEventListener('keydown', (e) => {
      const link = e.target.closest(SELECTOR_NAV_LINK);
      if (!link || link.closest('[data-bengal="tabs"]') !== container) return;

      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const targetId = link.dataset.tabTarget;
        if (targetId) {
          switchTab(targetId);
        }
      }
    });

    // Initialize: activate first tab if none active
    const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
      item.closest('[data-bengal="tabs"]') === container
    );

    if (navItems.length > 0 && !navItems.some(item => item.classList.contains(CLASS_ACTIVE))) {
      // Use default tab if specified, otherwise first tab
      if (options.defaultTab) {
        switchTab(options.defaultTab);
      } else {
        const firstLink = navItems[0].querySelector('[data-tab-target]');
        if (firstLink) {
          const targetId = firstLink.dataset.tabTarget;
          if (targetId) {
            switchTab(targetId);
          }
        }
      }
    }

    // Expose API on element
    container._bengalTabs = {
      switchTab
    };
  });

})();

