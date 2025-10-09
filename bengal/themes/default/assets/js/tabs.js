/**
 * Tabs JavaScript
 * Handles tab switching functionality
 */

(function() {
  'use strict';

  /**
   * Initialize all tab components
   */
  function initTabs() {
    const tabContainers = document.querySelectorAll('.tabs, .code-tabs');
    
    tabContainers.forEach(container => {
      const tabLinks = container.querySelectorAll('.tab-nav a');
      const tabPanes = container.querySelectorAll('.tab-pane');
      
      // Add click handlers to tab links
      tabLinks.forEach((link, index) => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          switchTab(container, index);
        });
        
        // Keyboard navigation
        link.addEventListener('keydown', (e) => {
          handleTabKeyboard(e, tabLinks, index);
        });
      });
      
      // Handle hash-based tab activation
      const hash = window.location.hash;
      if (hash) {
        const targetPane = container.querySelector(hash);
        if (targetPane) {
          const paneIndex = Array.from(tabPanes).indexOf(targetPane);
          if (paneIndex !== -1) {
            switchTab(container, paneIndex);
          }
        }
      }
    });
  }

  /**
   * Switch to a specific tab
   */
  function switchTab(container, index) {
    const tabLinks = container.querySelectorAll('.tab-nav li');
    const tabPanes = container.querySelectorAll('.tab-pane');
    
    // Remove active class from all tabs and panes
    tabLinks.forEach(li => li.classList.remove('active'));
    tabPanes.forEach(pane => pane.classList.remove('active'));
    
    // Add active class to selected tab and pane
    if (tabLinks[index]) {
      tabLinks[index].classList.add('active');
    }
    if (tabPanes[index]) {
      tabPanes[index].classList.add('active');
      
      // Trigger custom event for other scripts
      const event = new CustomEvent('tabSwitched', {
        detail: {
          container: container,
          index: index,
          pane: tabPanes[index]
        }
      });
      container.dispatchEvent(event);
    }
  }

  /**
   * Handle keyboard navigation in tabs
   */
  function handleTabKeyboard(e, tabLinks, currentIndex) {
    let newIndex = currentIndex;
    
    switch(e.key) {
      case 'ArrowLeft':
        e.preventDefault();
        newIndex = currentIndex > 0 ? currentIndex - 1 : tabLinks.length - 1;
        break;
      case 'ArrowRight':
        e.preventDefault();
        newIndex = currentIndex < tabLinks.length - 1 ? currentIndex + 1 : 0;
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = tabLinks.length - 1;
        break;
      default:
        return;
    }
    
    tabLinks[newIndex].focus({ preventScroll: true });
    tabLinks[newIndex].click();
  }

  /**
   * Save/restore tab state in sessionStorage
   */
  function saveTabState(containerId, index) {
    try {
      sessionStorage.setItem(`tab-${containerId}`, index.toString());
    } catch (e) {
      // sessionStorage not available
    }
  }

  function restoreTabState(containerId) {
    try {
      const saved = sessionStorage.getItem(`tab-${containerId}`);
      return saved !== null ? parseInt(saved, 10) : 0;
    } catch (e) {
      return 0;
    }
  }

  /**
   * Initialize on DOM ready
   */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTabs);
  } else {
    initTabs();
  }

  /**
   * Re-initialize on dynamic content load
   */
  window.addEventListener('contentLoaded', initTabs);

  // Export for use by other scripts
  window.BengalTabs = {
    init: initTabs,
    switchTab: switchTab
  };
})();

