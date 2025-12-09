/**
 * Bengal SSG Default Theme
 * Shared Utilities
 *
 * Common utilities used across multiple theme JavaScript modules.
 * Load this before other modules that depend on it.
 */

(function () {
  'use strict';

  // Debug mode flag (set via window.Bengal.debug = true)
  const DEBUG = (window.Bengal && window.Bengal.debug) || false;

  /**
   * Debug logging helper
   * Only logs if DEBUG is enabled
   */
  function log(...args) {
    if (DEBUG) {
      console.log('[Bengal]', ...args);
    }
  }

  /**
   * Copy text to clipboard with fallback
   * @param {string} text - Text to copy
   * @returns {Promise<void>}
   */
  async function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (err) {
        log('Clipboard API failed, using fallback:', err);
        // Fall through to fallback
      }
    }

    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.top = '0';
    textarea.style.left = '0';
    textarea.style.opacity = '0';
    textarea.style.pointerEvents = 'none';
    document.body.appendChild(textarea);

    try {
      textarea.select();
      textarea.setSelectionRange(0, text.length); // For iOS
      const successful = document.execCommand('copy');
      if (!successful) {
        throw new Error('execCommand copy failed');
      }
    } finally {
      document.body.removeChild(textarea);
    }
  }

  /**
   * Throttle function calls using requestAnimationFrame
   * @param {Function} callback - Function to throttle
   * @returns {Function} Throttled function
   */
  function throttleScroll(callback) {
    let ticking = false;
    return function throttled(...args) {
      const context = this;
      if (!ticking) {
        window.requestAnimationFrame(() => {
          callback.apply(context, args);
          ticking = false;
        });
        ticking = true;
      }
    };
  }

  /**
   * Debounce function calls
   * @param {Function} func - Function to debounce
   * @param {number} wait - Wait time in milliseconds
   * @returns {Function} Debounced function
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const context = this;
      const later = () => {
        clearTimeout(timeout);
        func.apply(context, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * DOM ready helper
   * @param {Function} callback - Function to call when DOM is ready
   */
  function ready(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
      callback();
    }
  }

  /**
   * Check if URL is external
   * @param {string} href - URL to check
   * @returns {boolean} True if external
   */
  function isExternalUrl(href) {
    // Skip anchor links, mailto, tel, etc.
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
      return false;
    }

    // Relative paths (starting with / or ./ or ../) are always internal
    if (href.startsWith('/') || href.startsWith('./') || href.startsWith('../')) {
      return false;
    }

    try {
      // Parse URL - if href is relative, resolve it relative to current page
      const url = new URL(href, window.location.href);
      const currentOrigin = window.location.origin;

      // Compare origins - must match exactly (including protocol)
      return url.origin !== currentOrigin;
    } catch (e) {
      // Invalid URL or parsing error - assume internal to be safe
      return false;
    }
  }

  /**
   * Escape regex special characters
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * Scroll manager for consolidating scroll listeners
   */
  const scrollManager = {
    listeners: new Set(),
    handler: null,

    add(callback) {
      this.listeners.add(callback);
      if (this.listeners.size === 1) {
        this.handler = throttleScroll(() => {
          this.listeners.forEach(cb => {
            try {
              cb();
            } catch (err) {
              log('Scroll listener error:', err);
            }
          });
        });
        window.addEventListener('scroll', this.handler, { passive: true });
      }
    },

    remove(callback) {
      this.listeners.delete(callback);
      if (this.listeners.size === 0 && this.handler) {
        window.removeEventListener('scroll', this.handler);
        this.handler = null;
      }
    }
  };

  /**
   * Focus trap utility for modals/dropdowns
   * @param {HTMLElement} container - Container element
   * @returns {Function} Keydown handler
   */
  function createFocusTrap(container) {
    const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    return function handleKeydown(e) {
      if (e.key !== 'Tab') return;

      const focusables = Array.from(container.querySelectorAll(FOCUSABLE));
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (e.shiftKey) {
        // Shift+Tab
        if (active === first || !container.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
  }

  /**
   * Load icon SVG content (for use in JavaScript)
   * @param {string} iconName - Icon name (e.g., "close", "enlarge")
   * @returns {Promise<string>} SVG HTML string
   */
  async function loadIcon(iconName) {
    // Check if icon paths are available
    if (!window.BENGAL_ICONS || !window.BENGAL_ICONS[iconName]) {
      log('Icon not found:', iconName);
      return '';
    }

    const iconPath = window.BENGAL_ICONS[iconName];
    try {
      const response = await fetch(iconPath);
      if (!response.ok) {
        log('Failed to load icon:', iconName, response.status);
        return '';
      }
      const svgText = await response.text();
      // Ensure SVG uses currentColor for theme compatibility, but preserve 'none'
      return svgText.replace(/fill="(?!(?:none|transparent))[^"]*"/g, 'fill="currentColor"')
                    .replace(/stroke="(?!(?:none|transparent))[^"]*"/g, 'stroke="currentColor"');
    } catch (err) {
      log('Error loading icon:', iconName, err);
      return '';
    }
  }

  // Export utilities
  window.BengalUtils = {
    log,
    copyToClipboard,
    throttleScroll,
    debounce,
    ready,
    isExternalUrl,
    escapeRegex,
    scrollManager,
    createFocusTrap,
    loadIcon
  };

  log('Utilities initialized');
})();
