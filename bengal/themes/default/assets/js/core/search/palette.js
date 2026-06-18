/**
 * Bengal Search — command palette module
 *
 * <bengal-search> custom element: native <dialog> command palette, search page UI,
 * and global keyboard-shortcuts help overlay (?).
 */
(function () {
  'use strict';

  const CONFIG = window.BengalSearchConfig;
  const debounce = window.BengalUtils?.debounce || function (fn, wait) {
    let t;
    return function () {
      clearTimeout(t);
      const args = arguments;
      const ctx = this;
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  };
  const log = window.BengalUtils?.log || (() => {});

  function indexApi() { return window.BengalSearchIndex; }
  function queryApi() { return window.BengalSearchQuery; }

  function isInputElement(element) {
    const tagName = element.tagName.toLowerCase();
    return tagName === 'input' || tagName === 'textarea' || element.isContentEditable;
  }

  function renderHeadingMatches(container, headings, prefix) {
    prefix = prefix || 'search-modal';
    if (!headings || !headings.length) return;

    const list = document.createElement('ul');
    list.className = prefix + '__heading-matches';
    list.setAttribute('aria-label', 'Matching sections');

    headings.forEach(function (heading) {
      const li = document.createElement('li');
      li.className = prefix + '__heading-match';
      const href = heading.href || heading.url;
      const title = heading.highlightedTitle || heading.title || 'Section';
      const snippet = heading.highlightedExcerpt || '';

      li.innerHTML =
        '<a href="' + href + '" class="' + prefix + '__heading-link" tabindex="-1">' +
          '<span class="' + prefix + '__heading-icon" aria-hidden="true">#</span>' +
          '<span class="' + prefix + '__heading-title">' + title + '</span>' +
          (snippet ? '<span class="' + prefix + '__heading-snippet">' + snippet + '</span>' : '') +
        '</a>';

      list.appendChild(li);
    });

    container.appendChild(list);
  }

  function createResultItem(result, index, options) {
    options = options || {};
    const prefix = options.prefix || 'search-modal';
    const item = document.createElement('div');
    item.className = prefix + '__result-item';
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', 'false');
    item.setAttribute('data-index', String(index));

    const href = result.href || result.uri;
    const title = result.highlightedTitle || result.title || 'Untitled';
    const snippet = result.highlightedExcerpt || result.description || result.excerpt || '';
    const section = result.section || '';
    const isHeading = queryApi().isHeadingRecord(result);
    const breadcrumb = isHeading ? (result.breadcrumb || result.parent_title || '') : section;

    item.innerHTML =
      '<a href="' + href + '" class="' + prefix + '__result-link" tabindex="-1">' +
        '<div class="' + prefix + '__result-content">' +
          '<span class="' + prefix + '__result-title">' + title + '</span>' +
          (breadcrumb ? '<span class="' + prefix + '__result-section">' + breadcrumb + '</span>' : '') +
        '</div>' +
        (snippet ? '<p class="' + prefix + '__result-excerpt">' + snippet + '</p>' : '') +
      '</a>';

    if (result.isAutodoc) {
      const badge = document.createElement('span');
      badge.className = prefix + '__autodoc-badge';
      badge.textContent = 'API';
      const contentEl = item.querySelector('.' + prefix + '__result-content');
      if (contentEl) contentEl.appendChild(badge);
    }

    if (result.headingMatches && result.headingMatches.length) {
      renderHeadingMatches(item, result.headingMatches, options.prefix || 'search-modal');
    }

    item.addEventListener('click', function (e) {
      e.preventDefault();
      if (options.onSelect) options.onSelect(index, item);
    });

    return item;
  }

  function createResultSection(title, items, collapsed, startIndex, options) {
    options = options || {};
    const prefix = options.prefix || 'search-modal';
    const section = document.createElement('div');
    section.className = prefix + '__results-group';

    const header = document.createElement('div');
    header.className = prefix + '__section-header';
    if (collapsed) {
      header.classList.add(prefix + '__section-header--collapsible');
    }
    header.innerHTML =
      '<span class="' + prefix + '__section-title">' + title + '</span>' +
      (collapsed ? '<span class="' + prefix + '__section-toggle" aria-hidden="true">▶</span>' : '');

    const itemsContainer = document.createElement('div');
    itemsContainer.className = prefix + '__section-items';
    if (collapsed) {
      itemsContainer.classList.add('hidden');
      itemsContainer.setAttribute('aria-hidden', 'true');
    }

    items.forEach(function (result, localIndex) {
      const globalIdx = startIndex + localIndex;
      itemsContainer.appendChild(createResultItem(result, globalIdx, options));
    });

    if (collapsed) {
      header.style.cursor = 'pointer';
      header.setAttribute('role', 'button');
      header.setAttribute('aria-expanded', 'false');
      header.setAttribute('tabindex', '0');

      const toggleSection = function () {
        const isHidden = itemsContainer.classList.contains('hidden');
        itemsContainer.classList.toggle('hidden', !isHidden);
        itemsContainer.setAttribute('aria-hidden', String(!isHidden));
        const toggle = header.querySelector('.' + prefix + '__section-toggle');
        if (toggle) toggle.textContent = isHidden ? '▼' : '▶';
        header.setAttribute('aria-expanded', String(isHidden));
        if (options.onToggle) options.onToggle();
      };

      header.addEventListener('click', toggleSection);
      header.addEventListener('keydown', function (e) {
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

  function renderOrganizedResults(container, results, options) {
    options = options || {};
    const organized = queryApi().organizeResultsWithHeadings(results);
    const displayResults = organized.pages.concat(organized.standaloneHeadings);
    const grouped = queryApi().groupByAutodoc(displayResults);

    container.innerHTML = '';
    let globalIndex = 0;

    if (grouped.docs.length > 0) {
      container.appendChild(createResultSection('Documentation', grouped.docs, false, globalIndex, options));
      globalIndex += grouped.docs.length;
    }
    if (grouped.api.length > 0) {
      container.appendChild(createResultSection('API Reference (' + grouped.api.length + ')', grouped.api, true, globalIndex, options));
    }

    return container.querySelectorAll('[data-index]').length
      ? Array.from(container.querySelectorAll('.' + (options.prefix || 'search-modal') + '__result-item'))
      : [];
  }

  /** Keyboard shortcuts help overlay (global singleton) */
  const ShortcutsOverlay = {
    dialog: null,

    ensure() {
      if (this.dialog) return this.dialog;

      const dialog = document.createElement('dialog');
      dialog.id = 'keyboard-shortcuts-dialog';
      dialog.className = 'keyboard-shortcuts-dialog';
      dialog.setAttribute('aria-label', 'Keyboard shortcuts');

      dialog.innerHTML =
        '<div class="keyboard-shortcuts-dialog__backdrop" data-close-shortcuts></div>' +
        '<div class="keyboard-shortcuts-dialog__panel">' +
          '<header class="keyboard-shortcuts-dialog__header">' +
            '<h2 class="keyboard-shortcuts-dialog__title">Keyboard shortcuts</h2>' +
            '<button type="button" class="keyboard-shortcuts-dialog__close" data-close-shortcuts aria-label="Close">' +
              '<kbd>ESC</kbd>' +
            '</button>' +
          '</header>' +
          '<div class="keyboard-shortcuts-dialog__body">' +
            '<section class="keyboard-shortcuts-dialog__group">' +
              '<h3>Search</h3>' +
              '<dl>' +
                '<div><dt><kbd>⌘</kbd><kbd>K</kbd> / <kbd>Ctrl</kbd><kbd>K</kbd></dt><dd>Open search</dd></div>' +
                '<div><dt><kbd>/</kbd></dt><dd>Open search</dd></div>' +
                '<div><dt><kbd>↑</kbd><kbd>↓</kbd></dt><dd>Navigate results</dd></div>' +
                '<div><dt><kbd>↵</kbd></dt><dd>Open selected result</dd></div>' +
                '<div><dt><kbd>ESC</kbd></dt><dd>Close search</dd></div>' +
              '</dl>' +
            '</section>' +
            '<section class="keyboard-shortcuts-dialog__group">' +
              '<h3>General</h3>' +
              '<dl>' +
                '<div><dt><kbd>?</kbd></dt><dd>Show this help</dd></div>' +
              '</dl>' +
            '</section>' +
          '</div>' +
        '</div>';

      document.body.appendChild(dialog);

      dialog.addEventListener('click', function (e) {
        if (e.target.hasAttribute('data-close-shortcuts')) {
          ShortcutsOverlay.close();
        }
      });

      this.dialog = dialog;
      return dialog;
    },

    open() {
      const dialog = this.ensure();
      if (!dialog.open) {
        dialog.showModal();
      }
    },

    close() {
      if (this.dialog && this.dialog.open) {
        this.dialog.close();
      }
    },

    isOpen() {
      return !!(this.dialog && this.dialog.open);
    },
  };

  function definePaletteElement() {
    if (!window.Bengal || !window.Bengal.define) return;

    window.Bengal.define('bengal-search', class extends window.Bengal.Base {
    init() {
      this.modal = this.querySelector('#search-modal') || document.getElementById('search-modal');
      this.isModalOpen = false;
      this.selectedIndex = -1;
      this.currentResults = [];
      this.recentSearches = [];

      this._onGlobalKeydown = this._handleGlobalKeydown.bind(this);
      this._onIndexLoaded = this._handleIndexLoaded.bind(this);
      document.addEventListener('keydown', this._onGlobalKeydown);
      window.addEventListener('searchIndexLoaded', this._onIndexLoaded);

      this._initSearchPage();

      if (!this.modal) {
        log('[bengal-search] No search modal — search page only');
        return;
      }

      this.modalInput = this.modal.querySelector('#search-modal-input');
      this.resultsList = this.modal.querySelector('#search-modal-results-list');
      this.recentSection = this.modal.querySelector('#search-modal-recent');
      this.recentList = this.modal.querySelector('#search-modal-recent-list');
      this.noResults = this.modal.querySelector('#search-modal-no-results');
      this.emptyState = this.modal.querySelector('#search-modal-empty');
      this.loading = this.modal.querySelector('#search-modal-loading');
      this.status = this.modal.querySelector('#search-modal-status');

      this.isModalOpen = false;
      this.selectedIndex = -1;
      this.currentResults = [];
      this.recentSearches = [];

      this._onModalKeydown = this._handleModalKeydown.bind(this);
      this._onModalClick = this._handleModalClick.bind(this);
      this._onModalInput = debounce(this._handleModalInput.bind(this), CONFIG.modalDebounceDelay);

      this._loadRecentSearches();
      this._bindModalEvents();

      log('[bengal-search] Command palette initialized');
    }

    teardown() {
      document.removeEventListener('keydown', this._onGlobalKeydown);
      if (this.modal) {
        this.modal.removeEventListener('keydown', this._onModalKeydown);
        this.modal.removeEventListener('click', this._onModalClick);
      }
      window.removeEventListener('searchIndexLoaded', this._onIndexLoaded);
    }

    _bindModalEvents() {
      this.modal.addEventListener('keydown', this._onModalKeydown);
      this.modal.addEventListener('click', this._onModalClick);

      if (this.modalInput) {
        this.modalInput.addEventListener('input', this._onModalInput);
        this.modalInput.addEventListener('focus', this._handleInputFocus.bind(this));
      }

      this.querySelectorAll('[data-close-modal]').forEach(function (el) {
        el.addEventListener('click', function () { this.closeModal(); }.bind(this));
      }.bind(this));

      const clearRecentBtn = this.modal.querySelector('#clear-recent-searches');
      if (clearRecentBtn) {
        clearRecentBtn.addEventListener('click', this._clearRecentSearches.bind(this));
      }

      document.querySelectorAll('#search-trigger, #nav-search-trigger, .nav-search-trigger').forEach(function (trigger) {
        trigger.addEventListener('click', function (e) {
          e.preventDefault();
          this.openModal();
        }.bind(this));
      }.bind(this));
    }

    _handleGlobalKeydown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (this.isModalOpen) {
          this.modalInput.focus();
          this.modalInput.select();
        } else {
          this.openModal();
        }
        return;
      }

      if (e.key === '/' && !this.isModalOpen && !ShortcutsOverlay.isOpen() && !isInputElement(e.target)) {
        e.preventDefault();
        this.openModal();
        return;
      }

      if (e.key === '?' && !isInputElement(e.target) && !this.isModalOpen) {
        e.preventDefault();
        ShortcutsOverlay.open();
      }
    }

    _handleModalKeydown(e) {
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          this.closeModal();
          break;
        case 'ArrowDown':
          e.preventDefault();
          this._navigateResults(1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          this._navigateResults(-1);
          break;
        case 'Enter':
          e.preventDefault();
          this._selectResult();
          break;
      }
    }

    _handleModalClick(e) {
      if (e.target.hasAttribute('data-close-modal')) {
        this.closeModal();
      }
    }

    _handleIndexLoaded() {
      if (this.loading) this.loading.classList.add('hidden');
      if (this.pageLoadingState) this.pageLoadingState.classList.add('hidden');
      if (this.pageLoadingIndicator) this.pageLoadingIndicator.classList.add('hidden');
      this._populatePageFilters();
      if (this.pageCurrentQuery && this.pageCurrentQuery.length >= CONFIG.minQueryLength) {
        this._performPageSearch(this.pageCurrentQuery);
      }
    }

    _handleModalInput(e) {
      const query = e.target.value.trim();
      if (query.length < CONFIG.minQueryLength) {
        this._hideResults();
        this._showRecentSearches();
        return;
      }
      this._performModalSearch(query);
    }

    _handleInputFocus() {
      if (!this.modalInput.value.trim()) {
        this._showRecentSearches();
      }
    }

    _performModalSearch(query) {
      if (!indexApi().isLoaded()) {
        if (this.loading) this.loading.classList.remove('hidden');
        indexApi().load();
        return;
      }

      if (this.loading) this.loading.classList.add('hidden');

      const results = queryApi().search(query);
      this.currentResults = results.slice(0, 20);
      this._displayModalResults(this.currentResults);
      this._updateStatus(this.currentResults.length + ' results found');
    }

    _displayModalResults(results) {
      this._hideRecentSearches();
      this._hideEmptyState();

      if (results.length === 0) {
        this._showNoResults(this.modalInput.value.trim());
        return;
      }

      this._hideNoResults();
      this.selectedIndex = -1;

      renderOrganizedResults(this.resultsList, results, {
        prefix: 'search-modal',
        onSelect: function (index) {
          this.selectedIndex = index;
          this._selectResult();
        }.bind(this),
      });

      this.resultsList.parentElement.classList.remove('hidden');
    }

    _getNavigableItems() {
      const resultItems = this.resultsList.querySelectorAll('.search-modal__result-item, .search-modal__heading-link');
      const recentItems = this.recentList ? this.recentList.querySelectorAll('.search-modal__recent-item') : [];

      if (resultItems.length > 0) {
        return Array.from(this.resultsList.querySelectorAll('.search-modal__result-item'));
      }
      if (this.recentSection && !this.recentSection.classList.contains('hidden')) {
        return Array.from(recentItems);
      }
      return [];
    }

    _navigateResults(direction) {
      const items = this._getNavigableItems();
      if (items.length === 0) return;

      if (this.selectedIndex >= 0 && this.selectedIndex < items.length) {
        items[this.selectedIndex].classList.remove('search-modal__result-item--selected');
        items[this.selectedIndex].setAttribute('aria-selected', 'false');
      }

      this.selectedIndex += direction;
      if (this.selectedIndex < 0) this.selectedIndex = items.length - 1;
      if (this.selectedIndex >= items.length) this.selectedIndex = 0;

      const selectedItem = items[this.selectedIndex];
      selectedItem.classList.add('search-modal__result-item--selected');
      selectedItem.setAttribute('aria-selected', 'true');
      selectedItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });

      const title = selectedItem.querySelector('.search-modal__result-title');
      if (title) {
        this._updateStatus(title.textContent + ', ' + (this.selectedIndex + 1) + ' of ' + items.length);
      }
    }

    _selectResult() {
      const query = this.modalInput.value.trim();
      const items = this._getNavigableItems();

      if (this.selectedIndex < 0) {
        if (query) this._goToSearchPage(query);
        return;
      }

      if (this.selectedIndex >= 0 && this.selectedIndex < items.length) {
        const link = items[this.selectedIndex].querySelector('a');
        if (link) {
          if (query) {
            this._addRecentSearch(query, link.href, items[this.selectedIndex].querySelector('.search-modal__result-title')?.textContent || query);
          }
          this.closeModal();
          window.location.href = link.href;
        }
      }
    }

    _goToSearchPage(query) {
      const baseurl = indexApi().resolveBaseUrl();
      this.closeModal();
      window.location.href = baseurl + '/search/?q=' + encodeURIComponent(query);
    }

    openModal() {
      if (!this.modal || this.isModalOpen) return;

      this.modal.showModal();
      this.isModalOpen = true;
      this.selectedIndex = -1;

      requestAnimationFrame(function () {
        this.modalInput.focus();
        this.modalInput.select();
      }.bind(this));

      if (!this.modalInput.value.trim()) {
        this._showRecentSearches();
      }

      if (!indexApi().isLoaded()) {
        if (this.loading) this.loading.classList.remove('hidden');
        indexApi().load();
      }

      document.body.classList.add('search-modal-open');
    }

    closeModal() {
      if (!this.modal || !this.isModalOpen) return;

      this.modal.close();
      this.isModalOpen = false;
      this.selectedIndex = -1;
      this.currentResults = [];
      this.modalInput.value = '';
      this._hideResults();
      this._showEmptyState();
      document.body.classList.remove('search-modal-open');
    }

    _loadRecentSearches() {
      try {
        const stored = localStorage.getItem(CONFIG.storageKey);
        this.recentSearches = stored ? JSON.parse(stored) : [];
      } catch (e) {
        this.recentSearches = [];
      }
    }

    _saveRecentSearches() {
      try {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(this.recentSearches));
      } catch (e) { /* no-op */ }
    }

    _addRecentSearch(query, href, title) {
      this.recentSearches = this.recentSearches.filter(function (s) { return s.query !== query; });
      this.recentSearches.unshift({ query: query, href: href, title: title, timestamp: Date.now() });
      if (this.recentSearches.length > CONFIG.maxRecentSearches) {
        this.recentSearches = this.recentSearches.slice(0, CONFIG.maxRecentSearches);
      }
      this._saveRecentSearches();
    }

    _showRecentSearches() {
      if (!this.recentList || !this.recentSection) return;

      if (this.recentSearches.length === 0) {
        this._hideRecentSearches();
        this._showEmptyState();
        return;
      }

      this._hideEmptyState();
      this._hideResults();
      this._hideNoResults();
      this.recentList.innerHTML = '';
      this.selectedIndex = -1;

      this.recentSearches.forEach(function (search, index) {
        const item = document.createElement('li');
        item.className = 'search-modal__recent-item';
        item.setAttribute('role', 'option');
        item.setAttribute('data-index', String(index));
        item.innerHTML =
          '<a href="' + search.href + '" class="search-modal__recent-link" tabindex="-1">' +
            '<svg class="search-modal__recent-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
              '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>' +
            '</svg>' +
            '<span class="search-modal__recent-text">' + (search.title || search.query) + '</span>' +
          '</a>' +
          '<button type="button" class="search-modal__recent-remove" data-query="' + search.query + '" title="Remove from recent">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
              '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>' +
            '</svg>' +
          '</button>';

        item.querySelector('a').addEventListener('click', function () { this.closeModal(); }.bind(this));
        item.querySelector('.search-modal__recent-remove').addEventListener('click', function (e) {
          e.stopPropagation();
          this.recentSearches = this.recentSearches.filter(function (s) { return s.query !== search.query; });
          this._saveRecentSearches();
          this._showRecentSearches();
        }.bind(this));

        this.recentList.appendChild(item);
      }.bind(this));

      this.recentSection.classList.remove('hidden');
    }

    _hideRecentSearches() {
      if (this.recentSection) this.recentSection.classList.add('hidden');
    }

    _showNoResults(query) {
      this._hideResults();
      const queryEl = this.modal.querySelector('#search-modal-no-results-query');
      if (queryEl) queryEl.textContent = query;
      if (this.noResults) this.noResults.classList.remove('hidden');
    }

    _hideNoResults() {
      if (this.noResults) this.noResults.classList.add('hidden');
    }

    _showEmptyState() {
      if (this.emptyState) this.emptyState.classList.remove('hidden');
    }

    _hideEmptyState() {
      if (this.emptyState) this.emptyState.classList.add('hidden');
    }

    _hideResults() {
      if (this.resultsList) this.resultsList.innerHTML = '';
      if (this.resultsList && this.resultsList.parentElement) {
        this.resultsList.parentElement.classList.add('hidden');
      }
      this.selectedIndex = -1;
      this.currentResults = [];
    }

    _updateStatus(message) {
      if (this.status) this.status.textContent = message;
    }

    _clearRecentSearches() {
      this.recentSearches = [];
      this._saveRecentSearches();
      this._showRecentSearches();
    }

    /* ---- Search page (full /search/ route) ---- */

    _initSearchPage() {
      const isNewLayout = document.querySelector('.search-page__container');
      if (isNewLayout) {
        this._initSearchPageNew();
      } else if (document.getElementById('search-input')) {
        this._initSearchPageLegacy();
      }
    }

    _initSearchPageNew() {
      this.pageInput = document.getElementById('search-input');
      if (!this.pageInput) return;

      this.pageClearBtn = document.getElementById('search-clear');
      this.pageResults = document.getElementById('search-results');
      this.pageResultsList = document.getElementById('search-results-list');
      this.pageResultsCount = document.getElementById('search-results-count');
      this.pageNoResults = document.getElementById('search-no-results');
      this.pageNoResultsQuery = document.getElementById('search-no-results-query');
      this.pageEmptyState = document.getElementById('search-empty');
      this.pageLoadingState = document.getElementById('search-loading');
      this.pageLoadingIndicator = document.getElementById('search-loading-indicator');
      this.pageErrorState = document.getElementById('search-error');
      this.pageFilterSection = document.getElementById('filter-section');
      this.pageFilterType = document.getElementById('filter-type');
      this.pageCurrentQuery = '';
      this.pageSelectedIndex = -1;
      this.pageResultItems = [];
      this.pageDebounceTimer = null;

      const params = new URLSearchParams(window.location.search);
      const urlQuery = params.has('q') ? params.get('q') : null;

      if (urlQuery && !indexApi().isLoaded() && !indexApi().isLoading()) {
        indexApi().load();
      }

      if (!indexApi().isLoaded()) {
        if (this.pageLoadingState) this.pageLoadingState.classList.remove('hidden');
        if (this.pageEmptyState) this.pageEmptyState.classList.add('hidden');
        window.addEventListener('searchIndexError', function () {
          if (this.pageLoadingState) this.pageLoadingState.classList.add('hidden');
          if (this.pageErrorState) this.pageErrorState.classList.remove('hidden');
        }.bind(this));
      } else {
        this._handleIndexLoaded();
      }

      this.pageInput.addEventListener('input', this._onPageInput.bind(this));
      this.pageInput.addEventListener('keydown', this._onPageKeydown.bind(this));
      if (this.pageClearBtn) {
        this.pageClearBtn.addEventListener('click', this._clearPageSearch.bind(this));
      }
      if (this.pageFilterSection) {
        this.pageFilterSection.addEventListener('change', function () {
          if (this.pageCurrentQuery) this._performPageSearch(this.pageCurrentQuery);
        }.bind(this));
      }
      if (this.pageFilterType) {
        this.pageFilterType.addEventListener('change', function () {
          if (this.pageCurrentQuery) this._performPageSearch(this.pageCurrentQuery);
        }.bind(this));
      }

      document.querySelectorAll('.search-page__suggestion').forEach(function (btn) {
        btn.addEventListener('click', function () {
          this.pageInput.value = btn.dataset.query;
          this.pageInput.dispatchEvent(new Event('input'));
          this.pageInput.focus();
        }.bind(this));
      }.bind(this));

      if (urlQuery) {
        this.pageInput.value = urlQuery;
        this.pageCurrentQuery = urlQuery;
        if (indexApi().isLoaded()) {
          this._performPageSearch(urlQuery);
        }
      }
    }

    _initSearchPageLegacy() {
      document.querySelectorAll('.popular-search-link').forEach(function (link) {
        link.addEventListener('click', function (e) {
          e.preventDefault();
          const query = link.getAttribute('data-query');
          const searchInput = document.getElementById('search-input');
          if (!searchInput) return;
          searchInput.value = query;
          searchInput.dispatchEvent(new Event('input', { bubbles: true }));
          searchInput.focus();
        });
      });

      const params = new URLSearchParams(window.location.search);
      let query = params.has('q') ? params.get('q') : '';
      if (!query && window.location.hash) {
        query = decodeURIComponent(window.location.hash.substring(1));
      }
      if (query) {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
          setTimeout(function () {
            searchInput.value = query;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            searchInput.focus();
          }, 500);
        }
      }
    }

    _populatePageFilters() {
      if (this.pageFilterSection) {
        queryApi().getAvailableSections().forEach(function (section) {
          const opt = document.createElement('option');
          opt.value = section;
          opt.textContent = section;
          this.pageFilterSection.appendChild(opt);
        }.bind(this));
      }
      if (this.pageFilterType) {
        queryApi().getAvailableTypes().forEach(function (type) {
          const opt = document.createElement('option');
          opt.value = type;
          opt.textContent = type;
          this.pageFilterType.appendChild(opt);
        }.bind(this));
      }
    }

    _onPageInput(e) {
      const query = e.target.value.trim();
      if (this.pageClearBtn) this.pageClearBtn.classList.toggle('hidden', !query);
      clearTimeout(this.pageDebounceTimer);
      this.pageDebounceTimer = setTimeout(function () {
        this._performPageSearch(query);
      }.bind(this), CONFIG.modalDebounceDelay);
    }

    _onPageKeydown(e) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          this._navigatePageResults(1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          this._navigatePageResults(-1);
          break;
        case 'Enter':
          e.preventDefault();
          this._selectPageResult();
          break;
        case 'Escape':
          if (this.pageCurrentQuery) {
            e.preventDefault();
            this._clearPageSearch();
          }
          break;
      }
    }

    _performPageSearch(query) {
      this.pageCurrentQuery = query;
      this.pageSelectedIndex = -1;
      this.pageResultItems = [];

      if (!query || query.length < CONFIG.minQueryLength) {
        this._hidePageResults();
        if (this.pageEmptyState) this.pageEmptyState.classList.remove('hidden');
        this._updatePageURL('');
        return;
      }

      if (!indexApi().isLoaded()) {
        if (this.pageEmptyState) this.pageEmptyState.classList.add('hidden');
        if (this.pageLoadingIndicator) this.pageLoadingIndicator.classList.remove('hidden');
        this._hidePageResults();
        return;
      }

      if (this.pageLoadingIndicator) this.pageLoadingIndicator.classList.add('hidden');

      const filters = {
        section: this.pageFilterSection?.value || null,
        type: this.pageFilterType?.value || null,
        tags: [],
      };

      const results = queryApi().search(query, filters);
      this._displayPageResults(results, query);
      this._updatePageURL(query);
    }

    _displayPageResults(results, query) {
      if (this.pageEmptyState) this.pageEmptyState.classList.add('hidden');
      if (this.pageResultsList) this.pageResultsList.innerHTML = '';

      if (results.length === 0) {
        if (this.pageResults) this.pageResults.classList.remove('hidden');
        if (this.pageNoResults) this.pageNoResults.classList.remove('hidden');
        if (this.pageNoResultsQuery) this.pageNoResultsQuery.textContent = query;
        return;
      }

      if (this.pageResults) this.pageResults.classList.remove('hidden');
      if (this.pageNoResults) this.pageNoResults.classList.add('hidden');
      if (this.pageResultsCount) {
        this.pageResultsCount.textContent = results.length + ' result' + (results.length !== 1 ? 's' : '');
      }

      this.pageResultItems = renderOrganizedResults(this.pageResultsList, results, {
        prefix: 'search-page',
        onSelect: function (index) {
          this.pageSelectedIndex = index;
          this._selectPageResult();
        }.bind(this),
        onToggle: function () {
          this.pageResultItems = Array.from(this.pageResultsList.querySelectorAll('.search-page__result-item'));
        }.bind(this),
      });
    }

    _navigatePageResults(direction) {
      if (this.pageResultItems.length === 0) return;

      if (this.pageSelectedIndex >= 0 && this.pageSelectedIndex < this.pageResultItems.length) {
        this.pageResultItems[this.pageSelectedIndex].classList.remove('search-page__result-item--selected');
        this.pageResultItems[this.pageSelectedIndex].setAttribute('aria-selected', 'false');
      }

      this.pageSelectedIndex += direction;
      if (this.pageSelectedIndex < 0) this.pageSelectedIndex = this.pageResultItems.length - 1;
      if (this.pageSelectedIndex >= this.pageResultItems.length) this.pageSelectedIndex = 0;

      const selected = this.pageResultItems[this.pageSelectedIndex];
      selected.classList.add('search-page__result-item--selected');
      selected.setAttribute('aria-selected', 'true');
      selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    _selectPageResult() {
      if (this.pageSelectedIndex >= 0 && this.pageSelectedIndex < this.pageResultItems.length) {
        const link = this.pageResultItems[this.pageSelectedIndex].querySelector('a');
        if (link) window.location.href = link.href;
      }
    }

    _hidePageResults() {
      if (this.pageResults) this.pageResults.classList.add('hidden');
      if (this.pageNoResults) this.pageNoResults.classList.add('hidden');
      if (this.pageResultsList) this.pageResultsList.innerHTML = '';
      this.pageSelectedIndex = -1;
      this.pageResultItems = [];
    }

    _clearPageSearch() {
      if (this.pageInput) this.pageInput.value = '';
      this.pageCurrentQuery = '';
      if (this.pageClearBtn) this.pageClearBtn.classList.add('hidden');
      if (this.pageLoadingIndicator) this.pageLoadingIndicator.classList.add('hidden');
      this._hidePageResults();
      if (this.pageEmptyState) this.pageEmptyState.classList.remove('hidden');
      this._updatePageURL('');
      if (this.pageInput) this.pageInput.focus();
    }

    _updatePageURL(query) {
      const url = new URL(window.location);
      if (query) {
        url.searchParams.set('q', query);
      } else {
        url.searchParams.delete('q');
      }
      history.replaceState({}, '', url);
    }
  });
  }

  definePaletteElement();

  window.BengalSearchPalette = {
    ShortcutsOverlay: ShortcutsOverlay,
  };
})();
