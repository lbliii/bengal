/**
 * Bengal SSG - Search Modal (Cmd/Ctrl+K)
 *
 * Command-palette style search modal with:
 * - Keyboard shortcuts (Cmd/Ctrl+K to open, Escape to close)
 * - Recent searches (localStorage)
 * - Keyboard navigation (↑↓ to navigate, Enter to select)
 * - Lazy loading of search index
 * - Focus trap for accessibility
 *
 * Dependencies:
 * - BengalSearch (search.js)
 * - BengalUtils (utils.js)
 */

(function () {
    'use strict';

    // Ensure dependencies
    if (!window.BengalUtils) {
        console.warn('BengalUtils not loaded - search-modal.js requires utils.js');
        return;
    }

    const { log, ready, debounce } = window.BengalUtils;

    // ====================================
    // Configuration
    // ====================================

    const CONFIG = {
        maxRecentSearches: 5,
        minQueryLength: 2,
        maxResults: 20,
        debounceDelay: 150,
        storageKey: 'bengal-recent-searches',
    };

    // ====================================
    // State
    // ====================================

    let modal = null;
    let input = null;
    let resultsList = null;
    let recentSection = null;
    let recentList = null;
    let noResults = null;
    let emptyState = null;
    let loading = null;
    let status = null;

    let isOpen = false;
    let selectedIndex = -1;
    let currentResults = [];
    let recentSearches = [];

    // ====================================
    // Initialization
    // ====================================

    function init() {
        modal = document.getElementById('search-modal');
        if (!modal) {
            log('Search modal not found - modal disabled in config?');
            return;
        }

        // Cache DOM elements
        input = document.getElementById('search-modal-input');
        resultsList = document.getElementById('search-modal-results-list');
        recentSection = document.getElementById('search-modal-recent');
        recentList = document.getElementById('search-modal-recent-list');
        noResults = document.getElementById('search-modal-no-results');
        emptyState = document.getElementById('search-modal-empty');
        loading = document.getElementById('search-modal-loading');
        status = document.getElementById('search-modal-status');

        // Load recent searches from localStorage
        loadRecentSearches();

        // Bind event handlers
        bindEvents();

        log('Search modal initialized');
    }

    function bindEvents() {
        // Global keyboard shortcut (Cmd/Ctrl + K)
        document.addEventListener('keydown', handleGlobalKeydown);

        // Modal-specific events
        modal.addEventListener('keydown', handleModalKeydown);
        modal.addEventListener('click', handleModalClick);

        // Input events
        input.addEventListener('input', debounce(handleInput, CONFIG.debounceDelay));
        input.addEventListener('focus', handleInputFocus);

        // Close buttons
        document.querySelectorAll('[data-close-modal]').forEach(el => {
            el.addEventListener('click', closeModal);
        });

        // Clear recent searches
        const clearRecentBtn = document.getElementById('clear-recent-searches');
        if (clearRecentBtn) {
            clearRecentBtn.addEventListener('click', clearRecentSearches);
        }

        // Search trigger buttons (nav and standalone)
        const triggers = document.querySelectorAll('#search-trigger, #nav-search-trigger, .nav-search-trigger');
        triggers.forEach(trigger => {
            trigger.addEventListener('click', openModal);
        });

        // Handle search index ready
        window.addEventListener('searchIndexLoaded', () => {
            if (loading) loading.style.display = 'none';
        });
    }

    // ====================================
    // Modal Control
    // ====================================

    function openModal() {
        if (isOpen) return;

        modal.showModal();
        isOpen = true;
        selectedIndex = -1;

        // Focus input
        requestAnimationFrame(() => {
            input.focus();
            input.select();
        });

        // Show recent searches if no query
        if (!input.value.trim()) {
            showRecentSearches();
        }

        // Trigger search index load if not already loaded
        if (window.BengalSearch && !window.BengalSearch.isLoaded()) {
            loading.style.display = 'flex';
            window.BengalSearch.load();
        }

        // Add body class to prevent scrolling
        document.body.classList.add('search-modal-open');

        log('Search modal opened');
    }

    function closeModal() {
        if (!isOpen) return;

        modal.close();
        isOpen = false;
        selectedIndex = -1;
        currentResults = [];

        // Clear input
        input.value = '';

        // Reset UI
        hideResults();
        showEmptyState();

        // Remove body class
        document.body.classList.remove('search-modal-open');

        log('Search modal closed');
    }

    // ====================================
    // Keyboard Handling
    // ====================================

    function handleGlobalKeydown(e) {
        // Cmd/Ctrl + K to open
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            if (isOpen) {
                input.focus();
                input.select();
            } else {
                openModal();
            }
        }

        // Also support "/" to open search (common pattern)
        if (e.key === '/' && !isOpen && !isInputElement(e.target)) {
            e.preventDefault();
            openModal();
        }
    }

    function handleModalKeydown(e) {
        switch (e.key) {
            case 'Escape':
                e.preventDefault();
                closeModal();
                break;

            case 'ArrowDown':
                e.preventDefault();
                navigateResults(1);
                break;

            case 'ArrowUp':
                e.preventDefault();
                navigateResults(-1);
                break;

            case 'Enter':
                e.preventDefault();
                selectResult();
                break;

            case 'Tab':
                // Trap focus within modal
                handleTabKey(e);
                break;
        }
    }

    function handleTabKey(e) {
        const focusableElements = modal.querySelectorAll(
            'input, button, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
        } else {
            if (document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    }

    function isInputElement(element) {
        const tagName = element.tagName.toLowerCase();
        return tagName === 'input' || tagName === 'textarea' || element.isContentEditable;
    }

    // ====================================
    // Search Handling
    // ====================================

    function handleInput(e) {
        const query = e.target.value.trim();

        if (query.length < CONFIG.minQueryLength) {
            hideResults();
            showRecentSearches();
            return;
        }

        performSearch(query);
    }

    function handleInputFocus() {
        if (!input.value.trim()) {
            showRecentSearches();
        }
    }

    function performSearch(query) {
        if (!window.BengalSearch || !window.BengalSearch.isLoaded()) {
            log('Search index not loaded yet');
            loading.style.display = 'flex';
            return;
        }

        loading.style.display = 'none';

        // Perform search
        const results = window.BengalSearch.search(query);
        currentResults = results.slice(0, CONFIG.maxResults);

        // Update UI
        displayResults(currentResults, query);

        // Update status for screen readers
        updateStatus(`${currentResults.length} results found`);
    }

    function displayResults(results, query) {
        // Hide other sections
        hideRecentSearches();
        hideEmptyState();

        if (results.length === 0) {
            showNoResults(query);
            return;
        }

        hideNoResults();
        resultsList.innerHTML = '';
        selectedIndex = -1;

        // Group results by autodoc status
        const { docs, api } = groupByAutodoc(results);

        // Track global index for keyboard navigation
        let globalIndex = 0;

        // Documentation section (always expanded, shown first)
        if (docs.length > 0) {
            const docsSection = createResultSection('Documentation', docs, query, false, globalIndex);
            resultsList.appendChild(docsSection);
            globalIndex += docs.length;
        }

        // API Reference section (collapsed by default)
        if (api.length > 0) {
            const apiSection = createResultSection(`API Reference (${api.length})`, api, query, true, globalIndex);
            resultsList.appendChild(apiSection);
        }

        resultsList.parentElement.style.display = 'block';
    }

    /**
     * Group results by autodoc status
     */
    function groupByAutodoc(results) {
        const docs = [];
        const api = [];

        results.forEach(result => {
            if (result.isAutodoc) {
                api.push(result);
            } else {
                docs.push(result);
            }
        });

        return { docs, api };
    }

    /**
     * Create a result section with optional collapse
     */
    function createResultSection(title, items, query, collapsed, startIndex) {
        const section = document.createElement('div');
        section.className = 'search-modal__result-section';

        // Section header
        const header = document.createElement('div');
        header.className = 'search-modal__section-header';
        if (collapsed) {
            header.classList.add('search-modal__section-header--collapsible');
        }
        header.innerHTML = `
            <span class="search-modal__section-title">${title}</span>
            ${collapsed ? '<span class="search-modal__section-toggle" aria-hidden="true">▶</span>' : ''}
        `;

        // Items container
        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'search-modal__section-items';
        if (collapsed) {
            itemsContainer.style.display = 'none';
            itemsContainer.setAttribute('aria-hidden', 'true');
        }

        // Render items with global index for keyboard nav
        items.forEach((result, localIndex) => {
            const globalIdx = startIndex + localIndex;
            const item = createResultItem(result, globalIdx, query);

            // Add API badge for autodoc items
            if (result.isAutodoc) {
                const badge = document.createElement('span');
                badge.className = 'search-modal__autodoc-badge';
                badge.textContent = 'API';
                const contentEl = item.querySelector('.search-modal__result-content');
                if (contentEl) {
                    contentEl.appendChild(badge);
                }
            }

            itemsContainer.appendChild(item);
        });

        // Toggle behavior for collapsed sections
        if (collapsed) {
            header.style.cursor = 'pointer';
            header.setAttribute('role', 'button');
            header.setAttribute('aria-expanded', 'false');
            header.setAttribute('tabindex', '0');

            const toggleSection = () => {
                const isHidden = itemsContainer.style.display === 'none';
                itemsContainer.style.display = isHidden ? 'block' : 'none';
                itemsContainer.setAttribute('aria-hidden', !isHidden);
                header.querySelector('.search-modal__section-toggle').textContent = isHidden ? '▼' : '▶';
                header.setAttribute('aria-expanded', isHidden);
            };

            header.addEventListener('click', toggleSection);
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleSection();
                }
            });
        }

        section.appendChild(header);
        section.appendChild(itemsContainer);
        return section;
    }

    function createResultItem(result, index, query) {
        const item = document.createElement('div');
        item.className = 'search-modal__result-item';
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', 'false');
        item.setAttribute('data-index', index);

        // Build HTML
        const href = result.href || result.uri || result.url;
        const title = result.highlightedTitle || result.title || 'Untitled';
        // Prefer frontmatter description over generated excerpt
        const description = result.description || result.highlightedExcerpt || result.excerpt || '';
        const section = result.section || '';

        item.innerHTML = `
      <a href="${href}" class="search-modal__result-link" tabindex="-1">
        <div class="search-modal__result-content">
          <span class="search-modal__result-title">${title}</span>
          ${section ? `<span class="search-modal__result-section">${section}</span>` : ''}
        </div>
        ${description ? `<p class="search-modal__result-excerpt">${description}</p>` : ''}
      </a>
    `;

        // Click handler
        item.addEventListener('click', (e) => {
            e.preventDefault();
            selectedIndex = index;
            selectResult();
        });

        return item;
    }

    // ====================================
    // Result Navigation
    // ====================================

    function navigateResults(direction) {
        const items = getNavigableItems();
        if (items.length === 0) return;

        // Remove previous selection
        if (selectedIndex >= 0 && selectedIndex < items.length) {
            items[selectedIndex].classList.remove('search-modal__result-item--selected');
            items[selectedIndex].setAttribute('aria-selected', 'false');
        }

        // Calculate new index
        selectedIndex += direction;
        if (selectedIndex < 0) selectedIndex = items.length - 1;
        if (selectedIndex >= items.length) selectedIndex = 0;

        // Apply new selection
        const selectedItem = items[selectedIndex];
        selectedItem.classList.add('search-modal__result-item--selected');
        selectedItem.setAttribute('aria-selected', 'true');

        // Scroll into view
        selectedItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });

        // Update status for screen readers
        const title = selectedItem.querySelector('.search-modal__result-title');
        if (title) {
            updateStatus(`${title.textContent}, ${selectedIndex + 1} of ${items.length}`);
        }
    }

    function selectResult() {
        const query = input.value.trim();
        const items = getNavigableItems();

        // If no selection made with arrow keys, go to search page with query
        if (selectedIndex < 0) {
            if (query) {
                goToSearchPage(query);
            }
            return;
        }

        // Navigate to selected result
        if (selectedIndex >= 0 && selectedIndex < items.length) {
            const selectedItem = items[selectedIndex];
            const link = selectedItem.querySelector('a');

            if (link) {
                // Save to recent searches
                if (query) {
                    addRecentSearch(query, link.href, selectedItem.querySelector('.search-modal__result-title')?.textContent || query);
                }

                // Navigate
                closeModal();
                window.location.href = link.href;
            }
        }
    }

    /**
     * Navigate to the full search page with query
     */
    function goToSearchPage(query) {
        // Get baseurl for proper URL construction
        let baseurl = '';
        try {
            const m = document.querySelector('meta[name="bengal:baseurl"]');
            baseurl = (m && m.getAttribute('content')) || '';
        } catch (e) { /* no-op */ }

        baseurl = baseurl.replace(/\/$/, '');
        const searchUrl = `${baseurl}/search/?q=${encodeURIComponent(query)}`;

        closeModal();
        window.location.href = searchUrl;
    }

    function getNavigableItems() {
        // Get items from either results or recent searches
        const resultItems = resultsList.querySelectorAll('.search-modal__result-item');
        const recentItems = recentList.querySelectorAll('.search-modal__recent-item');

        if (resultItems.length > 0) {
            return Array.from(resultItems);
        }
        if (recentSection.style.display !== 'none') {
            return Array.from(recentItems);
        }
        return [];
    }

    // ====================================
    // Recent Searches
    // ====================================

    function loadRecentSearches() {
        try {
            const stored = localStorage.getItem(CONFIG.storageKey);
            recentSearches = stored ? JSON.parse(stored) : [];
        } catch (e) {
            recentSearches = [];
        }
    }

    function saveRecentSearches() {
        try {
            localStorage.setItem(CONFIG.storageKey, JSON.stringify(recentSearches));
        } catch (e) {
            // localStorage not available
        }
    }

    function addRecentSearch(query, href, title) {
        // Remove duplicate if exists
        recentSearches = recentSearches.filter(s => s.query !== query);

        // Add to beginning
        recentSearches.unshift({ query, href, title, timestamp: Date.now() });

        // Limit size
        if (recentSearches.length > CONFIG.maxRecentSearches) {
            recentSearches = recentSearches.slice(0, CONFIG.maxRecentSearches);
        }

        saveRecentSearches();
    }

    function showRecentSearches() {
        if (recentSearches.length === 0) {
            hideRecentSearches();
            showEmptyState();
            return;
        }

        hideEmptyState();
        hideResults();
        hideNoResults();

        recentList.innerHTML = '';
        selectedIndex = -1;

        recentSearches.forEach((search, index) => {
            const item = document.createElement('li');
            item.className = 'search-modal__recent-item';
            item.setAttribute('role', 'option');
            item.setAttribute('aria-selected', 'false');
            item.setAttribute('data-index', index);

            item.innerHTML = `
        <a href="${search.href}" class="search-modal__recent-link" tabindex="-1">
          <svg class="search-modal__recent-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span class="search-modal__recent-text">${search.title || search.query}</span>
        </a>
        <button type="button" class="search-modal__recent-remove" data-query="${search.query}" title="Remove from recent">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;

            // Click to navigate
            item.querySelector('a').addEventListener('click', (e) => {
                closeModal();
            });

            // Remove button
            item.querySelector('.search-modal__recent-remove').addEventListener('click', (e) => {
                e.stopPropagation();
                removeRecentSearch(search.query);
            });

            recentList.appendChild(item);
        });

        recentSection.style.display = 'block';
    }

    function hideRecentSearches() {
        recentSection.style.display = 'none';
    }

    function removeRecentSearch(query) {
        recentSearches = recentSearches.filter(s => s.query !== query);
        saveRecentSearches();
        showRecentSearches();
    }

    function clearRecentSearches() {
        recentSearches = [];
        saveRecentSearches();
        showRecentSearches();
    }

    // ====================================
    // UI Helpers
    // ====================================

    function showNoResults(query) {
        hideResults();
        const queryEl = document.getElementById('search-modal-no-results-query');
        if (queryEl) queryEl.textContent = query;
        noResults.style.display = 'flex';
    }

    function hideNoResults() {
        noResults.style.display = 'none';
    }

    function showEmptyState() {
        emptyState.style.display = 'block';
    }

    function hideEmptyState() {
        emptyState.style.display = 'none';
    }

    function hideResults() {
        resultsList.innerHTML = '';
        resultsList.parentElement.style.display = 'none';
        selectedIndex = -1;
        currentResults = [];
    }

    function updateStatus(message) {
        if (status) {
            status.textContent = message;
        }
    }

    function handleModalClick(e) {
        // Close when clicking backdrop
        if (e.target.hasAttribute('data-close-modal')) {
            closeModal();
        }
    }

    // ====================================
    // Export API
    // ====================================

    window.BengalSearchModal = {
        open: openModal,
        close: closeModal,
        isOpen: () => isOpen,
    };

    // ====================================
    // Initialize
    // ====================================

    ready(init);

    log('Bengal Search Modal loaded');

})();
