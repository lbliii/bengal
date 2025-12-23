/**
 * Bengal SSG Default Theme
 * Image Lightbox
 *
 * PATTERN: DIALOG (see assets/COMPONENT-PATTERNS.md)
 * - Uses native <dialog> element with .showModal()
 * - Browser handles: focus trap, escape key, backdrop, inert on background
 * - JS handles: Image loading, navigation between images
 *
 * Click to enlarge images in a beautiful lightbox overlay.
 * No dependencies, vanilla JavaScript.
 */

(function() {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - lightbox.js requires utils.js');
    return;
  }

  const { log, ready } = window.BengalUtils;

  let dialog = null;
  let currentImage = null;

  /**
   * Get or create lightbox dialog element
   */
  function getDialog() {
    if (dialog) return dialog;

    // Try to find existing dialog from template first
    dialog = document.getElementById('lightbox-dialog');

    if (!dialog) {
      // Fallback: create dynamically if not in template
      dialog = document.createElement('dialog');
      dialog.id = 'lightbox-dialog';
      dialog.className = 'lightbox-dialog';
      dialog.setAttribute('aria-label', 'Image lightbox');

      const img = document.createElement('img');
      img.className = 'lightbox-dialog__image';
      img.alt = '';

      const form = document.createElement('form');
      form.method = 'dialog';
      form.className = 'lightbox-dialog__controls';

      const closeButton = document.createElement('button');
      closeButton.type = 'submit';
      closeButton.className = 'lightbox-dialog__close';
      closeButton.setAttribute('aria-label', 'Close lightbox');
      closeButton.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      `;
      form.appendChild(closeButton);

      const caption = document.createElement('div');
      caption.className = 'lightbox-dialog__caption';

      dialog.appendChild(img);
      dialog.appendChild(form);
      dialog.appendChild(caption);
      document.body.appendChild(dialog);
    }

    // Click on backdrop (dialog element itself) closes
    dialog.addEventListener('click', function(e) {
      if (e.target === dialog) {
        dialog.close();
      }
    });

    // Keyboard navigation
    dialog.addEventListener('keydown', handleKeyboard);

    return dialog;
  }

  /**
   * Open lightbox with an image
   *
   * @param {HTMLImageElement} imgElement - Image element to display
   */
  function openLightbox(imgElement) {
    const d = getDialog();

    currentImage = imgElement;
    const img = d.querySelector('.lightbox-dialog__image');
    const caption = d.querySelector('.lightbox-dialog__caption');

    // Set image source (use high-res version if available)
    const highResSrc = imgElement.getAttribute('data-lightbox-src') || imgElement.src;
    img.src = highResSrc;
    img.alt = imgElement.alt;

    // Set caption if available
    const captionText = imgElement.alt || imgElement.getAttribute('data-caption');
    if (captionText) {
      caption.textContent = captionText;
      caption.style.display = 'block';
    } else {
      caption.style.display = 'none';
    }

    // Show dialog using native modal (handles focus trap, backdrop, escape key)
    d.showModal();
  }

  /**
   * Close lightbox
   */
  function closeLightbox() {
    if (!dialog) return;

    dialog.close();

    // Return focus to the original image
    if (currentImage) {
      currentImage.focus();
    }

    currentImage = null;
  }

  /**
   * Handle keyboard controls
   *
   * @param {KeyboardEvent} e - Keyboard event
   */
  function handleKeyboard(e) {
    if (!dialog || !dialog.open) return;

    switch (e.key) {
      case 'ArrowLeft':
        // Navigate to previous image (if multiple)
        navigateImages(-1);
        e.preventDefault();
        break;

      case 'ArrowRight':
        // Navigate to next image (if multiple)
        navigateImages(1);
        e.preventDefault();
        break;

      // Escape is handled natively by <dialog>
    }
  }

  /**
   * Navigate between images (if multiple in a gallery)
   *
   * @param {number} direction - Direction to navigate (-1 or 1)
   */
  function navigateImages(direction) {
    if (!currentImage) return;

    // Find all lightbox-enabled images
    const images = Array.from(document.querySelectorAll('[data-lightbox]'));
    const currentIndex = images.indexOf(currentImage);

    if (currentIndex === -1 || images.length <= 1) return;

    // Calculate new index (with wrapping)
    let newIndex = currentIndex + direction;
    if (newIndex < 0) newIndex = images.length - 1;
    if (newIndex >= images.length) newIndex = 0;

    // Open new image
    openLightbox(images[newIndex]);
  }

  /**
   * Setup lightbox for images
   * Automatically adds lightbox to all content images
   */
  function setupImageLightbox() {
    // Find all images in content areas
    const selectors = [
      '.prose img',
      '.docs-content img',
      'article img',
      'main img'
    ];

    const images = document.querySelectorAll(selectors.join(', '));

    images.forEach(img => {
      // Skip if already has lightbox or explicitly disabled
      if (img.hasAttribute('data-lightbox') || img.hasAttribute('data-no-lightbox')) {
        return;
      }

      // Skip small images (icons, avatars)
      if (img.width < 400 && img.height < 400) {
        return;
      }

      // Skip images inside links (they already have a destination)
      if (img.closest('a')) {
        return;
      }

      // Enable lightbox
      img.setAttribute('data-lightbox', '');
      img.setAttribute('tabindex', '0');
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', `View larger version of: ${img.alt || 'image'}`);

      // Add click handler
      img.addEventListener('click', function() {
        openLightbox(this);
      });

      // Add keyboard handler for accessibility
      img.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openLightbox(this);
        }
      });
    });
  }

  /**
   * Initialize
   */
  function init() {
    setupImageLightbox();
    log('Image lightbox initialized (native dialog)');
  }

  // Initialize when DOM is ready
  ready(init);

  // Re-run setup if images are dynamically added
  // (e.g., via AJAX or lazy loading)
  // Use debounced observer to avoid conflicts with dev tools
  let mutationObserver = null;
  let updateTimeout = null;
  if (typeof MutationObserver !== 'undefined') {
    let isUpdating = false;
    const { debounce } = window.BengalUtils || {};

    const debouncedSetup = debounce ? debounce(function() {
      if (!isUpdating) {
        isUpdating = true;
        setupImageLightbox();
        setTimeout(function() { isUpdating = false; }, 100);
      }
    }, 250) : function() {
      if (isUpdating) return;
      clearTimeout(updateTimeout);
      updateTimeout = setTimeout(function() {
        if (!isUpdating) {
          isUpdating = true;
          setupImageLightbox();
          setTimeout(function() { isUpdating = false; }, 100);
        }
      }, 250);
    };

    mutationObserver = new MutationObserver(function(mutations) {
      // Skip if already updating to prevent loops
      if (isUpdating) return;

      let shouldUpdate = false;
      mutations.forEach(function(mutation) {
        if (mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach(function(node) {
            // Ignore text nodes, script tags, and dev tools elements
            if (node.nodeType !== 1) return; // Only element nodes
            if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;

            // Ignore nodes that are likely dev tools (contain dev tools markers)
            if (node.id && (
              node.id.includes('devtools') ||
              node.id.includes('chrome-devtools') ||
              node.id.includes('firefox-devtools') ||
              node.id.includes('__react') ||
              node.id.includes('__vue')
            )) return;

            // Ignore nodes with dev tools classes
            if (node.className && typeof node.className === 'string' && (
              node.className.includes('devtools') ||
              node.className.includes('chrome-devtools')
            )) return;

            // Only check content areas, not entire body
            const isInContentArea = node.closest && (
              node.closest('.prose') ||
              node.closest('.docs-content') ||
              node.closest('article') ||
              node.closest('main')
            );

            if (isInContentArea && (node.nodeName === 'IMG' || (node.querySelector && node.querySelector('img')))) {
              shouldUpdate = true;
            }
          });
        }
      });

      if (shouldUpdate) {
        debouncedSetup();
      }
    });

    // Only observe content areas, not entire body to avoid dev tools conflicts
    const contentAreas = document.querySelectorAll('.prose, .docs-content, article, main');
    if (contentAreas.length > 0) {
      contentAreas.forEach(function(area) {
        if (mutationObserver) {
          mutationObserver.observe(area, {
            childList: true,
            subtree: true
          });
        }
      });
    } else {
      // Fallback: observe body but with more defensive checks
      if (mutationObserver) {
        mutationObserver.observe(document.body, {
          childList: true,
          subtree: true
        });
      }
    }
  }

  /**
   * Cleanup function to prevent memory leaks
   */
  function cleanup() {
    if (mutationObserver) {
      mutationObserver.disconnect();
      mutationObserver = null;
    }
    if (updateTimeout) {
      clearTimeout(updateTimeout);
      updateTimeout = null;
    }
  }

  // ============================================================
  // Registration
  // ============================================================

  // Register with enhancement system (primary method)
  if (window.Bengal && window.Bengal.enhance) {
    Bengal.enhance.register('lightbox', function(el, options) {
      // Lightbox auto-initializes on image clicks via event delegation
      // This registration allows the enhancement system to track it
      log('[BengalLightbox] Registered via enhancement system');
    });
  }

  // ============================================================
  // Auto-initialize
  // ============================================================

  // Cleanup on page unload to prevent memory leaks
  window.addEventListener('beforeunload', cleanup);

  // Export cleanup for manual cleanup if needed (backward compatibility)
  window.BengalLightbox = {
    cleanup: cleanup,
    open: openLightbox,
    close: closeLightbox
  };

})();
