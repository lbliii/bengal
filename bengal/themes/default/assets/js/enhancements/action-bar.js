/**
 * Action Bar Component
 *
 * PATTERN: POPOVER (see assets/COMPONENT-PATTERNS.md)
 * - Share dropdowns and metadata panel use native [popover] API
 * - Browser handles: show/hide, light dismiss, escape key, top layer
 * - JS handles: Copy functionality, AI share, popover positioning
 *
 * Supports both action-bar (classic) and page-hero (magazine) variants.
 */

(function () {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - action-bar.js requires utils.js');
    return;
  }

  const { log, copyToClipboard, ready } = window.BengalUtils;

  ready(init);

  function init() {
    initPopoverPositioning();
    initCopyActions();
    initAIShareActions();
    updateShareLinks();
  }

  /**
   * Initialize popover positioning relative to triggers
   * Native popover appears in top layer, so we need to position it manually
   */
  function initPopoverPositioning() {
    // Find all popover triggers
    const triggers = document.querySelectorAll('[popovertarget]');

    triggers.forEach(trigger => {
      const targetId = trigger.getAttribute('popovertarget');
      const popover = document.getElementById(targetId);

      if (!popover) return;

      // Position popover when it opens (not beforetoggle - need dimensions)
      popover.addEventListener('toggle', (e) => {
        if (e.newState === 'open') {
          positionPopover(trigger, popover);
        }
      });

      // Handle chevron rotation
      const chevron = trigger.querySelector('[class*="chevron"]');
      if (chevron) {
        popover.addEventListener('toggle', (e) => {
          if (e.newState === 'open') {
            chevron.style.transform = 'rotate(180deg)';
          } else {
            chevron.style.transform = 'rotate(0deg)';
          }
        });
      }
    });
  }

  /**
   * Position popover relative to its trigger
   */
  function positionPopover(trigger, popover) {
    const rect = trigger.getBoundingClientRect();
    const popoverRect = popover.getBoundingClientRect();

    // Position below trigger, aligned to right edge
    let top = rect.bottom + 8;
    let left = rect.right - popoverRect.width;

    // Ensure it doesn't go off-screen left
    if (left < 8) {
      left = 8;
    }

    // Ensure it doesn't go off-screen right
    const rightOverflow = left + popoverRect.width - window.innerWidth + 8;
    if (rightOverflow > 0) {
      left -= rightOverflow;
    }

    // Ensure it doesn't go off-screen bottom
    if (top + popoverRect.height > window.innerHeight - 8) {
      // Position above trigger instead
      top = rect.top - popoverRect.height - 8;
    }

    popover.style.top = `${top}px`;
    popover.style.left = `${left}px`;
  }

  /**
   * Initialize copy action buttons
   */
  function initCopyActions() {
    // Use event delegation for copy buttons
    document.addEventListener('click', async (e) => {
      const button = e.target.closest('[data-action^="copy"]');
      if (!button) return;

      e.preventDefault();
      await handleCopyAction(button);
    });
  }

  /**
   * Initialize AI share links
   * Fetch content, copy to clipboard, then navigate
   */
  function initAIShareActions() {
    document.addEventListener('click', async (e) => {
      const aiLink = e.target.closest('[data-ai]');
      if (!aiLink) return;

      e.preventDefault();
      await handleAIShare(aiLink);
    });
  }

  /**
   * Handle AI assistant share - fetch content, copy to clipboard, then navigate
   */
  async function handleAIShare(link) {
    const aiName = link.getAttribute('data-ai');
    const originalHref = link.getAttribute('href');

    // Extract the LLM text URL from the href query parameter
    // The href looks like: https://claude.ai/new?q=Please%20help...%3A%20https%3A%2F%2Fsite.com%2Fdocs%2Findex.txt
    const urlMatch = originalHref.match(/index\.txt/);
    if (!urlMatch) {
      // Fallback: just navigate normally
      window.open(originalHref, '_blank', 'noopener,noreferrer');
      return;
    }

    // Get the LLM text URL from the copy-llm-txt button (it has the correct URL)
    const popover = link.closest('[popover]');
    const copyLlmBtn = popover?.querySelector('[data-action="copy-llm-txt"]');
    if (!copyLlmBtn) {
      window.open(originalHref, '_blank', 'noopener,noreferrer');
      return;
    }

    const llmTxtUrl = copyLlmBtn.getAttribute('data-url');

    // Show loading state
    const originalHTML = link.innerHTML;
    link.innerHTML = `
      <svg class="spinning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      <span>Loading...</span>
    `;

    try {
      // Fetch the LLM text content
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(llmTxtUrl, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const content = await response.text();

      // Copy content to clipboard
      await copyToClipboard(content);

      // Build a prompt with the full URL for reference
      const fullUrl = toAbsoluteUrl(llmTxtUrl);
      const aiPrompt = 'I have documentation content from ' + fullUrl + ' copied to my clipboard. Please help me understand it.';

      // Build the AI-specific URL with the instruction prompt
      const aiUrl = buildAIUrl(aiName, aiPrompt);

      // Show success briefly then navigate
      link.innerHTML = `
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M5 13l4 4L19 7" />
        </svg>
        <span>Copied! Opening...</span>
      `;

      setTimeout(() => {
        link.innerHTML = originalHTML;
        // Close the popover
        popover?.hidePopover?.();
        window.open(aiUrl, '_blank', 'noopener,noreferrer');
      }, 500);

    } catch (error) {
      log('AI share failed:', error);
      link.innerHTML = originalHTML;

      // Show error and fallback to original behavior
      const errorSpan = document.createElement('span');
      errorSpan.style.cssText = 'color: var(--color-warning); font-size: 0.75rem; display: block;';
      errorSpan.textContent = 'Could not load content. Opening with URL only...';
      link.appendChild(errorSpan);

      setTimeout(() => {
        link.innerHTML = originalHTML;
        popover?.hidePopover?.();
        window.open(originalHref, '_blank', 'noopener,noreferrer');
      }, 1500);
    }
  }

  /**
   * Build AI-specific chat URL with prompt
   * Note: Using string concatenation instead of template literals to avoid
   * minifier bug where // in URLs is treated as comment start
   */
  function buildAIUrl(aiName, prompt) {
    const encodedPrompt = encodeURIComponent(prompt);
    const baseUrls = {
      'claude': 'https:' + '//claude.ai/new?q=',
      'chatgpt': 'https:' + '//chatgpt.com/?q=',
      'gemini': 'https:' + '//gemini.google.com/app?q=',
      'copilot': 'https:' + '//copilot.microsoft.com/?q='
    };

    const baseUrl = baseUrls[aiName] || baseUrls['claude'];
    return baseUrl + encodedPrompt;
  }

  /**
   * Update share links to use absolute URLs
   * This ensures we send full URLs to AI assistants even if baseurl was missing/relative
   */
  function updateShareLinks() {
    const aiLinks = document.querySelectorAll('.action-bar-share-ai, .page-hero__share-ai');

    aiLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (!href) return;

      try {
        const url = new URL(href);
        const params = new URLSearchParams(url.search);
        const q = params.get('q');

        if (q) {
          // Look for relative paths ending in index.txt
          // Regex matches path starting with / or current dir, ending in index.txt
          // Ensures we don't match absolute URLs (containing :)
          const relativeMatch = q.match(/(^|\s)(\/?[^:\s]*index\.txt)/);

          if (relativeMatch && relativeMatch[2] && !relativeMatch[2].startsWith('http')) {
            const relativePath = relativeMatch[2];
            const absolutePath = toAbsoluteUrl(relativePath);

            const newQ = q.replace(relativePath, absolutePath);
            params.set('q', newQ);
            url.search = params.toString();

            link.setAttribute('href', url.toString());
          }
        }
      } catch (e) {
        // Ignore invalid URLs
      }
    });
  }

  /**
   * Convert relative URL to absolute URL using current origin
   */
  function toAbsoluteUrl(relativeUrl) {
    if (!relativeUrl) {
      return window.location.href;
    }
    if (relativeUrl.startsWith('http://') || relativeUrl.startsWith('https://')) {
      return relativeUrl;
    }
    return window.location.origin + relativeUrl;
  }

  /**
   * Handle copy actions
   */
  async function handleCopyAction(button) {
    const action = button.getAttribute('data-action');
    const url = button.getAttribute('data-url');

    if (!url) {
      log('Copy action missing data-url attribute');
      showError(button, 'URL missing');
      return;
    }

    try {
      let textToCopy = '';

      switch (action) {
        case 'copy-url':
          // Copy full absolute URL for external sharing
          textToCopy = toAbsoluteUrl(url);
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
