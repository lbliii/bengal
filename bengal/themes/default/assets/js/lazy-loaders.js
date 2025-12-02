/**
 * Bengal SSG - Lazy Library Loaders
 *
 * Conditionally loads heavy third-party libraries only when their
 * features are present on the page. URLs are injected by the template
 * via window.BENGAL_LAZY_ASSETS to support fingerprinted filenames.
 *
 * Libraries handled:
 * - Mermaid.js (~930KB) - Diagram rendering
 * - D3.js (~92KB) - Graph visualizations
 * - Tabulator (~100KB) - Interactive data tables
 */

(function () {
    'use strict';

    // Get asset URLs from template-injected config
    var assets = window.BENGAL_LAZY_ASSETS || {};

    /**
     * Helper to dynamically load a script
     * @param {string} src - Script URL
     * @param {function} [onload] - Callback after load
     */
    function loadScript(src, onload) {
        var script = document.createElement('script');
        script.src = src;
        if (onload) script.onload = onload;
        document.head.appendChild(script);
    }

    /**
     * Tabulator (~100KB) - Only load if data tables exist
     */
    function loadTabulator() {
        if (!document.querySelector('.bengal-data-table-wrapper')) return;
        if (!assets.tabulator) return;

        loadScript(assets.tabulator, function () {
            if (assets.dataTable) loadScript(assets.dataTable);
        });
    }

    /**
     * Mermaid.js (~930KB) - Only load if .mermaid elements exist
     */
    function loadMermaid() {
        if (!document.querySelector('.mermaid')) return;

        loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js', function () {
            // Load support scripts sequentially
            if (assets.mermaidToolbar) {
                loadScript(assets.mermaidToolbar, function () {
                    if (assets.mermaidTheme) loadScript(assets.mermaidTheme);
                });
            }
        });
    }

    /**
     * D3.js (~92KB) - Only load if graph elements exist
     */
    function loadD3() {
        if (!document.querySelector('.graph-minimap, .graph-contextual, [data-graph]')) return;

        loadScript('https://d3js.org/d3.v7.min.js', function () {
            // Dispatch event for graph scripts
            window.dispatchEvent(new Event('d3:ready'));

            // Load graph visualization scripts
            if (assets.graphMinimap) loadScript(assets.graphMinimap);
            if (assets.graphContextual) loadScript(assets.graphContextual);
        });
    }

    // Initialize all loaders
    loadTabulator();
    loadMermaid();
    loadD3();

})();
