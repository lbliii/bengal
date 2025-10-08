/**
 * Enhanced Table of Contents (TOC) JavaScript
 * 
 * Features:
 * - Intelligent grouping with collapsible H2 sections
 * - Active item tracking with auto-scroll
 * - Scroll progress indicator
 * - Quick navigation (top/bottom)
 * - Compact mode toggle
 * - Full keyboard navigation
 * - State persistence in localStorage
 */

(function() {
  'use strict';
  
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
  
  /**
   * Load state from localStorage
   */
  function loadState() {
    try {
      const savedState = localStorage.getItem('toc-state');
      if (savedState) {
        const state = JSON.parse(savedState);
        isCompactMode = state.compact || false;
        collapsedGroups = new Set(state.collapsed || []);
        
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
   */
  function updateActiveItem() {
    const scrollTop = window.scrollY;
    
    // Find active heading (closest one above viewport)
    let activeIndex = 0;
    for (let i = headings.length - 1; i >= 0; i--) {
      const heading = headings[i];
      if (heading.element.offsetTop <= scrollTop + 120) {
        activeIndex = i;
        break;
      }
    }
    
    // Only update if changed
    if (activeIndex === currentActiveIndex) return;
    currentActiveIndex = activeIndex;
    
    // Update active class on TOC links
    headings.forEach((heading, index) => {
      if (index === activeIndex) {
        heading.link.classList.add('active');
        
        // Auto-expand parent group if collapsed
        const parentGroup = heading.link.closest('.toc-group');
        if (parentGroup) {
          const groupId = getGroupId(parentGroup);
          if (collapsedGroups.has(groupId)) {
            expandGroup(parentGroup, groupId);
          }
          
          // Scroll into view if needed
          if (tocScrollContainer) {
            const linkRect = heading.link.getBoundingClientRect();
            const containerRect = tocScrollContainer.getBoundingClientRect();
            
            if (linkRect.top < containerRect.top || linkRect.bottom > containerRect.bottom) {
              heading.link.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
          }
        }
      } else {
        heading.link.classList.remove('active');
      }
    });
  }
  
  /**
   * Update on scroll (progress + active item)
   */
  function updateOnScroll() {
    updateProgress();
    updateActiveItem();
  }
  
  // ============================================================================
  // Collapsible Groups
  // ============================================================================
  
  /**
   * Get unique group ID
   */
  function getGroupId(group) {
    const link = group.querySelector('[data-toc-item]');
    return link ? link.getAttribute('data-toc-item') : null;
  }
  
  /**
   * Collapse a TOC group
   */
  function collapseGroup(group, groupId) {
    const toggle = group.querySelector('.toc-group-toggle');
    if (toggle) {
      toggle.setAttribute('aria-expanded', 'false');
    }
    group.setAttribute('data-collapsed', 'true');
    if (groupId) {
      collapsedGroups.add(groupId);
    }
    saveState();
  }
  
  /**
   * Expand a TOC group
   */
  function expandGroup(group, groupId) {
    const toggle = group.querySelector('.toc-group-toggle');
    if (toggle) {
      toggle.setAttribute('aria-expanded', 'true');
    }
    group.removeAttribute('data-collapsed');
    if (groupId) {
      collapsedGroups.delete(groupId);
    }
    saveState();
  }
  
  /**
   * Toggle a TOC group
   */
  function toggleGroup(group) {
    const groupId = getGroupId(group);
    const isCollapsed = group.hasAttribute('data-collapsed');
    
    if (isCollapsed) {
      expandGroup(group, groupId);
    } else {
      collapseGroup(group, groupId);
    }
  }
  
  /**
   * Initialize group toggle handlers
   */
  function initGroupToggles() {
    tocGroups.forEach(group => {
      const toggle = group.querySelector('.toc-group-toggle');
      const groupId = getGroupId(group);
      
      // Restore collapsed state
      if (groupId && collapsedGroups.has(groupId)) {
        collapseGroup(group, groupId);
      }
      
      if (toggle) {
        toggle.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          toggleGroup(group);
        });
      }
    });
  }
  
  // ============================================================================
  // Control Buttons
  // ============================================================================
  
  /**
   * Initialize control buttons (expand/collapse/compact)
   */
  function initControlButtons() {
    // Expand all sections
    const expandAllBtn = document.querySelector('[data-toc-action="expand-all"]');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', () => {
        tocGroups.forEach(group => {
          const groupId = getGroupId(group);
          expandGroup(group, groupId);
        });
      });
    }
    
    // Collapse all sections
    const collapseAllBtn = document.querySelector('[data-toc-action="collapse-all"]');
    if (collapseAllBtn) {
      collapseAllBtn.addEventListener('click', () => {
        tocGroups.forEach(group => {
          const groupId = getGroupId(group);
          collapseGroup(group, groupId);
        });
      });
    }
    
    // Toggle compact mode
    const compactBtn = document.querySelector('[data-toc-action="toggle-compact"]');
    if (compactBtn) {
      compactBtn.addEventListener('click', () => {
        isCompactMode = !isCompactMode;
        if (tocNav) {
          tocNav.setAttribute('data-toc-mode', isCompactMode ? 'compact' : 'normal');
        }
        saveState();
        
        // Visual feedback
        compactBtn.style.transform = 'scale(0.9)';
        setTimeout(() => {
          compactBtn.style.transform = '';
        }, 150);
      });
    }
  }
  
  // ============================================================================
  // Quick Navigation
  // ============================================================================
  
  /**
   * Initialize quick navigation buttons (top/bottom)
   */
  function initQuickNavigation() {
    const jumpTopBtn = document.querySelector('[data-toc-jump="top"]');
    if (jumpTopBtn) {
      jumpTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
    
    const jumpBottomBtn = document.querySelector('[data-toc-jump="bottom"]');
    if (jumpBottomBtn) {
      jumpBottomBtn.addEventListener('click', () => {
        window.scrollTo({ 
          top: document.documentElement.scrollHeight, 
          behavior: 'smooth' 
        });
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
    
    document.addEventListener('keydown', handleKeydown);
  }
  
  // ============================================================================
  // Scroll Event Listener (Throttled for Performance)
  // ============================================================================
  
  let ticking = false;
  
  /**
   * Throttled scroll handler
   */
  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateOnScroll();
        ticking = false;
      });
      ticking = true;
    }
  }
  
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
    tocGroups = Array.from(document.querySelectorAll('.toc-group'));
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
    initQuickNavigation();
    initSmoothScroll();
    initKeyboardNavigation();
    
    // Set up scroll listener
    window.addEventListener('scroll', onScroll, { passive: true });
    
    // Initial update
    updateOnScroll();
    
    // Update on hash change (e.g., clicking links elsewhere)
    window.addEventListener('hashchange', updateActiveItem);
    
    // Update on resize (debounced)
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(updateActiveItem, 250);
    }, { passive: true });
  }
  
  /**
   * Cleanup function
   */
  function cleanup() {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('hashchange', updateActiveItem);
    document.removeEventListener('keydown', handleKeydown);
  }
  
  // ============================================================================
  // Auto-initialize
  // ============================================================================
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTOC);
  } else {
    initTOC();
  }
  
  // Re-initialize on dynamic content load
  window.addEventListener('contentLoaded', initTOC);
  
  // Export for use by other scripts
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

