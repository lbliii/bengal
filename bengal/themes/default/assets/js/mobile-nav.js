/**
 * Bengal SSG Default Theme
 * Mobile Navigation
 */

(function() {
  'use strict';

  let mobileNav = null;
  let toggleBtn = null;
  let closeBtn = null;
  let isOpen = false;

  /**
   * Open mobile navigation
   */
  function openNav() {
    if (mobileNav) {
      mobileNav.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      isOpen = true;

      // Set focus to close button
      if (closeBtn) {
        closeBtn.focus();
      }

      // Update ARIA
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'true');
      }
    }
  }

  /**
   * Close mobile navigation
   */
  function closeNav() {
    if (mobileNav) {
      mobileNav.classList.remove('is-open');
      document.body.style.overflow = '';
      isOpen = false;

      // Return focus to toggle button
      if (toggleBtn) {
        toggleBtn.focus();
        toggleBtn.setAttribute('aria-expanded', 'false');
      }
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
    toggleBtn = document.querySelector('.mobile-nav-toggle');
    closeBtn = document.querySelector('.mobile-nav-close');

    if (!mobileNav || !toggleBtn) {
      return;
    }

    // Toggle button
    toggleBtn.addEventListener('click', toggleNav);

    // Close button
    if (closeBtn) {
      closeBtn.addEventListener('click', closeNav);
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
})();
