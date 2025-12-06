/**
 * Bengal SSG - Lazy Library Loaders
 *
 * Conditionally loads heavy third-party libraries only when their
 * features are actually needed. Uses IntersectionObserver for
 * viewport-based loading to improve LCP and reduce initial bundle.
 *
 * Libraries handled:
 * - Mermaid.js (~930KB) - Diagram rendering (loads when diagrams near viewport)
 * - D3.js (~92KB) - Graph visualizations (loads when graphs near viewport)
 * - Tabulator (~100KB) - Interactive data tables (loads immediately if present)
 *
 * Performance optimizations:
 * - IntersectionObserver for viewport-based loading
 * - Single observer instance shared across element types
 * - Preloading of scripts after idle time
 */

(function () {
    'use strict';

    // Get asset URLs from template-injected config
    var assets = window.BENGAL_LAZY_ASSETS || {};

    // Track loaded libraries to prevent duplicate loads
    var loaded = {
        mermaid: false,
        d3: false,
        tabulator: false
    };

    // Track pending loads to prevent race conditions
    var pending = {
        mermaid: false,
        d3: false
    };

    /**
     * Helper to dynamically load a script
     * @param {string} src - Script URL
     * @param {function} [onload] - Callback after load
     * @param {object} [options] - Script options (async, defer, etc.)
     */
    function loadScript(src, onload, options) {
        options = options || {};
        var script = document.createElement('script');
        script.src = src;
        if (options.async !== false) script.async = true;
        if (onload) script.onload = onload;
        script.onerror = function() {
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
        var link = document.createElement('link');
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

        pending.mermaid = true;
        loaded.mermaid = true;

        loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js', initMermaid);
    }

    /**
     * Initialize D3-dependent graphs once loaded
     */
    function initD3Graphs() {
        // Dispatch event for graph scripts
        window.dispatchEvent(new Event('d3:ready'));

        // Load graph visualization scripts
        if (assets.graphMinimap) loadScript(assets.graphMinimap);
        if (assets.graphContextual) loadScript(assets.graphContextual);
    }

    /**
     * Load D3.js (~92KB) - Deferred until graphs near viewport
     */
    function loadD3() {
        if (loaded.d3 || pending.d3) return;

        pending.d3 = true;
        loaded.d3 = true;

        loadScript('https://d3js.org/d3.v7.min.js', initD3Graphs);
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
            if (document.querySelector('.graph-minimap, .graph-contextual, [data-graph]')) loadD3();
            return;
        }

        // Single shared observer for all lazy-loaded elements
        // rootMargin: Load when within 200px of viewport (anticipate scroll)
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (!entry.isIntersecting) return;

                var el = entry.target;

                // Determine which library to load based on element class
                if (el.classList.contains('mermaid')) {
                    loadMermaid();
                } else if (el.classList.contains('graph-minimap') ||
                           el.classList.contains('graph-contextual') ||
                           el.hasAttribute('data-graph')) {
                    loadD3();
                }

                // Stop observing this element
                observer.unobserve(el);
            });
        }, {
            rootMargin: '200px 0px', // Load 200px before entering viewport
            threshold: 0
        });

        // Observe all mermaid diagrams
        document.querySelectorAll('.mermaid').forEach(function(el) {
            observer.observe(el);
        });

        // Observe all graph elements
        document.querySelectorAll('.graph-minimap, .graph-contextual, [data-graph]').forEach(function(el) {
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
        var scheduleIdle = window.requestIdleCallback || function(cb) {
            return setTimeout(cb, 2000);
        };

        scheduleIdle(function() {
            // Only preload if elements exist on page (will be needed eventually)
            if (document.querySelector('.mermaid') && !loaded.mermaid) {
                preloadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js');
            }
            if (document.querySelector('.graph-minimap, .graph-contextual, [data-graph]') && !loaded.d3) {
                preloadScript('https://d3js.org/d3.v7.min.js');
            }
        }, { timeout: 3000 });
    }

    // Initialize all loaders
    loadTabulator(); // Tables load immediately (typically above-fold)
    setupIntersectionObserver(); // Mermaid & D3 load on scroll
    schedulePreloads(); // Hint browser to preload during idle

    // Export for debugging
    window.BENGAL_LAZY_LOADERS = {
        loadMermaid: loadMermaid,
        loadD3: loadD3,
        loadTabulator: loadTabulator,
        loaded: loaded
    };

})();
