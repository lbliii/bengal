/**
 * Bengal SSG Default Theme
 * Main JavaScript
 */

(function() {
  'use strict';

  /**
   * Smooth scroll for anchor links
   */
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');

        // Skip empty anchors
        if (href === '#') {
          return;
        }

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });

          // Update URL without jumping
          history.pushState(null, null, href);

          // Focus target for accessibility
          target.focus({ preventScroll: true });
        }
      });
    });
  }

  /**
   * Add external link indicators
   */
  function setupExternalLinks() {
    const links = document.querySelectorAll('a[href^="http"]');
    links.forEach(function(link) {
      const href = link.getAttribute('href');

      // Check if external (not same domain)
      if (!href.includes(window.location.hostname)) {
        // Add external attribute
        link.setAttribute('rel', 'noopener noreferrer');
        link.setAttribute('target', '_blank');

        // Add visual indicator (optional)
        link.setAttribute('aria-label', link.textContent + ' (opens in new tab)');
      }
    });
  }

  /**
   * Copy code button for code blocks with language labels
   */
  function setupCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');

    codeBlocks.forEach(function(codeBlock) {
      const pre = codeBlock.parentElement;

      // Skip if already processed
      if (pre.querySelector('.code-copy-button')) {
        return;
      }

      // Detect language from class (e.g., language-python, hljs-python)
      let language = '';
      const classList = codeBlock.className;
      const matches = classList.match(/language-(\w+)|hljs-(\w+)/);
      if (matches) {
        language = (matches[1] || matches[2]).toUpperCase();
      }

      // Create header container
      const header = document.createElement('div');
      header.className = 'code-header-inline';
      header.style.position = 'absolute';
      header.style.top = '0.5rem';
      header.style.right = '0.5rem';
      header.style.left = '0.5rem';
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
      header.style.pointerEvents = 'none';

      // Create language label if detected
      if (language) {
        const langLabel = document.createElement('span');
        langLabel.className = 'code-language';
        langLabel.textContent = language;
        langLabel.style.fontSize = '0.75rem';
        langLabel.style.fontWeight = '600';
        langLabel.style.color = 'var(--color-text-muted)';
        langLabel.style.textTransform = 'uppercase';
        langLabel.style.letterSpacing = '0.05em';
        langLabel.style.opacity = '0.7';
        header.appendChild(langLabel);
      } else {
        // Empty span to maintain layout
        header.appendChild(document.createElement('span'));
      }

      // Create copy button
      const button = document.createElement('button');
      button.className = 'code-copy-button';
      button.setAttribute('aria-label', 'Copy code to clipboard');
      button.style.pointerEvents = 'auto';

      // Add copy icon (SVG)
      button.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;

      header.appendChild(button);

      // Insert header
      pre.style.position = 'relative';
      pre.style.paddingTop = '2.5rem'; // Make room for header
      pre.insertBefore(header, pre.firstChild);

      // Copy functionality
      button.addEventListener('click', function(e) {
        e.preventDefault();
        const code = codeBlock.textContent;

        // Use Clipboard API if available
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(code).then(function() {
            // Show success
            button.innerHTML = `
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <span>Copied!</span>
            `;
            button.classList.add('copied');

            // Reset after 2 seconds
            setTimeout(function() {
              button.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy</span>
              `;
              button.classList.remove('copied');
            }, 2000);
          }).catch(function(err) {
            console.error('Failed to copy code:', err);
            button.textContent = 'Failed';

            setTimeout(function() {
              button.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy</span>
              `;
            }, 2000);
          });
        } else {
          // Fallback for older browsers
          const textarea = document.createElement('textarea');
          textarea.value = code;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();

          try {
            document.execCommand('copy');
            button.innerHTML = '<span>Copied!</span>';
            button.classList.add('copied');

            setTimeout(function() {
              button.innerHTML = '<span>Copy</span>';
              button.classList.remove('copied');
            }, 2000);
          } catch (err) {
            console.error('Failed to copy code:', err);
          } finally {
            document.body.removeChild(textarea);
          }
        }
      });
    });
  }

  /**
   * Lazy load images
   */
  function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
            }
            imageObserver.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(function(img) {
        imageObserver.observe(img);
      });
    } else {
      // Fallback for older browsers
      document.querySelectorAll('img[data-src]').forEach(function(img) {
        img.src = img.dataset.src;
      });
    }
  }

  /**
   * Table of contents highlighting
   */
  function setupTOCHighlight() {
    const toc = document.querySelector('.toc');
    if (!toc) return;

    const headings = document.querySelectorAll('h2[id], h3[id], h4[id]');
    const tocLinks = toc.querySelectorAll('a');

    if (headings.length === 0 || tocLinks.length === 0) return;

    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');

          // Remove active class from all links
          tocLinks.forEach(function(link) {
            link.classList.remove('active');
          });

          // Add active class to current link
          const activeLink = toc.querySelector('a[href="#' + id + '"]');
          if (activeLink) {
            activeLink.classList.add('active');
          }
        }
      });
    }, {
      rootMargin: '-80px 0px -80% 0px'
    });

    headings.forEach(function(heading) {
      observer.observe(heading);
    });
  }

  /**
   * Detect keyboard navigation for better focus indicators
   */
  function setupKeyboardDetection() {
    // Add class to body when user tabs (keyboard navigation)
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        document.body.classList.add('user-is-tabbing');
      }
    });

    // Remove class when user clicks (mouse navigation)
    document.addEventListener('mousedown', function() {
      document.body.classList.remove('user-is-tabbing');
    });
  }

  /**
   * Initialize all features
   */
  function init() {
    setupSmoothScroll();
    setupExternalLinks();
    setupCodeCopyButtons();
    setupLazyLoading();
    setupTOCHighlight();
    setupKeyboardDetection();

    // Log initialization (optional, remove in production)
    console.log('Bengal theme initialized');
  }

  // Initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
