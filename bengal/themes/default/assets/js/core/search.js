/**
 * Bengal SSG - Search Implementation (Consolidated)
 *
 * Merged from:
 * - search.js (core search functionality)
 * - search-modal.js (Cmd/Ctrl+K modal)
 * - search-page.js (search page functionality)
 * - search-preload.js (smart preloading)
 *
 * Using Lunr.js for client-side full-text search
 *
 * Features:
 * - Full-text search across all pages
 * - Filtering by section, type, tags, author
 * - Result transformation and highlighting
 * - Keyboard shortcuts (Cmd/Ctrl + K)
 * - Search modal (command-palette style)
 * - Search page with URL query support
 * - Smart index preloading
 * - Accessible with ARIA labels
 *
 * @requires utils.js
 * @requires bengal-enhance.js (for enhancement registration)
 */

(function () {
    'use strict';

    // ============================================================
    // Dependencies
    // ============================================================

    if (!window.BengalUtils) {
        console.error('[Bengal] utils.js required for search');
        return;
    }

    const { log, escapeRegex, ready, debounce } = window.BengalUtils;

    // ============================================================
    // Configuration
    // ============================================================

    const CONFIG = {
        indexUrl: null, // computed from meta tag when available
        prebuiltIndexUrl: null, // search-index.json (pre-built Lunr)
        minQueryLength: 2,
        maxResults: 50,
        excerptLength: 150,
        highlightClass: 'search-highlight',
        debounceDelay: 200,
        usePrebuilt: true, // Prefer pre-built index if available
        // Modal config
        maxRecentSearches: 5,
        modalDebounceDelay: 150,
        storageKey: 'bengal-recent-searches',
    };

    // ============================================================
    // State
    // ============================================================

    let searchIndex = null;
    let searchData = null;
    let isIndexLoaded = false;
    let isIndexLoading = false;
    let currentFilters = {
        section: null,
        type: null,
        tags: [],
        author: null,
    };

    // Modal state
    let modal = null;
    let modalInput = null;
    let resultsList = null;
    let recentSection = null;
    let recentList = null;
    let noResults = null;
    let emptyState = null;
    let loading = null;
    let status = null;
    let isModalOpen = false;
    let selectedIndex = -1;
    let currentResults = [];
    let recentSearches = [];

    // Preload state
    let preloadTriggered = false;

    // ============================================================
    // Index Loading & Building
    // ============================================================

    /**
     * Resolve base URL from meta tag
     */
    function resolveBaseUrl() {
        let baseurl = '';
        try {
            const m = document.querySelector('meta[name="bengal:baseurl"]');
            baseurl = (m && m.getAttribute('content')) || '';
        } catch (e) { /* no-op */ }
        return baseurl.replace(/\/$/, '');
    }

    /**
     * Build URL with baseurl prefix
     */
    function buildIndexUrl(filename, baseurl) {
        let url = '/' + filename;
        if (baseurl) {
            url = baseurl + url;
        }
        return url;
    }

    /**
     * Detect current version from meta tag or URL
     */
    function detectCurrentVersion() {
        // Meta tag (authoritative)
        const meta = document.querySelector('meta[name="bengal:version"]');
        if (meta) {
            return meta.getAttribute('content');
        }

        // Fallback: parse URL pattern /docs/v1/...
        const match = window.location.pathname.match(/\/docs\/(v\d+)\//);
        return match ? match[1] : null;
    }

    /**
     * Build versioned index URL
     */
    function buildVersionedIndexUrl(baseurl) {
        const version = detectCurrentVersion();

        if (!version) {
            // Unversioned or latest
            return buildIndexUrl('index.json', baseurl);
        }

        // Version-specific: /docs/v1/index.json
        return buildIndexUrl(`docs/${version}/index.json`, baseurl);
    }

    /**
     * Load search index - prefers pre-built index, falls back to runtime building
     */
    async function loadSearchIndex() {
        if (isIndexLoaded || isIndexLoading) return;

        isIndexLoading = true;

        try {
            const baseurl = resolveBaseUrl();

            // Try loading pre-built Lunr index first (faster)
            if (CONFIG.usePrebuilt) {
                const prebuiltLoaded = await tryLoadPrebuiltIndex(baseurl);
                if (prebuiltLoaded) {
                    // Set flags BEFORE dispatching event so handlers see correct state
                    isIndexLoaded = true;
                    isIndexLoading = false;

                    // Dispatch event for other components
                    window.dispatchEvent(new CustomEvent('searchIndexLoaded', {
                        detail: { pages: searchData.pages.length, prebuilt: true }
                    }));
                    return;
                }
            }

            // Fall back to loading index.json and building at runtime
            await loadAndBuildRuntimeIndex(baseurl);

            // Set flags BEFORE dispatching event so handlers see correct state
            isIndexLoaded = true;
            isIndexLoading = false;

            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('searchIndexLoaded', {
                detail: { pages: searchData.pages.length, prebuilt: false }
            }));

        } catch (error) {
            console.error('Failed to load search index:', error);
            isIndexLoading = false;

            // Dispatch error event
            window.dispatchEvent(new CustomEvent('searchIndexError', {
                detail: { error: error.message }
            }));
        }
    }

    /**
     * Try loading pre-built Lunr index (search-index.json)
     * Returns true if successful, false to fall back to runtime building
     *
     * Note: The meta tag is only emitted when the lunr Python package is installed
     * (pip install bengal[search]). If the tag is missing, we skip the fetch entirely
     * to avoid unnecessary 404s and fall back to runtime index building.
     */
    async function tryLoadPrebuiltIndex(baseurl) {
        try {
            // Only attempt pre-built index if meta tag exists (indicates lunr is installed)
            const metaTag = document.querySelector('meta[name="bengal:search_index_url"]');
            if (!metaTag) {
                log('Pre-built index not available (lunr not installed)');
                return false;
            }

            // Build versioned pre-built index URL
            const version = detectCurrentVersion();
            let prebuiltUrl = '';
            if (version) {
                // Version-specific: /docs/v1/search-index.json
                prebuiltUrl = buildIndexUrl(`docs/${version}/search-index.json`, baseurl);
            } else {
                // Use meta tag URL for latest/unversioned
                prebuiltUrl = metaTag.getAttribute('content') || '';
            }

            if (!prebuiltUrl) {
                return false;
            }

            const response = await fetch(prebuiltUrl);

            if (!response.ok) {
                log('Pre-built index not found, falling back to runtime build');
                return false;
            }

            const prebuiltData = await response.json();

            // Load pre-built index using lunr.Index.load()
            if (typeof lunr === 'undefined' || !lunr.Index) {
                log('Lunr.js not available for pre-built index');
                return false;
            }

            searchIndex = lunr.Index.load(prebuiltData);

            // Still need to load index.json for page data (pre-built index only has search index)
            const indexUrl = buildVersionedIndexUrl(baseurl);
            const dataResponse = await fetch(indexUrl);

            if (!dataResponse.ok) {
                throw new Error(`Failed to load page data: ${dataResponse.status}`);
            }

            const data = await dataResponse.json();

            if (!data || !Array.isArray(data.pages)) {
                throw new Error('Invalid page data structure');
            }

            searchData = data;

            log(`Search index loaded (pre-built): ${data.pages.length} pages`);

            return true;

        } catch (error) {
            log('Pre-built index load failed, falling back to runtime build:', error.message);
            return false;
        }
    }

    /**
     * Load index.json and build Lunr index at runtime (fallback)
     */
    async function loadAndBuildRuntimeIndex(baseurl) {
        // Prefer explicit meta index URL first
        let indexUrl = '';
        try {
            const m2 = document.querySelector('meta[name="bengal:index_url"]');
            indexUrl = (m2 && m2.getAttribute('content')) || '';
        } catch (e) { /* no-op */ }

        if (!indexUrl) {
            indexUrl = buildVersionedIndexUrl(baseurl);
        }

        const response = await fetch(indexUrl);
        if (!response.ok) {
            throw new Error(`Failed to load search index: ${response.status}`);
        }

        const data = await response.json();

        // Validate data structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid search index: expected object, got ' + typeof data);
        }

        if (!Array.isArray(data.pages)) {
            throw new Error('Invalid search index: missing or invalid "pages" array. Got: ' + typeof data.pages);
        }

        searchData = data;

        // Build Lunr index at runtime
        searchIndex = lunr(function () {
            // Configure reference field (use objectID if available, fallback to url)
            this.ref('objectID');

            // Configure fields with boost values (inspired by Algolia/MiloDoc weighting)
            this.field('title', { boost: 10 });
            this.field('description', { boost: 5 });
            this.field('content', { boost: 1 });
            this.field('tags', { boost: 3 });
            this.field('section', { boost: 2 });
            this.field('author', { boost: 2 });
            this.field('search_keywords', { boost: 8 });
            this.field('kind', { boost: 1 });  // Content type

            // Add all pages to index (excluding those marked search_exclude)
            data.pages.forEach(page => {
                if (!page.search_exclude && !page.draft) {
                    this.add({
                        objectID: page.objectID || page.href,  // Use objectID for unique tracking
                        title: page.title || '',
                        description: page.description || '',
                        content: page.content || page.excerpt || '',
                        tags: (page.tags || []).join(' '),
                        section: page.section || '',
                        author: page.author || page.authors?.join(' ') || '',
                        search_keywords: (page.search_keywords || []).join(' '),
                        kind: page.kind || page.type || '',
                    });
                }
            });
        });

        log(`Search index loaded (runtime): ${data.pages.length} pages`);
    }

    // ============================================================
    // Search Functions
    // ============================================================

    /**
     * Parse query terms from user input
     * @param {string} query - Raw user query
     * @returns {Array} Array of term objects with metadata
     */
    function parseQueryTerms(query) {
        const rawTerms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);

        return rawTerms.map(term => {
            // Check for Lunr operators
            const hasOperators = /[*~+\-:]/.test(term);

            // Check for quoted phrases (basic support)
            const isExact = term.startsWith('"') && term.endsWith('"');
            if (isExact) {
                term = term.slice(1, -1);
            }

            return {
                term: term,
                hasOperators: hasOperators,
                isExact: isExact,
                isShort: term.length < 4
            };
        }).filter(t => t.term.length > 0);
    }

    /**
     * Perform search using Lunr's query builder API
     *
     * This approach uses the programmatic query builder instead of string parsing,
     * giving full control over how terms are matched and combined.
     *
     * Strategy for each term (ORed together):
     * 1. Exact match via pipeline (highest boost) - handles stemming correctly
     * 2. Prefix match (medium boost) - for autocomplete-style matching
     * 3. Fuzzy match (low boost) - for typo tolerance (longer terms only)
     *
     * @param {string} query - Search query
     * @param {Object} filters - Optional filters
     * @returns {Array} Search results
     */
    function search(query, filters = {}) {
        if (!isIndexLoaded || !searchIndex || !searchData || !Array.isArray(searchData.pages)) {
            console.warn('Search index not loaded');
            return [];
        }

        if (!query || query.length < CONFIG.minQueryLength) {
            return [];
        }

        try {
            const parsedTerms = parseQueryTerms(query);

            if (parsedTerms.length === 0) {
                return [];
            }

            // Use Lunr's query builder for precise control
            // This avoids the quirks of string-based query parsing
            let results = searchIndex.query(function(q) {
                parsedTerms.forEach(({ term, hasOperators, isExact, isShort }) => {

                    // If term has operators, pass through as-is
                    if (hasOperators) {
                        q.term(term);
                        return;
                    }

                    // Strategy 1: Exact match through pipeline
                    // Pipeline handles stemming, so "directives" matches "directive"
                    q.term(term, {
                        boost: 10,
                        usePipeline: true,
                        presence: lunr.Query.presence.OPTIONAL
                    });

                    // Strategy 2: Prefix/wildcard match
                    // Good for partial typing: "direct" → "directive", "direction"
                    if (!isExact) {
                        q.term(term, {
                            boost: 5,
                            wildcard: lunr.Query.wildcard.TRAILING,
                            usePipeline: true,  // Stem first, then wildcard
                            presence: lunr.Query.presence.OPTIONAL
                        });
                    }

                    // Strategy 3: Fuzzy match for typo tolerance
                    // Only for longer terms to avoid too many false positives
                    if (!isExact && !isShort) {
                        q.term(term, {
                            boost: 1,
                            editDistance: 1,
                            usePipeline: true,
                            presence: lunr.Query.presence.OPTIONAL
                        });
                    }
                });
            });

            // Get full page data for each result
            results = results.map(result => {
                // Match by objectID (which is the URI/relative path)
                const page = searchData.pages.find(p =>
                    (p.objectID || p.uri || p.href) === result.ref
                );
                if (page) {
                    return {
                        ...page,
                        // Use url (includes baseurl) for navigation
                        href: page.href || page.uri,
                        score: result.score,
                        matchData: result.matchData,
                    };
                }
                return null;
            }).filter(Boolean);

            // Apply filters
            results = applyFilters(results, filters);

            // Transform results (add highlights, format dates, etc.)
            results = transformResults(results, query);

            // Limit results
            results = results.slice(0, CONFIG.maxResults);

            return results;

        } catch (error) {
            console.error('Search error:', error);
            return [];
        }
    }

    /**
     * Group results by directory structure for flexible organization
     * @param {Array} results - Search results
     * @returns {Object} Grouped results
     */
    function groupResults(results) {
        const groups = {};

        results.forEach(result => {
            let groupName = 'Other';

            // Strategy 1: Use directory structure (most flexible)
            if (result.dir && result.dir !== '/') {
                // Extract parent directory name
                // e.g., /docs/getting-started/ → "Getting Started"
                // e.g., /api/core/ → "API / Core"
                const pathParts = result.dir.split('/').filter(Boolean);

                if (pathParts.length > 0) {
                    // Use last 1-2 parts for readability
                    if (pathParts.length === 1) {
                        // Top-level: /docs/ → "Docs"
                        groupName = formatGroupName(pathParts[0]);
                    } else {
                        // Nested: /docs/getting-started/ → "Docs / Getting Started"
                        // But show only parent for cleaner groups: → "Getting Started"
                        groupName = formatGroupName(pathParts[pathParts.length - 1]);
                    }
                }
            }

            // Strategy 2: Fall back to section if no dir
            else if (result.section) {
                groupName = formatGroupName(result.section);
            }

            // Strategy 3: Fall back to type
            else if (result.type) {
                groupName = formatGroupName(result.type);
            }

            // Add to group
            if (!groups[groupName]) {
                groups[groupName] = [];
            }
            groups[groupName].push(result);
        });

        // Sort groups by count (largest first), then alphabetically
        return Object.entries(groups)
            .map(([name, items]) => ({ name, items, count: items.length }))
            .sort((a, b) => {
                // Sort by count descending, then name ascending
                if (b.count !== a.count) {
                    return b.count - a.count;
                }
                return a.name.localeCompare(b.name);
            });
    }

    /**
     * Format directory/section name for display
     * @param {string} name - Raw name (kebab-case)
     * @returns {string} Formatted name (Title Case)
     */
    function formatGroupName(name) {
        return name
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Apply filters to search results
     * @param {Array} results - Search results
     * @param {Object} filters - Filters to apply
     * @returns {Array} Filtered results
     */
    function applyFilters(results, filters) {
        let filtered = results;

        // Filter by section
        if (filters.section) {
            filtered = filtered.filter(r => r.section === filters.section);
        }

        // Filter by type
        if (filters.type) {
            filtered = filtered.filter(r => r.type === filters.type);
        }

        // Filter by tags (any match)
        if (filters.tags && filters.tags.length > 0) {
            filtered = filtered.filter(r => {
                const pageTags = r.tags || [];
                return filters.tags.some(tag => pageTags.includes(tag));
            });
        }

        // Filter by author
        if (filters.author) {
            filtered = filtered.filter(r =>
                r.author === filters.author ||
                (r.authors && r.authors.includes(filters.author))
            );
        }

        // Filter by difficulty (for tutorials)
        if (filters.difficulty) {
            filtered = filtered.filter(r => r.difficulty === filters.difficulty);
        }

        // Filter by featured
        if (filters.featured) {
            filtered = filtered.filter(r => r.featured === true);
        }

        return filtered;
    }

    /**
     * Transform results (add highlights, format, etc.)
     * @param {Array} results - Search results
     * @param {string} query - Search query
     * @returns {Array} Transformed results
     */
    function transformResults(results, query) {
        const queryTerms = query.toLowerCase().split(/\s+/).filter(Boolean);

        return results.map(result => {
            // Highlight matches in title
            result.highlightedTitle = highlightMatches(result.title, queryTerms);

            // Create highlighted excerpt
            result.highlightedExcerpt = createHighlightedExcerpt(
                result.content || result.excerpt || result.description,
                queryTerms,
                CONFIG.excerptLength
            );

            // Format date
            if (result.date) {
                result.formattedDate = formatDate(result.date);
            }

            // Add breadcrumb if section exists
            if (result.section) {
                result.breadcrumb = `${result.section} / ${result.title}`;
            }

            // Add type badge info
            if (result.type) {
                result.typeBadge = {
                    text: result.type,
                    class: `badge-${result.type}`,
                };
            }

            return result;
        });
    }

    /**
     * Highlight query terms in text (HTML-aware)
     * @param {string} text - Text to highlight (may contain HTML)
     * @param {Array} terms - Terms to highlight
     * @returns {string} Text with highlights applied only to text content, not HTML tags
     */
    function highlightMatches(text, terms) {
        if (!text || !terms.length) return text;

        // Build a combined regex for all terms
        const escapedTerms = terms.map(term => escapeRegex(term)).join('|');
        const termRegex = new RegExp(`(${escapedTerms})`, 'gi');

        // Split text into HTML tags and text content
        // This regex matches HTML tags (including closing tags and self-closing)
        const htmlTagRegex = /<[^>]+>/g;

        let result = '';
        let lastIndex = 0;
        let match;

        while ((match = htmlTagRegex.exec(text)) !== null) {
            // Process text before this tag (this is safe to highlight)
            const textBefore = text.slice(lastIndex, match.index);
            if (textBefore) {
                result += textBefore.replace(termRegex, `<mark class="${CONFIG.highlightClass}">$1</mark>`);
            }
            // Add the HTML tag unchanged
            result += match[0];
            lastIndex = htmlTagRegex.lastIndex;
        }

        // Process any remaining text after the last tag
        const remainingText = text.slice(lastIndex);
        if (remainingText) {
            result += remainingText.replace(termRegex, `<mark class="${CONFIG.highlightClass}">$1</mark>`);
        }

        return result;
    }

    /**
     * Create excerpt with highlighted matches
     * @param {string} text - Full text
     * @param {Array} terms - Terms to highlight
     * @param {number} length - Excerpt length
     * @returns {string} Highlighted excerpt
     */
    function createHighlightedExcerpt(text, terms, length) {
        if (!text) return '';

        // Find first match position
        let matchPos = -1;
        terms.forEach(term => {
            const pos = text.toLowerCase().indexOf(term.toLowerCase());
            if (pos !== -1 && (matchPos === -1 || pos < matchPos)) {
                matchPos = pos;
            }
        });

        // Extract excerpt around first match (if found)
        let excerpt;
        if (matchPos !== -1) {
            const start = Math.max(0, matchPos - Math.floor(length / 2));
            const end = Math.min(text.length, start + length);
            excerpt = text.substring(start, end);

            // Add ellipsis if needed
            if (start > 0) excerpt = '...' + excerpt;
            if (end < text.length) excerpt = excerpt + '...';
        } else {
            // No match found, use beginning
            excerpt = text.substring(0, length);
            if (text.length > length) excerpt += '...';
        }

        // Highlight matches
        return highlightMatches(excerpt, terms);
    }

    /**
     * Format date string
     * @param {string} dateStr - Date string (YYYY-MM-DD)
     * @returns {string} Formatted date
     */
    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateStr;
        }
    }

    // ============================================================
    // Filter Functions
    // ============================================================

    /**
     * Get unique values for a field (for filter options)
     * @param {string} field - Field name
     * @returns {Array} Unique values
     */
    function getUniqueValues(field) {
        if (!searchData || !Array.isArray(searchData.pages)) return [];

        const values = new Set();
        searchData.pages.forEach(page => {
            const value = page[field];
            if (value) {
                if (Array.isArray(value)) {
                    value.forEach(v => values.add(v));
                } else {
                    values.add(value);
                }
            }
        });

        return Array.from(values).sort();
    }

    /**
     * Get available sections
     * @returns {Array} Section names
     */
    function getAvailableSections() {
        return getUniqueValues('section');
    }

    /**
     * Get available content types
     * @returns {Array} Type names
     */
    function getAvailableTypes() {
        return getUniqueValues('type');
    }

    /**
     * Get available tags
     * @returns {Array} Tag names
     */
    function getAvailableTags() {
        return getUniqueValues('tags');
    }

    /**
     * Get available authors
     * @returns {Array} Author names
     */
    function getAvailableAuthors() {
        const authors = new Set();

        if (searchData && Array.isArray(searchData.pages)) {
            searchData.pages.forEach(page => {
                if (page.author) authors.add(page.author);
                if (page.authors) page.authors.forEach(a => authors.add(a));
            });
        }

        return Array.from(authors).sort();
    }

    // ============================================================
    // Search Modal Functions
    // ============================================================

    /**
     * Initialize search modal
     */
    function initModal() {
        modal = document.getElementById('search-modal');
        if (!modal) {
            log('Search modal not found - modal disabled in config?');
            return;
        }

        // Cache DOM elements
        modalInput = document.getElementById('search-modal-input');
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
        bindModalEvents();

        log('Search modal initialized');
    }

    function bindModalEvents() {
        // Global keyboard shortcut (Cmd/Ctrl + K)
        document.addEventListener('keydown', handleGlobalKeydown);

        // Modal-specific events
        modal.addEventListener('keydown', handleModalKeydown);
        modal.addEventListener('click', handleModalClick);

        // Input events
        modalInput.addEventListener('input', debounce(handleModalInput, CONFIG.modalDebounceDelay));
        modalInput.addEventListener('focus', handleInputFocus);

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

    function handleGlobalKeydown(e) {
        // Cmd/Ctrl + K to open
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            if (isModalOpen) {
                modalInput.focus();
                modalInput.select();
            } else {
                openModal();
            }
        }

        // Also support "/" to open search (common pattern)
        if (e.key === '/' && !isModalOpen && !isInputElement(e.target)) {
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

    function handleModalInput(e) {
        const query = e.target.value.trim();

        if (query.length < CONFIG.minQueryLength) {
            hideResults();
            showRecentSearches();
            return;
        }

        performModalSearch(query);
    }

    function handleInputFocus() {
        if (!modalInput.value.trim()) {
            showRecentSearches();
        }
    }

    function performModalSearch(query) {
        if (!isIndexLoaded) {
            log('Search index not loaded yet');
            if (loading) loading.style.display = 'flex';
            return;
        }

        if (loading) loading.style.display = 'none';

        // Perform search
        const results = search(query);
        currentResults = results.slice(0, 20); // Modal uses smaller max

        // Update UI
        displayModalResults(currentResults, query);

        // Update status for screen readers
        updateStatus(`${currentResults.length} results found`);
    }

    function displayModalResults(results, query) {
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

    function createResultSection(title, items, query, collapsed, startIndex) {
        const section = document.createElement('div');
        section.className = 'search-modal__results-group';

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
        const href = result.href || result.uri;
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
        const query = modalInput.value.trim();
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

    function goToSearchPage(query) {
        // Get baseurl for proper URL construction
        const baseurl = resolveBaseUrl();
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

    function openModal() {
        if (isModalOpen) return;

        modal.showModal();
        isModalOpen = true;
        selectedIndex = -1;

        // Focus input
        requestAnimationFrame(() => {
            modalInput.focus();
            modalInput.select();
        });

        // Show recent searches if no query
        if (!modalInput.value.trim()) {
            showRecentSearches();
        }

        // Trigger search index load if not already loaded
        if (!isIndexLoaded) {
            if (loading) loading.style.display = 'flex';
            loadSearchIndex();
        }

        // Add body class to prevent scrolling
        document.body.classList.add('search-modal-open');

        log('Search modal opened');
    }

    function closeModal() {
        if (!isModalOpen) return;

        modal.close();
        isModalOpen = false;
        selectedIndex = -1;
        currentResults = [];

        // Clear input
        modalInput.value = '';

        // Reset UI
        hideResults();
        showEmptyState();

        // Remove body class
        document.body.classList.remove('search-modal-open');

        log('Search modal closed');
    }

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

    // ============================================================
    // Search Page Functions
    // ============================================================

    // Search page state
    let pageInput = null;
    let pageClearBtn = null;
    let pageResults = null;
    let pageResultsList = null;
    let pageResultsCount = null;
    let pageNoResults = null;
    let pageNoResultsQuery = null;
    let pageEmptyState = null;
    let pageLoadingState = null;
    let pageErrorState = null;
    let pageFiltersToggle = null;
    let pageFiltersPanel = null;
    let pageFilterSection = null;
    let pageFilterType = null;
    let pageDebounceTimer = null;
    let pageCurrentQuery = '';
    let pageCurrentFilters = {};
    let pageSelectedIndex = -1;
    let pageResultItems = [];

    /**
     * Initialize search page functionality
     */
    function initSearchPage() {
        // Check if this is the new search page layout
        const isNewLayout = document.querySelector('.search-page__container');

        if (isNewLayout) {
            initSearchPageNew();
        } else {
            initSearchPageLegacy();
        }
    }

    // Inline loading indicator (spinner in input)
    let pageLoadingIndicator = null;

    /**
     * Initialize the new search page layout (modal-style)
     */
    function initSearchPageNew() {
        // Cache elements
        pageInput = document.getElementById('search-input');
        pageClearBtn = document.getElementById('search-clear');
        pageResults = document.getElementById('search-results');
        pageResultsList = document.getElementById('search-results-list');
        pageResultsCount = document.getElementById('search-results-count');
        pageNoResults = document.getElementById('search-no-results');
        pageNoResultsQuery = document.getElementById('search-no-results-query');
        pageEmptyState = document.getElementById('search-empty');
        pageLoadingState = document.getElementById('search-loading');
        pageLoadingIndicator = document.getElementById('search-loading-indicator');
        pageErrorState = document.getElementById('search-error');
        pageFiltersToggle = document.getElementById('filters-toggle');
        pageFiltersPanel = document.getElementById('search-filters');
        pageFilterSection = document.getElementById('filter-section');
        pageFilterType = document.getElementById('filter-type');

        if (!pageInput) return;

        // Check for URL query parameter FIRST
        const params = new URLSearchParams(window.location.search);
        const urlQuery = params.has('q') ? params.get('q') : null;

        // If we have a query, start loading index immediately (no delay)
        // This ensures the index is loading ASAP when user arrives with a search query
        if (urlQuery && !isIndexLoaded && !isIndexLoading) {
            log('URL has query, loading index immediately');
            loadSearchIndex();
        }

        // Set up index loading state and listeners
        if (!isIndexLoaded) {
            if (pageLoadingState) pageLoadingState.style.display = 'flex';
            if (pageEmptyState) pageEmptyState.style.display = 'none';
            window.addEventListener('searchIndexLoaded', onPageIndexLoaded);
            window.addEventListener('searchIndexError', onPageIndexError);
        } else {
            onPageIndexLoaded();
        }

        // Input events
        pageInput.addEventListener('input', onPageInput);
        pageInput.addEventListener('keydown', onPageKeydown);
        if (pageClearBtn) pageClearBtn.addEventListener('click', clearPageSearch);

        // Filter events
        if (pageFiltersToggle) pageFiltersToggle.addEventListener('click', togglePageFilters);
        if (pageFilterSection) pageFilterSection.addEventListener('change', onPageFilterChange);
        if (pageFilterType) pageFilterType.addEventListener('change', onPageFilterChange);

        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) clearFiltersBtn.addEventListener('click', clearPageFilters);

        // Suggestion pills
        document.querySelectorAll('.search-page__suggestion').forEach(btn => {
            btn.addEventListener('click', () => {
                pageInput.value = btn.dataset.query;
                pageInput.dispatchEvent(new Event('input'));
                pageInput.focus();
            });
        });

        // Handle URL query parameter
        if (urlQuery) {
            pageInput.value = urlQuery;
            // Store the query so onPageIndexLoaded can use it
            pageCurrentQuery = urlQuery;

            if (isIndexLoaded) {
                performPageSearch(urlQuery);
            }
            // Note: onPageIndexLoaded will re-trigger search using pageCurrentQuery
            // No need for a separate listener - avoids duplicate event handlers
        }

        log('Search page initialized (new layout)');
    }

    function onPageIndexLoaded() {
        if (pageLoadingState) pageLoadingState.style.display = 'none';
        if (pageLoadingIndicator) pageLoadingIndicator.style.display = 'none';
        populatePageFilters();

        // Re-trigger search if user was typing while index was loading
        if (pageCurrentQuery && pageCurrentQuery.length >= CONFIG.minQueryLength) {
            log('Index loaded, re-triggering search for: ' + pageCurrentQuery);
            performPageSearch(pageCurrentQuery);
        } else if (pageEmptyState) {
            pageEmptyState.style.display = 'flex';
        }
    }

    function onPageIndexError(e) {
        if (pageLoadingState) pageLoadingState.style.display = 'none';
        if (pageErrorState) pageErrorState.style.display = 'block';
    }

    function populatePageFilters() {
        if (pageFilterSection) {
            const sections = getAvailableSections();
            sections.forEach(section => {
                const opt = document.createElement('option');
                opt.value = section;
                opt.textContent = section;
                pageFilterSection.appendChild(opt);
            });
        }

        if (pageFilterType) {
            const types = getAvailableTypes();
            types.forEach(type => {
                const opt = document.createElement('option');
                opt.value = type;
                opt.textContent = type;
                pageFilterType.appendChild(opt);
            });
        }
    }

    function onPageInput(e) {
        const query = e.target.value.trim();
        if (pageClearBtn) pageClearBtn.style.display = query ? 'flex' : 'none';

        clearTimeout(pageDebounceTimer);
        pageDebounceTimer = setTimeout(() => performPageSearch(query), CONFIG.modalDebounceDelay);
    }

    function onPageKeydown(e) {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                navigatePageResults(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                navigatePageResults(-1);
                break;
            case 'Enter':
                e.preventDefault();
                selectPageResult();
                break;
            case 'Escape':
                if (pageCurrentQuery) {
                    e.preventDefault();
                    clearPageSearch();
                }
                break;
        }
    }

    function performPageSearch(query) {
        pageCurrentQuery = query;
        pageSelectedIndex = -1;
        pageResultItems = [];

        if (!query || query.length < CONFIG.minQueryLength) {
            hidePageResults();
            if (pageEmptyState) pageEmptyState.style.display = 'flex';
            updatePageURL('');
            return;
        }

        // Wait for index to load before searching (prevents false "No results")
        if (!isIndexLoaded) {
            log('Search index not loaded yet, showing loading state');
            if (pageEmptyState) pageEmptyState.style.display = 'none';
            // Show inline spinner in input (better UX than full-page loading)
            if (pageLoadingIndicator) pageLoadingIndicator.style.display = 'flex';
            hidePageResults();
            // Search will be re-triggered when index loads via onPageIndexLoaded
            return;
        }

        // Hide loading indicator now that we're searching
        if (pageLoadingIndicator) pageLoadingIndicator.style.display = 'none';

        // Get filters
        pageCurrentFilters = {
            section: pageFilterSection?.value || null,
            type: pageFilterType?.value || null,
            tags: []
        };

        // Perform search
        const results = search(query, pageCurrentFilters);
        displayPageResults(results, query);
        updatePageURL(query);
    }

    function displayPageResults(results, query) {
        if (pageEmptyState) pageEmptyState.style.display = 'none';
        if (pageResultsList) pageResultsList.innerHTML = '';

        if (results.length === 0) {
            if (pageResults) pageResults.style.display = 'block';
            if (pageNoResults) pageNoResults.style.display = 'flex';
            if (pageNoResultsQuery) pageNoResultsQuery.textContent = query;
            return;
        }

        // Show results
        if (pageResults) pageResults.style.display = 'block';
        if (pageNoResults) pageNoResults.style.display = 'none';
        if (pageResultsCount) {
            pageResultsCount.textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;
        }

        // Group by autodoc status (matching modal behavior)
        const { docs, api } = groupByAutodoc(results);
        let globalIndex = 0;

        // Documentation section
        if (docs.length > 0) {
            const section = createPageResultSection('Documentation', docs, query, false, globalIndex);
            pageResultsList.appendChild(section);
            globalIndex += docs.length;
        }

        // API Reference section (collapsed by default)
        if (api.length > 0) {
            const section = createPageResultSection(`API Reference (${api.length})`, api, query, true, globalIndex);
            pageResultsList.appendChild(section);
        }

        // Cache navigable items
        pageResultItems = Array.from(pageResultsList.querySelectorAll('.search-page__result-item'));
    }

    function createPageResultSection(title, items, query, collapsed, startIndex) {
        const section = document.createElement('div');
        section.className = 'search-page__results-group';

        // Header
        const header = document.createElement('div');
        header.className = 'search-page__section-header' + (collapsed ? ' search-page__section-header--collapsible' : '');
        header.innerHTML = `
            <span class="search-page__section-title">${title}</span>
            ${collapsed ? '<span class="search-page__section-toggle" aria-hidden="true">▶</span>' : ''}
        `;

        // Items container
        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'search-page__section-items';
        if (collapsed) {
            itemsContainer.style.display = 'none';
            itemsContainer.setAttribute('aria-hidden', 'true');
        }

        // Render items
        items.forEach((result, localIndex) => {
            const item = createPageResultItem(result, startIndex + localIndex);
            itemsContainer.appendChild(item);
        });

        // Toggle behavior for collapsed sections
        if (collapsed) {
            header.style.cursor = 'pointer';
            header.setAttribute('role', 'button');
            header.setAttribute('aria-expanded', 'false');
            header.setAttribute('tabindex', '0');

            const toggle = () => {
                const isHidden = itemsContainer.style.display === 'none';
                itemsContainer.style.display = isHidden ? 'block' : 'none';
                itemsContainer.setAttribute('aria-hidden', !isHidden);
                header.querySelector('.search-page__section-toggle').textContent = isHidden ? '▼' : '▶';
                header.setAttribute('aria-expanded', isHidden);
                pageResultItems = Array.from(pageResultsList.querySelectorAll('.search-page__result-item'));
            };

            header.addEventListener('click', toggle);
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggle();
                }
            });
        }

        section.appendChild(header);
        section.appendChild(itemsContainer);
        return section;
    }

    function createPageResultItem(result, index) {
        const item = document.createElement('div');
        item.className = 'search-page__result-item';
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', 'false');
        item.setAttribute('data-index', index);

        const href = result.href || result.uri;
        const title = result.highlightedTitle || result.title || 'Untitled';
        const description = result.description || result.highlightedExcerpt || result.excerpt || '';
        const section = result.section || '';

        item.innerHTML = `
            <a href="${href}" class="search-page__result-link" tabindex="-1">
                <div class="search-page__result-content">
                    <span class="search-page__result-title">${title}</span>
                    ${section ? `<span class="search-page__result-section">${section}</span>` : ''}
                    ${result.isAutodoc ? '<span class="search-page__autodoc-badge">API</span>' : ''}
                </div>
                ${description ? `<p class="search-page__result-excerpt">${description}</p>` : ''}
            </a>
        `;

        // Click handler
        item.addEventListener('click', (e) => {
            e.preventDefault();
            pageSelectedIndex = index;
            selectPageResult();
        });

        return item;
    }

    function navigatePageResults(direction) {
        if (pageResultItems.length === 0) return;

        // Remove previous selection
        if (pageSelectedIndex >= 0 && pageSelectedIndex < pageResultItems.length) {
            pageResultItems[pageSelectedIndex].classList.remove('search-page__result-item--selected');
            pageResultItems[pageSelectedIndex].setAttribute('aria-selected', 'false');
        }

        // Calculate new index
        pageSelectedIndex += direction;
        if (pageSelectedIndex < 0) pageSelectedIndex = pageResultItems.length - 1;
        if (pageSelectedIndex >= pageResultItems.length) pageSelectedIndex = 0;

        // Apply new selection
        const selected = pageResultItems[pageSelectedIndex];
        selected.classList.add('search-page__result-item--selected');
        selected.setAttribute('aria-selected', 'true');
        selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    function selectPageResult() {
        if (pageSelectedIndex >= 0 && pageSelectedIndex < pageResultItems.length) {
            const link = pageResultItems[pageSelectedIndex].querySelector('a');
            if (link) window.location.href = link.href;
        }
    }

    function hidePageResults() {
        if (pageResults) pageResults.style.display = 'none';
        if (pageNoResults) pageNoResults.style.display = 'none';
        if (pageResultsList) pageResultsList.innerHTML = '';
        pageSelectedIndex = -1;
        pageResultItems = [];
    }

    function clearPageSearch() {
        if (pageInput) pageInput.value = '';
        pageCurrentQuery = '';
        if (pageClearBtn) pageClearBtn.style.display = 'none';
        if (pageLoadingIndicator) pageLoadingIndicator.style.display = 'none';
        hidePageResults();
        if (pageEmptyState) pageEmptyState.style.display = 'flex';
        updatePageURL('');
        if (pageInput) pageInput.focus();
    }

    function togglePageFilters() {
        if (!pageFiltersToggle || !pageFiltersPanel) return;
        const isExpanded = pageFiltersToggle.getAttribute('aria-expanded') === 'true';
        pageFiltersToggle.setAttribute('aria-expanded', !isExpanded);
        pageFiltersPanel.style.display = isExpanded ? 'none' : 'block';
    }

    function onPageFilterChange() {
        if (pageCurrentQuery) performPageSearch(pageCurrentQuery);
    }

    function clearPageFilters() {
        if (pageFilterSection) pageFilterSection.value = '';
        if (pageFilterType) pageFilterType.value = '';
        if (pageCurrentQuery) performPageSearch(pageCurrentQuery);
    }

    function updatePageURL(query) {
        const url = new URL(window.location);
        if (query) {
            url.searchParams.set('q', query);
        } else {
            url.searchParams.delete('q');
        }
        history.replaceState({}, '', url);
    }

    /**
     * Initialize legacy search page (backward compatibility)
     */
    function initSearchPageLegacy() {
        // Popular searches quick-fill
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

        // Initialize from URL query param (?q=) or hash (#query)
        let query = '';

        // Check for ?q= query param first (preferred)
        const params = new URLSearchParams(window.location.search);
        if (params.has('q')) {
            query = params.get('q');
        }
        // Fall back to hash for backward compatibility
        else if (window.location.hash) {
            query = decodeURIComponent(window.location.hash.substring(1));
        }

        if (query) {
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                // Wait for search index to be ready, then perform search
                setTimeout(() => {
                    searchInput.value = query;
                    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                    searchInput.focus();
                }, 500);
            }
        }

        log('Search page initialized (legacy layout)');
    }

    // ============================================================
    // Preload Functions
    // ============================================================

    /**
     * Trigger search index preload
     */
    function preloadSearch() {
        if (preloadTriggered || !window.BengalSearch) return;
        preloadTriggered = true;

        if (window.BengalUtils && window.BengalUtils.log) {
            window.BengalUtils.log('Preloading search index...');
        }
        loadSearchIndex();
    }

    /**
     * Set up smart preloading based on user intent signals
     */
    function setupSmartPreload() {
        // Preload on search link/button hover (user likely to search)
        const searchTriggers = document.querySelectorAll(
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
    function initPreload() {
        // Get preload mode from meta tag
        const metaEl = document.querySelector('meta[name="bengal:search_preload"]');
        const preloadMode = (metaEl && metaEl.getAttribute('content')) || 'smart';

        if (preloadMode === 'immediate') {
            // Load right away (best for small sites <100 pages)
            preloadSearch();
        } else if (preloadMode === 'smart') {
            // Load on user intent signals (default, best for most sites)
            setupSmartPreload();
        }
        // 'lazy' mode: No preloading - index loads on first search
    }

    // ============================================================
    // Public API
    // ============================================================

    window.BengalSearch = {
        // Core functions
        load: loadSearchIndex,
        search: search,
        groupResults: groupResults,

        // Filter functions
        getAvailableSections: getAvailableSections,
        getAvailableTypes: getAvailableTypes,
        getAvailableTags: getAvailableTags,
        getAvailableAuthors: getAvailableAuthors,

        // State
        isLoaded: () => isIndexLoaded,
        isLoading: () => isIndexLoading,
        getData: () => searchData,

        // Utilities
        highlightMatches: highlightMatches,
        formatDate: formatDate,

        // Modal API
        openModal: openModal,
        closeModal: closeModal,
        isModalOpen: () => isModalOpen,
    };

    // Export modal API for backward compatibility
    window.BengalSearchModal = {
        open: openModal,
        close: closeModal,
        isOpen: () => isModalOpen,
    };

    // Export preload API
    window.BengalSearchPreload = {
        trigger: preloadSearch
    };

    // ============================================================
    // Registration
    // ============================================================

    // Register with enhancement system (if available)
    if (window.Bengal && window.Bengal.enhance) {
        Bengal.enhance.register('search', function (el, options) {
            // Search page initialization
            initSearchPage();
        });
    }

    // ============================================================
    // Auto-initialize
    // ============================================================

    ready(() => {
        // Initialize modal if present
        if (document.getElementById('search-modal')) {
            initModal();
        }

        // Initialize search page if present
        if (document.getElementById('search-input')) {
            initSearchPage();
        }

        // Initialize preloading
        initPreload();

        // Pre-load index on page load (in background, delayed)
        setTimeout(loadSearchIndex, 500);
    });

    log('Bengal Search initialized (consolidated)');

})();
