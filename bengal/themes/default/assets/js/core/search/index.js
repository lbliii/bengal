/**
 * Bengal Search — index loading module
 *
 * Loads pre-built Lunr index (search-index.json) or builds at runtime from index.json.
 * Emits searchIndexLoaded / searchIndexError events.
 */
(function () {
  'use strict';

  const CONFIG = window.BengalSearchConfig;
  const log = window.BengalUtils?.log || (() => {});

  let searchIndex = null;
  let searchData = null;
  let isIndexLoaded = false;
  let isIndexLoading = false;
  let preloadTriggered = false;

  function resolveBaseUrl() {
    let baseurl = '';
    try {
      const m = document.querySelector('meta[name="bengal:baseurl"]');
      baseurl = (m && m.getAttribute('content')) || '';
    } catch (e) { /* no-op */ }
    return baseurl.replace(/\/$/, '');
  }

  function buildIndexUrl(filename, baseurl) {
    let url = '/' + filename;
    if (baseurl) {
      url = baseurl + url;
    }
    return url;
  }

  function detectCurrentVersion() {
    const meta = document.querySelector('meta[name="bengal:version"]');
    if (meta) {
      return meta.getAttribute('content');
    }
    const match = window.location.pathname.match(/\/docs\/(v\d+)\//);
    return match ? match[1] : null;
  }

  function buildVersionedIndexUrl(baseurl) {
    const version = detectCurrentVersion();
    if (!version) {
      return buildIndexUrl('index.json', baseurl);
    }
    return buildIndexUrl(`docs/${version}/index.json`, baseurl);
  }

  function addPagesToLunrBuilder(builder, pages) {
    pages.forEach(function (page) {
      if (!page.search_exclude && !page.draft) {
        builder.add({
          objectID: page.objectID || page.href,
          title: page.title || '',
          description: page.description || '',
          content: page.content || page.excerpt || '',
          tags: (page.tags || []).join(' '),
          section: page.section || '',
          author: page.author || (page.authors && page.authors.join(' ')) || '',
          search_keywords: (page.search_keywords || []).join(' '),
          kind: page.kind || page.type || '',
        });
      }
    });
  }

  function addHeadingsToLunrBuilder(builder, headings) {
    if (!Array.isArray(headings)) return;
    headings.forEach(function (heading) {
      if (!heading.title) return;
      builder.add({
        objectID: heading.objectID || heading.url || '',
        title: heading.title || '',
        description: heading.breadcrumb || '',
        content: heading.content || '',
        tags: '',
        section: heading.section || '',
        author: '',
        search_keywords: '',
        kind: 'heading',
        anchor: heading.anchor || '',
        parent_objectID: heading.parent_objectID || '',
        url: heading.url || heading.href || '',
      });
    });
  }

  function buildRuntimeLunrIndex(data) {
    return lunr(function () {
      this.ref('objectID');
      this.field('title', { boost: 10 });
      this.field('description', { boost: 5 });
      this.field('content', { boost: 1 });
      this.field('tags', { boost: 3 });
      this.field('section', { boost: 2 });
      this.field('author', { boost: 2 });
      this.field('search_keywords', { boost: 8 });
      this.field('kind', { boost: 1 });

      addPagesToLunrBuilder(this, data.pages || []);
      addHeadingsToLunrBuilder(this, data.headings || []);
    });
  }

  async function tryLoadPrebuiltIndex(baseurl) {
    try {
      const metaTag = document.querySelector('meta[name="bengal:search_index_url"]');
      if (!metaTag) {
        log('Pre-built index not available (lunr not installed)');
        return false;
      }

      const version = detectCurrentVersion();
      let prebuiltUrl = '';
      if (version) {
        prebuiltUrl = buildIndexUrl(`docs/${version}/search-index.json`, baseurl);
      } else {
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

      if (typeof lunr === 'undefined' || !lunr.Index) {
        log('Lunr.js not available for pre-built index');
        return false;
      }

      searchIndex = lunr.Index.load(prebuiltData);

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

  async function loadAndBuildRuntimeIndex(baseurl) {
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
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid search index: expected object, got ' + typeof data);
    }
    if (!Array.isArray(data.pages)) {
      throw new Error('Invalid search index: missing or invalid "pages" array');
    }

    searchData = data;
    searchIndex = buildRuntimeLunrIndex(data);

    const headingCount = Array.isArray(data.headings) ? data.headings.length : 0;
    log(`Search index loaded (runtime): ${data.pages.length} pages${headingCount ? `, ${headingCount} headings` : ''}`);
  }

  async function loadSearchIndex() {
    if (isIndexLoaded || isIndexLoading) return;

    isIndexLoading = true;

    try {
      const baseurl = resolveBaseUrl();

      if (CONFIG.usePrebuilt) {
        const prebuiltLoaded = await tryLoadPrebuiltIndex(baseurl);
        if (prebuiltLoaded) {
          isIndexLoaded = true;
          isIndexLoading = false;
          window.dispatchEvent(new CustomEvent('searchIndexLoaded', {
            detail: {
              pages: searchData.pages.length,
              headings: (searchData.headings || []).length,
              prebuilt: true,
            },
          }));
          return;
        }
      }

      await loadAndBuildRuntimeIndex(baseurl);
      isIndexLoaded = true;
      isIndexLoading = false;

      window.dispatchEvent(new CustomEvent('searchIndexLoaded', {
        detail: {
          pages: searchData.pages.length,
          headings: (searchData.headings || []).length,
          prebuilt: false,
        },
      }));
    } catch (error) {
      console.error('Failed to load search index:', error);
      isIndexLoading = false;
      window.dispatchEvent(new CustomEvent('searchIndexError', {
        detail: { error: error.message },
      }));
    }
  }

  function preloadSearch() {
    if (preloadTriggered || !window.BengalSearch) return;
    preloadTriggered = true;
    log('Preloading search index...');
    loadSearchIndex();
  }

  function setupSmartPreload() {
    const searchTriggers = document.querySelectorAll(
      'a[href$="/search/"], a[href*="search"], .nav-search-trigger, #nav-search-trigger'
    );
    searchTriggers.forEach(function (el) {
      el.addEventListener('mouseenter', preloadSearch, { once: true });
      el.addEventListener('focus', preloadSearch, { once: true });
    });

    document.addEventListener('keydown', function (e) {
      if (e.metaKey || e.ctrlKey) {
        preloadSearch();
      }
    }, { once: true });
  }

  function initPreload() {
    const metaEl = document.querySelector('meta[name="bengal:search_preload"]');
    const preloadMode = (metaEl && metaEl.getAttribute('content')) || 'smart';

    if (preloadMode === 'immediate') {
      preloadSearch();
    } else if (preloadMode === 'smart') {
      setupSmartPreload();
    }
  }

  window.BengalSearchIndex = {
    CONFIG: CONFIG,
    load: loadSearchIndex,
    preload: preloadSearch,
    initPreload: initPreload,
    resolveBaseUrl: resolveBaseUrl,
    isLoaded: function () { return isIndexLoaded; },
    isLoading: function () { return isIndexLoading; },
    getIndex: function () { return searchIndex; },
    getData: function () { return searchData; },
  };
})();
