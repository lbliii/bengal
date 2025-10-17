(function () {
    'use strict';

    // Popular searches quick-fill
    function initPopularSearches() {
        document.querySelectorAll('.popular-search-link').forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const query = this.getAttribute('data-query');
                const searchInput = document.getElementById('search-input');
                if (!searchInput) return;
                searchInput.value = query;
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                searchInput.focus();
                setTimeout(() => {
                    const results = document.getElementById('search-results');
                    if (results) results.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            });
        });
    }

    // Initialize from URL hash
    function initHashQuery() {
        if (!window.location.hash) return;
        const query = decodeURIComponent(window.location.hash.substring(1));
        if (!query) return;
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;
        setTimeout(() => {
            searchInput.value = query;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        }, 500);
    }

    function init() {
        initPopularSearches();
        initHashQuery();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
