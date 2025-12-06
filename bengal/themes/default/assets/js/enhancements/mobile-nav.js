/**
 * Bengal Enhancement: Mobile Navigation
 *
 * Provides accessible mobile navigation with slide-out menu.
 * Registers with Bengal.enhance for data-bengal="mobile-nav" elements.
 *
 * Usage:
 *   <nav data-bengal="mobile-nav">
 *     <ul>...</ul>
 *   </nav>
 *
 * Requires corresponding toggle button:
 *   <button class="mobile-nav-toggle">Menu</button>
 *
 * Options:
 *   - closeOnClick: Close nav when a link is clicked (default: true)
 *   - closeOnEscape: Close nav on Escape key (default: true)
 *
 * @requires bengal-enhance.js
 */

(function() {
  'use strict';

  // Ensure enhancement system is available
  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded - mobile-nav enhancement cannot register');
    return;
  }

  const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

  /**
   * Set background elements as inert (for focus trapping)
   * @param {boolean} inert - Whether to make inert
   */
  function setBackgroundInert(inert) {
    const regions = document.querySelectorAll('header[role="banner"], main[role="main"], footer[role="contentinfo"]');
    const inertSupported = 'inert' in HTMLElement.prototype;

    regions.forEach(function(el) {
      if (!el) return;
      if (inert) {
        if (inertSupported) {
          try { el.inert = true; } catch (e) { /* no-op */ }
        } else {
          el.setAttribute('aria-hidden', 'true');
        }
      } else {
        if (inertSupported) {
          try { el.inert = false; } catch (e) { /* no-op */ }
        } else {
          el.removeAttribute('aria-hidden');
        }
      }
    });
  }

  // Register the enhancement
  Bengal.enhance.register('mobile-nav', function(nav, options) {
    const closeOnClick = options.closeOnClick !== false;
    const closeOnEscape = options.closeOnEscape !== false;

    // Find related elements
    const toggleBtn = document.querySelector('.mobile-nav-toggle');
    const closeBtn = nav.querySelector('.mobile-nav-close');

    if (!toggleBtn) {
      console.warn('[Bengal] mobile-nav: No toggle button found (.mobile-nav-toggle)');
      return;
    }

    let isOpen = false;
    let prevFocused = null;

    /**
     * Focus trap handler
     */
    function trapFocus(e) {
      if (!isOpen || e.key !== 'Tab') return;

      const focusables = nav.querySelectorAll(FOCUSABLE);
      if (!focusables.length) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (e.shiftKey) {
        if (active === first || !nav.contains(active)) {
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
     * Open the navigation
     */
    function open() {
      if (isOpen) return;

      prevFocused = document.activeElement;
      nav.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      isOpen = true;

      setBackgroundInert(true);

      // Focus close button
      if (closeBtn) {
        closeBtn.focus();
      }

      // Update ARIA
      toggleBtn.setAttribute('aria-expanded', 'true');
      document.addEventListener('keydown', trapFocus);
    }

    /**
     * Close the navigation
     */
    function close() {
      if (!isOpen) return;

      nav.classList.remove('is-open');
      document.body.style.overflow = '';
      isOpen = false;

      setBackgroundInert(false);

      // Return focus
      toggleBtn.setAttribute('aria-expanded', 'false');
      if (prevFocused && typeof prevFocused.focus === 'function') {
        try { prevFocused.focus(); } catch (e) { /* ignore */ }
      }
      prevFocused = null;

      document.removeEventListener('keydown', trapFocus);
    }

    /**
     * Toggle the navigation
     */
    function toggle() {
      if (isOpen) {
        close();
      } else {
        open();
      }
    }

    // Set up event listeners
    toggleBtn.addEventListener('click', toggle);

    if (closeBtn) {
      closeBtn.addEventListener('click', close);
    }

    // Handle submenu toggles
    const submenuParents = nav.querySelectorAll('.has-submenu > a');
    submenuParents.forEach(function(link) {
      link.addEventListener('click', function(e) {
        const parent = link.parentElement;
        const isSubmenuOpen = parent.classList.contains('submenu-open');

        // Close all other submenus
        nav.querySelectorAll('.submenu-open').forEach(function(item) {
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

    // Close on link click
    if (closeOnClick) {
      const navLinks = nav.querySelectorAll('a:not(.has-submenu > a)');
      navLinks.forEach(function(link) {
        link.addEventListener('click', function() {
          setTimeout(close, 150);
        });
      });
    }

    // Close on Escape
    if (closeOnEscape) {
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isOpen) {
          close();
        }
      });
    }

    // Close on outside click
    document.addEventListener('click', function(e) {
      if (isOpen && !nav.contains(e.target) && !toggleBtn.contains(e.target)) {
        close();
      }
    });

    // Close on resize to desktop
    window.addEventListener('resize', function() {
      if (window.innerWidth >= 768 && isOpen) {
        close();
      }
    });

    // Expose API on element for external control
    nav._bengalNav = {
      open,
      close,
      toggle
    };
  });

})();

