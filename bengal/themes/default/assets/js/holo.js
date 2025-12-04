/**
 * Holographic Effect - Mouse Tracking
 * Updates CSS custom properties for holographic admonitions
 */

(function() {
  'use strict';

  function initHoloElements() {
    // Track all elements with holo class
    document.querySelectorAll('.admonition.holo').forEach(el => {
      el.addEventListener('mousemove', handleMouseMove);
      el.addEventListener('mouseleave', handleMouseLeave);
    });
  }

  function handleMouseMove(e) {
    const rect = this.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp values between 0 and 100
    const clampedX = Math.max(0, Math.min(100, x));
    const clampedY = Math.max(0, Math.min(100, y));

    this.style.setProperty('--holo-x', clampedX.toFixed(1));
    this.style.setProperty('--holo-y', clampedY.toFixed(1));
  }

  function handleMouseLeave() {
    // Reset to center when mouse leaves
    this.style.setProperty('--holo-x', '50');
    this.style.setProperty('--holo-y', '50');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHoloElements);
  } else {
    initHoloElements();
  }

  // Re-initialize if new content is added (for SPA-like navigation)
  if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1 && node.classList && node.classList.contains('holo')) {
            node.addEventListener('mousemove', handleMouseMove);
            node.addEventListener('mouseleave', handleMouseLeave);
          }
          if (node.querySelectorAll) {
            node.querySelectorAll('.admonition.holo').forEach(el => {
              el.addEventListener('mousemove', handleMouseMove);
              el.addEventListener('mouseleave', handleMouseLeave);
            });
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }
})();


