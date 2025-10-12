/**
 * Bengal SSG Default Theme
 * Copy Link Anchors
 *
 * Adds copy-to-clipboard anchor links to headings for easy sharing.
 * Links work as both permalinks and clipboard copy buttons.
 */

(function() {
  'use strict';

  /**
   * Copy Link Anchors for Headings
   * Adds an anchor link that copies the heading's URL to clipboard on click
   * and works as a normal permalink on right-click or ctrl/cmd+click
   */
  function setupCopyLinkButtons() {
    // Find all headings with IDs (anchors)
    const headings = document.querySelectorAll('h2[id], h3[id], h4[id], h5[id], h6[id]');

    if (headings.length === 0) return;

    headings.forEach(heading => {
      // Skip if already has copy link
      if (heading.querySelector('.copy-link')) return;

      // Wrap heading in anchor container
      if (!heading.classList.contains('heading-anchor')) {
        heading.classList.add('heading-anchor');
      }

      // Create copy link (anchor tag for proper link semantics)
      const id = heading.getAttribute('id');
      const link = document.createElement('a');
      link.href = `#${id}`;
      link.className = 'copy-link';
      link.setAttribute('aria-label', 'Copy link to this section');
      link.setAttribute('title', 'Copy link');
      link.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
        </svg>
      `;

      // Add click handler for copy (preserve right-click/ctrl+click for native link behavior)
      link.addEventListener('click', function(e) {
        // Only intercept normal left-clicks without modifiers
        if (!e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) {
          e.preventDefault();
          const url = `${window.location.origin}${window.location.pathname}#${id}`;

          // Copy to clipboard
          copyToClipboard(url, link);
        }
        // Otherwise let the browser handle it as a normal link
      });

      // Add link to heading
      heading.appendChild(link);
    });
  }

  /**
   * Copy text to clipboard with fallback
   *
   * @param {string} text - Text to copy
   * @param {HTMLElement} button - Button element to show feedback
   */
  function copyToClipboard(text, button) {
    // Modern Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showCopySuccess(button);
      }).catch(err => {
        console.error('Failed to copy:', err);
        showCopyError(button);
      });
    } else {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();

      try {
        const successful = document.execCommand('copy');
        if (successful) {
          showCopySuccess(button);
        } else {
          showCopyError(button);
        }
      } catch (err) {
        console.error('Failed to copy:', err);
        showCopyError(button);
      } finally {
        document.body.removeChild(textarea);
      }
    }
  }

  /**
   * Show success feedback
   */
  function showCopySuccess(button) {
    // Change icon to checkmark
    button.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;
    button.classList.add('copied');
    button.setAttribute('aria-label', 'Link copied!');

    // Reset after 2 seconds
    setTimeout(() => {
      button.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
        </svg>
      `;
      button.classList.remove('copied');
      button.setAttribute('aria-label', 'Copy link to this section');
    }, 2000);
  }

  /**
   * Show error feedback
   */
  function showCopyError(button) {
    button.setAttribute('aria-label', 'Failed to copy');

    // Reset after 2 seconds
    setTimeout(() => {
      button.setAttribute('aria-label', 'Copy link to this section');
    }, 2000);
  }

  /**
   * Initialize
   */
  function init() {
    setupCopyLinkButtons();
    console.log('Copy link anchors initialized');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
