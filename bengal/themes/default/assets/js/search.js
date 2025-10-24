/**
 * Bengal SSG - Search Implementation
 * Using Lunr.js for client-side full-text search
 *
 * Features:
 * - Full-text search across all pages
 * - Filtering by section, type, tags, author
 * - Result transformation and highlighting
 * - Keyboard shortcuts (Cmd/Ctrl + K)
 * - Accessible with ARIA labels
 */

(function() {
  'use strict';

  // ====================================
  // Configuration
  // ====================================

  const CONFIG = {
    indexUrl: null, // computed from meta tag when available
    minQueryLength: 2,
    maxResults: 50,
    excerptLength: 150,
    highlightClass: 'search-highlight',
    debounceDelay: 200,
  };

  // ====================================
  // State
  // ====================================

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

  // ====================================
  // Index Loading & Building
  // ====================================

  /**
   * Load search index from index.json
   */
  async function loadSearchIndex() {
    if (isIndexLoaded || isIndexLoading) return;

    isIndexLoading = true;

    try {
      // Resolve baseurl from meta tag if present
      let baseurl = '';
      try {
        const m = document.querySelector('meta[name="bengal:baseurl"]');
        baseurl = (m && m.getAttribute('content')) || '';
      } catch (e) { /* no-op */ }

      // Prefer explicit meta index URL first
      let indexUrl = '';
      try {
        const m2 = document.querySelector('meta[name="bengal:index_url"]');
        indexUrl = (m2 && m2.getAttribute('content')) || '';
      } catch (e) { /* no-op */ }

      if (!indexUrl) {
        indexUrl = '/index.json';
        if (baseurl) {
          baseurl = baseurl.replace(/\/$/, '');
          // Ensure leading slash on indexUrl
          indexUrl = indexUrl.startsWith('/') ? indexUrl : ('/' + indexUrl);
          indexUrl = baseurl + indexUrl;
        }
      }

      const response = await fetch(indexUrl);
      if (!response.ok) {
        throw new Error(`Failed to load search index: ${response.status}`);
      }

      const data = await response.json();
      searchData = data;

      // Build Lunr index
      searchIndex = lunr(function() {
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
              objectID: page.objectID || page.url,  // Use objectID for unique tracking
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

      isIndexLoaded = true;
      isIndexLoading = false;

      console.log(`Search index loaded: ${data.pages.length} pages`);

      // Dispatch event for other components
      window.dispatchEvent(new CustomEvent('searchIndexLoaded', {
        detail: { pages: data.pages.length }
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

  // ====================================
  // Search Functions
  // ====================================

  /**
   * Perform search with query
   * @param {string} query - Search query
   * @param {Object} filters - Optional filters
   * @returns {Array} Search results
   */
  function search(query, filters = {}) {
    if (!isIndexLoaded || !searchIndex || !searchData) {
      console.warn('Search index not loaded');
      return [];
    }

    if (!query || query.length < CONFIG.minQueryLength) {
      return [];
    }

    try {
      // Perform Lunr search
      let results = searchIndex.search(query);

      // Get full page data for each result
      results = results.map(result => {
        // Match by objectID (which is the URI/relative path)
        const page = searchData.pages.find(p =>
          (p.objectID || p.uri || p.url) === result.ref
        );
        if (page) {
          return {
            ...page,
            // Use url (includes baseurl) for navigation to work with GitHub Pages and similar deployments
            href: page.url || page.uri,
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
   * Highlight query terms in text
   * @param {string} text - Text to highlight
   * @param {Array} terms - Terms to highlight
   * @returns {string} Text with highlights
   */
  function highlightMatches(text, terms) {
    if (!text || !terms.length) return text;

    let highlighted = text;
    terms.forEach(term => {
      const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
      highlighted = highlighted.replace(regex, `<mark class="${CONFIG.highlightClass}">$1</mark>`);
    });

    return highlighted;
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

  /**
   * Escape regex special characters
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // ====================================
  // Filter Functions
  // ====================================

  /**
   * Get unique values for a field (for filter options)
   * @param {string} field - Field name
   * @returns {Array} Unique values
   */
  function getUniqueValues(field) {
    if (!searchData) return [];

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

    if (searchData) {
      searchData.pages.forEach(page => {
        if (page.author) authors.add(page.author);
        if (page.authors) page.authors.forEach(a => authors.add(a));
      });
    }

    return Array.from(authors).sort();
  }

  // ====================================
  // Export API
  // ====================================

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
  };

  // ====================================
  // Auto-initialize
  // ====================================

  // Pre-load index on page load (in background)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      // Delay loading to not block page rendering
      setTimeout(loadSearchIndex, 500);
    });
  } else {
    setTimeout(loadSearchIndex, 500);
  }

  console.log('Bengal Search initialized');

})();
