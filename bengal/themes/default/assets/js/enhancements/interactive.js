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
    const button = document.querySelector('.back-to-top');
    if (!button) {
      log('Back-to-top button not found in template');
      return;
    }

    button.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    const sentinel = document.querySelector('.back-to-top-sentinel');
    if (sentinel && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver(([entry]) => {
        button.classList.toggle('visible', !entry.isIntersecting);
      }, { threshold: 0 });
      observer.observe(sentinel);
      cleanupHandlers.scroll.push(() => observer.disconnect());
      return;
    }

    // Fallback for browsers without IntersectionObserver
    let isVisible = false;
    const toggleVisibility = () => {
      const scrolled = window.pageYOffset || document.documentElement.scrollTop;
      const shouldShow = scrolled > 300;
      if (shouldShow !== isVisible) {
        isVisible = shouldShow;
        button.classList.toggle('visible', shouldShow);
      }
    };
    const throttledToggle = throttleScroll(toggleVisibility);
    window.addEventListener('scroll', throttledToggle, { passive: true });
    cleanupHandlers.scroll.push(() => window.removeEventListener('scroll', throttledToggle));
    toggleVisibility();
  }

  /**
   * Reading Progress Indicator
   * Static bar from template; fill driven by CSS scroll timeline when supported.
   */
  function setupReadingProgress() {
    const progressBar = document.querySelector('.reading-progress');
    const progressFill = progressBar?.querySelector('.reading-progress__fill');
    if (!progressBar || !progressFill) {
      return;
    }

    if (CSS.supports('animation-timeline', 'scroll()')) {
      return;
    }

    let cachedDocHeight = document.documentElement.scrollHeight;
    let cachedWinHeight = window.innerHeight;
    let lastProgress = -1;

    const updateDimensions = () => {
      cachedDocHeight = document.documentElement.scrollHeight;
      cachedWinHeight = window.innerHeight;
    };

    const updateProgress = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollableHeight = cachedDocHeight - cachedWinHeight;
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (scrollTop / scrollableHeight) * 100))
        : 0;
      const roundedProgress = Math.round(progress);
      if (roundedProgress !== lastProgress) {
        lastProgress = roundedProgress;
        progressFill.style.transform = `scaleX(${progress / 100})`;
        progressBar.setAttribute('aria-valuenow', String(roundedProgress));
      }
    };

    const throttledUpdate = throttleScroll(updateProgress);
    window.addEventListener('scroll', throttledUpdate, { passive: true });
    cleanupHandlers.scroll.push(() => window.removeEventListener('scroll', throttledUpdate));

    const debouncedDimUpdate = debounce(() => {
      updateDimensions();
      updateProgress();
    }, 100);
    window.addEventListener('resize', debouncedDimUpdate, { passive: true });
    cleanupHandlers.resize.push(() => window.removeEventListener('resize', debouncedDimUpdate));

    updateProgress();
  }

  /**
   * Scroll Spy for Navigation
   * Highlights current section in navigation via IntersectionObserver.
   */
  function setupScrollSpy(root, cleanupList) {
    root = root || document;
    cleanupList = cleanupList || cleanupHandlers.scroll;

    const sections = document.querySelectorAll('h2[id], h3[id]');
    if (sections.length === 0) return;

    const navLinks = root.querySelectorAll('.docs-nav a');
    if (navLinks.length === 0) return;

    if (!('IntersectionObserver' in window)) {
      return;
    }

    let currentSection = '';
    const visibleSections = new Map();

    const highlightSection = (sectionId) => {
      if (!sectionId || sectionId === currentSection) return;
      currentSection = sectionId;
      navLinks.forEach((link) => {
        const href = link.getAttribute('href');
        link.classList.toggle('active', href === `#${sectionId}`);
      });
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const id = entry.target.getAttribute('id');
        if (!id) return;
        if (entry.isIntersecting) {
          visibleSections.set(id, entry.intersectionRatio);
        } else {
          visibleSections.delete(id);
        }
      });

      if (visibleSections.size === 0) return;

      let bestId = '';
      let bestRatio = -1;
      visibleSections.forEach((ratio, id) => {
        if (ratio >= bestRatio) {
          bestRatio = ratio;
          bestId = id;
        }
      });

      highlightSection(bestId);
    }, {
      root: null,
      rootMargin: '-80px 0px -55% 0px',
      threshold: [0, 0.1, 0.25, 0.5, 0.75, 1]
    });

    sections.forEach((section) => observer.observe(section));
    cleanupList.push(() => observer.disconnect());
  }

  /**
   * Documentation Navigation Enhancement
   *
   * Uses native <details>/<summary> for expand/collapse (no JS required for toggle).
   * CSS :has() syncs visibility of sibling items with details[open] state.
   *
   * This function provides a JS fallback for ensuring parent details elements
   * are opened when they contain the active page (for deep links/bookmarks).
   * The template already sets `open` attribute on active trail items via Jinja,
   * but this provides a fallback for dynamic scenarios.
   */
  function setupDocsNavigation(root) {
    root = root || document;
    // Find the active navigation link (scoped to the nav element)
    const activeLink = root.querySelector(
      '.docs-nav-link.active, .docs-nav-link[aria-current="page"], ' +
      '.docs-nav-group-link.active, .docs-nav-group-link[aria-current="page"]'
    );

    if (!activeLink) {
      log('Documentation navigation initialized (no active link)');
      return;
    }

    // If the active link is a section group link (section index page),
    // ensure its parent details is open
    if (activeLink.classList.contains('docs-nav-group-link')) {
      const group = activeLink.closest('.docs-nav-group');
      if (group) {
        const details = group.querySelector(':scope > .docs-nav-details');
        if (details) {
          details.setAttribute('open', '');
        }
      }
    }

    // Walk up the DOM and ensure all parent <details> elements are open
    let parent = activeLink.parentElement;
    while (parent) {
      if (parent.classList?.contains('docs-nav-group') &&
          !parent.classList.contains('docs-nav-group--root') &&
          !parent.classList.contains('docs-nav-group--leaf')) {
        const details = parent.querySelector(':scope > .docs-nav-details');
        if (details) {
          details.setAttribute('open', '');
        }
      }
      parent = parent.parentElement;
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

    // Setup document-global features. Docs-nav scroll-spy + active-trail are
    // element-scoped and run from the <bengal-docs-nav> custom element instead.
    setupBackToTop();
    setupReadingProgress();
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
  // Custom element: <bengal-docs-nav>
  // ============================================================

  // Owns the docs-nav scroll-spy + active-trail expansion, scoped to the nav
  // element. connectedCallback auto-inits (incl. dynamically inserted content);
  // disconnectedCallback removes its scroll/resize listeners (kept in a private
  // list so they don't collide with the document-global cleanupHandlers).
  if (window.Bengal && window.Bengal.define) {
    window.Bengal.define('bengal-docs-nav', class extends window.Bengal.Base {
      init() {
        this._docsNavCleanup = [];
        setupScrollSpy(this, this._docsNavCleanup);
        setupDocsNavigation(this);
      }
      teardown() {
        (this._docsNavCleanup || []).forEach((fn) => fn());
        this._docsNavCleanup = [];
      }
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
