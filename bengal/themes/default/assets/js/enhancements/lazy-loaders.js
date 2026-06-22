/**
 * Bengal SSG - Lazy Library Loaders
 *
 * Conditionally loads heavy third-party libraries only when their
 * features are actually needed. Uses IntersectionObserver for
 * viewport-based loading to improve LCP and reduce initial bundle.
 *
 * Capability vendor scripts are configured via window.BENGAL_CAPABILITY_LOADERS
 * (registry-driven, #585). Tabulator remains a theme-local lazy asset.
 */

(function () {
    'use strict';

    const assets = window.BENGAL_LAZY_ASSETS || {};
    const capabilityLoaders = window.BENGAL_CAPABILITY_LOADERS || [];

    const loaded = { tabulator: false };
    const pending = {};

    for (const spec of capabilityLoaders) {
        loaded[spec.key] = false;
        pending[spec.key] = false;
    }

    function loadScript(src, onload, options = {}) {
        const script = document.createElement('script');
        script.src = src;
        if (options.integrity) {
            script.integrity = options.integrity;
            script.crossOrigin = 'anonymous';
        }
        if (options.async !== false) script.async = true;
        if (onload) script.onload = onload;
        script.onerror = () => {
            console.warn('[Bengal] Failed to load script:', src);
        };
        document.head.appendChild(script);
    }

    function preloadScript(src) {
        if (!src) return;
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'script';
        link.href = src;
        document.head.appendChild(link);
    }

    function loadTabulator() {
        if (loaded.tabulator) return;
        if (!document.querySelector('.bengal-data-table-wrapper')) return;
        if (!assets.tabulator) return;

        loaded.tabulator = true;
        loadScript(assets.tabulator, function () {
            if (assets.dataTable) loadScript(assets.dataTable);
        });
    }

    function loadCompanions(companions, index = 0) {
        if (!companions || index >= companions.length) return;
        loadScript(companions[index], () => loadCompanions(companions, index + 1));
    }

    function loadCapability(spec) {
        if (!spec || loaded[spec.key] || pending[spec.key]) return;
        if (!spec.script) return;

        pending[spec.key] = true;
        loaded[spec.key] = true;

        loadScript(spec.script, () => loadCompanions(spec.companions || []), {
            integrity: spec.integrity || undefined,
        });
    }

    function setupIntersectionObserver() {
        if (!capabilityLoaders.length) return;

        if (!('IntersectionObserver' in window)) {
            for (const spec of capabilityLoaders) {
                if (spec.selector && document.querySelector(spec.selector)) {
                    loadCapability(spec);
                }
            }
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;

                const el = entry.target;
                for (const spec of capabilityLoaders) {
                    if (spec.selector && el.matches(spec.selector)) {
                        loadCapability(spec);
                    }
                }

                observer.unobserve(el);
            });
        }, {
            rootMargin: '200px 0px',
            threshold: 0
        });

        const selectors = capabilityLoaders
            .map((spec) => spec.selector)
            .filter(Boolean)
            .join(', ');

        if (selectors) {
            document.querySelectorAll(selectors).forEach((el) => observer.observe(el));
        }

        window.BENGAL_LAZY_OBSERVER = observer;
    }

    function schedulePreloads() {
        const scheduleIdle = window.requestIdleCallback || ((cb) => setTimeout(cb, 2000));

        scheduleIdle(() => {
            for (const spec of capabilityLoaders) {
                if (!spec.selector || !spec.script || loaded[spec.key]) continue;
                if (document.querySelector(spec.selector)) {
                    preloadScript(spec.script);
                }
            }
        }, { timeout: 3000 });
    }

    loadTabulator();
    setupIntersectionObserver();
    schedulePreloads();

    window.BENGAL_LAZY_LOADERS = {
        loadCapability,
        loadTabulator,
        loaded
    };

})();
