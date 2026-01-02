/**
 * Bengal Enhancement: Mobile Navigation
 *
 * Pattern: DIALOG (see COMPONENT-PATTERNS.md)
 * - Element: <dialog id="mobile-nav-dialog">
 * - Browser handles: Focus trap, escape key, backdrop, inert background
 * - JS handles: Close on link click, submenu toggles, search button
 *
 * Mobile UX Pattern:
 * - Split button: Section link navigates, chevron button expands/collapses
 * - Auto-expand: Active section expands when dialog opens
 * - Clear separation between navigation and expand actions
 *
 * @requires utils.js (optional, for logging)
 */

(function() {
  'use strict';

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  /**
   * Toggle submenu open/closed state
   * @param {HTMLElement} listItem - The li.has-submenu element
   * @param {boolean} [forceOpen] - Optional: force open (true) or closed (false)
   */
  function toggleSubmenu(listItem, forceOpen) {
    const isOpen = listItem.classList.contains('submenu-open');
    const shouldOpen = forceOpen !== undefined ? forceOpen : !isOpen;
    const toggleBtn = listItem.querySelector('.mobile-nav-toggle-submenu');

    if (shouldOpen) {
      listItem.classList.add('submenu-open');
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
    } else {
      listItem.classList.remove('submenu-open');
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
    }
  }

  /**
   * Auto-expand sections containing the active page
   * @param {HTMLElement} dialog - The mobile nav dialog
   */
  function autoExpandActiveSections(dialog) {
    // Find all active or active-trail items
    const activeItems = dialog.querySelectorAll('.mobile-nav-content li.active, .mobile-nav-content li.active-trail');

    activeItems.forEach(function(item) {
      // Walk up the tree and expand parent submenus
      let parent = item.parentElement;
      while (parent) {
        if (parent.classList && parent.classList.contains('has-submenu')) {
          toggleSubmenu(parent, true);
        }
        parent = parent.parentElement;
      }

      // If this item itself has a submenu and is active-trail, expand it
      if (item.classList.contains('has-submenu') && item.classList.contains('active-trail')) {
        toggleSubmenu(item, true);
      }
    });
  }

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
    // Only close for actual navigation links, not toggle triggers
    const navLinks = dialog.querySelectorAll('.mobile-nav-content a:not(.mobile-nav-toggle-submenu)');
    navLinks.forEach(function(link) {
      link.addEventListener('click', function() {
        // Small delay to allow navigation to start
        setTimeout(function() {
          dialog.close();
        }, 150);
      });
    });

    // Handle chevron toggle button clicks (split button pattern)
    const toggleButtons = dialog.querySelectorAll('.mobile-nav-toggle-submenu');
    toggleButtons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        const listItem = btn.closest('li.has-submenu');
        if (listItem) {
          toggleSubmenu(listItem);
        }
      });
    });

    // Handle nav-dropdown-trigger clicks (items with href='#')
    // These should toggle the submenu since there's no navigation
    const dropdownTriggers = dialog.querySelectorAll('.mobile-nav-content .nav-dropdown-trigger');
    dropdownTriggers.forEach(function(trigger) {
      trigger.addEventListener('click', function(e) {
        e.preventDefault();
        const listItem = trigger.closest('li.has-submenu');
        if (listItem) {
          toggleSubmenu(listItem);
        }
      });

      // Also handle keyboard activation
      trigger.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const listItem = trigger.closest('li.has-submenu');
          if (listItem) {
            toggleSubmenu(listItem);
          }
        }
      });
    });

    // Auto-expand active sections when dialog opens
    dialog.addEventListener('open', function() {
      autoExpandActiveSections(dialog);
    });

    // Also run on showModal since 'open' event may not fire in all browsers
    const originalShowModal = dialog.showModal.bind(dialog);
    dialog.showModal = function() {
      originalShowModal();
      autoExpandActiveSections(dialog);
    };

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
