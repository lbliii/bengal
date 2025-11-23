/**
 * Bengal SSG Default Theme
 * Interactive Elements
 *
 * Provides smooth, delightful interactions:
 * - Back to top button
 * - Reading progress indicator
 * - Smooth scroll enhancements
 */

(function() {
  'use strict';

  /**
   * Back to Top Button
   * Shows a floating button when user scrolls down
   */
  function setupBackToTop() {
    // Create button element
    const button = document.createElement('button');
    button.className = 'back-to-top';
    button.setAttribute('aria-label', 'Scroll to top');
    button.setAttribute('title', 'Back to top');
    button.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"></line>
        <polyline points="5 12 12 5 19 12"></polyline>
      </svg>
    `;

    // Add to document
    document.body.appendChild(button);

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
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          toggleVisibility();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });

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
    progressBar.appendChild(progressFill);

    // Add to document (at top)
    document.body.insertBefore(progressBar, document.body.firstChild);

    // Update progress on scroll
    const updateProgress = () => {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

      // Calculate progress (0-100)
      const scrollableHeight = documentHeight - windowHeight;
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (scrollTop / scrollableHeight) * 100))
        : 0;

      // Update UI
      progressFill.style.width = `${progress}%`;
      progressBar.setAttribute('aria-valuenow', Math.round(progress));
    };

    // Throttle scroll events
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          updateProgress();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });

    // Update on resize
    window.addEventListener('resize', updateProgress, { passive: true });

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
   */
  function setupScrollSpy() {
    const sections = document.querySelectorAll('h2[id], h3[id]');
    if (sections.length === 0) return;

    // Only select docs-nav links, not TOC links (toc.js handles those)
    const navLinks = document.querySelectorAll('.docs-nav a');
    if (navLinks.length === 0) return;

    let currentSection = '';

    const highlightNavigation = () => {
      const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;

      // Find current section
      let foundSection = '';
      sections.forEach(section => {
        const sectionTop = section.offsetTop - 100; // Offset for header
        if (scrollPosition >= sectionTop) {
          foundSection = section.getAttribute('id');
        }
      });

      // Update if changed
      if (foundSection !== currentSection) {
        currentSection = foundSection;

        // Remove all active classes
        navLinks.forEach(link => {
          link.classList.remove('active');
        });

        // Add active class to current section link
        if (currentSection) {
          navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === `#${currentSection}`) {
              link.classList.add('active');
            }
          });
        }
      }
    };

    // Throttle scroll events
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          highlightNavigation();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });

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

    console.log('Documentation navigation initialized');
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
    document.addEventListener('click', (e) => {
      if (sidebar.hasAttribute('data-open') &&
          !sidebar.contains(e.target) &&
          !toggleButton.contains(e.target)) {
        sidebar.removeAttribute('data-open');
        toggleButton.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
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
   * Initialize all interactive features
   */
  function init() {
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

    console.log('Interactive elements initialized');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

})();
