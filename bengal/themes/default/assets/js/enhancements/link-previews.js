/**
 * Bengal SSG - Link Previews
 *
 * Wikipedia-style hover cards powered by per-page JSON.
 * Shows title, excerpt, reading time, and tags when hovering over internal links.
 *
 * Features:
 * - Prefetch on hover intent (50ms before showing)
 * - LRU cache (50 entries)
 * - AbortController for rapid navigation
 * - Mobile long-press support (500ms threshold)
 * - Keyboard accessible (focus shows preview, Escape closes)
 * - Respects prefers-reduced-motion
 *
 * @module enhancements/link-previews
 * @see plan/drafted/rfc-link-previews.md
 */

(function () {
  'use strict';

  // ============================================================
  // Feature Detection & Configuration
  // ============================================================

  function getBengalConfig() {
    const el = document.getElementById('bengal-config');
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch {
      return null;
    }
  }

  const bengalConfig = getBengalConfig();
  const previewConfig = bengalConfig?.linkPreviews;

  // Exit early if link previews not enabled
  if (!previewConfig?.enabled) {
    return;
  }

  // ============================================================
  // Configuration (from server config or defaults)
  // ============================================================

  const CONFIG = {
    hoverDelay: previewConfig.hoverDelay ?? 200,
    hideDelay: previewConfig.hideDelay ?? 150,
    prefetchDelay: 50,
    maxCacheSize: 50,
    maxExcerptLength: 200,
    previewWidth: 320,
    longPressDelay: 500,
    showSection: previewConfig.showSection ?? true,
    showReadingTime: previewConfig.showReadingTime ?? true,
    showWordCount: previewConfig.showWordCount ?? true,
    showDate: previewConfig.showDate ?? true,
    showTags: previewConfig.showTags ?? true,
    maxTags: previewConfig.maxTags ?? 3,
    includeSelectors: previewConfig.includeSelectors ?? ['.prose'],
    excludeSelectors: previewConfig.excludeSelectors ?? [
      'nav', '.toc', '.breadcrumb', '.pagination'
    ],
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

  // Touch/long-press state
  let touchTimeout = null;
  let touchStartTime = 0;
  let touchStartPos = { x: 0, y: 0 };

  // ============================================================
  // Utility Functions
  // ============================================================

  /**
   * Convert page URL to JSON URL
   * /docs/getting-started/ → /docs/getting-started/index.json
   * /docs/getting-started → /docs/getting-started/index.json
   * /docs/page.html → /docs/page/index.json
   */
  function toJsonUrl(pageUrl) {
    // Normalize: remove trailing index.html and trailing slash
    let url = pageUrl
      .replace(/\/?index\.html$/, '')
      .replace(/\.html$/, '')
      .replace(/\/$/, '');

    // Handle empty path (root)
    if (!url || url === '') {
      url = '';
    }

    // Always append /index.json
    return url + '/index.json';
  }

  /**
   * Check if link should have preview
   */
  function isPreviewable(link) {
    // Internal links only
    if (link.hostname !== window.location.hostname) return false;

    // Skip anchors on same page, downloads, opt-out links
    if (link.hash && link.pathname === window.location.pathname) return false;
    if (link.hasAttribute('download')) return false;
    if (link.dataset.noPreview !== undefined) return false;
    if (link.closest('.link-preview')) return false; // Prevent nesting

    // Include only links inside prose sections (if configured)
    const includeSelector = CONFIG.includeSelectors.join(', ');
    if (includeSelector && !link.closest(includeSelector)) return false;

    // Skip links inside excluded selectors (nav, toc, etc.)
    const excludeSelector = CONFIG.excludeSelectors.join(', ');
    if (excludeSelector && link.closest(excludeSelector)) return false;

    return true;
  }

  /**
   * LRU cache eviction
   */
  function cacheSet(key, value) {
    if (cache.size >= CONFIG.maxCacheSize) {
      // Delete oldest entry
      const firstKey = cache.keys().next().value;
      cache.delete(firstKey);
    }
    cache.set(key, value);
  }

  /**
   * Generate unique ID for ARIA association
   */
  function generateId() {
    return 'link-preview-' + Math.random().toString(36).slice(2, 9);
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ============================================================
  // Fetch Manager
  // ============================================================

  async function fetchPreviewData(url) {
    // Check cache first
    if (cache.has(url)) {
      return cache.get(url);
    }

    // Abort any pending fetch for a different URL
    if (pendingFetch && pendingFetch.url !== url) {
      pendingFetch.controller.abort();
    }

    const controller = new AbortController();
    pendingFetch = { url, controller };

    try {
      const jsonUrl = toJsonUrl(url);
      const response = await fetch(jsonUrl, { signal: controller.signal });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      cacheSet(url, data);
      pendingFetch = null;
      return data;
    } catch (error) {
      pendingFetch = null;

      // Don't cache aborted requests
      if (error.name === 'AbortError') {
        return null;
      }

      // Cache failures to avoid repeated requests
      cacheSet(url, null);
      return null;
    }
  }

  /**
   * Prefetch on hover intent (before showing preview)
   */
  function prefetch(url) {
    if (cache.has(url)) return;

    clearTimeout(prefetchTimeout);
    prefetchTimeout = setTimeout(() => {
      fetchPreviewData(url);
    }, CONFIG.prefetchDelay);
  }

  // ============================================================
  // Render Manager
  // ============================================================

  function createPreviewCard(data, link) {
    if (!data) return null;

    const preview = document.createElement('div');
    preview.className = 'link-preview';
    preview.id = generateId();
    preview.setAttribute('role', 'tooltip');

    // Associate with link for accessibility
    link.setAttribute('aria-describedby', preview.id);

    // Build content
    let html = '';

    // Section badge (optional)
    if (CONFIG.showSection && data.section) {
      html += `<div class="link-preview__section">📚 ${escapeHtml(data.section)}</div>`;
    }

    // Title
    html += `<h4 class="link-preview__title">${escapeHtml(data.title || 'Untitled')}</h4>`;

    // Excerpt
    const excerpt = data.excerpt || data.description || '';
    if (excerpt) {
      html += `<p class="link-preview__excerpt">${escapeHtml(excerpt)}</p>`;
    }

    // Metadata row
    const metaParts = [];
    if (CONFIG.showReadingTime && data.reading_time) {
      metaParts.push(`<span class="link-preview__meta-item">📖 ${data.reading_time} min</span>`);
    }
    if (CONFIG.showWordCount && data.word_count) {
      const formatted = data.word_count >= 1000
        ? `${(data.word_count / 1000).toFixed(1)}k`
        : data.word_count;
      metaParts.push(`<span class="link-preview__meta-item">📝 ${formatted} words</span>`);
    }
    if (CONFIG.showDate && data.date) {
      const date = new Date(data.date);
      const formatted = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      metaParts.push(`<span class="link-preview__meta-item">📅 ${formatted}</span>`);
    }
    if (metaParts.length > 0) {
      html += `<div class="link-preview__meta">${metaParts.join('')}</div>`;
    }

    // Tags
    if (CONFIG.showTags && data.tags && data.tags.length > 0) {
      const tagsHtml = data.tags.slice(0, CONFIG.maxTags).map(tag =>
        `<span class="link-preview__tag">#${escapeHtml(tag)}</span>`
      ).join('');
      html += `<div class="link-preview__tags">${tagsHtml}</div>`;
    }

    preview.innerHTML = html;

    // Position and add to DOM
    document.body.appendChild(preview);
    positionPreview(link, preview);

    // Allow pointer events on preview (so user can hover to keep it open)
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

    // Vertical positioning
    const spaceAbove = linkRect.top;
    const spaceBelow = window.innerHeight - linkRect.bottom;

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

    // Horizontal positioning (centered, clamped)
    let left = linkRect.left + scrollX + (linkRect.width / 2) - (CONFIG.previewWidth / 2);
    left = Math.max(margin, Math.min(left, window.innerWidth + scrollX - CONFIG.previewWidth - margin));

    preview.style.top = `${top}px`;
    preview.style.left = `${left}px`;
  }

  function destroyPreview() {
    if (activePreview) {
      // Remove ARIA association
      if (activeLink) {
        activeLink.removeAttribute('aria-describedby');
      }
      activePreview.remove();
      activePreview = null;
      activeLink = null;
    }
  }

  // ============================================================
  // Event Handlers
  // ============================================================

  function scheduleShow(link) {
    cancelShow();
    cancelHide();

    hoverTimeout = setTimeout(async () => {
      const data = await fetchPreviewData(link.pathname);
      if (data && !activePreview) {
        activeLink = link;
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
    clearTimeout(hoverTimeout);
    clearTimeout(prefetchTimeout);
  }

  function cancelHide() {
    clearTimeout(hideTimeout);
  }

  // Mouse events for hover (mouseover/mouseout bubble, so event delegation works)
  // Note: pointerenter/pointerleave do NOT bubble, so event delegation fails with them
  function handleMouseOver(event) {
    // Guard: event.target may be a non-Element (e.g., Document, TextNode)
    if (!event.target || typeof event.target.closest !== 'function') return;

    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    // Ignore if already hovering the same link
    if (link === activeLink && activePreview) return;

    // Start prefetch immediately
    prefetch(link.pathname);

    // Schedule showing preview
    scheduleShow(link);
  }

  function handleMouseOut(event) {
    // Guard: event.target may be a non-Element (e.g., Document, TextNode)
    if (!event.target || typeof event.target.closest !== 'function') return;

    const link = event.target.closest('a');
    if (!link) return;

    // Check if we're moving to the preview card or staying within the link
    const relatedTarget = event.relatedTarget;
    if (relatedTarget) {
      // Still within the same link
      if (link.contains(relatedTarget)) return;
      // Moving to the preview card
      if (activePreview && activePreview.contains(relatedTarget)) return;
    }

    scheduleHide();
  }

  // Keyboard focus
  function handleFocusIn(event) {
    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    scheduleShow(link);
  }

  function handleFocusOut() {
    scheduleHide();
  }

  // Escape key to close
  function handleKeyDown(event) {
    if (event.key === 'Escape' && activePreview) {
      destroyPreview();
    }
  }

  // Touch/long-press handling for mobile
  function handleTouchStart(event) {
    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    touchStartTime = Date.now();
    touchStartPos = {
      x: event.touches[0].clientX,
      y: event.touches[0].clientY
    };

    // Start prefetch immediately
    prefetch(link.pathname);

    touchTimeout = setTimeout(async () => {
      // Prevent the link from being followed
      event.preventDefault();

      const data = await fetchPreviewData(link.pathname);
      if (data && !activePreview) {
        activeLink = link;
        activePreview = createPreviewCard(data, link);

        // Provide haptic feedback if available
        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      }
    }, CONFIG.longPressDelay);
  }

  function handleTouchMove(event) {
    // Cancel if user moves finger (scrolling)
    if (!touchTimeout) return;

    const touch = event.touches[0];
    const deltaX = Math.abs(touch.clientX - touchStartPos.x);
    const deltaY = Math.abs(touch.clientY - touchStartPos.y);

    // Cancel if moved more than 10px
    if (deltaX > 10 || deltaY > 10) {
      clearTimeout(touchTimeout);
      touchTimeout = null;
    }
  }

  function handleTouchEnd(event) {
    clearTimeout(touchTimeout);

    // If it was a quick tap (not long-press), let normal navigation happen
    if (Date.now() - touchStartTime < CONFIG.longPressDelay) {
      // If preview is showing, close it and let user re-tap to navigate
      if (activePreview) {
        event.preventDefault();
        destroyPreview();
      }
      return;
    }

    // For long-press, prevent navigation (preview is shown instead)
    if (activePreview) {
      event.preventDefault();
    }
  }

  // Close preview when tapping outside
  function handleDocumentClick(event) {
    if (!activePreview) return;

    // If click is outside preview and active link, close it
    if (!activePreview.contains(event.target) &&
        activeLink !== event.target &&
        !activeLink?.contains(event.target)) {
      destroyPreview();
    }
  }

  // ============================================================
  // Initialization
  // ============================================================

  function init() {
    // Use event delegation for efficiency
    // Note: mouseover/mouseout bubble (unlike pointerenter/pointerleave), so delegation works
    document.addEventListener('mouseover', handleMouseOver);
    document.addEventListener('mouseout', handleMouseOut);
    document.addEventListener('focusin', handleFocusIn, true);
    document.addEventListener('focusout', handleFocusOut, true);
    document.addEventListener('keydown', handleKeyDown);

    // Touch/mobile support
    document.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: false });
    document.addEventListener('click', handleDocumentClick);

    // Cleanup on navigation (for SPA-like behaviors)
    document.addEventListener('turbo:before-visit', destroyPreview);
    document.addEventListener('astro:before-preparation', destroyPreview);

    // Handle window resize - reposition preview
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        if (activePreview && activeLink) {
          positionPreview(activeLink, activePreview);
        }
      }, 100);
    });

    // Log initialization
    if (window.BengalUtils?.log) {
      window.BengalUtils.log('[LinkPreviews] Initialized');
    }
  }

  // ============================================================
  // Registration & Auto-init
  // ============================================================

  // Register with Bengal enhancement system if available
  if (window.Bengal?.enhance?.register) {
    Bengal.enhance.register('link-previews', function(_el, _options) {
      // The enhancement is document-wide, so we just init once
      init();
    });

    // Auto-init since this is a document-level enhancement
    // Don't wait for a specific element, init when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  } else {
    // Fallback: init directly when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  // Export for testing/debugging
  window.BengalLinkPreviews = {
    destroy: destroyPreview,
    clearCache: () => cache.clear(),
    getConfig: () => ({ ...CONFIG })
  };

})();
