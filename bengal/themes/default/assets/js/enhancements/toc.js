/**
 * Enhanced Table of Contents (TOC) JavaScript
 *
 * Uses native <details>/<summary> for collapsible groups (no JS required for toggle).
 * This script enhances with:
 * - Active item tracking with auto-scroll
 * - Scroll progress indicator
 * - Auto-expand active section on scroll
 * - Compact mode toggle
 * - Full keyboard navigation
 * - State persistence in localStorage
 */

(function() {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - toc.js requires utils.js');
    return;
  }

  const { throttleScroll, debounce, ready } = window.BengalUtils;

  // ============================================================================
  // State Management
  // ============================================================================

  let currentActiveIndex = -1;
  let isCompactMode = false;
  let collapsedGroups = new Set();

  // Cache DOM elements
  let tocItems = [];
  let progressBar = null;
  let progressPosition = null;
  let tocNav = null;
  let tocGroups = [];
  let tocScrollContainer = null;
  let headings = [];

  // Store handlers for cleanup
  let scrollHandler = null;
  let hashChangeHandler = null;
  let resizeHandler = null;
  let keyboardHandler = null;

  /**
   * Load state from localStorage
   */
  function loadState() {
    try {
      const savedState = localStorage.getItem('toc-state');
      if (savedState) {
        const state = JSON.parse(savedState);
        isCompactMode = state.compact || false;
        // Don't restore collapsed state - start fresh with all collapsed
        collapsedGroups = new Set();

        if (isCompactMode && tocNav) {
          tocNav.setAttribute('data-toc-mode', 'compact');
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }

  /**
   * Save state to localStorage
   */
  function saveState() {
    try {
      localStorage.setItem('toc-state', JSON.stringify({
        compact: isCompactMode,
        collapsed: Array.from(collapsedGroups)
      }));
    } catch (e) {
      // Ignore errors
    }
  }

  // ============================================================================
  // Progress Bar & Active Item Tracking
  // ============================================================================

  /**
   * Update scroll progress indicator
   */
  function updateProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = Math.min((scrollTop / docHeight) * 100, 100);

    // Update progress bar
    if (progressBar) {
      progressBar.style.height = `${progress}%`;
    }

    // Update progress position indicator
    if (progressPosition) {
      progressPosition.style.top = `${progress}%`;
    }
  }

  /**
   * Update active TOC item based on scroll position
   *
   * Performance: Batches all DOM reads before DOM writes to avoid forced reflows.
   * This prevents the browser from recalculating layout multiple times per frame.
   */
  function updateActiveItem() {
    const viewportOffset = 120; // Offset from top of viewport

    // ========================================
    // PHASE 1: Batch all DOM reads
    // ========================================

    // Read all heading positions in one batch (avoids interleaved read/write)
    const headingRects = headings.map(heading => ({
      top: heading.element.getBoundingClientRect().top,
      heading: heading
    }));

    // Read container rect once (if needed for scroll-into-view)
    let containerRect = null;
    if (tocScrollContainer) {
      containerRect = tocScrollContainer.getBoundingClientRect();
    }

    // Find active heading (closest one above viewport offset)
    let activeIndex = 0;
    for (let i = headingRects.length - 1; i >= 0; i--) {
      if (headingRects[i].top <= viewportOffset) {
        activeIndex = i;
        break;
      }
    }

    // Only update if changed
    if (activeIndex === currentActiveIndex) return;
    currentActiveIndex = activeIndex;

    // ========================================
    // PHASE 2: Batch all DOM writes
    // ========================================

    // Collect class changes to apply
    const activeHeading = headings[activeIndex];
    const activeLink = activeHeading ? activeHeading.link : null;
    const activeParentGroup = activeLink ? activeLink.closest('details.toc-group') : null;

    // Remove active class from all links
    headings.forEach((heading, index) => {
      if (index === activeIndex) {
        heading.link.classList.add('active');
      } else {
        heading.link.classList.remove('active');
      }
    });

    // Handle group expand/collapse (using native [open] attribute)
    if (activeParentGroup) {
      // Active link is inside a collapsible group
      // Collect ALL ancestor groups (nested groups need parent groups open too)
      const ancestorGroups = new Set();
      let currentGroup = activeParentGroup;
      while (currentGroup) {
        ancestorGroups.add(currentGroup);
        // Find next ancestor group
        const parent = currentGroup.parentElement?.closest('details.toc-group');
        currentGroup = parent;
      }

      // Expand all ancestor groups (from active up to root)
      ancestorGroups.forEach(group => {
        if (!group.open) {
          const groupId = getGroupId(group);
          expandGroup(group, groupId);
        }
      });

      // Collapse groups that are NOT ancestors of active item
      tocGroups.forEach(group => {
        if (!ancestorGroups.has(group)) {
          const otherGroupId = getGroupId(group);
          if (group.open) {
            collapseGroup(group, otherGroupId);
          }
        }
      });
    } else {
      // Active link is a standalone item (not in a group)
      // Collapse ALL groups to keep the minimal view
      tocGroups.forEach(group => {
        const groupId = getGroupId(group);
        if (group.open) {
          collapseGroup(group, groupId);
        }
      });
    }

    // Scroll active link into view if needed (using cached containerRect)
    if (tocScrollContainer && activeLink && containerRect) {
      const linkRect = activeLink.getBoundingClientRect();
      if (linkRect.top < containerRect.top || linkRect.bottom > containerRect.bottom) {
        activeLink.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }

  /**
   * Update on scroll (progress + active item)
   */
  function updateOnScroll() {
    updateProgress();
    updateActiveItem();
  }

  // ============================================================================
  // Collapsible Groups (Native <details>/<summary>)
  // The browser handles expand/collapse natively. These functions are for
  // programmatic control during scroll spy (auto-expand active group).
  // ============================================================================

  /**
   * Get unique group ID from the details element
   */
  function getGroupId(group) {
    const link = group.querySelector('[data-toc-item]');
    return link ? link.getAttribute('data-toc-item') : null;
  }

  /**
   * Collapse a TOC group (programmatic - for scroll spy)
   */
  function collapseGroup(group, groupId) {
    group.removeAttribute('open');
    if (groupId) {
      collapsedGroups.add(groupId);
    }
    saveState();
  }

  /**
   * Expand a TOC group (programmatic - for scroll spy)
   */
  function expandGroup(group, groupId) {
    group.setAttribute('open', '');
    if (groupId) {
      collapsedGroups.delete(groupId);
    }
    saveState();
  }

  /**
   * Initialize group toggle handlers
   * With native <details>/<summary>, the browser handles click toggling.
   * We just need to track state changes for persistence.
   */
  function initGroupToggles() {
    tocGroups.forEach(group => {
      const groupId = getGroupId(group);

      // Listen for native toggle events (for state persistence)
      group.addEventListener('toggle', () => {
        if (group.open) {
          if (groupId) collapsedGroups.delete(groupId);
        } else {
          if (groupId) collapsedGroups.add(groupId);
        }
        saveState();
      });
    });
  }

  // ============================================================================
  // Control Buttons
  // ============================================================================

  /**
   * Initialize control buttons and settings menu
   */
  function initControlButtons() {
    // Direct toggle-all button (new editorial style)
    const toggleAllBtn = document.querySelector('[data-toc-action="toggle-all"]');
    if (toggleAllBtn) {
      toggleAllBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        // Check if any group is expanded
        const anyExpanded = tocGroups.some(group => group.open);

        if (anyExpanded) {
          // Collapse all
          tocGroups.forEach(group => {
            const groupId = getGroupId(group);
            collapseGroup(group, groupId);
          });
          toggleAllBtn.setAttribute('aria-expanded', 'false');
          toggleAllBtn.setAttribute('aria-label', 'Expand all sections');
        } else {
          // Expand all
          tocGroups.forEach(group => {
            const groupId = getGroupId(group);
            expandGroup(group, groupId);
          });
          toggleAllBtn.setAttribute('aria-expanded', 'true');
          toggleAllBtn.setAttribute('aria-label', 'Collapse all sections');
        }
      });
    }

    // Legacy: Settings menu toggle
    const settingsBtn = document.querySelector('[data-toc-action="toggle-settings"]');
    const settingsMenu = document.querySelector('.toc-settings-menu');

    if (settingsBtn && settingsMenu) {
      settingsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = settingsMenu.hasAttribute('hidden');

        if (isHidden) {
          settingsMenu.removeAttribute('hidden');
          settingsBtn.setAttribute('aria-expanded', 'true');
        } else {
          settingsMenu.setAttribute('hidden', '');
          settingsBtn.setAttribute('aria-expanded', 'false');
        }
      });

      // Close menu when clicking outside
      document.addEventListener('click', (e) => {
        if (!settingsMenu.contains(e.target) && !settingsBtn.contains(e.target)) {
          settingsMenu.setAttribute('hidden', '');
          settingsBtn.setAttribute('aria-expanded', 'false');
        }
      });
    }

    // Legacy: Expand all sections
    const expandAllBtn = document.querySelector('[data-toc-action="expand-all"]');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', () => {
        tocGroups.forEach(group => {
          const groupId = getGroupId(group);
          expandGroup(group, groupId);
        });
        if (settingsMenu) settingsMenu.setAttribute('hidden', '');
      });
    }

    // Legacy: Collapse all sections
    const collapseAllBtn = document.querySelector('[data-toc-action="collapse-all"]');
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener('click', () => {
        tocGroups.forEach(group => {
          const groupId = getGroupId(group);
          collapseGroup(group, groupId);
        });
        if (settingsMenu) settingsMenu.setAttribute('hidden', '');
      });
    }
  }

  // ============================================================================
  // Smooth Scroll to Sections
  // ============================================================================

  /**
   * Initialize smooth scroll on TOC links
   */
  function initSmoothScroll() {
    tocItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const id = item.getAttribute('data-toc-item').slice(1);
        const target = document.getElementById(id);

        if (target) {
          const offsetTop = target.offsetTop - 100; // Account for fixed header
          window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
          });

          // Update URL without jumping
          history.replaceState(null, '', '#' + id);
        }
      });
    });
  }

  // ============================================================================
  // Keyboard Navigation
  // ============================================================================

  let focusedIndex = -1;
  let allLinks = [];

  /**
   * Handle keyboard navigation in TOC
   */
  function handleKeydown(e) {
    // Only handle if focus is within TOC
    if (!document.querySelector('.toc-sidebar:focus-within')) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIndex = Math.min(focusedIndex + 1, allLinks.length - 1);
      allLinks[focusedIndex]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIndex = Math.max(focusedIndex - 1, 0);
      allLinks[focusedIndex]?.focus();
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
      allLinks[focusedIndex]?.click();
    } else if (e.key === 'Home') {
      e.preventDefault();
      focusedIndex = 0;
      allLinks[0]?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      focusedIndex = allLinks.length - 1;
      allLinks[focusedIndex]?.focus();
    }
  }

  /**
   * Initialize keyboard navigation
   */
  function initKeyboardNavigation() {
    allLinks = Array.from(tocItems);

    // Track focused link
    allLinks.forEach((link, index) => {
      link.addEventListener('focus', () => {
        focusedIndex = index;
      });
    });

    keyboardHandler = handleKeydown;
    document.addEventListener('keydown', keyboardHandler);
  }

  // ============================================================================
  // Scroll Event Listener (Throttled for Performance)
  // ============================================================================

  /**
   * Throttled scroll handler
   */
  scrollHandler = throttleScroll(updateOnScroll);

  // ============================================================================
  // Initialization
  // ============================================================================

  /**
   * Initialize the TOC
   */
  function initTOC() {
    // Cache DOM elements
    tocItems = Array.from(document.querySelectorAll('[data-toc-item]'));
    progressBar = document.querySelector('.toc-progress-bar');
    progressPosition = document.querySelector('.toc-progress-position');
    tocNav = document.querySelector('.toc-nav');
    tocGroups = Array.from(document.querySelectorAll('details.toc-group'));
    tocScrollContainer = document.querySelector('.toc-scroll-container');

    if (!tocItems.length) return;

    // Get all heading targets
    headings = tocItems.map(item => {
      const id = item.getAttribute('data-toc-item').slice(1);
      const element = document.getElementById(id);
      return element ? { id, element, link: item } : null;
    }).filter(Boolean);

    if (!headings.length) return;

    // Load saved state
    loadState();

    // Initialize all features
    initGroupToggles();
    initControlButtons();
    initSmoothScroll();
    initKeyboardNavigation();

    // Set up scroll listener
    window.addEventListener('scroll', scrollHandler, { passive: true });

    // Initial update
    updateOnScroll();

    // Update on hash change (e.g., clicking links elsewhere)
    hashChangeHandler = updateActiveItem;
    window.addEventListener('hashchange', hashChangeHandler);

    // Update on resize (debounced)
    resizeHandler = debounce(updateActiveItem, 250);
    window.addEventListener('resize', resizeHandler, { passive: true });
  }

  /**
   * Cleanup function
   */
  function cleanup() {
    if (scrollHandler) {
      window.removeEventListener('scroll', scrollHandler);
      scrollHandler = null;
    }
    if (hashChangeHandler) {
      window.removeEventListener('hashchange', hashChangeHandler);
      hashChangeHandler = null;
    }
    if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler);
      resizeHandler = null;
    }
    if (keyboardHandler) {
      document.removeEventListener('keydown', keyboardHandler);
      keyboardHandler = null;
    }
  }

  // ============================================================================
  // Registration
  // ============================================================================

  // Register with enhancement system (primary method)
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('toc', function(el, options) {
      // Initialize TOC for this specific element
      initTOC();
    });
  }

  // ============================================================================
  // Auto-initialize
  // ============================================================================

  ready(initTOC);

  // Re-initialize on dynamic content load
  window.addEventListener('contentLoaded', initTOC);

  // Export for use by other scripts (backward compatibility)
  window.BengalTOC = {
    init: initTOC,
    cleanup: cleanup,
    updateActiveItem: updateActiveItem,
    expandAll: () => {
      tocGroups.forEach(group => {
        const groupId = getGroupId(group);
        expandGroup(group, groupId);
      });
    },
    collapseAll: () => {
      tocGroups.forEach(group => {
        const groupId = getGroupId(group);
        collapseGroup(group, groupId);
      });
    }
  };
})();
