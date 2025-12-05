/**
 * Bengal SSG - Smart Search Index Preloading
 *
 * Configurable preloading strategy for the search index:
 * - 'immediate': Load right away (best for small sites <100 pages)
 * - 'smart': Load on user intent signals (default, best for most sites)
 * - 'lazy': Only load when search is opened (best for large sites >500 pages)
 *
 * Configure via bengal.toml: search_preload = 'smart'
 */

(function () {
    'use strict';

    // Get preload mode from meta tag
    var metaEl = document.querySelector('meta[name="bengal:search_preload"]');
    var preloadMode = (metaEl && metaEl.getAttribute('content')) || 'smart';
    var preloadTriggered = false;

    /**
     * Trigger search index preload
     */
    function preloadSearch() {
        if (preloadTriggered || !window.BengalSearch) return;
        preloadTriggered = true;

        if (window.BengalUtils && window.BengalUtils.log) {
            window.BengalUtils.log('Preloading search index...');
        }
        window.BengalSearch.load();
    }

    /**
     * Set up smart preloading based on user intent signals
     */
    function setupSmartPreload() {
        // Preload on search link/button hover (user likely to search)
        var searchTriggers = document.querySelectorAll(
            'a[href$="/search/"], a[href*="search"], .nav-search-trigger, #nav-search-trigger'
        );
        searchTriggers.forEach(function (el) {
            el.addEventListener('mouseenter', preloadSearch, { once: true });
            el.addEventListener('focus', preloadSearch, { once: true });
        });

        // Preload if user presses Cmd/Ctrl (likely ⌘K)
        document.addEventListener('keydown', function (e) {
            if (e.metaKey || e.ctrlKey) {
                preloadSearch();
            }
        }, { once: true });
    }

    /**
     * Initialize preloading based on configured mode
     */
    function init() {
        if (preloadMode === 'immediate') {
            // Load right away (best for small sites <100 pages)
            preloadSearch();
        } else if (preloadMode === 'smart') {
            // Load on user intent signals (default, best for most sites)
            setupSmartPreload();
        }
        // 'lazy' mode: No preloading - index loads on first search
    }

    // Initialize when DOM is ready (defer ensures this)
    init();

    // Export for manual control if needed
    window.BengalSearchPreload = {
        trigger: preloadSearch
    };

})();
