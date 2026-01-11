/**
 * Bengal SSG - Link Previews
 *
 * Wikipedia-style hover cards powered by per-page JSON.
 * Shows title, excerpt, reading time, and tags when hovering over internal links.
 *
 * Features:
 * - Self-sufficient: works with or without config bridge
 * - Auto-detects if JSON files are available
 * - Prefetch on hover intent (50ms before showing)
 * - LRU cache (50 entries)
 * - AbortController for rapid navigation
 * - Mobile long-press support (500ms threshold)
 * - Keyboard accessible (focus shows preview, Escape closes)
 * - Respects prefers-reduced-motion
 * - Cross-site previews for whitelisted hosts (RFC: Cross-Site Link Previews)
 *
 * @module enhancements/link-previews
 * @see plan/drafted/rfc-link-previews.md
 * @see plan/rfc-cross-site-xref-link-previews.md
 */

(function () {
  'use strict';

  // ============================================================
  // Configuration (with sensible defaults, overridable via config bridge)
  // ============================================================

  function getConfig() {
    // Try to read from config bridge first
    const el = document.getElementById('bengal-config');
    if (el) {
      try {
        const cfg = JSON.parse(el.textContent);
        if (cfg?.linkPreviews) {
          return cfg.linkPreviews;
        }
      } catch (err) {
        console.warn('[LinkPreviews] Failed to parse config bridge:', err);
      }
    }

    // Check for data attribute on html/body as alternative config
    const dataEnabled = document.documentElement.dataset.linkPreviews ||
                        document.body?.dataset.linkPreviews;
    if (dataEnabled === 'false') {
      return { enabled: false };
    }

    // Default: enabled with sensible defaults (will verify JSON availability)
    return { enabled: true };
  }

  const userConfig = getConfig();

  // Exit early if explicitly disabled
  if (userConfig.enabled === false) {
    return;
  }

  const CONFIG = {
    debug: userConfig.debug ?? (window.Bengal?.debug) ?? false,
    hoverDelay: userConfig.hoverDelay ?? 200,
    hideDelay: userConfig.hideDelay ?? 150,
    prefetchDelay: 50,
    maxCacheSize: 50,
    maxExcerptLength: 200,
    previewWidth: 320,
    longPressDelay: 500,
    showSection: userConfig.showSection ?? true,
    showReadingTime: userConfig.showReadingTime ?? true,
    showWordCount: userConfig.showWordCount ?? true,
    showDate: userConfig.showDate ?? true,
    showTags: userConfig.showTags ?? true,
    maxTags: userConfig.maxTags ?? 3,
    includeSelectors: userConfig.includeSelectors ?? ['.prose', '.content', 'article', 'main'],
    excludeSelectors: userConfig.excludeSelectors ?? [
      'nav', '.toc', '.breadcrumb', '.pagination', '.card',
      "[class*='-card']", '.tab-nav', "[class*='-widget']",
      '.child-items', '.content-tiles'
    ],
    // Cross-site preview configuration (RFC: Cross-Site Link Previews)
    allowedHosts: userConfig.allowedHosts ?? [],
    allowedSchemes: userConfig.allowedSchemes ?? ['https'],
    hostFailureThreshold: userConfig.hostFailureThreshold ?? 3,
  };

  // ============================================================
  // State
  // ============================================================

  const cache = new Map();
  let activePreview = null;
  let activeLink = null;
  let hoverTimeout = null;
  let hideTimeout = null;
  let prefetchTimeout = null;
  let pendingFetch = null;
  let jsonAvailable = null; // Will be set after first fetch attempt

  // Touch/long-press state
  let touchTimeout = null;
  let touchStartTime = 0;
  let touchStartPos = { x: 0, y: 0 };

  // Cross-site failure tracking (RFC: Cross-Site Link Previews)
  const hostFailures = new Map();  // host -> failure count
  const disabledHosts = new Set(); // hosts disabled due to repeated failures

  // ============================================================
  // Utility Functions
  // ============================================================

  /**
   * Convert page URL to JSON URL
   * /docs/getting-started/ → /docs/getting-started/index.json
   * /docs/getting-started → /docs/getting-started/index.json
   * /docs/page.html → /docs/page.json
   */
  function toJsonUrl(pageUrl) {
    // If it ends in .html, swap for .json
    if (pageUrl.endsWith('.html')) {
      return pageUrl.replace(/\.html$/, '.json');
    }
    // Handle directory-style URLs
    let url = pageUrl.replace(/\/$/, '');
    if (!url || url === '') {
      return '/index.json';
    }
    return url + '/index.json';
  }

  /**
   * Check if a link is to a cross-origin host
   */
  function isCrossOrigin(link) {
    return link.hostname !== window.location.hostname;
  }

  /**
   * Check if a cross-origin host is allowed for previews
   */
  function isAllowedCrossOrigin(link) {
    // Check if host is in allowed list
    const isAllowedHost = CONFIG.allowedHosts.includes(link.hostname);
    if (!isAllowedHost) return false;

    // Check if scheme is allowed (strip trailing colon from protocol)
    const scheme = link.protocol.replace(':', '');
    const isAllowedScheme = CONFIG.allowedSchemes.includes(scheme);
    if (!isAllowedScheme) return false;

    // Check if host has been disabled due to failures
    if (disabledHosts.has(link.hostname)) return false;

    return true;
  }

  /**
   * Check if link should have preview (only regular text links in content)
   */
  function isPreviewable(link) {
    // Skip if JSON not available for same-origin (detected after first fetch)
    if (jsonAvailable === false && !isCrossOrigin(link)) return false;

    // Check origin: same-host OR whitelisted cross-origin
    const isSameHost = !isCrossOrigin(link);
    if (!isSameHost && !isAllowedCrossOrigin(link)) return false;

    // Skip anchors on same page, downloads, opt-out links
    if (link.hash && link.pathname === window.location.pathname) return false;
    if (link.hasAttribute('download')) return false;
    if (link.dataset.noPreview !== undefined) return false;
    if (link.closest('.link-preview')) return false;

    // Include only links inside content areas
    const includeSelector = CONFIG.includeSelectors.join(', ');
    if (includeSelector && !link.closest(includeSelector)) return false;

    // Skip links inside excluded selectors
    const excludeSelector = CONFIG.excludeSelectors.join(', ');
    if (excludeSelector && link.closest(excludeSelector)) return false;

    // ========================================
    // Only regular text links (no buttons/cards/icons)
    // ========================================

    // Skip button-styled links
    if (link.classList.contains('btn') ||
        link.classList.contains('button') ||
        link.className.includes('btn-') ||
        link.className.includes('button-') ||
        link.getAttribute('role') === 'button') {
      return false;
    }

    // Skip card links (the whole card is clickable)
    if (link.classList.contains('card') ||
        link.className.includes('-card') ||
        link.closest('.card-link, .card-body > a:only-child')) {
      return false;
    }

    // Skip links with icons (not plain text)
    if (link.querySelector('svg, img, .icon, [class*="icon"]')) {
      return false;
    }

    // Skip links that are just bare URLs (text matches href)
    const linkText = link.textContent.trim();
    if (linkText.startsWith('http://') ||
        linkText.startsWith('https://') ||
        linkText.startsWith('www.')) {
      return false;
    }

    // Skip links with no meaningful text (just whitespace or empty)
    if (!linkText || linkText.length < 2) {
      return false;
    }

    return true;
  }

  /**
   * LRU cache eviction
   */
  function cacheSet(key, value) {
    if (cache.size >= CONFIG.maxCacheSize) {
      const firstKey = cache.keys().next().value;
      cache.delete(firstKey);
    }
    cache.set(key, value);
  }

  function generateId() {
    return 'link-preview-' + Math.random().toString(36).slice(2, 9);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ============================================================
  // Fetch Manager
  // ============================================================

  /**
   * Track a failure for a host and disable if threshold reached
   */
  function recordHostFailure(host) {
    const count = (hostFailures.get(host) || 0) + 1;
    hostFailures.set(host, count);

    if (count >= CONFIG.hostFailureThreshold) {
      disabledHosts.add(host);
      console.info(`[LinkPreviews] Host ${host} disabled after ${count} consecutive failures`);
    }
  }

  /**
   * Clear failure count for a host (on successful fetch)
   */
  function clearHostFailures(host) {
    hostFailures.delete(host);
  }

  async function fetchPreviewData(url, link) {
    // Build full URL for cross-origin, use path for same-origin cache key
    const isCross = link && isCrossOrigin(link);
    const cacheKey = isCross ? link.href : url;

    if (cache.has(cacheKey)) {
      return cache.get(cacheKey);
    }

    // Check if host is disabled
    if (link && disabledHosts.has(link.hostname)) {
      return null;
    }

    if (pendingFetch && pendingFetch.url !== cacheKey) {
      pendingFetch.controller.abort();
    }

    const controller = new AbortController();
    pendingFetch = { url: cacheKey, controller };

    try {
      // Build JSON URL - for cross-origin, use full absolute URL
      let jsonUrl;
      if (isCross) {
        jsonUrl = toJsonUrl(link.href);
      } else {
        jsonUrl = toJsonUrl(url);
      }

      if (CONFIG.debug) console.log('[LinkPreviews] Fetching:', jsonUrl, isCross ? '(cross-origin)' : '');

      // Build fetch options
      const fetchOptions = { signal: controller.signal };

      // Cross-origin: explicit no-credentials, CORS mode for security
      if (isCross) {
        fetchOptions.credentials = 'omit';
        fetchOptions.mode = 'cors';
      }

      const response = await fetch(jsonUrl, fetchOptions);

      if (!response.ok) {
        // Track failure for cross-origin hosts
        if (isCross) {
          recordHostFailure(link.hostname);
        }

        // If 404 on same-origin first fetch, JSON files probably don't exist
        if (response.status === 404 && !isCross && jsonAvailable === null) {
          console.info('[LinkPreviews] JSON files not available, feature disabled');
          jsonAvailable = false;
          return null;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      // JSON is available for same-origin!
      if (!isCross && jsonAvailable === null) {
        jsonAvailable = true;
        if (CONFIG.debug) console.log('[LinkPreviews] JSON files detected, feature active');
      }

      // Clear failure count on success
      if (isCross) {
        clearHostFailures(link.hostname);
      }

      const data = await response.json();
      cacheSet(cacheKey, data);
      pendingFetch = null;
      return data;
    } catch (error) {
      pendingFetch = null;

      if (error.name === 'AbortError') return null;

      // Track failure for cross-origin hosts (CORS errors, network errors, parse errors)
      if (isCross && link) {
        recordHostFailure(link.hostname);
      }

      if (CONFIG.debug) {
        console.warn('[LinkPreviews] Fetch failed:', cacheKey, error.message);
      }

      cacheSet(cacheKey, null);
      return null;
    }
  }

  function prefetch(link) {
    // Build cache key based on origin
    const cacheKey = isCrossOrigin(link) ? link.href : link.pathname;
    if (cache.has(cacheKey)) return;

    clearTimeout(prefetchTimeout);
    prefetchTimeout = setTimeout(() => {
      fetchPreviewData(link.pathname, link);
    }, CONFIG.prefetchDelay);
  }

  // ============================================================
  // Render Manager
  // ============================================================

  function createPreviewCard(data, link) {
    if (!data) return null;
    if (activePreview && activeLink === link) return activePreview;

    const preview = document.createElement('div');
    preview.className = 'link-preview';
    preview.id = generateId();
    preview.setAttribute('role', 'tooltip');
    link.setAttribute('aria-describedby', preview.id);

    let html = '';

    if (CONFIG.showSection && data.section) {
      html += `<div class="link-preview__section">${escapeHtml(data.section)}</div>`;
    }

    html += `<h4 class="link-preview__title">${escapeHtml(data.title || 'Untitled')}</h4>`;

    const excerpt = data.excerpt || data.description || '';
    if (excerpt) {
      html += `<p class="link-preview__excerpt">${escapeHtml(excerpt)}</p>`;
    }

    const metaParts = [];
    if (CONFIG.showReadingTime && data.reading_time) {
      metaParts.push(`<span class="link-preview__meta-item">${data.reading_time} min read</span>`);
    }
    if (CONFIG.showWordCount && data.word_count) {
      const formatted = data.word_count >= 1000
        ? `${(data.word_count / 1000).toFixed(1)}k`
        : data.word_count;
      metaParts.push(`<span class="link-preview__meta-item">${formatted} words</span>`);
    }
    if (CONFIG.showDate && data.date) {
      const date = new Date(data.date);
      const formatted = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      metaParts.push(`<span class="link-preview__meta-item">${formatted}</span>`);
    }
    if (metaParts.length > 0) {
      html += `<div class="link-preview__meta">${metaParts.join(' · ')}</div>`;
    }

    if (CONFIG.showTags && data.tags && data.tags.length > 0) {
      const tagsHtml = data.tags.slice(0, CONFIG.maxTags).map(tag =>
        `<span class="link-preview__tag">${escapeHtml(tag)}</span>`
      ).join('');
      html += `<div class="link-preview__tags">${tagsHtml}</div>`;
    }

    preview.innerHTML = html;
    document.body.appendChild(preview);
    positionPreview(link, preview);

    preview.addEventListener('pointerenter', cancelHide);
    preview.addEventListener('pointerleave', scheduleHide);

    return preview;
  }

  function positionPreview(link, preview) {
    const linkRect = link.getBoundingClientRect();
    const previewRect = preview.getBoundingClientRect();
    const margin = 8;
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;
    const scrollX = window.pageXOffset || document.documentElement.scrollLeft;

    const spaceAbove = linkRect.top;
    let top;

    if (spaceAbove >= previewRect.height + margin) {
      top = linkRect.top + scrollY - previewRect.height - margin;
      preview.classList.add('link-preview--above');
      preview.classList.remove('link-preview--below');
    } else {
      top = linkRect.bottom + scrollY + margin;
      preview.classList.add('link-preview--below');
      preview.classList.remove('link-preview--above');
    }

    let left = linkRect.left + scrollX + (linkRect.width / 2) - (CONFIG.previewWidth / 2);
    left = Math.max(margin, Math.min(left, window.innerWidth + scrollX - CONFIG.previewWidth - margin));

    preview.style.top = `${top}px`;
    preview.style.left = `${left}px`;
  }

  function destroyPreview() {
    if (activeLink) {
      activeLink.removeAttribute('aria-describedby');
    }
    if (activePreview) {
      activePreview.remove();
      activePreview = null;
    }
    activeLink = null;
  }

  // ============================================================
  // Event Handlers
  // ============================================================

  function scheduleShow(link) {
    if (link === activeLink) {
      cancelHide();
      return;
    }

    cancelShow();
    cancelHide();

    if (activePreview) {
      destroyPreview();
    }

    activeLink = link;

    hoverTimeout = setTimeout(async () => {
      hoverTimeout = null;
      if (activeLink !== link) return;

      const data = await fetchPreviewData(link.pathname, link);

      if (data && activeLink === link && !activePreview) {
        activePreview = createPreviewCard(data, link);
      }
    }, CONFIG.hoverDelay);
  }

  function scheduleHide() {
    cancelShow();
    hideTimeout = setTimeout(() => {
      destroyPreview();
    }, CONFIG.hideDelay);
  }

  function cancelShow() {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
      hoverTimeout = null;
    }
    if (prefetchTimeout) {
      clearTimeout(prefetchTimeout);
      prefetchTimeout = null;
    }
    if (!activePreview) {
      activeLink = null;
    }
  }

  function cancelHide() {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      hideTimeout = null;
    }
  }

  function handleMouseOver(event) {
    if (!event.target || typeof event.target.closest !== 'function') return;

    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    if (link === activeLink) {
      cancelHide();
      if (!activePreview && !hoverTimeout) {
        scheduleShow(link);
      }
      return;
    }

    prefetch(link);
    scheduleShow(link);
  }

  function handleMouseOut(event) {
    if (!event.target || typeof event.target.closest !== 'function') return;

    const link = event.target.closest('a');
    if (!link) return;

    const relatedTarget = event.relatedTarget;
    if (relatedTarget && typeof relatedTarget.closest === 'function') {
      if (link.contains(relatedTarget)) return;
      if (activePreview && activePreview.contains(relatedTarget)) return;
    }

    scheduleHide();
  }

  function handleFocusIn(event) {
    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;
    scheduleShow(link);
  }

  function handleFocusOut() {
    scheduleHide();
  }

  function handleKeyDown(event) {
    if (event.key === 'Escape' && activePreview) {
      destroyPreview();
    }
  }

  function handleTouchStart(event) {
    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    touchStartTime = Date.now();
    touchStartPos = {
      x: event.touches[0].clientX,
      y: event.touches[0].clientY
    };

    prefetch(link);

    touchTimeout = setTimeout(async () => {
      event.preventDefault();
      const data = await fetchPreviewData(link.pathname, link);
      if (data && !activePreview) {
        activeLink = link;
        activePreview = createPreviewCard(data, link);
        if (navigator.vibrate) navigator.vibrate(10);
      }
    }, CONFIG.longPressDelay);
  }

  function handleTouchMove(event) {
    if (!touchTimeout) return;
    const touch = event.touches[0];
    const deltaX = Math.abs(touch.clientX - touchStartPos.x);
    const deltaY = Math.abs(touch.clientY - touchStartPos.y);
    if (deltaX > 10 || deltaY > 10) {
      clearTimeout(touchTimeout);
      touchTimeout = null;
    }
  }

  function handleTouchEnd(event) {
    clearTimeout(touchTimeout);
    if (Date.now() - touchStartTime < CONFIG.longPressDelay) {
      if (activePreview) {
        event.preventDefault();
        destroyPreview();
      }
      return;
    }
    if (activePreview) {
      event.preventDefault();
    }
  }

  function handleDocumentClick(event) {
    if (!activePreview) return;
    if (!activePreview.contains(event.target) &&
        activeLink !== event.target &&
        !activeLink?.contains(event.target)) {
      destroyPreview();
    }
  }

  // ============================================================
  // Initialization
  // ============================================================

  let initialized = false;

  function init() {
    if (initialized) return;
    initialized = true;

    if (CONFIG.debug) {
      console.log('[LinkPreviews] Initializing with config:', CONFIG);
    }

    document.addEventListener('mouseover', handleMouseOver);
    document.addEventListener('mouseout', handleMouseOut);
    document.addEventListener('focusin', handleFocusIn, true);
    document.addEventListener('focusout', handleFocusOut, true);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: false });
    document.addEventListener('click', handleDocumentClick);

    // SPA cleanup
    document.addEventListener('turbo:before-visit', destroyPreview);
    document.addEventListener('astro:before-preparation', destroyPreview);

    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        if (activePreview && activeLink) {
          positionPreview(activeLink, activePreview);
        }
      }, 100);
    });
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export for debugging
  window.BengalLinkPreviews = {
    destroy: destroyPreview,
    clearCache: () => cache.clear(),
    getConfig: () => ({ ...CONFIG }),
    isActive: () => jsonAvailable,
    // Cross-site debugging helpers
    getDisabledHosts: () => [...disabledHosts],
    getHostFailures: () => Object.fromEntries(hostFailures),
    resetHost: (host) => {
      disabledHosts.delete(host);
      hostFailures.delete(host);
    }
  };

})();
