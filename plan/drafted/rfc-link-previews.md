# RFC: Link Previews (Page Cards on Hover)

| Field | Value |
|-------|-------|
| **Title** | Link Previews (Page Cards on Hover) |
| **Author** | AI + Human reviewer |
| **Date** | 2025-12-23 |
| **Status** | Draft |
| **Priority** | P2 (Medium) |
| **Confidence** | 85% 🟢 |

---

## Executive Summary

Add **Wikipedia-style link previews** to Bengal's default theme. When users hover over internal links, a beautiful preview card appears showing the target page's title, excerpt, reading time, and tags — fetched from the per-page JSON files Bengal already generates.

**Strategic Context**: This is a "delight" feature that no other static site generator offers out of the box. It makes documentation feel alive and interconnected, dramatically improving content discovery and reducing navigation friction.

---

## Problem Statement

### Current State

Bengal generates per-page JSON files with rich metadata:

**Evidence**: `bengal/postprocess/output_formats/json_generator.py:1-50`
```python
"""
Per-page JSON generator for Bengal SSG.

Generates JSON files alongside each HTML page, providing machine-readable
page data for client-side features like search, previews, and navigation.

Output Format:
    Each page.html gets a corresponding page.json containing:
    - url: Full public URL with baseurl
    - title: Page title from frontmatter
    - description: Page description
    - excerpt: Truncated preview text
    - word_count: Content word count
    - reading_time: Estimated reading time in minutes
    - tags: List of tags
    - section: Parent section name
"""
```

This data exists but is only used for:
1. Client-side search (`index.json`)
2. Contextual graph minimap (`page.json → graph`)
3. LLM-friendly exports (`llm-full.txt`)

**The per-page JSON is underutilized** — it's perfect for link previews but we're not leveraging it.

### Pain Points

1. **Blind Navigation**: Users click links without knowing what's on the other side
2. **Context Switching**: Opening a page to "check what's there" interrupts flow
3. **Undiscoverable Connections**: Related content exists but users don't see it
4. **Documentation Feels Static**: No interactivity beyond basic navigation

### User Impact

| Scenario | Without Link Previews | With Link Previews |
|----------|----------------------|-------------------|
| Exploring docs | Click → wait → back-button if wrong | Hover → see excerpt → decide |
| Finding related content | Must open multiple tabs | Quick scan via hover |
| Learning new codebase | Slow, linear navigation | Fast, exploratory browsing |
| Mobile experience | Tap → full navigation | Long-press → preview |

---

## Goals & Non-Goals

### Goals

1. **Zero-Config Activation**: Works automatically when `per_page = ["json"]` is enabled
2. **Beautiful Design**: Preview cards that match the theme and feel premium
3. **Performant**: Prefetch on hover intent, cache aggressively, tiny bundle
4. **Accessible**: Keyboard navigable, screen reader friendly, respects motion preferences
5. **Progressive Enhancement**: Site works perfectly without JavaScript
6. **Integration**: Uses existing `Bengal.enhance` system for consistency

### Non-Goals

- **External link previews**: No scraping external sites (privacy, performance)
- **Real-time content**: Uses build-time JSON, not live fetching
- **CMS integration**: No API calls to content management systems
- **Full page embedding**: Preview only, not iframe embed

---

## Design

### Visual Design

```
┌─────────────────────────────────────────────────────────────────┐
│ Getting Started                                                 │
│                                                                 │
│ Learn how to install Bengal, create your first site, and       │
│ deploy to production in under 5 minutes...                     │
│                                                                 │
│ ┌─────────────┐  ┌──────────────────┐                          │
│ │ 📖 5 min    │  │ 🏷️ setup, beginner │                          │
│ └─────────────┘  └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
        ▲
        │ appears above/below link on hover
        │
    [Getting Started](/docs/getting-started/)
```

### Preview Card Anatomy

```
┌────────────────────────────────────────────┐
│  ┌────────────────────────────────────┐   │ ← Section badge (optional)
│  │ 📚 Documentation                   │   │
│  └────────────────────────────────────┘   │
│                                            │
│  Title of the Page                         │ ← Title (h4)
│                                            │
│  The first ~200 characters of the page     │ ← Excerpt
│  content, giving users a preview of        │
│  what they'll find when they click...      │
│                                            │
│  ┌────────┐ ┌────────┐ ┌────────┐         │ ← Metadata row
│  │ 5 min  │ │ 1.2k   │ │ v0.2   │         │
│  │ read   │ │ words  │ │        │         │
│  └────────┘ └────────┘ └────────┘         │
│                                            │
│  #getting-started  #tutorial               │ ← Tags (if present)
└────────────────────────────────────────────┘
```

### Color & Typography

The preview card inherits theme tokens:

```css
.link-preview {
  /* Background with subtle elevation */
  background: var(--color-surface-elevated, var(--color-bg-secondary));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  box-shadow: var(--shadow-lg,
    0 10px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1)
  );

  /* Smooth entrance animation */
  animation: preview-enter 150ms var(--ease-out-cubic);
  transform-origin: var(--preview-origin, center bottom);
}

.link-preview__title {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-text);
  margin-bottom: 0.5rem;
}

.link-preview__excerpt {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  /* Clamp to 3 lines max */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.link-preview__meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  margin-top: 0.75rem;
}

.link-preview__tag {
  background: var(--color-surface-tertiary);
  color: var(--color-text-secondary);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  font-size: 0.6875rem;
  font-weight: 500;
}

@keyframes preview-enter {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .link-preview {
    animation: none;
  }
}
```

### Positioning Algorithm

Preview cards use smart positioning:

1. **Preferred Position**: Above the link (reading direction)
2. **Fallback**: Below if not enough space above
3. **Horizontal**: Centered on link, clamped to viewport
4. **Safe Margins**: 8px from viewport edges

```javascript
function positionPreview(link, preview) {
  const linkRect = link.getBoundingClientRect();
  const previewRect = preview.getBoundingClientRect();
  const viewport = { width: window.innerWidth, height: window.innerHeight };
  const margin = 8;

  // Vertical: prefer above
  let top;
  const spaceAbove = linkRect.top;
  const spaceBelow = viewport.height - linkRect.bottom;

  if (spaceAbove >= previewRect.height + margin) {
    top = linkRect.top - previewRect.height - margin;
    preview.style.setProperty('--preview-origin', 'center bottom');
  } else if (spaceBelow >= previewRect.height + margin) {
    top = linkRect.bottom + margin;
    preview.style.setProperty('--preview-origin', 'center top');
  } else {
    // Fallback: position at center of viewport
    top = Math.max(margin, (viewport.height - previewRect.height) / 2);
  }

  // Horizontal: center on link, clamp to viewport
  let left = linkRect.left + (linkRect.width / 2) - (previewRect.width / 2);
  left = Math.max(margin, Math.min(left, viewport.width - previewRect.width - margin));

  preview.style.top = `${top}px`;
  preview.style.left = `${left}px`;
}
```

---

## Technical Implementation

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      Link Preview System                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│   │    Event     │────▶│    Fetch     │────▶│   Render   │  │
│   │   Manager    │     │   Manager    │     │   Manager  │  │
│   └──────────────┘     └──────────────┘     └────────────┘  │
│         │                     │                    │         │
│         │                     ▼                    │         │
│         │              ┌──────────────┐            │         │
│         │              │    Cache     │            │         │
│         │              │ (Map + LRU)  │            │         │
│         │              └──────────────┘            │         │
│         │                                          │         │
│         ▼                                          ▼         │
│   pointerenter ──────────────────────────▶ createCard()     │
│   pointerleave ──────────────────────────▶ destroyCard()    │
│   focusin      ──────────────────────────▶ createCard()     │
│   focusout     ──────────────────────────▶ destroyCard()    │
│   keydown(Esc) ──────────────────────────▶ destroyCard()    │
│   longpress    ──────────────────────────▶ createCard()     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Configuration Bridge: Server to Client

Bengal needs a mechanism to pass configuration to client-side JavaScript. This RFC introduces a standardized approach via a JSON config block in the base template:

**Template addition** (`base.html`):
```html
{% if site.config.link_previews.enabled %}
<script id="bengal-config" type="application/json">
{
  "linkPreviews": {
    "enabled": {{ site.config.link_previews.enabled | tojson }},
    "hoverDelay": {{ site.config.link_previews.hover_delay | default(200) }},
    "hideDelay": {{ site.config.link_previews.hide_delay | default(150) }},
    "showSection": {{ site.config.link_previews.show_section | default(true) | tojson }},
    "showReadingTime": {{ site.config.link_previews.show_reading_time | default(true) | tojson }},
    "showWordCount": {{ site.config.link_previews.show_word_count | default(true) | tojson }},
    "showDate": {{ site.config.link_previews.show_date | default(true) | tojson }},
    "showTags": {{ site.config.link_previews.show_tags | default(true) | tojson }},
    "maxTags": {{ site.config.link_previews.max_tags | default(3) }},
    "excludeSelectors": {{ site.config.link_previews.exclude_selectors | default(["nav", ".toc", ".breadcrumb", ".pagination"]) | tojson }}
  }
}
</script>
{% endif %}
```

**JavaScript config reader**:
```javascript
function getBengalConfig() {
  const el = document.getElementById('bengal-config');
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}
```

### Core JavaScript (~3.5KB gzipped)

```javascript
/**
 * Link Previews - Wikipedia-style hover cards powered by per-page JSON
 *
 * Integrates with Bengal's enhancement system for consistent behavior.
 *
 * @module enhancements/link-previews
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

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
    } else {
      top = linkRect.bottom + scrollY + margin;
      preview.classList.add('link-preview--below');
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

  // Pointer events (work for both mouse and touch)
  function handlePointerEnter(event) {
    // Skip touch events - handled separately via long-press
    if (event.pointerType === 'touch') return;

    const link = event.target.closest('a');
    if (!link || !isPreviewable(link)) return;

    // Start prefetch immediately
    prefetch(link.pathname);

    // Schedule showing preview
    scheduleShow(link);
  }

  function handlePointerLeave(event) {
    if (event.pointerType === 'touch') return;

    const link = event.target.closest('a');
    if (!link) return;

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
  // Integration with Bengal Enhancement System
  // ============================================================

  function init() {
    // Use event delegation for efficiency
    document.addEventListener('pointerenter', handlePointerEnter, true);
    document.addEventListener('pointerleave', handlePointerLeave, true);
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
  }

  // Register with Bengal enhancement system if available
  if (window.Bengal?.enhance?.register) {
    Bengal.enhance.register('link-previews', function(_el, _options) {
      // The enhancement is document-wide, so we just init once
      init();
    });

    // Auto-init since this is a document-level enhancement
    // Enhancement system will call us when DOM is ready
  } else {
    // Fallback: init directly when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

})();
```

### CSS (~1.2KB gzipped)

```css
/* ============================================================
   Link Previews
   ============================================================ */

.link-preview {
  position: absolute;
  z-index: var(--z-tooltip, 1000);
  width: 320px;
  max-width: calc(100vw - 16px);
  padding: 1rem;

  background: var(--color-surface-elevated, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 12px);
  box-shadow:
    0 10px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1);

  /* Entrance animation */
  animation: link-preview-enter 150ms var(--ease-out-cubic, cubic-bezier(0.33, 1, 0.68, 1));
  pointer-events: auto;
}

.link-preview--above {
  transform-origin: center bottom;
}

.link-preview--below {
  transform-origin: center top;
}

@keyframes link-preview-enter {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Section badge */
.link-preview__section {
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-primary, #0891b2);
  margin-bottom: 0.5rem;
}

/* Title */
.link-preview__title {
  font-family: var(--font-heading, inherit);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
  color: var(--color-text, #1e293b);
  margin: 0 0 0.5rem 0;
}

/* Excerpt */
.link-preview__excerpt {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--color-text-muted, #64748b);
  margin: 0;

  /* Clamp to 3 lines */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Metadata */
.link-preview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary, #94a3b8);
}

.link-preview__meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* Tags */
.link-preview__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin-top: 0.625rem;
}

.link-preview__tag {
  background: var(--color-surface-tertiary, #f1f5f9);
  color: var(--color-text-secondary, #475569);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .link-preview {
    background: var(--color-surface-elevated, #1e293b);
    border-color: var(--color-border, #334155);
    box-shadow:
      0 10px 25px -5px rgba(0, 0, 0, 0.4),
      0 8px 10px -6px rgba(0, 0, 0, 0.3);
  }
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .link-preview {
    animation: none;
  }
}

/* Mobile: slightly larger touch target, full width */
@media (max-width: 480px) {
  .link-preview {
    width: calc(100vw - 32px);
    left: 16px !important;
    right: 16px;
  }
}

/* Long-press visual feedback */
a:active {
  outline: 2px solid var(--color-primary, #0891b2);
  outline-offset: 2px;
  border-radius: 2px;
}

@media (prefers-reduced-motion: reduce) {
  a:active {
    outline: none;
  }
}
```

---

## Configuration

```toml
# bengal.toml

[link_previews]
enabled = true              # Default: true (when per_page JSON enabled)

# Timing
hover_delay = 200           # ms before showing preview
hide_delay = 150            # ms grace period for moving to preview

# Content display options
show_section = true         # Show section badge
show_reading_time = true    # Show reading time
show_word_count = true      # Show word count
show_date = true            # Show date (if available)
show_tags = true            # Show tags
max_tags = 3                # Maximum tags to display

# Exclusions
exclude_selectors = [       # Links inside these won't show previews
  "nav",
  ".toc",
  ".breadcrumb",
  ".pagination",
  ".card",
  "[class*='-card']",
  ".tab-nav",
  "[class*='-widget']",
  ".child-items",
  ".content-tiles",
]
```

### Per-Link Opt-Out

```html
<!-- Disable preview for specific link -->
<a href="/docs/something/" data-no-preview>Skip preview</a>
```

### Auto-Enable Logic

Link previews are automatically enabled when:
1. `[output_formats] per_page = ["json"]` is configured
2. `[link_previews] enabled` is not explicitly set to `false`

This means zero configuration for users who already have per-page JSON enabled.

---

## Performance Considerations

### Bundle Size Budget

| Component | Size (gzipped) |
|-----------|---------------|
| JavaScript | ~3.5KB |
| CSS | ~1.2KB |
| **Total** | **~4.7KB** |

### Optimization Strategies

1. **Prefetch on Hover Intent**
   - Start fetching JSON 50ms after pointer enters
   - By the time 200ms delay passes, data is likely cached

2. **Abort Controller for Rapid Navigation**
   - If user quickly hovers between links, abort pending fetches
   - Prevents request queue buildup

3. **LRU Cache**
   - Cache up to 50 page JSONs in memory
   - Evict oldest entries when limit reached
   - Persist across page navigations (SPA)

4. **Cache-Control Headers**
   - JSON files served with `Cache-Control: max-age=3600`
   - Browser caches reduce repeat fetches

5. **Event Delegation**
   - Single listener on document vs per-link listeners
   - No MutationObserver needed

6. **Feature Detection**
   - Only initialize if config block indicates previews are enabled
   - Zero overhead when disabled

### Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Time to preview | < 300ms | 200ms delay + 100ms fetch (cached) |
| JS parse time | < 5ms | Simple, no heavy dependencies |
| Memory overhead | < 500KB | 50 cached JSONs × ~10KB each |
| Layout shift | 0 | Absolute positioning |

---

## Accessibility

### ARIA Implementation

```html
<!-- Link with active preview -->
<a href="/docs/api/" aria-describedby="link-preview-abc123">API Reference</a>

<!-- Preview card -->
<div id="link-preview-abc123" class="link-preview" role="tooltip">
  <h4 class="link-preview__title">API Reference</h4>
  <p class="link-preview__excerpt">Complete API documentation...</p>
</div>
```

### Keyboard Support

| Key | Action |
|-----|--------|
| Tab | Focus moves to links; preview shows on focus |
| Tab away | Preview hides on blur |
| Escape | Close preview immediately |
| Enter | Navigate to link (normal behavior) |

### Screen Reader Considerations

- Preview content uses `role="tooltip"` with `aria-describedby` association
- Content is announced when link receives focus
- Content is concise (title + excerpt), not overwhelming
- Links remain fully functional without JavaScript

### Motion & Preferences

```css
@media (prefers-reduced-motion: reduce) {
  .link-preview {
    animation: none;
    transition: none;
  }

  a:active {
    outline: none;
  }
}
```

---

## Mobile Behavior

Mobile uses long-press instead of hover:

### Long-Press to Preview

- **500ms threshold**: Long-press for 500ms to show preview
- **Movement cancellation**: If finger moves >10px, cancel (user is scrolling)
- **Haptic feedback**: Subtle vibration when preview appears (if supported)
- **Tap to dismiss**: Tap anywhere outside preview to close
- **Tap-through**: Quick taps still navigate normally

### Visual Feedback

```css
/* Subtle highlight on long-press */
a:active {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

---

## Implementation Plan

### Prerequisites

1. **Config bridge mechanism**: Add `<script id="bengal-config">` to base template for server-to-client config passing. This is a general-purpose mechanism that can be reused by other features.

### Phase 1: Core Implementation (1 day)

1. Create `bengal/themes/default/assets/js/enhancements/link-previews.js`
2. Implement event handling (pointer + touch), fetch with abort, cache
3. Create preview card rendering
4. Add positioning algorithm

### Phase 2: Styling (0.5 day)

1. Add CSS to `bengal/themes/default/assets/css/components/link-preview.css`
2. Dark mode support
3. Responsive adjustments
4. Animation polish

### Phase 3: Configuration (0.5 day)

1. Add `[link_previews]` config section to schema
2. Add config bridge block to `base.html` template
3. Wire config to JavaScript via `bengal-config` JSON block
4. Add exclude selectors support

### Phase 4: Polish & Testing (1 day)

1. Accessibility audit (keyboard, screen reader)
2. Mobile long-press testing on real devices
3. Edge cases (scroll, resize, rapid hover, SPA navigation)
4. Integration with `Bengal.enhance` system
5. Documentation

**Total**: ~3 days

---

## Testing Strategy

### Unit Tests

```python
def test_json_url_conversion():
    """Page URLs correctly convert to JSON URLs."""
    assert to_json_url("/docs/getting-started/") == "/docs/getting-started/index.json"
    assert to_json_url("/docs/api") == "/docs/api/index.json"
    assert to_json_url("/docs/api/index.html") == "/docs/api/index.json"
    assert to_json_url("/docs/page.html") == "/docs/page/index.json"

def test_preview_exclusions():
    """Links in nav/toc don't trigger previews."""
    # Test isPreviewable() logic

def test_config_bridge_rendering():
    """Config bridge JSON block renders correctly in template."""
    # Test that bengal-config block contains expected JSON structure
```

### E2E Tests (Playwright)

```python
def test_hover_shows_preview(page):
    """Hovering over internal link shows preview card."""
    page.goto("/docs/")
    link = page.locator('article a[href^="/"]').first
    link.hover()

    # Wait for preview
    preview = page.locator('.link-preview')
    expect(preview).to_be_visible(timeout=500)
    expect(preview.locator('.link-preview__title')).to_have_text()

def test_preview_content_accuracy(page):
    """Preview shows correct title and excerpt."""
    page.goto("/docs/")
    link = page.locator('a[href="/docs/getting-started/"]')
    link.hover()

    preview = page.locator('.link-preview')
    expect(preview.locator('.link-preview__title')).to_contain_text("Getting Started")

def test_keyboard_accessibility(page):
    """Preview shows on focus, hides on blur."""
    page.goto("/docs/")
    link = page.locator('article a[href^="/"]').first

    # Tab to link
    link.focus()
    expect(page.locator('.link-preview')).to_be_visible(timeout=500)

    # Tab away
    page.keyboard.press("Tab")
    expect(page.locator('.link-preview')).not_to_be_visible()

def test_escape_closes_preview(page):
    """Escape key immediately closes preview."""
    page.goto("/docs/")
    page.locator('article a[href^="/"]').first.hover()

    expect(page.locator('.link-preview')).to_be_visible(timeout=500)

    page.keyboard.press("Escape")
    expect(page.locator('.link-preview')).not_to_be_visible()

def test_aria_association(page):
    """Preview has proper ARIA association with link."""
    page.goto("/docs/")
    link = page.locator('article a[href^="/"]').first
    link.hover()

    preview = page.locator('.link-preview')
    expect(preview).to_be_visible(timeout=500)

    # Check aria-describedby points to preview
    preview_id = preview.get_attribute('id')
    expect(link).to_have_attribute('aria-describedby', preview_id)

def test_mobile_long_press(page):
    """Long press on mobile shows preview."""
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto("/docs/")

    link = page.locator('article a[href^="/"]').first

    # Simulate long press
    box = link.bounding_box()
    page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
    page.mouse.down()
    page.wait_for_timeout(600)  # Wait for long-press threshold
    page.mouse.up()

    expect(page.locator('.link-preview')).to_be_visible()

def test_rapid_hover_aborts_pending(page):
    """Rapidly hovering between links doesn't queue multiple requests."""
    page.goto("/docs/")
    links = page.locator('article a[href^="/"]')

    # Quickly hover between multiple links
    for i in range(5):
        links.nth(i % 3).hover()
        page.wait_for_timeout(50)

    # Only one preview should appear (for the last hovered link)
    expect(page.locator('.link-preview')).to_have_count(1, timeout=500)

def test_nav_links_excluded(page):
    """Links in navigation don't show previews."""
    page.goto("/docs/")
    nav_link = page.locator('nav a[href^="/"]').first
    nav_link.hover()

    page.wait_for_timeout(400)
    expect(page.locator('.link-preview')).not_to_be_visible()
```

---

## Comparison: Static Site Generators

| Feature | Bengal | Hugo | MkDocs | Docusaurus | Astro |
|---------|--------|------|--------|------------|-------|
| Link previews | ✅ Built-in | ❌ | ❌ | ❌ | ❌ |
| Per-page JSON | ✅ | ❌ | ❌ | Partial | ❌ |
| Client search | ✅ | Plugin | Plugin | ✅ | Plugin |
| Graph viz | ✅ | ❌ | ❌ | ❌ | ❌ |

**Bengal becomes the only SSG with Wikipedia-style link previews out of the box.**

---

## Future Enhancements

### Preview Images

If page has a featured image, show thumbnail:

```javascript
if (data.metadata?.image) {
  html += `<img class="link-preview__image" src="${data.metadata.image}" alt="" loading="lazy" />`;
}
```

### Rich Previews for Special Pages

Different preview templates for different page types:

| Page Type | Preview Content |
|-----------|-----------------|
| Blog post | Title, date, author, excerpt |
| API reference | Function signature, description |
| Changelog | Version, date, highlights |
| Gallery | Thumbnail grid |

### Graph Connection Indicator

Show number of connections to this page:

```javascript
if (data.graph && data.graph.nodes) {
  const connections = data.graph.nodes.length - 1; // Exclude current
  metaParts.push(`<span>🔗 ${connections} connections</span>`);
}
```

### Speculation Rules Integration

Combine with browser prefetch for instant navigation:

```javascript
// If preview shown for > 1s, add prefetch hint
if (previewDuration > 1000) {
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = pageUrl;
  document.head.appendChild(link);
}
```

---

## Success Metrics

1. **Engagement**: Track hover → click conversion rate
2. **Performance**: P95 time-to-preview < 400ms
3. **Accessibility**: Pass automated a11y audit
4. **Bundle size**: < 5KB gzipped total
5. **User feedback**: Delight factor in user surveys

---

## Open Questions

1. **~~Default enabled?~~** ✅ Yes, auto-enable when per_page JSON is configured
2. **Mobile threshold**: Is 500ms the right long-press duration? (Standard is 400-600ms)
3. **Animation style**: Current fade-in + scale feels natural; alternatives welcome
4. **~~Preview persistence~~**: ✅ Allow moving to preview card (hide delay provides grace period)

---

## References

- Per-page JSON generator: `bengal/postprocess/output_formats/json_generator.py`
- Enhancement system: `bengal/themes/default/assets/js/enhancements/README.md`
- Wikipedia previews: https://en.wikipedia.org/wiki/Wikipedia:Page_previews
- Touch Events: https://developer.mozilla.org/en-US/docs/Web/API/Touch_events
- AbortController: https://developer.mozilla.org/en-US/docs/Web/API/AbortController
