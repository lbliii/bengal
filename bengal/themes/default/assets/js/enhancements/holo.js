/**
 * Bengal Enhancement: Holographic Effects
 *
 * Merged from:
 * - holo.js (admonition holographic effects)
 * - holo-cards.js (card holographic effects)
 *
 * Provides interactive holographic effects for:
 * - Admonitions with .admonition.holo class
 * - Cards with .holo-card class
 *
 * Features:
 * - Mouse tracking for dynamic effects
 * - Touch support for mobile devices
 * - Automatic initialization and DOM observation
 * - Smooth animations with requestAnimationFrame
 *
 * @requires utils.js (optional, for logging)
 * @requires bengal-enhance.js (for enhancement registration)
 */

(function() {
  'use strict';

  // ============================================================
  // Dependencies
  // ============================================================

  // Utils are optional - graceful degradation if not available
  const log = window.BengalUtils?.log || (() => {});
  const ready = window.BengalUtils?.ready || ((fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  });

  // ============================================================
  // Configuration
  // ============================================================

  const CONFIG = {
    // Maximum rotation angle in degrees (for cards)
    maxRotation: 15,
    // Transition timing for smooth reset
    resetDuration: 400,
    // Throttle interval for mousemove (ms)
    throttleMs: 16, // ~60fps
    // Selectors
    selectors: {
      holoCard: '.holo-card',
      holoAdmonition: '.admonition.holo',
      all: '.holo-card, .admonition.holo'
    }
  };

  // ============================================================
  // State
  // ============================================================

  let rafId = null;
  let lastMoveTime = 0;
  let domObserver = null;
  let holoObserver = null; // For admonitions (legacy)

  // ============================================================
  // Private Functions - Admonition Effects (Legacy)
  // ============================================================

  /**
   * Initialize admonition holo element (legacy - simpler version)
   */
  function initAdmonitionElement(el) {
    // Skip if already initialized
    if (el.dataset.holoInit) return;
    el.dataset.holoInit = 'true';

    el.addEventListener('mousemove', handleAdmonitionMouseMove);
    el.addEventListener('mouseleave', handleAdmonitionMouseLeave);
  }

  function handleAdmonitionMouseMove(e) {
    const rect = this.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp values between 0 and 100
    const clampedX = Math.max(0, Math.min(100, x));
    const clampedY = Math.max(0, Math.min(100, y));

    this.style.setProperty('--holo-x', clampedX.toFixed(1));
    this.style.setProperty('--holo-y', clampedY.toFixed(1));
  }

  function handleAdmonitionMouseLeave() {
    // Reset to center when mouse leaves
    this.style.setProperty('--holo-x', '50');
    this.style.setProperty('--holo-y', '50');
  }

  // ============================================================
  // Private Functions - Card Effects
  // ============================================================

  /**
   * Calculate pointer position as percentage (0-100) relative to element
   */
  function getPointerPosition(event, element) {
    const rect = element.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Normalize to 0-100
    const percentX = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const percentY = Math.max(0, Math.min(100, (y / rect.height) * 100));

    return { x: percentX, y: percentY };
  }

  /**
   * Calculate rotation angles based on pointer position
   */
  function getRotation(percentX, percentY) {
    // Convert 0-100 to -1 to 1
    const normalX = (percentX / 50) - 1;
    const normalY = (percentY / 50) - 1;

    return {
      x: normalY * CONFIG.maxRotation,
      y: normalX * CONFIG.maxRotation
    };
  }

  /**
   * Update CSS custom properties on element (for cards)
   */
  function updateCardStyles(element, percentX, percentY) {
    const rotation = getRotation(percentX, percentY);

    element.style.setProperty('--pointer-x', percentX.toFixed(2));
    element.style.setProperty('--pointer-y', percentY.toFixed(2));
    element.style.setProperty('--rotate-x', `${rotation.x.toFixed(2)}deg`);
    element.style.setProperty('--rotate-y', `${rotation.y.toFixed(2)}deg`);
    element.style.setProperty('--bg-x', `${percentX}%`);
    element.style.setProperty('--bg-y', `${percentY}%`);
  }

  /**
   * Reset card to default state
   */
  function resetCardStyles(element) {
    element.style.setProperty('--pointer-x', '50');
    element.style.setProperty('--pointer-y', '50');
    element.style.setProperty('--rotate-x', '0deg');
    element.style.setProperty('--rotate-y', '0deg');
    element.style.setProperty('--bg-x', '50%');
    element.style.setProperty('--bg-y', '50%');
    element.classList.remove('active');
  }

  /**
   * Handle mouse enter (for cards)
   */
  function handleCardMouseEnter(event) {
    const element = event.currentTarget;
    element.classList.add('active');
  }

  /**
   * Handle mouse move with throttling (for cards)
   */
  function handleCardMouseMove(event) {
    const now = performance.now();
    if (now - lastMoveTime < CONFIG.throttleMs) return;
    lastMoveTime = now;

    const element = event.currentTarget;

    // Use requestAnimationFrame for smooth updates
    if (rafId) {
      cancelAnimationFrame(rafId);
    }

    rafId = requestAnimationFrame(() => {
      const pos = getPointerPosition(event, element);
      updateCardStyles(element, pos.x, pos.y);
    });
  }

  /**
   * Handle mouse leave (for cards)
   */
  function handleCardMouseLeave(event) {
    const element = event.currentTarget;

    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }

    // Smoothly reset
    resetCardStyles(element);
  }

  /**
   * Touch event handlers (for cards)
   */
  function handleTouchStart(event) {
    const element = event.currentTarget;
    element.classList.add('active');

    const touch = event.touches[0];
    const pos = getPointerPosition(touch, element);
    updateCardStyles(element, pos.x, pos.y);
  }

  function handleTouchMove(event) {
    const element = event.currentTarget;
    const touch = event.touches[0];

    if (rafId) {
      cancelAnimationFrame(rafId);
    }

    rafId = requestAnimationFrame(() => {
      const pos = getPointerPosition(touch, element);
      updateCardStyles(element, pos.x, pos.y);
    });
  }

  function handleTouchEnd(event) {
    const element = event.currentTarget;
    resetCardStyles(element);
  }

  /**
   * Initialize a single card element
   */
  function initCard(element) {
    // Skip if already initialized
    if (element.dataset.holoInit) return;
    element.dataset.holoInit = 'true';

    // Set initial state
    resetCardStyles(element);

    // Attach event listeners
    element.addEventListener('mouseenter', handleCardMouseEnter);
    element.addEventListener('mousemove', handleCardMouseMove);
    element.addEventListener('mouseleave', handleCardMouseLeave);

    // Touch support
    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchmove', handleTouchMove, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });
  }

  // ============================================================
  // Public API
  // ============================================================

  /**
   * Initialize all holo elements (admonitions and cards)
   */
  function init() {
    // Initialize cards
    const cards = document.querySelectorAll(CONFIG.selectors.holoCard);
    cards.forEach(initCard);

    // Initialize admonitions (legacy - simpler version)
    const admonitions = document.querySelectorAll(CONFIG.selectors.holoAdmonition);
    admonitions.forEach(initAdmonitionElement);

    log('[BengalHolo] Initialized');
  }

  /**
   * Initialize a single element (public API)
   */
  function initElement(el) {
    if (el.matches(CONFIG.selectors.holoCard)) {
      initCard(el);
    } else if (el.matches(CONFIG.selectors.holoAdmonition)) {
      initAdmonitionElement(el);
    }
  }

  /**
   * Cleanup function
   */
  function cleanup() {
    // Disconnect observers
    if (domObserver) {
      domObserver.disconnect();
      domObserver = null;
    }
    if (holoObserver) {
      holoObserver.disconnect();
      holoObserver = null;
    }

    // Remove event listeners
    const allElements = document.querySelectorAll(CONFIG.selectors.all);
    allElements.forEach((element) => {
      // Card listeners
      element.removeEventListener('mouseenter', handleCardMouseEnter);
      element.removeEventListener('mousemove', handleCardMouseMove);
      element.removeEventListener('mouseleave', handleCardMouseLeave);
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
      element.removeEventListener('touchend', handleTouchEnd);
      // Admonition listeners
      element.removeEventListener('mousemove', handleAdmonitionMouseMove);
      element.removeEventListener('mouseleave', handleAdmonitionMouseLeave);
      delete element.dataset.holoInit;
    });
  }

  /**
   * Observe DOM for dynamically added elements
   * Uses debouncing to prevent DevTools-induced feedback loops
   */
  function observeDOM() {
    // Prevent duplicate observers
    if (domObserver) return domObserver;

    // Debounce to batch rapid DOM changes (prevents DevTools crashes)
    let pendingNodes = [];
    let debounceTimer = null;

    function processPendingNodes() {
      const nodes = pendingNodes;
      pendingNodes = [];
      debounceTimer = null;

      nodes.forEach((node) => {
        // Check if the added node is a holo element
        if (node.matches && node.matches(CONFIG.selectors.all)) {
          initElement(node);
        }

        // Check children
        const children = node.querySelectorAll?.(CONFIG.selectors.all);
        if (children) {
          children.forEach(initElement);
        }
      });
    }

    domObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType !== Node.ELEMENT_NODE) return;
          pendingNodes.push(node);
        });
      });

      // Debounce processing
      if (pendingNodes.length > 0 && !debounceTimer) {
        debounceTimer = setTimeout(processPendingNodes, 50);
      }
    });

    domObserver.observe(document.body, {
      childList: true,
      subtree: true
    });

    return domObserver;
  }

  // ============================================================
  // Registration
  // ============================================================

  // Register with enhancement system (primary method)
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('holo', init);
  }

  // Export public API (backward compatibility)
  window.BengalHolo = {
    init: init,
    initElement: initElement,
    cleanup: cleanup,
  };

  // Also export HoloCards API for backward compatibility
  window.HoloCards = {
    init: init,
    initCard: initCard,
    cleanup: cleanup,
    config: CONFIG
  };

  // ============================================================
  // Auto-initialize
  // ============================================================

  ready(() => {
    init();
    observeDOM();
  });

  // Re-initialize on Turbo/PJAX navigation (if applicable)
  document.addEventListener('turbo:load', init);
  document.addEventListener('pjax:end', init);

})();
