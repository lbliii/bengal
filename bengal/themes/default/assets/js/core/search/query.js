/**
 * Bengal Search — query module
 *
 * Lunr query builder, filtering, highlighting, and heading-aware result grouping.
 */
(function () {
  'use strict';

  const CONFIG = window.BengalSearchConfig;
  const escapeRegex = window.BengalUtils?.escapeRegex || function (s) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  function getIndexApi() {
    return window.BengalSearchIndex;
  }

  function isHeadingRecord(record) {
    return record && (record.kind === 'heading' || record.isHeading);
  }

  function resolveRecord(ref) {
    const api = getIndexApi();
    const data = api.getData();
    if (!data) return null;

    const page = (data.pages || []).find(function (p) {
      return (p.objectID || p.uri || p.href) === ref;
    });
    if (page) {
      return Object.assign({}, page, {
        href: page.href || page.uri,
        recordKind: 'page',
      });
    }

    const headings = data.headings || [];
    const heading = headings.find(function (h) {
      return (h.objectID || h.url || h.href) === ref;
    });
    if (heading) {
      return Object.assign({}, heading, {
        href: heading.href || heading.url,
        recordKind: 'heading',
        isHeading: true,
        kind: 'heading',
      });
    }

    return null;
  }

  function parseQueryTerms(query) {
    const rawTerms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);

    return rawTerms.map(function (term) {
      const hasOperators = /[*~+\-:]/.test(term);
      const isExact = term.startsWith('"') && term.endsWith('"');
      if (isExact) {
        term = term.slice(1, -1);
      }
      return {
        term: term,
        hasOperators: hasOperators,
        isExact: isExact,
        isShort: term.length < 4,
      };
    }).filter(function (t) { return t.term.length > 0; });
  }

  function applyFilters(results, filters) {
    let filtered = results;

    if (filters.section) {
      filtered = filtered.filter(function (r) { return r.section === filters.section; });
    }
    if (filters.type) {
      filtered = filtered.filter(function (r) { return r.type === filters.type; });
    }
    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter(function (r) {
        const pageTags = r.tags || [];
        return filters.tags.some(function (tag) { return pageTags.includes(tag); });
      });
    }
    if (filters.author) {
      filtered = filtered.filter(function (r) {
        return r.author === filters.author ||
          (r.authors && r.authors.includes(filters.author));
      });
    }
    if (filters.difficulty) {
      filtered = filtered.filter(function (r) { return r.difficulty === filters.difficulty; });
    }
    if (filters.featured) {
      filtered = filtered.filter(function (r) { return r.featured === true; });
    }

    return filtered;
  }

  function highlightMatches(text, terms) {
    if (!text || !terms.length) return text;

    const escapedTerms = terms.map(function (term) { return escapeRegex(term); }).join('|');
    const termRegex = new RegExp('(' + escapedTerms + ')', 'gi');
    const htmlTagRegex = /<[^>]+>/g;

    let result = '';
    let lastIndex = 0;
    let match;

    while ((match = htmlTagRegex.exec(text)) !== null) {
      const textBefore = text.slice(lastIndex, match.index);
      if (textBefore) {
        result += textBefore.replace(termRegex, '<mark class="' + CONFIG.highlightClass + '">$1</mark>');
      }
      result += match[0];
      lastIndex = htmlTagRegex.lastIndex;
    }

    const remainingText = text.slice(lastIndex);
    if (remainingText) {
      result += remainingText.replace(termRegex, '<mark class="' + CONFIG.highlightClass + '">$1</mark>');
    }

    return result;
  }

  function createHighlightedExcerpt(text, terms, length) {
    if (!text) return '';

    let matchPos = -1;
    terms.forEach(function (term) {
      const pos = text.toLowerCase().indexOf(term.toLowerCase());
      if (pos !== -1 && (matchPos === -1 || pos < matchPos)) {
        matchPos = pos;
      }
    });

    let excerpt;
    if (matchPos !== -1) {
      const start = Math.max(0, matchPos - Math.floor(length / 2));
      const end = Math.min(text.length, start + length);
      excerpt = text.substring(start, end);
      if (start > 0) excerpt = '...' + excerpt;
      if (end < text.length) excerpt = excerpt + '...';
    } else {
      excerpt = text.substring(0, length);
      if (text.length > length) excerpt += '...';
    }

    return highlightMatches(excerpt, terms);
  }

  function extractMatchSnippet(result, queryTerms) {
    const matchData = result.matchData;
    if (!matchData || !matchData.metadata) return null;

    const ref = result.objectID || result.ref || result.href;
    const metadata = matchData.metadata[ref];
    if (!metadata) return null;

    const fields = ['content', 'description', 'title'];
    for (let i = 0; i < fields.length; i++) {
      const fieldMeta = metadata[fields[i]];
      if (fieldMeta && fieldMeta.position && fieldMeta.position.length) {
        const positions = fieldMeta.position;
        const sourceText = result[fields[i]] || '';
        if (!sourceText) continue;

        const pos = positions[0];
        const start = Math.max(0, pos[0] - 40);
        const end = Math.min(sourceText.length, pos[0] + pos[1] + 80);
        let snippet = sourceText.substring(start, end);
        if (start > 0) snippet = '...' + snippet;
        if (end < sourceText.length) snippet = snippet + '...';
        return highlightMatches(snippet, queryTerms);
      }
    }

    return null;
  }

  function transformResults(results, query) {
    const queryTerms = query.toLowerCase().split(/\s+/).filter(Boolean);

    return results.map(function (result) {
      result.highlightedTitle = highlightMatches(result.title, queryTerms);

      const snippetSource = result.content || result.excerpt || result.description || '';
      result.highlightedExcerpt =
        extractMatchSnippet(result, queryTerms) ||
        createHighlightedExcerpt(snippetSource, queryTerms, CONFIG.excerptLength);

      if (result.date) {
        result.formattedDate = formatDate(result.date);
      }

      if (isHeadingRecord(result)) {
        result.breadcrumb = result.breadcrumb ||
          (result.parent_title ? result.parent_title + ' › ' + result.title : result.title);
      } else if (result.section) {
        result.breadcrumb = result.section + ' / ' + result.title;
      }

      if (result.type) {
        result.typeBadge = {
          text: result.type,
          class: 'badge-' + result.type,
        };
      }

      return result;
    });
  }

  function formatDate(dateStr) {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch (error) {
      return dateStr;
    }
  }

  function formatGroupName(name) {
    return name
      .split('-')
      .map(function (word) { return word.charAt(0).toUpperCase() + word.slice(1); })
      .join(' ');
  }

  function groupResults(results) {
    const groups = {};

    results.forEach(function (result) {
      let groupName = 'Other';

      if (result.dir && result.dir !== '/') {
        const pathParts = result.dir.split('/').filter(Boolean);
        if (pathParts.length > 0) {
          groupName = formatGroupName(pathParts[pathParts.length - 1]);
        }
      } else if (result.section) {
        groupName = formatGroupName(result.section);
      } else if (result.type) {
        groupName = formatGroupName(result.type);
      }

      if (!groups[groupName]) {
        groups[groupName] = [];
      }
      groups[groupName].push(result);
    });

    return Object.entries(groups)
      .map(function (entry) {
        return { name: entry[0], items: entry[1], count: entry[1].length };
      })
      .sort(function (a, b) {
        if (b.count !== a.count) return b.count - a.count;
        return a.name.localeCompare(b.name);
      });
  }

  /**
   * Attach heading deep-link hits under their parent page; surface orphan headings.
   */
  function organizeResultsWithHeadings(results) {
    const pages = [];
    const headingsByParent = new Map();
    const standaloneHeadings = [];

    results.forEach(function (result) {
      if (isHeadingRecord(result)) {
        const parentId = result.parent_objectID || result.parentObjectID;
        if (parentId) {
          if (!headingsByParent.has(parentId)) {
            headingsByParent.set(parentId, []);
          }
          headingsByParent.get(parentId).push(result);
        } else {
          standaloneHeadings.push(result);
        }
      } else {
        pages.push(result);
      }
    });

    pages.forEach(function (page) {
      const pageId = page.objectID || page.uri || page.href;
      const childHeadings = headingsByParent.get(pageId);
      if (childHeadings && childHeadings.length) {
        page.headingMatches = childHeadings;
        headingsByParent.delete(pageId);
      }
    });

    headingsByParent.forEach(function (headings) {
      headings.forEach(function (heading) {
        heading.standaloneHeading = true;
        standaloneHeadings.push(heading);
      });
    });

    return { pages: pages, standaloneHeadings: standaloneHeadings };
  }

  function groupByAutodoc(results) {
    const docs = [];
    const api = [];

    results.forEach(function (result) {
      if (result.isAutodoc) {
        api.push(result);
      } else {
        docs.push(result);
      }
    });

    return { docs: docs, api: api };
  }

  function search(query, filters) {
    filters = filters || {};
    const api = getIndexApi();
    const searchIndex = api.getIndex();
    const searchData = api.getData();

    if (!api.isLoaded() || !searchIndex || !searchData || !Array.isArray(searchData.pages)) {
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

      let results = searchIndex.query(function (q) {
        parsedTerms.forEach(function (_ref) {
          const term = _ref.term;
          const hasOperators = _ref.hasOperators;
          const isExact = _ref.isExact;
          const isShort = _ref.isShort;

          if (hasOperators) {
            q.term(term);
            return;
          }

          q.term(term, {
            boost: 10,
            usePipeline: true,
            presence: lunr.Query.presence.OPTIONAL,
          });

          if (!isExact) {
            q.term(term, {
              boost: 5,
              wildcard: lunr.Query.wildcard.TRAILING,
              usePipeline: true,
              presence: lunr.Query.presence.OPTIONAL,
            });
          }

          if (!isExact && !isShort) {
            q.term(term, {
              boost: 1,
              editDistance: 1,
              usePipeline: true,
              presence: lunr.Query.presence.OPTIONAL,
            });
          }
        });
      });

      results = results.map(function (result) {
        const record = resolveRecord(result.ref);
        if (record) {
          return Object.assign({}, record, {
            score: result.score,
            matchData: result.matchData,
            ref: result.ref,
          });
        }
        return null;
      }).filter(Boolean);

      results = applyFilters(results, filters);
      results = transformResults(results, query);
      results = results.slice(0, CONFIG.maxResults);

      return results;
    } catch (error) {
      console.error('Search error:', error);
      return [];
    }
  }

  function getUniqueValues(field) {
    const api = getIndexApi();
    const searchData = api.getData();
    if (!searchData || !Array.isArray(searchData.pages)) return [];

    const values = new Set();
    searchData.pages.forEach(function (page) {
      const value = page[field];
      if (value) {
        if (Array.isArray(value)) {
          value.forEach(function (v) { values.add(v); });
        } else {
          values.add(value);
        }
      }
    });

    return Array.from(values).sort();
  }

  function getAvailableSections() {
    return getUniqueValues('section');
  }

  function getAvailableTypes() {
    return getUniqueValues('type');
  }

  function getAvailableTags() {
    return getUniqueValues('tags');
  }

  function getAvailableAuthors() {
    const api = getIndexApi();
    const searchData = api.getData();
    const authors = new Set();

    if (searchData && Array.isArray(searchData.pages)) {
      searchData.pages.forEach(function (page) {
        if (page.author) authors.add(page.author);
        if (page.authors) page.authors.forEach(function (a) { authors.add(a); });
      });
    }

    return Array.from(authors).sort();
  }

  window.BengalSearchQuery = {
    search: search,
    groupResults: groupResults,
    groupByAutodoc: groupByAutodoc,
    organizeResultsWithHeadings: organizeResultsWithHeadings,
    getAvailableSections: getAvailableSections,
    getAvailableTypes: getAvailableTypes,
    getAvailableTags: getAvailableTags,
    getAvailableAuthors: getAvailableAuthors,
    highlightMatches: highlightMatches,
    formatDate: formatDate,
    isHeadingRecord: isHeadingRecord,
  };
})();
