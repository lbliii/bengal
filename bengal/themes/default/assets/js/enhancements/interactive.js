/**
 * Bengal SSG Default Theme
 * Interactive Elements
 *
 * Provides smooth, delightful interactions:
 * - Back to top button
 * - Reading progress indicator
 * - Smooth scroll enhancements
 */

(function () {
  'use strict';

  // Ensure utils are available (with graceful degradation)
  if (!window.BengalUtils) {
    console.error('[Bengal] BengalUtils not loaded - interactive.js requires utils.js');
    // Provide fallback functions to prevent errors
    window.BengalUtils = {
      log: () => {},
      throttleScroll: (fn) => {
        let ticking = false;
        return function throttled(...args) {
          if (!ticking) {
            window.requestAnimationFrame(() => {
              fn.apply(this, args);
              ticking = false;
            });
            ticking = true;
          }
        };
      },
      debounce: (fn, wait) => {
        let timeout;
        return function debounced(...args) {
          clearTimeout(timeout);
          timeout = setTimeout(() => fn.apply(this, args), wait);
        };
      },
      ready: (fn) => {
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', fn);
        } else {
          fn();
        }
      }
    };
  }

  // Safely destructure with defaults to prevent errors
  const log = window.BengalUtils?.log || (() => {});
  const throttleScroll = window.BengalUtils?.throttleScroll || ((fn) => {
    let ticking = false;
    return function throttled(...args) {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          fn.apply(this, args);
          ticking = false;
        });
        ticking = true;
      }
    };
  });
  const debounce = window.BengalUtils?.debounce || ((fn, wait) => {
    let timeout;
    return function debounced(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), wait);
    };
  });
  const ready = window.BengalUtils?.ready || ((fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  });

  // Store references for cleanup to prevent memory leaks
  const cleanupHandlers = {
    scroll: [],
    resize: [],
    click: [],
    keydown: []
  };

  /**
   * Back to Top Button
   * Shows a floating button when user scrolls down
   */
  function setupBackToTop() {
    // Find existing button from template (static HTML is more reliable)
    const button = document.querySelector('.back-to-top');
    if (!button) {
      log('Back-to-top button not found in template');
      return;
    }

    // Show/hide based on scroll position
    let isVisible = false;
    const toggleVisibility = () => {
      const scrolled = window.pageYOffset || document.documentElement.scrollTop;
      const shouldShow = scrolled > 300; // Show after 300px

      if (shouldShow !== isVisible) {
        isVisible = shouldShow;
        button.classList.toggle('visible', shouldShow);
      }
    };

    // Throttle scroll events for performance
    const throttledToggle = throttleScroll(toggleVisibility);
    window.addEventListener('scroll', throttledToggle, { passive: true });
    cleanupHandlers.scroll.push(() => {
      window.removeEventListener('scroll', throttledToggle);
    });

    // Scroll to top on click
    button.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });

    // Initial check
    toggleVisibility();
  }

  /**
   * Reading Progress Indicator
   * Shows a bar at the top indicating reading progress
   *
   * Performance: Caches document dimensions and uses transform
   * instead of width for GPU-accelerated updates.
   */
  function setupReadingProgress() {
    // Create progress bar
    const progressBar = document.createElement('div');
    progressBar.className = 'reading-progress';
    progressBar.setAttribute('role', 'progressbar');
    progressBar.setAttribute('aria-label', 'Reading progress');
    progressBar.setAttribute('aria-valuemin', '0');
    progressBar.setAttribute('aria-valuemax', '100');

    const progressFill = document.createElement('div');
    progressFill.className = 'reading-progress__fill';
    // Use transform for GPU-accelerated updates (avoids reflow)
    progressFill.style.width = '100%';
    progressFill.style.transformOrigin = 'left';
    progressBar.appendChild(progressFill);

    // Add to document (at top)
    document.body.insertBefore(progressBar, document.body.firstChild);

    // Cache document dimensions (avoid reading on every scroll)
    let cachedDocHeight = document.documentElement.scrollHeight;
    let cachedWinHeight = window.innerHeight;
    let lastProgress = -1;

    // Update cached dimensions on resize
    const updateDimensions = () => {
      cachedDocHeight = document.documentElement.scrollHeight;
      cachedWinHeight = window.innerHeight;
    };

    // Update progress on scroll (uses cached dimensions)
    const updateProgress = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

      // Calculate progress (0-100) using cached dimensions
      const scrollableHeight = cachedDocHeight - cachedWinHeight;
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (scrollTop / scrollableHeight) * 100))
        : 0;

      // Only update DOM if progress changed significantly (avoid micro-updates)
      const roundedProgress = Math.round(progress);
      if (roundedProgress !== lastProgress) {
        lastProgress = roundedProgress;
        // Use transform for GPU-accelerated animation (no reflow)
        progressFill.style.transform = `scaleX(${progress / 100})`;
        progressBar.setAttribute('aria-valuenow', roundedProgress);
      }
    };

    // Throttle scroll events
    const throttledUpdate = throttleScroll(updateProgress);
    window.addEventListener('scroll', throttledUpdate, { passive: true });
    cleanupHandlers.scroll.push(() => {
      window.removeEventListener('scroll', throttledUpdate);
    });

    // Update dimensions on resize (debounced)
    const debouncedDimUpdate = debounce(() => {
      updateDimensions();
      updateProgress();
    }, 100);
    window.addEventListener('resize', debouncedDimUpdate, { passive: true });
    cleanupHandlers.resize.push(() => {
      window.removeEventListener('resize', debouncedDimUpdate);
    });

    // Initial update
    updateProgress();
  }

  /**
   * Enhanced Smooth Scroll
   * NOTE: Removed - already handled by main.js
   * Keeping function signature for backwards compatibility
   */
  function setupSmoothScroll() {
    // Smooth scroll is now only handled in main.js to avoid duplicate event listeners
    // This function is kept as a no-op for backwards compatibility
  }

  /**
   * Scroll Spy for Navigation
   * Highlights current section in navigation as user scrolls
   *
   * Note: Only handles docs-nav links. TOC links are handled by toc.js
   * which has more sophisticated collapse/expand behavior.
   *
   * Performance: Caches section offsets and batches DOM reads/writes
   * to avoid forced reflows during scroll.
   */
  function setupScrollSpy() {
    const sections = document.querySelectorAll('h2[id], h3[id]');
    if (sections.length === 0) return;

    // Only select docs-nav links, not TOC links (toc.js handles those)
    const navLinks = document.querySelectorAll('.docs-nav a');
    if (navLinks.length === 0) return;

    let currentSection = '';

    // Cache section data to avoid reading offsetTop on every scroll
    // Structure: { id: string, element: Element, offsetTop: number }
    let sectionData = [];

    // Build initial cache
    const updateSectionCache = () => {
      sectionData = Array.from(sections).map(section => ({
        id: section.getAttribute('id'),
        element: section,
        offsetTop: section.offsetTop
      }));
    };

    // Initialize cache
    updateSectionCache();

    // Rebuild cache on resize (layout may change)
    const debouncedCacheUpdate = debounce(updateSectionCache, 250);
    window.addEventListener('resize', debouncedCacheUpdate, { passive: true });
    cleanupHandlers.resize.push(() => {
      window.removeEventListener('resize', debouncedCacheUpdate);
    });

    const highlightNavigation = () => {
      const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;
      const headerOffset = 80; // Matches header height + buffer

      // Find current section using cached offsets (no DOM reads)
      let foundSection = '';
      for (let i = 0; i < sectionData.length; i++) {
        if (scrollPosition >= sectionData[i].offsetTop - headerOffset) {
          foundSection = sectionData[i].id;
        }
      }

      // Only update DOM if changed
      if (foundSection !== currentSection) {
        currentSection = foundSection;

        // Batch all class changes
        navLinks.forEach(link => {
          const href = link.getAttribute('href');
          const shouldBeActive = currentSection && href === `#${currentSection}`;

          if (shouldBeActive) {
            link.classList.add('active');
          } else {
            link.classList.remove('active');
          }
        });
      }
    };

    // Throttle scroll events
    const throttledHighlight = throttleScroll(highlightNavigation);
    window.addEventListener('scroll', throttledHighlight, { passive: true });
    cleanupHandlers.scroll.push(() => {
      window.removeEventListener('scroll', throttledHighlight);
    });

    // Initial highlight
    highlightNavigation();
  }

  /**
   * Documentation Navigation Toggles
   * Handles expand/collapse of navigation sections
   */
  function setupDocsNavigation() {
    const toggleButtons = document.querySelectorAll('.docs-nav-group-toggle');

    if (toggleButtons.length === 0) return;

    toggleButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();

        // Toggle aria-expanded state
        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        button.setAttribute('aria-expanded', !isExpanded);

        // Get the associated content
        const controlsId = button.getAttribute('aria-controls');
        if (controlsId) {
          const content = document.getElementById(controlsId);
          if (content) {
            // Toggle display (CSS handles this via aria-expanded selector)
            // But we can add/remove a class for additional styling if needed
            content.classList.toggle('expanded', !isExpanded);
          }
        }
      });
    });

    // Auto-expand sections that contain the active page
    // Check for both .active class and aria-current="page" attribute
    const activeLink = document.querySelector(
      '.docs-nav-link.active, .docs-nav-link[aria-current="page"], ' +
      '.docs-nav-group-link.active, .docs-nav-group-link[aria-current="page"]'
    );

    if (activeLink) {
      // If the active link is a section group link (section index page), expand that section
      if (activeLink.classList.contains('docs-nav-group-link')) {
        const wrapper = activeLink.parentElement;
        if (wrapper && wrapper.classList.contains('docs-nav-group-toggle-wrapper')) {
          const toggle = wrapper.querySelector('.docs-nav-group-toggle');
          const items = wrapper.nextElementSibling;
          if (toggle && items && items.classList.contains('docs-nav-group-items')) {
            toggle.setAttribute('aria-expanded', 'true');
            items.classList.add('expanded');
          }
        }
      }

      // Find all parent nav groups and expand them (walk up the DOM tree)
      let parent = activeLink.parentElement;
      while (parent) {
        if (parent.classList.contains('docs-nav-group-items')) {
          // Find the toggle button for this group
          // It's now inside a wrapper that's the previous sibling
          const wrapper = parent.previousElementSibling;
          if (wrapper && wrapper.classList.contains('docs-nav-group-toggle-wrapper')) {
            const toggle = wrapper.querySelector('.docs-nav-group-toggle');
            if (toggle) {
              toggle.setAttribute('aria-expanded', 'true');
              parent.classList.add('expanded');
            }
          }
        }
        parent = parent.parentElement;
      }
    }

    log('Documentation navigation initialized');
  }

  /**
   * Mobile Sidebar Toggle
   * Handles show/hide of sidebar on mobile devices
   */
  function setupMobileSidebar() {
    const toggleButton = document.querySelector('.docs-sidebar-toggle');
    const sidebar = document.getElementById('docs-sidebar');

    if (!toggleButton || !sidebar) return;

    toggleButton.addEventListener('click', () => {
      const isOpen = sidebar.hasAttribute('data-open');

      if (isOpen) {
        sidebar.removeAttribute('data-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      } else {
        sidebar.setAttribute('data-open', '');
        toggleButton.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
      }
    });

    // Close sidebar when clicking outside on mobile
    const outsideClickHandler = (e) => {
      if (sidebar.hasAttribute('data-open') &&
        !sidebar.contains(e.target) &&
        !toggleButton.contains(e.target)) {
        sidebar.removeAttribute('data-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    };
    document.addEventListener('click', outsideClickHandler);
    cleanupHandlers.click.push(() => {
      document.removeEventListener('click', outsideClickHandler);
    });

    // Close sidebar on navigation (mobile) - use event delegation for better performance
    sidebar.addEventListener('click', (e) => {
      // Check if clicked element is a link
      const link = e.target.closest('a');
      if (link && window.innerWidth < 768) {
        sidebar.removeAttribute('data-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });
  }

  /**
   * Changelog Filter
   * Handles filtering of changelog timeline items by change type
   */
  function setupChangelogFilter() {
    const filterButtons = document.querySelectorAll('.changelog-filter-btn');
    const timelineItems = document.querySelectorAll('.timeline-item');

    if (filterButtons.length === 0 || timelineItems.length === 0) return;

    filterButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        const filter = this.getAttribute('data-filter');

        // Update button states
        filterButtons.forEach(function (btn) {
          btn.classList.remove('active');
          btn.setAttribute('aria-pressed', 'false');
        });
        this.classList.add('active');
        this.setAttribute('aria-pressed', 'true');

        // Filter timeline items
        timelineItems.forEach(function (item) {
          const changeTypes = item.getAttribute('data-change-types') || '';

          // Items without structured data (empty or 'all') show for all filters
          // Items with structured data only show if they match the filter
          const hasStructuredData = changeTypes && changeTypes !== 'all';
          const shouldShow = filter === 'all' ||
            !hasStructuredData ||
            changeTypes.includes(filter);

          if (shouldShow) {
            item.style.display = '';
            // Smooth fade-in animation
            item.style.opacity = '0';
            setTimeout(function () {
              item.style.transition = 'opacity 0.3s ease';
              item.style.opacity = '1';
            }, 10);
          } else {
            item.style.display = 'none';
          }
        });
      });
    });
  }

  /**
   * Initialize all interactive features
   */
  function init() {
    // IMPORTANT: Clean up any existing handlers before re-initializing
    // This prevents memory leaks if init is called multiple times
    cleanup();

    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      // Disable animations for accessibility
      document.documentElement.classList.add('reduce-motion');
    }

    // Setup features
    setupBackToTop();
    setupReadingProgress();
    setupSmoothScroll();
    setupScrollSpy();
    setupDocsNavigation();
    setupMobileSidebar();
    setupChangelogFilter();

    log('Interactive elements initialized');
  }

  /**
   * Cleanup function to prevent memory leaks
   */
  function cleanup() {
    cleanupHandlers.scroll.forEach(handler => handler());
    cleanupHandlers.resize.forEach(handler => handler());
    cleanupHandlers.click.forEach(handler => handler());
    cleanupHandlers.keydown.forEach(handler => handler());
    cleanupHandlers.scroll = [];
    cleanupHandlers.resize = [];
    cleanupHandlers.click = [];
    cleanupHandlers.keydown = [];
  }

  // ============================================================
  // Registration
  // ============================================================

  // Register with enhancement system (multiple registrations for different features)
  if (window.Bengal && window.Bengal.enhance) {
    // Back to top button
    Bengal.enhance.register('back-to-top', function(el, options) {
      setupBackToTop();
    });

    // Reading progress bar
    Bengal.enhance.register('reading-progress', function(el, options) {
      setupReadingProgress();
    });

    // Docs navigation scroll spy
    Bengal.enhance.register('docs-nav', function(el, options) {
      setupScrollSpy();
    });
  }

  // ============================================================
  // Auto-initialize
  // ============================================================

  // Initialize when DOM is ready
  ready(init);

  // Cleanup on page unload to prevent memory leaks
  window.addEventListener('beforeunload', cleanup);

  // Export cleanup for manual cleanup if needed (backward compatibility)
  window.BengalInteractive = {
    cleanup: cleanup
  };

})();
