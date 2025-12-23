/**
 * Bengal Enhancement: Mobile Navigation
 *
 * Pattern: DIALOG (see COMPONENT-PATTERNS.md)
 * - Element: <dialog id="mobile-nav-dialog">
 * - Browser handles: Focus trap, escape key, backdrop, inert background
 * - JS handles: Close on link click, submenu toggles, search button
 *
 * @requires utils.js (optional, for logging)
 */

(function() {
  'use strict';

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  /**
   * Initialize dialog-based mobile navigation
   */
  function init() {
    const dialog = document.getElementById('mobile-nav-dialog');
    if (!dialog) {
      log('[BengalNav] Mobile nav dialog not found');
      return;
    }

    log('[BengalNav] Initialized dialog-based mobile navigation');

    // Close on navigation link click (for same-page navigation)
    const navLinks = dialog.querySelectorAll('.mobile-nav-content a');
    navLinks.forEach(function(link) {
      link.addEventListener('click', function() {
        // Small delay to allow navigation to start
        setTimeout(function() {
          dialog.close();
        }, 150);
      });
    });

    // Handle submenu toggles
    const submenuParents = dialog.querySelectorAll('.has-submenu > a');
    submenuParents.forEach(function(link) {
      link.addEventListener('click', function(e) {
        const parent = link.parentElement;
        const isSubmenuOpen = parent.classList.contains('submenu-open');

        // Close all other submenus
        dialog.querySelectorAll('.submenu-open').forEach(function(item) {
          if (item !== parent) {
            item.classList.remove('submenu-open');
          }
        });

        // Toggle this submenu
        parent.classList.toggle('submenu-open');

        // If submenu is being opened, prevent navigation
        if (!isSubmenuOpen) {
          e.preventDefault();
        }
      });
    });

    // Search button - close dialog and open search modal
    const searchBtn = dialog.querySelector('.mobile-nav-search');
    if (searchBtn) {
      searchBtn.addEventListener('click', function() {
        dialog.close();
        // Small delay to let dialog close animation complete
        setTimeout(function() {
          if (window.BengalSearchModal && typeof window.BengalSearchModal.open === 'function') {
            window.BengalSearchModal.open();
          }
        }, 100);
      });
    }

    // Close on backdrop click (clicking the dialog element itself, not its contents)
    dialog.addEventListener('click', function(e) {
      if (e.target === dialog) {
        dialog.close();
      }
    });
  }

  // Initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export minimal API
  window.BengalNav = {
    open: function() {
      const dialog = document.getElementById('mobile-nav-dialog');
      if (dialog) dialog.showModal();
    },
    close: function() {
      const dialog = document.getElementById('mobile-nav-dialog');
      if (dialog) dialog.close();
    },
    toggle: function() {
      const dialog = document.getElementById('mobile-nav-dialog');
      if (dialog) {
        if (dialog.open) dialog.close();
        else dialog.showModal();
      }
    }
  };

  // Register with progressive enhancement system if available
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('mobile-nav', function(el, options) {
      el._bengalNav = window.BengalNav;
    }, { override: true });
  }
})();
