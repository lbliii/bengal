/**
 * Bengal Search — shared configuration
 */
(function () {
  'use strict';

  window.BengalSearchConfig = {
    indexUrl: null,
    prebuiltIndexUrl: null,
    minQueryLength: 2,
    maxResults: 50,
    excerptLength: 150,
    highlightClass: 'search-highlight',
    debounceDelay: 200,
    usePrebuilt: true,
    maxRecentSearches: 5,
    modalDebounceDelay: 150,
    storageKey: 'bengal-recent-searches',
  };
})();
