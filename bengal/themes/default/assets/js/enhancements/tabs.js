/**
 * Bengal Enhancement: Tabs Component
 *
 * Pattern: CSS STATE MACHINE + JS ENHANCEMENT (see COMPONENT-PATTERNS.md)
 *
 * Base functionality uses CSS :target selector (tabs-native.css).
 * This JS provides optional enhancements:
 * - Tab sync across multiple tab-sets (data-sync)
 * - localStorage persistence for sync preferences
 * - Enhanced keyboard navigation
 * - Event delegation for dynamic content
 * - Copy button functionality for code-tabs
 *
 * Without this JS, tabs still work via URL fragments (#tab-id).
 *
 * @requires utils.js (optional, for logging)
 */

(function() {
  'use strict';

  // ============================================================
  // Dependencies & Constants
  // ============================================================

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});

  // CSS classes
  const CLASS_ACTIVE = 'active';
  const SELECTOR_TABS = '.tabs, .code-tabs';
  const SELECTOR_NAV_LINK = '.tab-nav a';
  const SELECTOR_NAV_ITEM = '.tab-nav li';
  const SELECTOR_PANE = '.tab-pane';

  // Sync storage prefix
  const STORAGE_PREFIX = 'bengal-tabs-sync-';

  // ============================================================
  // Tab Switching
  // ============================================================

  /**
   * Switch tab within a container
   * @param {HTMLElement} container - The tabs container
   * @param {HTMLElement} activeLink - The clicked link
   * @param {string} targetId - ID of the target pane
   */
  function switchTab(container, activeLink, targetId) {
    // 1. Deactivate all nav items in THIS container
    const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
      item.closest(SELECTOR_TABS) === container
    );
    navItems.forEach(item => item.classList.remove(CLASS_ACTIVE));

    // 2. Activate clicked nav item
    const activeItem = activeLink.closest('li');
    if (activeItem) activeItem.classList.add(CLASS_ACTIVE);

    // 3. Hide all panes in THIS container
    const panes = Array.from(container.querySelectorAll(SELECTOR_PANE)).filter(pane =>
      pane.closest(SELECTOR_TABS) === container
    );
    panes.forEach(pane => pane.classList.remove(CLASS_ACTIVE));

    // 4. Show target pane
    const targetPane = document.getElementById(targetId);
    if (targetPane) {
      targetPane.classList.add(CLASS_ACTIVE);

      // Update ARIA attributes
      activeLink.setAttribute('aria-selected', 'true');
      navItems.forEach(item => {
        const link = item.querySelector('a');
        if (link && link !== activeLink) {
          link.setAttribute('aria-selected', 'false');
        }
      });

      // Dispatch event
      const event = new CustomEvent('tabSwitched', {
        detail: { container, link: activeLink, pane: targetPane }
      });
      container.dispatchEvent(event);
    }
  }

  // ============================================================
  // Tab Sync (RFC: Enhanced Code Tabs)
  // ============================================================

  /**
   * Sync all tab containers with matching data-sync key.
   *
   * When a user selects a tab (e.g., "Python"), all other tab containers
   * on the page with the same sync key will switch to the matching tab.
   *
   * @param {string} syncKey - The sync group key (e.g., "language")
   * @param {string} syncValue - The value to sync to (e.g., "python")
   */
  function syncTabs(syncKey, syncValue, skipContainer = null) {
    if (!syncKey || syncKey === 'none') return;

    // Find all containers with this sync key
    const containers = document.querySelectorAll(`[data-sync="${syncKey}"]`);

    containers.forEach(container => {
      if (container === skipContainer) return;

      // Find link with matching sync value
      const matchingLink = container.querySelector(
        `[data-sync-value="${syncValue}"]`
      );

      if (matchingLink) {
        const targetId = matchingLink.getAttribute('data-tab-target');
        if (targetId) {
          switchTab(container, matchingLink, targetId);
        }
      }
    });

    // Persist preference to localStorage
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${syncKey}`, syncValue);
      log(`[BengalTabs] Synced ${syncKey}=${syncValue}`);
    } catch (e) {
      // localStorage may be unavailable (private browsing, etc.)
      log('[BengalTabs] localStorage unavailable, sync not persisted');
    }
  }

  /**
   * Restore synced tab preferences from localStorage on page load.
   *
   * Checks each sync group for a saved preference and applies it.
   */
  function restoreSyncPreferences() {
    const containers = document.querySelectorAll('[data-sync]');
    const restored = new Set();

    containers.forEach(container => {
      const syncKey = container.dataset.sync;
      if (!syncKey || syncKey === 'none' || restored.has(syncKey)) return;

      try {
        const saved = localStorage.getItem(`${STORAGE_PREFIX}${syncKey}`);
        if (saved) {
          // Find matching link in this container
          const link = container.querySelector(`[data-sync-value="${saved}"]`);
          if (link) {
            const targetId = link.getAttribute('data-tab-target');
            if (targetId) {
              // Sync all containers with this key
              syncTabs(syncKey, saved);
              restored.add(syncKey);
              log(`[BengalTabs] Restored ${syncKey}=${saved}`);
            }
          }
        }
      } catch (e) {
        // localStorage unavailable
      }
    });
  }

  // ============================================================
  // Copy Button (RFC: Enhanced Code Tabs)
  // ============================================================

  /**
   * Handle copy button clicks for code-tabs.
   *
   * @param {HTMLElement} button - The copy button element
   */
  async function handleCopyClick(button) {
    const targetId = button.getAttribute('data-copy-target');
    if (!targetId) return;

    const codeElement = document.getElementById(targetId);
    if (!codeElement) return;

    // Get plain text content (not HTML)
    const code = codeElement.textContent || '';

    try {
      await navigator.clipboard.writeText(code);

      // Visual feedback
      button.classList.add('copied');
      const label = button.querySelector('.copy-label');
      const originalText = label ? label.textContent : '';
      if (label) label.textContent = 'Copied!';

      // Reset after delay
      setTimeout(() => {
        button.classList.remove('copied');
        if (label) label.textContent = originalText;
      }, 2000);

      log('[BengalTabs] Code copied to clipboard');
    } catch (err) {
      log('[BengalTabs] Copy failed:', err);

      // Fallback for older browsers
      try {
        const textarea = document.createElement('textarea');
        textarea.value = code;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        button.classList.add('copied');
        setTimeout(() => button.classList.remove('copied'), 2000);
      } catch (fallbackErr) {
        log('[BengalTabs] Copy fallback failed:', fallbackErr);
      }
    }
  }

  /**
   * Copy a literal value from a data-copy attribute.
   *
   * @param {HTMLElement} button - The copy button element
   */
  async function handleLiteralCopy(button) {
    const value = button.getAttribute('data-copy');
    if (!value) return;

    try {
      await navigator.clipboard.writeText(value);
      button.classList.add('copied');
      setTimeout(() => button.classList.remove('copied'), 1600);
    } catch (err) {
      log('[BengalTabs] Literal copy failed:', err);
    }
  }

  /**
   * Switch OpenAPI request sample tabs.
   *
   * @param {HTMLElement} button - The clicked language tab
   */
  function switchApiCodeSample(button) {
    const samples = button.closest('.api-code-samples');
    if (!samples) return;

    const targetId = button.getAttribute('aria-controls');
    if (!targetId) return;

    samples.querySelectorAll('.api-code-samples__tab').forEach(tab => {
      tab.classList.toggle('api-code-samples__tab--active', tab === button);
      tab.setAttribute('aria-selected', tab === button ? 'true' : 'false');
    });

    samples.querySelectorAll('.api-code-samples__panel').forEach(panel => {
      panel.classList.toggle('api-code-samples__panel--active', panel.id === targetId);
    });
  }

  /**
   * Switch OpenAPI response panels.
   *
   * @param {HTMLElement} button - The clicked response status tab
   */
  function switchApiResponse(button) {
    const responses = button.closest('.api-responses');
    if (!responses) return;

    const targetId = button.getAttribute('aria-controls');
    if (!targetId) return;

    responses.querySelectorAll('.api-responses__tab').forEach(tab => {
      tab.classList.toggle('api-responses__tab--active', tab === button);
      tab.setAttribute('aria-selected', tab === button ? 'true' : 'false');
    });

    responses.querySelectorAll('.api-responses__panel').forEach(panel => {
      panel.classList.toggle('api-responses__panel--active', panel.id === targetId);
    });
  }

  /**
   * Filter OpenAPI sidebar items.
   *
   * @param {HTMLInputElement} input - Search input
   */
  function filterApiSidebar(input) {
    const nav = input.closest('.api-sidebar-nav');
    if (!nav) return;

    const query = input.value.trim().toLowerCase();
    nav.querySelectorAll('[data-api-search-item]').forEach(item => {
      const text = item.textContent.toLowerCase();
      item.hidden = query.length > 0 && !text.includes(query);
    });
  }

  // ============================================================
  // Event Handlers
  // ============================================================

  /**
   * Handle click events on tab links
   */
  document.addEventListener('click', (e) => {
    // Handle copy button clicks
    const copyBtn = e.target.closest('.copy-btn, .api-code-samples__copy');
    if (copyBtn) {
      e.preventDefault();
      handleCopyClick(copyBtn);
      return;
    }

    const literalCopyBtn = e.target.closest('[data-copy]');
    if (literalCopyBtn) {
      e.preventDefault();
      handleLiteralCopy(literalCopyBtn);
      return;
    }

    const apiCodeTab = e.target.closest('.api-code-samples__tab');
    if (apiCodeTab) {
      e.preventDefault();
      switchApiCodeSample(apiCodeTab);
      return;
    }

    const apiResponseTab = e.target.closest('.api-responses__tab');
    if (apiResponseTab) {
      e.preventDefault();
      switchApiResponse(apiResponseTab);
      return;
    }

    // Handle tab clicks
    const link = e.target.closest(SELECTOR_NAV_LINK);
    if (!link) return;

    // Find the container
    const container = link.closest(SELECTOR_TABS);
    if (!container) return;

    // Prevent default anchor behavior
    e.preventDefault();

    // Get target ID
    const targetId = link.getAttribute('data-tab-target');
    if (!targetId) return;

    // Check for sync
    const syncKey = container.dataset.sync;
    const syncValue = link.dataset.syncValue;

    // Always switch the clicked tab first — sync must not override local selection.
    switchTab(container, link, targetId);

    if (syncKey && syncValue && syncKey !== 'none') {
      // Sync peer containers only (skip the one the user clicked).
      syncTabs(syncKey, syncValue, container);
    }
  });

  document.addEventListener('input', (e) => {
    const input = e.target.closest('[data-api-search]');
    if (!input) return;
    filterApiSidebar(input);
  });

  /**
   * Handle keyboard navigation (arrow keys)
   */
  document.addEventListener('keydown', (e) => {
    const link = e.target.closest(SELECTOR_NAV_LINK);
    if (!link) return;

    const container = link.closest(SELECTOR_TABS);
    if (!container) return;

    const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
      item.closest(SELECTOR_TABS) === container
    );

    const currentIndex = navItems.findIndex(item => item.contains(link));
    if (currentIndex === -1) return;

    let newIndex = -1;

    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        newIndex = currentIndex > 0 ? currentIndex - 1 : navItems.length - 1;
        break;
      case 'ArrowRight':
      case 'ArrowDown':
        e.preventDefault();
        newIndex = currentIndex < navItems.length - 1 ? currentIndex + 1 : 0;
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = navItems.length - 1;
        break;
      default:
        return;
    }

    if (newIndex >= 0) {
      const newLink = navItems[newIndex].querySelector('a');
      if (newLink) {
        newLink.focus();
        newLink.click();
      }
    }
  });

  // ============================================================
  // Initialization
  // ============================================================

  /**
   * Initialize tabs state.
   * Ensure at least one tab is active if HTML didn't set it.
   */
  function initTabs() {
    const containers = document.querySelectorAll(SELECTOR_TABS);
    containers.forEach(container => {
      const navItems = Array.from(container.querySelectorAll(SELECTOR_NAV_ITEM)).filter(item =>
        item.closest(SELECTOR_TABS) === container
      );

      // If no active item, activate first
      if (navItems.length > 0 && !navItems.some(item => item.classList.contains(CLASS_ACTIVE))) {
        navItems[0].classList.add(CLASS_ACTIVE);
        const link = navItems[0].querySelector('a');
        if (link) {
          const targetId = link.getAttribute('data-tab-target');
          if (targetId) {
            const pane = document.getElementById(targetId);
            if (pane) pane.classList.add(CLASS_ACTIVE);
          }
        }
      }
    });
  }

  /**
   * Full initialization: tabs state + sync restoration
   */
  function init() {
    initTabs();
    restoreSyncPreferences();
    log('[BengalTabs] Initialized with sync support');
  }

  // ============================================================
  // Auto-initialize
  // ============================================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ============================================================
  // Public API (optional)
  // ============================================================

  // Expose sync function for programmatic use
  window.BengalTabs = {
    sync: syncTabs,
    switch: switchTab,
    restoreSync: restoreSyncPreferences
  };

})();
