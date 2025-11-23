/**
 * Action Bar Component
 *
 * Handles:
 * - Expandable metadata toggle
 * - Share dropdown interactions
 * - Copy functionality for URLs and LLM text
 */

(function() {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - action-bar.js requires utils.js');
    return;
  }

  const { log, copyToClipboard, ready } = window.BengalUtils;

  ready(init);

  function init() {
    initMetadataToggle();
    initShareDropdown();
  }

  /**
   * Initialize metadata toggle functionality
   */
  function initMetadataToggle() {
    const toggleBtn = document.querySelector('.action-bar-meta-toggle');
    const metadataPanel = document.getElementById('action-bar-metadata');

    if (!toggleBtn || !metadataPanel) return;

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';

      toggleBtn.setAttribute('aria-expanded', !isExpanded);
      metadataPanel.setAttribute('aria-hidden', isExpanded);
    });
  }

  /**
   * Initialize share dropdown functionality
   */
  function initShareDropdown() {
    const trigger = document.querySelector('.action-bar-share-trigger');
    const dropdown = document.querySelector('.action-bar-share-dropdown');

    if (!trigger || !dropdown) return;

    // Toggle dropdown
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleDropdown(trigger, dropdown);
    });

    // Copy actions
    const copyButtons = dropdown.querySelectorAll('[data-action^="copy"]');
    copyButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        handleCopyAction(button);
      });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      const shareWrapper = trigger.closest('.action-bar-share');
      if (!shareWrapper || !shareWrapper.contains(e.target)) {
        closeDropdown(trigger, dropdown);
      }
    });

    // Close dropdown on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && dropdown.getAttribute('aria-hidden') === 'false') {
        closeDropdown(trigger, dropdown);
        trigger.focus();
      }
    });

    // Close dropdown when selecting AI link
    const aiLinks = dropdown.querySelectorAll('.action-bar-share-ai');
    aiLinks.forEach(link => {
      link.addEventListener('click', () => {
        setTimeout(() => closeDropdown(trigger, dropdown), 100);
      });
    });
  }

  /**
   * Toggle dropdown open/closed
   */
  function toggleDropdown(trigger, dropdown) {
    const isOpen = trigger.getAttribute('aria-expanded') === 'true';

    if (isOpen) {
      closeDropdown(trigger, dropdown);
    } else {
      openDropdown(trigger, dropdown);
    }
  }

  /**
   * Open dropdown
   */
  function openDropdown(trigger, dropdown) {
    trigger.setAttribute('aria-expanded', 'true');
    dropdown.setAttribute('aria-hidden', 'false');
  }

  /**
   * Close dropdown
   */
  function closeDropdown(trigger, dropdown) {
    trigger.setAttribute('aria-expanded', 'false');
    dropdown.setAttribute('aria-hidden', 'true');
  }

  /**
   * Handle copy actions
   */
  async function handleCopyAction(button) {
    const action = button.getAttribute('data-action');
    const url = button.getAttribute('data-url');

    try {
      let textToCopy = '';

      switch(action) {
        case 'copy-url':
          textToCopy = url;
          await copyToClipboard(textToCopy);
          showSuccess(button, 'URL copied!');
          break;

        case 'copy-llm-txt':
          // Add timeout for fetch
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 5000);
          try {
            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            textToCopy = await response.text();
            await copyToClipboard(textToCopy);
            showSuccess(button, 'LLM text copied!');
          } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
              throw new Error('Request timed out');
            }
            throw fetchError;
          }
          break;

        default:
          log('Unknown copy action:', action);
      }
    } catch (error) {
      log('Copy failed:', error);
      showError(button, 'Copy failed');
    }
  }

  /**
   * Show success feedback
   */
  function showSuccess(button, message) {
    const originalHTML = button.innerHTML;

    button.classList.add('success');
    button.innerHTML = `
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M5 13l4 4L19 7" />
      </svg>
      <span>${message}</span>
    `;

    setTimeout(() => {
      button.classList.remove('success');
      button.innerHTML = originalHTML;
    }, 2000);
  }

  /**
   * Show error feedback
   */
  function showError(button, message) {
    const originalHTML = button.innerHTML;

    button.innerHTML = `
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M6 18L18 6M6 6l12 12" />
      </svg>
      <span>${message}</span>
    `;

    setTimeout(() => {
      button.innerHTML = originalHTML;
    }, 2000);
  }

})();
