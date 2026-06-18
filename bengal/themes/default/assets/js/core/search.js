/**
 * Bengal Search — bootstrap
 *
 * Wires index / query / palette modules and exposes the public BengalSearch API.
 * Palette UI lives in the <bengal-search> custom element (search/palette.js).
 */
(function () {
  'use strict';

  if (!window.BengalUtils) {
    console.error('[Bengal] utils.js required for search');
    return;
  }

  const { log, ready } = window.BengalUtils;
  const indexApi = function () { return window.BengalSearchIndex; };
  const queryApi = function () { return window.BengalSearchQuery; };

  function getPaletteInstance() {
    const el = document.querySelector('bengal-search');
    return el || null;
  }

  function ensureSearchElement() {
    let el = document.querySelector('bengal-search');
    if (el) return el;

    const modal = document.getElementById('search-modal');
    if (!modal || !modal.parentElement) return null;

    el = document.createElement('bengal-search');
    modal.parentElement.insertBefore(el, modal);
    el.appendChild(modal);
    return el;
  }

  function openModal() {
    const el = getPaletteInstance() || ensureSearchElement();
    if (el && typeof el.openModal === 'function') {
      el.openModal();
    }
  }

  function closeModal() {
    const el = getPaletteInstance();
    if (el && typeof el.closeModal === 'function') {
      el.closeModal();
    }
  }

  function isModalOpen() {
    const el = getPaletteInstance();
    return el ? !!el.isModalOpen : false;
  }

  window.BengalSearch = {
    load: function () { return indexApi().load(); },
    search: function (query, filters) { return queryApi().search(query, filters); },
    groupResults: function (results) { return queryApi().groupResults(results); },
    organizeResultsWithHeadings: function (results) {
      return queryApi().organizeResultsWithHeadings(results);
    },

    getAvailableSections: function () { return queryApi().getAvailableSections(); },
    getAvailableTypes: function () { return queryApi().getAvailableTypes(); },
    getAvailableTags: function () { return queryApi().getAvailableTags(); },
    getAvailableAuthors: function () { return queryApi().getAvailableAuthors(); },

    isLoaded: function () { return indexApi().isLoaded(); },
    isLoading: function () { return indexApi().isLoading(); },
    getData: function () { return indexApi().getData(); },

    highlightMatches: function (text, terms) { return queryApi().highlightMatches(text, terms); },
    formatDate: function (dateStr) { return queryApi().formatDate(dateStr); },

    openModal: openModal,
    closeModal: closeModal,
    isModalOpen: isModalOpen,
  };

  window.BengalSearchModal = {
    open: openModal,
    close: closeModal,
    isOpen: isModalOpen,
  };

  window.BengalSearchPreload = {
    trigger: function () { return indexApi().preload(); },
  };

  ready(function () {
    ensureSearchElement();

    indexApi().initPreload();

    if (!document.querySelector('bengal-search') && document.getElementById('search-input')) {
      const pageHost = document.createElement('bengal-search');
      document.body.appendChild(pageHost);
    }

    setTimeout(function () {
      indexApi().load();
    }, 500);
  });

  log('Bengal Search initialized (modular)');
})();
