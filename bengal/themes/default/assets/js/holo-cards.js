/**
 * Holographic Card Effects - Interactive JavaScript
 * Tracks mouse position and updates CSS custom properties for dynamic effects.
 *
 * Inspired by simeydotme/pokemon-cards-css
 * https://github.com/simeydotme/pokemon-cards-css
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    // Maximum rotation angle in degrees
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

  // State
  let rafId = null;
  let lastMoveTime = 0;

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
   * Update CSS custom properties on element
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
   * Handle mouse enter
   */
  function handleMouseEnter(event) {
    const element = event.currentTarget;
    element.classList.add('active');
  }

  /**
   * Handle mouse move with throttling
   */
  function handleMouseMove(event) {
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
   * Handle mouse leave
   */
  function handleMouseLeave(event) {
    const element = event.currentTarget;

    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }

    // Smoothly reset
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
    element.addEventListener('mouseenter', handleMouseEnter);
    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);

    // Touch support
    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchmove', handleTouchMove, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });
  }

  /**
   * Touch event handlers
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
   * Initialize all holo cards on the page
   */
  function initAllCards() {
    const cards = document.querySelectorAll(CONFIG.selectors.all);
    cards.forEach(initCard);
  }

  /**
   * Observe DOM for dynamically added cards
   */
  function observeDOM() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType !== Node.ELEMENT_NODE) return;

          // Check if the added node is a holo card
          if (node.matches && node.matches(CONFIG.selectors.all)) {
            initCard(node);
          }

          // Check children
          const children = node.querySelectorAll?.(CONFIG.selectors.all);
          if (children) {
            children.forEach(initCard);
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    return observer;
  }

  /**
   * Clean up function
   */
  function cleanup() {
    const cards = document.querySelectorAll(CONFIG.selectors.all);
    cards.forEach((element) => {
      element.removeEventListener('mouseenter', handleMouseEnter);
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
      element.removeEventListener('touchend', handleTouchEnd);
      delete element.dataset.holoInit;
    });
  }

  /**
   * Public API
   */
  window.HoloCards = {
    init: initAllCards,
    initCard: initCard,
    cleanup: cleanup,
    config: CONFIG
  };

  /**
   * Auto-initialize when DOM is ready
   */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initAllCards();
      observeDOM();
    });
  } else {
    initAllCards();
    observeDOM();
  }

  // Re-initialize on Turbo/PJAX navigation (if applicable)
  document.addEventListener('turbo:load', initAllCards);
  document.addEventListener('pjax:end', initAllCards);

})();

