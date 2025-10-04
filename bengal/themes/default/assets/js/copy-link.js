/**
 * Bengal SSG Default Theme
 * Copy Link Buttons
 * 
 * Adds copy-to-clipboard buttons to headings for easy sharing.
 */

(function() {
  'use strict';

  /**
   * Copy Link Buttons for Headings
   * Adds a button to copy the heading's anchor link to clipboard
   */
  function setupCopyLinkButtons() {
    // Find all headings with IDs (anchors)
    const headings = document.querySelectorAll('h2[id], h3[id], h4[id], h5[id], h6[id]');
    
    if (headings.length === 0) return;
    
    headings.forEach(heading => {
      // Skip if already has copy button
      if (heading.querySelector('.copy-link')) return;
      
      // Wrap heading in anchor container
      if (!heading.classList.contains('heading-anchor')) {
        heading.classList.add('heading-anchor');
      }
      
      // Create copy button
      const button = document.createElement('button');
      button.className = 'copy-link';
      button.setAttribute('aria-label', 'Copy link to this section');
      button.setAttribute('title', 'Copy link');
      button.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
        </svg>
      `;
      
      // Add click handler
      button.addEventListener('click', function(e) {
        e.preventDefault();
        const id = heading.getAttribute('id');
        const url = `${window.location.origin}${window.location.pathname}#${id}`;
        
        // Copy to clipboard
        copyToClipboard(url, button);
      });
      
      // Add button to heading
      heading.appendChild(button);
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
    console.log('Copy link buttons initialized');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

