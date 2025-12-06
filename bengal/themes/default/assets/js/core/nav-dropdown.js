/**
 * Navigation Dropdown Handler
 *
 * Handles dropdown menus in main navigation with keyboard navigation support.
 * Uses JavaScript for reliable state management, consistent with theme dropdown pattern.
 */

(function() {
  'use strict';

  /**
   * Initialize navigation dropdowns
   */
  function initNavDropdowns() {
    const navItems = document.querySelectorAll('.nav-main > li');

    if (!navItems.length) {
      return;
    }

    navItems.forEach(function(navItem) {
      const submenu = navItem.querySelector('.submenu');
      const navLink = navItem.querySelector('a');

      if (!submenu || !navLink) {
        return;
      }

      // Skip if already initialized to prevent duplicate event listeners
      if (navItem.dataset.dropdownInit) {
        return;
      }
      navItem.dataset.dropdownInit = 'true';

      // Mark nav item as having dropdown
      navItem.classList.add('has-dropdown');

      // Initialize state attributes (Supabase/Radix pattern)
      navItem.setAttribute('data-state', 'closed');
      navLink.setAttribute('data-state', 'closed');

      // Add ARIA attributes for accessibility
      navLink.setAttribute('aria-haspopup', 'true');
      navLink.setAttribute('aria-expanded', 'false');
      navLink.setAttribute('aria-controls', submenu.id || `submenu-${Math.random().toString(36).substr(2, 9)}`);

      if (!submenu.id) {
        submenu.id = navLink.getAttribute('aria-controls');
      }

      let isOpen = false;
      let hoverTimeout = null;

      /**
       * Open dropdown
       */
      function openDropdown() {
        if (isOpen) return;

        isOpen = true;
        navItem.setAttribute('data-state', 'open');
        navLink.setAttribute('data-state', 'open');
        navLink.setAttribute('aria-expanded', 'true');

        // Close other dropdowns
        document.querySelectorAll('.nav-main > li[data-state="open"]').forEach(function(item) {
          if (item !== navItem) {
            const otherSubmenu = item.querySelector('.submenu');
            const otherLink = item.querySelector('a');
            item.setAttribute('data-state', 'closed');
            if (otherLink) {
              otherLink.setAttribute('data-state', 'closed');
              otherLink.setAttribute('aria-expanded', 'false');
            }
          }
        });
      }

      /**
       * Close dropdown
       */
      function closeDropdown() {
        if (!isOpen) return;

        isOpen = false;
        navItem.setAttribute('data-state', 'closed');
        navLink.setAttribute('data-state', 'closed');
        navLink.setAttribute('aria-expanded', 'false');
      }

      /**
       * Toggle dropdown
       */
      function toggleDropdown() {
        if (isOpen) {
          closeDropdown();
        } else {
          openDropdown();
        }
      }

      // Mouse events
      navItem.addEventListener('mouseenter', function() {
        clearTimeout(hoverTimeout);
        openDropdown();
      });

      navItem.addEventListener('mouseleave', function() {
        hoverTimeout = setTimeout(function() {
          closeDropdown();
        }, 150); // Small delay to allow moving to dropdown
      });

      // Keep dropdown open when hovering over it
      submenu.addEventListener('mouseenter', function() {
        clearTimeout(hoverTimeout);
        openDropdown();
      });

      submenu.addEventListener('mouseleave', function() {
        hoverTimeout = setTimeout(function() {
          closeDropdown();
        }, 150);
      });

      // Click navigates to the link (Supabase pattern: hover opens, click navigates)
      // No preventDefault - allow normal link behavior
      // Dropdown is controlled by hover, not click

      // Keyboard navigation
      navLink.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleDropdown();
        } else if (e.key === 'ArrowDown') {
          e.preventDefault();
          openDropdown();
          // Focus first item in dropdown
          const firstLink = submenu.querySelector('a');
          if (firstLink) {
            firstLink.focus();
          }
        } else if (e.key === 'Escape') {
          closeDropdown();
          navLink.focus();
        }
      });

      // Keyboard navigation within dropdown
      const dropdownLinks = submenu.querySelectorAll('a');
      dropdownLinks.forEach(function(link, index) {
        link.addEventListener('keydown', function(e) {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextLink = dropdownLinks[index + 1] || dropdownLinks[0];
            if (nextLink) nextLink.focus();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prevLink = dropdownLinks[index - 1] || navLink;
            prevLink.focus();
          } else if (e.key === 'Escape') {
            closeDropdown();
            navLink.focus();
          } else if (e.key === 'Home') {
            e.preventDefault();
            dropdownLinks[0]?.focus();
          } else if (e.key === 'End') {
            e.preventDefault();
            dropdownLinks[dropdownLinks.length - 1]?.focus();
          }
        });
      });

      // Close on outside click
      document.addEventListener('click', function(e) {
        if (!navItem.contains(e.target)) {
          closeDropdown();
        }
      });

      // Close on window resize (mobile)
      window.addEventListener('resize', function() {
        if (window.innerWidth < 768) {
          closeDropdown();
        }
      });
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavDropdowns);
  } else {
    initNavDropdowns();
  }
})();
