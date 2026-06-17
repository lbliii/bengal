/**
 * Bengal SSG - Lazy Library Loaders
 *
 * Conditionally loads heavy third-party libraries only when their
 * features are actually needed. Uses IntersectionObserver for
 * viewport-based loading to improve LCP and reduce initial bundle.
 *
 * Libraries handled:
 * - Mermaid.js (~930KB) - Diagram rendering (loads when diagrams near viewport)
 * - Tabulator (~100KB) - Interactive data tables (loads immediately if present)
 *
 * Note: the knowledge-graph minimap/explorer are dependency-free (no D3) and
 * self-load via graph-contextual.js / the /graph/ page, so they are not handled
 * here.
 *
 * Performance optimizations:
 * - IntersectionObserver for viewport-based loading
 * - Single observer instance shared across element types
 * - Preloading of scripts after idle time
 */

(function () {
    'use strict';

    // Get asset URLs from template-injected config
    const assets = window.BENGAL_LAZY_ASSETS || {};

    // Track loaded libraries to prevent duplicate loads
    const loaded = {
        mermaid: false,
        tabulator: false
    };

    // Track pending loads to prevent race conditions
    const pending = {
        mermaid: false
    };

    /**
     * Helper to dynamically load a script
     * @param {string} src - Script URL
     * @param {function} [onload] - Callback after load
     * @param {object} [options] - Script options (async, defer, etc.)
     */
    function loadScript(src, onload, options = {}) {
        const script = document.createElement('script');
        script.src = src;
        if (options.async !== false) script.async = true;
        if (onload) script.onload = onload;
        script.onerror = () => {
            console.warn('[Bengal] Failed to load script:', src);
        };
        document.head.appendChild(script);
    }

    /**
     * Preload a script (hint to browser without blocking)
     * @param {string} src - Script URL
     */
    function preloadScript(src) {
        if (!src) return;
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'script';
        link.href = src;
        document.head.appendChild(link);
    }

    /**
     * Tabulator (~100KB) - Only load if data tables exist
     * Loads immediately since tables are typically above-the-fold
     */
    function loadTabulator() {
        if (loaded.tabulator) return;
        if (!document.querySelector('.bengal-data-table-wrapper')) return;
        if (!assets.tabulator) return;

        loaded.tabulator = true;
        loadScript(assets.tabulator, function () {
            if (assets.dataTable) loadScript(assets.dataTable);
        });
    }

    /**
     * Initialize Mermaid once loaded
     */
    function initMermaid() {
        if (typeof mermaid !== 'undefined') {
            // Mermaid will auto-initialize elements with class="mermaid"
            // Load support scripts sequentially
            if (assets.mermaidToolbar) {
                loadScript(assets.mermaidToolbar, function () {
                    if (assets.mermaidTheme) loadScript(assets.mermaidTheme);
                });
            }
        }
    }

    /**
     * Load Mermaid.js (~930KB) - Deferred until diagrams near viewport
     */
    function loadMermaid() {
        if (loaded.mermaid || pending.mermaid) return;
        if (!assets.mermaid) return;

        pending.mermaid = true;
        loaded.mermaid = true;

        loadScript(assets.mermaid, initMermaid);
    }

    /**
     * IntersectionObserver-based lazy loading
     * Only loads libraries when their content is about to enter viewport
     */
    function setupIntersectionObserver() {
        // Check for IntersectionObserver support
        if (!('IntersectionObserver' in window)) {
            // Fallback: load immediately for older browsers
            if (document.querySelector('.mermaid')) loadMermaid();
            return;
        }

        // Single shared observer for all lazy-loaded elements
        // rootMargin: Load when within 200px of viewport (anticipate scroll)
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;

                const el = entry.target;

                // Determine which library to load based on element class
                if (el.classList.contains('mermaid')) {
                    loadMermaid();
                }

                // Stop observing this element
                observer.unobserve(el);
            });
        }, {
            rootMargin: '200px 0px', // Load 200px before entering viewport
            threshold: 0
        });

        // Observe all mermaid diagrams
        document.querySelectorAll('.mermaid').forEach((el) => {
            observer.observe(el);
        });

        // Store observer reference for cleanup
        window.BENGAL_LAZY_OBSERVER = observer;
    }

    /**
     * Preload heavy scripts during idle time
     * This hints to the browser to fetch scripts in the background
     * without blocking the main thread or affecting LCP
     */
    function schedulePreloads() {
        // Use requestIdleCallback if available, otherwise setTimeout
        const scheduleIdle = window.requestIdleCallback || ((cb) => setTimeout(cb, 2000));

        scheduleIdle(() => {
            // Only preload if self-hosted asset URLs are configured (#550)
            if (document.querySelector('.mermaid') && !loaded.mermaid && assets.mermaid) {
                preloadScript(assets.mermaid);
            }
        }, { timeout: 3000 });
    }

    // Initialize all loaders
    loadTabulator(); // Tables load immediately (typically above-fold)
    setupIntersectionObserver(); // Mermaid loads on scroll
    schedulePreloads(); // Hint browser to preload during idle

    // Export for debugging
    window.BENGAL_LAZY_LOADERS = {
        loadMermaid: loadMermaid,
        loadTabulator: loadTabulator,
        loaded: loaded
    };

})();
