/**
 * Bengal SSG - Progressive Enhancement Loader
 *
 * Central enhancement registry with auto-discovery and lazy loading.
 * Provides a unified pattern for declaring enhancements via data-bengal attributes.
 *
 * Philosophy: "Layered enhancement — HTML that works, CSS that delights, JS that elevates"
 *
 * Features:
 * - Unified data-bengal attribute for declaring enhancements
 * - Central registry with programmatic access
 * - Lazy-loading of enhancement scripts
 * - MutationObserver for dynamic content (configurable)
 * - Graceful degradation on errors
 *
 * @version 1.0.0
 * @see plan/active/rfc-progressive-enhancements.md
 */

(function() {
  'use strict';

  // Enhancement registry and state
  const REGISTRY = {};
  const ENHANCED = new WeakSet();
  const PENDING_LOADS = new Map();

  // Configuration with defaults
  const CONFIG = {
    debug: (window.Bengal && window.Bengal.debug) || false,
    watchDom: (window.Bengal && window.Bengal.watchDom !== false) || true,
    baseUrl: (window.Bengal && window.Bengal.enhanceBaseUrl) || '/assets/js/enhancements'
  };

  /**
   * Debug logging helper
   * @param {...any} args - Arguments to log
   */
  function log(...args) {
    if (CONFIG.debug) {
      console.log('[Bengal]', ...args);
    }
  }

  /**
   * Register an enhancement
   * @param {string} name - Enhancement name (matches data-bengal value)
   * @param {Function} init - Initialization function (element, options) => void
   * @param {Object} [options] - Registration options
   * @param {boolean} [options.override] - Allow overriding existing registration
   */
  function register(name, init, options = {}) {
    if (REGISTRY[name] && !options.override) {
      log(`Enhancement "${name}" already registered`);
      return false;
    }
    REGISTRY[name] = { init, options };
    log(`Registered enhancement: ${name}`);

    // If we were waiting for this enhancement, resolve pending elements
    if (PENDING_LOADS.has(name)) {
      const pendingElements = PENDING_LOADS.get(name);
      PENDING_LOADS.delete(name);
      pendingElements.forEach(el => applyEnhancement(el, REGISTRY[name]));
    }

    return true;
  }

  /**
   * Parse data attribute value (handle booleans, numbers, JSON)
   * @param {string} value - Raw attribute value
   * @returns {any} Parsed value
   */
  function parseValue(value) {
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (value === '') return true; // data-something with no value
    if (!isNaN(value) && value !== '') return Number(value);
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  /**
   * Extract options from data attributes
   * @param {HTMLElement} el - Element to extract options from
   * @returns {Object} Options object
   */
  function extractOptions(el) {
    const options = {};
    for (const [key, value] of Object.entries(el.dataset)) {
      // Skip bengal and enhanced attributes
      if (key !== 'bengal' && key !== 'enhanced' && key !== 'enhanceError') {
        options[key] = parseValue(value);
      }
    }
    return options;
  }

  /**
   * Apply an enhancement to an element
   * @param {HTMLElement} el - Element to enhance
   * @param {Object} enhancement - Enhancement definition
   */
  function applyEnhancement(el, enhancement) {
    if (ENHANCED.has(el)) return;

    try {
      const options = extractOptions(el);
      enhancement.init(el, options);
      ENHANCED.add(el);
      el.setAttribute('data-enhanced', 'true');
      log(`Enhanced: ${el.dataset.bengal}`, el);
    } catch (err) {
      console.error(`[Bengal] Enhancement error (${el.dataset.bengal}):`, err);
      el.setAttribute('data-enhance-error', 'true');
    }
  }

  /**
   * Lazy-load an enhancement script
   * @param {string} name - Enhancement name
   * @returns {Promise<void>}
   */
  async function loadEnhancement(name) {
    // Already loading this enhancement
    if (PENDING_LOADS.has(name)) {
      return;
    }

    const url = `${CONFIG.baseUrl}/${name}.js`;
    PENDING_LOADS.set(name, []);

    try {
      // Try dynamic import first (modern browsers)
      await import(url);
      log(`Loaded enhancement via import: ${name}`);
    } catch (err) {
      // Fallback to script tag for browsers without dynamic import
      return new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = () => {
          log(`Loaded enhancement via script tag: ${name}`);
          resolve();
        };
        script.onerror = () => {
          log(`Failed to load enhancement: ${name}`);
          PENDING_LOADS.delete(name);
          resolve(); // Don't reject - graceful degradation
        };
        document.head.appendChild(script);
      });
    }
  }

  /**
   * Enhance a single element
   * @param {HTMLElement} el - Element to enhance
   */
  function enhanceElement(el) {
    if (ENHANCED.has(el)) return;

    const name = el.dataset.bengal;
    if (!name) return;

    const enhancement = REGISTRY[name];
    if (enhancement) {
      applyEnhancement(el, enhancement);
    } else {
      // Track element for when enhancement loads
      if (!PENDING_LOADS.has(name)) {
        loadEnhancement(name);
        PENDING_LOADS.set(name, [el]);
      } else {
        PENDING_LOADS.get(name).push(el);
      }
    }
  }

  /**
   * Scan and enhance all elements with data-bengal
   * @param {HTMLElement|Document} [root=document] - Root element to scan
   */
  function enhanceAll(root = document) {
    const elements = root.querySelectorAll('[data-bengal]:not([data-enhanced])');
    elements.forEach(enhanceElement);
  }

  /**
   * Set up MutationObserver to watch for dynamic content
   * Debounced to prevent performance issues (especially with DevTools)
   */
  function setupDomWatcher() {
    if (!CONFIG.watchDom) return;

    // Debounce to batch rapid DOM changes (prevents DevTools-induced loops)
    let pendingNodes = [];
    let debounceTimer = null;

    function processPendingNodes() {
      if (pendingNodes.length === 0) return;

      // Process accumulated nodes
      const nodesToProcess = pendingNodes;
      pendingNodes = [];

      nodesToProcess.forEach((node) => {
        if (node.dataset && node.dataset.bengal) {
          enhanceElement(node);
        }
        enhanceAll(node);
      });
    }

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            pendingNodes.push(node);
          }
        });
      });

      // Debounce processing to batch rapid changes
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(processPendingNodes, 50);
    });

    observer.observe(document.body, { childList: true, subtree: true });
    log('DOM watcher initialized (debounced)');

    // Store reference for potential cleanup
    window.BENGAL_DOM_OBSERVER = observer;
  }

  /**
   * Initialize the enhancement system
   */
  function init() {
    // Enhance existing elements
    enhanceAll();

    // Watch for dynamic content
    setupDomWatcher();

    log('Enhancement system initialized');
  }

  // Auto-initialize when DOM is ready
  // Use setTimeout(0) to defer init until after all bundled scripts have executed.
  // This ensures enhancement registrations (which come later in the bundle) complete
  // before we scan for data-bengal elements, preventing unnecessary 404s from
  // lazy-loading files that are already bundled.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 0));
  } else {
    setTimeout(init, 0);
  }

  // Export API
  window.Bengal = window.Bengal || {};
  window.Bengal.enhance = {
    /**
     * Register an enhancement
     * @param {string} name - Enhancement name
     * @param {Function} init - Initialization function
     * @param {Object} [options] - Registration options
     */
    register,

    /**
     * Enhance all unenhanced elements
     * @param {HTMLElement|Document} [root] - Root element to scan
     */
    enhanceAll,

    /**
     * Enhance a single element
     * @param {HTMLElement} el - Element to enhance
     */
    enhanceElement,

    /**
     * List registered enhancements
     * @returns {string[]} Enhancement names
     */
    list: () => Object.keys(REGISTRY),

    /**
     * Get an enhancement definition
     * @param {string} name - Enhancement name
     * @returns {Object|undefined} Enhancement definition
     */
    get: (name) => REGISTRY[name],

    /**
     * Check if an element has been enhanced
     * @param {HTMLElement} el - Element to check
     * @returns {boolean}
     */
    isEnhanced: (el) => ENHANCED.has(el),

    /**
     * Configure the enhancement system
     * @param {Object} options - Configuration options
     */
    configure: (options) => {
      Object.assign(CONFIG, options);
    }
  };

  log('Bengal enhance API ready');

})();
