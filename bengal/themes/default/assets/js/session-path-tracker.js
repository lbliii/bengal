/**
 * Bengal SSG - Session Path Tracker
 *
 * Tracks the user's navigation path (last 3-5 pages visited) in the current session.
 * Used to highlight the user's journey in graph visualizations.
 */

(function() {
    'use strict';

    /**
     * Session Path Tracker
     * Tracks only the previous page visited (last page before current)
     */
    class SessionPathTracker {
        constructor(options = {}) {
            this.storageKey = options.storageKey || 'bengal_session_previous_page';
            this.previousPage = this.loadPreviousPage();
        }

        /**
         * Load previous page from sessionStorage
         * @returns {string|null} Normalized URL of previous page, or null
         */
        loadPreviousPage() {
            try {
                const stored = sessionStorage.getItem(this.storageKey);
                if (stored) {
                    return stored;
                }
            } catch (e) {
                console.warn('SessionPathTracker: Failed to load previous page from sessionStorage', e);
            }
            return null;
        }

        /**
         * Save previous page to sessionStorage
         */
        savePreviousPage() {
            try {
                if (this.previousPage) {
                    sessionStorage.setItem(this.storageKey, this.previousPage);
                } else {
                    sessionStorage.removeItem(this.storageKey);
                }
            } catch (e) {
                console.warn('SessionPathTracker: Failed to save previous page to sessionStorage', e);
            }
        }

        /**
         * Normalize URL for consistent comparison
         * @param {string} url - URL to normalize
         * @returns {string} Normalized URL
         */
        normalizeUrl(url) {
            if (!url) return '';

            // Remove protocol/host if present
            let normalized = url;
            if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
                try {
                    const urlObj = new URL(normalized);
                    normalized = urlObj.pathname;
                } catch (e) {
                    // Invalid URL, try to extract path manually
                    const match = normalized.match(/https?:\/\/[^\/]+(\/.*)/);
                    if (match) {
                        normalized = match[1];
                    }
                }
            }

            // Remove trailing slashes for comparison (but preserve root)
            normalized = normalized.replace(/\/+$/, '') || '/';

            // Ensure it starts with / for consistency
            if (!normalized.startsWith('/')) {
                normalized = '/' + normalized;
            }

            // Remove hash fragments (they don't affect page identity)
            normalized = normalized.split('#')[0];

            return normalized;
        }

        /**
         * Track a page visit
         * Updates previous page to the current page before navigation
         * @param {string} url - URL of the page being visited
         */
        trackPage(url) {
            const normalizedUrl = this.normalizeUrl(url);

            // Don't update if it's the same page (refresh/reload)
            if (this.previousPage === normalizedUrl) {
                return;
            }

            // Update previous page (will be saved on next page load)
            this.previousPage = normalizedUrl;
            this.savePreviousPage();
        }

        /**
         * Get the previous page URL
         * @returns {string|null} Normalized URL of previous page, or null
         */
        getPreviousPage() {
            return this.previousPage;
        }

        /**
         * Check if a URL is the previous page
         * @param {string} url - URL to check
         * @returns {boolean} True if URL is the previous page
         */
        isPreviousPage(url) {
            if (!this.previousPage) return false;
            const normalizedUrl = this.normalizeUrl(url);
            return this.previousPage === normalizedUrl;
        }

        /**
         * Clear the previous page
         */
        clearPreviousPage() {
            this.previousPage = null;
            this.savePreviousPage();
        }
    }

    // Create global instance
    window.BengalSessionPathTracker = SessionPathTracker;

    // Auto-track current page on load
    if (typeof window !== 'undefined') {
        const tracker = new SessionPathTracker();
        const currentUrl = window.location.pathname;

        // Track the current page (this will become the previous page on next navigation)
        tracker.trackPage(currentUrl);

        // Make tracker available globally for graph components
        window.bengalSessionPath = tracker;
    }
})();
