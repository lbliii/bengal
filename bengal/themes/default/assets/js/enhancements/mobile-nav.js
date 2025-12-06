/**
 * Bengal Enhancement: Mobile Navigation
 *
 * Provides mobile navigation menu functionality:
 * - Slide-out menu with backdrop
 * - Focus trap for accessibility
 * - Keyboard navigation support
 * - Submenu handling
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

  // ============================================================
  // State
  // ============================================================

  let mobileNav = null;
  let backdrop = null;
  let toggleBtn = null;
  let closeBtn = null;
  let isOpen = false;
  let prevFocused = null;
  const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

  function setBackgroundInert(inert) {
    const regions = document.querySelectorAll('header[role="banner"], main[role="main"], footer[role="contentinfo"]');
    const inertSupported = 'inert' in HTMLElement.prototype;
    regions.forEach(function(el) {
      if (!el) return;
      if (inert) {
        if (inertSupported) {
          try { el.inert = true; } catch (e) { /* no-op if unsupported */ }
        } else {
          el.setAttribute('aria-hidden', 'true');
        }
      } else {
        if (inertSupported) {
          try { el.inert = false; } catch (e) { /* no-op if unsupported */ }
        } else {
          el.removeAttribute('aria-hidden');
        }
      }
    });
  }

  function trapFocus(e) {
    if (!isOpen || e.key !== 'Tab' || !mobileNav) return;
    const focusables = mobileNav.querySelectorAll(FOCUSABLE);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement;
    if (e.shiftKey) {
      if (active === first || !mobileNav.contains(active)) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (active === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  /**
   * Open mobile navigation
   */
  function openNav() {
    if (mobileNav) {
      prevFocused = document.activeElement;
      mobileNav.classList.add('is-open');
      if (backdrop) {
        backdrop.classList.add('is-open');
      }
      document.body.style.overflow = 'hidden';
      isOpen = true;

      setBackgroundInert(true);

      // Set focus to close button
      if (closeBtn) {
        closeBtn.focus();
      }

      // Update ARIA
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'true');
      }

      document.addEventListener('keydown', trapFocus);
    }
  }

  /**
   * Close mobile navigation
   */
  function closeNav() {
    if (mobileNav) {
      mobileNav.classList.remove('is-open');
      if (backdrop) {
        backdrop.classList.remove('is-open');
      }
      document.body.style.overflow = '';
      isOpen = false;

      setBackgroundInert(false);

      // Return focus to toggle button
      if (toggleBtn) {
        toggleBtn.focus();
        toggleBtn.setAttribute('aria-expanded', 'false');
      }

      // Restore previously focused element when applicable
      if (prevFocused && typeof prevFocused.focus === 'function') {
        try { prevFocused.focus(); } catch (e) { /* ignore */ }
      }
      prevFocused = null;

      document.removeEventListener('keydown', trapFocus);
    }
  }

  /**
   * Toggle mobile navigation
   */
  function toggleNav() {
    if (isOpen) {
      closeNav();
    } else {
      openNav();
    }
  }

  /**
   * Handle escape key
   */
  function handleEscape(e) {
    if (e.key === 'Escape' && isOpen) {
      closeNav();
    }
  }

  /**
   * Handle outside click
   */
  function handleOutsideClick(e) {
    if (isOpen && mobileNav && !mobileNav.contains(e.target) && !toggleBtn.contains(e.target)) {
      closeNav();
    }
  }

  /**
   * Initialize mobile navigation
   */
  function init() {
    mobileNav = document.querySelector('.mobile-nav');
    backdrop = document.querySelector('.mobile-nav-backdrop');
    toggleBtn = document.querySelector('.mobile-nav-toggle');
    closeBtn = document.querySelector('.mobile-nav-close');

    if (!mobileNav || !toggleBtn) {
      log('[BengalNav] Mobile nav elements not found');
      return;
    }

    log('[BengalNav] Initialized');

    // Toggle button
    toggleBtn.addEventListener('click', toggleNav);

    // Close button
    if (closeBtn) {
      closeBtn.addEventListener('click', closeNav);
    }

    // Backdrop click to close
    if (backdrop) {
      backdrop.addEventListener('click', closeNav);
    }

    // Search button - close nav and open search modal
    const searchBtn = mobileNav.querySelector('.mobile-nav-search');
    if (searchBtn) {
      searchBtn.addEventListener('click', function() {
        closeNav();
        // Small delay to let nav close animation start, then open search
        setTimeout(function() {
          if (window.BengalSearchModal && typeof window.BengalSearchModal.open === 'function') {
            window.BengalSearchModal.open();
          }
        }, 100);
      });
    }

    // Handle submenu toggles
    const submenuParents = mobileNav.querySelectorAll('.has-submenu > a');
    submenuParents.forEach(function(link) {
      link.addEventListener('click', function(e) {
        const parent = link.parentElement;
        const isSubmenuOpen = parent.classList.contains('submenu-open');

        // Close all other submenus
        mobileNav.querySelectorAll('.submenu-open').forEach(function(item) {
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

    // Close on regular link click (for single-page apps or anchor links)
    const navLinks = mobileNav.querySelectorAll('a:not(.has-submenu > a)');
    navLinks.forEach(function(link) {
      link.addEventListener('click', function() {
        // Small delay to allow navigation
        setTimeout(closeNav, 150);
      });
    });

    // Keyboard support
    document.addEventListener('keydown', handleEscape);

    // Close on outside click
    document.addEventListener('click', handleOutsideClick);

    // Close on window resize to desktop
    window.addEventListener('resize', function() {
      if (window.innerWidth >= 768 && isOpen) {
        closeNav();
      }
    });
  }

  // Initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export for use in other scripts
  window.BengalNav = {
    open: openNav,
    close: closeNav,
    toggle: toggleNav
  };

  // Register with progressive enhancement system if available
  // This allows data-bengal="mobile-nav" elements to work with
  // the new enhancement loader while maintaining backward compatibility
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('mobile-nav', function(el, options) {
      // The existing init() already handles all mobile-nav elements,
      // but this registers the enhancement for consistency and allows
      // the enhancement system to track enhanced elements.
      el._bengalNav = {
        open: openNav,
        close: closeNav,
        toggle: toggleNav
      };
    }, { override: true });
  }
})();
