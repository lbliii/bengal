/**
 * Bengal SSG - Lazy Library Loaders
 *
 * Conditionally loads heavy third-party libraries only when their
 * features are present on the page. This eliminates ~1MB+ of JavaScript
 * from pages that don't need diagrams, tables, or graphs.
 *
 * Libraries handled:
 * - Mermaid.js (~930KB) - Diagram rendering
 * - D3.js (~92KB) - Graph visualizations
 * - Tabulator (~100KB) - Interactive data tables
 */

(function () {
    'use strict';

    /**
     * Helper to dynamically load a script
     * @param {string} src - Script URL
     * @param {function} [onload] - Callback after load
     * @returns {HTMLScriptElement}
     */
    function loadScript(src, onload) {
        var script = document.createElement('script');
        script.src = src;
        if (onload) {
            script.onload = onload;
        }
        document.head.appendChild(script);
        return script;
    }

    /**
     * Get asset URL using Bengal's asset_url pattern
     * Reads from a data attribute set by the template
     */
    function getAssetBase() {
        var meta = document.querySelector('meta[name="bengal:asset_base"]');
        return meta ? meta.getAttribute('content') : '/assets';
    }

    var assetBase = getAssetBase();

    /**
     * Tabulator (~100KB) - Only load if data tables exist
     */
    function loadTabulator() {
        if (!document.querySelector('.bengal-data-table-wrapper')) return;

        loadScript(assetBase + '/js/tabulator.min.js', function () {
            loadScript(assetBase + '/js/data-table.js');
        });
    }

    /**
     * Mermaid.js (~930KB) - Only load if .mermaid elements exist
     */
    function loadMermaid() {
        if (!document.querySelector('.mermaid')) return;

        loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js', function () {
            // Load support scripts sequentially: toolbar first, then theme
            loadScript(assetBase + '/js/mermaid-toolbar.js', function () {
                loadScript(assetBase + '/js/mermaid-theme.js');
            });
        });
    }

    /**
     * D3.js (~92KB) - Only load if graph elements exist
     */
    function loadD3() {
        if (!document.querySelector('.graph-minimap, .graph-contextual, [data-graph]')) return;

        loadScript('https://d3js.org/d3.v7.min.js', function () {
            // Dispatch event for graph scripts to listen for
            window.dispatchEvent(new Event('d3:ready'));

            // Load graph visualization scripts
            loadScript(assetBase + '/js/graph-minimap.js');
            loadScript(assetBase + '/js/graph-contextual.js');
        });
    }

    /**
     * Initialize all lazy loaders
     * Called when DOM is ready (defer script ensures this)
     */
    function init() {
        loadTabulator();
        loadMermaid();
        loadD3();
    }

    // Run immediately - defer attribute ensures DOM is ready
    init();

    // Export for manual triggering if needed
    window.BengalLazyLoaders = {
        loadTabulator: loadTabulator,
        loadMermaid: loadMermaid,
        loadD3: loadD3
    };

})();
