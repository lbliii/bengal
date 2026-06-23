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
  const ready = window.BengalUtils?.ready || ((fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  });

  /**
   * Delegated copy handler for build-time code copy buttons.
   */
  function announceCopy(message) {
    let region = document.getElementById('code-copy-live-region');
    if (!region) {
      region = document.createElement('div');
      region.id = 'code-copy-live-region';
      region.className = 'visually-hidden';
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      document.body.appendChild(region);
    }
    region.textContent = message;
  }

  function setupDelegatedCodeCopy() {
    document.addEventListener('click', function (e) {
      const wrapButton = e.target.closest('.code-wrap-toggle');
      if (wrapButton) {
        e.preventDefault();
        const wrapper = wrapButton.closest('.code-block-wrapper, .highlight, pre');
        const pre = wrapper?.querySelector('pre');
        if (pre) {
          pre.classList.toggle('code-block--wrap');
          const wrapped = pre.classList.contains('code-block--wrap');
          wrapButton.setAttribute('aria-pressed', wrapped ? 'true' : 'false');
          wrapButton.setAttribute('aria-label', wrapped ? 'Disable word wrap' : 'Enable word wrap');
        }
        return;
      }

      const button = e.target.closest('.code-copy-button');
      if (!button) return;

      e.preventDefault();
      const wrapper = button.closest('.code-block-wrapper, .highlight, .highlighttable');
      const codeBlock = wrapper
        ? wrapper.querySelector('pre code, .highlight pre, td.code')
        : button.closest('pre')?.querySelector('code');
      if (!codeBlock) return;

      const code = codeBlock.textContent;
      copyToClipboard(code).then(function () {
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Copied!</span>
          `;
        button.classList.add('copied');
        button.setAttribute('aria-label', 'Code copied!');
        announceCopy('Code copied to clipboard');

        setTimeout(function () {
          button.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            `;
          button.classList.remove('copied');
          button.setAttribute('aria-label', 'Copy code to clipboard');
        }, 2000);
      }).catch(function (err) {
        log('Failed to copy code:', err);
        button.setAttribute('aria-label', 'Failed to copy');
      });
    });
  }

  /**
   * Focus hash targets for accessibility (scroll uses CSS scroll-behavior).
   */
  function setupHashFocus() {
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (!href || href === '#') return;

        const target = document.getElementById(href.substring(1));
        if (!target) return;

        if (!target.hasAttribute('tabindex')) {
          target.setAttribute('tabindex', '-1');
        }
        requestAnimationFrame(function () {
          target.focus({ preventScroll: true });
        });
      });
    });
  }

  /**
   * Lazy load images
   */
  let imageObserver = null;
  let trackProgressHandler = null;
  let trackSectionObserver = null;

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
    const scrollRevealRoot = document.querySelector('.scroll-reveal-root');
    const selector = scrollRevealRoot
      ? '.scroll-reveal-root .prose > *, .fade-in-on-scroll, .stagger-fade-in > *'
      : '.fade-in-on-scroll, .stagger-fade-in > *';

    // Only setup fallback if browser doesn't support scroll-driven animations
    if (!CSS.supports('animation-timeline', 'scroll()')) {
      const animatedElements = document.querySelectorAll(selector);

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
      return;
    }

    const trackSections = document.querySelectorAll('.track-section');
    if (trackSections.length === 0) {
      return;
    }

    const navLinks = document.querySelectorAll('.track-progress-nav-link');
    let currentActiveSection = null;

    function updateProgressBar() {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollableHeight = documentHeight - windowHeight;
      const progress = scrollableHeight > 0
        ? Math.min(100, Math.max(0, (scrollTop / scrollableHeight) * 100))
        : 0;

      progressBar.style.width = progress + '%';
      progressBar.setAttribute('aria-valuenow', Math.round(progress));
    }

    function setActiveSection(activeSection) {
      if (activeSection === currentActiveSection) return;
      currentActiveSection = activeSection;

      navLinks.forEach(function (link) {
        const isActive = link.getAttribute('href') === '#' + activeSection;
        link.classList.toggle('active', isActive);
      });
    }

    if ('IntersectionObserver' in window) {
      const visibleSections = new Map();

      trackSectionObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            visibleSections.set(entry.target.id, entry.intersectionRatio);
          } else {
            visibleSections.delete(entry.target.id);
          }
        });

        if (visibleSections.size === 0) {
          return;
        }

        let bestId = null;
        let bestRatio = -1;
        visibleSections.forEach(function (ratio, id) {
          if (ratio >= bestRatio) {
            bestRatio = ratio;
            bestId = id;
          }
        });

        if (bestId) {
          setActiveSection(bestId);
        }
      }, {
        root: null,
        rootMargin: '-20% 0px -60% 0px',
        threshold: [0, 0.25, 0.5, 0.75, 1]
      });

      trackSections.forEach(function (section) {
        if (section.id) {
          trackSectionObserver.observe(section);
        }
      });
    }

    let ticking = false;
    trackProgressHandler = function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(function () {
          updateProgressBar();
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', trackProgressHandler, { passive: true });
    updateProgressBar();
  }

  function init() {
    cleanup();

    setupHashFocus();
    setupDelegatedCodeCopy();
    setupLazyLoading();
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
    if (trackProgressHandler) {
      window.removeEventListener('scroll', trackProgressHandler);
      trackProgressHandler = null;
    }
    if (trackSectionObserver) {
      trackSectionObserver.disconnect();
      trackSectionObserver = null;
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
