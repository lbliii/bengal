/**
 * Bengal SSG Default Theme
 * Main JavaScript
 */

(function () {
  'use strict';

  // Ensure utils are available (with graceful degradation)
  if (!window.BengalUtils) {
    console.error('[Bengal] BengalUtils not loaded - main.js requires utils.js');
    // Provide fallback functions to prevent errors
    window.BengalUtils = {
      log: () => {},
      copyToClipboard: async () => {},
      isExternalUrl: () => false,
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
  const copyToClipboard = window.BengalUtils?.copyToClipboard || (async () => {});
  const isExternalUrl = window.BengalUtils?.isExternalUrl || (() => false);
  const ready = window.BengalUtils?.ready || ((fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  });

  /**
   * Smooth scroll for anchor links
   */
  function setupSmoothScroll() {
    // Ensure document is available
    if (typeof document === 'undefined') {
      log('[Bengal] Document not available for setupSmoothScroll');
      return;
    }

    const anchors = document.querySelectorAll('a[href^="#"]');
    if (!anchors || anchors.length === 0) {
      return;
    }

    anchors.forEach(function (anchor) {
      if (!anchor || typeof anchor.addEventListener !== 'function') {
        return;
      }
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');

        // Skip empty anchors
        if (href === '#') {
          return;
        }

        // Extract ID from href (remove the '#')
        const id = href.substring(1);
        const target = document.getElementById(id);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });

          // Update URL without jumping
          history.pushState(null, null, href);

          // Focus target for accessibility
          target.focus({ preventScroll: true });
        }
      });
    });
  }

  /**
   * Add external link indicators
   */
  function setupExternalLinks() {
    const links = document.querySelectorAll('a[href]');
    links.forEach(function (link) {
      const href = link.getAttribute('href');

      // Skip anchor links and empty hrefs
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
        return;
      }

      // Check if external using URL parsing
      if (isExternalUrl(href)) {
        // Add external data attribute for CSS targeting
        link.setAttribute('data-external', 'true');
        link.setAttribute('rel', 'noopener noreferrer');
        link.setAttribute('target', '_blank');

        // Add visual indicator (optional)
        link.setAttribute('aria-label', link.textContent + ' (opens in new tab)');
      }
    });
  }

  /**
   * Copy code button for code blocks with language labels
   */
  function setupCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');

    codeBlocks.forEach(function (codeBlock) {
      const pre = codeBlock.parentElement;

      // Skip if already processed
      if (pre.closest('.code-block-wrapper') || pre.querySelector('.code-copy-button')) {
        return;
      }

      // Check if this is inside a Pygments table (has line numbers)
      const highlightTable = pre.closest('.highlighttable');
      const isTableLayout = !!highlightTable;

      // Detect language from class (e.g., language-python, hljs-python)
      let language = '';
      const classList = codeBlock.className;
      const matches = classList.match(/language-(\w+)|hljs-(\w+)/);
      if (matches) {
        language = (matches[1] || matches[2]).toUpperCase();
      }

      // Create copy button
      const button = document.createElement('button');
      button.className = 'code-copy-button';
      button.setAttribute('aria-label', 'Copy');

      // Add copy icon (SVG) - icon only, no text
      button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;

      if (isTableLayout) {
        // For Pygments table layout: add button to the .highlight wrapper
        // This ensures button stays in top-right of entire code block
        const highlightWrapper = highlightTable.closest('.highlight');
        if (highlightWrapper) {
          highlightWrapper.classList.add('has-copy-button');
          button.classList.add('code-copy-button--absolute');
          highlightWrapper.appendChild(button);
        }
      } else {
        // Standard layout: wrap pre in container

        // Create header container
        const header = document.createElement('div');
        header.className = 'code-header-inline';

        // Create language label if detected
        if (language) {
          const langLabel = document.createElement('span');
          langLabel.className = 'code-language';
          langLabel.textContent = language;
          header.appendChild(langLabel);
        } else {
          // Empty span to maintain layout
          header.appendChild(document.createElement('span'));
        }

        header.appendChild(button);

        // Wrap pre in a container and place button outside the scrolling area
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        // Move decorative border classes to wrapper so pseudo-borders stay fixed while <pre> scrolls
        const borderClasses = [
          'gradient-border',
          'gradient-border-subtle',
          'gradient-border-strong',
          'fluid-border',
          'fluid-combined'
        ];
        borderClasses.forEach(function (cls) {
          if (pre.classList.contains(cls)) {
            pre.classList.remove(cls);
            wrapper.classList.add(cls);
          }
        });

        // Insert wrapper before pre, then move pre into wrapper
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);

        // Add header to wrapper (not inside pre)
        wrapper.appendChild(header);
      }

      // Copy functionality
      button.addEventListener('click', function (e) {
        e.preventDefault();
        const code = codeBlock.textContent;

        copyToClipboard(code).then(function () {
          // Show success
          button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Copied!</span>
          `;
          button.classList.add('copied');
          button.setAttribute('aria-label', 'Code copied!');

          // Reset after 2 seconds
          setTimeout(function () {
            button.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            `;
            button.classList.remove('copied');
            button.setAttribute('aria-label', 'Copy');
          }, 2000);
        }).catch(function (err) {
          log('Failed to copy code:', err);
          button.setAttribute('aria-label', 'Failed to copy');

          // Show error state briefly
          setTimeout(function () {
            button.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            `;
            button.setAttribute('aria-label', 'Copy');
          }, 2000);
        });
      });
    });
  }

  /**
   * Lazy load images
   */
  let imageObserver = null;
  let trackScrollHandler = null;

  function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      imageObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
            }
            if (imageObserver) {
              imageObserver.unobserve(img);
            }
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(function (img) {
        if (imageObserver) {
          imageObserver.observe(img);
        }
      });
    } else {
      // Fallback for older browsers
      document.querySelectorAll('img[data-src]').forEach(function (img) {
        img.src = img.dataset.src;
      });
    }
  }

  /**
   * Table of contents highlighting
   *
   * NOTE: TOC highlighting functionality has been moved to enhancements/toc.js
   * This function is kept here for backward compatibility but is no longer called.
   * The toc.js module handles all TOC functionality including highlighting.
   */
  // Removed - functionality moved to enhancements/toc.js

  /**
   * Detect keyboard navigation for better focus indicators
   */
  function setupKeyboardDetection() {
    // Add class to body when user tabs (keyboard navigation)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        document.body.classList.add('user-is-tabbing');
      }
    });

    // Remove class when user clicks (mouse navigation)
    document.addEventListener('mousedown', function () {
      document.body.classList.remove('user-is-tabbing');
    });
  }

  /**
   * Setup scroll animations fallback (for browsers without scroll-driven animations)
   */
  function setupScrollAnimations() {
    // Only setup fallback if browser doesn't support scroll-driven animations
    if (!CSS.supports('animation-timeline', 'scroll()')) {
      const animatedElements = document.querySelectorAll('.stagger-fade-in > *');

      if (animatedElements.length === 0) return;

      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-visible');
              // Unobserve after animation to improve performance
              observer.unobserve(entry.target);
            }
          });
        }, {
          rootMargin: '0px 0px -50px 0px', // Trigger slightly before element enters viewport
          threshold: 0.1
        });

        animatedElements.forEach(function(element) {
          observer.observe(element);
        });
      } else {
        // Fallback: show all elements immediately
        animatedElements.forEach(function(element) {
          element.classList.add('is-visible');
        });
      }
    }
  }

  /**
   * Initialize all features
   */
  /**
   * Track progress bar - updates based on scroll position through track sections
   */
  function setupTrackProgress() {
    const progressBar = document.getElementById('track-progress-bar');
    if (!progressBar) {
      return; // Not on a track page
    }

    const trackSections = document.querySelectorAll('.track-section');
    if (trackSections.length === 0) {
      return; // No track sections found
    }

    function updateProgress() {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

      // Calculate progress based on scroll position
      // Progress = (scroll position + viewport height) / total document height
      const scrollableHeight = documentHeight - windowHeight;
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (scrollTop / scrollableHeight) * 100))
        : 0;

      // Update progress bar
      progressBar.style.width = progress + '%';
      progressBar.setAttribute('aria-valuenow', Math.round(progress));

      // Update active section in sidebar navigation
      updateActiveSection();
    }

    function updateActiveSection() {
      // Find which section is currently in view
      const scrollPosition = window.pageYOffset + window.innerHeight / 3; // Trigger at 1/3 down viewport

      let activeSection = null;
      trackSections.forEach(function(section) {
        const sectionTop = section.offsetTop;
        const sectionBottom = sectionTop + section.offsetHeight;

        if (scrollPosition >= sectionTop && scrollPosition < sectionBottom) {
          activeSection = section.id;
        }
      });

      // Update sidebar navigation active state
      if (activeSection) {
        document.querySelectorAll('.track-progress-nav-link').forEach(function(link) {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + activeSection) {
            link.classList.add('active');
          }
        });
      }
    }

    // Update on scroll (throttled)
    let ticking = false;
    trackScrollHandler = function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(function() {
          updateProgress();
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', trackScrollHandler, { passive: true });

    // Initial update
    updateProgress();
  }

  function init() {
    // IMPORTANT: Clean up any existing observers before re-initializing
    // This prevents memory leaks if init is called multiple times
    cleanup();

    setupSmoothScroll();
    setupExternalLinks();
    setupCodeCopyButtons();
    setupLazyLoading();
    // setupTOCHighlight() removed - TOC highlighting now handled by enhancements/toc.js
    setupKeyboardDetection();
    setupScrollAnimations();
    setupTrackProgress();

    log('Bengal theme initialized');
  }

  /**
   * Cleanup function to prevent memory leaks
   */
  function cleanup() {
    if (imageObserver) {
      imageObserver.disconnect();
      imageObserver = null;
    }
    // tocObserver removed - TOC functionality moved to enhancements/toc.js
    if (trackScrollHandler) {
      window.removeEventListener('scroll', trackScrollHandler);
      trackScrollHandler = null;
    }
  }

  // Initialize after DOM is ready
  ready(init);

  // Cleanup on page unload to prevent memory leaks
  window.addEventListener('beforeunload', cleanup);

  // Export cleanup for manual cleanup if needed
  window.BengalMain = {
    cleanup: cleanup
  };
})();
