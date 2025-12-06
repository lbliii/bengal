/**
 * Bengal Enhancement: Table of Contents
 *
 * Provides scroll spy, smooth scrolling, and collapsible sections for TOC.
 * Registers with Bengal.enhance for data-bengal="toc" elements.
 *
 * Usage:
 *   <nav data-bengal="toc" data-spy="true">
 *     <a data-toc-item="#section-1">Section 1</a>
 *     <a data-toc-item="#section-2">Section 2</a>
 *   </nav>
 *
 * Options:
 *   - spy: Enable scroll spy (default: true)
 *   - offset: Scroll offset in pixels (default: 120)
 *   - smooth: Enable smooth scrolling (default: true)
 *
 * @requires bengal-enhance.js
 * @requires utils.js (for throttleScroll)
 */

(function() {
  'use strict';

  // Ensure enhancement system is available
  if (!window.Bengal || !window.Bengal.enhance) {
    console.warn('[Bengal] Enhancement system not loaded - toc enhancement cannot register');
    return;
  }

  // Register the enhancement
  Bengal.enhance.register('toc', function(nav, options) {
    const spyEnabled = options.spy !== false;
    const scrollOffset = options.offset || 120;
    const smoothEnabled = options.smooth !== false;

    const items = nav.querySelectorAll('[data-toc-item]');
    if (!items.length) return;

    // Build heading map
    const headings = Array.from(items).map(link => {
      const id = link.dataset.tocItem.replace(/^#/, '');
      return {
        link,
        element: document.getElementById(id),
        id
      };
    }).filter(h => h.element);

    if (!headings.length) return;

    let currentActive = null;
    let scrollHandler = null;

    /**
     * Update active item based on scroll position
     */
    function updateActive() {
      const scrollTop = window.scrollY + scrollOffset;

      let active = headings[0];
      for (const heading of headings) {
        if (heading.element.offsetTop <= scrollTop) {
          active = heading;
        } else {
          break;
        }
      }

      if (active !== currentActive) {
        if (currentActive) {
          currentActive.link.classList.remove('active');
        }
        active.link.classList.add('active');
        currentActive = active;

        // Scroll active link into view if in a scroll container
        const scrollContainer = nav.closest('.toc-scroll-container');
        if (scrollContainer) {
          const containerRect = scrollContainer.getBoundingClientRect();
          const linkRect = active.link.getBoundingClientRect();
          if (linkRect.top < containerRect.top || linkRect.bottom > containerRect.bottom) {
            active.link.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        }
      }
    }

    // Set up smooth scrolling on click
    items.forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const id = link.dataset.tocItem.replace(/^#/, '');
        const target = document.getElementById(id);

        if (target) {
          if (smoothEnabled) {
            const offsetTop = target.offsetTop - (scrollOffset - 20);
            window.scrollTo({
              top: offsetTop,
              behavior: 'smooth'
            });
          } else {
            target.scrollIntoView({ block: 'start' });
          }

          // Update URL without jumping
          history.replaceState(null, '', '#' + id);
        }
      });
    });

    // Set up scroll spy
    if (spyEnabled) {
      // Use BengalUtils throttle if available
      if (window.BengalUtils && window.BengalUtils.throttleScroll) {
        scrollHandler = window.BengalUtils.throttleScroll(updateActive);
      } else {
        // Simple throttle fallback
        let ticking = false;
        scrollHandler = function() {
          if (!ticking) {
            window.requestAnimationFrame(() => {
              updateActive();
              ticking = false;
            });
            ticking = true;
          }
        };
      }

      window.addEventListener('scroll', scrollHandler, { passive: true });

      // Initial update
      updateActive();
    }

    // Handle hash changes
    window.addEventListener('hashchange', updateActive);

    // Expose API on element
    nav._bengalToc = {
      updateActive,
      cleanup: function() {
        if (scrollHandler) {
          window.removeEventListener('scroll', scrollHandler);
        }
        window.removeEventListener('hashchange', updateActive);
      }
    };
  });

})();

